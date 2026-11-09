# AJI TSTAJI

Application Python de recherche de stage/emploi et de suivi de candidatures, destinée aux étudiants à Marrakech.

## Objectif

Centraliser en une seule application :
- la découverte d'entreprises locales (secteur numérique) ;
- la génération d'un CV et d'une lettre de motivation ;
- le suivi des candidatures envoyées.

Voir `docs/objectif.md` pour le détail complet.

## Authentification

La fenêtre de connexion utilisée par `app/main.py` envoie l'inscription, la connexion et la réinitialisation de mot de passe au backend Django (`backend/`) et à PostgreSQL. Les candidatures et pages métier restent dans SQLite ; ces données ne sont pas déplacées par l'authentification.

Les comptes historiques peuvent être importés sans supprimer `data/utilisateurs.json`. Depuis `backend/`, lance d'abord la commande sans `--apply` pour le dry-run, puis relance-la avec `--apply` après vérification. Les détails et les commandes de démarrage sont dans `backend/README.md`.

## Technologies (100% Python)

| Bibliothèque | Rôle |
|---|---|
| Tkinter / ttk | Interface graphique |
| Pandas | Manipulation des données |
| Matplotlib | Graphiques (page Analyse) |
| SQLite (`sqlite3`) | Profils locaux et candidatures |
| Django REST Framework + PostgreSQL | Comptes, sessions et réinitialisation du mot de passe |
| Requests | Appels à l'API Google Places |
| openpyxl | Lecture/écriture Excel, génération du CV |
| Pillow | Images de l'interface |
| python-dotenv | Lecture des clés/API depuis `.env` |
| smtplib | Envoi d'email de confirmation |

L'interface Desktop reste en Python ; le backend est une API Django REST.

## Structure du projet

```
aji-tstaji-v2/
├── data/
│   ├── raw/          → données avant nettoyage (data_brute.xlsx)
│   ├── cleaned/       → données après nettoyage (data_nettoyee.xlsx, 16 colonnes)
│   ├── reports/        → rapport qualité, CV et lettres générés
│   └── aji_tstaji.db    → base SQLite (profil, candidatures)
├── src/
│   ├── data_collection/   → collecte via Google Places API
│   ├── data_cleaning/      → nettoyage des données
│   ├── database/            → base SQLite (fonctions profil/candidatures)
│   ├── analysis/              → analyses complémentaires
│   └── utils/                    → chargement des données, génération CV/lettre/email
├── app/
│   ├── main.py           → fenêtre principale, navigation
│   ├── theme.py           → couleurs, polices
│   ├── widgets.py          → composants réutilisables (boutons)
│   ├── assets/               → images (ex. hero.png)
│   └── pages/                → une page = un fichier
├── docs/objectif.md    → objectif détaillé du projet
├── .env                  → clés/API (jamais partagé)
├── .env.example           → variables attendues, sans valeurs
├── requirements.txt        → bibliothèques nécessaires
└── README.md                → ce fichier
```

## Installation

### 1. Créer et activer l'environnement virtuel

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Installer les bibliothèques

```powershell
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement

Copier `.env.example` en `.env`, puis renseigner :

```
GOOGLE_PLACES_API_KEY=ta_cle_google_places
SMTP_EMAIL=ton_adresse@example.com
SMTP_MOT_DE_PASSE=ton_mot_de_passe_application
SMTP_SERVEUR=smtp.gmail.com
SMTP_PORT=587
```

- `GOOGLE_PLACES_API_KEY` : nécessaire uniquement pour relancer une collecte (`src/data_collection/google_places.py`).
- `AJI_API_BASE_URL` : adresse de l'API Django ; elle pointe sur le backend local pendant le développement.
- `GROQ_API_KEY` : facultative, active le chatbot.
- Les variables `SMTP_*` sont nécessaires pour l'email de confirmation de candidature. Pour Gmail, utiliser un **mot de passe d'application**, pas le mot de passe de connexion.

## Construire l'application Windows

La version utilisateur s'installe avec un fichier `AJI_TSTAJI-Windows-Setup.exe`.
Le ZIP portable reste aussi disponible. Depuis PowerShell, à la racine du dépôt,
utilisez une URL HTTPS réelle du backend se terminant par `/api/v1` :

```powershell
$env:AJI_PUBLIC_API_BASE_URL = "https://api.example.com/api/v1" # remplacez par l'URL publique réelle
.\scripts\build_windows.ps1
```

Le script construit une version PyInstaller, l'installateur Inno Setup, le ZIP
portable et leurs empreintes SHA-256 dans un nouveau dossier de `release/`.
L'URL publique de l'API est une configuration non secrète incluse dans le build.
Les versions distribuées n'utilisent jamais `localhost` ; en développement,
l'application source continue d'utiliser l'API locale par défaut.

Le stockage des profils, candidatures, comptes historiques et documents générés
reste dans `%LOCALAPPDATA%\AJI TSTAJI\data`, hors du dossier d'installation.
Les mises à jour et la désinstallation ne suppriment pas ces données. Les `.env`,
les bases SQLite, les fichiers utilisateurs et les documents privés restent hors
des paquets. Pour les détails et les limites, voir
[`deployment/README_WINDOWS.md`](deployment/README_WINDOWS.md).
