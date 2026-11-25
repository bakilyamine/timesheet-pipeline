# PRD — Timesheet Pipeline

**Statut : proposition à valider — aucun développement n'est autorisé par ce document.**

## 1. Résumé et définition du produit

### Problème et objectif métier

Le projet actuel automatise le nettoyage de saisies de temps et le calcul de
synthèses d'heures et de coûts. L'objectif produit proposé est d'en faire une
application web interne permettant aux employés, managers et équipes Finance
de saisir ou importer des temps, de corriger les données et de consulter des
rapports cohérents.

La réduction des manipulations manuelles et l'amélioration de la fiabilité des
rapports sont des objectifs déduits du pipeline existant; ils restent à
confirmer avec les parties prenantes.

### Utilisateurs ciblés

- **Confirmé :** employés, managers et Finance sont les trois groupes visés.
- **À confirmer :** les employés ne voient-ils que leurs propres saisies, les
  managers celles de leurs équipes, et Finance l'ensemble des données?

### État existant vérifié

- API FastAPI et ETL pandas.
- Lecture d'un CSV local, filtrage des lignes incomplètes ou non positives,
  normalisation des noms, calcul des coûts et agrégations par projet et
  collaborateur.
- Exécution du pipeline et génération de trois CSV dans `output/`.
- Endpoints actuels : `/health`, `/pipeline/run`, `/rapports/projets` et
  `/rapports/collaborateurs`.
- Pas d'interface utilisateur, d'authentification ni de base de données.
- La majoration de 15 % est une valeur par défaut dans le code, **pas une règle
  métier confirmée**.

## 2. Exigences

### Exigences confirmées par le demandeur

- Application avec interface web.
- Saisie manuelle des temps.
- Import CSV à la demande et traitement CSV par lot.
- Import planifié.
- Export CSV des rapports.
- Authentification via le SSO de l'organisation; fournisseur non précisé.
- Possibilité de corriger les données; le processus de correction n'est pas
  encore défini.
- Hébergement décrit comme « local »; il reste à établir s'il s'agit d'un
  poste de développement ou d'un serveur interne.

### Exigences fonctionnelles proposées

- **FR-01 — Authentification :** authentifier les utilisateurs par le
  fournisseur OIDC/SAML retenu par l'organisation; ne pas créer un système de
  mots de passe local sans décision explicite.
- **FR-02 — Autorisation :** appliquer des droits distincts aux rôles employé,
  manager et Finance. La portée précise des données visibles par rôle doit être
  validée.
- **FR-03 — Saisie :** permettre la création et la correction d'une saisie avec
  date, collaborateur, projet, heures et, si nécessaire, taux horaire.
- **FR-04 — Import :** accepter un CSV, valider son format et ses lignes,
  présenter les erreurs à l'utilisateur et éviter qu'une ligne invalide soit
  silencieusement perdue.
- **FR-05 — Traitement par lot :** permettre de traiter plusieurs fichiers ou
  un lot défini; emplacement, convention de nommage et comportement sur les
  doublons restent à préciser.
- **FR-06 — Import planifié :** exécuter des imports sans intervention
  manuelle. Source, calendrier, fuseau horaire et stratégie d'échec restent à
  préciser.
- **FR-07 — Rapports :** afficher les synthèses d'heures et de coûts par projet
  et collaborateur; filtres par période et règles de visibilité à confirmer.
- **FR-08 — Export :** permettre le téléchargement des rapports en CSV.
- **FR-09 — Traçabilité :** recommandation d'enregistrer l'auteur, la date et
  les changements des imports et corrections; rétention à décider.

### Exigences non fonctionnelles proposées

Ces seuils sont des cibles initiales de planification, pas des engagements
confirmés :

- **NFR-01 — Confidentialité :** protéger les noms, heures, projets et taux
  horaires; appliquer le principe du moindre privilège.
- **NFR-02 — Disponibilité :** pour un serveur interne, viser 99,5 % par mois
  hors maintenance planifiée, sous réserve de l'infrastructure disponible.
