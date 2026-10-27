import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from apps.core.access import login_snapshot, sync_credentials


def bootstrap_django():
    from apps.core.envfile import load_env_into_os

    load_env_into_os()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
    if not os.environ.get("MOHSEN_SECRET_KEY"):
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.dev"
    import django

    django.setup()


def _hr():
    print("─" * 64)


def _banner():
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║              محسن  ·  مدیریت سایت‌ساز               ║")
    print("╚════════════════════════════════════════════════════════════╝")


def _root():
    return hasattr(os, "geteuid") and os.geteuid() == 0


def _require_root():
    if not _root():
        print("این کار به root نیاز دارد. دستور را این‌طور اجرا کنید:  sudo mohsen")
        return False
    return True


def _print_login(snapshot=None):
    snap = snapshot or login_snapshot()
    _hr()
    print("ورود پنل — این آدرس را عیناً در نوار مرورگر وارد کنید")
    if snap["urls"]:
        for url in snap["urls"]:
            print(f"  {url}")
    else:
        print("  آی‌پی قابل استفاده روی کارت شبکه پیدا نشد.")
        print("  آدرس ساختگی نشان داده نمی‌شود، چون در مرورگر باز نمی‌شود.")
        print("  روی سرور بررسی کنید: hostname -I")
    print(f"  نام کاربری: {snap['username']}")
    if snap["password"] and _root():
        print(f"  رمز عبور:   {snap['password']}")
    elif snap["password"]:
        print("  رمز عبور:   (برای دیدن رمز: sudo mohsen)")
    elif os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(".dev"):
        print("  رمز عبور:   در توسعه محلی، اگر bootstrap شده باشد admin12345 است.")
    else:
        print("  رمز عبور:   در /root/mohsen-credentials.txt پیدا نشد.")
    if snap["credentials_path"]:
        print(f"  فایل رمز:   {snap['credentials_path']}")
    _hr()


def _menu():
    _banner()
    _print_login()
    print("  1) وضعیت سیستم")
    print("  2) افزودن دامنه پنل (add domain)")
    print("  3) نمایش دوباره اطلاعات ورود")
    print("  4) تغییر رمز عبور مدیر")
    print("  5) تغییر مسیر محرمانه (web pass)")
    print("  6) راه‌اندازی مجدد سرویس")
    print("  7) پشتیبان‌گیری")
    print("  8) حذف دامنه پنل")
    print("  9) به‌روزرسانی از گیت‌هاب   sudo mohsen update")
    print(" 10) حذف کامل پروژه         sudo mohsen uninstall --yes")
    print(" 11) صدور و تمدید TLS       sudo mohsen tls")
    print("  0) خروج")
    _hr()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def status():
    from django.conf import settings

    from apps.categories.models import Category
    from apps.plugins.models import PluginPackage
    from apps.sites.models import Website

    _banner()
    active = "نامشخص"
    try:
        result = subprocess.run(["systemctl", "is-active", "mohsen"], capture_output=True, text=True, timeout=5)
        active = (result.stdout or result.stderr or "").strip() or "نامشخص"
    except Exception:
        active = "systemd در دسترس نیست"
    db_path = Path(settings.DATABASES["default"].get("NAME", ""))
    size = ""
    if db_path.is_file():
        size = f"{db_path.stat().st_size / 1024:.0f} KB"
    snap = login_snapshot()
    print(f"  نسخه:          {settings.VERSION}")
    print(f"  سرویس:         {active}")
    print(f"  پورت پنل:      {settings.PANEL_PORT}")
    print(f"  مسیر محرمانه:  /{settings.WEB_PASS}/")
    print(f"  پایگاه داده:   {db_path} {size}")
    print(f"  دسته‌ها:       {Category.objects.count()}")
    print(f"  قالب‌ها:       {__import__('apps.templates_engine.models', fromlist=['TemplatePackage']).TemplatePackage.objects.count()}")
    print(f"  افزونه‌ها:     {PluginPackage.objects.count()}")
    print(f"  وب‌سایت‌ها:    {Website.objects.count()}")
    try:
        from apps.tls.models import Certificate

        print(f"  گواهی فعال:    {Certificate.objects.filter(status=Certificate.Status.ACTIVE).count()}")
        print(f"  گواهی ناموفق:  {Certificate.objects.filter(status=Certificate.Status.FAILED).count()}")
    except Exception:
        print("  گواهی TLS:     هنوز آماده نیست")
    _print_login(snap)


