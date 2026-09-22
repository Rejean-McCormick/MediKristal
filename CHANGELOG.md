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
