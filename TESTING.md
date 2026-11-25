# Stratégie de test — Timesheet Pipeline

**Statut : stratégie proposée à valider.**

## Objectifs

Vérifier la justesse des calculs et imports, la protection des données entre
rôles, la persistance des corrections et la reproductibilité du déploiement.
Les seuils financiers et de performance ne deviennent obligatoires qu'après
validation des règles métier et de la volumétrie.

## Pyramide de tests

### Tests unitaires — `pytest`

Tester les fonctions métier sans réseau ni base de données :

- normalisation des champs admis, dates et projets;
- heures nulles/négatives, taux absents, colonnes manquantes et valeurs
  malformées;
- arrondis et coûts, une fois les règles financières approuvées;
- agrégations par période, projet et collaborateur, y compris ensemble vide;
- conversions décimales et limites de précision;
- règles de rôle et de portée avec autorisation et refus explicites;
- export CSV, échappement des valeurs et neutralisation des cellules de type
  formule;
- correction d'une saisie et attribution de l'auteur.

Chaque test de calcul utilise des exemples de référence chiffrés validés par
Finance; le multiplicateur 1.15 actuel ne constitue pas un oracle tant qu'il
n'est pas confirmé.

### Tests d'intégration

Outils proposés : `pytest`, `httpx`/`TestClient`, PostgreSQL de test via service
GitHub Actions ou conteneur de test.

- routes API, validation HTTP et codes d'erreur;
- migrations Alembic depuis une base vide et depuis la version précédente;
- transactions d'import : aucune validation partielle si le contrat exige
  l'atomicité;
- doublons, reprises après échec et répétition idempotente selon la politique
  décidée;
- application des filtres d'accès en lecture, écriture et export;
- intégration OIDC simulée avec un fournisseur de test, jamais avec l'IdP de
  production depuis CI;
- exécution planifiée : prise en charge d'une source absente, d'un fichier
  invalide et d'une répétition.

### Tests de bout en bout

Outil proposé : Playwright, une fois l'interface et les parcours approuvés.

1. Connexion simulée en test et affichage du rôle.
2. Création d'une saisie, correction, puis vérification dans le rapport.
3. Import valide et prévisualisation d'un CSV invalide avec erreurs de ligne.
4. Vérification qu'un rôle n'accède pas à une saisie non autorisée, y compris
   en appelant directement une route.
5. Export d'un rapport filtré, vérification des colonnes et du contenu.
6. Exécution du parcours de régression sur les navigateurs approuvés.

### Lint, types et qualité

- `ruff check .` pour le lint existant.
- `ruff format --check .` si le formatage Ruff est adopté.
- Vérification de types avec `mypy` ou Pyright après définition de la politique
  de typage; ne pas introduire les deux sans besoin.
- Vérification que les migrations et les dépendances sont cohérentes.

### Sécurité et dépendances

- `bandit` (ou équivalent) pour les motifs Python à risque.
- `pip-audit` pour les dépendances Python et Dependabot/Renovate selon la
  politique du dépôt.
- Scan de l'image avec Trivy ou outil approuvé par l'organisation.
- Tests d'autorisation négatifs pour chaque rôle et chaque ressource.
- Tests d'upload : fichier trop volumineux, mauvais encodage, colonnes inattendues,
  CSV mal formé, valeurs de formule et noms de fichiers hostiles.
- Revue de configuration des cookies, TLS, CORS, CSRF, en-têtes proxy et
  permissions des secrets.
- Aucun test d'intrusion contre l'IdP ou un système réel sans autorisation
  explicite et environnement dédié.

## CI et seuils

Chaque pull request devrait exécuter, dans l'ordre :

1. installation reproductible des dépendances verrouillées;
2. lint et formatage;
3. tests unitaires;
4. tests d'intégration sur PostgreSQL;
5. audit de dépendances et analyse statique de sécurité;
6. build Docker;
7. tests E2E ciblés sur environnement de test, si l'application UI est livrée.

Critères de merge proposés : suite obligatoire verte, aucune régression de
permission connue, aucune vulnérabilité critique/high non acceptée avec
dérogation documentée, migrations testées. Définir la politique des exceptions
et des versions vulnérables avant de rendre le scan bloquant.

## Tests d'acceptation métier

- Finance approuve un jeu de données étalon et les totaux attendus.
- Managers et employés valident les règles de visibilité et correction.
- L'équipe métier valide le modèle de CSV, les erreurs, les doublons et
  l'import planifié.
- Un export est comparé aux filtres affichés et ne contient aucune donnée hors
  portée.
- Restauration réelle d'une sauvegarde sur un environnement isolé.
- Test de performance sur un volume convenu, avec percentile, durée et
  simultanéité mesurés.

## Jeux de données et confidentialité

Utiliser des données synthétiques en CI et en démonstration. Ne pas copier le
CSV métier ou des taux horaires réels dans des journaux, artefacts publics ou
tests partagés. Les jeux de production ne peuvent être utilisés qu'avec
autorisation, minimisation et protection approuvées.
