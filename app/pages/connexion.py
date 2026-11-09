
"""
connexion.py
Page d'authentification AJI TSTAJI (connexion + création de compte).
Design : panneau gauche illustré avec photo circulaire de Marrakech,
panneau droit pour la connexion ou l'inscription.
"""

import json
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
import customtkinter as ctk

from app import theme
from app.widgets import (
    barre_defilement_moderne, entree_moderne, lier_defilement_molette,
    liste_moderne,
)
from src.utils.authentification import verifier
from src.utils.api_authentification import AuthAPIError, AuthClient
from src.utils.paths import chemin_ressource
from src.database.base_donnees import (
    initialiser_base,
    obtenir_profil_utilisateur,
    enregistrer_profil_utilisateur,
)

try:
    from PIL import Image, ImageDraw, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False


_AUTH_CLIENT = AuthClient()


# ------------------------------------------------------------ Chemins
IMAGE_MARRAKECH = chemin_ressource("app", "assets", "koutoubia.png")
LOGO = chemin_ressource("app", "assets", "logo.png")

EMAIL_RE = re.compile(r"^[\w.+\-]+@[\w\-]+(\.[\w\-]+)+$")
ROUGE_ERREUR = "#DC2626"
GRIS_TEXTE = "#64748B"
BLEU_CLAIR = "#EAF5FF"
BLEU_PALE = "#D7EBFF"
BLEU = "#1769E8"
BLEU_FONCE = "#123D73"
BLANC = "#FFFFFF"


# ------------------------------------------------------ Visuel Marrakech
def _recadrer(img, largeur, hauteur):
    """Recadre une image pour remplir une zone sans l'étirer."""
    echelle = max(largeur / img.width, hauteur / img.height)
    taille = (
        max(1, int(img.width * echelle)),
        max(1, int(img.height * echelle)),
    )
    img = img.resize(taille, Image.Resampling.LANCZOS)
    gauche = (img.width - largeur) // 2
    haut = (img.height - hauteur) // 2
    return img.crop(
        (gauche, haut, gauche + largeur, haut + hauteur)
    )


def construire_visuel(largeur, hauteur):
    """Panneau gauche moderne avec bord courbe et photo circulaire."""
    from PIL import ImageFont, ImageDraw, Image

    largeur = max(largeur, 300)
    hauteur = max(hauteur, 400)

    image = Image.new("RGB", (largeur, hauteur), "#F5FAFF")
    dessin = ImageDraw.Draw(image)

    dessin.rectangle(
        (0, 0, int(largeur * 0.65), hauteur),
        fill="#EAF5FF"
    )
    dessin.ellipse(
        (
            int(largeur * 0.12), -int(hauteur * 0.28),
            int(largeur * 1.04), int(hauteur * 1.10)
        ),
        fill="#C7E3FF"
    )
    dessin.ellipse(
        (
            int(largeur * 0.07), -int(hauteur * 0.28),
            int(largeur * 0.97), int(hauteur * 1.06)
        ),
        fill="#EFF7FF"
    )

    dessin.ellipse(
        (
            -int(largeur * 0.35), int(hauteur * 0.78),
            int(largeur * 0.95), int(hauteur * 1.50)
        ),
        fill="#D8EBFF"
    )
    dessin.ellipse(
        (
            -int(largeur * 0.38), int(hauteur * 0.76),
            int(largeur * 0.88), int(hauteur * 1.43)
        ),
        fill="#F2F8FF"
    )

    try:
        police_grande = ImageFont.truetype(
            "arial.ttf", max(24, int(largeur * 0.064))
        )
        police_moyenne = ImageFont.truetype(
            "arial.ttf", max(12, int(largeur * 0.026))
        )
        police_petite = ImageFont.truetype(
            "arial.ttf", max(11, int(largeur * 0.022))
        )
    except OSError:
        police_grande = ImageFont.load_default()
        police_moyenne = ImageFont.load_default()
        police_petite = ImageFont.load_default()

    marge = int(largeur * 0.07)
    haut_logo = int(hauteur * 0.07)

    logo_img = None
    if LOGO.exists():
        try:
            logo_img = Image.open(LOGO).convert("RGBA")
            logo_img.thumbnail(
                (int(largeur * 0.20), int(hauteur * 0.17)),
                Image.Resampling.LANCZOS
            )
        except Exception:
            logo_img = None

    if logo_img:
        image.paste(logo_img, (marge, haut_logo), logo_img)
        texte_x = marge + logo_img.width + int(largeur * 0.025)
        dessin.line(
            (
                texte_x - 8, haut_logo + 3,
                texte_x - 8, haut_logo + logo_img.height - 3
            ),
            fill="#1769E8", width=2
        )
    else:
        tour_x = marge + 24
        dessin.rectangle(
            (
                tour_x - 9, haut_logo + 12,
                tour_x + 9, haut_logo + 76
            ),
            outline="#0877C9", width=3
        )
        dessin.line(
            (
                tour_x - 5, haut_logo + 12,
                tour_x - 5, haut_logo + 2
            ),
            fill="#0877C9", width=3
        )
        dessin.line(
            (
                tour_x + 5, haut_logo + 12,
                tour_x + 5, haut_logo + 2
            ),
            fill="#0877C9", width=3
        )
        dessin.arc(
            (
                marge - 4, haut_logo + 30,
                marge + 42, haut_logo + 78
            ),
            190, 330, fill="#0877C9", width=3
        )
        texte_x = marge + 60

    dessin.text(
        (texte_x, haut_logo + 2),
        "AJI TSTAJI", fill="#123D73", font=police_grande
    )
    dessin.text(
        (texte_x, haut_logo + int(hauteur * 0.095)),
        "Trouvez votre prochaine opportunité",
        fill="#315F98", font=police_moyenne
    )
    dessin.text(
        (texte_x, haut_logo + int(hauteur * 0.135)),
        "professionnelle à Marrakech",
        fill="#315F98", font=police_moyenne
    )

    diametre = min(int(largeur * 0.80), int(hauteur * 0.50))
    centre_x = int(largeur * 0.46)
    centre_y = int(hauteur * 0.52)
    gauche = centre_x - diametre // 2
    haut = centre_y - diametre // 2

    if IMAGE_MARRAKECH.exists():
        try:
            photo = Image.open(IMAGE_MARRAKECH).convert("RGB")
            photo = _recadrer(photo, diametre, diametre)
        except Exception:
            photo = Image.new(
                "RGB", (diametre, diametre), "#D3E8FA"
            )
    else:
        photo = Image.new(
            "RGB", (diametre, diametre), "#D3E8FA"
        )

    masque = Image.new("L", (diametre, diametre), 0)
    ImageDraw.Draw(masque).ellipse(
        (0, 0, diametre - 1, diametre - 1), fill=255
    )
    image.paste(photo, (gauche, haut), masque)

    trait_y = min(
        hauteur - 75,
        haut + diametre + int(hauteur * 0.035)
    )
    dessin.rounded_rectangle(
        (
            centre_x - 22, trait_y,
            centre_x + 22, trait_y + 5
        ),
        radius=3, fill="#0877F9"
    )
    dessin.text(
        (centre_x, trait_y + 17),
        "Trouvez les opportunités",
        fill="#315F98", font=police_petite, anchor="mt"
    )
    dessin.text(
        (
            centre_x,
            trait_y + 17 + max(17, int(hauteur * 0.03))
        ),
        "qui correspondent à votre avenir",
        fill="#315F98", font=police_petite, anchor="mt"
    )

    return image


