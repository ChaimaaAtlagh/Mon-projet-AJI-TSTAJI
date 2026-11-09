from pathlib import PurePath

from django.core.exceptions import ValidationError


MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc"}
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}


def validate_document_size(value: int) -> None:
    if value <= 0:
        raise ValidationError("Le fichier doit contenir des données.")
    if value > MAX_DOCUMENT_BYTES:
        raise ValidationError("La taille maximale est de 10 MiB.")


def validate_document_name(value: str) -> None:
    suffix = PurePath(value).suffix.lower()
    if suffix not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError("Format accepté : PDF, DOCX ou DOC.")


def validate_document_type(value: str) -> None:
    if value not in ALLOWED_DOCUMENT_TYPES:
        raise ValidationError("Type de document non accepté.")

