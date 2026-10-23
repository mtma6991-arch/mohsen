from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.categories.models import Category
from apps.core.audit import log_action
from apps.core.decorators import staff_required
from apps.core.models import ActivityLog, AdminDomain
from apps.plugins.models import PluginPackage
from apps.sites.models import ContactMessage, Website
from apps.templates_engine.models import TemplatePackage


class PanelAuthForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "نام کاربری"
        self.fields["password"].label = "رمز عبور"


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
