"""Widgets réutilisables au style moderne AJI TSTAJI.

Les champs reprennent le fond doux, les bordures fines et les coins arrondis
de l'interface du chatbot. Ils restent utilisables dans les pages Tkinter.
"""

from tkinter import font as tkfont
import weakref

import customtkinter as ctk
from types import SimpleNamespace

from app import theme

RAYON = 12
POLICE_BOUTON = (theme.POLICE, 11, "bold")


def entree_moderne(parent, *, largeur=260, hauteur=46, police=None,
                   texte_variable=None, placeholder=None, mot_de_passe="",
                   justification="left", **options):
    """Construit un champ CustomTkinter avec les méthodes habituelles d'Entry."""
    configuration = {
        "width": largeur,
        "height": hauteur,
        "font": police or theme.NORMAL,
        "textvariable": texte_variable,
        "placeholder_text": placeholder,
        "placeholder_text_color": theme.CHAMP_PLACEHOLDER,
        "show": mot_de_passe,
        "justify": justification,
        "fg_color": theme.CHAMP_FOND,
        "text_color": theme.CHAMP_TEXTE,
        "border_color": theme.CHAMP_BORDURE,
        "border_width": 1,
        "corner_radius": 10,
    }
    configuration.update(options)
    return ctk.CTkEntry(parent, **configuration)


def zone_texte_moderne(parent, *, largeur=520, hauteur=120, police=None,
                       retour_ligne="word", **options):
    """Construit une zone multiligne arrondie, compatible avec Text.get/insert."""
    return ctk.CTkTextbox(
        parent,
        width=largeur,
        height=hauteur,
        font=police or theme.NORMAL,
        wrap=retour_ligne,
        fg_color=theme.CHAMP_FOND,
        text_color=theme.CHAMP_TEXTE,
        border_color=theme.CHAMP_BORDURE,
        border_width=1,
        corner_radius=10,
        **options,
    )


class ListeDeroulanteModerne(ctk.CTkComboBox):
    """Menu arrondi qui conserve l'API current/get/set et l'événement ttk usuel."""

    def __init__(self, parent, *, valeurs, largeur=260, hauteur=46,
                 police=None, variable=None, state="readonly"):
        self._valeurs = list(valeurs)
        self._selection_handlers = []
        super().__init__(
            parent,
            values=self._valeurs,
            width=largeur,
            height=hauteur,
            state=state,
            variable=variable,
            font=police or theme.NORMAL,
            dropdown_font=police or theme.NORMAL,
            fg_color=theme.CHAMP_FOND,
            border_color=theme.CHAMP_BORDURE,
            border_width=1,
            corner_radius=10,
            button_color=theme.CHAMP_BORDURE,
            button_hover_color="#E8ECFF",
            dropdown_fg_color=theme.BLANC,
            dropdown_hover_color="#E8ECFF",
            dropdown_text_color=theme.CHAMP_TEXTE,
            text_color=theme.CHAMP_TEXTE,
            command=self._emettre_selection,
        )

    def bind(self, sequence=None, func=None, add=None):
        if sequence == "<<ComboboxSelected>>":
            if func is not None:
                self._selection_handlers.append(func)
            return "liste-moderne-selection"
        return super().bind(sequence, func, add)

    def current(self, index=None):
        if index is None:
            try:
                return self._valeurs.index(self.get())
            except ValueError:
                return -1
        if not self._valeurs:
            return -1
        self.set(self._valeurs[index])

    def set_values(self, valeurs, selection=None):
        """Met à jour les options sans reconstruire le widget ni son style."""
        self._valeurs = list(valeurs)
        self.configure(values=self._valeurs)
        if selection in self._valeurs:
            self.set(selection)
        elif self._valeurs:
            self.set(self._valeurs[0])
        else:
            self.set("")

    def _emettre_selection(self, _valeur):
        evenement = SimpleNamespace(widget=self)
        for callback in tuple(self._selection_handlers):
            callback(evenement)


def liste_moderne(parent, valeurs, *, largeur=260, hauteur=46, police=None,
                  variable=None, state="readonly"):
    """Construit un menu déroulant arrondi dans la palette des champs."""
    return ListeDeroulanteModerne(
        parent,
        valeurs=valeurs,
        largeur=largeur,
        hauteur=hauteur,
        police=police,
        variable=variable,
        state=state,
    )


def barre_defilement_moderne(parent, commande, *, orientation="vertical",
                              fond=theme.FOND, largeur=12):
    """Barre fine et arrondie, sans flèches Windows, aux couleurs de l'application."""
    return ctk.CTkScrollbar(
        parent,
        command=commande,
        orientation=orientation,
        width=largeur,
        corner_radius=8,
        border_spacing=2,
        bg_color=fond,
        fg_color=fond,
        button_color=theme.CHAMP_BORDURE,
        button_hover_color=theme.BLEU_CHAT,
    )


