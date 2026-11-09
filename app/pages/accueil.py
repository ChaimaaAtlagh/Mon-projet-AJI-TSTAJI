"""
accueil.py
Page d'accueil de l'application AJI TSTAJI :
titre, recherche et section « Pourquoi choisir ».
"""

import tkinter as tk

from PIL import Image, ImageTk

from app import theme
from app.widgets import (
    BoutonModerne, barre_defilement_moderne, entree_moderne,
    lier_defilement_molette, liste_moderne,
)
from src.utils.paths import chemin_ressource

IMAGE_HERO = chemin_ressource("app", "assets", "hero.png")

POLICE_EMOJI = "Segoe UI Emoji"
TEXTE_RECHERCHE = "Rechercher une entreprise, un domaine..."

AVANTAGES = [
    ("🎯", "Simple et intuitif", "Une interface facile à utiliser, accessible à tous.",
     theme.BLEU, theme.BLEU_CLAIR),
    ("🛡", "Données fiables", "Des entreprises issues de Google Maps, nettoyées et vérifiées.",
     theme.VERT, theme.VERT_PASTEL),
    ("⚡", "Gain de temps", "Ton profil et les infos de l'entreprise se remplissent seuls.",
     theme.VIOLET, theme.VIOLET_PASTEL),
    ("🤝", "Accompagnement", "De la recherche d'une entreprise au suivi de ta candidature.",
     theme.ORANGE, theme.ORANGE_PASTEL),
]


