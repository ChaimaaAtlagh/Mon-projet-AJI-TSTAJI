"""Création de liens de recherche d'adresses sur Google Maps."""

from math import isnan
from urllib.parse import urlencode


VALEURS_INCONNUES = {"", "-", "nan", "<na>", "none", "non renseigné", "a_confirmer"}


def _texte_disponible(valeur):
    if valeur is None:
        return ""
    try:
        if isnan(float(valeur)):
            return ""
    except (TypeError, ValueError, OverflowError):
        pass
    texte = str(valeur).strip()
    if texte.lower() in VALEURS_INCONNUES:
        return ""
    return texte


def lien_google_maps(entreprise):
    """Retourne une recherche Maps fondée sur l'entreprise et son adresse."""
    nom = _texte_disponible(entreprise.get("Nom_Entreprise"))
    adresse = _texte_disponible(entreprise.get("Adresse"))
    quartier = _texte_disponible(entreprise.get("Quartier"))

    requete = ", ".join(
        valeur for valeur in (nom, adresse, quartier, "Marrakech", "Maroc") if valeur
    )
    return "https://www.google.com/maps/search/?" + urlencode(
        {"api": 1, "query": requete}
    )
