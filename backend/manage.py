#!/usr/bin/env python
"""Django management entry point for the isolated backend."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aji_api.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is unavailable. Install backend/requirements.txt in the backend venv."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

