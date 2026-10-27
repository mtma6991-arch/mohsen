from apps.sites.domains import host_lookup_variants
from apps.sites.models import Website


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.is_admin_domain = False
        request.url_prefix = ""
        host = request.get_host().split(":")[0].lower()
        variants = host_lookup_variants(host)
        if variants:
            request.tenant = (
                Website.objects.filter(domain__in=variants)
                .select_related("category", "template")
                .first()
            )
            if request.tenant is None:
                from apps.core.models import AdminDomain

                request.is_admin_domain = AdminDomain.objects.filter(domain__in=variants).exists()
        return self.get_response(request)
