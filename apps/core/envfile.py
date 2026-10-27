from pathlib import Path


def env_paths():
    paths = [
        Path("/etc/mohsen/mohsen.env"),
        Path("/opt/mohsen/mohsen.env"),
        Path(__file__).resolve().parents[2] / "mohsen.env",
    ]
    return [p for p in paths if p.is_file()]


def parse_env(path: Path) -> dict:
    data = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def load_env_into_os():
    import os

    for path in env_paths():
        for key, value in parse_env(path).items():
            os.environ.setdefault(key, value)
        return path
    return None


def write_env(path: Path, data: dict) -> None:
    lines = [f"{key}={value}" for key, value in data.items()]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        path.chmod(0o640)
    except OSError:
        pass


def update_keys(changes: dict) -> list[str]:
    updated = []
    paths = env_paths()
    if not paths:
        raise FileNotFoundError("هیچ فایل mohsen.env پیدا نشد.")
    for path in paths:
        data = parse_env(path)
        data.update(changes)
        write_env(path, data)
        updated.append(str(path))
    return updated
