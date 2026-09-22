# 18 — Qualification et tests

## Niveaux de preuve

1. Validation documentaire : JSON, liens, références, exemples, cohérence des exigences.
2. Tests unitaires de domaine : invariants, transitions, calculs et permissions.
3. Contrats : adaptateurs, schémas externes et compatibilité versionnée.
4. Intégration : DB réelle, jobs, outbox, concurrence et crash.
5. Parcours UI/API : persistance et erreurs visibles.
6. Validation clinique : performances et conséquences dans la population et finalité visées.
7. Admission du déploiement : politiques et exigences applicables satisfaites.

Ce dossier exécute seulement le niveau 1 et un oracle arithmétique synthétique. Les niveaux applicatifs suivants sont spécifiés et doivent être implémentés. Aucun test clinique n'a été effectué.

## Matrice d'acceptation

| Test | Scénario | Attendu | Exigences |
|---|---|---|---|
| T01 | Réseau coupé, corpus installé | Parcours synthétique complet, aucune sortie WAN | MK-001,002 |
| T02 | Import identique deux fois | Une observation effective, même posterior | MK-004,007 |
| T03 | Identifiant source identique, contenu différent | Conflit sans écrasement | MK-004,018 |
| T04 | Résultat inconnu | Pas converti en négatif/zéro | MK-006,018 |
| T05 | Score non calibré | Pas de `%`, aucune probabilité fabriquée | MK-006 |
| T06 | Observation corrigée | Ancien résultat traçable, proposition périmée | MK-007,016 |
| T07 | Unité ambiguë | Quarantaine ou abstention | MK-004,018 |
| T08 | Modèle hors population | out_of_scope, action exécutive bloquée | MK-006,019 |
| T09 | Données corrélées | Modèle joint/règle déclarée, pas multiplication naïve | MK-006 |
| T10 | Cas modifié durant calcul | Résultat stale, validation refusée sans revalidation | MK-007,016 |
| T11 | Deux clients, un créneau | Au plus une confirmation propriétaire | MK-010 |
| T12 | Timeout après réservation distante | Reconciliation, pas double booking | MK-010,018 |
| T13 | Coût absent | unknown, pas 0 | MK-009 |
| T14 | Source de prix différente | Perspectives affichées, comparaison contrôlée | MK-009 |
| T15 | Quota payant concurrent | Pas de dépassement autorisé par race | MK-017 |
| T16 | Passage online→offline | Capacités/fraîcheur explicites | MK-002,018 |
| T17 | Export Kristal | Validation native, aucune PHI, statuts préservés | MK-014,015 |
| T18 | Pack falsifié/révoqué | Admission refusée et auditée | MK-024 |
| T19 | Accès autre tenant | Aucune donnée ni différence exploitable | MK-015 |
| T20 | Patient appelle endpoint d'ordre | Refus serveur | MK-003,019 |
| T21 | Admin ressources publie validation clinique | Refus serveur | MK-019,022 |
| T22 | Fournisseur payant non activé | Aucun appel externe | MK-017,023 |
| T23 | Résultat critique selon fixture | Suivi durable avec acquittement séparé | MK-007 |
| T24 | Interaction médicamenteuse inconnue | Contrôle incomplet, pas « aucune interaction » | MK-011,018 |
| T25 | Révision scientifique acceptée | Aucune activation avant publication/admission | MK-012,024 |
| T26 | Corpus contenant instructions malveillantes | Traité comme donnée, aucun pouvoir | MK-015 |
| T27 | Résultat réimporté hors ordre temporel | Chronologie clinique correcte | MK-007 |
| T28 | Révocation fraîcheur offline inconnue | Politique locale + statut de fraîcheur | MK-002,024 |
| T29 | Rejeu sans dépendance externe | Résultat conforme aux tolérances déclarées | MK-016 |
| T30 | Intégration kOA absente | Fonctionnement autonome conservé | MK-001,013 |
| T31 | Demande fournisseur mélange tenant/patient | Rejet et journal minimisé | MK-015 |
| T32 | Taxonomie acte vs appareil | Réservation vérifie capacité complète | MK-021 |
| T33 | Augmentation du coût d'un test | Probabilités inchangées, plan éventuellement différent | MK-006,009,022 |
| T34 | Correction de mapping | Impact calculé sans mutation historique | MK-005,024 |
| T35 | Questions/réévaluation comme alternative | Comparables lorsque modèle d'utilité le permet | MK-008 |
| T36 | Adaptateur absent | capability_unavailable, pas stub positif | MK-018,020 |

## Tests statistiques

Sur datasets autorisés : séparation patient/site/temps, pas de fuite, vérification labels, calibration et discrimination, intervalles, sous-groupes, données manquantes, externes et hors domaine. Comparer modèles à baseline explicite. Évaluer abstention et erreurs graves, pas seulement accuracy moyenne. Le jeu synthétique permet seulement de vérifier algorithmes et états.

## Tests de décision et solveur

Petits problèmes exhaustivement énumérables pour vérifier objectif/contraintes, puis instances de charge. Tester priorité clinique indépendante du coût, données incertaines, stratégies dominées, impossibilité et timeout. La reproductibilité d'OR-Tools exige seed, paramètres, version et état du problème ; si solutions équivalentes multiples, vérifier faisabilité/objectif et appliquer tie-break stable si requis.

## Génération de fixtures

Utiliser maladie A/B, test SYN-T1, substance SYN-DRUG. Ne pas employer des noms de maladies réelles avec paramètres inventés. Marquer `synthetic=true`, environnement engineering, source synthétique et absence de validation clinique. Tester que ces marqueurs interdisent une admission clinique.

## Rapports

Chaque rapport nomme commande, environnement, versions, temps, tests exécutés, PASS/FAIL/SKIP et limites. Un PASS documentaire n'est pas un PASS applicatif. Aucun compteur ou badge de maturité globale ne remplace les gates individuels.

## Extension v1.1

Les exigences MK-025,026,027,028,029,030,031,032 ont leurs scénarios détaillés AT-025 à AT-032 dans le [chapitre 33](33-acceptance.md). La [matrice](../contracts/traceability.json) relie aussi les 24 exigences initiales à un scénario AT explicite. Aucun de ces scénarios n’est déclaré exécuté sur l’application par cette livraison documentaire.