def show_login():
    _banner()
    _print_login()


def add_domain():
    from django.conf import settings

    from apps.core.models import AdminDomain
    from apps.sites.domains import validate_admin_domain

    if not _require_root():
        return
    print("دامنه‌ای که کنار آی‌پی، پنل را باز کند. مثال: panel.example.com")
    raw = input("دامنه: ").strip()
    try:
        domain = validate_admin_domain(raw)
    except ValueError as exc:
        print(exc)
        return
    AdminDomain.objects.filter(is_primary=True).update(is_primary=False)
    AdminDomain.objects.update_or_create(domain=domain, defaults={"is_primary": True, "note": "افزوده‌شده با دستور mohsen"})
    registry = Path("/etc/mohsen/admin-domains.txt")
    try:
        registry.parent.mkdir(parents=True, exist_ok=True)
        names = "\n".join(AdminDomain.objects.values_list("domain", flat=True))
        registry.write_text(names + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"هشدار: فهرست دامنه نوشته نشد: {exc}")
    from apps.tls.names import is_public_dns_name
    from apps.tls.service import enqueue

    print()
    print("دامنه ثبت شد. رکورد DNS از نوع A را به آی‌پی همین سرور اشاره دهید.")
    if is_public_dns_name(domain):
        print(enqueue(domain, "panel", force=False))
    else:
        print("برای آی‌پی یا نام محلی گواهی عمومی صادر نمی‌شود.")
        print(f"  ورود با پورت پنل: http://{domain}:{settings.PANEL_PORT}/{settings.WEB_PASS}/")
    _print_login()
    sync_credentials()
    _hr()


def remove_domain():
    from apps.core.models import AdminDomain

    if not _require_root():
        return
    rows = list(AdminDomain.objects.all())
    if not rows:
        print("دامنه‌ای ثبت نشده است.")
        return
    for index, row in enumerate(rows, start=1):
        print(f"  {index}) {row.domain}")
    raw = input("شماره دامنه برای حذف: ").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= len(rows)):
        print("شماره نامعتبر است.")
        return
    row = rows[int(raw) - 1]
    from apps.tls.service import enqueue_remove

    print(enqueue_remove(row.domain))
    row.delete()
    print(f"{row.domain} حذف شد.")
    _print_login()
    sync_credentials()


def change_password():
    from django.contrib.auth import get_user_model

    if not _require_root():
        return
    User = get_user_model()
    users = list(User.objects.filter(is_staff=True))
    if not users:
        print("کاربر مدیری وجود ندارد.")
        return
    for index, user in enumerate(users, start=1):
        print(f"  {index}) {user.username}")
    raw = input("شماره کاربر [1]: ").strip() or "1"
    if not raw.isdigit() or not (1 <= int(raw) <= len(users)):
        print("شماره نامعتبر است.")
        return
    user = users[int(raw) - 1]
    password = input("رمز جدید (حداقل ۸ نویسه): ").strip()
    again = input("تکرار رمز: ").strip()
    if len(password) < 8 or password != again:
        print("رمز معتبر نیست یا تکرارش یکی نیست.")
        return
    user.set_password(password)
    user.save()
    sync_credentials(password=password, username=user.username)
    print(f"رمز {user.username} عوض شد و در /root/mohsen-credentials.txt نوشته شد.")
    _print_login()


def change_web_pass():
    import secrets

    if not _require_root():
        return
    suggested = secrets.token_urlsafe(9)
    raw = input(f"مسیر محرمانه جدید [{suggested}]: ").strip() or suggested
    raw = raw.strip().strip("/")
    if not raw or "/" in raw or len(raw) < 6:
        print("مسیر باید بدون اسلش و حداقل ۶ نویسه باشد.")
        return
    from apps.core.envfile import update_keys

    try:
        files = update_keys({"MOHSEN_WEB_PASS": raw})
    except Exception as exc:
        print(exc)
        return
    os.environ["MOHSEN_WEB_PASS"] = raw
    from django.conf import settings

    settings.WEB_PASS = raw
    print("فایل‌های به‌روز شده:")
    for item in files:
        print(" ", item)
    sync_credentials()
    print("آدرس تازه:")
    _print_login()
    answer = input("سرویس الان راه‌اندازی مجدد شود؟ [Y/n]: ").strip().lower()
    if answer not in {"n", "no", "خیر"}:
        restart_service()


