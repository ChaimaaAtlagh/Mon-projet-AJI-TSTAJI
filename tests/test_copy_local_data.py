import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.copy_local_data import copy_local_data, database_info, sha256


class CopyLocalDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.source = self.project / "data"
        self.source.mkdir(parents=True)
        self.external = self.root / "private-cv.pdf"
        self.external.write_bytes(b"synthetic test CV")
        (self.source / "reports" / "documents_candidat").mkdir(parents=True)
        (self.source / "reports" / "documents_candidat" / "lettre.txt").write_text(
            "synthetic document", encoding="utf-8"
        )
        db_path = self.source / "aji_tstaji.db"
        with closing(sqlite3.connect(db_path)) as db:
            db.executescript(
                """
                CREATE TABLE profil (id INTEGER PRIMARY KEY, cv_chemin TEXT);
                CREATE TABLE profils_utilisateurs (
                    email TEXT PRIMARY KEY,
                    cv_chemin TEXT
                );
                CREATE TABLE candidatures (id INTEGER PRIMARY KEY, entreprise_nom TEXT);
                INSERT INTO profil VALUES (1, 'PLACEHOLDER');
                INSERT INTO profils_utilisateurs VALUES ('test@example.invalid', 'PLACEHOLDER');
                INSERT INTO candidatures VALUES (1, 'Example Co');
                INSERT INTO candidatures VALUES (2, 'Example Labs');
                """
            )
            db.execute("UPDATE profil SET cv_chemin=? WHERE id=1", (str(self.external),))
            db.execute(
                "UPDATE profils_utilisateurs SET cv_chemin=? WHERE email=?",
                (str(self.external), "test@example.invalid"),
            )
            db.commit()
        self.target = self.root / "localappdata" / "AJI TSTAJI" / "data"
        self.backups = self.root / "localappdata" / "AJI TSTAJI" / "backups"

    def tearDown(self):
        self.temp.cleanup()

    def test_dry_run_does_not_write(self):
        result = copy_local_data(
            self.source, self.target, self.backups, apply=False, project_root=self.project
        )
        self.assertEqual(result["status"], "dry_run")
        self.assertFalse(self.target.exists())
        self.assertFalse(self.backups.exists())

    def test_apply_preserves_source_and_schema_and_copies_external_cv(self):
        source_db_hash = sha256(self.source / "aji_tstaji.db")
        source_cv_hash = sha256(self.external)
        source_info = database_info(self.source / "aji_tstaji.db")

        result = copy_local_data(
            self.source, self.target, self.backups, apply=True, project_root=self.project
        )

        self.assertEqual(result["status"], "copied_and_verified", result)
        self.assertEqual(result["source_row_counts"], result["target_row_counts"])
        self.assertEqual(result["copied_cv_reference_rows"], 2)
        self.assertTrue(result["target_cv_files_exist"])
        self.assertTrue(result["target_file_hashes_match_staging"])
        self.assertEqual(sha256(self.source / "aji_tstaji.db"), source_db_hash)
        self.assertEqual(sha256(self.external), source_cv_hash)
        self.assertEqual(database_info(self.target / "aji_tstaji.db")["schema"], source_info["schema"])
        with closing(sqlite3.connect(self.target / "aji_tstaji.db")) as db:
            paths = [db.execute("SELECT cv_chemin FROM profil").fetchone()[0]]
            paths.append(db.execute("SELECT cv_chemin FROM profils_utilisateurs").fetchone()[0])
        self.assertEqual(paths[0], paths[1])
        self.assertTrue(Path(paths[0]).is_file())
        self.assertEqual(sha256(Path(paths[0])), source_cv_hash)

    def test_nonempty_target_is_never_overwritten(self):
        self.target.mkdir(parents=True)
        sentinel = self.target / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        result = copy_local_data(
            self.source, self.target, self.backups, apply=True, project_root=self.project
        )
        self.assertEqual(result["status"], "backup_created_target_not_empty_copy_skipped")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
        self.assertEqual(len(list(self.backups.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
