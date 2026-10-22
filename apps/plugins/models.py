from django.db import models

from apps.categories.models import Category


class PluginPackage(models.Model):
    name = models.CharField("نام", max_length=160)
    slug = models.SlugField("نامک", max_length=80, unique=True)
    version = models.CharField("نسخه", max_length=40, default="1.0.0")
    author = models.CharField("سازنده", max_length=120, blank=True)
    description = models.TextField("توضیح", blank=True)
    archive = models.FileField("فایل زیپ", upload_to="plugin_archives/", blank=True)
    extracted_path = models.CharField(max_length=500, blank=True)
    manifest = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CategoryPlugin(models.Model):
    category = models.ForeignKey(
        Category, verbose_name="دسته", on_delete=models.CASCADE, related_name="category_plugins"
    )
    plugin = models.ForeignKey(
        PluginPackage, verbose_name="افزونه", on_delete=models.CASCADE, related_name="assignments"
    )
    enabled = models.BooleanField("فعال برای دسته", default=True)
    settings = models.JSONField("تنظیمات پیش‌فرض دسته", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["category", "plugin"], name="uniq_category_plugin"),
        ]
        ordering = ["plugin__name"]

    def __str__(self):
        return f"{self.plugin} → {self.category}"


class PluginStorage(models.Model):
    website = models.ForeignKey("sites.Website", on_delete=models.CASCADE, related_name="plugin_storage")
    plugin_slug = models.SlugField(max_length=80)
    key = models.CharField(max_length=80)
    value = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["website", "plugin_slug", "key"], name="uniq_plugin_storage"),
        ]

    def __str__(self):
        return f"{self.plugin_slug}:{self.key}@{self.website_id}"
