"""
charger_donnees.py
Charge le dataset nettoyé de l'application Aji Tstaji.

LECTURE SEULE : ce fichier ne modifie jamais data_nettoyee.xlsx.

Utilisation dans l'application :
    from src.utils.charger_donnees import charger_entreprises
    df = charger_entreprises()

Utilisation directe (aperçu des données) :
    python src/utils/charger_donnees.py
"""

import pandas as pd
from src.utils.classification import normaliser_donnees_entreprises
from src.utils.paths import chemin_ressource

# Chemin du dataset nettoyé (la seule source de l'application)
FICHIER_DONNEES = chemin_ressource(
    "data", "cleaned", "data_nettoyee.xlsx"
)


def charger_entreprises():
    """Lit le fichier Excel nettoyé et retourne un DataFrame pandas."""
    if not FICHIER_DONNEES.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {FICHIER_DONNEES}")
    donnees = pd.read_excel(FICHIER_DONNEES)
    return normaliser_donnees_entreprises(donnees)


def afficher_apercu(df):
    """Affiche les colonnes, les types, les valeurs manquantes et un aperçu."""
    # Options d'affichage : montrer toutes les colonnes sans les couper
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 50)

    print(f"Fichier : {FICHIER_DONNEES}")
    print(f"Nombre de lignes   : {df.shape[0]}")
    print(f"Nombre de colonnes : {df.shape[1]}")

    print("\n=== LES COLONNES ===")
    for numero, nom in enumerate(df.columns, start=1):
        print(f"{numero:>2}. {nom}  ({df[nom].dtype})")

    print("\n=== VALEURS MANQUANTES PAR COLONNE ===")
    print(df.isna().sum())

    print("\n=== APERÇU : 3 PREMIÈRES ENTREPRISES (une colonne = une ligne) ===")
    print(df.head(3).T)


if __name__ == "__main__":
    donnees = charger_entreprises()
    afficher_apercu(donnees)
