import stat
import zipfile
from pathlib import Path

from django.conf import settings

ALLOWED_TEMPLATE_EXT = {
    ".html", ".css", ".js", ".json", ".svg", ".png", ".jpg", ".jpeg",
    ".webp", ".gif", ".ico", ".woff", ".woff2", ".txt", ".md", ".map", ".webmanifest",
}
ALLOWED_PLUGIN_EXT = ALLOWED_TEMPLATE_EXT | {".py"}


class ZipRejected(Exception):
    pass


def _is_ignored(name: str) -> bool:
    parts = Path(name).parts
    if not parts:
        return True
    if parts[0] == "__MACOSX" or name.startswith("__MACOSX/"):
        return True
    if Path(name).name in {".DS_Store", "Thumbs.db"}:
        return True
    return False


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return bool(mode and stat.S_ISLNK(mode))


def inspect_zip(zf: zipfile.ZipFile, allowed_ext: set[str]) -> list[str]:
    bad = zf.testzip()
    if bad is not None:
        raise ZipRejected(f"فایل زیپ خراب است: {bad}")
    total = 0
    names = []
    for info in zf.infolist():
        name = info.filename.replace("\\", "/").lstrip("/")
        if _is_ignored(name):
            continue
        parts = Path(name).parts
        if ".." in parts or name.startswith("/"):
            raise ZipRejected("مسیر ناامن داخل زیپ رد شد.")
        if _is_symlink(info):
            raise ZipRejected("لینک نمادین داخل زیپ مجاز نیست.")
        total += info.file_size
        if info.file_size > settings.MOHSEN_MAX_UNCOMPRESSED or total > settings.MOHSEN_MAX_UNCOMPRESSED:
            raise ZipRejected("حجم غیرفشرده زیپ بیش از حد مجاز است.")
        if info.is_dir():
            continue
        ext = Path(name).suffix.lower()
        if ext not in allowed_ext:
            raise ZipRejected(f"پسوند مجاز نیست: {name}")
        names.append(name)
    if not names:
        raise ZipRejected("زیپ هیچ فایل مجازی ندارد.")
    if len(names) > 2000:
        raise ZipRejected("تعداد فایل‌های زیپ بیش از حد است.")
    return names


def extract_zip(zf: zipfile.ZipFile, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()
    for info in zf.infolist():
        name = info.filename.replace("\\", "/").lstrip("/")
        if _is_ignored(name) or info.is_dir():
            continue
        target = (dest / name).resolve()
        if not str(target).startswith(str(dest_resolved)):
            raise ZipRejected("مسیر ناامن هنگام استخراج.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info, "r") as src, open(target, "wb") as out:
            remaining = info.file_size
            while True:
                chunk = src.read(1024 * 256)
                if not chunk:
                    break
                remaining -= len(chunk)
                if remaining < -1024:
                    raise ZipRejected("اندازه فایل با هدر زیپ نمی‌خواند.")
                out.write(chunk)


def locate_root(dest: Path, marker: str) -> Path:
    if (dest / marker).is_file():
        return dest
    children = [p for p in dest.iterdir() if p.name != "__MACOSX"]
    dirs = [p for p in children if p.is_dir()]
    files = [p for p in children if p.is_file() and p.name != ".DS_Store"]
    if len(dirs) == 1 and not files and (dirs[0] / marker).is_file():
        return dirs[0]
    return dest
