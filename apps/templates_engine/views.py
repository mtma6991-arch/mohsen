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
from apps.templates_engine.models import TemplatePackage
from apps.templates_engine.services import store_template


def _zip_directory(root: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in root.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                zf.write(path, path.relative_to(root).as_posix())
    return buf.getvalue()


@staff_required
def template_list(request):
    q = (request.GET.get("q") or "").strip()
    rows = TemplatePackage.objects.select_related("category")
    if q:
        rows = rows.filter(name__icontains=q)
    return render(
        request,
        "panel/templates/list.html",
        {"rows": rows, "q": q, "categories": Category.objects.filter(is_active=True)},
    )


@staff_required
def template_upload(request):
    categories = Category.objects.filter(is_active=True)
    error = ""
    if request.method == "POST":
        category = categories.filter(pk=request.POST.get("category") or 0).first()
        upload = request.FILES.get("archive")
        if category is None:
            error = "دسته را انتخاب کنید."
        elif upload is None:
            error = "فایل زیپ را انتخاب کنید."
        else:
            try:
                obj, created = store_template(raw=upload.read(), category=category, filename=upload.name)
            except ZipRejected as exc:
                error = str(exc)
            else:
                log_action(request, "template.upload", obj.slug, "ایجاد" if created else "به‌روزرسانی")
                messages.success(request, "قالب ثبت شد." if created else "نسخه قالب به‌روز شد.")
                return redirect("template-detail", pk=obj.pk)
    return render(request, "panel/templates/form.html", {"categories": categories, "error": error})


@staff_required
def template_detail(request, pk):
    obj = get_object_or_404(TemplatePackage.objects.select_related("category"), pk=pk)
    root = Path(obj.extracted_path)
    files = []
    if root.is_dir():
        files = sorted(
            p.relative_to(root).as_posix()
            for p in root.rglob("*")
            if p.is_file()
        )[:400]
    return render(request, "panel/templates/detail.html", {"obj": obj, "files": files})


@staff_required
def template_toggle(request, pk):
    obj = get_object_or_404(TemplatePackage, pk=pk)
    if request.method == "POST":
        obj.is_active = not obj.is_active
        obj.save(update_fields=["is_active", "updated_at"])
        log_action(request, "template.toggle", obj.slug, "فعال" if obj.is_active else "غیرفعال")
        messages.success(request, "وضعیت قالب عوض شد.")
    return redirect("template-detail", pk=pk)


@staff_required
def template_delete(request, pk):
    obj = get_object_or_404(TemplatePackage, pk=pk)
    if request.method == "POST":
        if obj.websites.exists():
            messages.error(request, "این قالب روی حداقل یک سایت است و حذف نمی‌شود.")
            return redirect("template-detail", pk=pk)
        slug = obj.slug
        root = Path(obj.extracted_path)
        obj.delete()
        if root.is_dir() and root.parent.name == "templates":
            import shutil

            shutil.rmtree(root, ignore_errors=True)
        log_action(request, "template.delete", slug, "")
        messages.success(request, "قالب حذف شد.")
        return redirect("template-list")
    return render(request, "panel/confirm_delete.html", {"object_name": obj.name, "cancel_url_name": "template-detail", "cancel_pk": pk})


@staff_required
def template_download(request, pk):
    obj = get_object_or_404(TemplatePackage, pk=pk)
    if not obj.archive:
        raise Http404()
    return FileResponse(obj.archive.open("rb"), as_attachment=True, filename=f"{obj.slug}.zip")


@staff_required
def example_download(request, name):
    from django.conf import settings as dj_settings

    mapping = {
        "jewelry": "jewelry-atelier",
        "phones": "silver-phones",
    }
    folder = mapping.get(name)
    if not folder:
        raise Http404()
    root = Path(dj_settings.BASE_DIR) / "examples" / "templates" / folder
    if not root.is_dir():
        raise Http404()
    payload = _zip_directory(root)
    return FileResponse(io.BytesIO(payload), as_attachment=True, filename=f"{folder}.zip")
