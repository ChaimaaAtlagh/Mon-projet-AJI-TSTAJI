
"""
mes_candidatures.py
Page « Mes candidatures » : liste SQLite, changement de statut,
notes et suppression par utilisateur.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from app import theme
from app.widgets import (
    BoutonModerne, barre_defilement_moderne, lier_defilement_molette, liste_moderne,
    saisir_texte_moderne,
)
from src.database.base_donnees import (
    lister_candidatures,
    modifier_statut,
    modifier_notes,
    supprimer_candidature,
    STATUTS_POSSIBLES,
)

VIDE = "-"
TOUS_STATUTS = "Tous les statuts"

COULEURS_STATUT = {
    "À envoyer": (theme.TEXTE_CLAIR, "#F1F5F9"),
    "Envoyée": (theme.BLEU, theme.BLEU_CLAIR),
    "Relancée": (theme.ORANGE, theme.ORANGE_PASTEL),
    "Entretien": (theme.VIOLET, theme.VIOLET_PASTEL),
    "Acceptée": (theme.VERT, theme.VERT_PASTEL),
    "Refusée": (theme.ROSE, theme.ROSE_PASTEL),
}


def texte(valeur):
    if valeur is None or str(valeur).strip() in ("", "nan"):
        return VIDE
    return str(valeur)


class MesCandidatures(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=theme.FOND)
        self.app = app
        self._candidatures_cache = None
        self._email_cache = None
        self._revision_cache = None
        self._rendu_apres = None
        self._rendu_version = 0
        self._candidatures_rendu = []
        self._index_rendu = 0

        self._creer_defilement()
        self._creer_titre()
        self._creer_filtre()

        self.compteur = tk.Label(
            self.contenu_page,
            text="",
            font=theme.PETIT,
            fg=theme.TEXTE_CLAIR,
            bg=theme.FOND
        )
        self.compteur.pack(anchor="w", padx=50, pady=(0, 10))

        self._creer_zone_liste()

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

    def _creer_titre(self):
        tk.Label(
            self.contenu_page,
            text="Mes candidatures",
            font=theme.TITRE,
            fg=theme.MARINE,
            bg=theme.FOND
        ).pack(anchor="w", padx=50, pady=(25, 0))

        tk.Label(
            self.contenu_page,
            text="Suis l'avancement de tes candidatures et mets à jour leur statut.",
            font=theme.NORMAL,
            fg=theme.TEXTE_CLAIR,
            bg=theme.FOND
        ).pack(anchor="w", padx=50, pady=(0, 14))

    def _creer_filtre(self):
        carte = tk.Frame(
            self.contenu_page,
            bg=theme.BLANC,
            highlightbackground=theme.BORDURE,
            highlightthickness=1
        )
        carte.pack(fill="x", padx=50, pady=(0, 10))

        ligne = tk.Frame(carte, bg=theme.BLANC)
        ligne.pack(fill="x", padx=14, pady=12)
        ligne.grid_columnconfigure(0, weight=1)

        tk.Label(
            ligne,
            text="Statut",
            font=theme.PETIT,
            fg=theme.TEXTE_CLAIR,
            bg=theme.BLANC
        ).grid(row=0, column=0, sticky="w")

        self.choix_statut = liste_moderne(
            ligne, [TOUS_STATUTS] + STATUTS_POSSIBLES,
            largeur=220, hauteur=46,
        )
        self.choix_statut.current(0)
        self.choix_statut.grid(
            row=1, column=0, sticky="ew", padx=(0, 14), pady=(5, 0)
        )
        self.choix_statut.bind(
            "<<ComboboxSelected>>",
            lambda evenement: self._afficher_filtre()
        )

        BoutonModerne(
            ligne,
            texte="Actualiser",
            commande=lambda: self.actualiser(force=True),
            style="secondaire",
            icone="↺",
            fond_parent=theme.BLANC,
            hauteur=32
        ).grid(row=1, column=1, padx=(6, 0))

    def _creer_zone_liste(self):
        cadre = tk.Frame(self.contenu_page, bg=theme.FOND)
        cadre.pack(fill="x", padx=40, pady=(0, 20))
        self.liste = tk.Frame(cadre, bg=theme.FOND)
        self.liste.pack(fill="x")

    def _email_utilisateur(self):
        email = getattr(self.app, "utilisateur", None)

        if not isinstance(email, str):
            return ""

        return email.strip().lower()

    def actualiser(self, force=False):
        email = self._email_utilisateur()
        revision = getattr(self.app, "candidatures_revision", 0)
        donnees_modifiees = (
            force
            or self._candidatures_cache is None
            or email != self._email_cache
            or revision != self._revision_cache
        )

        if donnees_modifiees:
            self._candidatures_cache = lister_candidatures(email) if email else []
            self._email_cache = email
            self._revision_cache = revision
            self._afficher_filtre()
        elif (
            self._candidatures_rendu
            and self._index_rendu < len(self._candidatures_rendu)
            and self._rendu_apres is None
        ):
            self._rendu_apres = self.after_idle(
                lambda v=self._rendu_version: self._rendre_lot(v)
            )

    def _afficher_filtre(self):
        candidatures = list(self._candidatures_cache or [])
        email = self._email_utilisateur()

        statut_choisi = self.choix_statut.get()

        if statut_choisi and statut_choisi != TOUS_STATUTS:
            candidatures = [
                candidature
                for candidature in candidatures
                if candidature.get("statut") == statut_choisi
            ]

        self.compteur.config(text=f"{len(candidatures)} candidature(s)")

        if self._rendu_apres is not None:
            self.after_cancel(self._rendu_apres)
            self._rendu_apres = None
        self._rendu_version += 1
        version = self._rendu_version

        for enfant in self.liste.winfo_children():
            enfant.destroy()

        if not candidatures:
            self._candidatures_rendu = []
            self._index_rendu = 0
            message = (
                "Connecte-toi pour consulter tes candidatures."
                if not email
                else
                "Aucune candidature pour le moment. "
                "Postule depuis « Entreprises » ou « Opportunités »."
            )

            tk.Label(
                self.liste,
                text=message,
                font=theme.NORMAL,
                fg=theme.TEXTE_CLAIR,
                bg=theme.FOND,
                wraplength=700
            ).pack(pady=40)

            return

        self._candidatures_rendu = candidatures
        self._index_rendu = 0
        self.compteur.config(text=f"Chargement des candidatures : 0/{len(candidatures)}…")
        self._rendre_lot(version)

    def _rendre_lot(self, version):
        self._rendu_apres = None
        if version != self._rendu_version or not self.winfo_exists():
            return
        if not self.winfo_ismapped():
            return

        fin = min(self._index_rendu + 12, len(self._candidatures_rendu))
        for index in range(self._index_rendu, fin):
            self._ligne_candidature(self._candidatures_rendu[index])
        self._index_rendu = fin

        total = len(self._candidatures_rendu)
        if fin < total:
            self.compteur.config(text=f"Affichage des candidatures : {fin}/{total}…")
            self._rendu_apres = self.after(
                1, lambda v=version: self._rendre_lot(v)
            )
        else:
            self.compteur.config(text=f"{total} candidature(s)")
            self._candidatures_rendu = []
            self._index_rendu = 0

    def _ligne_candidature(self, candidature):
        carte = tk.Frame(
            self.liste,
            bg=theme.BLANC,
            highlightbackground=theme.BORDURE,
            highlightthickness=1
        )
        carte.pack(fill="x", pady=6)

        contenu = tk.Frame(carte, bg=theme.BLANC)
        contenu.pack(fill="x", padx=20, pady=14)

        haut = tk.Frame(contenu, bg=theme.BLANC)
        haut.pack(fill="x")

        gauche = tk.Frame(haut, bg=theme.BLANC)
        gauche.pack(side="left", fill="x", expand=True)

        tk.Label(
            gauche,
            text=texte(candidature.get("entreprise_nom")),
            font=(theme.POLICE, 12, "bold"),
            fg=theme.MARINE,
            bg=theme.BLANC
        ).pack(anchor="w")

        tk.Label(
            gauche,
            text=(
                f"{texte(candidature.get('entreprise_domaine'))}  ·  "
                f"candidature du "
                f"{texte(candidature.get('date_candidature'))}"
            ),
            font=theme.PETIT,
            fg=theme.TEXTE_CLAIR,
            bg=theme.BLANC
        ).pack(anchor="w")

        statut = candidature.get("statut") or "À envoyer"

        couleur_texte, couleur_fond = COULEURS_STATUT.get(
            statut,
            (theme.TEXTE_CLAIR, "#F1F5F9")
        )

        tk.Label(
            haut,
            text=statut,
            font=(theme.POLICE, 9, "bold"),
            fg=couleur_texte,
            bg=couleur_fond,
            padx=10,
            pady=4
        ).pack(side="right")

        bas = tk.Frame(contenu, bg=theme.BLANC)
        bas.pack(fill="x", pady=(10, 0))

        choix = liste_moderne(
            bas, STATUTS_POSSIBLES, largeur=180, hauteur=46,
            police=theme.PETIT,
        )
        choix.set(statut)
        choix.pack(side="left")

        choix.bind(
            "<<ComboboxSelected>>",
            lambda evenement, c=candidature, cb=choix:
                self._changer_statut(c["id"], cb.get())
        )

        boutons = tk.Frame(bas, bg=theme.BLANC)
        boutons.pack(side="right")

        BoutonModerne(
            boutons,
            texte="Notes",
            icone="✎",
            style="fantome",
            commande=lambda c=candidature: self._editer_notes(c),
            fond_parent=theme.BLANC,
            hauteur=30
        ).pack(side="left", padx=(0, 8))

        BoutonModerne(
            boutons,
            texte="Supprimer",
            icone="🗑",
            style="fantome",
            commande=lambda c=candidature: self._supprimer(c),
            fond_parent=theme.BLANC,
            hauteur=30
        ).pack(side="left")

        if candidature.get("notes"):
            tk.Label(
                contenu,
                text=f"Notes : {candidature['notes']}",
                font=theme.PETIT,
                fg=theme.TEXTE_CLAIR,
                bg=theme.BLANC,
                wraplength=700,
                justify="left"
            ).pack(anchor="w", pady=(8, 0))

    def _changer_statut(self, id_candidature, nouveau_statut):
        email = self._email_utilisateur()

        if not email:
            messagebox.showwarning(
                "Connexion",
                "Connecte-toi pour modifier une candidature.",
                parent=self
            )
            return

        succes = modifier_statut(
            id_candidature,
            nouveau_statut,
            email
        )

        if not succes:
            messagebox.showerror(
                "Erreur",
                "Impossible de modifier cette candidature.",
                parent=self
            )

        self.actualiser(force=True)

    def _editer_notes(self, candidature):
        email = self._email_utilisateur()

        if not email:
            messagebox.showwarning(
                "Connexion",
                "Connecte-toi pour modifier les notes.",
                parent=self
            )
            return

        nouvelles_notes = saisir_texte_moderne(
            self,
            "Notes personnelles",
            f"Notes pour {candidature['entreprise_nom']} :",
            valeur_initiale=candidature.get("notes") or "",
        )

        if nouvelles_notes is None:
            return

        succes = modifier_notes(
            candidature["id"],
            nouvelles_notes.strip(),
            email
        )

        if not succes:
            messagebox.showerror(
                "Erreur",
                "Impossible de modifier les notes.",
                parent=self
            )

        self.actualiser(force=True)

    def _supprimer(self, candidature):
        email = self._email_utilisateur()

        if not email:
            messagebox.showwarning(
                "Connexion",
                "Connecte-toi pour supprimer une candidature.",
                parent=self
            )
            return

        confirmation = messagebox.askyesno(
            "AJI TSTAJI",
            f"Supprimer la candidature chez "
            f"{candidature['entreprise_nom']} ?",
            parent=self
        )

        if not confirmation:
            return

        succes = supprimer_candidature(
            candidature["id"],
            email
        )

        if not succes:
            messagebox.showerror(
                "Erreur",
                "Impossible de supprimer cette candidature.",
                parent=self
            )

        self.actualiser(force=True)
