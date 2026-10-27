from django.db import models

from apps.categories.models import Category


class TemplatePackage(models.Model):
    category = models.ForeignKey(Category, verbose_name="دسته", on_delete=models.PROTECT, related_name="templates")
    name = models.CharField("نام", max_length=160)
    slug = models.SlugField("نامک", max_length=80, unique=True)
    version = models.CharField("نسخه", max_length=40, default="1.0.0")
    author = models.CharField("سازنده", max_length=120, blank=True)
    description = models.TextField("توضیح", blank=True)
    archive = models.FileField("فایل زیپ", upload_to="template_archives/", blank=True)
    extracted_path = models.CharField(max_length=500, blank=True)
    manifest = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__sort_order", "name"]

    def __str__(self):
        return self.name

    @property
    def pages(self):
        return list((self.manifest or {}).get("pages") or [])
