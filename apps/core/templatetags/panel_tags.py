import jdatetime
from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def jalali(value):
    if not value:
        return ""
    try:
        local = timezone.localtime(value) if timezone.is_aware(value) else value
        converted = jdatetime.datetime.fromgregorian(datetime=local.replace(tzinfo=None))
        return converted.strftime("%Y/%m/%d %H:%M")
    except Exception:
        return str(value)


@register.filter
def get_item(mapping, key):
    if isinstance(mapping, dict):
        return mapping.get(key)
    return None