class FenetreReinitialisation(tk.Toplevel):
    """Compact two-step password reset dialog styled for the Desktop app."""

    def __init__(self, page, email=""):
        super().__init__(page.winfo_toplevel())
        self.page = page
        self.email = email.strip().lower()
        self.etape = 1
        self._requete_en_cours = False
        self._boutons_requete = []
        self._action_button = None
        self.title("Mot de passe oublié · AJI TSTAJI")
        self.configure(bg=BLANC)
        self.resizable(True, True)
        self.transient(page.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.update_idletasks()
        parent = page.winfo_toplevel()
        largeur = min(560, max(460, int(parent.winfo_width() * 0.56)))
        hauteur = min(
            640,
            max(560, min(parent.winfo_height() - 70, self.winfo_screenheight() - 100)),
        )
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - largeur) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - hauteur) // 2)
        self.geometry(f"{largeur}x{hauteur}+{x}+{y}")

        tk.Frame(self, bg=BLEU, height=7).pack(fill="x")
        header = tk.Frame(self, bg=BLANC)
        header.pack(fill="x", padx=34, pady=(24, 0))
        tk.Label(
            header, text="AJI TSTAJI", bg=BLANC, fg=BLEU,
            font=(theme.POLICE, 10, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header, text="Mot de passe oublié ?", bg=BLANC,
            fg=BLEU_FONCE, font=(theme.POLICE, 22, "bold"),
        ).pack(anchor="w", pady=(12, 4))
        tk.Label(
            header,
            text="Récupérez l'accès à votre espace en deux étapes.",
            bg=BLANC, fg=GRIS_TEXTE, font=(theme.POLICE, 10),
        ).pack(anchor="w")

        corps = tk.Frame(self, bg=BLANC)
        corps.pack(fill="both", expand=True, padx=34, pady=(24, 10))
        self.body_canvas = tk.Canvas(corps, bg=BLANC, highlightthickness=0, bd=0)
        body_scroll = barre_defilement_moderne(
            corps, self.body_canvas.yview, fond=BLANC
        )
        self.body_canvas.configure(yscrollcommand=body_scroll.set)
        body_scroll.pack(side="right", fill="y")
        self.body_canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.body_canvas, bg=BLANC)
        self._body_window = self.body_canvas.create_window(
            (0, 0), window=self.body, anchor="nw"
        )
        self.body.bind(
            "<Configure>",
            lambda _event: self.body_canvas.configure(
                scrollregion=self.body_canvas.bbox("all")
            ),
        )
        self.body_canvas.bind(
            "<Configure>",
            lambda event: self.body_canvas.itemconfigure(
                self._body_window, width=event.width
            ),
        )
        lier_defilement_molette(self.body_canvas)
        self.error_var = tk.StringVar(value="")
        self._render_step_one()

        ctk.CTkButton(
            self, text="Retour à la connexion", command=self.destroy,
            fg_color="transparent", hover_color="#E8ECFF", text_color=BLEU,
            border_width=0, corner_radius=10, height=40,
            font=(theme.POLICE, 10, "bold"),
        ).pack(pady=(0, 18))
        self.bind("<Return>", self._enter)
        self.grab_set()
        self.focus_force()

    def _clear_body(self):
        for child in self.body.winfo_children():
            child.destroy()
        self._boutons_requete = []
        self._action_button = None

    def _step_badge(self, text):
        tk.Label(
            self.body, text=text, bg=BLEU_CLAIR, fg=BLEU,
            font=(theme.POLICE, 9, "bold"), padx=11, pady=6,
        ).pack(anchor="w", pady=(0, 16))

    def _field_label(self, parent, text):
        tk.Label(
            parent, text=text, bg=BLANC, fg=BLEU_FONCE,
            font=(theme.POLICE, 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

    def _entry(self, parent, *, show="", centered=False, validate=None):
        entry = entree_moderne(
            parent, largeur=440, hauteur=52,
            police=(theme.POLICE, 12), mot_de_passe=show,
            justification="center" if centered else "left",
        )
        if validate is not None:
            entry.configure(
                validate="key",
                validatecommand=(self.register(validate), "%P"),
            )
        entry.pack(fill="x")
        return entry

    def _error_label(self):
        self._lbl_etat = tk.Label(
            self.body, textvariable=self.error_var, bg=BLANC, fg=ROUGE_ERREUR,
            font=(theme.POLICE, 9), wraplength=440, justify="left", anchor="w",
        )
        self._lbl_etat.pack(fill="x", pady=(12, 0))

    def _primary_button(self, text, command):
        self._action_button = ctk.CTkButton(
            self.body, text=text, command=command,
            fg_color=theme.BLEU_CHAT, hover_color=theme.BLEU_CHAT_SURVOL,
            text_color=BLANC, border_width=0, corner_radius=12,
            height=48, font=(theme.POLICE, 11, "bold"),
        )
        self._action_button.pack(fill="x", pady=(20, 0))
        self._boutons_requete.append(self._action_button)

    def _executer_requete(self, texte_attente, operation, terminer):
        if self._requete_en_cours:
            return

        self._requete_en_cours = True
        boutons = list(self._boutons_requete)
        textes_boutons = [(bouton, bouton.cget("text")) for bouton in boutons]
        for bouton in boutons:
            bouton.configure(state="disabled")
        if self._action_button is not None:
            self._action_button.configure(text=texte_attente)
        self.error_var.set(texte_attente)
        self._lbl_etat.configure(fg=GRIS_TEXTE)

        def executer():
            try:
                resultat = operation()
                erreur = None
            except Exception as exc:
                resultat = None
                erreur = exc

            def afficher_resultat():
                try:
                    if not self.winfo_exists():
                        return
                    self._requete_en_cours = False
                    for bouton, texte in textes_boutons:
                        if bouton.winfo_exists():
                            bouton.configure(state="normal", text=texte)
                    if erreur is not None:
                        self.error_var.set(str(erreur))
                        self._lbl_etat.configure(fg=ROUGE_ERREUR)
                    else:
                        terminer(resultat)
                except tk.TclError:
                    return

            try:
                self.page.after(0, afficher_resultat)
            except (RuntimeError, tk.TclError):
                pass

        threading.Thread(target=executer, daemon=True).start()

    def _render_step_one(self):
        self.etape = 1
        self.error_var.set("")
        self._clear_body()
        self._step_badge("ÉTAPE 1 SUR 2")
        tk.Label(
            self.body, text="Quelle est votre adresse e-mail ?", bg=BLANC,
            fg=BLEU_FONCE, font=(theme.POLICE, 13, "bold"),
        ).pack(anchor="w", pady=(0, 14))
        self._field_label(self.body, "Adresse e-mail")
        self.email_entry = self._entry(self.body)
        self.email_entry.insert(0, self.email)
        tk.Label(
            self.body,
            text="Nous vous enverrons un code à 6 chiffres valable 30 minutes.",
            bg=BLANC, fg=GRIS_TEXTE, font=(theme.POLICE, 9),
        ).pack(anchor="w", pady=(9, 0))
        self._error_label()
        self._primary_button("Envoyer le code", self._send_code)
        self.email_entry.focus_set()

    def _send_code(self):
        email = self.email_entry.get().strip().lower()
        if not email or not EMAIL_RE.match(email):
            self.error_var.set("Saisissez une adresse e-mail valide.")
            return
        self._executer_requete(
            "Envoi du code en cours…",
            lambda: _AUTH_CLIENT.request_password_reset(email),
            lambda _resultat: self._code_envoye(email),
        )

    def _code_envoye(self, email):
        self.email = email
        self._render_step_two()

    @staticmethod
    def _digits_only(value):
        return value == "" or (
            value.isascii() and value.isdigit() and len(value) <= 6
        )

    def _render_step_two(self):
        self.etape = 2
        self.error_var.set("")
        self._clear_body()
        self._step_badge("ÉTAPE 2 SUR 2")
        tk.Label(
            self.body, text="Vérifiez votre adresse", bg=BLANC,
            fg=BLEU_FONCE, font=(theme.POLICE, 13, "bold"),
        ).pack(anchor="w")
        tk.Label(
            self.body,
            text=(
                "Si un compte correspond à cette adresse, un code a été envoyé à\n"
                f"{self.email}. Saisissez-le puis choisissez un nouveau mot de passe."
            ),
            bg=BLANC, fg=GRIS_TEXTE, font=(theme.POLICE, 9),
            justify="left", wraplength=440,
        ).pack(anchor="w", pady=(6, 15))

        self._field_label(self.body, "Code reçu par e-mail")
        self.code_entry = self._entry(
            self.body, centered=True, validate=self._digits_only
        )
        self.code_entry.configure(font=(theme.POLICE, 20, "bold"), text_color=BLEU)
        self.code_entry.focus_set()

        self._field_label(self.body, "Nouveau mot de passe")
        self.password_entry = self._entry(self.body, show="*")
        self._field_label(self.body, "Confirmer le mot de passe")
        self.confirm_entry = self._entry(self.body, show="*")

        self._error_label()
        self._primary_button("Enregistrer le nouveau mot de passe", self._confirm)
        actions = tk.Frame(self.body, bg=BLANC)
        actions.pack(fill="x", pady=(10, 0))
        bouton_changer = ctk.CTkButton(
            actions, text="Changer d'adresse", command=self._render_step_one,
            fg_color="transparent", hover_color="#E8ECFF", text_color=BLEU,
            border_width=0, corner_radius=10, height=36,
            font=(theme.POLICE, 9),
        )
        bouton_changer.pack(side="left")
        self._boutons_requete.append(bouton_changer)
        bouton_renvoyer = ctk.CTkButton(
            actions, text="Renvoyer le code", command=self._resend,
            fg_color="transparent", hover_color="#E8ECFF", text_color=BLEU,
            border_width=0, corner_radius=10, height=36,
            font=(theme.POLICE, 9),
        )
        bouton_renvoyer.pack(side="right")
        self._boutons_requete.append(bouton_renvoyer)

    def _resend(self):
        self._executer_requete(
            "Renvoi du code en cours…",
            lambda: _AUTH_CLIENT.request_password_reset(self.email),
            lambda _resultat: self._message_neutre(
                "Si cette adresse correspond à un compte, un nouveau code a été envoyé."
            ),
        )

    def _message_neutre(self, message):
        self.error_var.set(message)
        self._lbl_etat.configure(fg=GRIS_TEXTE)

    def _confirm(self):
        code = self.code_entry.get().strip()
        password = self.password_entry.get()
        confirmation = self.confirm_entry.get()
        if len(code) != 6 or not code.isascii() or not code.isdigit():
            self.error_var.set("Saisissez le code à 6 chiffres reçu par e-mail.")
            return
        if len(password) < 8:
            self.error_var.set("Le mot de passe doit contenir au moins 8 caractères.")
            return
        if password != confirmation:
            self.error_var.set("Les deux mots de passe ne correspondent pas.")
            return
        self._executer_requete(
            "Enregistrement en cours…",
            lambda: _AUTH_CLIENT.confirm_password_reset(self.email, code, password),
            lambda _resultat: self._confirmation_reussie(),
        )

    def _confirmation_reussie(self):
        self.page.email_var.set(self.email)
        self.page.mdp_var.set("")
        self.page._erreur("")
        messagebox.showinfo(
            "Mot de passe modifié",
            "Votre mot de passe a été réinitialisé. Vous pouvez vous connecter.",
            parent=self,
        )
        self.destroy()

    def _enter(self, _event=None):
        self._send_code() if self.etape == 1 else self._confirm()
        return "break"


# -------------------------------------------------------------- Connexion
class Connexion(tk.Frame):

    def __init__(self, parent, app, on_succes=None):
        super().__init__(parent, bg=BLANC)

        self.app = app
        self.on_succes = on_succes
        self.mode = "connexion"
        self._photo = None
        self._tache = None
        self._last_size = (0, 0)
        self._inscription_conteneur = None
        self._show_password = False
        self._auth_en_cours = False
        self.boutons_formulaire = []

        self.canvas = tk.Canvas(
            self, bg=BLEU_CLAIR, highlightthickness=0, bd=0
        )
        self.canvas.place(
            relx=0, rely=0, relwidth=0.53, relheight=1
        )
        self.canvas.bind("<Configure>", self._planifier_dessin)

        self.droite = tk.Frame(self, bg=BLANC)
        self.droite.place(
            relx=0.53, rely=0, relwidth=0.47, relheight=1
        )

        self.zone_formulaire = tk.Frame(self.droite, bg=BLANC)
        self.zone_formulaire.place(
            relx=0.5, rely=0.5, anchor="center",
            relwidth=0.82
        )

        tk.Label(
            self.droite, text="© AJI TSTAJI",
            font=(theme.POLICE, 9),
            fg=GRIS_TEXTE, bg=BLANC
        ).place(relx=0.5, rely=1.0, anchor="s", y=-12)

        self._afficher_connexion()

    # ------------------------------------------------------ Panneau gauche
    def _planifier_dessin(self, event):
        taille = (event.width, event.height)
        if taille == self._last_size:
            return

        self._last_size = taille

        if self._tache:
            try:
                self.after_cancel(self._tache)
            except tk.TclError:
                pass

        self._tache = self.after(
            70,
            lambda w=event.width, h=event.height:
                self._dessiner(w, h)
        )

    def _dessiner(self, largeur, hauteur):
        self._tache = None

        if largeur < 100 or hauteur < 150:
            return

        self.canvas.delete("all")

        if PIL_OK:
            try:
                visuel = construire_visuel(largeur, hauteur)
                self._photo = ImageTk.PhotoImage(visuel)
                self.canvas.create_image(
                    0, 0, image=self._photo, anchor="nw"
                )
                return
            except Exception:
                pass

        self.canvas.create_rectangle(
            0, 0, largeur, hauteur,
            fill=BLEU_CLAIR, outline=""
        )
        self.canvas.create_text(
            largeur // 2, hauteur // 3,
            text="AJI TSTAJI",
            fill=BLEU_FONCE,
            font=(theme.POLICE, 28, "bold")
        )
        self.canvas.create_text(
            largeur // 2, hauteur // 3 + 45,
            text=(
                "Trouvez votre prochaine opportunité\n"
                "professionnelle à Marrakech"
            ),
            fill="#315F98",
            font=(theme.POLICE, 12),
            justify="center"
        )

    # ------------------------------------------------------ Auto-complétion
    def _fichier_suggestions(self):
        """Fichier local contenant uniquement les noms et e-mails."""
        return Path.home() / ".aji_tstaji" / "suggestions.json"

    def _charger_suggestions(self):
        fichier = self._fichier_suggestions()

        try:
            with fichier.open("r", encoding="utf-8") as f:
                donnees = json.load(f)

            if not isinstance(donnees, dict):
                donnees = {}

            emails = donnees.get("email", [])
            noms = donnees.get("nom", [])

            return {
                "email": emails if isinstance(emails, list) else [],
                "nom": noms if isinstance(noms, list) else [],
            }

        except (OSError, ValueError, TypeError):
            return {"email": [], "nom": []}

    def _sauvegarder_suggestion(self, categorie, valeur):
        valeur = valeur.strip()

        if not valeur:
            return

        suggestions = self._charger_suggestions()
        anciennes = suggestions.get(categorie, [])

        suggestions[categorie] = [
            valeur,
            *[
                v for v in anciennes
                if isinstance(v, str)
                and v.lower() != valeur.lower()
            ]
        ][:20]

        fichier = self._fichier_suggestions()

        try:
            fichier.parent.mkdir(parents=True, exist_ok=True)

            with fichier.open("w", encoding="utf-8") as f:
                json.dump(
                    suggestions, f,
                    ensure_ascii=False, indent=2
                )
        except OSError:
            pass

    def _fermer_suggestions(self, entree):
        popup = getattr(entree, "_popup_suggestions", None)

        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass

            entree._popup_suggestions = None

    def _choisir_suggestion(self, entree, variable, valeur):
        variable.set(valeur)
        self._fermer_suggestions(entree)
        entree.focus_set()
        entree.icursor(tk.END)

    def _actualiser_suggestions(
        self, event, entree, variable, categorie
    ):
        if event.keysym == "Escape":
            self._fermer_suggestions(entree)
            return

        if event.keysym in ("Up", "Down", "Return", "Tab"):
            return

        texte = variable.get().strip().lower()
        self._fermer_suggestions(entree)

        if not texte:
            return

        suggestions = self._charger_suggestions().get(
            categorie, []
        )

        correspondances = [
            valeur
            for valeur in suggestions
            if isinstance(valeur, str)
            and valeur.lower().startswith(texte)
            and valeur.lower() != texte
        ][:6]

        if not correspondances:
            return

        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        entree._popup_suggestions = popup

        liste = tk.Listbox(
            popup,
            font=(theme.POLICE, 10),
            bg=BLANC,
            fg="#1F2937",
            selectbackground=BLEU,
            selectforeground=BLANC,
            relief="solid",
            bd=1,
            activestyle="none",
            height=len(correspondances)
        )
        liste.pack(fill="both", expand=True)

        for valeur in correspondances:
            liste.insert(tk.END, valeur)

        x = entree.winfo_rootx()
        y = entree.winfo_rooty() + entree.winfo_height()
        largeur = max(entree.winfo_width(), 220)
        hauteur = len(correspondances) * 24 + 4

        popup.geometry(
            f"{largeur}x{hauteur}+{x}+{y}"
        )
        popup.lift()

        def selectionner(event=None):
            choix = liste.curselection()

            if choix:
                valeur = liste.get(choix[0])
                self._choisir_suggestion(
                    entree, variable, valeur
                )

        liste.bind("<ButtonRelease-1>", selectionner)
        liste.bind("<Return>", selectionner)

    # ------------------------------------------------------ Helpers formulaire
    def _vider(self):
        for widget in self.zone_formulaire.winfo_children():
            widget.destroy()
        self.boutons_formulaire = []

        if self._inscription_conteneur is not None:
            try:
                self._inscription_conteneur.destroy()
            except tk.TclError:
                pass

            self._inscription_conteneur = None

    def _titre(self, titre, sous_titre):
        tk.Label(
            self.zone_formulaire,
            text=titre,
            font=(theme.POLICE, 25, "bold"),
            fg=BLEU_FONCE, bg=BLANC
        ).pack(anchor="w", pady=(0, 5))

        tk.Label(
            self.zone_formulaire,
            text=sous_titre,
            font=(theme.POLICE, 10),
            fg=GRIS_TEXTE, bg=BLANC
        ).pack(anchor="w", pady=(0, 23))

    def _champ(
        self, parent, label, password=False,
        largeur=420, suggestion_key=None
    ):
        cadre = tk.Frame(parent, bg=BLANC)
        cadre.pack(fill="x", pady=8)

        tk.Label(
            cadre,
            text=label,
            font=(theme.POLICE, 10, "bold"),
            fg=BLEU_FONCE, bg=BLANC
        ).pack(anchor="w", pady=(0, 7))

        variable = tk.StringVar()

        enveloppe = ctk.CTkFrame(
            cadre,
            width=largeur,
            height=50,
            fg_color=theme.CHAMP_FOND,
            border_color=theme.CHAMP_BORDURE,
            border_width=1,
            corner_radius=10,
        )
        enveloppe.pack(fill="x")
        enveloppe.pack_propagate(False)

        entree = entree_moderne(
            enveloppe,
            largeur=360,
            hauteur=46,
            police=(theme.POLICE, 11),
            texte_variable=variable,
            mot_de_passe="*" if password else "",
            fg_color="transparent",
            border_width=0,
            corner_radius=0,
        )
        entree.pack(
            side="left", fill="x", expand=True,
            padx=(10, 4)
        )
        entree.bind(
            "<FocusIn>",
            lambda _event, box=enveloppe:
                box.configure(border_color=theme.BLEU_CHAT)
        )
        entree.bind(
            "<FocusOut>",
            lambda _event, box=enveloppe:
                box.configure(border_color=theme.CHAMP_BORDURE)
        )

        # Activer les suggestions uniquement pour les champs concernés.
        if suggestion_key:
            entree.bind(
                "<KeyRelease>",
                lambda event, e=entree, v=variable, k=suggestion_key:
                    self._actualiser_suggestions(
                        event, e, v, k
                    )
            )

            entree.bind(
                "<FocusOut>",
                lambda event, e=entree:
                    e.after(
                        150,
                        lambda: self._fermer_suggestions(e)
                        if e.winfo_exists() else None
                    )
            )

        if password:
            bouton_voir = ctk.CTkButton(
                enveloppe,
                text="Afficher",
                command=None,
                width=76,
                height=36,
                font=(theme.POLICE, 9),
                fg_color="transparent",
                hover_color="#E8ECFF",
                text_color=BLEU,
                corner_radius=8,
                border_width=0,
            )
            bouton_voir.configure(
                command=lambda e=entree, b=bouton_voir:
                    self._basculer_mot_de_passe(e, b)
            )
            bouton_voir.pack(side="right", padx=(0, 5), pady=5)

        return variable

    def _basculer_mot_de_passe(self, entree, bouton):
        self._show_password = not self._show_password
        entree.configure(show="" if self._show_password else "*")
        bouton.configure(
            text="Masquer" if self._show_password else "Afficher"
        )

    def _bouton(self, parent, texte, commande, principal=True):
        bouton = ctk.CTkButton(
            parent,
            text=texte,
            command=commande,
            fg_color=theme.BLEU_CHAT if principal else BLANC,
            hover_color=theme.BLEU_CHAT_SURVOL if principal else "#E8ECFF",
            text_color=BLANC if principal else theme.BLEU_CHAT,
            border_width=0 if principal else 1,
            border_color=theme.CHAMP_BORDURE,
            corner_radius=12,
            height=48,
            font=(theme.POLICE, 11, "bold"),
        )
        bouton.pack(fill="x", pady=(12, 4))
        self.boutons_formulaire.append(bouton)
        return bouton

    def _zone_erreur(self, parent):
        self.lbl_erreur = tk.Label(
            parent,
            text="",
            font=(theme.POLICE, 9),
            fg=ROUGE_ERREUR,
            bg=BLANC,
            wraplength=430,
            justify="left",
            anchor="w"
        )
        self.lbl_erreur.pack(fill="x", pady=(3, 2))

    def _erreur(self, message):
        if hasattr(self, "lbl_erreur"):
            self.lbl_erreur.config(text=message, fg=ROUGE_ERREUR)

    # ------------------------------------------------------ Connexion

    def _afficher_connexion(self):
        self.mode = "connexion"
        self._vider()

        formulaire = self.zone_formulaire

        self._titre(
            "Connexion",
            "Accédez à votre espace personnel"
        )

        self.email_var = self._champ(
            formulaire,
            "Adresse e-mail",
            suggestion_key="email"
        )

        self.mdp_var = self._champ(
            formulaire,
            "Mot de passe",
            password=True
        )

        # Mot de passe oublié
        lbl_oubli = tk.Label(
            formulaire,
            text="Mot de passe oublié ?",
            font=(theme.POLICE, 9),
            fg=BLEU,
            bg=BLANC,
            cursor="hand2"
        )
        lbl_oubli.pack(anchor="e", pady=(2, 6))

        lbl_oubli.bind(
            "<Button-1>",
            lambda event: self._mot_de_passe_oublie()
        )

        self._zone_erreur(formulaire)

        self._bouton(
            formulaire,
            "Se connecter  →",
            self._valider
        )

        separateur = tk.Frame(formulaire, bg=BLANC)
        separateur.pack(fill="x", pady=(12, 5))

        tk.Frame(
            separateur, bg="#D8E1ED", height=1
        ).pack(
            side="left", fill="x", expand=True, pady=8
        )

        tk.Label(
            separateur,
            text="ou",
            font=(theme.POLICE, 9),
            fg=GRIS_TEXTE,
            bg=BLANC,
            padx=12
        ).pack(side="left")

        tk.Frame(
            separateur, bg="#D8E1ED", height=1
        ).pack(
            side="left", fill="x", expand=True, pady=8
        )

        self._bouton(
            formulaire,
            "Créer un compte",
            self._afficher_inscription,
            principal=False
        )


    # ------------------------------------------------------ Inscription scrollable
    def _creer_formulaire_scrollable(self):
        conteneur = tk.Frame(self.droite, bg=BLANC)
        conteneur.place(
            relx=0.5, rely=0.03, anchor="n",
            relwidth=0.84, relheight=0.90
        )

        canvas = tk.Canvas(
            conteneur, bg=BLANC,
            highlightthickness=0, bd=0
        )

        scrollbar = barre_defilement_moderne(
            conteneur, canvas.yview, fond=BLANC
        )

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        formulaire = tk.Frame(canvas, bg=BLANC)

        fenetre = canvas.create_window(
            (0, 0), window=formulaire, anchor="nw"
        )

        formulaire.bind(
            "<Configure>",
            lambda event:
                canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.bind(
            "<Configure>",
            lambda event:
                canvas.itemconfigure(fenetre, width=event.width)
        )
        lier_defilement_molette(canvas)

        return conteneur, formulaire

    def _afficher_inscription(self):
        self.mode = "inscription"
        self._vider()

        conteneur, formulaire = self._creer_formulaire_scrollable()
        self._inscription_conteneur = conteneur

        self.zone_formulaire.place_forget()

        tk.Label(
            formulaire,
            text="Créer un compte",
            font=(theme.POLICE, 24, "bold"),
            fg=BLEU_FONCE, bg=BLANC
        ).pack(anchor="w", pady=(8, 4))

        tk.Label(
            formulaire,
            text=(
                "Complétez vos informations pour "
                "personnaliser votre espace."
            ),
            font=(theme.POLICE, 10),
            fg=GRIS_TEXTE, bg=BLANC,
            wraplength=470,
            justify="left"
        ).pack(anchor="w", pady=(0, 16))

        self.nom_var = self._champ(
            formulaire,
            "Nom complet",
            suggestion_key="nom"
        )

        self.email_var = self._champ(
            formulaire,
            "Adresse e-mail",
            suggestion_key="email"
        )

        self.telephone_var = self._champ(
            formulaire, "Téléphone"
        )
        self.ville_var = self._champ(
            formulaire, "Ville"
        )
        self.etablissement_var = self._champ(
            formulaire, "Établissement"
        )
        self.filiere_var = self._champ(
            formulaire, "Filière / domaine"
        )
        self.diplome_var = self._champ(
            formulaire, "Diplôme préparé"
        )

        cadre = tk.Frame(formulaire, bg=BLANC)
        cadre.pack(fill="x", pady=8)

        tk.Label(
            cadre,
            text="Type d'opportunité recherchée",
            font=(theme.POLICE, 10, "bold"),
            fg=BLEU_FONCE, bg=BLANC
        ).pack(anchor="w", pady=(0, 7))

        self.recherche_var = tk.StringVar(value="Stage")

        liste_moderne(
            cadre,
            [
                "Stage",
                "Stage de fin d'études (PFE)",
                "Emploi",
                "Alternance"
            ],
            state="readonly",
            police=(theme.POLICE, 10),
            variable=self.recherche_var,
        ).pack(fill="x")

        self.mdp_var = self._champ(
            formulaire, "Mot de passe", password=True
        )

        self.confirm_var = self._champ(
            formulaire, "Confirmer le mot de passe",
            password=True
        )

        self._zone_erreur(formulaire)

        self._bouton(
            formulaire,
            "Créer mon compte",
            self._valider
        )

        self._bouton(
            formulaire,
            "Retour à la connexion",
            self._retour_connexion,
            principal=False
        )

    def _retour_connexion(self):
        if self._inscription_conteneur is not None:
            self._inscription_conteneur.destroy()
            self._inscription_conteneur = None

        self.zone_formulaire.place(
            relx=0.5, rely=0.5, anchor="center",
            relwidth=0.82
        )

        self._afficher_connexion()

    def _mot_de_passe_oublie(self):
        email = self.email_var.get().strip().lower()
        self._erreur("")
        FenetreReinitialisation(self, email)

    # ------------------------------------------------------ Validation
    def _valider(self):
        if self._auth_en_cours:
            return

        email = self.email_var.get().strip().lower()
        mdp = self.mdp_var.get()

        if not email or not mdp:
            self._erreur(
                "Veuillez remplir les champs obligatoires."
            )
            return

        if not EMAIL_RE.match(email):
            self._erreur(
                "Veuillez saisir une adresse e-mail valide."
            )
            return

        # ---------------------------- Connexion
        if self.mode == "connexion":
            self._executer_auth_en_arriere_plan(
                "Connexion en cours…",
                lambda: self._authentifier(email, mdp),
                lambda resultat: self._terminer(
                    email, resultat[1], resultat[0]
                ),
            )
            return

        # ---------------------------- Création de compte
        nom = self.nom_var.get().strip()
        confirmation = self.confirm_var.get()

        informations = {
            "telephone": self.telephone_var.get().strip(),
            "ville": self.ville_var.get().strip() or "Marrakech",
            "etablissement": self.etablissement_var.get().strip(),
            "secteur": self.filiere_var.get().strip(),
            "diplome": self.diplome_var.get().strip(),
            "recherche": self.recherche_var.get(),
        }

        if not nom:
            self._erreur(
                "Veuillez saisir votre nom complet."
            )
            return

        champs_obligatoires = {
            "Téléphone": informations["telephone"],
            "Établissement": informations["etablissement"],
            "Filière": informations["secteur"],
            "Diplôme préparé": informations["diplome"],
        }

        for label, valeur in champs_obligatoires.items():
            if not valeur:
                self._erreur(
                    f"Veuillez renseigner : {label}."
                )
                return

        if len(mdp) < 8:
            self._erreur(
                "Le mot de passe doit contenir au moins 8 caractères."
            )
            return

        if mdp != confirmation:
            self._erreur(
                "Les mots de passe ne correspondent pas."
            )
            return

        self._executer_auth_en_arriere_plan(
            "Création du compte en cours…",
            lambda: self._inscrire(email, mdp, nom, informations),
            lambda auth_session: self._terminer(email, nom, auth_session),
        )

    def _executer_auth_en_arriere_plan(self, texte_attente, operation, terminer):
        if self._auth_en_cours:
            return

        self._auth_en_cours = True
        boutons = list(self.boutons_formulaire)
        textes_boutons = [(bouton, bouton.cget("text")) for bouton in boutons]
        for bouton in boutons:
            bouton.configure(state="disabled")
        self.lbl_erreur.config(text=texte_attente, fg=GRIS_TEXTE)
        racine = self.winfo_toplevel()

        def executer():
            try:
                resultat = operation()
                erreur = None
            except Exception as exc:
                resultat = None
                erreur = exc

            def afficher_resultat():
                try:
                    if not self.winfo_exists():
                        return
                    self._auth_en_cours = False
                    for bouton, texte in textes_boutons:
                        if bouton.winfo_exists():
                            bouton.configure(state="normal", text=texte)
                    if erreur is not None:
                        self._erreur(str(erreur))
                    else:
                        terminer(resultat)
                except tk.TclError:
                    return

            try:
                racine.after(0, afficher_resultat)
            except (RuntimeError, tk.TclError):
                pass

        threading.Thread(target=executer, daemon=True).start()

    def _authentifier(self, email, mot_de_passe):
        try:
            auth_session = _AUTH_CLIENT.login(email, mot_de_passe)
        except AuthAPIError as api_error:
            if api_error.status_code != 401:
                raise

            # Migrer uniquement un ancien compte dont les identifiants locaux sont valides.
            try:
                legacy_ok, legacy_message, legacy_name = verifier(email, mot_de_passe)
            except Exception as erreur:
                raise AuthAPIError(
                    f"Erreur de migration du compte historique : {erreur}"
                ) from erreur
            if not legacy_ok:
                raise AuthAPIError(
                    legacy_message or "E-mail ou mot de passe incorrect.", 401
                )

            try:
                initialiser_base()
                ancien_profil = obtenir_profil_utilisateur(email) or {}
                nom_legacy = legacy_name.strip() or email.split("@", 1)[0]
                parties = nom_legacy.split(maxsplit=1)
                auth_session = _AUTH_CLIENT.register(
                    email,
                    mot_de_passe,
                    display_name=nom_legacy,
                    first_name=ancien_profil.get("prenom") or (parties[0] if parties else ""),
                    last_name=ancien_profil.get("nom") or (parties[1] if len(parties) > 1 else ""),
                    phone=ancien_profil.get("telephone", ""),
                    city=ancien_profil.get("ville", "Marrakech"),
                    diploma=ancien_profil.get("diplome", ""),
                    sector=ancien_profil.get("secteur", ""),
                    institution=ancien_profil.get("etablissement", ""),
                    skills=ancien_profil.get("competences", ""),
                    job_search=ancien_profil.get("recherche", ""),
                )
            except AuthAPIError as erreur:
                if erreur.status_code == 400:
                    raise AuthAPIError("E-mail ou mot de passe incorrect.", 400) from erreur
                raise
            except Exception as erreur:
                raise AuthAPIError(
                    f"Erreur lors de la migration du compte : {erreur}"
                ) from erreur

        nom = (
            auth_session.user.get("display_name", "").strip()
            or email.split("@", 1)[0]
        )
        try:
            initialiser_base()
            profil = obtenir_profil_utilisateur(email)
            if not profil:
                parties = nom.split(maxsplit=1)
                enregistrer_profil_utilisateur(
                    email,
                    {
                        "prenom": parties[0] if parties else nom,
                        "nom": parties[1] if len(parties) > 1 else "",
                        "ville": "Marrakech",
                        "email": email,
                    },
                )
        except Exception as erreur:
            raise AuthAPIError(
                f"Erreur lors du chargement du profil : {erreur}"
            ) from erreur

        self._sauvegarder_suggestion("email", email)
        self._sauvegarder_suggestion("nom", nom)
        return auth_session, nom

    def _inscrire(self, email, mot_de_passe, nom, informations):
        parties_nom = nom.split(maxsplit=1)
        try:
            auth_session = _AUTH_CLIENT.register(
                email,
                mot_de_passe,
                display_name=nom,
                first_name=parties_nom[0],
                last_name=parties_nom[1] if len(parties_nom) > 1 else "",
                phone=informations["telephone"],
                city=informations["ville"],
                institution=informations["etablissement"],
                sector=informations["secteur"],
                diploma=informations["diplome"],
                job_search=informations["recherche"],
            )

            # Ne jamais remplacer un profil local déjà présent.
            initialiser_base()
            if not obtenir_profil_utilisateur(email):
                enregistrer_profil_utilisateur(
                    email,
                    {
                        "prenom": parties_nom[0],
                        "nom": parties_nom[1] if len(parties_nom) > 1 else "",
                        "email": email,
                        "telephone": informations["telephone"],
                        "ville": informations["ville"],
                        "etablissement": informations["etablissement"],
                        "secteur": informations["secteur"],
                        "diplome": informations["diplome"],
                        "recherche": informations["recherche"],
                    },
                )
        except AuthAPIError:
            raise
        except Exception as erreur:
            raise AuthAPIError(
                f"Erreur lors de la création du compte : {erreur}"
            ) from erreur

        self._sauvegarder_suggestion("email", email)
        self._sauvegarder_suggestion("nom", nom)
        return auth_session

    def _terminer(self, email, nom, auth_session=None):
        """Appelée après une connexion ou une inscription réussie."""
        if self.app is not None and auth_session is not None:
            self.app.auth_session = auth_session
        if self.on_succes:
            self.on_succes(email, nom)
        else:
            messagebox.showinfo(
                "Connexion réussie",
                f"Bonjour {nom} !"
            )
