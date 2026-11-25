# Feuille de route — Timesheet Pipeline

**Statut : proposition à valider — aucun travail d'implémentation ne commence
avant l'approbation explicite du périmètre, de l'architecture et de cette
feuille de route.**

## Principes de séquencement

- Clarifier les décisions qui changent le modèle de données et le déploiement
  avant d'écrire ces composants.
- Livrer une tranche fonctionnelle vérifiable à chaque phase.
- Ne pas importer de vraies données dans des environnements de test.
- Les durées dépendent des réponses ouvertes, de l'équipe et des accès; aucune
  estimation calendaire n'est inventée ici.

## Phase 0 — Décisions produit et architecture

**Tâches**

- Confirmer le problème métier, la portée des rôles et les règles de visibilité.
- Préciser si l'hébergement « local » est développement ou production on-premise.
- Identifier l'IdP, le protocole et les groupes/claims disponibles.
- Définir CSV, encodage, source, fréquence, doublons et reprise des imports.
- Valider les corrections, audit, rétention et suppression.
- Faire approuver par Finance devise, majoration, précision et arrondis.
- Définir volumétrie, simultanéité, disponibilité, RPO/RTO et navigateurs.
- Approuver les cinq documents de planification.

**Dépendances :** disponibilité des parties prenantes métier, Finance et IT.

**Livrables :** PRD, architecture, stratégie de test, DevOps et roadmap
approuvés; décisions ouvertes consignées.

**Critère de sortie :** aucun choix bloquant n'est présenté comme confirmé sans
validation; périmètre MVP signé.

## Phase 1 — Socle applicatif et données

**Tâches**

- Définir le modèle relationnel, migrations, contraintes et conversions
  décimales.
- Configurer PostgreSQL, paramètres par environnement et gestion de secrets.
- Séparer API, règles métier et accès aux données selon la structure approuvée.
- Ajouter liveness/readiness et erreurs cohérentes.
- Tester migrations et sauvegarde/restauration de base.

**Dépend de :** phase 0, décision de persistance et hôte de développement.

**Livrables :** service exécutable avec schéma versionné et tests d'intégration.

**Critère de sortie :** migrations reproductibles; données de test survivent au
redémarrage; erreurs de configuration sont explicites.

## Phase 2 — Identité et autorisations

**Tâches**

- Intégrer OIDC/SAML à l'IdP confirmé.
- Mapper les identités/groupes aux rôles employé, manager et Finance.
- Protéger les routes, les lignes de données, rapports et exports côté serveur.
- Ajouter audit minimal des changements suivant la politique décidée.

**Dépend de :** phase 0 et accès à un IdP de test; phase 1 pour les relations
persistées d'identité/saisie.

**Livrables :** parcours SSO testé et matrice d'accès automatisée.

**Critère de sortie :** accès autorisés fonctionnels; tests négatifs prouvent
qu'un rôle ne franchit pas sa portée.

## Phase 3 — MVP de saisie, correction et rapports

**Tâches**

- Construire l'interface web server-rendered de saisie et correction.
- Implémenter les rapports par période, projet et collaborateur.
- Ajouter calculs utilisant uniquement les règles financières approuvées.
- Ajouter exports CSV filtrés et protégés.
- Valider les parcours avec les trois groupes d'utilisateurs.

**Dépend de :** phases 1 et 2; règles Finance approuvées.

**Livrables :** parcours web de bout en bout pour saisir, corriger, consulter
et exporter.

**Critère de sortie :** les totaux concordent avec le jeu d'acceptation; aucun
écart de permission connu; validation utilisateur réussie.

## Phase 4 — Imports CSV, batch et planification

**Tâches**

- Définir et documenter le format CSV canonique.
- Implémenter validation, prévisualisation, erreurs par ligne, atomicité ou
  politique de rejet partiel approuvée.
- Ajouter gestion de doublons, idempotence et identifiant d'exécution.
- Traiter les lots de fichiers.
- Configurer le déclencheur et l'accès sécurisé à la source interne.
- Ajouter reprise, timeout, limites et alertes d'échec.

**Dépend de :** phase 0 (source/cadence/politique de doublons), phase 1 et
permissions de la phase 2.

**Livrables :** imports interactifs et planifiés traçables.

**Critère de sortie :** jeux de test valides, invalides, répétés et incomplets
produisent des résultats déterministes et des erreurs exploitables.

## Phase 5 — CI/CD, staging et préparation production

**Tâches**

- Renforcer CI sur pull request : tests, scan dépendances/sécurité et build.
- Construire une image immuable et publier vers un registre privé approuvé.
- Déployer en staging et valider SSO de préproduction.
- Tester sauvegarde/restauration, supervision et procédure de rollback.
- Mesurer performance et ajuster les limites à la volumétrie convenue.
- Obtenir approbation opérationnelle et métier pour la production.

**Dépend de :** phases 1 à 4 et environnement cible disponible.

**Livrables :** procédure reproductible de staging/production et runbook.

**Critère de sortie :** checks obligatoires verts; restauration vérifiée;
rollback documenté; critères d'acceptation signés.

## Principaux risques et mitigations

| Risque ou bloqueur | Impact | Réponse proposée |
|---|---|---|
| « Local » signifie poste personnel et non serveur permanent | Imports planifiés et SSO multi-utilisateurs peu fiables | Décider le lieu d'hébergement en phase 0; recommander un hôte interne toujours disponible. |
| Fournisseur SSO ou claims indisponibles | Blocage auth/rôles | Obtenir un IdP de test et un propriétaire IT avant phase 2. |
| Majoration de 15 % non validée | Rapports financiers erronés | Suspendre la mise en production des montants jusqu'à validation Finance. |
| Politique de doublons/corrections inconnue | Perte ou double comptage | Définir idempotence, audit et règles de correction avant import persistant. |
| Fichiers et taux confidentiels | Fuite de données métier | Données synthétiques en CI, stockage privé, contrôle d'accès et rétention. |
| Volumétrie inconnue | Mauvais choix de limites/traitement | Mesurer sur un échantillon autorisé et fixer un jeu de charge de référence. |
| Déploiement Docker Hub existant | Publication inattendue ou image publique | Confirmer registre/visibilité; remplacer la publication automatique par une promotion contrôlée. |

## Approbation requise avant implémentation

L'approbation doit couvrir explicitement :

1. le périmètre MVP et les exclusions;
2. l'architecture et les technologies;
3. les règles d'accès, données et calculs;
4. la stratégie d'hébergement, CI/CD et exploitation;
5. l'ordre des phases et leurs critères de sortie.

Tant que ces éléments ne sont pas approuvés, seuls la planification et la
documentation sont dans le périmètre.
