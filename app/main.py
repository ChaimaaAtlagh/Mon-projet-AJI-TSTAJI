"""
main.py
Fenêtre principale de l'application AJI TSTAJI : page de connexion, barre de
navigation et changement de page.

Lancement (depuis la racine du projet) :
    python app/main.py
"""

import sys
import threading
import tkinter as tk
from pathlib import Path
import customtkinter as ctk
RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))
from app.chatbot_page import ChatbotPage, creer_icone_robot
from app import theme
from src.utils.paths import chemin_ressource
from app.pages.page_vide import PageVide
from app.pages.connexion import Connexion
from app.pages.accueil import Accueil
from app.pages.entreprises import Entreprises
from app.pages.opportunites import Opportunites
from app.pages.mon_profil import MonProfil
from app.pages.candidature import Candidature
from app.pages.mes_candidatures import MesCandidatures
from app.pages.analyse import Analyse
from src.utils.charger_donnees import charger_entreprises



PAGES_MENU = [
    "Accueil",
    "Entreprises",
    "Opportunités",
    "Mes candidatures",
    "Analyse",
    "Candidature",
    "Mon profil",
]

ICONE_PAGE = {
    "Accueil": "accueil",
    "Entreprises": "entreprises",
    "Opportunités": "opportunites",
    "Mes candidatures": "candidatures",
    "Analyse": "analyse",
    "Candidature": "candidature",
    "Mon profil": "profil",
}
LARGEUR_SIDEBAR = 246
LARGEUR_SIDEBAR_REDUITE = 78

