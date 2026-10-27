import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("sites", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Certificate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("domain", models.CharField(max_length=253, unique=True, verbose_name="دامنه")),
                (
                    "kind",
                    models.CharField(
                        choices=[("panel", "پنل"), ("website", "وب‌سایت")],
                        max_length=20,
                        verbose_name="نوع",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "در صف"),
                            ("issuing", "در حال صدور"),
                            ("active", "فعال"),
                            ("failed", "ناموفق"),
                        ],
                        default="queued",
                        max_length=20,
                        verbose_name="وضعیت",
                    ),
                ),
                ("sans", models.JSONField(blank=True, default=list, verbose_name="نام‌های گواهی")),
                (
                    "issuer",
                    models.CharField(blank=True, default="Let's Encrypt", max_length=80, verbose_name="صادرکننده"),
                ),
                ("issued_at", models.DateTimeField(blank=True, null=True, verbose_name="زمان صدور")),
                ("expires_at", models.DateTimeField(blank=True, null=True, verbose_name="انقضا")),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True, verbose_name="آخرین تلاش")),
                ("last_error", models.TextField(blank=True, verbose_name="آخرین خطا")),
                ("auto", models.BooleanField(default=True, verbose_name="تمدید خودکار")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "website",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="certificates",
                        to="sites.website",
                        verbose_name="وب‌سایت",
                    ),
                ),
            ],
            options={
                "verbose_name": "گواهی",
                "verbose_name_plural": "گواهی‌ها",
                "ordering": ["kind", "domain"],
            },
        ),
    ]
