from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from apps.categories.forms import CategoryForm
from apps.categories.models import Category
from apps.core.audit import log_action
from apps.core.decorators import staff_required
from apps.plugins.models import CategoryPlugin, PluginPackage


@staff_required
def category_list(request):
    q = (request.GET.get("q") or "").strip()
    rows = Category.objects.annotate(
        n_sites=Count("websites", distinct=True),
        n_templates=Count("templates", distinct=True),
        n_plugins=Count("category_plugins", distinct=True),
    )
    if q:
        rows = rows.filter(name__icontains=q)
    return render(request, "panel/categories/list.html", {"rows": rows, "q": q})


@staff_required
def category_create(request):
    form = CategoryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        log_action(request, "category.create", obj.name, obj.slug)
        messages.success(request, "دسته ساخته شد.")
        return redirect("category-list")
    return render(request, "panel/categories/form.html", {"form": form, "mode": "create"})


@staff_required
def category_edit(request, pk):
    obj = get_object_or_404(Category, pk=pk)
    form = CategoryForm(request.POST or None, instance=obj)
    plugins = PluginPackage.objects.filter(is_active=True)
    assigned = set(obj.category_plugins.filter(enabled=True).values_list("plugin_id", flat=True))
    if request.method == "POST" and request.POST.get("form") == "plugins":
        chosen = {int(x) for x in request.POST.getlist("plugins") if x.isdigit()}
        for plugin in plugins:
            if plugin.id in chosen:
                CategoryPlugin.objects.update_or_create(
                    category=obj, plugin=plugin, defaults={"enabled": True}
                )
            else:
                CategoryPlugin.objects.filter(category=obj, plugin=plugin).delete()
        log_action(request, "category.plugins", obj.name, f"{len(chosen)} افزونه")
        messages.success(request, "افزونه‌های دسته ذخیره شد. همه سایت‌های این دسته همان افزونه‌ها را دارند.")
        return redirect("category-edit", pk=obj.pk)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request, "category.update", obj.name, obj.slug)
        messages.success(request, "دسته به‌روز شد.")
        return redirect("category-list")
    return render(
        request,
        "panel/categories/form.html",
        {"form": form, "mode": "edit", "obj": obj, "plugins": plugins, "assigned": assigned},
    )


@staff_required
def category_delete(request, pk):
    obj = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        if obj.websites.exists() or obj.templates.exists():
            messages.error(request, "دسته دارای سایت یا قالب است و حذف نمی‌شود.")
            return redirect("category-edit", pk=pk)
        name = obj.name
        obj.delete()
        log_action(request, "category.delete", name, "")
        messages.success(request, "دسته حذف شد.")
        return redirect("category-list")
    return render(request, "panel/confirm_delete.html", {"object_name": obj.name, "cancel": "category-list"})
