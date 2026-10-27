import re
import socket
import subprocess
import urllib.request

IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
IPV6_RE = re.compile(r"^[0-9a-f:]+$")


def _valid_v4(value: str) -> bool:
    if not IPV4_RE.fullmatch(value or ""):
        return False
    parts = [int(part) for part in value.split(".")]
    if any(part > 255 for part in parts):
        return False
    if value.startswith("127.") or value == "0.0.0.0" or value.startswith("169.254."):
        return False
    return True


def resolve_ips(host: str) -> set[str]:
    found: set[str] = set()
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return found
    for family, _type, _proto, _canon, sockaddr in infos:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        ip = sockaddr[0].split("%", 1)[0].lower()
        if ip:
            found.add(ip)
    return found


def server_addresses() -> set[str]:
    """آی‌پی‌های این ماشین، به‌اضافه آی‌پی عمومی اگر پشت NAT باشد."""
    from apps.core.access import server_ips

    found = {ip for ip in server_ips() if _valid_v4(ip)}
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=3) as response:
            public = (response.read() or b"").decode().strip()
        if _valid_v4(public):
            found.add(public)
    except Exception:
        pass
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


def points_here(host: str, addresses: set[str]) -> tuple[bool, set[str]]:
    resolved = resolve_ips(host)
    if not resolved or not addresses:
        return False, resolved
    return bool(resolved & addresses), resolved
