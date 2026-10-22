from django.db import models


class Category(models.Model):
    name = models.CharField("نام", max_length=120)
    slug = models.SlugField("نامک", max_length=80, unique=True, allow_unicode=True)
    tier_label = models.CharField("برچسب سطح", max_length=80, blank=True)
    description = models.TextField("توضیح", blank=True)
    color = models.CharField("رنگ", max_length=7, default="#B6894A")
    icon = models.CharField("نماد", max_length=40, default="gem")
    sort_order = models.PositiveIntegerField("ترتیب", default=0)
    is_active = models.BooleanField("فعال", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "دسته"
        verbose_name_plural = "دسته‌ها"

    def __str__(self):
        return self.name

    @property
    def site_count(self):
        return self.websites.count()

    @property
    def template_count(self):
        return self.templates.count()
