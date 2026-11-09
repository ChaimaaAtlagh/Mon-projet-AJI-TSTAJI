"""Add legacy Desktop accounts to PostgreSQL without changing source files."""

import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.hashers import LegacyDesktopPBKDF2PasswordHasher
from core.models import Profile, Role, User, UserPreferences, UserRole


PROJECT_ROOT = Path(settings.BASE_DIR).parent
DEFAULT_JSON = PROJECT_ROOT / "data" / "utilisateurs.json"
HEX_16_BYTES = re.compile(r"^[0-9a-fA-F]{32}$")
HEX_32_BYTES = re.compile(r"^[0-9a-fA-F]{64}$")


def _load_records(source):
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise CommandError("Impossible de lire le fichier JSON source.") from exc
    except json.JSONDecodeError as exc:
        raise CommandError("Le fichier JSON source est invalide.") from exc
    if not isinstance(payload, dict):
        raise CommandError("Le fichier JSON source doit contenir un objet d'utilisateurs.")

    records = []
    for email, item in payload.items():
        if not isinstance(email, str) or not isinstance(item, dict):
            raise CommandError("Un enregistrement utilisateur a un format invalide.")
        salt = item.get("sel")
        digest = item.get("hash")
        if not isinstance(salt, str) or not HEX_16_BYTES.fullmatch(salt):
            raise CommandError("Un sel de mot de passe historique est invalide.")
        if not isinstance(digest, str) or not HEX_32_BYTES.fullmatch(digest):
            raise CommandError("Une empreinte de mot de passe historique est invalide.")
        normalized = email.strip().lower()
        if not normalized or len(normalized) > 254 or "@" not in normalized:
            raise CommandError("Une adresse e-mail historique est invalide.")
        name = item.get("nom", "")
        if not isinstance(name, str):
            raise CommandError("Un nom de compte historique est invalide.")
        records.append({
            "email": normalized,
            "display_name": name.strip()[:150],
            "salt": salt.lower(),
            "digest": digest.lower(),
        })
    return records


def _read_sqlite_profiles():
    """Read profile rows only; the SQLite file is opened in read-only mode."""
    sqlite_path = PROJECT_ROOT / "data" / "aji_tstaji.db"
    if not sqlite_path.is_file():
        return {}
    uri = f"file:{quote(sqlite_path.as_posix(), safe='/:')}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        try:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                ("profils_utilisateurs",),
            ).fetchone()
            if not table:
                return {}
            rows = connection.execute("SELECT * FROM profils_utilisateurs").fetchall()
            return {str(row["email"]).strip().lower(): dict(row) for row in rows if row["email"]}
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise CommandError("Impossible de lire les profils SQLite en mode lecture seule.") from exc


def _profile_values(record, sqlite_profile):
    profile = sqlite_profile or {}
    name_parts = record["display_name"].split(maxsplit=1)
    return {
        "first_name": str(profile.get("prenom") or (name_parts[0] if name_parts else ""))[:120],
        "last_name": str(profile.get("nom") or (name_parts[1] if len(name_parts) > 1 else ""))[:120],
        "phone": str(profile.get("telephone") or "")[:64],
        "city": str(profile.get("ville") or "")[:120],
        "diploma": str(profile.get("diplome") or "")[:200],
        "sector": str(profile.get("secteur") or "")[:160],
        "institution": str(profile.get("etablissement") or "")[:200],
        "skills": str(profile.get("competences") or ""),
        "job_search": str(profile.get("recherche") or ""),
    }


def _create_imported_user(record, sqlite_profile):
    hasher = LegacyDesktopPBKDF2PasswordHasher()
    encoded = f"{hasher.algorithm}${hasher.iterations}${record['salt']}${record['digest']}"
    user = User(
        email=record["email"],
        email_normalized=record["email"],
        display_name=record["display_name"],
        password=encoded,
        password_scheme=User.PasswordScheme.LEGACY_PBKDF2,
        status=User.Status.ACTIVE,
        registered_at=timezone.now(),
    )
    user.save(force_insert=True)
    Profile.objects.create(user=user, **_profile_values(record, sqlite_profile))
    UserPreferences.objects.get_or_create(user=user)
    role, _ = Role.objects.get_or_create(
        code=Role.Code.USER,
        defaults={"name": "Utilisateur"},
    )
    UserRole.objects.get_or_create(user=user, role=role)
    return user


class Command(BaseCommand):
    help = "Importe les comptes JSON sans modifier la source ni remplacer un compte existant."

    def add_arguments(self, parser):
        parser.add_argument("--source", type=Path, default=DEFAULT_JSON)
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Effectue l'import. Sans cette option, la commande fait un dry-run.",
        )

    def handle(self, *args, **options):
        source = options["source"].expanduser().resolve()
        if not source.is_file():
            raise CommandError("Le fichier JSON source est introuvable ; aucun compte importé.")
        records = _load_records(source)
        profiles = _read_sqlite_profiles()
        existing_emails = set(
            User.objects.filter(email_normalized__in=[row["email"] for row in records])
            .values_list("email_normalized", flat=True)
        )
        pending = [row for row in records if row["email"] not in existing_emails]
        skipped = len(records) - len(pending)

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY-RUN : {len(pending)} compte(s) à importer, {skipped} déjà présent(s). "
                    "Aucune donnée modifiée. Relancez avec --apply pour importer."
                )
            )
            return

        imported = 0
        with transaction.atomic():
            for record in pending:
                try:
                    # Savepoint keeps an account inserted concurrently from
                    # aborting the rest of this additive import.
                    with transaction.atomic():
                        _create_imported_user(record, profiles.get(record["email"]))
                except IntegrityError:
                    skipped += 1
                    continue
                imported += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Import terminé : {imported} compte(s) ajouté(s), {skipped} ignoré(s). "
                "Le fichier JSON source a été conservé."
            )
        )
