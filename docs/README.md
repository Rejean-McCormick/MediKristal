# Documentation MediKristal

[Accueil du dépôt](../README.md) · [Instructions de codage](../AGENTS.md)

La [documentation du système final](SYSTEME_FINAL.md) présente l’architecture cible, les parcours, les choix d’optimisation et les preuves attendues. L’[état observé du 27 novembre 2026](ETAT_2026-11-27.md) précise ce que la capture permet de vérifier. Les chapitres ci-dessous détaillent les exigences, et le dossier `contracts/` contient les contrats de la version livrée.

## Utiliser cette version

[Installation, parcours et périmètre livré](LIVRAISON_2.0.md)

## Démarrer le codage

1. [Démarrage IA](DEMARRAGE_IA.md) — ordre de lecture, points d’entrée du code et commandes du dépôt.
2. [Backlog du système final](BACKLOG_SYSTEME_FINAL.md) — dépendances, livrables et preuves par ticket. Commencer par MK-SF-01.
3. [Patterns retenus](PATTERNS_ARCHITECTURE.md) — frontières du monolithe, reprise et interface.
4. [Profil de qualification](PROFIL_QUALIFICATION.md) — scénario autonome, concurrence, charge et restauration.

Ce dossier s’intègre à la racine du checkout MediKristal. Les chemins vers le code, les contrats et `AGENTS.md` se résolvent dans ce checkout.

## Référentiels locaux

- [Télécharger les référentiels](TELECHARGER_SOURCES_MEDICALES.md) — emplacement, lot public et accès éditeurs.
- [Importer et rechercher](IMPORTER_REFERENTIELS_PUBLICS.md) — index SQLite hors ligne et commande de recherche.
- [Résultat sur Windows](ETAT_2026-11-27.md#vérification-des-référentiels-sur-le-poste-windows) — fichiers, volumes et preuve de recherche.

## Parcours de lecture

- **IA de développement** : AGENTS, chapitres 01–04, puis 19, le module concerné, 13, 18 et 24–25.
- **Architecture et intégration** : 02–06, 12–14, 16–17 et 20.
- **Raisonnement clinique et méthodes** : 04–11, 18 et 21–23.
- **Interfaces et exploitation** : 09, 12, 15–17 et 22.

## Fondements

- [01 — Vision et exigences](01-vision.md)
- [02 — Architecture et choix techniques](02-architecture.md)
- [03 — Dictionnaire des données et persistance](03-data.md)

## Modules fonctionnels

- [04 — Cycle du cas et observations](04-case.md)
- [05 — Sources, terminologies et droits](05-sources.md)
- [06 — Connaissances, preuves et publications](06-knowledge.md)
- [07 — Inférence probabiliste](07-inference.md)
- [08 — Protocoles et investigations](08-pathways.md)
- [09 — Ressources, coûts et ordonnancement](09-resources.md)
- [10 — Options thérapeutiques](10-treatment.md)
- [11 — Contributions scientifiques et gouvernance](11-contributions.md)
- [12 — Modes, fournisseurs et synchronisation](12-modes.md)

## Contrats et intégrations

- [13 — API, événements et adaptateurs](13-api.md)
- [14 — FHIR, Kristal et écosystème](14-integrations.md)

## Interfaces, sécurité et exploitation

- [15 — Interfaces et parcours](15-interfaces.md)
- [16 — Sécurité, confidentialité et autorisations](16-security.md)
- [17 — Installation et exploitation](17-operations.md)

## Tests et réalisation

- [18 — Qualification et tests](18-tests.md)
- [19 — Plan de développement exécutable](19-delivery.md)
- [20 — Décisions d'architecture et points non résolus](20-decisions.md)

## Références détaillées

- [21 — Taxonomie des actes diagnostiques](21-diagnostics.md)
- [22 — Scénarios de bout en bout](22-scenarios.md)
- [23 — Sources et provenance documentaire](23-sources.md)
- [24 — Erreurs et invariants](24-errors.md)
- [25 — Compléments d'implémentation](25-implementation-details.md)

## Annexes exécutables

- [Contrats et schémas](../contracts/README.md)
- [Exemples synthétiques](../examples/README.md)
- [Rapport de vérification documentaire](../VALIDATION.md)

## Maintenir cette référence

Mettre à jour ensemble le chapitre concerné, les contrats, les exemples et les critères d’acceptation. Enregistrer les décisions structurantes dans le chapitre 20. Ne pas annoncer une fonctionnalité implémentée sur la seule base de sa présence dans ces documents.

## Spécifications opérationnelles v1.1

- [26 — Couverture fonctionnelle et règles de complétude](26-coverage.md)
- [27 — Connecteurs et intégration des sources](27-connectors.md)
- [28 — Politique d’optimisation et comparaison des stratégies](28-optimization.md)
- [29 — Automatisation autorisée du parcours](29-automation.md)
- [30 — Contrats opérationnels complémentaires](30-operational-contracts.md)
- [31 — Contrats des interfaces et états visibles](31-ui-acceptance.md)
- [32 — Ordre de réalisation et décisions techniques](32-build-order.md)
- [33 — Scénarios d’acceptation et preuve de réalisation](33-acceptance.md)

- [Historique des versions](../CHANGELOG.md)
- [Matrice structurée de traçabilité](../contracts/traceability.json)

## Final-system interoperability and independent evidence

- [Engineering-only qualification boundary (FC-20 / FC-18)](FINAL_SYSTEM_ENGINEERING_BOUNDARY.md) — English owner/diagnostic agreement, without claiming clinical certification.

## Vérification des dépôts satellites

- [Contrats, versions et limites de qualification (27 octobre 2026)](Integration-Verification-2026-10-27.md)
