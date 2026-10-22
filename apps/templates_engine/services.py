import io
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from jinja2 import FileSystemLoader, TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment

from apps.core.zipsafe import ALLOWED_TEMPLATE_EXT, ZipRejected, extract_zip, inspect_zip, locate_root
from apps.templates_engine.models import TemplatePackage

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def read_template_manifest(root: Path) -> dict:
    path = root / "template.json"
    if not path.is_file():
        raise ZipRejected("template.json در ریشه زیپ پیدا نشد. اگر زیپ یک پوشه والد دارد، فایل باید داخل همان پوشه باشد.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ZipRejected(f"template.json نامعتبر است: {exc}") from exc
    if not isinstance(data, dict):
        raise ZipRejected("template.json باید یک شیء JSON باشد.")
    for key in ("name", "slug", "pages"):
        if not data.get(key):
            raise ZipRejected(f"فیلد الزامی وجود ندارد: {key}")
    slug = str(data["slug"]).strip()
    if not SLUG_RE.fullmatch(slug):
        raise ZipRejected("slug قالب فقط حروف کوچک انگلیسی، عدد و خط تیره مجاز است.")
    pages = data["pages"]
    if not isinstance(pages, list) or not pages:
        raise ZipRejected("حداقل یک صفحه در pages لازم است.")
    seen = set()
    root_resolved = root.resolve()
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise ZipRejected(f"ساختار صفحه {index} نادرست است.")
        for key in ("slug", "title", "file"):
            if not str(page.get(key) or "").strip():
                raise ZipRejected(f"صفحه {index} فیلد {key} ندارد.")
        page_slug = str(page["slug"]).strip()
        if not SLUG_RE.fullmatch(page_slug):
            raise ZipRejected(f"slug صفحه نامعتبر است: {page_slug}")
        if page_slug in seen:
            raise ZipRejected(f"slug صفحه تکراری است: {page_slug}")
        seen.add(page_slug)
        rel = str(page["file"]).strip().replace("\\", "/")
        if rel.startswith("/") or ".." in Path(rel).parts or not rel.endswith(".html"):
            raise ZipRejected(f"مسیر صفحه نامعتبر است: {rel}")
        target = (root / rel).resolve()
        if not str(target).startswith(str(root_resolved)) or not target.is_file():
            raise ZipRejected(f"فایل صفحه پیدا نشد: {rel}")
        page["slug"] = page_slug
        page["title"] = str(page["title"])[:160]
        page["file"] = rel
        page["in_menu"] = bool(page.get("in_menu", True))
    home = str(data.get("homepage") or pages[0]["slug"])
    if home not in seen:
        raise ZipRejected("homepage باید یکی از slugهای صفحات باشد.")
    demo = data.get("demo_data", {})
    if demo is None:
        demo = {}
    if not isinstance(demo, dict):
        raise ZipRejected("demo_data باید شیء JSON باشد.")
    return {
        "name": str(data["name"])[:160],
        "slug": slug,
        "version": str(data.get("version") or "1.0.0")[:40],
        "author": str(data.get("author") or "")[:120],
        "description": str(data.get("description") or "")[:4000],
        "homepage": home,
        "pages": pages,
        "demo_data": demo,
        "engine": "jinja2",
    }


def compile_template_tree(root: Path, manifest: dict) -> None:
    env = SandboxedEnvironment(loader=FileSystemLoader(str(root)), autoescape=True)
    try:
        for page in manifest["pages"]:
            env.get_template(page["file"])
    except TemplateSyntaxError as exc:
        where = exc.filename or page.get("file") or ""
        raise ZipRejected(f"خطای نحوی قالب در {where} خط {exc.lineno}: {exc.message}") from exc


def store_template(*, raw: bytes, category, filename: str = "template.zip") -> tuple[TemplatePackage, bool]:
    if len(raw) > settings.MOHSEN_MAX_ZIP_BYTES:
        raise ZipRejected("حجم فایل زیپ بیش از حد مجاز است.")
    if len(raw) < 32 or not zipfile.is_zipfile(io.BytesIO(raw)):
        raise ZipRejected("فایل بارگذاری‌شده یک زیپ معتبر نیست.")
    media_root = Path(settings.MEDIA_ROOT)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        inspect_zip(zf, ALLOWED_TEMPLATE_EXT)
        tmp = Path(tempfile.mkdtemp(prefix="mohsen-tpl-"))
        try:
            extract_zip(zf, tmp)
            root = locate_root(tmp, "template.json")
            manifest = read_template_manifest(root)
            compile_template_tree(root, manifest)
            slug = manifest["slug"]
            final_parent = media_root / "templates"
            final_parent.mkdir(parents=True, exist_ok=True)
            staging = final_parent / f".{slug}.staging"
            final = final_parent / slug
            if staging.exists():
                shutil.rmtree(staging)
            shutil.copytree(root, staging)
            if final.exists():
                shutil.rmtree(final)
            staging.rename(final)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    existed = TemplatePackage.objects.filter(slug=manifest["slug"]).exists()
    obj, _created = TemplatePackage.objects.update_or_create(
        slug=manifest["slug"],
        defaults={
            "category": category,
            "name": manifest["name"],
            "version": manifest["version"],
            "author": manifest["author"],
            "description": manifest["description"],
            "extracted_path": str(final),
            "manifest": manifest,
            "is_active": True,
        },
    )
    safe_name = f"{manifest['slug']}-{manifest['version']}.zip"
    obj.archive.save(safe_name, ContentFile(raw), save=True)
    return obj, not existed
