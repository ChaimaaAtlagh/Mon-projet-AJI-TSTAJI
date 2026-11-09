
"""
base_donnees.py
Base SQLite de l'application AJI TSTAJI :
profil, candidatures et authentification.
Conserve les données déjà présentes dans la base.
"""

import hashlib
import random
import sqlite3
from datetime import date, datetime, timedelta
from src.utils.paths import chemin_donnees

FICHIER_BASE = chemin_donnees("aji_tstaji.db")

STATUTS_POSSIBLES = [
    "À envoyer", "Envoyée", "Relancée",
    "Entretien", "Acceptée", "Refusée"
]

COLONNES_PROFIL_AJOUTEES = [
    ("diplome", "TEXT"),
    ("secteur", "TEXT"),
    ("etablissement", "TEXT"),
    ("recherche", "TEXT"),
    ("cv_chemin", "TEXT"),
    ("lettre_brouillon", "TEXT"),
    ("mot_de_passe_hash", "TEXT"),
    ("code_reinitialisation", "TEXT"),
    ("code_expiration", "TEXT"),
]

COLONNES_CANDIDATURES_AJOUTEES = [
    ("lettre_motivation", "TEXT"),
    ("email_confirmation", "TEXT"),
    ("utilisateur_email", "TEXT"),
]

COLONNES_PROFIL_UTILISATEUR = {
    "nom", "prenom", "telephone", "ville", "diplome",
    "secteur", "etablissement", "competences", "recherche",
    "cv_chemin", "lettre_brouillon"
}

_BASE_INITIALISEE = False
_CHEMIN_BASE_INITIALISE = None


# ---------- CONNEXION ET INITIALISATION ----------

def obtenir_connexion():
    FICHIER_BASE.parent.mkdir(parents=True, exist_ok=True)
    connexion = sqlite3.connect(FICHIER_BASE)
    connexion.row_factory = sqlite3.Row
    connexion.execute("PRAGMA foreign_keys = ON")
    return connexion


def _colonnes_existantes(connexion, table):
    lignes = connexion.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()
    return {ligne["name"] for ligne in lignes}


def initialiser_base():
    global _BASE_INITIALISEE, _CHEMIN_BASE_INITIALISE

    chemin_base = FICHIER_BASE.resolve()
    if (
        _BASE_INITIALISEE
        and _CHEMIN_BASE_INITIALISE == chemin_base
        and chemin_base.is_file()
    ):
        return

    connexion = obtenir_connexion()

    try:
        connexion.execute("""
            CREATE TABLE IF NOT EXISTS profil (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                nom TEXT,
                prenom TEXT,
                email TEXT,
                telephone TEXT,
                ville TEXT,
                formation TEXT,
                niveau_etude TEXT,
                competences TEXT,
                linkedin TEXT,
                portfolio TEXT,
                date_maj TEXT
            )
        """)

        connexion.execute("""
            CREATE TABLE IF NOT EXISTS candidatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entreprise_nom TEXT NOT NULL,
                entreprise_domaine TEXT,
                entreprise_quartier TEXT,
                entreprise_adresse TEXT,
                entreprise_telephone TEXT,
                entreprise_email TEXT,
                entreprise_site TEXT,
                date_candidature TEXT,
                statut TEXT NOT NULL DEFAULT 'À envoyer',
                notes TEXT,
                date_maj TEXT
            )
        """)

        # Ajouter les colonnes manquantes sans supprimer les anciennes données.
        colonnes_profil = _colonnes_existantes(
            connexion, "profil"
        )

        for nom_colonne, type_colonne in COLONNES_PROFIL_AJOUTEES:
            if nom_colonne not in colonnes_profil:
                connexion.execute(
                    f"ALTER TABLE profil ADD COLUMN "
                    f"{nom_colonne} {type_colonne}"
                )

        colonnes_candidatures = _colonnes_existantes(
            connexion, "candidatures"
        )

        for nom_colonne, type_colonne in COLONNES_CANDIDATURES_AJOUTEES:
            if nom_colonne not in colonnes_candidatures:
                connexion.execute(
                    f"ALTER TABLE candidatures ADD COLUMN "
                    f"{nom_colonne} {type_colonne}"
                )

        # Profil séparé pour chaque utilisateur.
        connexion.execute("""
            CREATE TABLE IF NOT EXISTS profils_utilisateurs (
                email TEXT PRIMARY KEY COLLATE NOCASE,
                nom TEXT,
                prenom TEXT,
                telephone TEXT,
                ville TEXT DEFAULT 'Marrakech',
                diplome TEXT,
                secteur TEXT,
                etablissement TEXT,
                competences TEXT,
                recherche TEXT,
                cv_chemin TEXT,
                lettre_brouillon TEXT,
                date_maj TEXT
            )
        """)

        connexion.execute("""
            CREATE INDEX IF NOT EXISTS idx_candidatures_utilisateur_date
            ON candidatures (utilisateur_email, date_candidature DESC, id DESC)
        """)

        connexion.commit()
        _BASE_INITIALISEE = True
        _CHEMIN_BASE_INITIALISE = chemin_base

    finally:
        connexion.close()


