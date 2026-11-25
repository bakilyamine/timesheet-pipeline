# DevOps et déploiement — Timesheet Pipeline

**Statut : proposition à valider — déploiement de production non autorisé.**

## 1. Environnements

- **Développement :** Docker Compose ou environnement local; données
  synthétiques; connexion SSO remplacée par une simulation de test.
- **CI :** environnements jetables; PostgreSQL de test; secrets de production
  interdits.
- **Staging :** instance isolée et données synthétiques/anonymisées; intégration
  SSO de préproduction si l'organisation en fournit une.
- **Production :** serveur interne recommandé sous réserve de clarifier
  « local », réseau, sauvegardes et responsabilités d'exploitation.

Staging/production et la plateforme interne ne sont pas encore confirmés.
L'absence de détails sur l'hôte et l'IdP bloque une procédure de déploiement
finale.

## 2. Stratégie Git

- `main` protégée; aucun push direct de développement en production.
- Branches courtes `feature/*`, `fix/*`, `docs/*`; pull request vers `main`.
- Revue obligatoire et checks CI verts avant fusion.
- Releases par tag versionné (`vX.Y.Z`) après validation; migrations incluses
  et documentées.
- Les commits sur `main` ne doivent pas publier automatiquement un déploiement
  de production sans environnement et mécanisme de promotion approuvés.

## 3. CI/CD proposé

### CI pour pull request et branche

1. checkout et installation avec versions verrouillées;
2. lint, formatage, tests unitaires et d'intégration;
3. audit de dépendances et scan de sécurité;
4. build Docker et test de démarrage/health;
5. publication d'artefacts uniquement si non sensibles et avec rétention
   limitée.

### Livraison continue

- Build image immuable identifiée par SHA; éviter de se fier uniquement au tag
  mutable `latest`.
- Promotion manuelle ou contrôlée de CI vers staging, puis approbation humaine
  avant production.
- Migrations compatibles avec la version déployée; sauvegarde avant migration
  destructive.
- Vérification post-déploiement des endpoints de readiness et des logs.
- Retour arrière par redéploiement de l'image précédente; rollback de schéma
  uniquement si la migration le permet, sinon restauration documentée.

### Écart avec la configuration actuelle

Le workflow actuel publie l'image Docker Hub sur un push de `main` si les
secrets Docker Hub existent. Il ne déploie pas l'application sur un serveur.
Cette publication doit être considérée comme une livraison d'image, pas comme
un déploiement de production; son maintien dépend de la décision sur le
registre et l'infrastructure cible.

## 4. Hébergement et réseau

Recommandation conditionnelle : conteneurs Docker sur serveur Linux interne,
reverse proxy TLS et PostgreSQL administré/sauvegardé selon les normes de
l'organisation. Une seule instance web suffit au MVP tant que la capacité est
mesurée. Le planificateur doit survivre aux redémarrages et éviter les doubles
exécutions concurrentes.

Clarifier si « local » signifie poste personnel, serveur on-premise ou cloud
privé. Un poste personnel ne convient pas à un import planifié continu ni à un
service SSO multi-utilisateur disponible en permanence.

## 5. Secrets et configuration

- Configuration par variables d'environnement non sensibles; secrets injectés
  depuis le gestionnaire de secrets approuvé ou le mécanisme de déploiement.
- Séparer les secrets de développement, staging et production.
- Rotation des secrets OIDC/DB selon les règles de l'organisation.
- Ne pas inscrire d'identifiants, mots de passe ou tokens dans Git, Dockerfile,
  logs, image ou artefacts CI.
- Autoriser uniquement les variables nécessaires et valider la configuration
  au démarrage; échouer explicitement si une variable obligatoire manque.
- Clés OIDC, URL d'issuer, audience, URL DB, niveau de journalisation, fuseau
  horaire et répertoire d'import sont des paramètres à formaliser.

## 6. Journaux, supervision et alertes

- Journaux structurés sur stdout avec horodatage, niveau, identifiant de
  requête/import et résultat; exclure tokens, CSV bruts et données personnelles
  inutiles.
- Indicateurs minimaux : état du service et de la DB, durée/échec des imports,
  volume de lignes traitées/rejetées, erreurs HTTP et espace disque.
- Endpoints séparés liveness/readiness; ne pas y exposer de secrets ou détails
  internes.
- Alertes recommandées pour échec répété du planificateur, DB indisponible,
  échec de sauvegarde et taux d'erreurs anormal.
- Outil de collecte/alerting à choisir selon l'infrastructure existante; aucun
  fournisseur de monitoring n'est confirmé.

## 7. Sauvegarde, reprise et rollback

- PostgreSQL : sauvegarde chiffrée quotidienne au minimum comme recommandation
  initiale, plus WAL/PITR si le RPO exigé le justifie.
- Définir RPO/RTO avec les propriétaires métier et tester la restauration au
  moins avant chaque release majeure, puis à une fréquence approuvée.
- Stocker les sauvegardes hors de l'hôte applicatif, avec accès restreint,
  rétention et suppression conformes à la politique interne.
- Les exports/imports temporaires ne sont pas des sauvegardes.
- Garder l'image précédente et les migrations; documenter l'ordre de rollback
  application/base et les cas où un rollback de schéma est impossible.

## 8. Risques et prérequis

- Sans IdP confirmé, impossible de valider l'authentification réelle et le
  mappage de rôles.
- Sans hôte permanent et source CSV définis, l'import planifié ne peut pas être
  exploité.
- Sans politique de sauvegarde approuvée, la conservation de saisies corrigées
  présente un risque métier.
- Les taux horaires et noms de projets peuvent être confidentiels; artefacts et
  dépôts d'images doivent être privés et les exports protégés.
