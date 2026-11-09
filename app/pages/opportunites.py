"""
opportunites.py
Page « Opportunités » : meilleures entreprises classées par pertinence
(rating + nombre d'avis), avec filtre par domaine.
Le dataset (app.donnees) est lu, jamais modifié.
"""

import math
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

import pandas as pd

from app import theme
from app.widgets import (
    BoutonModerne, barre_defilement_moderne, lier_defilement_molette,
    liste_moderne,
)
from src.utils.geolocalisation import lien_google_maps

VIDE = "-"
VALEURS_VIDES = {"", "Non renseigné", "A_CONFIRMER"}
TOUS_DOMAINES = "Tous les domaines"
POLICE_EMOJI = "Segoe UI Emoji"
NB_COLONNES = 2
NB_TOP = 3  # nombre de cartes marquées "Top opportunité"
TAILLE_LOT_CARTES = 16


def texte(valeur):
    """Remplace une valeur vide/non renseignée par '-', sans toucher au dataset."""
    if pd.isna(valeur) or str(valeur).strip() in VALEURS_VIDES:
        return VIDE
    return str(valeur)


def texte_quartier(valeur):
    if pd.isna(valeur) or str(valeur).strip() in ("", "A_CONFIRMER"):
        return "Non confirmé"
    return str(valeur)


def calculer_score(df):
    """
    Score de pertinence = Rating x log(Nb_Avis + 1).
    Le logarithme évite qu'une entreprise avec très peu d'avis écrase
    une entreprise mieux établie, tout en récompensant les bons ratings.
    """
    df = df.copy()
    df["Score"] = df["Rating"].fillna(0) * df["Nb_Avis"].fillna(0).apply(
        lambda n: math.log(n + 1))
    return df


