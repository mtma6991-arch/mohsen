from django.db import models

from apps.categories.models import Category
from apps.templates_engine.models import TemplatePackage


class Website(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        ACTIVE = "active", "فعال"
        SUSPENDED = "suspended", "معلق"

    customer_name = models.CharField("نام مشتری", max_length=160)
    domain = models.CharField("دامنه", max_length=253, unique=True)
    category = models.ForeignKey(Category, verbose_name="دسته", on_delete=models.PROTECT, related_name="websites")
    template = models.ForeignKey(
        TemplatePackage, verbose_name="قالب", on_delete=models.PROTECT, related_name="websites"
    )
    title = models.CharField("عنوان سایت", max_length=180)
    tagline = models.CharField("شعار", max_length=240, blank=True)
    description = models.TextField("توضیح", blank=True)
    phone = models.CharField("تلفن", max_length=40, blank=True)
    email = models.EmailField("ایمیل", blank=True)
    address = models.CharField("نشانی", max_length=300, blank=True)
    logo_text = models.CharField("متن نشان", max_length=80, blank=True)
    accent_color = models.CharField("رنگ تأکید", max_length=7, blank=True)
    status = models.CharField("وضعیت", max_length=20, choices=Status.choices, default=Status.ACTIVE)
    settings = models.JSONField("تنظیمات محتوا", default=dict, blank=True)
    notes = models.TextField("یادداشت داخلی", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.domain})"


class ContactMessage(models.Model):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name="messages")
    name = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.CharField(max_length=180, blank=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.website.domain}: {self.name}"
