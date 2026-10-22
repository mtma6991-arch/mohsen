import io
import zipfile
from pathlib import Path

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.categories.models import Category
from apps.core.audit import log_action
from apps.core.decorators import staff_required
from apps.core.zipsafe import ZipRejected
from apps.plugins.loader import get_plugin_instance
from apps.plugins.models import CategoryPlugin, PluginPackage
from apps.plugins.services import store_plugin


def _zip_directory(root: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in root.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                zf.write(path, path.relative_to(root).as_posix())
    return buf.getvalue()


@staff_required
def plugin_list(request):
    q = (request.GET.get("q") or "").strip()
    rows = PluginPackage.objects.all()
    if q:
        rows = rows.filter(name__icontains=q)
    return render(request, "panel/plugins/list.html", {"rows": rows, "q": q})


@staff_required
def plugin_upload(request):
    error = ""
    if request.method == "POST":
        upload = request.FILES.get("archive")
        if upload is None:
            error = "فایل زیپ افزونه را انتخاب کنید."
        else:
            try:
                obj, created = store_plugin(raw=upload.read(), filename=upload.name)
            except ZipRejected as exc:
                error = str(exc)
            else:
                log_action(request, "plugin.upload", obj.slug, "ایجاد" if created else "به‌روزرسانی")
                messages.success(request, "افزونه در مرکز افزونه ثبت شد." if created else "افزونه به‌روز شد.")
                return redirect("plugin-detail", pk=obj.pk)
    return render(request, "panel/plugins/form.html", {"error": error})


@staff_required
def plugin_detail(request, pk):
    obj = get_object_or_404(PluginPackage, pk=pk)
    categories = list(Category.objects.filter(is_active=True))
    assignments = {row.category_id: row for row in obj.assignments.select_related("category")}
    instance = None
    load_error = ""
    try:
        instance = get_plugin_instance(obj)
    except Exception as exc:
        load_error = str(exc)

    if request.method == "POST" and request.POST.get("form") == "assign":
        chosen = {int(x) for x in request.POST.getlist("categories") if str(x).isdigit()}
        for category in categories:
            if category.id in chosen:
                CategoryPlugin.objects.update_or_create(
                    category=category, plugin=obj, defaults={"enabled": True}
                )
            else:
                CategoryPlugin.objects.filter(category=category, plugin=obj).delete()
        log_action(request, "plugin.assign", obj.slug, f"{len(chosen)} دسته")
        messages.success(request, "افزونه روی دسته‌های انتخاب‌شده فعال شد. همه وب‌سایت‌های آن دسته‌ها این افزونه را دارند.")
        return redirect("plugin-detail", pk=pk)

    if request.method == "POST" and request.POST.get("_plugin") and instance is not None:
        category = Category.objects.filter(pk=request.POST.get("_category") or 0).first()
        assignment = assignments.get(getattr(category, "id", None))
        if category and assignment:
            try:
                instance.handle_category_post(request, category, assignment)
                log_action(request, "plugin.category-settings", obj.slug, category.slug)
                messages.success(request, "تنظیمات پیش‌فرض دسته ذخیره شد.")
            except Exception as exc:
                messages.error(request, f"ذخیره تنظیمات افزونه ناموفق بود: {exc}")
        return redirect("plugin-detail", pk=pk)

    panels = []
    if instance is not None:
        for category in categories:
            assignment = assignments.get(category.id)
            if not assignment:
                continue
            try:
                panel = instance.category_admin_panel(request, category, assignment)
            except Exception as exc:
                panel = {"title": category.name, "html": f"<p>خطای پنل افزونه: {exc}</p>"}
            if panel:
                panels.append(panel)

    root = Path(obj.extracted_path)
    files = []
    if root.is_dir():
        files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())[:300]
    return render(
        request,
        "panel/plugins/detail.html",
        {
            "obj": obj,
            "categories": categories,
            "assigned_ids": set(assignments),
            "panels": panels,
            "files": files,
            "load_error": load_error,
        },
    )


@staff_required
def plugin_toggle(request, pk):
    obj = get_object_or_404(PluginPackage, pk=pk)
    if request.method == "POST":
        obj.is_active = not obj.is_active
        obj.save(update_fields=["is_active", "updated_at"])
        log_action(request, "plugin.toggle", obj.slug, "فعال" if obj.is_active else "غیرفعال")
        messages.success(request, "وضعیت افزونه عوض شد.")
    return redirect("plugin-detail", pk=pk)


@staff_required
def plugin_delete(request, pk):
    obj = get_object_or_404(PluginPackage, pk=pk)
    if request.method == "POST":
        slug = obj.slug
        root = Path(obj.extracted_path)
        obj.delete()
        if root.is_dir() and root.parent.name == "plugins":
            import shutil

            shutil.rmtree(root, ignore_errors=True)
        log_action(request, "plugin.delete", slug, "")
        messages.success(request, "افزونه حذف شد.")
        return redirect("plugin-list")
    return render(request, "panel/confirm_delete.html", {"object_name": obj.name, "cancel_url_name": "plugin-detail", "cancel_pk": pk})


@staff_required
def example_plugin_download(request, name):
    from django.conf import settings as dj_settings

    mapping = {"sms": "sms", "page-builder": "page-builder"}
    folder = mapping.get(name)
    if not folder:
        raise Http404()
    root = Path(dj_settings.BASE_DIR) / "examples" / "plugins" / folder
    if not root.is_dir():
        raise Http404()
    return FileResponse(io.BytesIO(_zip_directory(root)), as_attachment=True, filename=f"{folder}.zip")
