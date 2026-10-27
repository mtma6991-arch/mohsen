import io
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model

from apps.categories.models import Category
from apps.core.zipsafe import ZipRejected
from apps.plugins.models import CategoryPlugin, PluginPackage
from apps.plugins.services import store_plugin
from apps.sites.models import Website
from apps.templates_engine.models import TemplatePackage
from apps.templates_engine.services import store_template


def zip_tree(root: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            zf.write(path, path.relative_to(root).as_posix())
    return buf.getvalue()


def ensure_categories():
    specs = [
        {
            "slug": "gold",
            "name": "طلایی",
            "tier_label": "Gold",
            "description": "سطح تجاری لوکس. مناسب فروشگاه‌هایی که قالب و افزونه اختصاصی سطح بالا می‌خواهند.",
            "color": "#B6894A",
            "icon": "gem",
            "sort_order": 1,
        },
        {
            "slug": "silver",
            "name": "نقره‌ای",
            "tier_label": "Silver",
            "description": "سطح فروشگاهی. مناسب کسب‌وکارهایی که صفحه عمومی و ابزار ساخت صفحه می‌خواهند.",
            "color": "#8D99A6",
            "icon": "device",
            "sort_order": 2,
        },
    ]
    created = []
    for spec in specs:
        obj, was_created = Category.objects.get_or_create(slug=spec["slug"], defaults=spec)
        if was_created:
            created.append(obj.slug)
    return created


def ensure_examples():
    base = Path(settings.BASE_DIR)
    notes = []
    gold = Category.objects.filter(slug="gold").first()
    silver = Category.objects.filter(slug="silver").first()
    pairs = [
        (base / "examples" / "templates" / "jewelry-atelier", gold, "jewelry-atelier"),
        (base / "examples" / "templates" / "silver-phones", silver, "silver-phones"),
    ]
    for folder, category, slug in pairs:
        if category is None or not folder.is_dir():
            continue
        if TemplatePackage.objects.filter(slug=slug).exists():
            notes.append(f"قالب {slug} از قبل نصب است")
            continue
        try:
            obj, created = store_template(raw=zip_tree(folder), category=category)
        except ZipRejected as exc:
            notes.append(f"قالب {folder.name}: {exc}")
            continue
        notes.append(f"قالب {obj.slug} نصب شد" if created else f"قالب {obj.slug} به‌روز شد")
    plugin_pairs = [
        (base / "examples" / "plugins" / "sms", "sms", gold),
        (base / "examples" / "plugins" / "page-builder", "page-builder", silver),
    ]
    for folder, slug, category in plugin_pairs:
        if not folder.is_dir():
            continue
        obj = PluginPackage.objects.filter(slug=slug).first()
        if obj is None:
            try:
                obj, created = store_plugin(raw=zip_tree(folder))
            except ZipRejected as exc:
                notes.append(f"افزونه {slug}: {exc}")
                continue
            notes.append(f"افزونه {obj.slug} نصب شد" if created else f"افزونه {obj.slug} به‌روز شد")
        else:
            notes.append(f"افزونه {slug} از قبل نصب است")
        if category is not None and obj is not None:
            CategoryPlugin.objects.get_or_create(
                category=category, plugin=obj, defaults={"enabled": True, "settings": {}}
            )
    _ensure_sample_sites()
    return notes


def _ensure_sample_sites():
    gold = Category.objects.filter(slug="gold").first()
    silver = Category.objects.filter(slug="silver").first()
    jewelry = None
    phones = None
    if gold:
        jewelry = gold.templates.filter(slug="jewelry-atelier").first()
    if silver:
        phones = silver.templates.filter(slug="silver-phones").first()
    if gold and jewelry and not Website.objects.filter(domain="zarrin.local").exists():
        Website.objects.create(
            customer_name="خانه زرین",
            domain="zarrin.local",
            category=gold,
            template=jewelry,
            title="خانه زرین",
            tagline="جواهراتی برای مناسبت‌هایی که می‌مانند",
            description="نمونه نصب‌شده دسته طلایی. از پیش‌نمایش پنل باز می‌شود.",
            phone="021-91098080",
            email="hello@zarrin.local",
            address="تهران، خیابان شریعتی",
            logo_text="زرین",
            accent_color="#B6894A",
            status=Website.Status.ACTIVE,
            notes="نمونه نصب",
        )
    if silver and phones and not Website.objects.filter(domain="hamrah.local").exists():
        Website.objects.create(
            customer_name="همراه کالا",
            domain="hamrah.local",
            category=silver,
            template=phones,
            title="همراه کالا",
            tagline="گوشی، لوازم و مشاوره انتخاب",
            description="نمونه نصب‌شده دسته نقره‌ای با صفحه ساز.",
            phone="021-42000000",
            email="hello@hamrah.local",
            address="تهران، پاساژ علاءالدین",
            logo_text="همراه",
            accent_color="#3E4C59",
            status=Website.Status.ACTIVE,
            notes="نمونه نصب",
        )


def ensure_admin_user():
    import os

    username = os.environ.get("MOHSEN_ADMIN_USER", "").strip()
    password = os.environ.get("MOHSEN_ADMIN_PASSWORD", "").strip()
    User = get_user_model()
    if username and password:
        user, created = User.objects.get_or_create(username=username, defaults={"is_staff": True, "is_superuser": True, "email": ""})
        if created or os.environ.get("MOHSEN_ADMIN_RESET", "") == "1":
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
        return user, created
    if settings.DEBUG and not User.objects.filter(is_staff=True).exists():
        user = User(username="admin", email="admin@localhost", is_staff=True, is_superuser=True)
        user.set_password("admin12345")
        user.save()
        return user, True
    return None, False
