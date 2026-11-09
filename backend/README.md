# AJI TSTAJI — backend de développement

Ce dossier contient le backend Django REST Framework et sa base PostgreSQL locale. Il est indépendant des dépendances Desktop.

## Secrets locaux

1. Créer une seule fois le fichier local ignoré par Git : `python scripts/create_local_env.py` depuis ce dossier.
2. Le script génère une clé Django et un mot de passe PostgreSQL aléatoires, les écrit dans `.env`, et n'affiche aucune valeur secrète.
3. `.env.example` ne contient que des exemples fictifs et n'est pas utilisé pour démarrer le service.

Ne jamais copier un vrai secret dans `.env.example`, dans Git, ou dans un rapport.

## Démarrage local

Depuis `backend/` :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
docker compose up -d db
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py test --settings=aji_api.test_settings
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Le service PostgreSQL est lié à `127.0.0.1` et utilise un volume Docker dédié. Ne pas exécuter `docker compose down -v` si le volume local doit être conservé.

## Comptes Desktop historiques

`data/utilisateurs.json` est conservé. Après la migration Django et avant le lancement Desktop, vérifier d'abord l'import :

```powershell
.\.venv\Scripts\python.exe manage.py import_legacy_users --source ..\data\utilisateurs.json
```

Sans `--apply`, la commande est en **dry-run** : elle valide le format et indique les nombres à importer et à ignorer, sans écrire. Après vérification, l'import additif s'exécute avec :

```powershell
.\.venv\Scripts\python.exe manage.py import_legacy_users --source ..\data\utilisateurs.json --apply
```

Les comptes déjà présents sont ignorés sans remplacer leur mot de passe ni leur profil. L'import convertit les empreintes PBKDF2 historiques dans un format Django vérifiable, ne lit jamais de mot de passe en clair et n'efface pas le JSON. Après une authentification réussie, Django remplace automatiquement cette empreinte par Argon2. Les profils existants de `data/aji_tstaji.db` sont lus en mode SQLite lecture seule.

L'import est nécessaire pour rendre immédiatement réinitialisables par Brevo les anciens comptes qui n'ont pas encore fait de connexion Desktop. Une connexion réussie depuis le JSON peut aussi migrer le compte au premier lancement, en gardant priorité au compte PostgreSQL s'il existe déjà.

## API d'authentification

- `POST /api/v1/auth/register` crée le compte, le profil, les préférences, le rôle utilisateur et sa session.
- `POST /api/v1/auth/login` vérifie le mot de passe et émet une paire de jetons opaques.
- `POST /api/v1/auth/refresh` fait tourner la paire de jetons ; la réutilisation d'un ancien jeton révoque sa famille.
- `POST /api/v1/auth/logout` révoque la famille à partir du jeton de renouvellement.
- `GET /api/v1/me` accepte `Authorization: Bearer <access_token>`.
- L'accès expire après 15 minutes et le renouvellement après 30 jours. Seules les empreintes SHA-256 des jetons sont stockées.

Le Desktop utilise `http://127.0.0.1:8000/api/v1` par défaut. On peut remplacer cette adresse avec `AJI_API_BASE_URL` dans l'environnement du processus. Les jetons restent en mémoire dans l'application Desktop.

## Portée

- Les tests ne créent que des données fictives dans une base de test Django.
- Les tests utilisent SQLite en mémoire et ne se connectent pas à PostgreSQL. La commande d'import lit le fichier JSON et les profils SQLite en lecture seule.
- La connexion, l'inscription et le formulaire « Mot de passe oublié » Desktop utilisent cette API.
- Les candidatures et pages métier du Desktop continuent d'utiliser SQLite ; ces données ne sont ni supprimées ni migrées par ces changements.
- Les permissions de documents sont privées par propriétaire ; le rôle admin n'accorde pas l'accès au contenu.

## Réinitialisation du mot de passe

- `POST /api/v1/auth/password-reset` avec `{"email":"..."}` demande un code. La réponse est identique que le compte existe ou non.
- `POST /api/v1/auth/password-reset/confirm` avec `{"email":"...","token":"...","new_password":"..."}` consomme le code et remplace le mot de passe.
- Les nouveaux codes à 6 chiffres ne sont stockés qu'en SHA-256, sont à usage unique et expirent après 30 minutes. Les confirmations sont limitées à 10 tentatives par adresse et par heure, et 30 par IP et par heure. Les anciens jetons longs déjà envoyés restent acceptés jusqu'à leur expiration. Les sessions existantes sont révoquées après une réinitialisation.
- Les demandes sont limitées à 3 par adresse e-mail et par heure, et à 15 par adresse IP et par heure. Les empreintes de limitation sont HMACées avant stockage.
- L'API Brevo lit `BREVO_API_KEY` et `BREVO_SENDER_EMAIL` depuis `backend/.env` ou l'environnement du processus. Gardez ces paramètres hors Git et configurez l'adresse uniquement après sa vérification dans Brevo.
- Les tests simulent Brevo ; ils n'envoient aucun e-mail réel.

