from django.db import models


class Certificate(models.Model):
    class Kind(models.TextChoices):
        PANEL = "panel", "پنل"
        WEBSITE = "website", "وب‌سایت"

    class Status(models.TextChoices):
        QUEUED = "queued", "در صف"
        ISSUING = "issuing", "در حال صدور"
        ACTIVE = "active", "فعال"
        FAILED = "failed", "ناموفق"

    domain = models.CharField("دامنه", max_length=253, unique=True)
    kind = models.CharField("نوع", max_length=20, choices=Kind.choices)
    status = models.CharField("وضعیت", max_length=20, choices=Status.choices, default=Status.QUEUED)
    sans = models.JSONField("نام‌های گواهی", default=list, blank=True)
    issuer = models.CharField("صادرکننده", max_length=80, default="Let's Encrypt", blank=True)
    issued_at = models.DateTimeField("زمان صدور", null=True, blank=True)
    expires_at = models.DateTimeField("انقضا", null=True, blank=True)
    last_attempt_at = models.DateTimeField("آخرین تلاش", null=True, blank=True)
    last_error = models.TextField("آخرین خطا", blank=True)
    auto = models.BooleanField("تمدید خودکار", default=True)
    website = models.ForeignKey(
        "sites.Website",
        verbose_name="وب‌سایت",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certificates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind", "domain"]
        verbose_name = "گواهی"
        verbose_name_plural = "گواهی‌ها"

    def __str__(self):
        return f"{self.domain} ({self.get_status_display()})"
