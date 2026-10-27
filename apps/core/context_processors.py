from django.conf import settings

from apps.core.models import AdminDomain


def panel(request):
    prefix = f"/{settings.WEB_PASS}/"
    if not request.path.startswith(prefix):
        return {}
    domains = list(AdminDomain.objects.all()[:20])
    return {
        "WEB_PASS": settings.WEB_PASS,
        "PANEL_PORT": settings.PANEL_PORT,
        "MOHSEN_VERSION": settings.VERSION,
        "admin_domains": domains,
        "panel_prefix": prefix,
    }
