from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import env

DEBUG = False
SECRET_KEY = env("MOHSEN_SECRET_KEY", "")
if not SECRET_KEY or SECRET_KEY.startswith("dev-"):
    raise ImproperlyConfigured("MOHSEN_SECRET_KEY در محیط تولید الزامی است.")

WEB_PASS = env("MOHSEN_WEB_PASS", "").strip().strip("/")
if not WEB_PASS:
    raise ImproperlyConfigured("MOHSEN_WEB_PASS در محیط تولید الزامی است.")

DATA_DIR = Path(env("MOHSEN_DATA_DIR", "/var/lib/mohsen"))  # noqa: F405
MEDIA_ROOT = Path(env("MOHSEN_MEDIA_ROOT", str(DATA_DIR / "media")))
STATIC_ROOT = Path(env("MOHSEN_STATIC_ROOT", "/opt/mohsen/staticfiles"))

_db_url = env("DATABASE_URL", "").strip()
if _db_url.startswith("postgres://") or _db_url.startswith("postgresql://"):
    from urllib.parse import urlparse

    parsed = urlparse(_db_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": (parsed.path or "/mohsen").lstrip("/"),
            "USER": parsed.username or "mohsen",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "127.0.0.1",
            "PORT": str(parsed.port or 5432),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(DATA_DIR / "db.sqlite3"),
            "OPTIONS": {"timeout": 20},
        }
    }

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

LOGIN_URL = f"/{WEB_PASS}/login/"
LOGIN_REDIRECT_URL = f"/{WEB_PASS}/"
LOGOUT_REDIRECT_URL = f"/{WEB_PASS}/login/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False}},
}
