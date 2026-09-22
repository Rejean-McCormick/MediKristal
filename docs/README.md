# Documentation MediKristal

[Accueil du dépôt](../README.md) · [Instructions de codage](../AGENTS.md)

Cette documentation définit la cible à implémenter. Les chapitres sont modulaires ; les contrats et exemples sont conservés dans leurs dossiers respectifs.

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