# ---------- PROFIL UNIQUE HISTORIQUE ----------

def obtenir_profil():
    connexion = obtenir_connexion()
    try:
        ligne = connexion.execute(
            "SELECT * FROM profil WHERE id = 1"
        ).fetchone()
        return dict(ligne) if ligne else None
    finally:
        connexion.close()


def enregistrer_profil(donnees):
    donnees = dict(donnees)
    donnees["id"] = 1
    donnees["date_maj"] = date.today().isoformat()

    connexion = obtenir_connexion()

    try:
        colonnes_existantes = _colonnes_existantes(
            connexion, "profil"
        )

        # Ne conserver que les colonnes existantes dans la table.
        donnees = {
            cle: valeur
            for cle, valeur in donnees.items()
            if cle in colonnes_existantes
        }

        colonnes = ", ".join(donnees.keys())
        placeholders = ", ".join("?" for _ in donnees)

        connexion.execute(
            f"INSERT OR REPLACE INTO profil ({colonnes}) "
            f"VALUES ({placeholders})",
            list(donnees.values())
        )
        connexion.commit()

    finally:
        connexion.close()


# ---------- PROFIL PERSONNEL PAR UTILISATEUR ----------

def obtenir_profil_utilisateur(email):
    if not email:
        return None

    initialiser_base()
    email = email.strip().lower()

    connexion = obtenir_connexion()
    try:
        ligne = connexion.execute(
            """
            SELECT *
            FROM profils_utilisateurs
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        return dict(ligne) if ligne else None

    finally:
        connexion.close()


def enregistrer_profil_utilisateur(email, donnees):
    if not email:
        raise ValueError(
            "Un utilisateur connecté est nécessaire."
        )

    initialiser_base()

    email = email.strip().lower()

    donnees = {
        cle: valeur
        for cle, valeur in donnees.items()
        if cle in COLONNES_PROFIL_UTILISATEUR
    }

    donnees["date_maj"] = date.today().isoformat()

    connexion = obtenir_connexion()

    try:
        connexion.execute(
            """
            INSERT INTO profils_utilisateurs (email)
            VALUES (?)
            ON CONFLICT(email) DO NOTHING
            """,
            (email,)
        )

        colonnes = list(donnees.keys())

        if colonnes:
            affectations = ", ".join(
                f"{colonne} = ?" for colonne in colonnes
            )

            connexion.execute(
                f"""
                UPDATE profils_utilisateurs
                SET {affectations}
                WHERE email = ?
                """,
                [donnees[colonne] for colonne in colonnes]
                + [email]
            )

        connexion.commit()

    finally:
        connexion.close()


# ---------- CANDIDATURES PAR UTILISATEUR ----------

def ajouter_candidature(entreprise, utilisateur_email=None):
    if not utilisateur_email:
        raise ValueError(
            "Utilisateur connecté obligatoire."
        )

    initialiser_base()

    utilisateur_email = utilisateur_email.strip().lower()

    connexion = obtenir_connexion()

    try:
        curseur = connexion.execute(
            """
            INSERT INTO candidatures (
                entreprise_nom,
                entreprise_domaine,
                entreprise_quartier,
                entreprise_adresse,
                entreprise_telephone,
                entreprise_email,
                entreprise_site,
                date_candidature,
                statut,
                notes,
                date_maj,
                utilisateur_email
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entreprise.get("Nom_Entreprise") or "Entreprise",
                entreprise.get("Domaine"),
                entreprise.get("Quartier"),
                entreprise.get("Adresse"),
                entreprise.get("Telephone"),
                entreprise.get("Email"),
                entreprise.get("Site_Web"),
                date.today().isoformat(),
                "À envoyer",
                "",
                date.today().isoformat(),
                utilisateur_email,
            )
        )

        nouvel_id = curseur.lastrowid
        connexion.commit()
        return nouvel_id

    finally:
        connexion.close()


