import logging

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect

from apps.plugins.loader import iter_site_plugins
from apps.sites.models import ContactMessage, Website
from apps.sites.rendering import render_page, serve_asset

logger = logging.getLogger(__name__)


def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def page_not_found(request, exception):
    return render(request, "public/platform_message.html", {"title": "پیدا نشد", "body": "این مسیر وجود ندارد."}, status=404)


def server_error(request):
    return render(request, "public/platform_message.html", {"title": "خطای سرور", "body": "درخواست انجام نشد."}, status=500)


def _dispatch(request, website, rest, url_prefix):
    rest = (rest or "").strip("/")
    request.tenant = website
    request.url_prefix = url_prefix
    if rest.startswith("assets/"):
        return serve_asset(website, rest[len("assets/"):])
    if rest.startswith("_mohsen/form/"):
        name = rest[len("_mohsen/form/"):].strip("/")
        return handle_form(request, website, name or "contact", url_prefix)
    if rest == "":
        page_slug = ""
    else:
        if "/" in rest:
            raise Http404()
        page_slug = rest
    return render_page(request, website, page_slug, url_prefix=url_prefix)


def front(request, rest=""):
    website = getattr(request, "tenant", None)
    if website is None:
        if (rest or "").strip("/") == "":
            return render(request, "public/unconfigured.html")
        return render(request, "public/platform_message.html", {"title": "دامنه ثبت نشده", "body": "برای این میزبان سایتی تعریف نشده است."}, status=404)
    return _dispatch(request, website, rest, "")


def preview(request, domain, rest=""):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect(settings.LOGIN_URL)
    website = get_object_or_404(Website.objects.select_related("category", "template"), domain=domain)
    return _dispatch(request, website, rest, f"/_preview/{website.domain}")


@csrf_protect
def handle_form(request, website, name, url_prefix):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if website.status != Website.Status.ACTIVE and not request.user.is_staff:
        return HttpResponse("سایت فعال نیست.", status=403)
    if request.POST.get("company_website"):
        return _form_redirect(url_prefix)
    ip = request.META.get("REMOTE_ADDR") or "-"
    cache_key = f"mohsen-form:{website.id}:{ip}"
    count = cache.get(cache_key, 0)
    if count >= 8:
        return HttpResponse("تعداد ارسال بیش از حد است. کمی بعد دوباره تلاش کنید.", status=429)
    cache.set(cache_key, count + 1, 600)
    data = {
        "name": (request.POST.get("name") or "").strip()[:160],
        "phone": (request.POST.get("phone") or "").strip()[:40],
        "email": (request.POST.get("email") or "").strip()[:180],
        "message": (request.POST.get("message") or "").strip()[:4000],
    }
    if not data["name"] or not data["message"]:
        return HttpResponse("نام و متن پیام لازم است.", status=400)
    ContactMessage.objects.create(
        website=website,
        name=data["name"],
        phone=data["phone"],
        email=data["email"],
        body=data["message"],
        meta={"form": name[:40]},
    )
    for _row, inst in iter_site_plugins(website):
        try:
            inst.on_form_submit(website, name, data)
        except Exception:
            logger.exception("plugin form hook failed")
    return _form_redirect(url_prefix)


def _form_redirect(url_prefix):
    prefix = (url_prefix or "").rstrip("/")
    target = f"{prefix}/contact/?sent=1" if prefix else "/contact/?sent=1"
    return redirect(target)
