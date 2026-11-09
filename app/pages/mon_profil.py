"""
mon_profil.py
Page « Mon profil » : formulaire SQLite + section CV + section lettre
de motivation (brouillon générique, adapté à l'entreprise au moment
de la candidature).
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app import theme
from app.widgets import (
    BoutonModerne, barre_defilement_moderne, entree_moderne,
    lier_defilement_molette,
    liste_moderne, zone_texte_moderne,
)
from src.database.base_donnees import (
    initialiser_base,
    obtenir_profil_utilisateur,
    enregistrer_profil_utilisateur,
)
from src.utils.documents import generer_cv_excel, generer_lettre_motivation

CHAMPS_TEXTE = [
    ("prenom", "Prénom"), ("nom", "Nom"), ("email", "Email"),
    ("telephone", "Téléphone"), ("ville", "Ville"),
    ("diplome", "Diplôme préparé"), ("secteur", "Secteur étudié"),
    ("etablissement", "Établissement"),
]

VILLE_PAR_DEFAUT = "Marrakech"
OPTIONS_RECHERCHE = ["Stage", "Stage de fin d'études (PFE)", "Emploi", "Alternance"]


class MonProfil(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=theme.FOND)
        self.app = app
        self.entrees = {}
        self.chemin_cv = ""
        self._profil_charge = False
        initialiser_base()

        self._creer_defilement()
        self._creer_formulaire()
        self._creer_section_cv()
        self._creer_section_lettre()
        self._creer_bas()
        self._charger_profil()

    # ---------- DÉFILEMENT ----------
    def _creer_defilement(self):
        self.canvas = tk.Canvas(self, bg=theme.FOND, highlightthickness=0, yscrollincrement=30)
        barre = barre_defilement_moderne(self, self.canvas.yview)
        self.canvas.configure(yscrollcommand=barre.set)
        barre.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.contenu = tk.Frame(self.canvas, bg=theme.FOND)
        fenetre = self.canvas.create_window((0, 0), window=self.contenu, anchor="nw")
        self.contenu.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(fenetre, width=e.width))
        lier_defilement_molette(self.canvas)

    # ---------- FORMULAIRE PRINCIPAL ----------
    def _creer_formulaire(self):
        tk.Label(self.contenu, text="Mon profil", font=theme.TITRE, fg=theme.MARINE,
                 bg=theme.FOND).pack(anchor="w", padx=50, pady=(25, 0))
        tk.Label(self.contenu, text="Renseigne tes informations une seule fois : elles "
                            "seront réutilisées pour tes candidatures.",
                 font=theme.NORMAL, fg=theme.TEXTE_CLAIR,
                 bg=theme.FOND).pack(anchor="w", padx=50, pady=(0, 20))

        carte = tk.Frame(self.contenu, bg=theme.BLANC,
                         highlightbackground=theme.BORDURE, highlightthickness=1)
        carte.pack(fill="x", padx=50, pady=(0, 16))
        grille = tk.Frame(carte, bg=theme.BLANC)
        grille.pack(fill="x", padx=24, pady=20)
        grille.grid_columnconfigure(0, weight=1, uniform="profil")
        grille.grid_columnconfigure(1, weight=1, uniform="profil")

        for i, (cle, titre) in enumerate(CHAMPS_TEXTE):
            ligne, colonne = i // 2, i % 2
            bloc = tk.Frame(grille, bg=theme.BLANC)
            bloc.grid(row=ligne, column=colonne, sticky="ew", padx=12, pady=8)
            bloc.grid_columnconfigure(0, weight=1)
            tk.Label(bloc, text=titre, font=theme.GRAS, fg="#000000",
                     bg=theme.BLANC).pack(anchor="w")
            champ = entree_moderne(bloc, largeur=250, hauteur=46)
            champ.pack(fill="x", pady=(6, 0))
            self.entrees[cle] = champ

        rangee_suivante = (len(CHAMPS_TEXTE) // 2) + 1
        bloc_recherche = tk.Frame(grille, bg=theme.BLANC)
        bloc_recherche.grid(row=rangee_suivante, column=0, sticky="ew", padx=12, pady=8)
        bloc_recherche.grid_columnconfigure(0, weight=1)
        tk.Label(bloc_recherche, text="Je cherche", font=theme.GRAS, fg="#000000",
                 bg=theme.BLANC).pack(anchor="w")
        self.choix_recherche = liste_moderne(
            bloc_recherche, OPTIONS_RECHERCHE, largeur=250,
        )
        self.choix_recherche.pack(fill="x", pady=(6, 0))

        bloc_competences = tk.Frame(grille, bg=theme.BLANC)
        bloc_competences.grid(row=rangee_suivante + 1, column=0, columnspan=2,
                              sticky="ew", padx=12, pady=8)
        bloc_competences.grid_columnconfigure(0, weight=1)
        tk.Label(bloc_competences, text="Compétences (séparées par des virgules)",
                 font=theme.GRAS, fg="#000000", bg=theme.BLANC).pack(anchor="w")
        self.champ_competences = zone_texte_moderne(
            bloc_competences, largeur=520, hauteur=94
        )
        self.champ_competences.pack(fill="x", pady=(6, 0))

    # ---------- SECTION MON CV ----------
    def _creer_section_cv(self):
        carte = tk.Frame(self.contenu, bg=theme.BLANC,
                         highlightbackground=theme.BORDURE, highlightthickness=1)
        carte.pack(fill="x", padx=50, pady=(0, 16))
        contenu = tk.Frame(carte, bg=theme.BLANC)
        contenu.pack(fill="x", padx=24, pady=20)

        tk.Label(contenu, text="Mon CV", font=(theme.POLICE, 13, "bold"), fg=theme.MARINE,
                 bg=theme.BLANC).pack(anchor="w")
        tk.Label(contenu, text="Consulte ton CV, génère-le depuis ton profil, ou "
                            "remplace-le par un fichier existant.",
                 font=theme.PETIT, fg=theme.TEXTE_CLAIR, bg=theme.BLANC
                 ).pack(anchor="w", pady=(2, 12))

        ligne_cv = tk.Frame(contenu, bg=theme.BLANC)
        ligne_cv.pack(anchor="w", fill="x")
        self.label_cv = tk.Label(ligne_cv, text="Aucun CV enregistré", font=theme.PETIT,
                                 fg=theme.TEXTE_CLAIR, bg=theme.BLANC, anchor="w")
        self.label_cv.pack(side="left")

        boutons = tk.Frame(contenu, bg=theme.BLANC)
        boutons.pack(anchor="w", pady=(12, 0))
        BoutonModerne(boutons, texte="Ouvrir", icone="📂", style="fantome",
                     commande=self.ouvrir_cv, fond_parent=theme.BLANC,
                     hauteur=32).pack(side="left", padx=(0, 8))
        BoutonModerne(boutons, texte="Générer depuis mon profil", icone="⚙", style="secondaire",
                     commande=self.generer_cv, fond_parent=theme.BLANC,
                     hauteur=32).pack(side="left", padx=(0, 8))
        BoutonModerne(boutons, texte="Remplacer par un fichier", icone="📎", style="secondaire",
                     commande=self.choisir_cv, fond_parent=theme.BLANC,
                     hauteur=32).pack(side="left")

    def ouvrir_cv(self):
        if self.chemin_cv and os.path.isfile(self.chemin_cv):
            os.startfile(self.chemin_cv)
        else:
            messagebox.showinfo("AJI TSTAJI", "Aucun CV valide n'est enregistré pour l'instant.")

    def choisir_cv(self):
        chemin = filedialog.askopenfilename(
            title="Choisir ton CV",
            filetypes=[("Documents", "*.pdf *.docx *.doc *.xlsx"), ("Tous les fichiers", "*.*")])
        if chemin:
            self.chemin_cv = chemin
            self.label_cv.config(text=os.path.basename(chemin), fg=theme.TEXTE)

    def generer_cv(self):
        donnees = self._donnees_actuelles()
        if not donnees["nom"]:
            messagebox.showwarning("AJI TSTAJI", "Renseigne au moins ton nom avant de générer un CV.")
            return
        chemin = generer_cv_excel(donnees)
        self.chemin_cv = str(chemin)
        self.label_cv.config(text=os.path.basename(self.chemin_cv), fg=theme.TEXTE)
        self._sauvegarder(donnees)
        messagebox.showinfo("AJI TSTAJI", f"CV généré : {chemin}")

    # ---------- SECTION LETTRE DE MOTIVATION ----------
    def _creer_section_lettre(self):
        carte = tk.Frame(self.contenu, bg=theme.BLANC,
                         highlightbackground=theme.BORDURE, highlightthickness=1)
        carte.pack(fill="x", padx=50, pady=(0, 16))
        contenu = tk.Frame(carte, bg=theme.BLANC)
        contenu.pack(fill="x", padx=24, pady=20)

        tk.Label(contenu, text="Lettre de motivation", font=(theme.POLICE, 13, "bold"),
                 fg=theme.MARINE, bg=theme.BLANC).pack(anchor="w")
        tk.Label(contenu, text="Un brouillon général, réutilisé et adapté automatiquement "
                            "à chaque entreprise au moment de la candidature. Modifiable.",
                 font=theme.PETIT, fg=theme.TEXTE_CLAIR, bg=theme.BLANC
                 ).pack(anchor="w", pady=(2, 12))

        self.champ_lettre = zone_texte_moderne(
            contenu, largeur=620, hauteur=220
        )
        self.champ_lettre.pack(fill="x")

        boutons = tk.Frame(contenu, bg=theme.BLANC)
        boutons.pack(anchor="w", pady=(10, 0))
        BoutonModerne(boutons, texte="Générer un brouillon", icone="✎", style="secondaire",
                     commande=self.generer_brouillon_lettre, fond_parent=theme.BLANC,
                     hauteur=32).pack(side="left")

    def generer_brouillon_lettre(self):
        donnees = self._donnees_actuelles()
        if not donnees["nom"]:
            messagebox.showwarning("AJI TSTAJI",
                "Renseigne au moins ton nom avant de générer un brouillon.")
            return
        brouillon = generer_lettre_motivation(donnees, entreprise=None)
        self.champ_lettre.delete("1.0", "end")
        self.champ_lettre.insert("1.0", brouillon)

    # ---------- BAS DE PAGE : ENREGISTRER ----------
    def _creer_bas(self):
        bas = tk.Frame(self.contenu, bg=theme.FOND)
        bas.pack(fill="x", padx=50, pady=(0, 40))
        self.message = tk.Label(bas, text="", font=theme.PETIT, fg=theme.VERT, bg=theme.FOND)
        self.message.pack(side="left")
        BoutonModerne(bas, texte="Enregistrer", icone="💾", style="principal",
                     commande=self.enregistrer, fond_parent=theme.FOND,
                     hauteur=38).pack(side="right")

    # ---------- CHARGEMENT / ENREGISTREMENT ----------
    def _donnees_actuelles(self):
        """Construit un dict à partir de ce qui est actuellement dans le formulaire."""
        donnees = {cle: champ.get().strip() for cle, champ in self.entrees.items()}
        donnees["competences"] = self.champ_competences.get("1.0", "end").strip()
        donnees["recherche"] = self.choix_recherche.get()
        donnees["cv_chemin"] = self.chemin_cv
        donnees["lettre_brouillon"] = self.champ_lettre.get("1.0", "end").strip()
        return donnees

   
    def _sauvegarder(self, donnees):
        email = getattr(self.app, "utilisateur", None)

        if not email:
            messagebox.showerror(
                "AJI TSTAJI",
                "Aucun utilisateur connecté."
            )
            return

        enregistrer_profil_utilisateur(email, donnees)



    def _charger_profil(self):
        """Charge le profil associé au compte actuellement connecté."""
        email = getattr(self.app, "utilisateur", None)
        profil = obtenir_profil_utilisateur(email) if email else None
        profil = profil or {}

        nom_compte = getattr(self.app, "nom_utilisateur", "") or ""
        parties_nom = nom_compte.strip().split(maxsplit=1)

        for cle, champ in self.entrees.items():
            champ.delete(0, "end")
            valeur = profil.get(cle) or ""

            if cle == "email":
                valeur = email or ""
            elif cle == "prenom" and not valeur:
                valeur = parties_nom[0] if parties_nom else ""
            elif cle == "nom" and not valeur:
                valeur = parties_nom[1] if len(parties_nom) > 1 else (
                    parties_nom[0] if parties_nom else ""
                )
            elif cle == "ville" and not valeur:
                valeur = VILLE_PAR_DEFAUT

            champ.insert(0, valeur)

        self.champ_competences.delete("1.0", "end")
        self.champ_competences.insert(
            "1.0", profil.get("competences") or ""
        )

        recherche = profil.get("recherche") or "Stage"
        self.choix_recherche.set(
            recherche if recherche in OPTIONS_RECHERCHE else "Stage"
        )

        self.chemin_cv = profil.get("cv_chemin") or ""
        self.label_cv.config(
            text=os.path.basename(self.chemin_cv)
            if self.chemin_cv else "Aucun CV enregistré",
            fg=theme.TEXTE if self.chemin_cv else theme.TEXTE_CLAIR
        )

        self.champ_lettre.delete("1.0", "end")
        self.champ_lettre.insert(
            "1.0", profil.get("lettre_brouillon") or ""
        )
        self._profil_charge = True

    def actualiser(self):
        if not self._profil_charge:
            self._charger_profil()

    def enregistrer(self):
        donnees = self._donnees_actuelles()

        if not donnees.get("nom") or not donnees.get("email"):
            messagebox.showwarning(
                "Informations manquantes",
                "Veuillez renseigner votre nom et votre e-mail."
            )
            return

        try:
            self._sauvegarder(donnees)
            self.message.config(
                text="Profil enregistré avec succès.",
                fg=theme.VERT
            )
        except Exception as erreur:
            messagebox.showerror(
                "Erreur",
                f"Impossible d'enregistrer le profil : {erreur}"
            )
