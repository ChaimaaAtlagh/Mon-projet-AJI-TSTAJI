# Hébergement Render

Le fichier racine `render.yaml` décrit l'API Django, sa base PostgreSQL et un
disque persistant pour les documents privés. Il n'inclut aucune donnée SQLite
locale et ne configure aucune importation de comptes historiques. La commande
`migrate` ne fait qu'appliquer les migrations Django versionnées à la base Render
neuve.

## Création

1. Importer le dépôt `ChaimaaAtlagh/AJI-TSTAJI-FINAL` dans Render et sélectionner
   le Blueprint `render.yaml`.
2. Vérifier la région Frankfurt, le plan web Starter, le plan PostgreSQL
   `0.1c-256mb` et le disque persistant de 1 Go. Ces ressources sont payantes.
3. Configurer `BREVO_API_KEY` comme variable secrète Render et
   `BREVO_SENDER_EMAIL` avec une adresse expéditrice vérifiée. La réinitialisation
   de mot de passe par courriel ne fonctionnera pas avant cette configuration.
4. Déployer puis vérifier `https://<service>.onrender.com/health/`; le résultat
   `{"status":"ok"}` confirme que Django et PostgreSQL répondent.
5. Copier l'URL HTTPS publique avec suffixe `/api/v1` dans la variable GitHub
   `AJI_PUBLIC_API_BASE_URL`. Le build Desktop l'intègre; ce n'est pas une donnée
   secrète.

## Données et persistance

Le disque `/var/data` est réservé aux documents téléversés privés, via
`PRIVATE_DOCUMENT_ROOT=/var/data/private-documents`. PostgreSQL ne reçoit que les
nouvelles données envoyées à l'API. Les profils, candidatures et documents SQLite
déjà présents sur les ordinateurs des utilisateurs restent locaux. Aucune donnée
locale n'est transférée, fusionnée ou supprimée lors de la création du service.

Le stockage persistant est attaché à une seule instance du service web Render et
peut désactiver le déploiement sans interruption. Prévoir une sauvegarde distincte
des documents privés avant toute opération de maintenance sur ce disque.

## Variables configurées par le Blueprint

Render génère `DJANGO_SECRET_KEY` et fournit les cinq paramètres `DB_*` depuis la
base liée. `DJANGO_DEBUG` est désactivé; l'hôte externe Render est ajouté aux hôtes
autorisés et Django fait confiance au proxy HTTPS Render. Ne jamais committer les
valeurs affichées dans le tableau de bord Render.
