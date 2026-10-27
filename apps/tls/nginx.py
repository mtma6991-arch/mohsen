import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings


def ssl_dir() -> Path:
    return Path(getattr(settings, "TLS_SSL_DIR", "/etc/mohsen/ssl"))


def nginx_group() -> str:
    import grp

    for name in ("www-data", "nginx"):
        try:
            grp.getgrnam(name)
            return name
        except KeyError:
            continue
    return "root"


def secure_tree(path: Path) -> None:
    """Workerهای nginx با گواهی متغیر باید خود فایل را بخوانند."""
    import grp

    group = nginx_group()
    try:
        gid = grp.getgrnam(group).gr_gid
    except KeyError:
        gid = 0
    if not path.exists():
        return
    for root, dirs, files in os.walk(path):
        os.chown(root, 0, gid)
        os.chmod(root, 0o750)
        for name in dirs:
            child = Path(root) / name
            os.chown(child, 0, gid)
            os.chmod(child, 0o750)
        for name in files:
            file_path = Path(root) / name
            os.chown(file_path, 0, gid)
            os.chmod(file_path, 0o640)


def installed_certs() -> list[tuple[list[str], Path, Path]]:
    root = ssl_dir()
    found = []
    if not root.is_dir():
        return found
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith(("_", ".")):
            continue
        fullchain = child / "fullchain.pem"
        key = child / "privkey.pem"
        if not (fullchain.is_file() and key.is_file()):
            continue
        names = [child.name]
        names_file = child / "names.txt"
        if names_file.is_file():
            parsed = []
            for line in names_file.read_text(encoding="utf-8").splitlines():
                item = line.strip().lower()
                if item and item not in parsed:
                    parsed.append(item)
            if parsed:
                names = parsed
        found.append((names, fullchain.resolve(), key.resolve()))
    return found


def _render(found) -> tuple[str, str, str]:
    cert_lines = []
    key_lines = []
    redirect_lines = []
    seen = set()
    for names, fullchain, key in found:
        for name in names:
            if name in seen:
                continue
            seen.add(name)
            cert_lines.append(f"{name} {fullchain};")
            key_lines.append(f"{name} {key};")
            redirect_lines.append(f"{name} 1;")
    return (
        "\n".join(cert_lines) + ("\n" if cert_lines else ""),
        "\n".join(key_lines) + ("\n" if key_lines else ""),
        "\n".join(redirect_lines) + ("\n" if redirect_lines else ""),
    )


def _nginx_test() -> tuple[bool, str]:
    try:
        result = subprocess.run(["nginx", "-t"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    output = "\n".join(part for part in (result.stderr, result.stdout) if part).strip()
    return result.returncode == 0, output


def _nginx_reload() -> None:
    if shutil.which("systemctl"):
        subprocess.run(["systemctl", "reload", "nginx"], check=False, timeout=30)
        return
    subprocess.run(["nginx", "-s", "reload"], check=False, timeout=30)


def apply_maps() -> tuple[bool, str]:
    root = ssl_dir()
    root.mkdir(parents=True, exist_ok=True)
    cert_map, key_map, redirect_map = _render(installed_certs())
    targets = {
        "cert.map": cert_map,
        "key.map": key_map,
        "redirect.map": redirect_map,
    }
    backups = {}
    for name in targets:
        path = root / name
        backups[name] = path.read_text(encoding="utf-8") if path.is_file() else ""
        path.write_text(targets[name], encoding="utf-8")
        os.chmod(path, 0o644)
    ok, output = _nginx_test()
    if not ok:
        for name, content in backups.items():
            (root / name).write_text(content, encoding="utf-8")
        _nginx_test()
        return False, output or "nginx -t ناموفق بود. نقشه گواهی برگردانده شد."
    try:
        _nginx_reload()
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    return True, ""