def restart_service():
    if not _require_root():
        return
    proc = subprocess.run(["systemctl", "restart", "mohsen"])
    if proc.returncode == 0:
        print("سرویس mohsen راه‌اندازی مجدد شد.")
    else:
        print("راه‌اندازی مجدد ناموفق بود. وضعیت: systemctl status mohsen")


def backup():
    from django.conf import settings

    if not _require_root():
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = Path("/var/backups/mohsen") / stamp
    dest.mkdir(parents=True, exist_ok=True)
    db = Path(settings.DATABASES["default"].get("NAME", ""))
    if db.is_file():
        shutil.copy2(db, dest / db.name)
    media = Path(settings.MEDIA_ROOT)
    if media.is_dir():
        shutil.copytree(media, dest / "media", dirs_exist_ok=True)
    env = Path("/etc/mohsen/mohsen.env")
    if env.is_file():
        shutil.copy2(env, dest / "mohsen.env")
    ssl = Path("/etc/mohsen/ssl")
    if ssl.is_dir():
        shutil.copytree(ssl, dest / "ssl", dirs_exist_ok=True)
    os.chmod(dest, 0o700)
    print(f"پشتیبان ساخته شد: {dest}")


def update_project():
    if not _require_root():
        return
    script = _project_root() / "deploy" / "update.sh"
    if not script.is_file():
        print("فایل به‌روزرسانی پیدا نشد: deploy/update.sh")
        return
    print("دریافت کد تازه از https://github.com/mtma6991-arch/mohsen")
    os.execv("/bin/bash", ["bash", str(script)])


def uninstall_project():
    if not _require_root():
        return
    print("حذف کامل محسن: سرویس، سایت nginx، دستور، کد، پایگاه، رسانه، تنظیمات و فایل رمز.")
    print("برگشت‌پذیر نیست. برای تأیید بنویسید: uninstall")
    answer = input("تأیید: ").strip().lower()
    if answer != "uninstall":
        print("لغو شد.")
        return
    script = _project_root() / "uninstall.sh"
    os.execv("/bin/bash", ["bash", str(script), "--yes"])


def tls_maintain_cli():
    if not _require_root():
        return
    from apps.tls.service import perform_maintain

    print("صدور گواهی‌های جاافتاده و تمدید نزدیک به انقضا. ممکن است چند دقیقه طول بکشد.")
    print(perform_maintain())


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "update":
        if not _require_root():
            return 1
        script = _project_root() / "deploy" / "update.sh"
        os.execv("/bin/bash", ["bash", str(script)])
    if argv and argv[0] == "uninstall":
        if not _require_root():
            return 1
        script = _project_root() / "uninstall.sh"
        os.execv("/bin/bash", ["bash", str(script), *argv[1:]])
    try:
        bootstrap_django()
    except Exception as exc:
        print("برنامه بالا نیامد. اگر روی سرور هستید فایل /etc/mohsen/mohsen.env را بررسی کنید.")
        print(exc)
        return 1
    actions = {
        "1": status,
        "2": add_domain,
        "add-domain": add_domain,
        "3": show_login,
        "login": show_login,
        "4": change_password,
        "5": change_web_pass,
        "6": restart_service,
        "7": backup,
        "8": remove_domain,
        "9": update_project,
        "update": update_project,
        "10": uninstall_project,
        "uninstall": uninstall_project,
        "11": tls_maintain_cli,
        "tls": tls_maintain_cli,
        "status": status,
    }
    if argv:
        action = actions.get(argv[0])
        if action is None:
            print("فرمان ناشناخته.")
            print("  sudo mohsen")
            print("  sudo mohsen tls")
            print("  sudo mohsen update")
            print("  sudo mohsen uninstall --yes")
            return 2
        action()
        return 0
    while True:
        _menu()
        choice = input("گزینه: ").strip().lower()
        if choice in {"0", "q", "exit", "خروج"}:
            print("خداحافظ.")
            return 0
        action = actions.get(choice)
        if action is None:
            print("گزینه نامعتبر است.")
            continue
        try:
            action()
        except KeyboardInterrupt:
            print("\nلغو شد.")
        except EOFError:
            print()
            return 0
        except Exception as exc:
            print(f"خطا: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
