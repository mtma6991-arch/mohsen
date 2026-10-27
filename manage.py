#!/usr/bin/env python3
import os
import sys


def main():
    try:
        from apps.core.envfile import load_env_into_os

        load_env_into_os()
    except Exception:
        pass
    if os.environ.get("MOHSEN_SECRET_KEY"):
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django نصب نیست. ابتدا محیط مجازی بسازید و requirements.txt را نصب کنید."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
