from urllib.parse import urlparse

from django.conf import settings


class DynamicCsrfMiddleware:
    """جلوگیری از خطای 403 CSRF هنگام ورود با پورت 8787 یا پشت کلودفلر/پراکسی."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = (request.META.get("HTTP_ORIGIN") or "").strip()
        if origin and origin != "null":
            try:
                parsed = urlparse(origin)
                origin_host = (parsed.hostname or "").strip().lower()
                req_host = request.get_host().split(":")[0].strip().lower()
                if origin_host and origin_host == req_host:
                    trusted = list(getattr(settings, "CSRF_TRUSTED_ORIGINS", []) or [])
                    base_origin = f"{parsed.scheme}://{parsed.netloc}"
                    if base_origin not in trusted:
                        trusted.append(base_origin)
                        settings.CSRF_TRUSTED_ORIGINS = trusted
            except Exception:
                pass
        return self.get_response(request)
