"""Taxonomie IT partagée par le chargement et la collecte des entreprises."""

import re
import unicodedata


# Les sous-domaines sont ordonnés comme dans le sélecteur de la page Entreprises.
# Les mots-clés servent à la collecte; ils ne remplacent pas les classifications
# déjà présentes dans le fichier d'entreprises.
DOMAINES = {
    "Développement": {
        "Développement Web": ["développement web", "web development", "site web", "agence web", "création site", "web"],
        "Front-end": ["front-end", "frontend", "react", "vue.js", "angular", "html css"],
        "Back-end": ["back-end", "backend", "django", "laravel", "spring boot"],
        "Full Stack": ["full stack", "fullstack"],
        "Développement Mobile": ["application mobile", "app mobile", "développement mobile", "android", "ios"],
        "Développement Logiciel": ["développement logiciel", "logiciel sur mesure", "software", "éditeur logiciel"],
        "Développement Desktop": ["développement desktop", "application desktop", "application bureau", "winforms"],
    },
    "Intelligence Artificielle": {
        "Machine Learning": ["machine learning", "apprentissage automatique"],
        "Deep Learning": ["deep learning", "apprentissage profond"],
        "NLP": ["natural language processing", "traitement du langage", "nlp"],
        "Computer Vision": ["computer vision", "vision par ordinateur"],
        "IA générative": ["ia générative", "generative ai", "llm", "large language model"],
        "Robotique": ["robotique", "robotics"],
        # Sous-domaine complémentaire conservé pour les anciennes étiquettes
        # d'IA généraliste qui ne permettent pas d'inférer une spécialité.
        "IA & automatisation": ["intelligence artificielle", "automatisation ia"],
    },
    "Data": {
        "Data Analysis": ["data analysis", "analyse de données", "analyste de données"],
        "Data Science": ["data science", "data scientist"],
        "Data Engineering": ["data engineering", "data engineer"],
        "Big Data": ["big data", "hadoop", "spark"],
        "Data Mining": ["data mining", "exploration de données"],
    },
    "Business Intelligence": {
        "Power BI": ["power bi"],
        "Tableau": ["tableau software", "tableau public", "tableau bi"],
        "Reporting": ["reporting", "rapports décisionnels"],
        "Data Visualization": ["data visualization", "visualisation de données"],
        "ETL": ["etl", "extract transform load"],
    },
    "Cybersécurité": {
        "Sécurité des réseaux": ["sécurité des réseaux", "network security"],
        "Ethical Hacking": ["ethical hacking", "piratage éthique"],
        "Pentesting": ["pentest", "penetration testing", "test d'intrusion"],
        "Sécurité des systèmes": ["sécurité des systèmes", "sécurité informatique", "cybersécurité", "system security"],
        "SOC": ["soc", "security operations center"],
    },
    "Réseaux et Systèmes": {
        "Administration systèmes": ["administration systèmes", "administration systeme", "sysadmin"],
        "Administration réseaux": ["administration réseaux", "administration reseaux", "network admin"],
        "Linux": ["linux"],
        "Windows Server": ["windows server"],
        "Virtualisation": ["virtualisation", "virtualization", "vmware", "hyper-v"],
    },
    "Cloud et DevOps": {
        "AWS": ["aws", "amazon web services"],
        "Azure": ["azure", "microsoft azure"],
        "Google Cloud": ["google cloud", "gcp"],
        "Docker": ["docker"],
        "Kubernetes": ["kubernetes", "k8s"],
        "CI/CD": ["ci/cd", "continuous integration", "continuous delivery"],
        # Sous-domaine complémentaire pour conserver les anciens classements
        # « Hébergement & cloud », qui ne précisent aucun fournisseur cloud.
        "Cloud computing": ["hébergement cloud", "cloud computing", "hébergement & cloud"],
    },
    "Bases de données": {
        "MySQL": ["mysql"],
        "PostgreSQL": ["postgresql", "postgres"],
        "SQL Server": ["sql server", "microsoft sql"],
        "Oracle": ["oracle database", "oracle db"],
        "NoSQL": ["nosql"],
        "MongoDB": ["mongodb", "mongo db"],
    },
    "Design numérique": {
        "UI Design": ["ui design", "interface utilisateur"],
        "UX Design": ["ux design", "expérience utilisateur"],
        "Web Design": ["web design", "conception web"],
        "Prototypage": ["prototypage", "prototype figma", "figma"],
    },
    "QA et Testing": {
        "Tests manuels": ["tests manuels", "manual testing"],
        "Tests automatisés": ["tests automatisés", "automated testing", "selenium", "cypress"],
        "Tests logiciels": ["tests logiciels", "software testing"],
        "Quality Assurance": ["quality assurance", "assurance qualité", "qa"],
    },
    "ERP et CRM": {
        "SAP": ["sap"],
        "Odoo": ["odoo"],
        "Salesforce": ["salesforce"],
        "Gestion ERP": ["gestion erp", "erp", "crm"],
    },
    "IoT et Systèmes embarqués": {
        "Arduino": ["arduino"],
        "Raspberry Pi": ["raspberry pi"],
        "Systèmes embarqués": ["systèmes embarqués", "systemes embarques", "embedded systems"],
        "Internet of Things (IoT)": ["internet of things", "iot"],
    },
    "Autre domaine IT": {
        "Autres spécialités informatiques": [],
    },
}

