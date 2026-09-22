# 19 — Plan de développement exécutable

## Stratégie

Le périmètre total est architecturalement prévu ; chaque lot livre une tranche réellement persistée. Le produit ne se limite pas à la recherche, mais les fixtures restent synthétiques tant que les contenus réels n'ont pas leurs preuves. L'IA peut avancer sans attendre un établissement pour les lots de structure, simulation de connecteurs et tests.

| Lot | Livrable | Dépendances | Gate de sortie |
|---|---|---|---|
| L0 | ADR stack, versions lockées, build offline, schémas et CI | Aucun | Validation contrats, SBOM, démarrage reproductible |
| L1 | Identité locale, tenant, cas et observations | L0 | Tests isolation, révision, doublons, correction |
| L2 | Source registry, imports, concepts, provenance et releases | L0 | Version source conservée, admission hash/droits |
| L3 | Snapshot et moteur synthétique probabiliste | L1,L2 | Oracle positif/négatif, missingness, replay |
| L4 | Protocoles et propositions, port CQF | L3 | Étapes, inconnus, arrêt, stale et permissions |
| L5 | Options thérapeutiques et contrôles synthétiques | L4 | Aucune ordonnance implicite, contrôles incomplets explicites |
| L6 | Capacités, coûts et comparaison de stratégies | L4 | Prix inconnus, perspectives, priorité indépendante |
| L7 | Booking et ordonnanceur OR-Tools | L6 | Concurrence, reçus, reconciliation et infeasible |
| L8 | Contributions, review, publication et retrait | L2,L3 | Comparaison versions, aucune promotion automatique |
| L9 | Interfaces patient/professionnel/admin/scientifique | L1-L8 par tranche | Parcours persistés et droits serveur |
| L10 | Trois modes, budget fournisseurs et sync | L2,L6 | Offline strict, coût borné, panne honnête |
| L11 | FHIR et export Kristal | L2,L4 | Fixtures externes, contrats épinglés, pas de PHI publique |
| L12 | Déploiement, sauvegarde, performance et exploitation | Lots précédents | Restauration, charge, incidents et statut honnête |
| L13 | Premier corpus clinique réel et qualification adaptée | Données/protocoles/revue | Rapports pour usage/population précis |

L13 n'est pas une condition pour écrire L0-L12 ; il est nécessaire avant de revendiquer l'usage clinique correspondant. Les connecteurs institutionnels réels exigent leurs contrats et accès, leur simulateur reste explicitement nommé test double.

## Tranche de référence

Créer un cas fictif ; collecter un symptôme synthétique ; calculer une hypothèse à partir du modèle synthétique ; demander une action ; comparer deux ressources fictives ; autoriser dans le seul environnement engineering ; recevoir un résultat fictif ; réévaluer ; proposer une option thérapeutique fictive ; corriger résultat ; montrer invalidation et nouvelle évaluation ; exporter seulement connaissance synthétique vers le profil Kristal lorsque conforme. Vérifier l'ensemble sans WAN.

## Definition of Done par ticket

Exigences associées, contrat/DTO, propriétaire, migration, contrôle d'accès, cas d'erreur, tests utiles, observabilité sans PHI, doc alignée et limitation déclarée. Aucune dépendance arbitraire à un réseau ou une clé fournisseur. Les TODO médicaux ne sont pas remplacés par valeurs plausibles.

## Tickets fondateurs

TKT-001 générer types depuis schémas ; TKT-002 create/read case avec tenant et ETag ; TKT-003 observation idempotente ; TKT-004 amendment + stale ; TKT-005 loader release signé ; TKT-006 feature builder avec unité/temps ; TKT-007 inference synthetic ; TKT-008 explanation API ; TKT-009 order guard ; TKT-010 source import quarantine ; TKT-011 provider budget ledger ; TKT-012 booking reconciliation. L'ordre suit dépendances, non ces numéros seuls.

## Priorités de réutilisation

Faire une preuve de compatibilité limitée pour CQF et les données FHIR avant un investissement UI important. Évaluer Snowstorm seulement si le volume/besoin terminologique le justifie. Éviter un dossier hospitalier complet et une intégration nationale initiale. Les adaptations Kristal sont petites et testées ; ne pas forker le framework pour faire passer une fixture incompatible.

## Livraison continue

Versions application, contrats, connaissances et modèles distinctes. Releases reproducibles avec digest, notes de migration, rapport de tests et capacités. Feature flags ne contournent pas les guards serveur. Un flag experimental peut rendre une capacité visible en engineering, pas cliniquement admise.

## Précision de séquencement v1.1

Les [tickets complémentaires](32-build-order.md) rendent les imports, workflows, suivi et catalogues livrables séparément. Offline, permissions et interface minimale commencent avec chaque tranche ; L9/L10 sont des lots de consolidation. Utiliser la [matrice de couverture](26-coverage.md) comme checklist de lot.
