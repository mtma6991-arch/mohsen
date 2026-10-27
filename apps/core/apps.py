import atexit
import os

from django.apps import AppConfig


def _fix_sqlite_perms():
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        return
    try:
        from apps.tls.service import _restore_db_owner

        _restore_db_owner()
    except Exception:
        pass


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "هسته"

    def ready(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            atexit.register(_fix_sqlite_perms)
