import unittest

import pandas as pd

from src.utils.classification import (
    DOMAINES,
    classifier_domaine,
    filtrer_entreprises,
    normaliser_classifications,
    normaliser_donnees_entreprises,
)
from src.utils.charger_donnees import FICHIER_DONNEES, charger_entreprises


class ClassificationTests(unittest.TestCase):
    def test_taxonomie_contient_les_domaines_et_sous_domaines_uniques(self):
        self.assertEqual(len(DOMAINES), 13)
        for sous_domaines in DOMAINES.values():
            self.assertTrue(sous_domaines)
            self.assertEqual(len(sous_domaines), len(set(sous_domaines)))

    def test_anciennes_valeurs_sont_converties_sans_perdre_les_couples(self):
        self.assertEqual(
            normaliser_classifications("Développement", "Web"),
            [("Développement", "Développement Web")],
        )
        self.assertEqual(
            normaliser_classifications("Cloud", "Hébergement & cloud"),
            [("Cloud et DevOps", "Cloud computing")],
        )
        self.assertEqual(
            normaliser_classifications("IA", "IA & automatisation"),
            [("Intelligence Artificielle", "IA & automatisation")],
        )
        self.assertEqual(
            normaliser_classifications("Développement", "Web & mobile"),
            [
                ("Développement", "Développement Web"),
                ("Développement", "Développement Mobile"),
            ],
        )
        self.assertEqual(
            normaliser_classifications(
                "Développement; Data; Développement",
                "Web; Data Analysis; Web",
            ),
            [
                ("Développement", "Développement Web"),
                ("Data", "Data Analysis"),
            ],
        )

    def test_filtres_parent_sous_domaine_et_associations_multiples(self):
        brut = pd.DataFrame(
            {
                "Domaine": ["Développement; Data", "Développement", "Data"],
                "Sous_Domaine": ["Web; Data Analysis", "Front-end", "Data Science"],
            }
        )
        donnees = normaliser_donnees_entreprises(brut)

        self.assertEqual(len(filtrer_entreprises(donnees, "Data")), 2)
        self.assertEqual(
            len(filtrer_entreprises(donnees, "Développement", "Développement Web")),
            1,
        )
        self.assertEqual(
            len(filtrer_entreprises(donnees, None, "Data Analysis")),
            1,
        )

    def test_classifieur_privilegie_les_specialites_precises(self):
        self.assertEqual(
            classifier_domaine("studio spécialisé en web design"),
            ("Design numérique", "Web Design"),
        )
        self.assertEqual(
            classifier_domaine("intelligence artificielle et machine learning"),
            ("Intelligence Artificielle", "Machine Learning"),
        )
        self.assertEqual(
            classifier_domaine("entreprise cybersécurité pentest"),
            ("Cybersécurité", "Pentesting"),
        )

    def test_dataset_actuel_est_lu_sans_modification_et_filtrable(self):
        donnees_brutes = pd.read_excel(FICHIER_DONNEES)
        donnees = charger_entreprises()

        self.assertEqual(len(donnees), len(donnees_brutes))
        self.assertEqual(
            donnees["Domaine_Source"].tolist(), donnees_brutes["Domaine"].tolist()
        )
        resultat = filtrer_entreprises(
            donnees, "Développement", "Développement Web"
        )
        self.assertGreater(len(resultat), 0)
        self.assertLessEqual(len(resultat), len(donnees))


if __name__ == "__main__":
    unittest.main()
