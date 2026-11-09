"""
entreprises.py
Page « Entreprises » : cartes d'entreprises (2 colonnes) avec recherche, filtres et tri.
Le dataset (app.donnees) est lu, jamais modifié.
"""

import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

import pandas as pd

from app import theme
from app.widgets import (
    BoutonModerne, barre_defilement_moderne, entree_moderne, lier_defilement_molette,
    liste_moderne,
)
from src.utils.geolocalisation import lien_google_maps
from src.utils.classification import DOMAINES, SOUS_DOMAINES, filtrer_entreprises

VIDE = "-"
VALEURS_VIDES = {"", "Non renseigné", "A_CONFIRMER"}
TOUS_DOMAINES = "Tous les domaines"
TOUS_SOUS_DOMAINES = "Tous les sous-domaines"
TOUS_QUARTIERS = "Tous les quartiers"
POLICE_EMOJI = "Segoe UI Emoji"

COLONNES_RECHERCHE = ["Nom_Entreprise", "Domaine", "Sous_Domaine", "Adresse", "Quartier"]

TRIS = {
    "Meilleur rating": (["Rating", "Nb_Avis"], [False, False]),
    "Plus d'avis": (["Nb_Avis", "Rating"], [False, False]),
    "Nom (A-Z)": (["Nom_Entreprise"], [True]),
}

NB_COLONNES = 2
TAILLE_LOT_CARTES = 16


def texte(valeur):
    """Remplace une valeur vide/non renseignée par '-', sans toucher au dataset."""
    if pd.isna(valeur) or str(valeur).strip() in VALEURS_VIDES:
        return VIDE
    return str(valeur)


def texte_quartier(valeur):
    """Le quartier 'A_CONFIRMER' s'affiche 'Non confirmé' (affichage seulement)."""
    if pd.isna(valeur) or str(valeur).strip() in ("", "A_CONFIRMER"):
        return "Non confirmé"
    return str(valeur)


