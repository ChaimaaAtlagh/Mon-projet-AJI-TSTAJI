"""
analyse.py
Page « Analyse » : graphiques Matplotlib calculés avec pandas sur le
dataset nettoyé (app.donnees). Lecture seule.
"""

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from app import theme
from app.widgets import barre_defilement_moderne, lier_defilement_molette

COULEUR_BARRES = "#2563EB"


class Analyse(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=theme.FOND)
        self.app = app
        self._construit = False

    def actualiser(self):
        """Les graphiques sont construits une seule fois, au premier affichage."""
        if self._construit:
            return
        self._construit = True

        self._creer_defilement()
        self._creer_titre()
        self._creer_cartes_chiffres()
        self._creer_graphiques()

    def _creer_defilement(self):
        self.canvas_page = tk.Canvas(self, bg=theme.FOND, highlightthickness=0,
                                     yscrollincrement=30)
        barre = barre_defilement_moderne(self, self.canvas_page.yview)
        self.canvas_page.configure(yscrollcommand=barre.set)
        barre.pack(side="right", fill="y")
        self.canvas_page.pack(side="left", fill="both", expand=True)

        self.contenu = tk.Frame(self.canvas_page, bg=theme.FOND)
        fenetre = self.canvas_page.create_window((0, 0), window=self.contenu, anchor="nw")
        self.contenu.bind("<Configure>",
            lambda e: self.canvas_page.configure(scrollregion=self.canvas_page.bbox("all")))
        self.canvas_page.bind("<Configure>",
            lambda e: self.canvas_page.itemconfig(fenetre, width=e.width))
        lier_defilement_molette(self.canvas_page)

    def _creer_titre(self):
        tk.Label(self.contenu, text="Analyse", font=theme.TITRE, fg=theme.MARINE,
                 bg=theme.FOND).pack(anchor="w", padx=50, pady=(25, 0))
        tk.Label(self.contenu, text="Statistiques calculées avec pandas sur les "
                            "entreprises du dataset nettoyé.",
                 font=theme.NORMAL, fg=theme.TEXTE_CLAIR,
                 bg=theme.FOND).pack(anchor="w", padx=50, pady=(0, 20))

    def _creer_cartes_chiffres(self):
        df = self.app.donnees
        chiffres = [
            ("Entreprises", str(len(df))),
            ("Domaines", str(df["Domaine"].nunique())),
            ("Quartiers", str(df[df["Quartier"] != "A_CONFIRMER"]["Quartier"].nunique())),
            ("Rating moyen", f"{df['Rating'].mean():.2f} / 5"),
            ("Total avis", str(int(df["Nb_Avis"].sum()))),
        ]
        ligne = tk.Frame(self.contenu, bg=theme.FOND)
        ligne.pack(fill="x", padx=50, pady=(0, 20))
        for titre, valeur in chiffres:
            carte = tk.Frame(ligne, bg=theme.BLANC,
                             highlightbackground=theme.BORDURE, highlightthickness=1)
            carte.pack(side="left", fill="both", expand=True, padx=6)
            tk.Label(carte, text=valeur, font=(theme.POLICE, 18, "bold"), fg=theme.MARINE,
                     bg=theme.BLANC).pack(padx=14, pady=(14, 0))
            tk.Label(carte, text=titre, font=theme.PETIT, fg=theme.TEXTE_CLAIR,
                     bg=theme.BLANC).pack(padx=14, pady=(0, 14))

    def _creer_graphiques(self):
        grille = tk.Frame(self.contenu, bg=theme.FOND)
        grille.pack(fill="x", padx=44, pady=(0, 40))
        grille.columnconfigure(0, weight=1, uniform="g")
        grille.columnconfigure(1, weight=1, uniform="g")

        self._graphique(grille, 0, 0, self._figure_domaines(), "Entreprises par domaine")
        self._graphique(grille, 0, 1, self._figure_quartiers(), "Top 10 quartiers")
        self._graphique(grille, 1, 0, self._figure_ratings(), "Distribution des ratings")
        self._graphique(grille, 1, 1, self._figure_top_avis(), "Top 10 par nombre d'avis")

    def _graphique(self, parent, rangee, colonne, figure, titre):
        carte = tk.Frame(parent, bg=theme.BLANC,
                         highlightbackground=theme.BORDURE, highlightthickness=1)
        carte.grid(row=rangee, column=colonne, sticky="nsew", padx=8, pady=8)
        tk.Label(carte, text=titre, font=(theme.POLICE, 11, "bold"), fg=theme.MARINE,
                 bg=theme.BLANC).pack(anchor="w", padx=16, pady=(12, 0))
        canevas = FigureCanvasTkAgg(figure, master=carte)
        canevas.draw()
        canevas.get_tk_widget().pack(padx=10, pady=10)

    def _nouvelle_figure(self):
        figure = Figure(figsize=(5, 3.2), dpi=90)
        axe = figure.add_subplot(111)
        figure.patch.set_facecolor("#FFFFFF")
        return figure, axe

    def _figure_domaines(self):
        figure, axe = self._nouvelle_figure()
        compte = self.app.donnees["Domaine"].value_counts()
        axe.bar(compte.index, compte.values, color=COULEUR_BARRES)
        axe.set_ylabel("Nombre d'entreprises")
        axe.tick_params(axis="x", labelrotation=20)
        figure.tight_layout()
        return figure

    def _figure_quartiers(self):
        figure, axe = self._nouvelle_figure()
        df = self.app.donnees[self.app.donnees["Quartier"] != "A_CONFIRMER"]
        compte = df["Quartier"].value_counts().head(10)
        axe.barh(compte.index[::-1], compte.values[::-1], color=theme.VIOLET)
        axe.set_xlabel("Nombre d'entreprises")
        figure.tight_layout()
        return figure

    def _figure_ratings(self):
        figure, axe = self._nouvelle_figure()
        axe.hist(self.app.donnees["Rating"].dropna(), bins=10, color=theme.VERT,
                edgecolor="white")
        axe.set_xlabel("Rating")
        axe.set_ylabel("Nombre d'entreprises")
        figure.tight_layout()
        return figure

    def _figure_top_avis(self):
        figure, axe = self._nouvelle_figure()
        top = self.app.donnees.sort_values("Nb_Avis", ascending=False).head(10)
        noms = [n[:18] for n in top["Nom_Entreprise"]]
        axe.barh(noms[::-1], top["Nb_Avis"].values[::-1], color=theme.ORANGE)
        axe.set_xlabel("Nombre d'avis")
        figure.tight_layout()
        return figure