SOUS_DOMAINES = {domaine: tuple(sous_domaines) for domaine, sous_domaines in DOMAINES.items()}
SOUS_DOMAINE_AUTRE = "Autres spécialités informatiques"
DOMAINE_AUTRE = "Autre domaine IT"

_SEPARATEUR_VALEURS = re.compile(r"\s*[;,|]\s*")


def _normaliser_cle(valeur):
    texte = unicodedata.normalize("NFKD", str(valeur or ""))
    texte = "".join(caractere for caractere in texte if not unicodedata.combining(caractere))
    return re.sub(r"[^a-z0-9]+", " ", texte.casefold()).strip()


def _separer_valeurs(valeur):
    if valeur is None:
        return []
    try:
        if valeur != valeur:  # NaN
            return []
    except (TypeError, ValueError):
        pass
    if isinstance(valeur, (list, tuple, set)):
        elements = valeur
    else:
        elements = _SEPARATEUR_VALEURS.split(str(valeur))
    return [str(element).strip() for element in elements if str(element).strip()]


_DOMAINES_PAR_CLE = {_normaliser_cle(domaine): domaine for domaine in DOMAINES}
_DOMAINES_PAR_CLE.update({
    "ia": "Intelligence Artificielle",
    "intelligence artificielle ia": "Intelligence Artificielle",
    "reseaux": "Réseaux et Systèmes",
    "reseau": "Réseaux et Systèmes",
    "cloud": "Cloud et DevOps",
    "services it": DOMAINE_AUTRE,
    "services informatiques": DOMAINE_AUTRE,
})

_SOUS_DOMAINES_PAR_CLE = {
    domaine: {_normaliser_cle(sous_domaine): sous_domaine for sous_domaine in sous_domaines}
    for domaine, sous_domaines in DOMAINES.items()
}
_SOUS_DOMAINES_GLOBAUX = {
    _normaliser_cle(sous_domaine): (domaine, sous_domaine)
    for domaine, sous_domaines in DOMAINES.items()
    for sous_domaine in sous_domaines
}

_ANCIENNES_CLASSIFICATIONS = {
    ("developpement", "web"): ("Développement", "Développement Web"),
    ("developpement", "web mobile"): [
        ("Développement", "Développement Web"),
        ("Développement", "Développement Mobile"),
    ],
    ("developpement", "logiciels sur mesure"): ("Développement", "Développement Logiciel"),
    ("ia", "ia automatisation"): ("Intelligence Artificielle", "IA & automatisation"),
    ("cybersecurite", "cybersecurite"): ("Cybersécurité", "Sécurité des systèmes"),
    ("reseaux", "reseaux infrastructure"): ("Réseaux et Systèmes", "Administration réseaux"),
    ("cloud", "hebergement cloud"): ("Cloud et DevOps", "Cloud computing"),
    ("services it", "conseil support it"): (DOMAINE_AUTRE, SOUS_DOMAINE_AUTRE),
}


def normaliser_classifications(domaine, sous_domaine):
    """Retourne les couples canoniques (domaine, sous-domaine) sans doublons.

    Les valeurs historiques sont converties en mémoire. Les colonnes d'origine
    dans le fichier Excel ne sont ni réécrites ni supprimées. Des valeurs
    séparées par « ; », « , » ou « | » permettent plusieurs associations.
    """
    domaines = _separer_valeurs(domaine)
    sous_domaines = _separer_valeurs(sous_domaine)
    if not domaines and sous_domaines:
        domaines = [""]
    if not domaines:
        return [(DOMAINE_AUTRE, SOUS_DOMAINE_AUTRE)]

    couples = []
    for index, domaine_source in enumerate(domaines):
        if len(sous_domaines) == len(domaines):
            sous_source = sous_domaines[index]
        elif len(sous_domaines) == 1:
            sous_source = sous_domaines[0]
        elif len(domaines) == 1:
            sous_source = sous_domaines or [""]
            sous_source = sous_source[0] if len(sous_source) == 1 else sous_source
        else:
            sous_source = sous_domaines[index] if index < len(sous_domaines) else ""

        sous_sources = sous_source if isinstance(sous_source, list) else [sous_source]
        domaine_cle = _normaliser_cle(domaine_source)
        domaine_canonique = _DOMAINES_PAR_CLE.get(domaine_cle)

        for sous_source_item in sous_sources:
            sous_cle = _normaliser_cle(sous_source_item)
            couple = _ANCIENNES_CLASSIFICATIONS.get((domaine_cle, sous_cle))
            if couple is None and domaine_canonique:
                sous_canonique = _SOUS_DOMAINES_PAR_CLE[domaine_canonique].get(sous_cle)
                if sous_canonique:
                    couple = (domaine_canonique, sous_canonique)
            if couple is None and sous_cle in _SOUS_DOMAINES_GLOBAUX:
                couple = _SOUS_DOMAINES_GLOBAUX[sous_cle]
            if couple is None and domaine_canonique:
                couple = (domaine_canonique, "")
            if couple is None:
                couple = (DOMAINE_AUTRE, SOUS_DOMAINE_AUTRE)
            couples_a_ajouter = couple if isinstance(couple, list) else [couple]
            for couple_canonique in couples_a_ajouter:
                if couple_canonique not in couples:
                    couples.append(couple_canonique)

    return couples or [(DOMAINE_AUTRE, SOUS_DOMAINE_AUTRE)]


