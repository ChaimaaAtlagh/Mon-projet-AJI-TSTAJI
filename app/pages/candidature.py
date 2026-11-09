
"""
candidature.py
Page « Candidature » :
- Récupération du profil de l'utilisateur connecté.
- Affichage des informations de l'entreprise et du candidat.
- Lettre de motivation modifiable.
- Enregistrement de la candidature avec l'email du compte connecté.
- Envoi d'un email de TEST à l'adresse personnelle de l'étudiant.
"""

import os
import threading
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from app import theme
from app.widgets import (
    BoutonModerne, barre_defilement_moderne, lier_defilement_molette,
    zone_texte_moderne,
)

from src.database.base_donnees import (
    initialiser_base,
    obtenir_profil_utilisateur,
    ajouter_candidature,
    modifier_notes,
    modifier_lettre_candidature,
    modifier_email_confirmation,
)

from src.utils.documents import (
    generer_lettre_motivation,
    envoyer_confirmation_test,
)

VIDE = "-"


def texte(valeur):
    """Remplace les valeurs vides par un tiret pour l'affichage."""
    if valeur is None or str(valeur).strip() in (
        "", "nan", "Non renseigné", "A_CONFIRMER"
    ):
        return VIDE
    return str(valeur)


class Candidature(tk.Frame):

    def __init__(self, parent, app):
        super().__init__(parent, bg=theme.FOND)
        self.app = app
        self._confirmation_en_cours = False

        initialiser_base()

        self._creer_defilement()
        self._creer_titre()

        self.zone_contenu = tk.Frame(self.contenu, bg=theme.FOND)
        self.zone_contenu.pack(
            fill="both",
            expand=True,
            padx=50
        )

    # --------------------------------------------------
    # UTILISATEUR CONNECTÉ
    # --------------------------------------------------

    def _email_utilisateur(self):
        """Retourne l'email du compte actuellement connecté."""
        return (
            getattr(self.app, "utilisateur", None) or ""
        ).strip().lower()

    def _obtenir_profil(self):
        """Récupère le profil associé au compte connecté."""
        email = self._email_utilisateur()

        if not email:
            return None

        return obtenir_profil_utilisateur(email)

    # --------------------------------------------------
    # DÉFILEMENT
    # --------------------------------------------------

    def _creer_defilement(self):
        self.canvas = tk.Canvas(
            self,
            bg=theme.FOND,
            highlightthickness=0,
            yscrollincrement=30
        )

        barre = barre_defilement_moderne(self, self.canvas.yview)

        self.canvas.configure(yscrollcommand=barre.set)

        barre.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.contenu = tk.Frame(self.canvas, bg=theme.FOND)

        fenetre = self.canvas.create_window(
            (0, 0),
            window=self.contenu,
            anchor="nw"
        )

        self.contenu.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(
                fenetre,
                width=e.width
            )
        )

        lier_defilement_molette(self.canvas)

    # --------------------------------------------------
    # TITRE
    # --------------------------------------------------

    def _creer_titre(self):
        tk.Label(
            self.contenu,
            text="Candidature",
            font=theme.TITRE,
            fg=theme.MARINE,
            bg=theme.FOND
        ).pack(anchor="w", padx=50, pady=(25, 0))

        tk.Label(
            self.contenu,
            text=(
                "Vérifie les informations récupérées automatiquement, "
                "adapte la lettre, puis confirme ta candidature."
            ),
            font=theme.NORMAL,
            fg=theme.TEXTE_CLAIR,
            bg=theme.FOND,
            wraplength=750,
            justify="left"
        ).pack(anchor="w", padx=50, pady=(0, 14))

    # --------------------------------------------------
    # ACTUALISATION
    # --------------------------------------------------

    def actualiser(self):
        """Recharge l'entreprise sélectionnée et le profil connecté."""

        for enfant in self.zone_contenu.winfo_children():
            enfant.destroy()

        entreprise = getattr(
            self.app,
            "entreprise_choisie",
            None
        )

        profil = self._obtenir_profil()

        if not self._email_utilisateur():
            self._message_manquant(
                "Aucun utilisateur connecté",
                "Connecte-toi à ton compte avant de préparer une candidature.",
                "Connexion"
            )
            return

        if not entreprise:
            self._message_manquant(
                "Aucune entreprise sélectionnée",
                "Choisis une entreprise depuis « Entreprises » ou "
                "« Opportunités », puis clique sur « Postuler ».",
                "Entreprises"
            )
            return

        if not profil or not profil.get("nom") or not profil.get("email"):
            self._message_manquant(
                "Ton profil n'est pas encore complet",
                "Renseigne au moins ton nom et ton email dans "
                "« Mon profil » avant de confirmer une candidature.",
                "Mon profil"
            )
            return

        self._carte_entreprise(entreprise)
        self._carte_profil(profil)
        self._zone_lettre(profil, entreprise)

    # --------------------------------------------------
    # MESSAGE D'ERREUR / REDIRECTION
    # --------------------------------------------------

    def _message_manquant(self, titre, texte_msg, page_cible):
        carte = tk.Frame(
            self.zone_contenu,
            bg=theme.BLANC,
            highlightbackground=theme.BORDURE,
            highlightthickness=1
        )
        carte.pack(fill="x", pady=20)

        contenu = tk.Frame(carte, bg=theme.BLANC)
        contenu.pack(padx=24, pady=24)

        tk.Label(
            contenu,
            text=titre,
            font=(theme.POLICE, 13, "bold"),
            fg=theme.MARINE,
            bg=theme.BLANC
        ).pack(anchor="w")

        tk.Label(
            contenu,
            text=texte_msg,
            font=theme.NORMAL,
            fg=theme.TEXTE_CLAIR,
            bg=theme.BLANC,
            wraplength=600,
            justify="left"
        ).pack(anchor="w", pady=(6, 14))

        bouton_acces = BoutonModerne(
            contenu,
            texte=f"Aller à {page_cible}",
            icone="→",
            style="principal",
            commande=lambda: self.app.afficher_page(page_cible),
            fond_parent=theme.BLANC,
            hauteur=36
        )
        bouton_acces.pack(anchor="w")

    # --------------------------------------------------
    # CARTE ENTREPRISE
    # --------------------------------------------------

    def _carte_entreprise(self, entreprise):
        carte = tk.Frame(
            self.zone_contenu,
            bg=theme.BLANC,
            highlightbackground=theme.BORDURE,
            highlightthickness=1
        )
        carte.pack(fill="x", pady=(10, 14))

        contenu = tk.Frame(carte, bg=theme.BLANC)
        contenu.pack(fill="x", padx=22, pady=18)

        tk.Label(
            contenu,
            text="Entreprise",
            font=theme.PETIT,
            fg=theme.TEXTE_CLAIR,
            bg=theme.BLANC
        ).pack(anchor="w")

        tk.Label(
            contenu,
            text=texte(entreprise.get("Nom_Entreprise")),
            font=(theme.POLICE, 15, "bold"),
            fg=theme.MARINE,
            bg=theme.BLANC
        ).pack(anchor="w", pady=(2, 10))

        infos = [
            ("Domaine", entreprise.get("Domaine")),
            ("Quartier", entreprise.get("Quartier")),
            ("Adresse", entreprise.get("Adresse")),
            ("Téléphone", entreprise.get("Telephone")),
            ("Email", entreprise.get("Email")),
            ("Site web", entreprise.get("Site_Web")),
        ]

        grille = tk.Frame(contenu, bg=theme.BLANC)
        grille.pack(anchor="w", fill="x")

        for i, (titre, valeur) in enumerate(infos):
            ligne, colonne = i // 2, i % 2

            bloc = tk.Frame(grille, bg=theme.BLANC)
            bloc.grid(
                row=ligne,
                column=colonne,
                sticky="w",
                padx=(0, 30),
                pady=4
            )

            tk.Label(
                bloc,
                text=f"{titre} :",
                font=theme.PETIT,
                fg=theme.TEXTE_CLAIR,
                bg=theme.BLANC
            ).pack(side="left")

            tk.Label(
                bloc,
                text=texte(valeur),
                font=theme.PETIT,
                fg=theme.TEXTE,
                bg=theme.BLANC
            ).pack(side="left", padx=(4, 0))

    # --------------------------------------------------
    # CARTE PROFIL
    # --------------------------------------------------

    def _carte_profil(self, profil):
        carte = tk.Frame(
            self.zone_contenu,
            bg=theme.BLANC,
            highlightbackground=theme.BORDURE,
            highlightthickness=1
        )
        carte.pack(fill="x", pady=(0, 14))

        contenu = tk.Frame(carte, bg=theme.BLANC)
        contenu.pack(fill="x", padx=22, pady=18)

        entete = tk.Frame(contenu, bg=theme.BLANC)
        entete.pack(fill="x")

        tk.Label(
            entete,
            text="Candidat",
            font=theme.PETIT,
            fg=theme.TEXTE_CLAIR,
            bg=theme.BLANC
        ).pack(anchor="w")

        BoutonModerne(
            entete,
            texte="Modifier mon profil",
            icone="✎",
            style="fantome",
            commande=lambda: self.app.afficher_page("Mon profil"),
            fond_parent=theme.BLANC,
            hauteur=30
        ).pack(anchor="e")

        nom_complet = (
            f"{texte(profil.get('prenom'))} "
            f"{texte(profil.get('nom'))}"
        ).strip()

        tk.Label(
            contenu,
            text=nom_complet,
            font=(theme.POLICE, 13, "bold"),
            fg=theme.MARINE,
            bg=theme.BLANC
        ).pack(anchor="w", pady=(2, 10))

        infos = [
            ("Email", profil.get("email")),
            ("Téléphone", profil.get("telephone")),
            ("Ville", profil.get("ville")),
            ("Diplôme", profil.get("diplome")),
            ("Secteur", profil.get("secteur")),
            ("Établissement", profil.get("etablissement")),
        ]

        grille = tk.Frame(contenu, bg=theme.BLANC)
        grille.pack(anchor="w", fill="x")

        for i, (titre, valeur) in enumerate(infos):
            ligne, colonne = i // 2, i % 2

            bloc = tk.Frame(grille, bg=theme.BLANC)
            bloc.grid(
                row=ligne,
                column=colonne,
                sticky="w",
                padx=(0, 30),
                pady=4
            )

            tk.Label(
                bloc,
                text=f"{titre} :",
                font=theme.PETIT,
                fg=theme.TEXTE_CLAIR,
                bg=theme.BLANC
            ).pack(side="left")

            tk.Label(
                bloc,
                text=texte(valeur),
                font=theme.PETIT,
                fg=theme.TEXTE,
                bg=theme.BLANC
            ).pack(side="left", padx=(4, 0))

        chemin_cv = profil.get("cv_chemin")
        cv_valide = bool(chemin_cv) and os.path.isfile(chemin_cv)

        if not cv_valide:
            tk.Label(
                contenu,
                text=(
                    "⚠ Aucun CV valide n'est enregistré dans ton profil : "
                    "génère-le ou choisis un fichier dans « Mon profil »."
                ),
                font=theme.PETIT,
                fg=theme.ORANGE,
                bg=theme.BLANC,
                wraplength=600,
                justify="left"
            ).pack(anchor="w", pady=(10, 0))

    # --------------------------------------------------
    # LETTRE ET NOTES
    # --------------------------------------------------

    def _zone_lettre(self, profil, entreprise):
        carte = tk.Frame(
            self.zone_contenu,
            bg=theme.BLANC,
            highlightbackground=theme.BORDURE,
            highlightthickness=1
        )
        carte.pack(fill="x", pady=(0, 30))

        contenu = tk.Frame(carte, bg=theme.BLANC)
        contenu.pack(fill="x", padx=22, pady=18)

        tk.Label(
            contenu,
            text="Lettre de motivation (adaptée à l'entreprise, modifiable)",
            font=theme.PETIT,
            fg=theme.TEXTE_CLAIR,
            bg=theme.BLANC
        ).pack(anchor="w")

        self.champ_lettre = zone_texte_moderne(
            contenu, largeur=620, hauteur=250
        )
        self.champ_lettre.pack(fill="x", pady=(6, 12))

        base = profil.get("lettre_brouillon")

        if not base:
            lettre = generer_lettre_motivation(
                profil,
                entreprise=entreprise
            )
        else:
            lettre = (
                base
                + f"\n\n(Adapte ce brouillon pour "
                  f"{texte(entreprise.get('Nom_Entreprise'))}.)"
            )

        self.champ_lettre.insert("1.0", lettre)

        tk.Label(
            contenu,
            text="Notes personnelles (facultatif, non envoyées)",
            font=theme.PETIT,
            fg=theme.TEXTE_CLAIR,
            bg=theme.BLANC
        ).pack(anchor="w")

        self.champ_notes = zone_texte_moderne(
            contenu, largeur=620, hauteur=104
        )
        self.champ_notes.pack(fill="x", pady=(6, 16))

        self.bouton_confirmer = BoutonModerne(
            contenu,
            texte="Confirmer la candidature",
            icone="✓",
            style="principal",
            commande=lambda: self._confirmer(profil, entreprise),
            fond_parent=theme.BLANC,
            hauteur=40
        )
        self.bouton_confirmer.pack(anchor="w")

    # --------------------------------------------------
    # CONFIRMATION DE LA CANDIDATURE
    # --------------------------------------------------

    def _confirmer(self, profil, entreprise):
        if self._confirmation_en_cours:
            return

        email_utilisateur = self._email_utilisateur()

        if not email_utilisateur:
            messagebox.showerror(
                "AJI TSTAJI",
                "Aucun utilisateur connecté. Veuillez vous reconnecter."
            )
            return

        # Toujours récupérer le profil du compte connecté
        profil_actuel = obtenir_profil_utilisateur(email_utilisateur)

        if not profil_actuel or not profil_actuel.get("email"):
            messagebox.showerror(
                "AJI TSTAJI",
                "Profil introuvable. Vérifie ton profil avant de continuer."
            )
            return

        notes = self.champ_notes.get("1.0", "end").strip()
        lettre = self.champ_lettre.get("1.0", "end").strip()
        date_du_jour = date.today().isoformat()
        bouton = self.bouton_confirmer
        texte_bouton = bouton.cget("text")
        bouton.configure(state="disabled", text="Enregistrement en cours…")
        self._confirmation_en_cours = True
        racine = self.winfo_toplevel()

        def enregistrer():
            resultat = {"id": None, "succes": False, "message": "", "erreur": None}
            try:
                resultat["id"] = ajouter_candidature(entreprise, email_utilisateur)
                if not resultat["id"]:
                    raise RuntimeError("Impossible d'enregistrer la candidature.")
                if notes:
                    modifier_notes(resultat["id"], notes, email_utilisateur)
                modifier_lettre_candidature(
                    resultat["id"], lettre, email_utilisateur
                )
                resultat["succes"], resultat["message"] = envoyer_confirmation_test(
                    profil_actuel, entreprise, date_du_jour
                )
                modifier_email_confirmation(
                    resultat["id"],
                    "Test envoyé" if resultat["succes"] else "Test échoué",
                    email_utilisateur,
                )
            except Exception as erreur:
                resultat["erreur"] = erreur

            def terminer():
                try:
                    if not racine.winfo_exists():
                        return
                    if resultat["id"]:
                        self.app.candidatures_revision = (
                            getattr(self.app, "candidatures_revision", 0) + 1
                        )
                    if not self.winfo_exists():
                        return
                    self._confirmation_en_cours = False
                    if bouton.winfo_exists():
                        bouton.configure(state="normal", text=texte_bouton)
                    if resultat["erreur"] is not None:
                        messagebox.showerror(
                            "AJI TSTAJI",
                            "Une erreur est survenue lors de l'enregistrement "
                            f"de la candidature :\n{resultat['erreur']}",
                            parent=racine,
                        )
                        return

                    nom_entreprise = texte(entreprise.get("Nom_Entreprise"))
                    icone = "✅" if resultat["succes"] else "❌"
                    messagebox.showinfo(
                        "AJI TSTAJI",
                        f"Candidature enregistrée pour {nom_entreprise}.\n\n"
                        f"{icone} {resultat['message']}",
                        parent=racine,
                    )
                    self.app.entreprise_choisie = None
                    if self.app.page_active == "Candidature":
                        self.app.afficher_page("Mes candidatures")
                except tk.TclError:
                    return

            try:
                racine.after(0, terminer)
            except (RuntimeError, tk.TclError):
                pass

        threading.Thread(target=enregistrer, daemon=True).start()
