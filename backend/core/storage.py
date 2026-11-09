"""Private local document storage used only by the development backend."""

from pathlib import Path

from django.conf import settings


class PrivateDocumentError(Exception):
    """Raised when a private document key is invalid or unavailable."""


def document_path(storage_key: str) -> Path:
    root = Path(settings.PRIVATE_DOCUMENT_ROOT).resolve()
    target = (root / storage_key).resolve()
    if target == root or root not in target.parents:
        raise PrivateDocumentError("Invalid private document key")
    return target


def open_private_document(storage_key: str):
    path = document_path(storage_key)
    try:
        return path.open("rb")
    except OSError as exc:
        raise PrivateDocumentError("Private document unavailable") from exc