- **NFR-03 — Performance :** viser un temps de réponse inférieur à 2 s au
  95e percentile pour les rapports usuels, sur un jeu de données convenu.
- **NFR-04 — Capacité :** valider la taille maximale des imports et les
  utilisateurs simultanés avant de dimensionner; aucune volumétrie n'est
  actuellement connue.
- **NFR-05 — Exploitabilité :** fournir des journaux exploitables, des
  sauvegardes testées et une procédure de restauration.
- **NFR-06 — Compatibilité :** supporter les versions de navigateurs approuvées
  par l'organisation; liste à confirmer.
- **NFR-07 — Accessibilité :** viser WCAG 2.2 AA pour les parcours essentiels,
  recommandation à confirmer.

## 3. Périmètre

### MVP proposé

1. Application web interne et intégration au fournisseur SSO existant.
2. Autorisations pour les trois groupes d'utilisateurs, après validation des
   portées de données.
3. Persistance des saisies, imports, corrections et éléments nécessaires aux
   rapports.
4. Saisie et correction manuelles.
5. Import CSV interactif avec prévalidation et retour d'erreurs explicite.
6. Import par lot et import planifié depuis une source interne convenue.
7. Rapports par période, projet et collaborateur, puis export CSV.
8. Déploiement dans l'environnement local/interne qui sera confirmé.

L'import planifié ne peut pas être accepté tant que sa source, sa fréquence et
son comportement en cas d'échec ne sont pas définis.

### Explicitement hors périmètre provisoire

À moins d'une décision ultérieure : paie, facturation, approbation de feuilles
de temps, application mobile native, intégration avec des outils externes de
temps, prévisions budgétaires, conversion multi-devises et gestion
multi-organisation. Ces éléments ne sont pas des besoins confirmés.

## 4. Critères d'acceptation proposés

Les critères ci-dessous sont mesurables; les règles métier et la volumétrie
doivent être approuvées avant qu'ils deviennent contractuels.

1. Un utilisateur authentifié peut accéder aux fonctions permises par son rôle;
   les tests négatifs confirment qu'il ne peut pas lire ou modifier les données
   hors de sa portée.
2. Un CSV conforme à un schéma publié est validé et importé; un fichier
   invalide renvoie des erreurs localisées (ligne et champ) sans succès
   trompeur.
3. Une saisie peut être créée, corrigée et retrouvée après redémarrage du
   service.
4. Les imports répétés et les doublons suivent une règle explicitement
   approuvée et couverte par des tests.
5. Les rapports par période concordent exactement avec un jeu de données de
   référence approuvé, selon les règles financières validées.
6. Un import planifié réussit à l'heure prévue, journalise le résultat et
   signale un échec sans perdre les données déjà persistées.
7. Les exports CSV respectent les filtres et les permissions de l'utilisateur.
8. La restauration d'une sauvegarde est testée et atteint les objectifs RPO/RTO
   qui seront approuvés.
9. Pour la volumétrie de référence à définir, les rapports usuels respectent
   la cible de performance approuvée.

## 5. Hypothèses, recommandations et décisions ouvertes

- **Hypothèse :** le service est destiné à une seule organisation.
- **Recommandation :** privilégier le fournisseur d'identité déjà géré par
  l'organisation plutôt que d'introduire un IdP distinct.
- **Recommandation :** persister les saisies et corrections dans PostgreSQL;
  des corrections par plusieurs rôles ne sont pas adaptées à un simple CSV
  faisant office de base de données.
- **À décider avant conception détaillée :** sens de « local », fournisseur
  SSO, droits des rôles, source/cadence des imports, conservation/audit,
  devise, majoration et arrondis, volumétrie et objectifs de reprise.
- **Règle financière :** le multiplicateur `1.15` n'est pas confirmé. Ne pas
  l'utiliser comme règle de production sans validation de Finance.

## 6. Approbation

Ce PRD est une proposition. L'architecture, le périmètre MVP et la feuille de
route doivent être explicitement approuvés avant toute implémentation.
