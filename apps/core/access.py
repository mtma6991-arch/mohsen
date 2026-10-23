import os
import re
import socket
import subprocess
from pathlib import Path

CRED_PATH = Path("/root/mohsen-credentials.txt")
IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
USER_RE = re.compile(r"(?:نام کاربری|USERNAME)\s*[:=]\s*(\S+)", re.IGNORECASE)
PASS_RE = re.compile(r"(?:رمز عبور|PASSWORD)\s*[:=]\s*(\S+)", re.IGNORECASE)


def _valid_public_ip(value: str) -> bool:
    if not IPV4_RE.fullmatch(value or ""):
        return False
    parts = [int(part) for part in value.split(".")]
    if any(part > 255 for part in parts):
        return False
    if value.startswith("127.") or value == "0.0.0.0" or value.startswith("169.254."):
        return False
    return True


def server_ips() -> list[str]:
    found: list[str] = []

    def add(raw: str) -> None:
        for token in re.split(r"[\s,]+", raw or ""):
            token = token.strip().split("%", 1)[0]
            if _valid_public_ip(token) and token not in found:
                found.append(token)

    try:
        result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=3)
        add(result.stdout or "")
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        result = subprocess.run(["ip", "-4", "-o", "addr", "show", "scope", "global"], capture_output=True, text=True, timeout=3)
        add(" ".join(re.findall(r"inet\s+(\d+\.\d+\.\d+\.\d+)", result.stdout or "")))
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        sock.connect(("8.8.8.8", 80))
        add(sock.getsockname()[0])
        sock.close()
    except OSError:
        pass
    return found


def build_login_urls(ips, port, web_pass, domains) -> list[str]:
    """آدرس‌هایی که واقعاً در نوار مرورگر باز می‌شوند. میزبان ساختگی برنمی‌گرداند."""
    port = str(port or "8787").strip()
    web_pass = str(web_pass or "").strip().strip("/")
    if not web_pass or not port.isdigit():
        return []
    urls: list[str] = []
    seen = set()

    def push(url: str) -> None:
        if not url or url in seen:
            return
        if any(token in url for token in ("SERVER", "IP-SERVER", "SERVER_IP", "example.invalid")):
            return
        seen.add(url)
        urls.append(url)

    for ip in ips or []:
        if not _valid_public_ip(str(ip)):
            continue
        push(f"http://{ip}:{port}/{web_pass}/")
        push(f"http://{ip}/{web_pass}/")
    for row in domains or []:
        if isinstance(row, dict):
            domain = str(row.get("domain") or "").strip().strip(".")
            https = bool(row.get("https"))
        else:
            domain = str(getattr(row, "domain", "") or "").strip().strip(".")
            https = bool(getattr(row, "https", False))
        if not domain or " " in domain or domain.upper() in {"SERVER", "SERVER_IP", "IP-SERVER"}:
            continue
        if https:
            push(f"https://{domain}/{web_pass}/")
        else:
            push(f"http://{domain}/{web_pass}/")
            if port not in {"80", "443"}:
                push(f"http://{domain}:{port}/{web_pass}/")
    return urls


def read_credentials() -> dict:
    username = os.environ.get("MOHSEN_ADMIN_USER", "").strip() or "admin"
    password = ""
    path = CRED_PATH if CRED_PATH.is_file() else None
    if path is not None:
        text = path.read_text(encoding="utf-8", errors="replace")
        user_match = USER_RE.search(text)
        pass_match = PASS_RE.search(text)
        if user_match:
            username = user_match.group(1)
        if pass_match:
            password = pass_match.group(1)
    return {"username": username, "password": password, "path": path}


def login_snapshot() -> dict:
    from django.conf import settings

    from apps.core.models import AdminDomain

    domains = []
    try:
        domains = list(AdminDomain.objects.all())
    except Exception:
        domains = []
    urls = build_login_urls(server_ips(), settings.PANEL_PORT, settings.WEB_PASS, domains)
    creds = read_credentials()
    return {
        "urls": urls,
        "username": creds["username"],
        "password": creds["password"],
        "credentials_path": creds["path"],
        "port": str(settings.PANEL_PORT),
        "web_pass": settings.WEB_PASS,
    }


def write_credentials(username: str, password: str, urls: list[str]) -> None:
    if not username or not password:
        return
    lines = [
        "محسن — مشخصات ورود",
        "این آدرس را عیناً در نوار مرورگر وارد کنید:",
    ]
    for index, url in enumerate(urls, start=1):
        lines.append(f"LOGIN_URL_{index}={url}")
    lines.append(f"USERNAME={username}")
    lines.append(f"PASSWORD={password}")
    lines.append(f"نام کاربری: {username}")
    lines.append(f"رمز عبور: {password}")
    lines.append("دستور مدیریت: sudo mohsen")
    lines.append("به‌روزرسانی از گیت‌هاب: sudo mohsen update")
    lines.append("حذف کامل: sudo mohsen uninstall --yes")
    try:
        CRED_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.chmod(CRED_PATH, 0o600)
    except OSError:
        return


def sync_credentials(password: str | None = None, username: str | None = None) -> None:
    current = read_credentials()
    user = username or current["username"]
    secret = password if password is not None else current["password"]
    if not secret:
        return
    snap = login_snapshot()
    write_credentials(user, secret, snap["urls"])
