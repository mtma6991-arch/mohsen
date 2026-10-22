import re

from django import forms
from django.utils.text import slugify

from apps.categories.models import Category

ICON_CHOICES = [
    ("gem", "جواهر"),
    ("crown", "تاج"),
    ("device", "دستگاه"),
    ("shop", "فروشگاه"),
    ("star", "ستاره"),
    ("leaf", "برگ"),
]


class CategoryForm(forms.ModelForm):
    slug = forms.CharField(label="نامک", required=False)
    color = forms.CharField(label="رنگ", widget=forms.TextInput(attrs={"type": "color"}))
    icon = forms.ChoiceField(label="نماد", choices=ICON_CHOICES)

    class Meta:
        model = Category
        fields = ["name", "slug", "tier_label", "description", "color", "icon", "sort_order", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def clean_color(self):
        color = (self.cleaned_data.get("color") or "").strip()
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise forms.ValidationError("رنگ باید مثل #C6A15B باشد.")
        return color.upper()

    def clean_slug(self):
        raw = (self.cleaned_data.get("slug") or "").strip()
        source = raw or self.cleaned_data.get("name") or "category"
        slug = slugify(source, allow_unicode=True)[:80]
        if not slug:
            slug = "category"
        qs = Category.objects.filter(slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("این نامک قبلاً استفاده شده است.")
        return slug
