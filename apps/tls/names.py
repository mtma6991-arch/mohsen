import re

IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}$"
)
_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://")


def clean_domain(value: str) -> str:
    raw = (value or "").strip().lower()
    raw = _SCHEME_RE.sub("", raw)
    raw = raw.split("/")[0].split("?")[0].split("#")[0]
    if raw.startswith("["):
        return raw
    if ":" in raw:
        raw = raw.split(":", 1)[0]
    return raw.strip(".")


def is_ip(value: str) -> bool:
    if not IPV4_RE.fullmatch(value or ""):
        return False
    return all(int(part) <= 255 for part in value.split("."))


def is_public_dns_name(value: str) -> bool:
    """نامی که Let's Encrypt با HTTP-01 می‌تواند برایش گواهی بدهد."""
    if not value or is_ip(value) or value in {"localhost", "localhost.localdomain"}:
        return False
    if value.endswith((".local", ".localhost", ".invalid", ".test", ".example", ".lan")):
        return False
    if ".." in value or value.startswith("-") or value.endswith("-"):
        return False
    return bool(DOMAIN_RE.fullmatch(value))


def partner_name(domain: str) -> str:
    if domain.startswith("www."):
        return domain[4:]
    return "www." + domain
