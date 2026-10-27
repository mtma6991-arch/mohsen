import re

HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9-]{2,63}$"
)
LOCAL_RE = re.compile(r"^(?:localhost|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+local)$")
IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
_INVISIBLE_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]")
_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_domain(value: str) -> str:
    raw = _INVISIBLE_RE.sub("", (value or "")).translate(_DIGIT_MAP).strip().lower()
    raw = re.sub(r"^[a-z][a-z0-9+.-]*://", "", raw, flags=re.IGNORECASE)
    raw = raw.split("/")[0].split("?")[0].split("#")[0].strip()
    if raw.startswith("["):
        raise ValueError("IPv6 به‌عنوان دامنه سایت پشتیبانی نمی‌شود.")
    if ":" in raw:
        raw = raw.split(":", 1)[0]
    raw = raw.strip(".")
    if raw and not raw.isascii():
        try:
            raw = ".".join(
                label.encode("idna").decode("ascii") if label else ""
                for label in raw.split(".")
            )
        except UnicodeError as exc:
            raise ValueError("دامنه شامل نویسه‌های نامعتبر است.") from exc
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
    if not domain or " " in domain or ".." in domain:
        raise ValueError("دامنه خالی یا نامعتبر است.")
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
