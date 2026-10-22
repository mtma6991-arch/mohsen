import logging
from pathlib import Path

from django.http import Http404, HttpResponse
from django.shortcuts import render
from jinja2 import FileSystemLoader, TemplateError, Undefined
from jinja2.sandbox import SandboxedEnvironment
from markupsafe import Markup

from apps.plugins.loader import iter_site_plugins

logger = logging.getLogger(__name__)


class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args, **kwargs):
        return ""

    def __str__(self):
        return ""

    def __iter__(self):
        return iter(())

    def __bool__(self):
        return False


def site_payload(website):
    return {
        "id": website.id,
        "customer_name": website.customer_name,
        "domain": website.domain,
        "title": website.title,
        "tagline": website.tagline,
        "description": website.description,
        "phone": website.phone,
        "email": website.email,
        "address": website.address,
        "logo_text": website.logo_text or website.title,
        "accent_color": website.accent_color or website.category.color,
        "category": website.category.name,
        "category_slug": website.category.slug,
        "status": website.status,
    }


def merged_demo_data(website):
    manifest = website.template.manifest or {}
    base = dict(manifest.get("demo_data") or {})
    override = (website.settings or {}).get("content") or {}
    if isinstance(override, dict):
        base.update(override)
    return base


def build_environment(root: Path, url_prefix: str):
    prefix = url_prefix.rstrip("/")

    def asset(path=""):
        rel = str(path or "").lstrip("/")
        return f"{prefix}/assets/{rel}"

    def page_url(slug=""):
        slug = str(slug or "").strip("/")
        home = ""
        if not slug or slug == "home":
            return f"{prefix}/" or "/"
        return f"{prefix}/{slug}/"

    def form_action(name="contact"):
        name = str(name or "contact").strip("/")
        return f"{prefix}/_mohsen/form/{name}/"

    env = SandboxedEnvironment(
        loader=FileSystemLoader(str(root)),
        autoescape=True,
        undefined=SilentUndefined,
    )
    env.globals["asset"] = asset
    env.globals["page_url"] = page_url
    env.globals["form_action"] = form_action
    return env, page_url


def plugin_contexts(website, request):
    bag = {}
    heads = []
    for _row, inst in iter_site_plugins(website):
        try:
            ctx = inst.site_context(website, request) or {}
        except Exception:
            logger.exception("site_context failed for %s", getattr(inst, "slug", "?"))
            ctx = {}
        slug = getattr(inst, "slug", "") or ""
        if slug:
            bag[slug] = ctx
            bag[slug.replace("-", "_")] = ctx
        try:
            head = inst.head_html(website, request) or ""
        except Exception:
            logger.exception("head_html failed")
            head = ""
        if head:
            heads.append(str(head))
    return bag, Markup("\n".join(heads))


def render_page(request, website, page_slug, url_prefix=""):
    if website.status == website.Status.SUSPENDED:
        return render(request, "public/suspended.html", {"website": website}, status=423)
    if website.status == website.Status.DRAFT and not request.user.is_staff:
        return render(request, "public/suspended.html", {"website": website, "draft": True}, status=403)
    template = website.template
    if not template.is_active:
        return render(request, "public/platform_message.html", {"title": "قالب غیرفعال است", "body": "قالب این سایت توسط مدیر غیرفعال شده است."}, status=503)
    root = Path(template.extracted_path)
    manifest = template.manifest or {}
    if not root.is_dir() or not (root / "template.json").is_file():
        return render(request, "public/platform_message.html", {"title": "قالب پیدا نشد", "body": "فایل‌های قالب روی سرور موجود نیست."}, status=500)
    pages = list(manifest.get("pages") or [])
    home = manifest.get("homepage") or (pages[0]["slug"] if pages else "home")
    if not page_slug:
        page_slug = home
    page = next((item for item in pages if item.get("slug") == page_slug), None)
    if page is None:
        raise Http404("صفحه در قالب تعریف نشده است.")
    env, page_url = build_environment(root, url_prefix)
    # Fix page_url so the manifest homepage also maps to root, not only "home".
    prefix = url_prefix.rstrip("/")

    def smart_page_url(slug=""):
        slug = str(slug or "").strip("/")
        if not slug or slug == home:
            return f"{prefix}/" if prefix else "/"
        return f"{prefix}/{slug}/"

    env.globals["page_url"] = smart_page_url
    plugins, head_html = plugin_contexts(website, request)
    context = {
        "site": site_payload(website),
        "page": {"slug": page["slug"], "title": page.get("title") or "", "file": page.get("file") or ""},
        "pages": pages,
        "data": merged_demo_data(website),
        "plugins": plugins,
        "plugins_head": head_html,
        "csrf_token": request.META.get("CSRF_COOKIE") or "",
        "sent": request.GET.get("sent") == "1",
        "url_prefix": prefix,
    }
    # Ensure a csrf cookie exists for public forms.
    from django.middleware.csrf import get_token

    context["csrf_token"] = get_token(request)
    try:
        html = env.get_template(page["file"]).render(context)
    except TemplateError as exc:
        logger.exception("template render failed for %s", website.domain)
        return render(
            request,
            "public/platform_message.html",
            {"title": "خطای قالب", "body": "قالب این صفحه خطا دارد. جزئیات در گزارش سرور ثبت شد.", "detail": str(exc) if request.user.is_staff else ""},
            status=500,
        )
    return HttpResponse(html)


def serve_asset(website, relative: str):
    from django.utils._os import safe_join

    rel = (relative or "").lstrip("/")
    if not rel or ".." in Path(rel).parts:
        raise Http404()
    root = Path(website.template.extracted_path) / "assets"
    try:
        path = Path(safe_join(str(root), rel))
    except Exception as exc:
        raise Http404() from exc
    if not path.is_file():
        raise Http404()
    content_types = {
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".json": "application/json; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
        ".webmanifest": "application/manifest+json",
    }
    data = path.read_bytes()
    response = HttpResponse(data, content_type=content_types.get(path.suffix.lower(), "application/octet-stream"))
    response["Cache-Control"] = "public, max-age=3600"
    return response