PAGES_REELLES = {
    "Accueil": Accueil,
    "Entreprises": Entreprises,
    "Opportunités": Opportunites,
    "Mon profil": MonProfil,
    "Candidature": Candidature,
    "Mes candidatures": MesCandidatures,
    "Analyse": Analyse,
}


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AJI TSTAJI")
        try:
            self.iconbitmap(str(chemin_ressource("app", "assets", "AJI_TSTAJI.ico")))
        except (tk.TclError, OSError):
            pass
        self.geometry("1280x800")
        self.minsize(1000, 650)
        try:
            self.state("zoomed")
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)   # Linux
            except tk.TclError:
                pass
        theme.appliquer_style(self)

        self.donnees = None
        self.recherche = {"texte": "", "quartier": ""}
        self.entreprise_choisie = None

        # utilisateur connecté (disponible pour toutes les pages via app.utilisateur)
        self.utilisateur = None          # e-mail
        self.nom_utilisateur = ""
        self.auth_session = None          # jetons backend conservés en mémoire
        self.candidatures_revision = 0

        self.pages = {}
        self.liens = {}
        self.traits = {}
        self.page_active = None
        self.page_precedente = "Accueil"
        self.bouton_ia = None
        self.image_robot = None
        self.panneau_chatbot = None      # chatbot en demi-page (à droite)
        self._widgets_session = []       # barre + zone des pages (détruits à la déconnexion)
        self.navigation_reduite = False

        self._afficher_connexion()

    # ------------------------------------------------------------ connexion
    def _afficher_connexion(self):
        self.connexion = Connexion(self, self, on_succes=self._apres_connexion)
        self.connexion.pack(fill="both", expand=True)

    def _apres_connexion(self, email, nom):
        self.utilisateur = email.strip().lower()
        self.nom_utilisateur = nom

        try:
            if self.donnees is None:
                self.donnees = charger_entreprises()
            self.connexion.destroy()
            self._creer_barre()
            self._creer_pages()
            self.afficher_page("Accueil")
            self._creer_bouton_ia()
            self.focus_set()

        except Exception:
            import traceback
            from tkinter import messagebox

            erreur = traceback.format_exc()
            print(erreur)
            messagebox.showerror("Erreur AJI TSTAJI", erreur)

    # --------------------------------------------------------- bouton robot IA
    def _creer_bouton_ia(self):
        """Petit bouton robot rond en bas à droite (sans texte)."""
        self.image_robot = ctk.CTkImage(
            creer_icone_robot(120, rayon=0.5), size=(60, 60))
        self.bouton_ia = ctk.CTkButton(
            self,
            text="",
            image=self.image_robot,
            fg_color="transparent",
            hover_color=theme.FOND,
            border_width=0,
            corner_radius=30,
            width=60,
            height=60,
            command=self.ouvrir_chatbot,
        )
        self._mettre_a_jour_bouton_ia()

    def _mettre_a_jour_bouton_ia(self):
        """Le bouton robot est visible, sauf quand le panneau chatbot est ouvert."""
        if self.bouton_ia is None:
            return
        if self.panneau_chatbot is not None and self.panneau_chatbot.winfo_ismapped():
            self.bouton_ia.place_forget()
        else:
            self.bouton_ia.place(relx=0.98, rely=0.96, anchor="se")
            self.bouton_ia.lift()

    def ouvrir_chatbot(self):
        """Ouvre le chatbot en demi-page à droite, par-dessus la page en cours."""
        if self.utilisateur is None:
            return
        if self.panneau_chatbot is None:
            self.panneau_chatbot = ChatbotPage(
                self, app=self, fermer=self.fermer_chatbot
            )
        self.panneau_chatbot.place(relx=0.5, rely=0.1, relwidth=0.5, relheight=0.88)
        self.panneau_chatbot.lift()
        self._mettre_a_jour_bouton_ia()

    def fermer_chatbot(self):
        if self.panneau_chatbot is not None:
            self.panneau_chatbot.place_forget()
        self._mettre_a_jour_bouton_ia()

    def basculer_chatbot(self):
        if self.panneau_chatbot is not None and self.panneau_chatbot.winfo_ismapped():
            self.fermer_chatbot()
        else:
            self.ouvrir_chatbot()

    # ancien nom conservé pour ne rien casser si une autre page l'utilise
    _basculer_chatbot = ouvrir_chatbot

    def deconnecter(self):
        """Ferme la session et revient à la connexion."""
        session = self.auth_session
        self.auth_session = None
        if session is not None:
            threading.Thread(
                target=self._fermer_session_en_arriere_plan,
                args=(session,),
                daemon=True,
            ).start()

        for widget in self._widgets_session:
            widget.destroy()

        if self.bouton_ia is not None:
            self.bouton_ia.destroy()
            self.bouton_ia = None

        if self.panneau_chatbot is not None:
            self.panneau_chatbot.destroy()
            self.panneau_chatbot = None

        self._widgets_session = []
        self.pages, self.liens, self.traits = {}, {}, {}
        self.page_active = None
        self.page_precedente = "Accueil"
        self.utilisateur = None
        self.nom_utilisateur = ""
        self.recherche = {"texte": "", "quartier": ""}
        self.entreprise_choisie = None
        self.candidatures_revision = 0
        self._afficher_connexion()

    @staticmethod
    def _fermer_session_en_arriere_plan(session):
        try:
            session.logout()
        except Exception:
            # Une panne réseau ne doit pas empêcher la déconnexion locale.
            pass

    # ----------------------------------------------------------- navigation
    def _creer_barre(self):
        self.zone_session = tk.Frame(self, bg=theme.FOND)
        self.zone_session.pack(fill="both", expand=True)
        self._widgets_session.append(self.zone_session)

        self.sidebar = ctk.CTkFrame(
            self.zone_session, fg_color=theme.BLANC, width=LARGEUR_SIDEBAR,
            corner_radius=16, border_width=1, border_color=theme.BORDURE,
        )
        self.sidebar.pack(side="left", fill="y", padx=(8, 6), pady=8)
        self.sidebar.pack_propagate(False)

        self.zone_contenu = tk.Frame(self.zone_session, bg=theme.FOND)
        self.zone_contenu.pack(side="left", fill="both", expand=True,
                               padx=(0, 8), pady=8)

        entete = tk.Frame(self.sidebar, bg=theme.BLANC)
        entete.pack(fill="x", padx=12, pady=(10, 14))
        ligne_reduction = tk.Frame(entete, bg=theme.BLANC)
        ligne_reduction.pack(fill="x", pady=(0, 2))
        self.bouton_reduire = ctk.CTkButton(
            ligne_reduction, text="«", width=34, height=34, corner_radius=17,
            border_width=1, border_color=theme.BORDURE,
            fg_color=theme.BLANC, hover_color="#E8ECFF", text_color=theme.BLEU,
            font=(theme.POLICE, 15, "bold"), command=self.basculer_sidebar,
        )
        self.bouton_reduire.pack(side="right")

        self.zone_logo = tk.Frame(entete, bg=theme.BLANC)
        self.zone_logo.pack(fill="x", pady=(0, 5))
        self.logo_symbole = tk.Canvas(
            self.zone_logo, width=48, height=56, bg=theme.BLANC,
            highlightthickness=0, bd=0,
        )
        self.logo_texte = tk.Frame(self.zone_logo, bg=theme.BLANC)
        self.logo_nom = tk.Label(
            self.logo_texte, text="AJI TSTAJI", font=(theme.POLICE, 16, "bold"),
            fg=theme.BLEU, bg=theme.BLANC,
        )
        self.logo_nom.pack(anchor="w", pady=(7, 2))
        self.logo_accroche = tk.Label(
            self.logo_texte, text="Ton avenir professionnel\ncommence ici",
            font=(theme.POLICE, 9, "bold"), fg=theme.BLEU,
            bg=theme.BLANC, justify="left",
        )
        self.logo_accroche.pack(anchor="w")
        self._dessiner_logo_sidebar()

        separateur = tk.Frame(self.sidebar, bg=theme.BORDURE, height=1)
        separateur.pack(fill="x", padx=14, pady=(0, 14))
        self.zone_liens = tk.Frame(self.sidebar, bg=theme.BLANC)
        self.zone_liens.pack(fill="both", expand=True)

        self.liens = {}
        self.traits = {}
        for nom in PAGES_MENU:
            self._creer_lien(nom)

        bas = tk.Frame(self.sidebar, bg=theme.BLANC)
        bas.pack(side="bottom", fill="x", padx=12, pady=(8, 8))
        tk.Frame(bas, bg=theme.BORDURE, height=1).pack(fill="x", pady=(0, 8))
        self.bouton_deconnexion = ctk.CTkButton(
            bas, text="↪  Déconnexion", anchor="w", height=44,
            corner_radius=10, fg_color="transparent", hover_color="#FDECEC",
            text_color="#D84343", font=(theme.POLICE, 12, "bold"),
            command=self.deconnecter,
        )
        self.bouton_deconnexion.pack(fill="x")
        self.decoration_sidebar = tk.Canvas(
            bas, height=84, bg=theme.BLANC, highlightthickness=0, bd=0,
        )
        self.decoration_sidebar.pack(fill="x", pady=(8, 0))
        self.decoration_sidebar.bind(
            "<Configure>", self._dessiner_decoration_sidebar
        )
        self._actualiser_sidebar()

    def _dessiner_logo_sidebar(self):
        """Dessine une petite épingle de Marrakech avec une mallette au centre."""
        canevas = self.logo_symbole
        canevas.create_rectangle(0, 0, 48, 56, fill=theme.BLANC, outline=theme.BLANC)
        # Silhouette de ville derrière l'épingle.
        for x, hauteur in ((2, 12), (8, 17), (39, 14), (44, 20)):
            canevas.create_rectangle(
                x, 53 - hauteur, x + 5, 53,
                fill="#DCEBFF", outline="#DCEBFF",
            )
        canevas.create_polygon(
            24, 54, 8, 29, 7, 21, 10, 12, 17, 7, 24, 5,
            31, 7, 38, 12, 41, 21, 40, 29,
            fill=theme.BLEU, outline=theme.BLEU,
        )
        canevas.create_oval(13, 11, 35, 33, fill=theme.BLANC, outline=theme.BLANC)
        canevas.create_rectangle(17, 19, 31, 28, fill=theme.BLEU, outline=theme.BLEU)
        canevas.create_rectangle(21, 16, 27, 20, fill=theme.BLEU, outline=theme.BLEU)
        canevas.create_line(21, 16, 27, 16, fill=theme.BLEU, width=2)
        canevas.create_line(17, 22, 31, 22, fill=theme.BLANC, width=1)

    def _dessiner_decoration_sidebar(self, evenement=None):
        """Décor discret de skyline en bleu pâle au bas du menu."""
        canevas = self.decoration_sidebar
        largeur = max(1, evenement.width if evenement else canevas.winfo_width())
        hauteur = max(1, evenement.height if evenement else canevas.winfo_height())
        base = hauteur - 2
        loin, proche = "#EEF5FF", "#E2EEFF"
        canevas.delete("all")
        canevas.create_rectangle(0, base - 23, largeur, base, fill=loin, outline=loin)
        for index, proportion in enumerate((.08, .19, .31, .69, .81, .93)):
            x = int(largeur * proportion)
            h = 25 + (index * 13 % 28)
            w = max(8, int(largeur * .08))
            canevas.create_rectangle(
                x, base - h, x + w, base,
                fill=proche if index % 2 else loin,
                outline=proche if index % 2 else loin,
            )
        centre = largeur // 2
        canevas.create_rectangle(
            centre - 7, base - 62, centre + 7, base,
            fill="#D8E8FF", outline="#D8E8FF",
        )
        canevas.create_rectangle(
            centre - 10, base - 42, centre + 10, base - 39,
            fill="#D8E8FF", outline="#D8E8FF",
        )
        canevas.create_polygon(
            centre - 9, base - 62, centre, base - 76,
            centre + 9, base - 62,
            fill="#D8E8FF", outline="#D8E8FF",
        )

    def _creer_lien(self, nom):
        ligne = ctk.CTkFrame(
            self.zone_liens, fg_color="transparent", corner_radius=10,
            height=48,
        )
        ligne.pack(fill="x", padx=12, pady=4)
        ligne.pack_propagate(False)
        icone = tk.Canvas(
            ligne, width=30, height=30, bg=theme.BLANC,
            highlightthickness=0, bd=0,
        )
        icone.pack(side="left", padx=(14, 10), pady=8)
        etiquette = tk.Label(
            ligne, text=nom, anchor="w", font=theme.GRAS,
            fg="#000000", bg=theme.BLANC,
        )
        etiquette.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def ouvrir_page(_evenement=None, page=nom):
            self.afficher_page(page)
            return "break"

        for widget in (ligne, icone, etiquette):
            widget.bind("<Button-1>", ouvrir_page)
        self.liens[nom] = {
            "ligne": ligne,
            "icone": icone,
            "etiquette": etiquette,
        }

    @staticmethod
    def _dessiner_icone_menu(canevas, nom, couleur):
        """Dessine les icônes de navigation en traits, sans image externe."""
        canevas.delete("all")
        trait = {"fill": couleur, "width": 2}

        if nom == "accueil":
            canevas.create_line(4, 13, 15, 4, 26, 13, **trait, joinstyle="round")
            canevas.create_line(7, 12, 7, 26, 23, 26, 23, 12, **trait)
            canevas.create_rectangle(13, 18, 18, 26, outline=couleur, width=2)
        elif nom == "entreprises":
            canevas.create_rectangle(3, 11, 12, 26, outline=couleur, width=2)
            canevas.create_rectangle(13, 5, 26, 26, outline=couleur, width=2)
            for x, y in ((6, 14), (9, 14), (6, 19), (9, 19),
                         (17, 9), (22, 9), (17, 14), (22, 14), (17, 19), (22, 19)):
                canevas.create_rectangle(x, y, x + 1, y + 1, fill=couleur, outline=couleur)
        elif nom == "opportunites":
            canevas.create_rectangle(3, 10, 27, 25, outline=couleur, width=2)
            canevas.create_line(10, 10, 10, 7, 12, 5, 18, 5, 20, 7, 20, 10, **trait)
            canevas.create_line(3, 16, 27, 16, **trait)
            canevas.create_rectangle(12, 14, 18, 18, fill=couleur, outline=couleur)
        elif nom == "candidatures":
            canevas.create_polygon(3, 12, 27, 4, 19, 26, 13, 17, 3, 12,
                                   fill="", outline=couleur, width=2)
            canevas.create_line(13, 17, 27, 4, **trait)
            canevas.create_line(13, 17, 14, 25, 19, 26, **trait)
        elif nom == "analyse":
            canevas.create_line(4, 26, 27, 26, **trait)
            canevas.create_rectangle(6, 17, 10, 25, outline=couleur, width=2)
            canevas.create_rectangle(14, 11, 18, 25, outline=couleur, width=2)
            canevas.create_rectangle(22, 5, 26, 25, outline=couleur, width=2)
        elif nom == "candidature":
            canevas.create_polygon(7, 3, 19, 3, 25, 9, 25, 27, 7, 27,
                                   fill="", outline=couleur, width=2)
            canevas.create_line(19, 3, 19, 9, 25, 9, **trait)
            canevas.create_line(11, 14, 21, 14, **trait)
            canevas.create_line(11, 18, 21, 18, **trait)
            canevas.create_line(11, 22, 18, 22, **trait)
        elif nom == "profil":
            canevas.create_oval(10, 4, 20, 14, outline=couleur, width=2)
            canevas.create_arc(4, 12, 26, 29, start=0, extent=180,
                               style="arc", outline=couleur, width=2)

    def basculer_sidebar(self):
        self.navigation_reduite = not self.navigation_reduite
        self._actualiser_sidebar()

    def _actualiser_sidebar(self):
        reduite = self.navigation_reduite
        if hasattr(self, "sidebar"):
            self.sidebar.configure(
                width=LARGEUR_SIDEBAR_REDUITE if reduite else LARGEUR_SIDEBAR
            )
        if hasattr(self, "logo_nom"):
            self.logo_symbole.pack_forget()
            self.logo_texte.pack_forget()
            if reduite:
                self.logo_symbole.pack(anchor="center")
                self.bouton_reduire.configure(text="»")
                self.decoration_sidebar.pack_forget()
            else:
                self.logo_symbole.pack(side="left", padx=(0, 8))
                self.logo_texte.pack(side="left")
                self.bouton_reduire.configure(text="«")
                self.decoration_sidebar.pack(fill="x", pady=(8, 0))

        for nom, elements in self.liens.items():
            actif = nom == self.page_active
            fond = theme.BLEU if actif else "transparent"
            couleur = theme.BLANC if actif else "#111111"
            elements["ligne"].configure(fg_color=fond)
            elements["icone"].configure(bg=theme.BLEU if actif else theme.BLANC)
            elements["etiquette"].configure(
                fg=couleur, bg=theme.BLEU if actif else theme.BLANC,
                font=(theme.POLICE, 12, "bold"),
            )
            self._dessiner_icone_menu(elements["icone"], ICONE_PAGE[nom], couleur)
            elements["icone"].pack_forget()
            elements["etiquette"].pack_forget()
            if reduite:
                elements["icone"].pack(anchor="center", pady=8)
            else:
                elements["icone"].pack(side="left", padx=(14, 10), pady=8)
                elements["etiquette"].pack(
                    side="left", fill="x", expand=True, padx=(0, 8)
                )
        if hasattr(self, "bouton_deconnexion"):
            self.bouton_deconnexion.configure(
                text="↪" if reduite else "↪  Déconnexion",
                anchor="center" if reduite else "w",
                text_color="#D84343",
                fg_color="#FEF2F2" if reduite else "transparent",
            )

    # -------------------------------------------------------------- pages
    def _creer_pages(self):
        self.zone_pages = tk.Frame(self.zone_contenu, bg=theme.FOND)
        self.zone_pages.pack(fill="both", expand=True)
        self.pages = {}
        self.panneau_chatbot = None

    def afficher_page(self, nom):
        ancienne_page = self.pages.get(self.page_active)
        if ancienne_page is not None and self.page_active != nom:
            ancienne_page.pack_forget()

        page = self.pages.get(nom)
        if page is None:
            classe_page = PAGES_REELLES.get(nom)
            page = (
                classe_page(self.zone_pages, self)
                if classe_page is not None
                else PageVide(self.zone_pages, self, nom)
            )
            self.pages[nom] = page

        self.page_active = nom
        self.page_precedente = nom
        page.pack(fill="both", expand=True)

        if hasattr(page, "actualiser"):
            page.actualiser()

        self._actualiser_sidebar()

        # garder le chatbot et le bouton robot au-dessus de la nouvelle page
        if self.panneau_chatbot is not None and self.panneau_chatbot.winfo_ismapped():
            self.panneau_chatbot.lift()
        self._mettre_a_jour_bouton_ia()


if __name__ == "__main__":
    app = Application()
    app.mainloop()
