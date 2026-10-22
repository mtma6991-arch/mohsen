import io
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile

from apps.core.zipsafe import ALLOWED_PLUGIN_EXT, ZipRejected, extract_zip, inspect_zip, locate_root
from apps.plugins.loader import load_plugin_class
from apps.plugins.models import PluginPackage

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def read_plugin_manifest(root: Path) -> dict:
    path = root / "plugin.json"
    if not path.is_file():
        raise ZipRejected("plugin.json در ریشه زیپ افزونه پیدا نشد.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ZipRejected(f"plugin.json نامعتبر است: {exc}") from exc
    if not isinstance(data, dict):
        raise ZipRejected("plugin.json باید شیء JSON باشد.")
    for key in ("name", "slug"):
        if not str(data.get(key) or "").strip():
            raise ZipRejected(f"فیلد الزامی وجود ندارد: {key}")
    slug = str(data["slug"]).strip()
    if not SLUG_RE.fullmatch(slug):
        raise ZipRejected("slug افزونه فقط حروف کوچک انگلیسی، عدد و خط تیره.")
    entry = str(data.get("entry") or "plugin.py").strip().replace("\\", "/")
    if entry.startswith("/") or ".." in Path(entry).parts or not entry.endswith(".py"):
        raise ZipRejected("entry افزونه باید یک فایل py نسبی باشد.")
    if not (root / entry).is_file():
        raise ZipRejected(f"فایل ورود پیدا نشد: {entry}")
    hooks = data.get("hooks") or []
    if not isinstance(hooks, list):
        raise ZipRejected("hooks باید آرایه باشد.")
    return {
        "name": str(data["name"])[:160],
        "slug": slug,
        "version": str(data.get("version") or "1.0.0")[:40],
        "author": str(data.get("author") or "")[:120],
        "description": str(data.get("description") or "")[:4000],
        "entry": entry,
        "class": str(data.get("class") or "Plugin")[:80],
        "hooks": [str(h)[:80] for h in hooks],
    }


def store_plugin(*, raw: bytes, filename: str = "plugin.zip") -> tuple[PluginPackage, bool]:
    if len(raw) > settings.MOHSEN_MAX_ZIP_BYTES:
        raise ZipRejected("حجم فایل زیپ بیش از حد مجاز است.")
    if len(raw) < 32 or not zipfile.is_zipfile(io.BytesIO(raw)):
        raise ZipRejected("فایل بارگذاری‌شده یک زیپ معتبر نیست.")
    media_root = Path(settings.MEDIA_ROOT)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        inspect_zip(zf, ALLOWED_PLUGIN_EXT)
        tmp = Path(tempfile.mkdtemp(prefix="mohsen-plug-"))
        try:
            extract_zip(zf, tmp)
            root = locate_root(tmp, "plugin.json")
            manifest = read_plugin_manifest(root)
            load_plugin_class(root, manifest)
            slug = manifest["slug"]
            final_parent = media_root / "plugins"
            final_parent.mkdir(parents=True, exist_ok=True)
            staging = final_parent / f".{slug}.staging"
            final = final_parent / slug
            if staging.exists():
                shutil.rmtree(staging)
            shutil.copytree(root, staging)
            if final.exists():
                shutil.rmtree(final)
            staging.rename(final)
        except ZipRejected:
            raise
        except Exception as exc:
            raise ZipRejected(f"افزونه قابل بارگذاری نیست: {exc}") from exc
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    existed = PluginPackage.objects.filter(slug=manifest["slug"]).exists()
    obj, _created = PluginPackage.objects.update_or_create(
        slug=manifest["slug"],
        defaults={
            "name": manifest["name"],
            "version": manifest["version"],
            "author": manifest["author"],
            "description": manifest["description"],
            "extracted_path": str(final),
            "manifest": manifest,
            "is_active": True,
        },
    )
    obj.archive.save(f"{manifest['slug']}-{manifest['version']}.zip", ContentFile(raw), save=True)
    return obj, not existed
