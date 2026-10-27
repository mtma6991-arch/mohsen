"""صدور خودکار TLS با acme.sh، همان الگوی CyberPanel: وب‌روت HTTP-01، نقشه SNI و تمدید."""

import fcntl
import os
import re
import shutil
import subprocess
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.tls import acme
from apps.tls.acme import AcmeError
from apps.tls.dns import points_here, server_addresses
from apps.tls.names import clean_domain, is_ip, is_public_dns_name, partner_name
from apps.tls.nginx import apply_maps, secure_tree, ssl_dir

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
LOCK_PATH = Path("/var/lock/mohsen-tls.lock")
CRON_STAMP = Path("/var/lib/mohsen/tls-acme-cron")
LOG_PATH = Path("/var/log/mohsen/tls.log")


def _log(text: str) -> None:
    line = text.rstrip()
    if not line:
        return
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def _tail(text: str, limit: int = 1500) -> str:
    clean = ANSI_RE.sub("", text or "").strip()
    if len(clean) <= limit:
        return clean
    return clean[-limit:]


@contextmanager
def _lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK_PATH.open("a", encoding="utf-8")
    fcntl.flock(handle, fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


def _restore_db_owner() -> None:
    if os.geteuid() != 0:
        return
    engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    if "sqlite" not in engine:
        return
    import pwd

    try:
        user = pwd.getpwnam("mohsen")
    except KeyError:
        return
    data = Path(settings.DATA_DIR)
    for name in ("db.sqlite3", "db.sqlite3-wal", "db.sqlite3-shm"):
        path = data / name
        if path.exists():
            try:
                os.chown(path, user.pw_uid, user.pw_gid)
            except OSError:
                pass


def _email_for(domain: str) -> str:
    configured = (getattr(settings, "TLS_EMAIL", "") or os.environ.get("MOHSEN_ACME_EMAIL", "")).strip()
    if configured and "@" in configured and " " not in configured:
        return configured
    return f"admin@{domain}"


def _cert_datetime(path: Path, flag: str) -> datetime | None:
    if not path.is_file() or not shutil.which("openssl"):
        return None
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", str(path), "-noout", flag],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    raw = (result.stdout or "").strip().split("=", 1)[-1].strip().replace(" GMT", "")
    if result.returncode != 0 or not raw:
        return None
    try:
        parsed = datetime.strptime(raw, "%b %d %H:%M:%S %Y")
    except ValueError:
        return None
    return timezone.make_aware(parsed, dt_timezone.utc)


def cert_paths(domain: str) -> Path:
    return ssl_dir() / domain


def _fullchain(domain: str) -> Path:
    return cert_paths(domain) / "fullchain.pem"


def _write_names(domain: str, names: list[str]) -> None:
    dest = cert_paths(domain)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "names.txt").write_text("\n".join(names) + "\n", encoding="utf-8")


def _mark(cert, **fields):
    for key, value in fields.items():
        setattr(cert, key, value)
    cert.save()


def _sync_https_flag(domain: str, enabled: bool) -> None:
    from apps.core.access import sync_credentials
    from apps.core.models import AdminDomain

    updated = AdminDomain.objects.filter(domain=domain, https=not enabled).update(https=enabled)
    if not updated:
        return
    try:
        sync_credentials()
    except Exception as exc:
        _log(f"credentials: {exc}")


def _webroot() -> Path:
    path = Path(getattr(settings, "TLS_WEBROOT", "/var/lib/mohsen-acme"))
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o755)
    except OSError:
        pass
    return path