def normaliser_donnees_entreprises(donnees):
    """Ajoute les classifications canoniques au DataFrame chargé en mémoire."""
    resultat = donnees.copy()
    if "Classifications_IT" in resultat.columns:
        return resultat

    resultat["Domaine_Source"] = resultat.get("Domaine", "")
    resultat["Sous_Domaine_Source"] = resultat.get("Sous_Domaine", "")
    classifications = [
        normaliser_classifications(domaine, sous_domaine)
        for domaine, sous_domaine in zip(
            resultat["Domaine_Source"], resultat["Sous_Domaine_Source"]
        )
    ]
    resultat["Classifications_IT"] = classifications
    resultat["Domaine"] = [couples[0][0] for couples in classifications]
    resultat["Sous_Domaine"] = [couples[0][1] for couples in classifications]
    return resultat


def filtrer_entreprises(donnees, domaine=None, sous_domaine=None):
    """Filtre les entreprises par couple canonique, y compris les associations multiples."""
    if domaine in (None, "") and sous_domaine in (None, ""):
        return donnees
    if "Classifications_IT" not in donnees.columns:
        donnees = normaliser_donnees_entreprises(donnees)

    def correspond(couples):
        return any(
            (domaine in (None, "") or domaine == candidat_domaine)
            and (sous_domaine in (None, "") or sous_domaine == candidat_sous_domaine)
            for candidat_domaine, candidat_sous_domaine in couples
        )

    masque = donnees["Classifications_IT"].apply(correspond)
    return donnees.loc[masque]


def classifier_domaine(texte: str) -> tuple[str, str]:
    """Retourne le premier domaine et sous-domaine dont un mot-clé correspond."""
    texte_lower = str(texte or "").casefold()
    correspondances = []
    termes_generiques = {
        "intelligence artificielle", "cybersécurité", "cloud", "développement",
        "réseau", "web", "data",
    }
    for domaine, sous_domaines in DOMAINES.items():
        for sous_domaine, mots_cles in sous_domaines.items():
            for mot in mots_cles:
                mot = mot.casefold()
                if len(mot) <= 3:
                    trouve = re.search(rf"(?<!\w){re.escape(mot)}(?!\w)", texte_lower)
                else:
                    trouve = mot in texte_lower
                if trouve:
                    score = len(mot) - (30 if mot in termes_generiques else 0)
                    correspondances.append((score, domaine, sous_domaine))
    if correspondances:
        _, domaine, sous_domaine = max(correspondances, key=lambda item: item[0])
        return domaine, sous_domaine
    return DOMAINE_AUTRE, SOUS_DOMAINE_AUTRE


QUARTIERS_CONNUS = [
    "Guéliz", "Sidi Ghanem", "Al Massar", "Mabrouka", "Ménara",
    "M'hamid", "Massira", "Semlalia", "Daoudiate", "Hivernage",
    "Medina", "Targa", "Route de Safi", "Route de Casablanca",
]


def detecter_quartier(adresse: str) -> tuple[str, str]:
    """Retourne (Quartier, Fiabilite_Quartier)."""
    for quartier in QUARTIERS_CONNUS:
        if quartier.lower() in adresse.lower():
            return quartier, "Explicite"
    return "A_CONFIRMER", "A_CONFIRMER"


MOTS_CLES_IT_GENERIQUES = [
    "informatique", "digital", "numérique", "technologie", "logiciel",
    "site web", "application", "développement", "it ", " it", "tech",
    "cloud", "réseau", "cybersécurité", "intelligence artificielle",
    "data", "système d'information", "web", "mobile", "machine learning",
    "cybersecurity", "devops", "robotique", "iot", "base de données",
]


def est_pertinent_it(texte: str) -> bool:
    """Vérifie si le nom/type de l'entreprise correspond bien au domaine IT."""
    texte_lower = str(texte or "").casefold()
    return any(mot.casefold() in texte_lower for mot in MOTS_CLES_IT_GENERIQUES)
