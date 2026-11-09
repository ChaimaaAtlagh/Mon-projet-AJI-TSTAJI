# AJI TSTAJI — distribution Windows

## Installer l'application

Télécharger `AJI_TSTAJI_Setup.exe`, l'ouvrir et suivre l'assistant.
L'installation est limitée au compte Windows courant, ne demande pas Python et
crée les raccourcis Démarrer et Bureau nommés `AJI TSTAJI FINAL`.

Le ZIP portable contient `AJI_TSTAJI_FINAL.exe` en un seul fichier, avec son
icône et ses ressources intégrées. Il ne nécessite ni Python ni dossier
`_internal`.

## Données conservées

Les profils, candidatures, comptes historiques, fichiers de configuration locaux
et documents générés restent dans `%LOCALAPPDATA%\AJI TSTAJI` (les données de
l'application dans son sous-dossier `data`). Ce chemin n'est pas situé dans le
dossier d'installation. Les mises à jour, réinstallations et désinstallations
retirent les fichiers du programme sans effacer le dossier utilisateur. Aucun
fichier de ce stockage ne sera déplacé ou migré vers PostgreSQL sans une stratégie
séparée et votre validation.

Les données déjà présentes dans l'ancien dossier de développement (`data/` du
projet, notamment SQLite et documents) restent à leur emplacement et ne sont pas
copiées automatiquement par l'installateur. Une copie de ces données vers le
profil Windows doit faire l'objet d'une procédure dédiée avec sauvegarde et
vérification avant d'être activée.

## API et configuration

Le build de distribution reçoit une URL publique HTTPS se terminant par `/api/v1`
via `AJI_PUBLIC_API_BASE_URL`. Cette URL n'est pas un secret et est intégrée au
programme. En build figé, une ancienne valeur locale présente dans `.env` ne prend
pas le dessus sur l'URL publique ; en l'absence d'URL publique, la connexion
échoue avec un message explicite au lieu d'appeler `localhost`.

En développement, l'application source conserve son URL locale par défaut. Les
clés du chatbot et autres identifiants personnels sont facultatifs et restent dans
le fichier `.env` privé de l'utilisateur. Ils ne doivent jamais être intégrés au
build ou publiés.

## Données distribuées

Le build comprend le dataset nettoyé `data/cleaned/data_nettoyee.xlsx`, les images
de l'interface, l'icône, les bibliothèques Python/Tcl/Tk collectées par PyInstaller
et la configuration publique de l'API. Il exclut le dataset brut, les comptes,
la base SQLite, les CV, les lettres, les documents et tout fichier `.env`.

Dans l'EXE distribué, le chatbot transmet les messages au backend HTTPS après
authentification. La clé Groq reste dans les variables secrètes du serveur et
n'est jamais incluse dans le programme. Le texte d'un document joint pour analyse
est envoyé au backend puis au fournisseur IA, comme toute requête de chat.

Le paquetage vérifie les noms des fichiers sensibles avant de créer le ZIP et
l'installateur. Toute détection bloque la suite du build.

## Construire

Depuis la racine du dépôt, avec `.venv` installé et Inno Setup disponible :

```powershell
$env:AJI_PUBLIC_API_BASE_URL = "https://api.example.com/api/v1" # remplacez par l'URL publique réelle
.\scripts\build_windows.ps1
```

Le script crée un nouveau dossier horodaté sous `release/` sans remplacer les
paquets précédents. Il y dépose `AJI_TSTAJI_FINAL.exe`, le ZIP portable,
`AJI_TSTAJI_Setup.exe` et une empreinte SHA-256 de chaque livrable. Pour un build portable local sans
Inno Setup, ajouter `-SkipInstaller`. Un paquet sans URL publique ne peut être
produit qu'en passant explicitement `-AllowEmptyApiUrlForTests` ; il reste
strictement réservé aux tests et refuse toute connexion locale.

Le backend Django et PostgreSQL sont hébergés séparément. Le build Windows ne
contient aucun dump, identifiant de base ou secret de déploiement.