def _challenge_reachable(domain: str) -> tuple[bool, str]:
    import secrets
    import urllib.request

    token = "mohsen-" + secrets.token_hex(8)
    directory = _webroot() / ".well-known" / "acme-challenge"
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / token
    file_path.write_text(token, encoding="utf-8")
    try:
        os.chmod(file_path, 0o644)
    except OSError:
        pass
    request = urllib.request.Request(
        f"http://127.0.0.1/.well-known/acme-challenge/{token}",
        headers={"Host": domain},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read().decode("utf-8", errors="replace").strip()
        if token not in body:
            return False, "nginx فایل چالش ACME را برنگرداند. پیکربندی nginx محسن را دوباره نصب کنید."
        return True, ""
    except Exception as exc:
        return False, f"مسیر /.well-known/acme-challenge از nginx روی پورت ۸۰ خوانده نشد: {exc}"
    finally:
        file_path.unlink(missing_ok=True)


def _names_for(domain: str, addresses: set[str]) -> tuple[list[str], str]:
    from apps.core.models import AdminDomain
    from apps.sites.models import Website

    names = [domain]
    other = partner_name(domain)
    if not is_public_dns_name(other):
        return names, ""
    taken = Website.objects.filter(domain=other).exists() or AdminDomain.objects.filter(domain=other).exists()
    if taken:
        return names, ""
    ok, resolved = points_here(other, addresses)
    if ok:
        names.append(other)
        return names, ""
    if resolved:
        return names, f"{other} به این سرور اشاره نمی‌کند و داخل گواهی نیامد."
    return names, ""


def _reload_edge() -> str:
    ok, error = apply_maps()
    if not ok:
        return error or "nginx بازنشانی نشد."
    return ""


def _finish_active(cert, names: list[str], note: str) -> str:
    fullchain = _fullchain(cert.domain)
    now = timezone.now()
    _mark(
        cert,
        status=cert.Status.ACTIVE,
        sans=names,
        issuer="Let's Encrypt",
        issued_at=_cert_datetime(fullchain, "-startdate") or now,
        expires_at=_cert_datetime(fullchain, "-enddate"),
        last_attempt_at=now,
        last_error=note,
    )
    secure_tree(cert_paths(cert.domain))
    if cert.kind == cert.Kind.PANEL:
        _sync_https_flag(cert.domain, True)
    edge = _reload_edge()
    if edge:
        _mark(cert, last_error=(note + " " + edge).strip())
        return f"گواهی {cert.domain} صادر شد ولی nginx بارگذاری نشد: {edge}"
    extra = f" ({note})" if note else ""
    return f"گواهی TLS برای {cert.domain} فعال شد.{extra}"


def _issue_unlocked(domain: str, *, force: bool) -> str:
    from apps.tls.models import Certificate

    domain = clean_domain(domain)
    cert = Certificate.objects.filter(domain=domain).first()
    if cert is None:
        return "ردیف گواهی پیدا نشد. اول دامنه را در پنل ثبت کنید."
    if not is_public_dns_name(domain):
        why = "برای آی‌پی، localhost و دامنه محلی گواهی عمومی صادر نمی‌شود. پنل با http و پورت ۸۷۸۷ باز می‌ماند."
        if is_ip(domain):
            why = "Let's Encrypt برای آی‌پی گواهی نمی‌دهد. یک نام دامنه به پنل بدهید. ورود با http://IP:8787 همچنان کار می‌کند."
        _mark(cert, status=Certificate.Status.FAILED, last_error=why, last_attempt_at=timezone.now())
        return why

    now = timezone.now()
    if (
        not force
        and cert.status == Certificate.Status.ISSUING
        and cert.last_attempt_at
        and now - cert.last_attempt_at < timedelta(minutes=15)
    ):
        return f"صدور {domain} همین حالا در جریان است."

    addresses = server_addresses()
    if not addresses:
        why = "آی‌پی این سرور تشخیص داده نشد. شبکه را بررسی کنید و دوباره تلاش کنید."
        _mark(cert, status=Certificate.Status.FAILED, last_error=why, last_attempt_at=now)
        return why
    dns_ok, resolved = points_here(domain, addresses)
    if not dns_ok:
        if resolved:
            why = f"DNS دامنه {domain} به این سرور اشاره نمی‌کند. رکورد A را به آی‌پی سرور بدهید و چند دقیقه بعد دوباره تلاش کنید."
        else:
            why = f"هنوز رکورد DNS برای {domain} پیدا نشد. بعد از اشاره دادن دامنه، صدور خودکار دوباره تلاش می‌کند."
        _mark(cert, status=Certificate.Status.FAILED, last_error=why, last_attempt_at=now)
        return why

    names, note = _names_for(domain, addresses)
    reachable, reach_error = _challenge_reachable(domain)
    if not reachable:
        _mark(cert, status=Certificate.Status.FAILED, last_error=reach_error, last_attempt_at=timezone.now())
        return reach_error

    _mark(cert, status=Certificate.Status.ISSUING, sans=names, last_attempt_at=timezone.now(), last_error="")
    _log(f"issue {domain} names={','.join(names)} force={force}")
    try:
        result = acme.issue(names, _webroot(), _email_for(domain), force=force)
    except AcmeError as exc:
        _mark(cert, status=Certificate.Status.FAILED, last_error=str(exc), last_attempt_at=timezone.now())
        return str(exc)

    output = acme.combined_output(result)
    _log(output or f"acme exit {result.returncode}")
    installed = _fullchain(domain).is_file()
    lowered = output.lower()
    skipped = result.returncode == 2 or "skip" in lowered or "domains not changed" in lowered
    fresh = result.returncode == 0 and not skipped
    if result.returncode != 0 and not (installed and skipped and not force):
        why = _tail(output) or f"acme.sh با کد {result.returncode} متوقف شد."
        _mark(cert, status=Certificate.Status.FAILED, last_error=why, last_attempt_at=timezone.now())
        return f"صدور {domain} ناموفق بود: {why}"

    if fresh or not installed:
        try:
            installed_result = acme.install_cert(domain, cert_paths(domain))
        except AcmeError as exc:
            _mark(cert, status=Certificate.Status.FAILED, last_error=str(exc), last_attempt_at=timezone.now())
            return str(exc)
        install_output = acme.combined_output(installed_result)
        if installed_result.returncode != 0 or not _fullchain(domain).is_file():
            why = _tail(install_output) or "کپی گواهی در /etc/mohsen/ssl انجام نشد."
            _mark(cert, status=Certificate.Status.FAILED, last_error=why, last_attempt_at=timezone.now())
            return why
        _log(install_output)
        _write_names(domain, names)
    else:
        names_path = cert_paths(domain) / "names.txt"
        if names_path.is_file():
            names = [line.strip().lower() for line in names_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            names = [domain]
            _write_names(domain, names)
        note = ""

    secure_tree(cert_paths(domain))
    return _finish_active(cert, names, note)


def _due(cert, now) -> bool:
    from apps.tls.models import Certificate

    if cert is None:
        return True
    if cert.status in {Certificate.Status.QUEUED, Certificate.Status.ISSUING}:
        if cert.status == Certificate.Status.ISSUING and cert.last_attempt_at and now - cert.last_attempt_at < timedelta(minutes=15):
            return False
        return True
    if cert.status == Certificate.Status.ACTIVE:
        if not _fullchain(cert.domain).is_file():
            return True
        return False
    if not cert.last_attempt_at:
        return True
    age = now - cert.last_attempt_at
    text = cert.last_error or ""
    if "DNS" in text or "رکورد" in text or "اشاره" in text:
        return age >= timedelta(minutes=30)
    return age >= timedelta(hours=3)


def _expiring(cert, now) -> bool:
    if cert is None or not cert.expires_at:
        return False
    if cert.expires_at > now + timedelta(days=30):
        return False
    if cert.last_attempt_at and now - cert.last_attempt_at < timedelta(hours=12):
        return False
    return True


def _ensure_row(cert, *, domain: str, kind: str, website=None):
    from apps.tls.models import Certificate

    if cert is None:
        return Certificate.objects.create(
            domain=domain,
            kind=kind,
            status=Certificate.Status.QUEUED,
            website=website,
            auto=True,
        )
    changed = []
    if cert.kind != kind:
        cert.kind = kind
        changed.append("kind")
    if website is not None and cert.website_id != website.pk:
        cert.website = website
        changed.append("website")
    if changed:
        changed.append("updated_at")
        cert.save(update_fields=changed)
    return cert


def _refresh_disk(cert) -> bool:
    fullchain = _fullchain(cert.domain)
    if not fullchain.is_file():
        return False
    expires = _cert_datetime(fullchain, "-enddate")
    issued = _cert_datetime(fullchain, "-startdate")
    cert.status = cert.Status.ACTIVE
    cert.expires_at = expires
    if issued:
        cert.issued_at = issued
    cert.save()
    if cert.kind == cert.Kind.PANEL:
        _sync_https_flag(cert.domain, True)
    return True


def _cron_due() -> bool:
    try:
        if CRON_STAMP.is_file() and (timezone.now().timestamp() - CRON_STAMP.stat().st_mtime) < 12 * 3600:
            return False
    except OSError:
        return True
    return acme.acme_bin().is_file()


def _remove_unlocked(domain: str) -> str:
    from apps.tls.models import Certificate

    domain = clean_domain(domain)
    if not domain:
        return "دامنه خالی است."
    try:
        result = acme.remove(domain)
        output = acme.combined_output(result)
        if output:
            _log(output)
    except AcmeError as exc:
        _log(str(exc))
    dest = cert_paths(domain)
    if dest.is_dir() and dest.parent == ssl_dir():
        shutil.rmtree(dest, ignore_errors=True)
    Certificate.objects.filter(domain=domain).delete()
    _sync_https_flag(domain, False)
    return f"گواهی {domain} برداشته شد."


def _maintain_unlocked() -> str:
    from apps.core.models import AdminDomain
    from apps.sites.models import Website
    from apps.tls.models import Certificate

    notes = []
    if _cron_due():
        try:
            result = acme.cron()
            output = acme.combined_output(result)
            if output:
                _log(output)
            CRON_STAMP.parent.mkdir(parents=True, exist_ok=True)
            CRON_STAMP.write_text(timezone.now().isoformat(), encoding="utf-8")
            notes.append("تمدید acme.sh بررسی شد.")
        except AcmeError as exc:
            notes.append(str(exc))
            _log(str(exc))

    live_domains = set()
    now = timezone.now()

    def consider(domain: str, kind: str, website=None, eligible: bool = True) -> None:
        live_domains.add(domain)
        cert = Certificate.objects.filter(domain=domain).first()
        if not eligible:
            return
        if cert and _fullchain(domain).is_file():
            _refresh_disk(cert)
            if not _expiring(cert, now):
                return
        elif not _due(cert, now):
            return
        _ensure_row(cert, domain=domain, kind=kind, website=website)
        notes.append(_issue_unlocked(domain, force=False))

    for site in Website.objects.all():
        consider(
            site.domain,
            Certificate.Kind.WEBSITE,
            website=site,
            eligible=site.status == Website.Status.ACTIVE and is_public_dns_name(site.domain),
        )

    for row in AdminDomain.objects.all():
        consider(
            row.domain,
            Certificate.Kind.PANEL,
            eligible=is_public_dns_name(row.domain),
        )

    for cert in list(Certificate.objects.all()):
        if cert.domain in live_domains:
            continue
        notes.append(_remove_unlocked(cert.domain))

    edge = _reload_edge()
    if edge:
        notes.append(edge)
    return "\n".join(note for note in notes if note) or "گواهی تازه‌ای لازم نبود."


def perform_issue(domain: str, force: bool = False) -> str:
    with _lock():
        try:
            return _issue_unlocked(domain, force=force)
        finally:
            _restore_db_owner()


def perform_remove(domain: str) -> str:
    with _lock():
        try:
            message = _remove_unlocked(domain)
            edge = _reload_edge()
            if edge:
                return f"{message} اما nginx بارگذاری نشد: {edge}"
            return message
        finally:
            _restore_db_owner()


def perform_maintain() -> str:
    with _lock():
        try:
            return _maintain_unlocked()
        finally:
            _restore_db_owner()


def _poke(cmd: str, domain: str = "", force: bool = False) -> str:
    from apps.tls.client import notify

    payload = {"cmd": cmd, "force": bool(force)}
    if domain:
        payload["domain"] = domain
    try:
        reply = notify(payload)
    except OSError:
        return "در صف ماند. سرویس mohsen-tlsd روشن نیست؛ تایمر خودکار یا sudo mohsen tls ادامه می‌دهد."
    if not reply.get("ok"):
        return f"سرویس صدور پاسخ نداد: {reply.get('error') or 'خطای نامشخص'}"
    return ""


def enqueue(domain: str, kind: str, *, website_id: int | None = None, force: bool = False) -> str:
    from apps.tls.models import Certificate

    domain = clean_domain(domain)
    if not domain:
        return "دامنه خالی است."
    cert, _created = Certificate.objects.get_or_create(
        domain=domain,
        defaults={"kind": kind, "status": Certificate.Status.QUEUED, "auto": True, "website_id": website_id},
    )
    cert.kind = kind
    cert.status = Certificate.Status.QUEUED
    cert.auto = True
    cert.website_id = website_id
    cert.last_error = ""
    cert.save()

    if not is_public_dns_name(domain):
        why = "برای این نام گواهی عمومی صادر نمی‌شود. ورود پنل از http و پورت ۸۷۸۷ برقرار است."
        _mark(cert, status=Certificate.Status.FAILED, last_error=why, last_attempt_at=timezone.now())
        return why

    if os.geteuid() == 0:
        return perform_issue(domain, force=force)

    def _after_commit():
        warning = _poke("issue", domain, force)
        if warning:
            _log(warning)

    transaction.on_commit(_after_commit)
    return f"صدور TLS برای {domain} در صف است. اگر DNS به این سرور اشاره کند، تا حدود یک دقیقه دیگر فعال می‌شود."


def enqueue_remove(domain: str) -> str:
    domain = clean_domain(domain)
    if not domain:
        return ""
    if os.geteuid() == 0:
        return perform_remove(domain)

    def _after_commit():
        warning = _poke("remove", domain, False)
        if warning:
            _log(warning)

    transaction.on_commit(_after_commit)
    return f"حذف گواهی {domain} در صف است."
