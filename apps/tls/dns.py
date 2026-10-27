"""
تشخیص DNS و آی‌پی سرور، با تحمل خطای شبکه‌های ایران.

سرویس‌دهنده‌های DNS سیستم (resolv.conf) در بسیاری از سرورهای ایرانی فقط
یک آدرس دارند که گاهی کند، فیلتر یا از کار افتاده است. اگر فقط به همان
resolver سیستمی تکیه کنیم، صدور TLS با خطای دروغین «رکورد DNS پیدا نشد»
متوقف می‌شود، در حالی که خود Let's Encrypt (که اعتبارسنجی واقعی را انجام
می‌دهد) هیچ مشکلی در تحریم یا فیلترینگ ندارد و دامنه را درست می‌بیند.

برای همین اینجا دو لایه داریم:
1) ریزالور سیستم (سریع‌ترین حالت، معمولاً کافی است).
2) اگر آن خالی برگشت: چند DNS resolver عمومی و معروفِ ایران (شکن،
   403online، الکترو) به‌علاوه چند resolver بین‌المللی، مستقیماً و موازی
   با UDP خام (بدون هیچ وابستگیِ بیرونی) پرسیده می‌شوند.

نتیجه این است که «رکورد پیدا نشد» فقط وقتی نشان داده می‌شود که دست‌کم
یکی از این resolverها واقعاً و قطعی (NOERROR/NXDOMAIN) جواب داده باشد؛
اگر همه timeout بزنند (یعنی وضعیت نامعلوم است، نه قطعاً خالی)، لایه‌ی
سرویس (service.py) به‌جایِ متوقف‌کردن کار، صدور acme.sh را هم امتحان
می‌کند -- چون داور نهایی، سرورهای اعتبارسنجیِ خودِ Let's Encrypt هستند
نه resolver محلی ما.
"""

import random
import re
import socket
import struct
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
IPV6_RE = re.compile(r"^[0-9a-f:]+$")

# resolverهای عمومی برای حالتی که resolver سیستم جواب نداد. چندتای اول
# resolverهای «ضد تحریم/ضد فیلتر» معروف ایران هستند که از داخل شبکه‌ی
# کشور معمولاً بدون مشکل در دسترس‌اند؛ بقیه برای تکمیل و تنوع‌اند.
FALLBACK_RESOLVERS = [
    "178.22.122.100",  # Shecan
    "185.51.200.2",    # Shecan
    "10.202.10.10",    # 403.online
    "10.202.10.11",    # 403.online
    "78.157.42.100",   # Electro
    "78.157.42.101",   # Electro
    "1.1.1.1",         # Cloudflare
    "1.0.0.1",
    "8.8.8.8",          # Google
    "8.8.4.4",
    "9.9.9.9",          # Quad9
]

# برای خودِ سرور هم چند سرویسِ تشخیص آی‌پی عمومی را امتحان می‌کنیم؛ اگر
# یکی از آن‌ها در دسترس نبود (فیلتر/قطعی) بقیه جایگزین می‌شوند.
IP_ECHO_URLS = [
    "https://api.ipify.org",
    "https://ipv4.icanhazip.com",
    "https://ifconfig.me/ip",
    "https://checkip.amazonaws.com",
]


def _valid_v4(value: str) -> bool:
    if not IPV4_RE.fullmatch(value or ""):
        return False
    parts = [int(part) for part in value.split(".")]
    if any(part > 255 for part in parts):
        return False
    if value.startswith("127.") or value == "0.0.0.0" or value.startswith("169.254."):
        return False
    return True


def _resolver_list() -> list[str]:
    extra: list[str] = []
    try:
        from django.conf import settings

        raw = getattr(settings, "TLS_DNS_RESOLVERS", "") or ""
        extra = [token.strip() for token in re.split(r"[\s,]+", raw) if token.strip()]
    except Exception:
        extra = []
    merged = extra + [ip for ip in FALLBACK_RESOLVERS if ip not in extra]
    return merged


