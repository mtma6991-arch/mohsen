from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.access import sync_credentials
from apps.core.audit import log_action
from apps.core.decorators import staff_required
from apps.core.models import AdminDomain
from apps.core.views import sync_admin_domains_file
from apps.sites.domains import validate_admin_domain
from apps.sites.models import Website
from apps.tls.models import Certificate
from apps.tls.names import clean_domain, is_public_dns_name
from apps.tls.service import enqueue, enqueue_remove


@staff_required
@require_http_methods(["GET", "POST"])
def tls_home(request):
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        raw = (request.POST.get("domain") or "").strip()
        try:
            if action == "add-panel":
                domain = validate_admin_domain(raw)
                AdminDomain.objects.filter(is_primary=True).update(is_primary=False)
                AdminDomain.objects.update_or_create(
                    domain=domain, defaults={"is_primary": True, "note": "ثبت از صفحه TLS"}
                )
                sync_admin_domains_file()
                sync_credentials()
                log_action(request, "tls.panel-add", domain, "")
                if is_public_dns_name(domain):
                    messages.success(request, f"دامنه پنل {domain} ثبت شد.")
                    messages.info(request, enqueue(domain, Certificate.Kind.PANEL, force=False))
                else:
                    messages.warning(
                        request,
                        "دامنه ثبت شد. برای آی‌پی گواهی عمومی صادر نمی‌شود و ورود http://IP:8787 می‌ماند.",
                    )
            elif action == "issue":
                domain = clean_domain(raw)
                site = Website.objects.filter(domain=domain).first()
                panel = AdminDomain.objects.filter(domain=domain).first()
                if site is None and panel is None:
                    messages.error(request, "این دامنه در پنل یا وب‌سایت‌ها ثبت نشده است.")
                    return redirect("tls-home")
                kind = Certificate.Kind.WEBSITE if site is not None else Certificate.Kind.PANEL
                website_id = site.pk if site is not None else None
                log_action(request, "tls.issue", domain, kind)
                messages.info(request, enqueue(domain, kind, website_id=website_id, force=True))
            elif action == "remove-panel":
                domain = validate_admin_domain(raw)
                row = AdminDomain.objects.filter(domain=domain).first()
                if row is None:
                    messages.error(request, "این دامنه پنل ثبت نشده است.")
                else:
                    enqueue_remove(domain)
                    row.delete()
                    sync_admin_domains_file()
                    sync_credentials()
                    log_action(request, "tls.panel-remove", domain, "")
                    messages.success(request, f"{domain} و گواهی آن حذف شد.")
            else:
                messages.error(request, "عملیات نامعتبر است.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("tls-home")

    certs = {row.domain: row for row in Certificate.objects.all()}
    return render(
        request,
        "panel/tls.html",
        {
            "panel_domains": AdminDomain.objects.all(),
            "sites": Website.objects.select_related("category").all(),
            "certs": certs,
        },
    )
