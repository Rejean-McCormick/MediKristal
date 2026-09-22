# Historique

## Documentation 1.1 — Contrats 0.2.0

- Ajout de huit chapitres : couverture, connecteurs, optimisation, automatisation, contrats opérationnels, interfaces, réalisation et acceptation.
- 32 exigences reliées à leurs contrats, objets, interfaces, événements, lots et scénarios d’acceptation.
- Extension à 107 définitions de schéma et 80 opérations d’API ; 12 exemples synthétiques.
- Catalogues révisables, workflows durables, réception atomique de résultats, plans de soins et suivi.
- Clarification des choix économiques : stratégies conditionnelles, contraintes cliniques, coûts inconnus et absence de modèle.
- Formats LOINC/HPO/RxNorm et échange FHIR documentés avec sources officielles ; aucune qualification d’import réel revendiquée.
- Correction des ambiguïtés sur l’exhaustivité, les tests documentaires et l’ordre de réalisation.

Le contrat API reste sous `/api/v1`; la version 0.2.0 désigne le contrat de développement. `Capabilities.api_version` passe à 0.2.0. Les schémas existants restent conservés sauf cette constante ; les nouvelles définitions et routes sont additives. Les consommateurs doivent régénérer leurs types et revoir les permissions. Les exemples 0.1.0 d’artefacts synthétiques gardent leur version propre.

## Documentation 1.0 — Contrats 0.1.0

Première référence modulaire : 25 chapitres, 24 exigences, 80 définitions, 47 opérations et 8 exemples. Aucun logiciel clinique implémenté dans le dossier.

## Implémentation de référence 0.2.0 — 2026-09-22

- Runtime FastAPI aligné sur les 80 opérations du contrat.
- Historique de révisions append-only, grants par cas, claims de réservation atomiques et inbox/outbox dédupliquée.
- Import CSV local en quarantaine, releases synthétiques versionnées, révocation avec analyse d’impact et politiques fournisseur/budget.
- Interface Web corrigée pour utiliser les digests d’artefacts réels au lieu de références factices.
- Migration Alembic rendue rejouable en mode batch SQLite pour le harnais de test.
- Suite applicative portée à 73 tests avec 91 % de couverture globale mesurée ; intégrations Kristal/FHIR externes restent explicitement non configurées.

- Durcissement du worker par claim inbox transactionnel, rejeu exact des résultats, grants par cas, claims de réservation et erreurs HTTP au format Problem JSON.
- Compose sans mot de passe PostgreSQL codé en dur et processus applicatifs Docker exécutés sous un utilisateur non-root.