def _build_query(name: str, qtype: int) -> tuple[bytes, int]:
    tid = random.randint(0, 65535)
    header = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    labels = [label for label in name.rstrip(".").split(".") if label]
    question = b""
    for label in labels:
        encoded = label.encode("idna") if not label.isascii() else label.encode("ascii")
        question += bytes([len(encoded)]) + encoded
    question += b"\x00" + struct.pack(">HH", qtype, 1)
    return header + question, tid


def _parse_name(data: bytes, offset: int) -> tuple[str, int]:
    labels = []
    hops = 0
    cursor = offset
    end_of_record = None
    while hops < 128:
        if cursor >= len(data):
            break
        length = data[cursor]
        if length == 0:
            cursor += 1
            if end_of_record is None:
                end_of_record = cursor
            break
        if length & 0xC0 == 0xC0:
            if cursor + 1 >= len(data):
                break
            pointer = ((length & 0x3F) << 8) | data[cursor + 1]
            if end_of_record is None:
                end_of_record = cursor + 2
            cursor = pointer
            hops += 1
            continue
        cursor += 1
        labels.append(data[cursor:cursor + length].decode("ascii", "ignore"))
        cursor += length
    if end_of_record is None:
        end_of_record = cursor
    return ".".join(labels), end_of_record


def _parse_response(data: bytes, tid: int) -> tuple[set[str], bool]:
    """برمی‌گرداند (آی‌پی‌های پیدا شده, آیا پاسخ قطعی/معتبر بود)."""
    if len(data) < 12:
        return set(), False
    r_tid, flags, qdcount, ancount = struct.unpack(">HHHH", data[0:8])
    if r_tid != tid:
        return set(), False
    is_response = bool(flags & 0x8000)
    rcode = flags & 0x000F
    if not is_response or rcode not in (0, 3):  # NOERROR یا NXDOMAIN معتبرند
        return set(), False
    offset = 12
    for _ in range(qdcount):
        _, offset = _parse_name(data, offset)
        offset += 4
    found: set[str] = set()
    for _ in range(ancount):
        if offset >= len(data):
            break
        _, offset = _parse_name(data, offset)
        if offset + 10 > len(data):
            break
        rtype, _rclass, _ttl, rdlength = struct.unpack(">HHIH", data[offset:offset + 10])
        offset += 10
        rdata = data[offset:offset + rdlength]
        offset += rdlength
        if rtype == 1 and len(rdata) == 4:
            found.add(".".join(str(b) for b in rdata))
        elif rtype == 28 and len(rdata) == 16:
            found.add(":".join(f"{rdata[i]:02x}{rdata[i + 1]:02x}" for i in range(0, 16, 2)))
    return found, True


def _query_one(resolver: str, host: str, qtype: int, timeout: float) -> tuple[set[str], bool]:
    try:
        packet, tid = _build_query(host, qtype)
    except UnicodeError:
        return set(), False
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(timeout)
        sock.sendto(packet, (resolver, 53))
        data, _from = sock.recvfrom(4096)
    except OSError:
        return set(), False
    finally:
        sock.close()
    return _parse_response(data, tid)


def _query_fallback(host: str, timeout: float = 2.5, resolver_count: int = 6) -> tuple[set[str], int]:
    """چند resolver عمومی را مستقیماً و موازی می‌پرسد (بدون وابستگی به
    resolv.conf سیستم). برمی‌گرداند (آی‌پی‌ها, تعداد resolverهای متفاوتی
    که پاسخ معتبر داده‌اند)."""
    pool = _resolver_list()[:resolver_count]
    if not pool:
        return set(), 0
    found: set[str] = set()
    confirmed_resolvers: set[str] = set()
    with ThreadPoolExecutor(max_workers=max(len(pool) * 2, 1)) as executor:
        future_map = {}
        for resolver in pool:
            future_map[executor.submit(_query_one, resolver, host, 1, timeout)] = resolver  # A
            future_map[executor.submit(_query_one, resolver, host, 28, timeout)] = resolver  # AAAA
        for future in as_completed(future_map, timeout=timeout + 2):
            resolver = future_map[future]
            try:
                ips, ok = future.result()
            except Exception:
                continue
            if ok:
                confirmed_resolvers.add(resolver)
            found |= ips
    return found, len(confirmed_resolvers)


