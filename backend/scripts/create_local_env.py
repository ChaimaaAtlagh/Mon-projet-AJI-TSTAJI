"""Create an ignored local backend/.env with fresh development secrets."""

from pathlib import Path
import secrets
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_ROOT / ".env"


def main() -> int:
    if ENV_PATH.exists():
        print("backend/.env existe déjà ; aucun fichier n'a été modifié.")
        return 1

    django_secret = secrets.token_urlsafe(48)
    database_password = secrets.token_urlsafe(36)
    contents = "\n".join(
        (
            f"DJANGO_SECRET_KEY={django_secret}",
            "DJANGO_DEBUG=false",
            "DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost",
            "POSTGRES_DB=aji_tstaji_dev",
            "POSTGRES_USER=aji_dev",
            f"POSTGRES_PASSWORD={database_password}",
            "DB_NAME=aji_tstaji_dev",
            "DB_USER=aji_dev",
            f"DB_PASSWORD={database_password}",
            "DB_HOST=127.0.0.1",
            "DB_PORT=5432",
            "",
        )
    )

    try:
        ENV_PATH.write_text(contents, encoding="utf-8", newline="\n")
    except OSError:
        print("Impossible de créer backend/.env ; aucune valeur secrète affichée.")
        return 2

    print("backend/.env créé avec des secrets aléatoires (valeurs masquées).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

