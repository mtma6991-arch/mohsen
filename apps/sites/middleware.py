from apps.sites.domains import host_lookup_variants
from apps.sites.models import Website


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.url_prefix = ""
        host = request.get_host().split(":")[0].lower()
        variants = host_lookup_variants(host)
        if variants:
            request.tenant = (
                Website.objects.filter(domain__in=variants)
                .select_related("category", "template")
                .first()
            )
        return self.get_response(request)