class Accueil(tk.Frame):
    """Page d'accueil : un Frame affiché par la fenêtre principale."""

    def __init__(self, parent, app):
        super().__init__(parent, bg=theme.FOND)
        self.app = app

        self._creer_defilement()
        self._creer_hero()
        self._creer_pourquoi()

    # ---------- DÉFILEMENT (canvas + barre de défilement) ----------
    def _creer_defilement(self):
        self.canvas = tk.Canvas(self, bg=theme.FOND, highlightthickness=0,
                                yscrollincrement=30)
        barre = barre_defilement_moderne(self, self.canvas.yview)
        self.canvas.configure(yscrollcommand=barre.set)
        barre.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.contenu = tk.Frame(self.canvas, bg=theme.FOND)
        fenetre = self.canvas.create_window((0, 0), window=self.contenu, anchor="nw")

        self.contenu.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(fenetre, width=e.width))
        lier_defilement_molette(self.canvas)

    # ---------- SECTION 1 : TITRE + RECHERCHE ----------
    def _creer_hero(self):
        hero = tk.Frame(self.contenu, bg=theme.FOND)
        hero.pack(fill="x", padx=70, pady=(40, 30))

        gauche = tk.Frame(hero, bg=theme.FOND)
        gauche.pack(side="left", fill="both", expand=True)

        droite = tk.Frame(hero, bg=theme.FOND)
        droite.pack(side="right")

                # Salutation de l'utilisateur connecté
        nom_utilisateur = getattr(self.app, "nom_utilisateur", "")

        self.label_salutation = tk.Label(
            gauche,
            text=f"Bonjour, {nom_utilisateur} 👋" if nom_utilisateur else "",
            font=(theme.POLICE, 27, "bold"),
            fg=theme.TEXTE,
            bg=theme.FOND
        )
        self.label_salutation.pack(anchor="w", pady=(8, 0))

        # Phrase placée sous Bonjour
        tk.Label(
            gauche,
            text="Ton avenir professionnel commence ici",
            font=(theme.POLICE, 19, "bold"),
            fg=theme.BLEU,
            bg=theme.FOND
        ).pack(anchor="w", pady=(4, 0))

        # Titre principal
        titre = tk.Frame(gauche, bg=theme.FOND)
        titre.pack(anchor="w", pady=(6, 0))

        for texte_partie, couleur in (("AJI ", theme.MARINE), ("TSTAJI", theme.BLEU)):
            tk.Label(
                titre,
                text=texte_partie,
                font=theme.TITRE_GEANT,
                fg=couleur,
                bg=theme.FOND
            ).pack(side="left")

        self.label_bienvenue = tk.Label(
            gauche,
            text="Bienvenue ! Explore les entreprises, découvre les opportunités, "
                 "postule facilement et construis ton avenir professionnel.",
            font=theme.SOUS_TITRE, fg=theme.TEXTE, bg=theme.FOND,
            justify="left", anchor="w")
        self.label_bienvenue.pack(anchor="w", fill="x", pady=(10, 24))
        gauche.bind("<Configure>",
                   lambda e: self.label_bienvenue.config(wraplength=max(e.width - 10, 100)))

        self._creer_recherche(gauche)

        donnees = self.app.donnees
        chiffres = (f"{len(donnees)} entreprises  ·  {donnees['Domaine'].nunique()} domaines  ·  "
                    "données Google Maps (Places API)")
        tk.Label(gauche, text=chiffres, font=theme.PETIT,
                 fg=theme.TEXTE_CLAIR, bg=theme.FOND).pack(anchor="w", pady=(12, 0))

        if IMAGE_HERO.is_file():
            image = Image.open(IMAGE_HERO)
            hauteur = 260
            largeur = int(image.width * hauteur / image.height)
            image = image.resize((largeur, hauteur), Image.Resampling.LANCZOS)
            self.image_hero = ImageTk.PhotoImage(image)
            tk.Label(droite, image=self.image_hero, bg=theme.FOND).pack()

    def _creer_recherche(self, parent):
        barre = tk.Frame(parent, bg=theme.BLANC,
                         highlightbackground=theme.BORDURE, highlightthickness=1)
        barre.pack(fill="x")
        ligne = tk.Frame(barre, bg=theme.BLANC)
        ligne.pack(fill="x", padx=14, pady=12)

        rang_recherche = tk.Frame(ligne, bg=theme.BLANC)
        rang_recherche.pack(fill="x")
        tk.Label(rang_recherche, text="🔍", font=(POLICE_EMOJI, 13),
                 fg=theme.TEXTE_CLAIR, bg=theme.BLANC).pack(side="left", padx=(0, 8))
        self.champ_texte = entree_moderne(
            rang_recherche, largeur=360, hauteur=46,
            placeholder=TEXTE_RECHERCHE,
        )
        self.champ_texte.pack(side="left", fill="x", expand=True)
        self._ajouter_texte_indicatif(self.champ_texte, TEXTE_RECHERCHE)
        self.champ_texte.bind("<Return>", lambda e: self._rechercher())

        controles = tk.Frame(ligne, bg=theme.BLANC)
        controles.pack(fill="x", pady=(10, 0))
        tk.Label(controles, text="📍", font=(POLICE_EMOJI, 13),
                 fg=theme.TEXTE_CLAIR, bg=theme.BLANC).pack(side="left")

        quartiers = sorted(q for q in self.app.donnees["Quartier"].dropna().unique()
                           if q != "A_CONFIRMER")
        self.choix_quartier = liste_moderne(
            controles, ["Tous les quartiers"] + quartiers, largeur=250,
        )
        self.choix_quartier.current(0)
        self.choix_quartier.pack(side="left", padx=(8, 0), fill="x", expand=True)

        BoutonModerne(controles, texte="Rechercher", commande=self._rechercher,
                     style="principal", icone="🔍", fond_parent=theme.BLANC,
                     hauteur=42).pack(side="left", padx=(12, 0))

    def _ajouter_texte_indicatif(self, champ, texte_indicatif):
        champ.insert(0, texte_indicatif)
        champ.configure(text_color=theme.CHAMP_PLACEHOLDER)

        def entrer(evenement):
            if champ.get() == texte_indicatif:
                champ.delete(0, "end")
                champ.configure(text_color=theme.CHAMP_TEXTE)

        def sortir(evenement):
            if not champ.get():
                champ.insert(0, texte_indicatif)
                champ.configure(text_color=theme.CHAMP_PLACEHOLDER)

        champ.bind("<FocusIn>", entrer)
        champ.bind("<FocusOut>", sortir)

    def _rechercher(self):
        texte_saisi = self.champ_texte.get().strip()
        if texte_saisi == TEXTE_RECHERCHE:
            texte_saisi = ""
        quartier = self.choix_quartier.get()
        if quartier == "Tous les quartiers":
            quartier = ""

        self.app.recherche = {"texte": texte_saisi, "quartier": quartier}
        self.app.afficher_page("Entreprises")

    # ---------- SECTION 2 : POURQUOI CHOISIR ----------
    def _creer_pourquoi(self):
        section = tk.Frame(self.contenu, bg=theme.FOND)
        section.pack(fill="x", pady=(40, 50))

        titre = tk.Frame(section, bg=theme.FOND)
        titre.pack()
        for texte_partie, couleur in (("Pourquoi choisir ", theme.MARINE),
                                      ("AJI TSTAJI", theme.BLEU), (" ?", theme.MARINE)):
            tk.Label(titre, text=texte_partie, font=(theme.POLICE, 22, "bold"),
                     fg=couleur, bg=theme.FOND).pack(side="left")

        tk.Label(section,
                 text="Une plateforme simple pour t'accompagner dans ta recherche de stage "
                      "ou d'emploi, du choix de l'entreprise au suivi de ta candidature.",
                 font=theme.NORMAL, fg=theme.TEXTE_CLAIR, bg=theme.FOND,
                 wraplength=700, justify="center").pack(pady=(8, 30))

        grille = tk.Frame(section, bg=theme.FOND)
        grille.pack(fill="x", padx=70)
        for i, (emoji, titre_bloc, texte_bloc, couleur, pastel) in enumerate(AVANTAGES):
            grille.columnconfigure(i, weight=1, uniform="avantage")
            bloc = tk.Frame(grille, bg=theme.FOND)
            bloc.grid(row=0, column=i, sticky="nw", padx=10)

            pastille = tk.Frame(bloc, bg=pastel, width=56, height=56)
            pastille.pack(side="left", anchor="n")
            pastille.pack_propagate(False)
            tk.Label(pastille, text=emoji, font=(POLICE_EMOJI, 20),
                     fg=couleur, bg=pastel).pack(expand=True)

            zone_texte = tk.Frame(bloc, bg=theme.FOND)
            zone_texte.pack(side="left", anchor="n", padx=(12, 0))
            tk.Label(zone_texte, text=titre_bloc, font=theme.GRAS,
                     fg=theme.MARINE, bg=theme.FOND).pack(anchor="w")
            tk.Label(zone_texte, text=texte_bloc, font=theme.PETIT, fg=theme.TEXTE_CLAIR,
                     bg=theme.FOND, justify="left", wraplength=170).pack(anchor="w", pady=(4, 0))
