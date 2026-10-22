import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def bootstrap_django():
    from apps.core.envfile import load_env_into_os

    load_env_into_os()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
    if not os.environ.get("MOHSEN_SECRET_KEY"):
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.dev"
    import django

    django.setup()


def _hr():
    print("─" * 56)


def _banner():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║              محسن  ·  مدیریت سایت‌ساز               ║")
    print("╚══════════════════════════════════════════════════════╝")


def _menu():
    _banner()
    print("  1) وضعیت سیستم")
    print("  2) افزودن دامنه پنل (add domain)")
    print("  3) نمایش اطلاعات ورود")
    print("  4) تغییر رمز عبور مدیر")
    print("  5) تغییر مسیر محرمانه (web pass)")
    print("  6) راه‌اندازی مجدد سرویس")
    print("  7) پشتیبان‌گیری")
    print("  8) حذف دامنه پنل")
    print("  0) خروج")
    _hr()


def _require_root():
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        print("این کار به root نیاز دارد. دستور را این‌طور اجرا کنید:  sudo mohsen")
        return False
    return True


def status():
    from django.conf import settings

    from apps.categories.models import Category
    from apps.core.models import AdminDomain
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
    print(f"  نسخه:          {settings.VERSION}")
    print(f"  سرویس:         {active}")
    print(f"  پورت پنل:      {settings.PANEL_PORT}")
    print(f"  مسیر محرمانه:  /{settings.WEB_PASS}/")
    print(f"  پایگاه داده:   {db_path} {size}")
    print(f"  دسته‌ها:       {Category.objects.count()}")
    print(f"  قالب‌ها:       {__import__('apps.templates_engine.models', fromlist=['TemplatePackage']).TemplatePackage.objects.count()}")
    print(f"  افزونه‌ها:     {PluginPackage.objects.count()}")
    print(f"  وب‌سایت‌ها:    {Website.objects.count()}")
    domains = list(AdminDomain.objects.values_list("domain", flat=True))
    print("  دامنه‌های پنل: " + ("، ".join(domains) if domains else "هنوز دامنه‌ای اضافه نشده"))
    print("  آدرس با آی‌پی: http://IP-SERVER:" + f"{settings.PANEL_PORT}/{settings.WEB_PASS}/")
    _hr()


def show_login():
    from django.conf import settings
    from django.contrib.auth import get_user_model

    _banner()
    users = list(get_user_model().objects.filter(is_staff=True).values_list("username", flat=True))
    print("  رمز عبور در این صفحه نشان داده نمی‌شود (فقط هنگام نصب چاپ شده است).")
    print(f"  کاربران مدیر: {', '.join(users) if users else '—'}")
    print(f"  مسیر محرمانه: {settings.WEB_PASS}")
    print(f"  پورت:          {settings.PANEL_PORT}")
    print(f"  نمونه آدرس:    http://SERVER:{settings.PANEL_PORT}/{settings.WEB_PASS}/")
    cred = Path("/root/mohsen-credentials.txt")
    if cred.is_file():
        print(f"  رونوشت نصب:    {cred}")
    _hr()


def add_domain():
    from django.conf import settings

    from apps.core.models import AdminDomain
    from apps.sites.domains import validate_admin_domain

    if not _require_root():
        return
    print("دامنه‌ای که می‌خواهید کنار آی‌پی، پنل را باز کند.")
    print("مثال: panel.example.com")
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
    https = False
    answer = input("گواهی SSL با certbot گرفته شود؟ [y/N]: ").strip().lower()
    if answer in {"y", "yes", "بله"}:
        if shutil.which("certbot"):
            proc = subprocess.run(["certbot", "--nginx", "-d", domain, "--non-interactive", "--agree-tos", "-m", f"admin@{domain}", "--redirect"])
            https = proc.returncode == 0
            if https:
                AdminDomain.objects.filter(domain=domain).update(https=True)
            else:
                print("certbot ناموفق بود. دامنه ثبت شد ولی HTTPS فعال نشد.")
        else:
            print("certbot نصب نیست. بعداً: apt install certbot python3-certbot-nginx")
    scheme = "https" if https else "http"
    port = settings.PANEL_PORT
    print()
    print("دامنه ثبت شد. پنل همزمان از هر دو آدرس باز می‌شود:")
    print(f"  آی‌پی:   http://SERVER_IP:{port}/{settings.WEB_PASS}/")
    print(f"  دامنه:   {scheme}://{domain}/{settings.WEB_PASS}/")
    print("رکورد DNS از نوع A را به آی‌پی همین سرور اشاره دهید.")
    print("nginx روی پورت ۸۰ و پورت پنل همه میزبان‌ها را به برنامه می‌دهد؛ نیازی به ساخت سایت جدا برای پنل نیست.")
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
    row.delete()
    print(f"{row.domain} حذف شد. دسترسی با آی‌پی همچنان برقرار است.")


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
    print(f"رمز {user.username} عوض شد.")
    cred = Path("/root/mohsen-credentials.txt")
    if cred.is_file():
        print("فایل /root/mohsen-credentials.txt را دستی به‌روز کنید؛ رمز جدید آنجا نوشته نمی‌شود.")


def change_web_pass():
    import secrets

    from django.conf import settings

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
    print("فایل‌های به‌روز شده:")
    for item in files:
        print(" ", item)
    print(f"آدرس تازه پس از راه‌اندازی مجدد: http://SERVER:{settings.PANEL_PORT}/{raw}/")
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
    os.chmod(dest, 0o700)
    print(f"پشتیبان ساخته شد: {dest}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
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
        "4": change_password,
        "5": change_web_pass,
        "6": restart_service,
        "7": backup,
        "8": remove_domain,
        "status": status,
    }
    if argv:
        action = actions.get(argv[0])
        if action is None:
            print("فرمان ناشناخته. بدون آرگومان اجرا کنید تا منو باز شود.")
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