class _GestionnaireDefilementSouris:
    """Route la molette vers le canevas sous le pointeur, avec un bind global unique."""

    def __init__(self, racine):
        self.racine = racine
        self.canevas = weakref.WeakSet()
        racine.bind_all("<MouseWheel>", self._molette_windows, add="+")
        racine.bind_all("<Button-4>", self._molette_linux, add="+")
        racine.bind_all("<Button-5>", self._molette_linux, add="+")

    def ajouter(self, canevas):
        self.canevas.add(canevas)

    def _canevas_sous_pointeur(self, evenement):
        widget = evenement.widget
        while widget is not None:
            if widget in self.canevas:
                try:
                    if widget.winfo_ismapped():
                        return widget
                except tk.TclError:
                    return None
            widget = getattr(widget, "master", None)
        return None

    def _defiler(self, evenement, unites):
        canevas = self._canevas_sous_pointeur(evenement)
        if canevas is None or not unites:
            return None

        avant = canevas.yview()
        canevas.yview_scroll(unites, "units")
        return "break" if canevas.yview() != avant else None

    def _molette_windows(self, evenement):
        delta = int(-evenement.delta / 120)
        if delta == 0 and evenement.delta:
            delta = -1 if evenement.delta > 0 else 1
        return self._defiler(evenement, delta)

    def _molette_linux(self, evenement):
        return self._defiler(evenement, -1 if evenement.num == 4 else 1)


def lier_defilement_molette(canevas):
    """Enregistre un canevas dans le routeur unique de la fenêtre principale."""
    racine = canevas._root()
    gestionnaire = getattr(racine, "_gestionnaire_defilement_souris", None)
    if gestionnaire is None:
        gestionnaire = _GestionnaireDefilementSouris(racine)
        racine._gestionnaire_defilement_souris = gestionnaire
    gestionnaire.ajouter(canevas)


def saisir_texte_moderne(parent, titre, invite, valeur_initiale=""):
    """Affiche une boîte modale de saisie moderne et retourne le texte, ou None."""
    dialogue = ctk.CTkToplevel(parent)
    dialogue.title(titre)
    dialogue.geometry("560x360")
    dialogue.minsize(440, 320)
    dialogue.configure(fg_color=theme.BLANC)
    dialogue.transient(parent.winfo_toplevel())
    dialogue.protocol("WM_DELETE_WINDOW", dialogue.destroy)

    dialogue.update_idletasks()
    parent_top = parent.winfo_toplevel()
    x = parent_top.winfo_rootx() + max(0, (parent_top.winfo_width() - 560) // 2)
    y = parent_top.winfo_rooty() + max(0, (parent_top.winfo_height() - 360) // 2)
    dialogue.geometry(f"560x360+{x}+{y}")

    contenu = ctk.CTkFrame(dialogue, fg_color=theme.BLANC, corner_radius=0)
    contenu.pack(fill="both", expand=True, padx=28, pady=24)
    ctk.CTkLabel(
        contenu, text=titre, text_color=theme.MARINE,
        font=(theme.POLICE, 20, "bold"), anchor="w",
    ).pack(fill="x", pady=(0, 8))
    ctk.CTkLabel(
        contenu, text=invite, text_color=theme.TEXTE_CLAIR,
        font=theme.NORMAL, anchor="w", justify="left", wraplength=490,
    ).pack(fill="x", pady=(0, 14))

    champ = zone_texte_moderne(contenu, largeur=480, hauteur=150)
    champ.pack(fill="both", expand=True)
    champ.insert("1.0", valeur_initiale)

    resultat = {"texte": None}

    def terminer(valider):
        if valider:
            resultat["texte"] = champ.get("1.0", "end-1c")
        dialogue.destroy()

    boutons = ctk.CTkFrame(contenu, fg_color="transparent")
    boutons.pack(fill="x", pady=(16, 0))
    BoutonModerne(
        boutons, "Annuler", lambda: terminer(False), style="secondaire",
        hauteur=42,
    ).pack(side="right", padx=(10, 0))
    BoutonModerne(
        boutons, "Enregistrer", lambda: terminer(True), style="principal",
        hauteur=42,
    ).pack(side="right")

    dialogue.bind("<Escape>", lambda _event: terminer(False))
    dialogue.bind("<Control-Return>", lambda _event: terminer(True))
    dialogue.grab_set()
    champ.focus_set()
    dialogue.wait_window()
    return resultat["texte"]


class BoutonModerne(ctk.CTkButton):
    """Bouton arrondi cohérent avec les contrôles du chatbot."""

    def __init__(self, parent, texte, commande, style="principal", icone=None,
                 hauteur=40, fond_parent=None):
        contenu = f"{icone}  {texte}" if icone else texte
        largeur_texte = tkfont.Font(font=POLICE_BOUTON).measure(contenu)
        largeur = max(96, largeur_texte + 42)
        fond_parent = fond_parent or theme.BLANC

        if style == "principal":
            couleurs = {
                "fg_color": theme.BLEU_CHAT,
                "hover_color": theme.BLEU_CHAT_SURVOL,
                "text_color": theme.BLANC,
                "border_width": 0,
            }
        elif style == "fantome":
            couleurs = {
                "fg_color": fond_parent,
                "hover_color": theme.BLEU_CLAIR,
                "text_color": theme.TEXTE_CLAIR,
                "border_width": 0,
            }
        else:
            couleurs = {
                "fg_color": theme.BLANC,
                "hover_color": "#E8ECFF",
                "text_color": theme.BLEU_CHAT,
                "border_width": 1,
                "border_color": theme.CHAMP_BORDURE,
            }

        super().__init__(
            parent,
            text=contenu,
            command=commande,
            width=largeur,
            height=max(40, int(hauteur)),
            corner_radius=RAYON,
            font=POLICE_BOUTON,
            **couleurs,
        )
