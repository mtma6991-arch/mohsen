import json
import re

from django import forms

from apps.sites.domains import validate_customer_domain
from apps.sites.models import Website
from apps.templates_engine.models import TemplatePackage

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class WebsiteForm(forms.ModelForm):
    content_json = forms.CharField(
        label="محتوای اختصاصی (JSON)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 8, "dir": "ltr", "spellcheck": "false"}),
        help_text="جایگزین کلیدهای demo_data قالب می‌شود. مثال: {\"products\": []}. خالی یعنی داده نمونه قالب.",
    )

    class Meta:
        model = Website
        fields = [
            "customer_name", "domain", "category", "template", "title", "tagline",
            "description", "phone", "email", "address", "logo_text", "accent_color",
            "status", "notes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "accent_color": forms.TextInput(attrs={"type": "color"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = TemplatePackage.objects.filter(is_active=True).select_related("category")
        self.fields["category"].queryset = self.fields["category"].queryset.filter(is_active=True)
        content = {}
        if self.instance.pk:
            content = (self.instance.settings or {}).get("content") or {}
        if content:
            self.fields["content_json"].initial = json.dumps(content, ensure_ascii=False, indent=2)
        if not self.instance.pk and not self.initial.get("status"):
            self.initial["status"] = Website.Status.ACTIVE

    def clean_domain(self):
        try:
            domain = validate_customer_domain(self.cleaned_data.get("domain") or "")
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
        qs = Website.objects.filter(domain=domain)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("این دامنه قبلاً ثبت شده است.")
        return domain

    def clean_accent_color(self):
        value = (self.cleaned_data.get("accent_color") or "").strip()
        if not value:
            return ""
        if not HEX_RE.fullmatch(value):
            raise forms.ValidationError("رنگ نامعتبر است.")
        return value.upper()

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        template = cleaned.get("template")
        if category and template and template.category_id != category.id:
            self.add_error("template", "قالب باید متعلق به همان دسته سایت باشد.")
        raw = (cleaned.get("content_json") or "").strip()
        if not raw:
            cleaned["content"] = {}
            return cleaned
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.add_error("content_json", f"JSON نامعتبر است: {exc}")
            return cleaned
        if not isinstance(parsed, dict):
            self.add_error("content_json", "محتوا باید یک شیء JSON باشد.")
            return cleaned
        cleaned["content"] = parsed
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        settings_data = dict(obj.settings or {})
        settings_data["content"] = self.cleaned_data.get("content") or {}
        obj.settings = settings_data
        if not obj.logo_text:
            obj.logo_text = obj.title[:80]
        if commit:
            obj.save()
        return obj
