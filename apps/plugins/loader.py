import importlib.util
import logging
from pathlib import Path

from mohsen_sdk.plugin_base import BasePlugin

logger = logging.getLogger(__name__)
_CLASS_CACHE = {}


def load_plugin_class(root: Path, manifest: dict):
    slug = manifest["slug"]
    entry = str(manifest.get("entry") or "plugin.py").replace("\\", "/")
    if entry.startswith("/") or ".." in Path(entry).parts:
        raise ImportError("مسیر ورود افزونه نامعتبر است.")
    entry_path = (root / entry).resolve()
    if not str(entry_path).startswith(str(root.resolve())) or not entry_path.is_file():
        raise ImportError("فایل ورود افزونه پیدا نشد.")
    class_name = manifest.get("class") or "Plugin"
    module_name = f"mohsen_loaded_{slug}"
    spec = importlib.util.spec_from_file_location(module_name, entry_path)
    if spec is None or spec.loader is None:
        raise ImportError("بارگذاری ماژول افزونه ممکن نیست.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, class_name, None)
    if cls is None or not isinstance(cls, type) or not issubclass(cls, BasePlugin):
        raise ImportError(f"کلاس {class_name} باید از BasePlugin ارث ببرد.")
    return cls


def get_plugin_instance(package):
    root = Path(package.extracted_path)
    if not root.is_dir():
        raise ImportError("پوشه افزونه روی دیسک نیست.")
    stamp = int(root.stat().st_mtime)
    key = (package.slug, package.version, stamp)
    cls = _CLASS_CACHE.get(key)
    if cls is None:
        cls = load_plugin_class(root, package.manifest or {})
        _CLASS_CACHE.clear()
        _CLASS_CACHE[key] = cls
    instance = cls()
    instance.slug = instance.slug or package.slug
    instance.name = instance.name or package.name
    return instance


def iter_site_plugins(website):
    from apps.plugins.models import CategoryPlugin

    rows = (
        CategoryPlugin.objects.filter(
            category=website.category,
            enabled=True,
            plugin__is_active=True,
        )
        .select_related("plugin")
    )
    for row in rows:
        try:
            yield row, get_plugin_instance(row.plugin)
        except Exception:
            logger.exception("plugin load failed: %s", row.plugin.slug)
