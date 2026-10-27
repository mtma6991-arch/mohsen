from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.categories.models import Category
from apps.core.access import sync_credentials
from apps.core.audit import log_action
from apps.core.decorators import staff_required
from apps.core.models import ActivityLog, AdminDomain
from apps.plugins.models import PluginPackage
from apps.sites.domains import validate_admin_domain
from apps.sites.models import ContactMessage, Website
from apps.templates_engine.models import TemplatePackage
from apps.tls.models import Certificate
from apps.tls.names import is_public_dns_name
from apps.tls.service import enqueue, enqueue_remove


class PanelAuthForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "نام کاربری"
        self.fields["password"].label = "رمز عبور"


def sync_admin_domains_file() -> None:
    registry = Path("/etc/mohsen/admin-domains.txt")
    try:
        registry.parent.mkdir(parents=True, exist_ok=True)
        names = "\n".join(AdminDomain.objects.values_list("domain", flat=True))
        registry.write_text((names + "\n") if names else "", encoding="utf-8")
    except OSError:
        pass


def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("dashboard")
    form = PanelAuthForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if not user.is_staff:
            form.add_error(None, "این حساب به پنل دسترسی ندارد.")
        else:
            from django.contrib.auth import login

            login(request, user)
            log_action(request, "login", user.username, "ورود به پنل")
            return redirect("dashboard")
    return render(request, "panel/login.html", {"form": form})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        log_action(request, "logout", request.user.username, "خروج")
    logout(request)
    return redirect("login")


@staff_required
def dashboard(request):
    return render(
        request,
        "panel/dashboard.html",
        {
            "counts": {
                "categories": Category.objects.count(),
                "templates": TemplatePackage.objects.count(),
                "plugins": PluginPackage.objects.count(),
                "websites": Website.objects.count(),
                "messages": ContactMessage.objects.count(),
            },
            "websites": Website.objects.select_related("category", "template")[:6],
            "activity": ActivityLog.objects.all()[:8],
            "messages_recent": ContactMessage.objects.select_related("website")[:6],
        },
    )


@staff_required
def settings_view(request):
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        raw = (request.POST.get("domain") or "").strip()
        try:
            if action == "add-panel":
                domain = validate_admin_domain(raw)
                AdminDomain.objects.filter(is_primary=True).update(is_primary=False)
                AdminDomain.objects.update_or_create(
                    domain=domain, defaults={"is_primary": True, "note": "ثبت از تنظیمات پنل"}
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
                        f"دامنه {domain} ثبت شد. برای آی‌پی یا دامنه محلی گواهی عمومی صادر نمی‌شود.",
                    )
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
                    messages.success(request, f"دامنه {domain} حذف شد.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("settings")

    return render(
        request,
        "panel/settings.html",
        {"domains": AdminDomain.objects.all(), "debug": settings.DEBUG},
    )


@staff_required
def activity_view(request):
    return render(request, "panel/activity.html", {"logs": ActivityLog.objects.all()[:200]})


@staff_required
def password_view(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    form.fields["old_password"].label = "رمز فعلی"
    form.fields["new_password1"].label = "رمز جدید"
    form.fields["new_password2"].label = "تکرار رمز جدید"
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        log_action(request, "password", user.username, "تغییر رمز پنل")
        messages.success(request, "رمز عبور عوض شد.")
        return redirect("settings")
    return render(request, "panel/password.html", {"form": form})


@staff_required
def guide_template(request):
    from apps.architect.catalog import ELEMENTS, GROUPS

    return render(request, "panel/guides/template.html", {"elements": ELEMENTS, "groups": GROUPS})


@staff_required
def guide_plugin(request):
    return render(request, "panel/guides/plugin.html")
