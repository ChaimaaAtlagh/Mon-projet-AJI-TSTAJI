"""Chemins partagés pour le projet Python et sa distribution Windows."""

import os
import sys
from pathlib import Path


NOM_APPLICATION = "AJI TSTAJI"


def racine_ressources():
    """Racine des fichiers livrés avec l'application ou du dépôt source."""
    if getattr(sys, "frozen", False):
        return Path(
            getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)
        )
    return Path(__file__).resolve().parents[2]


def dossier_application():
    """Dossier utilisateur inscriptible pour configuration et données privées."""
    if not getattr(sys, "frozen", False):
        return racine_ressources()

    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / NOM_APPLICATION


def chemin_ressource(*morceaux):
    """Construit un chemin vers une ressource incluse dans le paquet."""
    return racine_ressources().joinpath(*morceaux)


def chemin_donnees(*morceaux):
    """Construit un chemin persistant hors du dossier d'installation."""
    return dossier_application().joinpath("data", *morceaux)


def chemin_configuration():
    """Fichier .env du dépôt ou fichier privé à l'utilisateur sous Windows."""
    if getattr(sys, "frozen", False):
        return dossier_application() / ".env"
    return racine_ressources() / ".env"
