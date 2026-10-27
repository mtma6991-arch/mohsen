from .base import *  # noqa: F403

DEBUG = True
SECRET_KEY = env("MOHSEN_SECRET_KEY", "dev-secret-key-not-for-production-0001")  # noqa: F405
WEB_PASS = env("MOHSEN_WEB_PASS", "panel").strip().strip("/") or "panel"  # noqa: F405
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405
DATA_DIR = BASE_DIR / "data"  # noqa: F405
DATA_DIR.mkdir(exist_ok=True)
(MEDIA_ROOT).mkdir(exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
        "OPTIONS": {"timeout": 20},
    }
}

WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

LOGIN_URL = f"/{WEB_PASS}/login/"
LOGIN_REDIRECT_URL = f"/{WEB_PASS}/"
LOGOUT_REDIRECT_URL = f"/{WEB_PASS}/login/"
