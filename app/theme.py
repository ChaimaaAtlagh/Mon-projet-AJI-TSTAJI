"""
theme.py
Couleurs, polices et styles de l'application Aji Tstaji.
Tout le design est défini ici, une seule fois.

Aperçu du thème :
    python app/theme.py
"""

import tkinter as tk
from tkinter import ttk

# ---------- COULEURS ----------
BLEU = "#2563EB"          # couleur principale
BLEU_FONCE = "#1D4ED8"    # survol des boutons
BLEU_CLAIR = "#DBEAFE"    # fonds légers, cartes actives
MARINE = "#0F1B4C"        # titres (texte bleu très foncé)
FOND = "#F4F8FF"          # fond des pages
BLANC = "#FFFFFF"
TEXTE = "#1E293B"         # texte normal
TEXTE_CLAIR = "#64748B"   # texte secondaire
BORDURE = "#E2E8F0"

# Contrôles de saisie inspirés de l'interface du chatbot.
BLEU_CHAT = "#3B4FE0"
BLEU_CHAT_SURVOL = "#2F40C0"
CHAMP_FOND = "#F4F6FB"
CHAMP_BORDURE = "#D5DBF5"
CHAMP_PLACEHOLDER = "#6B7280"
CHAMP_TEXTE = "#1A1F36"

# Couleurs des cartes de la page d'accueil
VIOLET = "#7C3AED"
VERT = "#16A34A"
ORANGE = "#EA580C"
ROSE = "#E11D48"
# Fonds pastel des icônes (cartes de la page d'accueil)
VIOLET_PASTEL = "#EDE9FE"
VERT_PASTEL = "#DCFCE7"
ORANGE_PASTEL = "#FFEDD5"
ROSE_PASTEL = "#FFE4E6"

# ---------- POLICES ----------
POLICE = "Segoe UI"       # police moderne disponible sur Windows
TITRE_GEANT = (POLICE, 48, "bold")
TITRE = (POLICE, 24, "bold")
SOUS_TITRE = (POLICE, 14)
NORMAL = (POLICE, 11)
GRAS = (POLICE, 11, "bold")
PETIT = (POLICE, 10)


def appliquer_style(fenetre):
    """Configure les styles ttk (boutons, tableaux...) pour toute l'application."""
    style = ttk.Style(fenetre)
    style.theme_use("clam")  # thème qui permet de changer les couleurs des boutons
    fenetre.configure(bg=FOND)

    # Cadres et textes
    style.configure("TFrame", background=FOND)
    style.configure("Carte.TFrame", background=BLANC)
    style.configure("TLabel", background=FOND, foreground=TEXTE, font=NORMAL)

    # Bouton principal (bleu)
    style.configure("Principal.TButton", background=BLEU, foreground=BLANC,
                    font=GRAS, padding=(22, 10), borderwidth=0)
    style.map("Principal.TButton", background=[("active", BLEU_FONCE)])

    # Bouton secondaire (blanc, bord bleu)
    style.configure("Secondaire.TButton", background=BLANC, foreground=BLEU,
                    font=GRAS, padding=(22, 10), bordercolor=BLEU)
    style.map("Secondaire.TButton", background=[("active", BLEU_CLAIR)])

    # Menus déroulants : même palette douce et lisible que les nouveaux champs.
    style.configure(
        "TCombobox",
        fieldbackground=CHAMP_FOND,
        background=BLANC,
        foreground=CHAMP_TEXTE,
        selectbackground=BLEU_CHAT,
        selectforeground=BLANC,
        padding=(10, 8),
        relief="flat",
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", CHAMP_FOND), ("focus", BLANC)],
        foreground=[("readonly", CHAMP_TEXTE)],
        selectbackground=[("readonly", CHAMP_FOND)],
        selectforeground=[("readonly", CHAMP_TEXTE)],
    )

    # Tableau (utilisé plus tard dans la page Entreprises)
    style.configure("Treeview", background=BLANC, fieldbackground=BLANC,
                    foreground=TEXTE, font=NORMAL, rowheight=30, borderwidth=0)
    style.configure("Treeview.Heading", background=BLEU_CLAIR, foreground=MARINE,
                    font=GRAS, padding=8)
    style.map("Treeview", background=[("selected", BLEU)],
              foreground=[("selected", BLANC)])


def apercu():
    """Ouvre une petite fenêtre pour voir les couleurs et les polices."""
    fenetre = tk.Tk()
    fenetre.title("Aperçu du thème - Aji Tstaji")
    fenetre.geometry("900x520")
    appliquer_style(fenetre)

    # Titre géant en deux couleurs : "AJI" en marine, "TSTAJI" en bleu
    ligne_titre = tk.Frame(fenetre, bg=FOND)
    ligne_titre.pack(pady=(40, 0))
    tk.Label(ligne_titre, text="AJI ", font=TITRE_GEANT, fg=MARINE, bg=FOND).pack(side="left")
    tk.Label(ligne_titre, text="TSTAJI", font=TITRE_GEANT, fg=BLEU, bg=FOND).pack(side="left")

    tk.Label(fenetre, text="Ton avenir professionnel commence ici.",
             font=SOUS_TITRE, fg=TEXTE_CLAIR, bg=FOND).pack(pady=(5, 25))

    # Carte blanche avec deux boutons
    carte = tk.Frame(fenetre, bg=BLANC, highlightbackground=BORDURE, highlightthickness=1)
    carte.pack(padx=60, pady=10, fill="x")
    tk.Label(carte, text="Exemple de carte", font=GRAS, fg=MARINE, bg=BLANC).pack(pady=(20, 5))
    tk.Label(carte, text="Texte normal, sur fond blanc.", font=NORMAL,
             fg=TEXTE, bg=BLANC).pack()
    boutons = tk.Frame(carte, bg=BLANC)
    boutons.pack(pady=20)
    ttk.Button(boutons, text="Rechercher", style="Principal.TButton").pack(side="left", padx=8)
    ttk.Button(boutons, text="Annuler", style="Secondaire.TButton").pack(side="left", padx=8)

    # Pastilles de couleurs
    pastilles = tk.Frame(fenetre, bg=FOND)
    pastilles.pack(pady=25)
    for couleur in (BLEU, VIOLET, VERT, ORANGE, ROSE):
        tk.Frame(pastilles, bg=couleur, width=60, height=40).pack(side="left", padx=6)

    fenetre.mainloop()


if __name__ == "__main__":
    apercu()