class Opportunites(tk.Frame):
    """Page Opportunités : filtre domaine + cartes triées par score de pertinence."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=theme.FOND)
        self.app = app
        self._filtre_applique = None
        self._rendu_apres = None
        self._rendu_version = 0
        self._lignes_rendu = []
        self._index_rendu = 0
        self.donnees_scorees = calculer_score(self.app.donnees)

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
        tk.Label(self.contenu_page, text="Opportunités", font=theme.TITRE, fg=theme.MARINE,
                 bg=theme.FOND).pack(anchor="w", padx=50, pady=(25, 0))
        tk.Label(self.contenu_page, text="Les entreprises les plus pertinentes, classées "
                            "selon leur rating et leur nombre d'avis.",
                 font=theme.NORMAL, fg=theme.TEXTE_CLAIR,
                 bg=theme.FOND).pack(anchor="w", padx=50, pady=(0, 14))

    def _creer_filtres(self):
        carte = tk.Frame(self.contenu_page, bg=theme.BLANC,
                         highlightbackground=theme.BORDURE, highlightthickness=1)
        carte.pack(fill="x", padx=50, pady=(0, 10))
        ligne = tk.Frame(carte, bg=theme.BLANC)
        ligne.pack(fill="x", padx=14, pady=12)
        ligne.grid_columnconfigure(0, weight=1)

        domaines = sorted(self.app.donnees["Domaine"].dropna().unique())

        tk.Label(ligne, text="Domaine", font=theme.PETIT, fg=theme.TEXTE_CLAIR,
                 bg=theme.BLANC).grid(row=0, column=0, sticky="w")
        self.choix_domaine = liste_moderne(
            ligne, [TOUS_DOMAINES] + domaines, largeur=240,
        )
        self.choix_domaine.current(0)
        self.choix_domaine.grid(
            row=1, column=0, sticky="ew", padx=(0, 14), pady=(5, 0)
        )
        self.choix_domaine.bind("<<ComboboxSelected>>", lambda e: self.appliquer_filtres())

        BoutonModerne(ligne, texte="Réinitialiser", commande=self.reinitialiser,
                     style="secondaire", icone="↺", fond_parent=theme.BLANC,
                     hauteur=32).grid(row=1, column=1, padx=(6, 0))

    def _creer_zone_cartes(self):
        cadre = tk.Frame(self.contenu_page, bg=theme.FOND)
        cadre.pack(fill="x", padx=40, pady=(0, 20))

        self.grille = tk.Frame(cadre, bg=theme.FOND)
        self.grille.pack(fill="x")
        self.grille.columnconfigure(0, weight=1, uniform="carte")
        self.grille.columnconfigure(1, weight=1, uniform="carte")

    # ---------- FILTRES + SCORE (pandas) ----------
    def actualiser(self):
        """Construit la liste une fois et reprend un rendu suspendu si nécessaire."""
        if self._filtre_applique is None:
            self.appliquer_filtres()
        elif self._lignes_rendu and self._rendu_apres is None:
            self._rendu_apres = self.after_idle(
                lambda v=self._rendu_version: self._rendre_lot(v)
            )

    def reinitialiser(self):
        self.choix_domaine.current(0)
        self.appliquer_filtres()

    def appliquer_filtres(self):
        domaine = self.choix_domaine.get()
        if domaine == self._filtre_applique:
            return
        self._filtre_applique = domaine
        df = self.donnees_scorees

        if domaine != TOUS_DOMAINES:
            df = df[df["Domaine"] == domaine]

        df = df.sort_values(by="Score", ascending=False)

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
            self.compteur.config(text="0 opportunité affichée")
            tk.Label(self.grille, text="Aucune opportunité pour ce filtre.",
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
            self._creer_carte(ligne, rang, rang // NB_COLONNES, rang % NB_COLONNES)
        self._index_rendu = fin

        total = len(self._lignes_rendu)
        if fin < total:
            self.compteur.config(text=f"Affichage des cartes : {fin}/{total}…")
            self._rendu_apres = self.after(
                1, lambda v=version: self._rendre_lot(v)
            )
        else:
            self.compteur.config(
                text=f"{total} opportunité(s) affichée(s), classée(s) par pertinence"
            )
            self._lignes_rendu = []
            self._index_rendu = 0

    def _creer_carte(self, ligne, rang, rangee, colonne):
        carte = tk.Frame(self.grille, bg=theme.BLANC,
                         highlightbackground=theme.BORDURE, highlightthickness=1)
        carte.grid(row=rangee, column=colonne, sticky="nsew", padx=10, pady=10)

        contenu = tk.Frame(carte, bg=theme.BLANC)
        contenu.pack(fill="both", expand=True, padx=22, pady=20)

        # Badge "Top opportunité" pour les 3 premières
        if rang < NB_TOP:
            tk.Label(contenu, text="⭐ Top opportunité", font=(theme.POLICE, 9, "bold"),
                     fg=theme.BLANC, bg=theme.VIOLET, padx=10, pady=3
                     ).pack(anchor="w", pady=(0, 10))

        tk.Label(contenu, text=texte(ligne["Nom_Entreprise"]), font=(theme.POLICE, 14, "bold"),
                 fg=theme.MARINE, bg=theme.BLANC, anchor="w", justify="left",
                 wraplength=340).pack(anchor="w", pady=(0, 10))

        badges = tk.Frame(contenu, bg=theme.BLANC)
        badges.pack(anchor="w", pady=(0, 14))
        self._badge(badges, texte(ligne["Domaine"]), theme.BLEU, theme.BLEU_CLAIR)
        self._badge(badges, texte_quartier(ligne["Quartier"]), theme.ORANGE, theme.ORANGE_PASTEL)

        infos = tk.Frame(contenu, bg=theme.BLANC)
        infos.pack(anchor="w", fill="x", pady=(0, 16))
        self._ligne_info(infos, "📍", texte(ligne["Adresse"]))
        self._ligne_info(infos, "📞", texte(ligne["Telephone"]))

        tk.Frame(contenu, bg=theme.BORDURE, height=1).pack(fill="x", pady=(0, 14))

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
        ligne = tk.Frame(parent, bg=theme.BLANC)
        ligne.pack(anchor="w", fill="x", pady=2)
        tk.Label(ligne, text=emoji, font=(POLICE_EMOJI, 10), bg=theme.BLANC,
                 width=2).pack(side="left")
        tk.Label(ligne, text=valeur, font=theme.PETIT, fg=theme.TEXTE, bg=theme.BLANC,
                 anchor="w", justify="left", wraplength=300).pack(side="left")

    def _bloc_rating(self, parent, ligne):
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
        print("Entreprise choisie (Opportunités) :", ligne["Nom_Entreprise"])
        self.app.afficher_page("Candidature")
