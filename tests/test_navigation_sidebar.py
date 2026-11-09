import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.main import (
    Application,
    ICONE_PAGE,
    LARGEUR_SIDEBAR,
    LARGEUR_SIDEBAR_REDUITE,
    PAGES_MENU,
)


class FauxWidget:
    def __init__(self):
        self.options = {}
        self.pack_args = None

    def configure(self, **options):
        self.options.update(options)

    def pack(self, **options):
        self.pack_args = options

    def pack_forget(self):
        self.pack_args = None


class CanevasEnregistreur:
    def __init__(self):
        self.appels = []

    def delete(self, *args):
        self.appels.append(("delete", args, {}))

    def __getattr__(self, nom):
        if nom.startswith("create_"):
            return lambda *args, **options: self.appels.append(
                (nom, args, options)
            )
        raise AttributeError(nom)

    def pack_forget(self):
        self.pack_args = None


def faux_sidebar_app():
    liens = {
        nom: {
            "ligne": FauxWidget(),
            "icone": FauxWidget(),
            "etiquette": FauxWidget(),
        }
        for nom in PAGES_MENU
    }
    app = SimpleNamespace(
        navigation_reduite=False,
        sidebar=FauxWidget(),
        logo_nom=FauxWidget(),
        logo_symbole=FauxWidget(),
        logo_texte=FauxWidget(),
        decoration_sidebar=FauxWidget(),
        bouton_reduire=FauxWidget(),
        bouton_deconnexion=FauxWidget(),
        page_active=None,
        liens=liens,
    )
    app._actualiser_sidebar = lambda: Application._actualiser_sidebar(app)
    app._dessiner_icone_menu = lambda icone, nom, couleur: icone.configure(
        icone=nom, couleur=couleur
    )
    return app


class SidebarNavigationTests(unittest.TestCase):
    def test_items_et_icones_suivent_l_ordre_demande(self):
        self.assertEqual(
            PAGES_MENU,
            [
                "Accueil", "Entreprises", "Opportunités", "Mes candidatures",
                "Analyse", "Candidature", "Mon profil",
            ],
        )
        self.assertEqual(list(ICONE_PAGE), PAGES_MENU)

    def test_chaque_icone_vectorielle_est_dessinee(self):
        for nom, icone in ICONE_PAGE.items():
            with self.subTest(page=nom):
                canevas = CanevasEnregistreur()
                Application._dessiner_icone_menu(canevas, icone, "#111111")
                self.assertGreater(len(canevas.appels), 1)

    def test_reduction_et_agrandissement_actualisent_la_sidebar(self):
        app = faux_sidebar_app()
        app.page_active = "Entreprises"

        Application.basculer_sidebar(app)
        self.assertTrue(app.navigation_reduite)
        self.assertEqual(app.sidebar.options["width"], LARGEUR_SIDEBAR_REDUITE)
        self.assertEqual(
            app.liens["Entreprises"]["icone"].options["icone"],
            ICONE_PAGE["Entreprises"],
        )
        self.assertEqual(app.liens["Entreprises"]["ligne"].options["fg_color"], "#2563EB")
        self.assertEqual(app.bouton_deconnexion.options["text"], "↪")
        self.assertIsNone(app.logo_texte.pack_args)
        self.assertEqual(app.bouton_deconnexion.options["text_color"], "#D84343")

        Application.basculer_sidebar(app)
        self.assertFalse(app.navigation_reduite)
        self.assertEqual(app.sidebar.options["width"], LARGEUR_SIDEBAR)
        self.assertEqual(
            app.liens["Entreprises"]["etiquette"].options["fg"],
            "#FFFFFF",
        )
        self.assertEqual(app.bouton_deconnexion.options["text"], "↪  Déconnexion")
        self.assertIsNotNone(app.logo_texte.pack_args)
        self.assertEqual(app.liens["Entreprises"]["etiquette"].options["font"][2], "bold")

    def test_navigation_affiche_et_reutilise_chaque_page(self):
        app = faux_sidebar_app()
        appels = []

        class FauxPage:
            def __init__(self, _parent, _app, nom):
                self.nom = nom
                self.actualisations = 0

            def pack(self, **_options):
                pass

            def pack_forget(self):
                pass

            def actualiser(self):
                self.actualisations += 1
                appels.append(self.nom)

        app.pages = {}
        app.page_active = None
        app.page_precedente = "Accueil"
        app.zone_pages = object()
        app.panneau_chatbot = None
        app.bouton_ia = None
        app._actualiser_sidebar = lambda: Application._actualiser_sidebar(app)
        app._mettre_a_jour_bouton_ia = lambda: None
        classes = {nom: lambda parent, instance, n=nom: FauxPage(parent, instance, n)
                   for nom in PAGES_MENU}

        with patch("app.main.PAGES_REELLES", classes):
            for nom in PAGES_MENU:
                Application.afficher_page(app, nom)
            Application.afficher_page(app, "Entreprises")

        self.assertEqual(appels, PAGES_MENU + ["Entreprises"])
        self.assertEqual(len(app.pages), len(PAGES_MENU))
        self.assertEqual(app.pages["Entreprises"].actualisations, 2)
        self.assertEqual(app.page_active, "Entreprises")
        self.assertEqual(
            app.liens["Entreprises"]["ligne"].options["fg_color"],
            "#2563EB",
        )


if __name__ == "__main__":
    unittest.main()
