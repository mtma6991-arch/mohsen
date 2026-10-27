import subprocess
from pathlib import Path

from django.conf import settings


class AcmeError(RuntimeError):
    def __init__(self, message: str, output: str = ""):
        super().__init__(message)
        self.output = output


def acme_home() -> Path:
    return Path(getattr(settings, "TLS_ACME_HOME", "/root/.acme.sh"))


def acme_bin() -> Path:
    return acme_home() / "acme.sh"


def _run(args: list[str], timeout: int) -> subprocess.CompletedProcess:
    binary = acme_bin()
    if not binary.is_file():
        raise AcmeError(
            "acme.sh نصب نیست. روی سرور sudo bash install.sh را دوباره اجرا کنید تا از get.acme.sh نصب شود."
        )
    cmd = [str(binary), "--home", str(acme_home()), *args]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise AcmeError("acme.sh بیش از حد طول کشید.", output=str(exc)) from exc
    except OSError as exc:
        raise AcmeError(f"اجرای acme.sh ممکن نشد: {exc}") from exc


def combined_output(result: subprocess.CompletedProcess) -> str:
    text = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return text.strip()


def issue(domains: list[str], webroot: Path, email: str, *, force: bool = False) -> subprocess.CompletedProcess:
    server = getattr(settings, "TLS_ACME_SERVER", "letsencrypt") or "letsencrypt"
    args = [
        "--issue",
        "--server",
        server,
        "--webroot",
        str(webroot),
        "--keylength",
        "2048",
        "--accountemail",
        email,
        "--dnssleep",
        "0",
    ]
    for domain in domains:
        args.extend(["-d", domain])
    if force:
        args.append("--force")
    return _run(args, timeout=240)


def install_cert(primary: str, dest: Path) -> subprocess.CompletedProcess:
    dest.mkdir(parents=True, exist_ok=True)
    args = [
        "--install-cert",
        "-d",
        primary,
        "--cert-file",
        str(dest / "cert.pem"),
        "--key-file",
        str(dest / "privkey.pem"),
        "--fullchain-file",
        str(dest / "fullchain.pem"),
        "--ca-file",
        str(dest / "chain.pem"),
    ]
    return _run(args, timeout=60)


def remove(primary: str) -> subprocess.CompletedProcess:
    return _run(["--remove", "-d", primary], timeout=60)


def cron() -> subprocess.CompletedProcess:
    return _run(["--cron"], timeout=600)