class Entreprises(tk.Frame):
    """Page Entreprises : filtres en haut, cartes en dessous, sur 2 colonnes."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=theme.FOND)
        self.app = app
        self._filtre_applique = None
        self._filtre_apres = None
        self._rendu_apres = None
        self._rendu_version = 0
        self._lignes_rendu = []
        self._index_rendu = 0
        self._recherche_index = (
            self.app.donnees[COLONNES_RECHERCHE]
            .fillna("").astype(str).agg(" ".join, axis=1).str.casefold()
        )

        self._creer_defilement()
        self._creer_titre()
        self._creer_filtres()
        self.compteur = tk.Label(self.contenu_page, text="", font=theme.PETIT,
                                 fg=theme.TEXTE_CLAIR, bg=theme.FOND)
        self.compteur.pack(anchor="w", padx=50, pady=(0, 10))
        self._creer_zone_cartes()

    def _creer_defilement(self):
        self.canvas = tk.Canvas(
            self, bg=theme.FOND, highlightthickness=0, yscrollincrement=30
        )
        barre = barre_defilement_moderne(self, self.canvas.yview)
        self.canvas.configure(yscrollcommand=barre.set)
        barre.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.contenu_page = tk.Frame(self.canvas, bg=theme.FOND)
        fenetre = self.canvas.create_window(
            (0, 0), window=self.contenu_page, anchor="nw"
        )
        self.contenu_page.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )
        self.canvas.bind(
            "<Configure>",
            lambda evenement: self.canvas.itemconfigure(
                fenetre, width=evenement.width
            ),
        )
        lier_defilement_molette(self.canvas)

    # ---------- CONSTRUCTION ----------
    def _creer_titre(self):
        tk.Label(self.contenu_page, text="Entreprises", font=theme.TITRE, fg=theme.MARINE,
                 bg=theme.FOND).pack(anchor="w", padx=50, pady=(25, 0))
        tk.Label(self.contenu_page, text="Recherche, filtre et postule directement depuis une carte.",
                 font=theme.NORMAL, fg=theme.TEXTE_CLAIR,
                 bg=theme.FOND).pack(anchor="w", padx=50, pady=(0, 14))

    def _creer_filtres(self):
        carte = tk.Frame(self.contenu_page, bg=theme.BLANC,
                         highlightbackground=theme.BORDURE, highlightthickness=1)
        carte.pack(fill="x", padx=50, pady=(0, 10))
        ligne = tk.Frame(carte, bg=theme.BLANC)
        ligne.pack(fill="x", padx=14, pady=12)
        for colonne in range(2):
            ligne.grid_columnconfigure(colonne, weight=1, uniform="filtres")

        donnees = self.app.donnees
        quartiers = sorted(q for q in donnees["Quartier"].dropna().unique()
                           if q != "A_CONFIRMER")

        tk.Label(ligne, text="Recherche", font=theme.PETIT, fg=theme.TEXTE_CLAIR,
                 bg=theme.BLANC).grid(row=0, column=0, sticky="w")
        self.champ_texte = entree_moderne(ligne, largeur=220, hauteur=44)
        self.champ_texte.grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=(5, 0))
        self.champ_texte.bind("<KeyRelease>", self._programmer_filtres)

        self.choix_domaine = self._liste(
            ligne, 1, "Domaine principal", [TOUS_DOMAINES] + list(DOMAINES), 22,
            commande=lambda _e: self._domaine_selectionne(),
        )
        self.choix_quartier = self._liste(
            ligne, 0, "Quartier", [TOUS_QUARTIERS] + quartiers, 18, ligne_titre=2
        )
        self.choix_sous_domaine = self._liste(
            ligne, 1, "Sous-domaine", [TOUS_SOUS_DOMAINES], 22, ligne_titre=2
        )
        self.choix_tri = self._liste(
            ligne, 0, "Trier par", list(TRIS), 16, ligne_titre=4
        )
        self.choix_sous_domaine.bind(
            "<<ComboboxSelected>>", lambda _e: self.appliquer_filtres()
        )

        BoutonModerne(ligne, texte="Réinitialiser", commande=self.reinitialiser,
                     style="secondaire", icone="↺", fond_parent=theme.BLANC,
                     hauteur=40).grid(
                         row=5, column=1, sticky="e"
                     )

    def _liste(self, parent, colonne, titre, valeurs, largeur, ligne_titre=0,
               commande=None):
        """Crée une liste déroulante avec son titre ; le changement relance le filtre."""
        tk.Label(parent, text=titre, font=theme.PETIT, fg=theme.TEXTE_CLAIR,
                 bg=theme.BLANC).grid(row=ligne_titre, column=colonne, sticky="w")
        liste = liste_moderne(
            parent, valeurs, largeur=largeur * 10, hauteur=46,
        )
        liste.current(0)
        liste.grid(
            row=ligne_titre + 1, column=colonne, sticky="ew",
            padx=(0, 12), pady=(5, 12 if ligne_titre else 5),
        )
        liste.bind(
            "<<ComboboxSelected>>",
            commande or (lambda _e: self.appliquer_filtres()),
        )
        return liste

    # ---------- ZONE DÉFILANTE DES CARTES ----------
    def _creer_zone_cartes(self):
        cadre = tk.Frame(self.contenu_page, bg=theme.FOND)
        cadre.pack(fill="x", padx=40, pady=(0, 20))

        self.grille = tk.Frame(cadre, bg=theme.FOND)
        self.grille.pack(fill="x")
        self.grille.columnconfigure(0, weight=1, uniform="carte")
        self.grille.columnconfigure(1, weight=1, uniform="carte")

    # ---------- FILTRES (pandas) ----------
    def actualiser(self):
        """Préserve la liste et ne recalcule que lorsqu'un filtre change."""
        recherche = self.app.recherche
        if recherche["texte"] or recherche["quartier"]:
            self.champ_texte.delete(0, "end")
            self.champ_texte.insert(0, recherche["texte"])
            self.choix_domaine.set(TOUS_DOMAINES)
            self._mettre_a_jour_sous_domaines(reinitialiser=True)
            self.choix_quartier.set(recherche["quartier"] or TOUS_QUARTIERS)
            self.app.recherche = {"texte": "", "quartier": ""}
            self._filtre_applique = None
        if self._filtre_applique is None:
            self.appliquer_filtres()
        elif self._lignes_rendu and self._rendu_apres is None:
            self._rendu_apres = self.after_idle(
                lambda v=self._rendu_version: self._rendre_lot(v)
            )

    def _programmer_filtres(self, _evenement=None):
        if self._filtre_apres is not None:
            self.after_cancel(self._filtre_apres)
        self._filtre_apres = self.after(180, self._appliquer_filtres_programme)

    def _appliquer_filtres_programme(self):
        self._filtre_apres = None
        self.appliquer_filtres()

    def reinitialiser(self):
        self.champ_texte.delete(0, "end")
        self.choix_domaine.current(0)
        self._mettre_a_jour_sous_domaines(reinitialiser=True)
        self.choix_quartier.current(0)
        self.choix_tri.current(0)
        self.appliquer_filtres()

    def _sous_domaines_disponibles(self, domaine):
        if domaine == TOUS_DOMAINES:
            return list(dict.fromkeys(
                sous_domaine
                for sous_domaines in SOUS_DOMAINES.values()
                for sous_domaine in sous_domaines
            ))
        return list(SOUS_DOMAINES.get(domaine, ()))

    def _mettre_a_jour_sous_domaines(self, reinitialiser=False):
        domaine = self.choix_domaine.get()
        valeurs = [TOUS_SOUS_DOMAINES] + self._sous_domaines_disponibles(domaine)
        selection = (
            TOUS_SOUS_DOMAINES
            if reinitialiser
            else self.choix_sous_domaine.get()
        )
        self.choix_sous_domaine.set_values(valeurs, selection=selection)

    def _domaine_selectionne(self):
        self._mettre_a_jour_sous_domaines(reinitialiser=True)
        self.appliquer_filtres()

    def appliquer_filtres(self):
        """Filtre le dataset local et ne reconstruit que les résultats modifiés."""
        texte_recherche = self.champ_texte.get().strip().casefold()
        domaine = self.choix_domaine.get()
        sous_domaine = self.choix_sous_domaine.get()
        quartier = self.choix_quartier.get()
        tri = self.choix_tri.get()
        criteres = (texte_recherche, domaine, sous_domaine, quartier, tri)
        if criteres == self._filtre_applique:
            return
        self._filtre_applique = criteres

        df = self.app.donnees

        if texte_recherche:
            masque = self._recherche_index.str.contains(
                texte_recherche, regex=False, na=False
            )
            df = df.loc[masque]

        df = filtrer_entreprises(
            df,
            None if domaine == TOUS_DOMAINES else domaine,
            None if sous_domaine == TOUS_SOUS_DOMAINES else sous_domaine,
        )
        if quartier != TOUS_QUARTIERS:
            df = df[df["Quartier"] == quartier]

        colonnes_tri, ordre = TRIS[tri]
        df = df.sort_values(by=colonnes_tri, ascending=ordre)

        self._remplir_cartes(df)

    # ---------- CONSTRUCTION DES CARTES ----------
    def _remplir_cartes(self, df):
        if self._rendu_apres is not None:
            self.after_cancel(self._rendu_apres)
            self._rendu_apres = None
        self._rendu_version += 1
        version = self._rendu_version
        for enfant in self.grille.winfo_children():
            enfant.destroy()

        if df.empty:
            self._lignes_rendu = []
            self._index_rendu = 0
            self.compteur.config(text="0 entreprise affichée")
            tk.Label(self.grille, text="Aucune entreprise ne correspond à ta recherche.",
                     font=theme.NORMAL, fg=theme.TEXTE_CLAIR, bg=theme.FOND).grid(
                row=0, column=0, columnspan=NB_COLONNES, pady=40)
            return

        self._lignes_rendu = list(df.iterrows())
        self._index_rendu = 0
        self.compteur.config(text=f"Chargement des cartes : 0/{len(self._lignes_rendu)}…")
        self._rendre_lot(version)

    def _rendre_lot(self, version):
        self._rendu_apres = None
        if version != self._rendu_version or not self.winfo_exists():
            return
        if not self.winfo_ismapped():
            return

        fin = min(self._index_rendu + TAILLE_LOT_CARTES, len(self._lignes_rendu))
        for rang in range(self._index_rendu, fin):
            _, ligne = self._lignes_rendu[rang]
            self._creer_carte(ligne, rang // NB_COLONNES, rang % NB_COLONNES)
        self._index_rendu = fin

        total = len(self._lignes_rendu)
        if fin < total:
            self.compteur.config(text=f"Affichage des cartes : {fin}/{total}…")
            self._rendu_apres = self.after(
                1, lambda v=version: self._rendre_lot(v)
            )
        else:
            self.compteur.config(
                text=f"{total} entreprises affichées sur {len(self.app.donnees)}"
            )
            self._lignes_rendu = []
            self._index_rendu = 0

    def _creer_carte(self, ligne, rangee, colonne):
        carte = tk.Frame(self.grille, bg=theme.BLANC,
                         highlightbackground=theme.BORDURE, highlightthickness=1)
        carte.grid(row=rangee, column=colonne, sticky="nsew", padx=10, pady=10)

        contenu = tk.Frame(carte, bg=theme.BLANC)
        contenu.pack(fill="both", expand=True, padx=22, pady=20)

        # --- Nom de l'entreprise, bien détaché du reste ---
        tk.Label(contenu, text=texte(ligne["Nom_Entreprise"]), font=(theme.POLICE, 14, "bold"),
                 fg=theme.MARINE, bg=theme.BLANC, anchor="w", justify="left",
                 wraplength=340).pack(anchor="w", pady=(0, 10))

        # --- Badges domaine / quartier ---
        badges = tk.Frame(contenu, bg=theme.BLANC)
        badges.pack(anchor="w", pady=(0, 14))
        self._badge(badges, texte(ligne["Domaine"]), theme.BLEU, theme.BLEU_CLAIR)
        self._badge(badges, texte_quartier(ligne["Quartier"]), theme.ORANGE, theme.ORANGE_PASTEL)

        # --- Adresse et téléphone, groupés avec une icône ---
        infos = tk.Frame(contenu, bg=theme.BLANC)
        infos.pack(anchor="w", fill="x", pady=(0, 16))
        self._ligne_info(infos, "📍", texte(ligne["Adresse"]))
        self._ligne_info(infos, "📞", texte(ligne["Telephone"]))

        # --- Séparateur discret avant le bas de carte ---
        tk.Frame(contenu, bg=theme.BORDURE, height=1).pack(fill="x", pady=(0, 14))

        # --- Rating à gauche, boutons à droite ---
        bas = tk.Frame(contenu, bg=theme.BLANC)
        bas.pack(fill="x")
        self._bloc_rating(bas, ligne)

        boutons = tk.Frame(bas, bg=theme.BLANC)
        boutons.pack(side="right")
        BoutonModerne(boutons, texte="Voir le site", icone="🔗", style="fantome",
                     commande=lambda l=ligne: self.ouvrir_site(l), fond_parent=theme.BLANC,
                     hauteur=34).pack(side="left", padx=(0, 6))
        BoutonModerne(boutons, texte="Localisation", icone="📍", style="fantome",
                     commande=lambda l=ligne: self.ouvrir_localisation(l), fond_parent=theme.BLANC,
                     hauteur=34).pack(side="left", padx=(0, 6))
        BoutonModerne(boutons, texte="Postuler", icone="✓", style="principal",
                     commande=lambda l=ligne: self.postuler(l), fond_parent=theme.BLANC,
                     hauteur=34).pack(side="left")

    def _ligne_info(self, parent, emoji, valeur):
        """Une ligne icône + texte (adresse, téléphone), alignée proprement."""
        ligne = tk.Frame(parent, bg=theme.BLANC)
        ligne.pack(anchor="w", fill="x", pady=2)
        tk.Label(ligne, text=emoji, font=(POLICE_EMOJI, 10), bg=theme.BLANC,
                 width=2).pack(side="left")
        tk.Label(ligne, text=valeur, font=theme.PETIT, fg=theme.TEXTE, bg=theme.BLANC,
                 anchor="w", justify="left", wraplength=300).pack(side="left")

    def _bloc_rating(self, parent, ligne):
        """Étoile + note en évidence, nombre d'avis en gris discret séparé."""
        bloc = tk.Frame(parent, bg=theme.BLANC)
        bloc.pack(side="left")

        rating = f"{float(ligne['Rating']):.1f}" if not pd.isna(ligne["Rating"]) else VIDE
        avis = int(ligne["Nb_Avis"]) if not pd.isna(ligne["Nb_Avis"]) else 0

        ligne_note = tk.Frame(bloc, bg=theme.BLANC)
        ligne_note.pack(anchor="w")
        tk.Label(ligne_note, text="★", font=(POLICE_EMOJI, 13), fg="#F5A623",
                 bg=theme.BLANC).pack(side="left")
        tk.Label(ligne_note, text=rating, font=(theme.POLICE, 13, "bold"),
                 fg=theme.MARINE, bg=theme.BLANC).pack(side="left", padx=(3, 0))

        tk.Label(bloc, text=f"{avis} avis", font=(theme.POLICE, 9),
                 fg=theme.TEXTE_CLAIR, bg=theme.BLANC).pack(anchor="w")

    def _badge(self, parent, texte_badge, couleur_texte, couleur_fond):
        """Petite étiquette colorée (domaine, quartier)."""
        tk.Label(parent, text=texte_badge, font=(theme.POLICE, 9, "bold"),
                 fg=couleur_texte, bg=couleur_fond, padx=11, pady=4).pack(side="left", padx=(0, 8))

    # ---------- ACTIONS ----------
    def ouvrir_site(self, ligne):
        site = str(ligne["Site_Web"])
        if site.startswith("http"):
            webbrowser.open(site)
        else:
            messagebox.showinfo("AJI TSTAJI", "Cette entreprise n'a pas de site web renseigné.")

    def ouvrir_localisation(self, ligne):
        webbrowser.open(lien_google_maps(ligne))

    def postuler(self, ligne):
     """Mémorise l'entreprise choisie et ouvre la page Candidature."""
     self.app.entreprise_choisie = ligne.to_dict()
     self.app.afficher_page("Candidature")