def lister_candidatures(utilisateur_email=None):
    if not utilisateur_email:
        return []

    initialiser_base()
    utilisateur_email = utilisateur_email.strip().lower()

    connexion = obtenir_connexion()

    try:
        lignes = connexion.execute(
            """
            SELECT *
            FROM candidatures
            WHERE utilisateur_email = ?
            ORDER BY date_candidature DESC, id DESC
            """,
            (utilisateur_email,)
        ).fetchall()

        return [dict(ligne) for ligne in lignes]

    finally:
        connexion.close()


def modifier_statut(
    id_candidature, nouveau_statut, utilisateur_email=None
):
    if (
        not utilisateur_email
        or nouveau_statut not in STATUTS_POSSIBLES
    ):
        return False

    connexion = obtenir_connexion()

    try:
        curseur = connexion.execute(
            """
            UPDATE candidatures
            SET statut = ?, date_maj = ?
            WHERE id = ? AND utilisateur_email = ?
            """,
            (
                nouveau_statut,
                date.today().isoformat(),
                id_candidature,
                utilisateur_email.strip().lower(),
            )
        )

        connexion.commit()
        return curseur.rowcount > 0

    finally:
        connexion.close()


def modifier_notes(
    id_candidature, notes, utilisateur_email=None
):
    if not utilisateur_email:
        return False

    connexion = obtenir_connexion()

    try:
        curseur = connexion.execute(
            """
            UPDATE candidatures
            SET notes = ?, date_maj = ?
            WHERE id = ? AND utilisateur_email = ?
            """,
            (
                notes,
                date.today().isoformat(),
                id_candidature,
                utilisateur_email.strip().lower(),
            )
        )

        connexion.commit()
        return curseur.rowcount > 0

    finally:
        connexion.close()


def modifier_lettre_candidature(
    id_candidature, lettre, utilisateur_email=None
):
    if not utilisateur_email:
        return False

    connexion = obtenir_connexion()

    try:
        curseur = connexion.execute(
            """
            UPDATE candidatures
            SET lettre_motivation = ?, date_maj = ?
            WHERE id = ? AND utilisateur_email = ?
            """,
            (
                lettre,
                date.today().isoformat(),
                id_candidature,
                utilisateur_email.strip().lower(),
            )
        )

        connexion.commit()
        return curseur.rowcount > 0

    finally:
        connexion.close()


def modifier_email_confirmation(
    id_candidature, statut_email, utilisateur_email=None
):
    if not utilisateur_email:
        return False

    connexion = obtenir_connexion()

    try:
        curseur = connexion.execute(
            """
            UPDATE candidatures
            SET email_confirmation = ?
            WHERE id = ? AND utilisateur_email = ?
            """,
            (
                statut_email,
                id_candidature,
                utilisateur_email.strip().lower(),
            )
        )

        connexion.commit()
        return curseur.rowcount > 0

    finally:
        connexion.close()


