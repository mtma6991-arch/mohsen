from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def staff_required(view):
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if not user.is_staff:
            return redirect(settings.LOGIN_URL)
        return view(request, *args, **kwargs)

    return _wrapped
