"""Back up and copy legacy AJI TSTAJI data to the per-user Windows location.

The operation never edits or removes the source. It snapshots SQLite with the
SQLite backup API, preserves every other file under the source data directory,
copies existing CVs referenced outside that directory, and updates only those
paths in the copied database. The schema and row counts remain unchanged.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


DB_NAME = "aji_tstaji.db"
SIDECAR_SUFFIXES = ("-wal", "-shm", "-journal")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def connect_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def database_info(path: Path) -> dict[str, Any]:
    with closing(connect_read_only(path)) as connection:
        integrity = [row[0] for row in connection.execute("PRAGMA integrity_check")]
        foreign_key_issues = list(connection.execute("PRAGMA foreign_key_check"))
        schema = [
            tuple(row)
            for row in connection.execute(
                """SELECT type, name, tbl_name, sql
                   FROM sqlite_master
                   WHERE name NOT LIKE 'sqlite_%'
                   ORDER BY type, name"""
            )
        ]
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        counts = {
            table: connection.execute(
                f'SELECT COUNT(*) FROM "{table.replace(chr(34), chr(34) * 2)}"'
            ).fetchone()[0]
            for table in tables
        }
    return {
        "integrity_check": integrity,
        "foreign_key_issue_count": len(foreign_key_issues),
        "schema": schema,
        "row_counts": counts,
    }


def referenced_cvs(database: Path, project_root: Path) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []
    with closing(connect_read_only(database)) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for table in ("profil", "profils_utilisateurs"):
            if table not in tables:
                continue
            columns = {
                row[1]
                for row in connection.execute(f'PRAGMA table_info("{table}")')
            }
            if "cv_chemin" not in columns:
                continue
            rows = connection.execute(
                f'SELECT rowid, cv_chemin FROM "{table}" '
                "WHERE cv_chemin IS NOT NULL AND trim(cv_chemin) <> ''"
            ).fetchall()
            for rowid, raw_path in rows:
                source_path = Path(raw_path).expanduser()
                if not source_path.is_absolute():
                    source_path = project_root / source_path
                references.append(
                    {
                        "table": table,
                        "rowid": rowid,
                        "raw_path": raw_path,
                        "source_path": source_path.resolve(strict=False),
                    }
                )
    return references


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve())
        return True
    except ValueError:
        return False


def copy_source_data(source: Path, backup_data: Path, backup_sidecars: Path) -> None:
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if path.is_symlink():
            raise RuntimeError(f"Lien symbolique inattendu dans les données : {relative}")
        if path.is_dir():
            (backup_data / relative).mkdir(parents=True, exist_ok=True)
            continue
        if not path.is_file():
            continue
        if relative.as_posix() == DB_NAME:
            continue
        if path.name.startswith(DB_NAME) and path.name.endswith(SIDECAR_SUFFIXES):
            backup_sidecars.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup_sidecars / path.name)
            continue
        destination = backup_data / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def snapshot_database(source_db: Path, snapshot_db: Path) -> None:
    source = connect_read_only(source_db)
    destination = sqlite3.connect(snapshot_db)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def copy_external_documents(
    references: list[dict[str, Any]], backup_external: Path
) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    unique_sources: dict[str, Path] = {}
    missing: list[dict[str, Any]] = []
    for reference in references:
        path = reference["source_path"]
        key = os.path.normcase(str(path))
        if key in unique_sources:
            continue
        if not path.is_file():
            missing.append(reference)
            continue
        if not within(path, backup_external.parent.parent.parent):
            unique_sources[key] = path

    backup_external.mkdir(parents=True, exist_ok=True)
    copied: dict[str, Path] = {}
    for index, (key, source_path) in enumerate(unique_sources.items(), start=1):
        destination = backup_external / f"document_{index:03d}{source_path.suffix.lower()}"
        shutil.copy2(source_path, destination)
        copied[key] = destination
    return copied, missing


def prepare_migration_tree(
    backup_data: Path,
    staging: Path,
    references: list[dict[str, Any]],
    source_data: Path,
    project_root: Path,
    target: Path,
    backup_external: Path,
    external_backup_map: dict[str, Path],
) -> tuple[dict[str, str], int, int]:
    shutil.copytree(backup_data, staging)
    destination_docs = staging / "reports" / "documents_candidat"
    destination_docs.mkdir(parents=True, exist_ok=True)

    path_map: dict[str, str] = {}
    missing_count = 0
    changed_rows = 0
    for reference in references:
        source_path: Path = reference["source_path"]
        key = os.path.normcase(str(source_path))
        if not source_path.is_file():
            missing_count += 1
            continue

        if within(source_path, source_data):
            final_path = target / source_path.relative_to(source_data)
        else:
            if key not in path_map:
                archived = external_backup_map.get(key)
                if archived is None:
                    missing_count += 1
                    continue
                name = source_path.name
                destination = destination_docs / name
                if destination.exists():
                    destination = destination_docs / f"CV_importe_{len(path_map) + 1:02d}_{name}"
                shutil.copy2(archived, destination)
                final_path = target / destination.relative_to(staging)
                path_map[key] = str(final_path)
            final_path = Path(path_map[key])

        if within(source_path, source_data):
            path_map[key] = str(final_path)
        reference["final_path"] = str(final_path)
        changed_rows += 1

    staged_db = staging / DB_NAME
    with closing(sqlite3.connect(staged_db)) as connection:
        for reference in references:
            final_path = reference.get("final_path")
            if final_path:
                connection.execute(
                    f'UPDATE "{reference["table"]}" SET cv_chemin=? WHERE rowid=?',
                    (final_path, reference["rowid"]),
                )
        connection.commit()
    return path_map, changed_rows, missing_count


def copy_local_data(
    source_data: Path,
    target: Path,
    backup_parent: Path,
    *,
    apply: bool,
    project_root: Path | None = None,
) -> dict[str, Any]:
    source_data = source_data.resolve()
    target = target.resolve(strict=False)
    project_root = (project_root or source_data.parent).resolve()
    source_db = source_data / DB_NAME
    if not source_data.is_dir() or not source_db.is_file():
        raise FileNotFoundError("Le dossier source ou sa base SQLite est absent.")

    before_hashes = inventory(source_data)
    references: list[dict[str, Any]] = []
    with closing(connect_read_only(source_db)) as connection:
        # Read paths only; the report never prints personal path values.
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    references = referenced_cvs(source_db, project_root)
    external_source_hashes = {
        os.path.normcase(str(ref["source_path"])): sha256(ref["source_path"])
        for ref in references
        if ref["source_path"].is_file() and not within(ref["source_path"], source_data)
    }

    source_info = database_info(source_db)
    if source_info["integrity_check"] != ["ok"]:
        raise RuntimeError("La base source n'a pas passé PRAGMA integrity_check.")

    if not apply:
        return {
            "status": "dry_run",
            "source_file_count": len(before_hashes),
            "source_db_rows": source_info["row_counts"],
            "cv_reference_count": len(references),
            "existing_external_cv_count": len(external_source_hashes),
            "target_exists": target.exists(),
            "target_file_count": len(inventory(target)) if target.is_dir() else 0,
        }

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = backup_parent / f"pre-copy-{stamp}-{uuid.uuid4().hex[:6]}"
    backup_data = backup_root / "data"
    backup_external = backup_root / "external_documents"
    backup_sidecars = backup_root / "sqlite-sidecars"
    backup_data.mkdir(parents=True)
    copy_source_data(source_data, backup_data, backup_sidecars)
    snapshot_database(source_db, backup_data / DB_NAME)

    external_backup_map, missing_references = copy_external_documents(
        references, backup_external
    )
    snapshot_info = database_info(backup_data / DB_NAME)
    if snapshot_info["integrity_check"] != ["ok"]:
        raise RuntimeError("La sauvegarde SQLite n'a pas passé PRAGMA integrity_check.")
    if snapshot_info["row_counts"] != source_info["row_counts"]:
        raise RuntimeError("Les nombres de lignes diffèrent entre source et sauvegarde.")
    if snapshot_info["schema"] != source_info["schema"]:
        raise RuntimeError("Le schéma de la sauvegarde diffère de la source.")

    backup_hashes = inventory(backup_data)
    source_hashes_before_db = {
        name: digest for name, digest in before_hashes.items() if name != DB_NAME
    }
    backup_hashes_for_comparison = {
        name: digest for name, digest in backup_hashes.items() if name != DB_NAME
    }
    if source_hashes_before_db != backup_hashes_for_comparison:
        raise RuntimeError("Un ou plusieurs fichiers ont changé pendant la sauvegarde.")

    after_backup_hashes = inventory(source_data)
    external_hashes_after = {
        key: sha256(Path(key)) for key in external_source_hashes
    }
    source_unchanged = (
        after_backup_hashes == before_hashes
        and external_hashes_after == external_source_hashes
    )

    report: dict[str, Any] = {
        "created_at": datetime.now().astimezone().isoformat(),
        "source_data": str(source_data),
        "target_data": str(target),
        "backup_root": str(backup_root),
        "status": "backup_created",
        "source_files": len(before_hashes),
        "backup_data_files": len(backup_hashes),
        "backup_external_documents": len(external_backup_map),
        "missing_cv_references": len(missing_references),
        "source_unchanged_after_backup": source_unchanged,
        "source_row_counts": source_info["row_counts"],
        "backup_row_counts": snapshot_info["row_counts"],
        "source_integrity_check": source_info["integrity_check"],
        "backup_integrity_check": snapshot_info["integrity_check"],
        "schema_unchanged": source_info["schema"] == snapshot_info["schema"],
        "backup_file_sha256": backup_hashes,
        "external_document_sha256": {
            backup_path.name: sha256(backup_path)
            for backup_path in external_backup_map.values()
        },
    }

    if not source_unchanged:
        report["status"] = "backup_created_source_changed_copy_skipped"
        (backup_root / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return report

    if target.exists() and any(target.iterdir()):
        report["status"] = "backup_created_target_not_empty_copy_skipped"
        (backup_root / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return report

    staging = backup_root / "staging"
    path_map, changed_rows, missing_count = prepare_migration_tree(
        backup_data,
        staging,
        references,
        source_data,
        project_root,
        target,
        backup_external,
        external_backup_map,
    )
    staging_info = database_info(staging / DB_NAME)
    if staging_info["integrity_check"] != ["ok"]:
        raise RuntimeError("La copie préparée n'a pas passé PRAGMA integrity_check.")
    if staging_info["row_counts"] != source_info["row_counts"]:
        raise RuntimeError("Les nombres de lignes diffèrent dans la copie préparée.")
    if staging_info["schema"] != source_info["schema"]:
        raise RuntimeError("Le schéma a changé dans la copie préparée.")
    if staging_info["foreign_key_issue_count"] != source_info["foreign_key_issue_count"]:
        raise RuntimeError("Le nombre d'anomalies de clés étrangères a changé.")

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and any(target.iterdir()):
        report["status"] = "backup_created_target_became_nonempty_copy_skipped"
        (backup_root / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return report
    try:
        shutil.copytree(staging, target, dirs_exist_ok=target.exists())
    except FileExistsError:
        report["status"] = "backup_created_target_changed_copy_skipped"
        (backup_root / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return report

    target_info = database_info(target / DB_NAME)
    target_hashes = inventory(target)
    staging_hashes = inventory(staging)
    copy_hashes_match = target_hashes == staging_hashes
    target_cv_refs = referenced_cvs(target / DB_NAME, target.parent.parent)
    target_cv_files_exist = all(
        ref["source_path"].is_file()
        for ref in target_cv_refs
        if ref["raw_path"]
    )
    source_unchanged_after_copy = (
        inventory(source_data) == before_hashes
        and {
            key: sha256(Path(key)) for key in external_source_hashes
        }
        == external_source_hashes
    )
    report.update(
        {
            "status": "copied_and_verified",
            "target_files": len(target_hashes),
            "target_row_counts": target_info["row_counts"],
            "target_integrity_check": target_info["integrity_check"],
            "target_foreign_key_issue_count": target_info["foreign_key_issue_count"],
            "schema_unchanged": target_info["schema"] == source_info["schema"],
            "copied_cv_reference_rows": changed_rows,
            "missing_cv_reference_rows": missing_count,
            "target_cv_files_exist": target_cv_files_exist,
            "target_file_hashes_match_staging": copy_hashes_match,
            "source_unchanged_after_copy": source_unchanged_after_copy,
            "cv_paths_remapped_in_copy_only": len(path_map),
        }
    )
    if (
        target_info["integrity_check"] != ["ok"]
        or target_info["row_counts"] != source_info["row_counts"]
        or target_info["schema"] != source_info["schema"]
        or not copy_hashes_match
        or not target_cv_files_exist
        or not source_unchanged_after_copy
    ):
        report["status"] = "copied_verification_failed_backup_preserved"

    (backup_root / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-data",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
    )
    parser.add_argument(
        "--target-data",
        type=Path,
        help="Par défaut : %LOCALAPPDATA%\\AJI TSTAJI\\data",
    )
    parser.add_argument("--backup-parent", type=Path)
    parser.add_argument("--apply", action="store_true", help="Créer la sauvegarde puis copier.")
    args = parser.parse_args()

    local_app_data = os.environ.get("LOCALAPPDATA")
    if args.target_data is None:
        if not local_app_data:
            parser.error("LOCALAPPDATA n'est pas défini ; indiquez --target-data.")
        app_root = Path(local_app_data) / "AJI TSTAJI"
        args.target_data = app_root / "data"
    else:
        app_root = args.target_data.parent
    backup_parent = args.backup_parent or app_root / "backups"

    try:
        report = copy_local_data(
            args.source_data,
            args.target_data,
            backup_parent,
            apply=args.apply,
            project_root=args.source_data.resolve().parent,
        )
    except Exception as exc:
        print(f"Échec sans suppression de la source : {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({key: value for key, value in report.items() if key != "backup_file_sha256"}, ensure_ascii=False, indent=2))
    if report["status"] == "copied_verification_failed_backup_preserved":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
