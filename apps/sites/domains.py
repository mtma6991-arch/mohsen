import re

HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}$"
)
LOCAL_RE = re.compile(r"^(?:localhost|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+local)$")
IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")


def normalize_domain(value: str) -> str:
    raw = (value or "").strip().lower()
    raw = re.sub(r"^[a-z][a-z0-9+.-]*://", "", raw)
    raw = raw.split("/")[0].split("?")[0].split("#")[0]
    if raw.startswith("["):
        raise ValueError("IPv6 به‌عنوان دامنه سایت پشتیبانی نمی‌شود.")
    if ":" in raw:
        raw = raw.split(":", 1)[0]
    raw = raw.strip(".")
    if raw.startswith("www.") and raw.count(".") >= 2:
        # Keep the value the operator typed, including www, after basic cleanup only.
        pass
    return raw


def validate_customer_domain(value: str) -> str:
    domain = normalize_domain(value)
    if not domain or " " in domain or ".." in domain:
        raise ValueError("دامنه نامعتبر است.")
    if IPV4_RE.fullmatch(domain):
        raise ValueError("برای سایت مشتری یک نام دامنه وارد کنید، نه آی‌پی.")
    if not (HOST_RE.fullmatch(domain) or LOCAL_RE.fullmatch(domain)):
        raise ValueError("دامنه باید شبیه example.com یا shop.example.com باشد.")
    return domain


def validate_admin_domain(value: str) -> str:
    domain = normalize_domain(value)
    if not domain:
        raise ValueError("دامنه خالی است.")
    if IPV4_RE.fullmatch(domain) or domain == "localhost" or HOST_RE.fullmatch(domain) or LOCAL_RE.fullmatch(domain):
        return domain
    raise ValueError("دامنه پنل نامعتبر است.")


def host_lookup_variants(host: str) -> list[str]:
    host = (host or "").split(":")[0].strip().lower().strip(".")
    if not host:
        return []
    variants = [host]
    if host.startswith("www."):
        variants.append(host[4:])
    else:
        variants.append("www." + host)
    seen = []
    for item in variants:
        if item and item not in seen:
            seen.append(item)
    return seen
