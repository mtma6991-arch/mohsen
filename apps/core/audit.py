def log_action(request, action, obj="", message=""):
    from apps.core.models import ActivityLog

    user = getattr(request, "user", None)
    username = ""
    if user is not None and getattr(user, "is_authenticated", False):
        username = user.get_username()
    ActivityLog.objects.create(
        username=username[:150],
        action=str(action)[:80],
        object_repr=str(obj)[:200],
        message=str(message)[:500],
        ip=(request.META.get("REMOTE_ADDR") or "")[:64],
    )
