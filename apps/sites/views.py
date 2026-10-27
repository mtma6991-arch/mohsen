from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.audit import log_action
from apps.core.decorators import staff_required
from apps.plugins.loader import iter_site_plugins
from apps.sites.forms import WebsiteForm
from apps.sites.models import ContactMessage, Website
from apps.templates_engine.models import TemplatePackage


def _template_map():
    rows = TemplatePackage.objects.filter(is_active=True).values("id", "name", "category_id", "version")
    return list(rows)


@staff_required
def site_list(request):
    q = (request.GET.get("q") or "").strip()
    rows = Website.objects.select_related("category", "template")
    if q:
        rows = rows.filter(domain__icontains=q) | rows.filter(customer_name__icontains=q) | rows.filter(title__icontains=q)
        rows = rows.distinct()
    return render(request, "panel/sites/list.html", {"rows": rows, "q": q})


@staff_required
def site_create(request):
    form = WebsiteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        log_action(request, "site.create", obj.domain, obj.customer_name)
        messages.success(request, "سایت ثبت شد. با اشاره دادن DNS دامنه به این سرور، سایت باز می‌شود.")
        return redirect("site-edit", pk=obj.pk)
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

    form = WebsiteForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "site.update", obj.domain, obj.title)
        messages.success(request, "سایت به‌روز شد.")
        return redirect("site-edit", pk=pk)

    panels = []
    for _row, inst in iter_site_plugins(obj):
        try:
            panel = inst.admin_panel(request, obj)
        except Exception as exc:
            panel = {"title": inst.name or inst.slug, "html": f"<p>خطا در پنل افزونه: {exc}</p>"}
        if panel:
            panels.append(panel)
    inbox = obj.messages.all()[:30]
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
        },
    )


@staff_required
def site_delete(request, pk):
    obj = get_object_or_404(Website, pk=pk)
    if request.method == "POST":
        domain = obj.domain
        obj.delete()
        log_action(request, "site.delete", domain, "")
        messages.success(request, "سایت حذف شد.")
        return redirect("site-list")
    return render(request, "panel/confirm_delete.html", {"object_name": obj.domain, "cancel_url_name": "site-edit", "cancel_pk": pk})


@staff_required
def message_delete(request, pk):
    msg = get_object_or_404(ContactMessage, pk=pk)
    site_id = msg.website_id
    if request.method == "POST":
        msg.delete()
        messages.success(request, "پیام حذف شد.")
    return redirect("site-edit", pk=site_id)
