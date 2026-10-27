from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.architect.catalog import BY_ID, GROUPS
from apps.architect.document import load_architect
from apps.core.audit import log_action
from apps.core.decorators import staff_required
from apps.sites.models import Website


@staff_required
def site_memar(request, pk):
    website = get_object_or_404(Website, pk=pk)
    root = website.template.extracted_path
    document = load_architect(root)
    nodes = [item for item in document.get("nodes") or [] if isinstance(item, dict)]
    if request.method == "POST":
        saved = {}
        for node in nodes:
            uid = str(node.get("uid") or "")
            spec = BY_ID.get(str(node.get("id") or ""))
            if not uid or spec is None:
                continue
            bucket = {}
            for field in spec["settings"]:
                key = field["key"]
                raw = request.POST.get(f"{uid}__{key}")
                if raw is None:
                    continue
                value = str(raw).strip()
                if value:
                    bucket[key] = value[:4000]
            if bucket:
                saved[uid] = bucket
        settings = dict(website.settings or {})
        settings["memar"] = saved
        website.settings = settings
        website.save(update_fields=["settings", "updated_at"])
        log_action(request, "site.memar", website.domain, f"{len(saved)} المان")
        messages.success(request, "ویرایش معمار ذخیره شد و روی سایت مشتری اعمال می‌شود.")
        return redirect("site-memar", pk=pk)

    overrides = {}
    raw_over = (website.settings or {}).get("memar") or {}
    if isinstance(raw_over, dict):
        overrides = raw_over
    pages = _pages(website, nodes, overrides)
    return render(
        request,
        "panel/sites/memar.html",
        {
            "obj": website,
            "pages": pages,
            "groups": GROUPS,
            "node_count": len(nodes),
            "ready": bool(nodes) and document.get("builder") == "memar",
        },
    )


def _pages(website, nodes, overrides):
    titles = {"layout": "اسکلت قالب"}
    for page in (website.template.manifest or {}).get("pages") or []:
        titles[page.get("slug")] = page.get("title") or page.get("slug")
    order = []
    buckets = {}
    for node in nodes:
        uid = str(node.get("uid") or "")
        element_id = str(node.get("id") or "")
        spec = BY_ID.get(element_id)
        if spec is None or not uid:
            continue
        page = str(node.get("page") or "layout")
        if page not in buckets:
            buckets[page] = []
            order.append(page)
        current = overrides.get(uid) if isinstance(overrides.get(uid), dict) else {}
        fields = []
        for field in spec["settings"]:
            fields.append(
                {
                    "key": field["key"],
                    "label": field["label"],
                    "type": field["type"],
                    "options": field.get("options") or [],
                    "value": current.get(field["key"], ""),
                }
            )
        buckets[page].append(
            {
                "uid": uid,
                "id": element_id,
                "name": spec["name"],
                "group": spec["group"],
                "parent": node.get("parent") or "",
                "fields": fields,
            }
        )
    return [{"slug": slug, "title": titles.get(slug) or slug, "nodes": buckets[slug]} for slug in order]
