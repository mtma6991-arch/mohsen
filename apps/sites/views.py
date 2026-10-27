from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.audit import log_action
from apps.core.decorators import staff_required
from apps.plugins.loader import iter_site_plugins
from apps.sites.forms import WebsiteForm
from apps.sites.models import ContactMessage, Website
from apps.templates_engine.models import TemplatePackage
from apps.tls.models import Certificate
from apps.tls.service import enqueue, enqueue_remove


def _template_map():
    rows = TemplatePackage.objects.filter(is_active=True).values("id", "name", "category_id", "version")
    return list(rows)


def _schedule_site_tls(obj, *, previous_domain, previous_status, created):
    if previous_domain and previous_domain != obj.domain:
        enqueue_remove(previous_domain)
    became_active = previous_status != Website.Status.ACTIVE and obj.status == Website.Status.ACTIVE
    domain_changed = bool(previous_domain) and previous_domain != obj.domain
    if obj.status != Website.Status.ACTIVE:
        return ""
    if not (created or domain_changed or became_active):
        return ""
    return enqueue(obj.domain, Certificate.Kind.WEBSITE, website_id=obj.pk, force=False)


@staff_required
def site_list(request):
    q = (request.GET.get("q") or "").strip()
    rows = Website.objects.select_related("category", "template")
    if q:
        rows = rows.filter(domain__icontains=q) | rows.filter(customer_name__icontains=q) | rows.filter(title__icontains=q)
        rows = rows.distinct()
    rows = list(rows)
    tls_map = {cert.domain: cert for cert in Certificate.objects.filter(domain__in=[row.domain for row in rows])}
    return render(request, "panel/sites/list.html", {"rows": rows, "q": q, "tls_map": tls_map})


@staff_required
def site_create(request):
    form = WebsiteForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            obj = form.save()
            log_action(request, "site.create", obj.domain, obj.customer_name)
            messages.success(request, "سایت ثبت شد. با اشاره دادن DNS دامنه به این سرور، سایت باز می‌شود.")
            note = _schedule_site_tls(obj, previous_domain="", previous_status="", created=True)
            if note:
                messages.info(request, note)
            return redirect("site-edit", pk=obj.pk)
        messages.error(request, "ثبت سایت انجام نشد. لطفاً خطاهای مشخص‌شده در فرم را بررسی کنید.")
    return render(request, "panel/sites/form.html", {"form": form, "mode": "create", "template_map": _template_map()})


@staff_required
def site_edit(request, pk):
    obj = get_object_or_404(Website.objects.select_related("category", "template"), pk=pk)
    if request.method == "POST" and request.POST.get("_plugin"):
        slug = request.POST.get("_plugin")
        matched = None
        for _row, inst in iter_site_plugins(obj):
            if inst.slug == slug:
                matched = inst
                break
        if matched is None:
            messages.error(request, "این افزونه روی دسته سایت فعال نیست.")
        else:
            try:
                matched.handle_admin_post(request, obj)
                log_action(request, "site.plugin", obj.domain, slug)
                messages.success(request, "تغییر افزونه ذخیره شد.")
            except Exception as exc:
                messages.error(request, f"افزونه خطا داد: {exc}")
        return redirect("site-edit", pk=pk)

    previous_domain = obj.domain
    previous_status = obj.status
    form = WebsiteForm(request.POST or None, instance=obj)
    if request.method == "POST":
        if form.is_valid():
            saved = form.save()
            log_action(request, "site.update", saved.domain, saved.title)
            messages.success(request, "سایت به‌روز شد.")
            note = _schedule_site_tls(
                saved,
                previous_domain=previous_domain,
                previous_status=previous_status,
                created=False,
            )
            if note:
                messages.info(request, note)
            return redirect("site-edit", pk=pk)
        messages.error(request, "تغییرات ذخیره نشد. خطاهای فرم را بررسی کنید.")

    panels = []
    for _row, inst in iter_site_plugins(obj):
        try:
            panel = inst.admin_panel(request, obj)
        except Exception as exc:
            panel = {"title": inst.name or inst.slug, "html": f"<p>خطا در پنل افزونه: {exc}</p>"}
        if panel:
            panels.append(panel)
    inbox = obj.messages.all()[:30]
    tls_cert = Certificate.objects.filter(domain=obj.domain).first()
    return render(
        request,
        "panel/sites/form.html",
        {
            "form": form,
            "mode": "edit",
            "obj": obj,
            "template_map": _template_map(),
            "panels": panels,
            "inbox": inbox,
            "tls_cert": tls_cert,
        },
    )


@staff_required
def site_delete(request, pk):
    obj = get_object_or_404(Website, pk=pk)
    if request.method == "POST":
        domain = obj.domain
        enqueue_remove(domain)
        obj.delete()
        log_action(request, "site.delete", domain, "")
        messages.success(request, "سایت حذف شد.")
        return redirect("site-list")
    return render(request, "panel/confirm_delete.html", {"object_name": obj.domain, "cancel_url_name": "site-edit", "cancel_pk": pk})


@staff_required
@require_POST
def site_tls(request, pk):
    obj = get_object_or_404(Website, pk=pk)
    log_action(request, "tls.issue", obj.domain, "website")
    messages.info(request, enqueue(obj.domain, Certificate.Kind.WEBSITE, website_id=obj.pk, force=True))
    return redirect("site-edit", pk=pk)


@staff_required
def message_delete(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)
    site_id = msg.website_id
    if request.method == "POST":
        msg.delete()
        messages.success(request, "پیام حذف شد.")
    return redirect("site-edit", pk=site_id)
