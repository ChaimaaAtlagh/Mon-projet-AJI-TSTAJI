# Site AJI TSTAJI

Site statique en HTML, CSS et JavaScript, prévu pour être déployé directement sur Vercel. Il ne contient ni backend, ni variable secrète, ni donnée de compte.

## Configuration Vercel

- Importer le dépôt GitHub `ChaimaaAtlagh/AJI-TSTAJI-FINAL` dans Vercel.
- Définir `website` comme **Root Directory**.
- Laisser les commandes Build et Output Directory vides : les fichiers statiques sont servis directement.
- Aucun secret ni fichier `.env` n'est nécessaire au site.

## Téléchargements

Le site consulte l'API publique GitHub Releases de `ChaimaaAtlagh/AJI-TSTAJI-FINAL` et cherche l'actif `AJI_TSTAJI_Setup.exe` de la dernière release stable. Il affiche le tag de version et propose aussi le fichier SHA-256 associé. En l'absence de release publique, les boutons mènent à la page des versions et le site indique que le téléchargement n'est pas encore disponible.

Le workflow `../.github/workflows/windows-release.yml` construit l'installateur, exécute le test d'installation et de mise à jour dans un profil temporaire, puis publie ces actifs. Pour activer une release fonctionnelle, le dépôt doit être public et la variable Actions `AJI_PUBLIC_API_BASE_URL` doit contenir l'URL HTTPS réelle du backend terminant par `/api/v1`. Cette URL n'est pas un secret, mais aucun jeton, mot de passe ou clé d'API ne doit être intégré au site.

## Visuels

Les captures proviennent de la présentation du projet. La capture du profil contenant des coordonnées personnelles n'est pas incluse. Les images d'entreprises et d'analyse ne montrent pas de données de compte. Les fichiers historiques du projet ne sont pas transférés automatiquement par le site ou l'installateur.