def supprimer_candidature(
    id_candidature, utilisateur_email=None
):
    if not utilisateur_email:
        return False

    connexion = obtenir_connexion()

    try:
        curseur = connexion.execute(
            """
            DELETE FROM candidatures
            WHERE id = ? AND utilisateur_email = ?
            """,
            (
                id_candidature,
                utilisateur_email.strip().lower(),
            )
        )

        connexion.commit()
        return curseur.rowcount > 0

    finally:
        connexion.close()


# ---------- AUTHENTIFICATION HISTORIQUE ----------
# Conservée pour ne pas casser les pages qui l'utilisent encore.

def _hacher(mot_de_passe):
    return hashlib.sha256(
        mot_de_passe.encode("utf-8")
    ).hexdigest()


def compte_existe():
    profil = obtenir_profil()
    return bool(
        profil
        and profil.get("email")
        and profil.get("mot_de_passe_hash")
    )


def creer_compte(email, mot_de_passe):
    if compte_existe():
        return (
            False,
            "Un compte existe déjà. Utilise plutôt "
            "'Se connecter'."
        )

    donnees = obtenir_profil() or {}
    donnees["email"] = email.strip().lower()
    donnees["mot_de_passe_hash"] = _hacher(mot_de_passe)

    enregistrer_profil(donnees)
    return True, "Compte créé avec succès."


def verifier_connexion(email, mot_de_passe):
    profil = obtenir_profil()

    if not profil or not profil.get("email"):
        return (
            False,
            "Aucun compte configuré. Clique sur "
            "'Créer un compte'."
        )

    if profil.get("email", "").strip().lower() != email.strip().lower():
        return False, "Email incorrect."

    if profil.get("mot_de_passe_hash") != _hacher(mot_de_passe):
        return False, "Mot de passe incorrect."

    return True, "Connexion réussie."


def generer_code_reinitialisation(email):
    profil = obtenir_profil()

    if (
        not profil
        or profil.get("email", "").strip().lower()
        != email.strip().lower()
    ):
        return None, "Aucun compte ne correspond à cet email."

    code = f"{random.randint(100000, 999999)}"
    expiration = (
        datetime.now() + timedelta(minutes=15)
    ).isoformat()

    donnees = dict(profil)
    donnees["code_reinitialisation"] = code
    donnees["code_expiration"] = expiration

    enregistrer_profil(donnees)
    return code, None


def reinitialiser_mot_de_passe(
    email, code, nouveau_mot_de_passe
):
    profil = obtenir_profil()

    if (
        not profil
        or profil.get("email", "").strip().lower()
        != email.strip().lower()
    ):
        return False, "Email incorrect."

    if profil.get("code_reinitialisation") != code:
        return False, "Code incorrect."

    expiration = profil.get("code_expiration")

    if not expiration:
        return False, "Demande un nouveau code."

    if datetime.now() > datetime.fromisoformat(expiration):
        return False, "Code expiré, redemande-en un."

    donnees = dict(profil)
    donnees["mot_de_passe_hash"] = _hacher(
        nouveau_mot_de_passe
    )
    donnees["code_reinitialisation"] = ""
    donnees["code_expiration"] = ""

    enregistrer_profil(donnees)
    return True, "Mot de passe réinitialisé."


if __name__ == "__main__":
    initialiser_base()

    print(f"Base créée/ouverte : {FICHIER_BASE}")

    connexion = obtenir_connexion()

    print(
        "Colonnes profil :",
        sorted(_colonnes_existantes(connexion, "profil"))
    )
    print(
        "Colonnes candidatures :",
        sorted(_colonnes_existantes(connexion, "candidatures"))
    )

    connexion.close()
