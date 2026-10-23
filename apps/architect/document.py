import json
import re
from pathlib import Path

from apps.architect.catalog import BY_ID
from apps.core.zipsafe import ZipRejected

BUILDER = "memar"
UID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PAIR_RE = re.compile(
    r"""data-memar-id\s*=\s*["']([a-z0-9-]+)["'][^>]*data-memar-uid\s*=\s*["']([a-z0-9-]+)["']"""
    r"""|data-memar-uid\s*=\s*["']([a-z0-9-]+)["'][^>]*data-memar-id\s*=\s*["']([a-z0-9-]+)["']""",
    re.IGNORECASE,
)
MEMAR_CALL_RE = re.compile(r"""memar\(\s*['"]([a-z0-9-]+)['"]""")
RESERVED_PAGES = {"layout"}


def validate_architect(root: Path, page_slugs: list[str], page_files: dict[str, str]) -> dict:
    path = root / "architect.json"
    if not path.is_file():
        raise ZipRejected(
            "architect.json در ریشه قالب نیست. هر قالب باید بر اساس صفحه‌ساز معمار باشد. راهنمای زیپ قالب را ببینید."
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ZipRejected(f"architect.json نامعتبر است: {exc}") from exc
    if not isinstance(raw, dict):
        raise ZipRejected("architect.json باید یک شیء JSON باشد.")
    if str(raw.get("builder") or "") != BUILDER:
        raise ZipRejected('فیلد builder در architect.json باید دقیقاً "memar" باشد.')
    version = str(raw.get("version") or "").strip()
    if not version:
        raise ZipRejected("فیلد version در architect.json الزامی است.")
    nodes = raw.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ZipRejected("architect.json باید آرایه nodes با حداقل یک المان داشته باشد.")

    allowed_pages = set(page_slugs) | {"layout"}
    normalized = []
    seen = set()
    for index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            raise ZipRejected(f"المان {index} در architect.json شیء نیست.")
        uid = str(node.get("uid") or "").strip()
        element_id = str(node.get("id") or "").strip()
        page = str(node.get("page") or "").strip()
        parent = str(node.get("parent") or "").strip()
        if not UID_RE.fullmatch(uid):
            raise ZipRejected(f"uid نامعتبر است: {uid or index}. فقط حروف کوچک، عدد و خط تیره.")
        if uid in seen:
            raise ZipRejected(f"uid تکراری است: {uid}")
        seen.add(uid)
        if element_id not in BY_ID:
            raise ZipRejected(
                f"شناسه المان معمار ناشناخته است: {element_id or '—'}. فقط ۵۰ شناسه کاتالوگ معمار مجاز است."
            )
        if page not in allowed_pages:
            raise ZipRejected(f"صفحه المان {uid} ناشناخته است: {page}. از slug صفحات یا layout استفاده کنید.")
        settings = node.get("settings") or {}
        if settings is None:
            settings = {}
        if not isinstance(settings, dict):
            raise ZipRejected(f"settings المان {uid} باید شیء باشد.")
        known_keys = {item["key"] for item in BY_ID[element_id]["settings"]}
        unknown = [key for key in settings if key not in known_keys]
        if unknown:
            raise ZipRejected(f"تنظیم ناشناخته برای {element_id}/{uid}: {', '.join(unknown)}")
        clean_settings = {}
        for key, value in settings.items():
            if value is None:
                continue
            clean_settings[key] = str(value)[:4000]
        normalized.append(
            {
                "uid": uid,
                "id": element_id,
                "page": page,
                "parent": parent,
                "settings": clean_settings,
            }
        )

    by_uid = {item["uid"]: item for item in normalized}
    for item in normalized:
        parent = item["parent"]
        if not parent:
            continue
        holder = by_uid.get(parent)
        if holder is None:
            raise ZipRejected(f"والد {parent} برای {item['uid']} در architect.json نیست.")
        if holder["page"] != item["page"]:
            raise ZipRejected(f"المان {item['uid']} و والدش {parent} باید در یک صفحه باشند.")
        if not BY_ID[holder["id"]]["accepts_children"]:
            raise ZipRejected(f"المان {holder['id']} ({parent}) فرزند نمی‌پذیرد.")

    file_pages = _html_pages(root, page_files)
    found = {}
    for page_key, files in file_pages.items():
        for rel, text in files:
            singles = text.count("data-memar-id") + text.count("data-memar-uid")
            pairs = list(PAIR_RE.finditer(text))
            paired_attrs = len(pairs) * 2
            if singles != paired_attrs:
                raise ZipRejected(
                    f"در {rel} هر data-memar-id باید کنار data-memar-uid در همان برچسب باشد."
                )
            for match in pairs:
                if match.group(1):
                    element_id, uid = match.group(1), match.group(2)
                else:
                    uid, element_id = match.group(3), match.group(4)
                node = by_uid.get(uid)
                if node is None:
                    raise ZipRejected(f"uid در HTML هست ولی در architect.json نیست: {uid} ({rel})")
                if node["id"] != element_id:
                    raise ZipRejected(
                        f"شناسه معمار {uid} در HTML برابر {element_id} است ولی در architect.json برابر {node['id']} است."
                    )
                if node["page"] != page_key:
                    raise ZipRejected(f"المان {uid} در فایل صفحه {page_key} است ولی در سند صفحه {node['page']} ثبت شده.")
                found.setdefault(uid, rel)
            for uid in MEMAR_CALL_RE.findall(text):
                if uid not in by_uid:
                    raise ZipRejected(f"فراخوانی memar('{uid}') در {rel} معادلی در architect.json ندارد.")

    missing = [item["uid"] for item in normalized if item["uid"] not in found]
    if missing:
        raise ZipRejected("این uidها در architect.json هستند ولی در HTML با data-memar-uid نیامده‌اند: " + ", ".join(missing))

    pages_with_nodes = {item["page"] for item in normalized}
    for slug in page_slugs:
        if slug in RESERVED_PAGES:
            raise ZipRejected("slug صفحه نباید layout باشد؛ layout برای اسکلت قالب رزرو شده است.")
        if slug not in pages_with_nodes:
            raise ZipRejected(f"صفحه {slug} هیچ المان معمار ندارد.")
        page_file = page_files.get(slug)
        if page_file:
            blob = ""
            for rel, text in file_pages.get(slug, []):
                blob += text
            if "data-memar-uid" not in blob:
                raise ZipRejected(f"فایل صفحه {slug} نشانه‌گذاری معمار ندارد.")

    return {"builder": BUILDER, "version": version, "nodes": normalized}


def load_architect(root: Path) -> dict:
    path = Path(root) / "architect.json"
    if not path.is_file():
        return {"builder": BUILDER, "version": "", "nodes": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"builder": BUILDER, "version": "", "nodes": []}
    if not isinstance(data, dict):
        return {"builder": BUILDER, "version": "", "nodes": []}
    nodes = data.get("nodes") if isinstance(data.get("nodes"), list) else []
    return {"builder": str(data.get("builder") or ""), "version": str(data.get("version") or ""), "nodes": nodes}


def _html_pages(root: Path, page_files: dict[str, str]) -> dict[str, list[tuple[str, str]]]:
    by_file = {str(path).replace("\\", "/"): slug for slug, path in page_files.items()}
    grouped: dict[str, list[tuple[str, str]]] = {}
    for path in sorted(root.rglob("*.html")):
        rel = path.relative_to(root).as_posix()
        if rel.startswith("layout/"):
            page_key = "layout"
        elif rel in by_file:
            page_key = by_file[rel]
        else:
            page_key = rel
        text = path.read_text(encoding="utf-8")
        grouped.setdefault(page_key, []).append((rel, text))
    return grouped