# برای این‌که یک resolver خراب/فیلترشده (مثلاً یک مسیر شبکه‌ای که هر پرس‌و‌جوی
# UDP:53 را با NXDOMAIN جعلی جواب می‌دهد) باعث خطای کاذب «رکورد نیست» نشود،
# فقط وقتی نتیجه را قطعی می‌دانیم که حداقل این تعداد منبعِ مستقل (resolver
# سیستم + resolverهای fallback) همگی روی «رکوردی نیست» توافق داشته باشند.
CONFIRM_QUORUM = 2


def resolve_ips(host: str) -> tuple[set[str], bool]:
    """آی‌پی‌های یک نام را برمی‌گرداند، به‌همراه این‌که نتیجه قطعی است یا نه.

    قطعی یعنی دست‌کم CONFIRM_QUORUM منبعِ مستقل پاسخ معتبر (حتی خالی/
    NXDOMAIN) داده‌اند. اگر این‌تعداد به توافق نرسیدند -- چه به‌خاطر timeout
    و چه به‌خاطر فیلترشدنِ مسیر به resolverها -- نتیجه نامعلوم است و نباید
    به‌معنای «رکورد وجود ندارد» گرفته شود.
    """
    found: set[str] = set()
    votes = 0
    try:
        infos = socket.getaddrinfo(host, None)
        votes += 1
    except socket.gaierror as exc:
        infos = []
        # EAI_NONAME/EAI_NODATA یعنی resolver سیستم واقعاً جواب داد و
        # رکوردی نیست (یک رأی قطعی). بقیه‌ی کدها (EAI_AGAIN موقت، EAI_FAIL
        # و...) یعنی خودِ resolver مشکل دارد -- این رأی حساب نمی‌شود.
        definite_codes = {
            code
            for code in (getattr(socket, "EAI_NONAME", None), getattr(socket, "EAI_NODATA", None))
            if code is not None
        }
        if exc.errno in definite_codes:
            votes += 1
    except OSError:
        infos = []
    for family, _type, _proto, _canon, sockaddr in infos:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        ip = sockaddr[0].split("%", 1)[0].lower()
        if ip:
            found.add(ip)
    if found:
        return found, True

    fallback_ips, fallback_votes = _query_fallback(host)
    if fallback_ips:
        return {ip.lower() for ip in fallback_ips}, True
    votes += fallback_votes
    return set(), votes >= CONFIRM_QUORUM


def server_addresses() -> set[str]:
    """آی‌پی‌های این ماشین، به‌اضافه آی‌پی عمومی اگر پشت NAT باشد."""
    from apps.core.access import server_ips

    found = {ip for ip in server_ips() if _valid_v4(ip)}
    for url in IP_ECHO_URLS:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                public = (response.read() or b"").decode().strip()
            if _valid_v4(public):
                found.add(public)
                break
        except Exception:
            continue
    try:
        result = subprocess.run(
            ["ip", "-6", "-o", "addr", "show", "scope", "global"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        for match in re.findall(r"inet6\s+([0-9a-f:]+)", (result.stdout or "").lower()):
            if not match.startswith("fe80") and IPV6_RE.fullmatch(match):
                found.add(match)
    except (OSError, subprocess.SubprocessError):
        pass
    return found


def points_here(host: str, addresses: set[str]) -> tuple[bool, set[str], bool]:
    """برمی‌گرداند (اشاره‌می‌کند؟, آی‌پی‌های پیدا شده, قطعی‌بودن نتیجه)."""
    resolved, confirmed = resolve_ips(host)
    if not resolved or not addresses:
        return False, resolved, confirmed
    return bool(resolved & addresses), resolved, confirmed
