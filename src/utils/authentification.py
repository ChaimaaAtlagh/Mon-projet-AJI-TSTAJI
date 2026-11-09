"""
authentification.py
Gestion simple des comptes utilisateurs (stockage local, mots de passe hachés).

Fichier créé automatiquement : data/utilisateurs.json
Si votre projet possède déjà un système de comptes, remplacez simplement le
contenu de `verifier` et `inscrire` en gardant les mêmes valeurs de retour.
"""

import hashlib
import hmac
import json
import os
from src.utils.paths import chemin_donnees

FICHIER = chemin_donnees("utilisateurs.json")
ITERATIONS = 200_000


def _charger():
    if FICHIER.exists():
        try:
            return json.loads(FICHIER.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _enregistrer(utilisateurs):
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(json.dumps(utilisateurs, indent=2, ensure_ascii=False),
                       encoding="utf-8")


def _hacher(mot_de_passe, sel):
    return hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"),
                               sel, ITERATIONS).hex()




def inscrire(nom, email, mot_de_passe, informations=None):
    """Crée un compte et enregistre ses informations."""
    email = email.strip().lower()
    nom = nom.strip()

    utilisateurs = _charger()

    if email in utilisateurs:
        return False, "Un compte existe déjà avec cette adresse e-mail."

    sel = os.urandom(16)

    utilisateurs[email] = {
        "nom": nom,
        "sel": sel.hex(),
        "hash": _hacher(mot_de_passe, sel),
        "informations": informations or {}
    }

    _enregistrer(utilisateurs)
    return True, ""




def verifier(email, mot_de_passe):
    """Retourne (ok: bool, message: str, nom: str)."""
    email = email.strip().lower()
    fiche = _charger().get(email)
    if not fiche:
        return False, "E-mail ou mot de passe incorrect.", ""
    calcule = _hacher(mot_de_passe, bytes.fromhex(fiche["sel"]))
    if hmac.compare_digest(calcule, fiche["hash"]):
        return True, "", fiche.get("nom", "")
    return False, "E-mail ou mot de passe incorrect.", ""

def obtenir_informations(email):
    """Retourne les informations complémentaires du compte."""
    email = email.strip().lower()
    fiche = _charger().get(email, {})
    return fiche.get("informations", {})
