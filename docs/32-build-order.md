# 32 — Ordre de réalisation et décisions techniques

## Optimisation de l’effort

Conserver le monolithe modulaire, une base relationnelle et une outbox. Commencer par une tranche verticale synthétique traversant toutes les frontières : cas, connaissance, inférence, proposition, ressource, résultat et suivi. Étendre ensuite chaque module. Une interface complète construite sur des réponses simulées ne valide pas la tranche.

Le fonctionnement offline, les permissions et les contrôles de révision commencent en L0/L1 ; L10 les étend aux fournisseurs et synchronisations. Les interfaces arrivent avec chaque tranche ; L9 consolide les quatre parcours. Cela corrige toute lecture du plan initial qui reporterait sécurité, offline ou utilisabilité à la fin.

## Tickets complémentaires

| Ticket | Lot | Livrable | Dépendance | Gate |
| --- | --- | --- | --- | --- |
| TKT-013 | L2 | Import local en deux phases et rapport | TKT-010 | Diff stable, reprise sans doublons |
| TKT-014 | L2 | Premier profil LOINC sur fixture autorisée | TKT-013 | Colonnes, statut, version et droits |
| TKT-015 | L2 | HPO et annotations distinctes | TKT-013 | Négations et fréquences non inversées |
| TKT-016 | L5 | Terminologie de médicaments | TKT-013 | Ingrédient/produit séparés |
| TKT-017 | L4 | Workflow durable | TKT-009 | Reprise et guards à chaque étape |
| TKT-018 | L6 | Comparateur de stratégies finies | L3,L4 | Coût de branche et contraintes |
| TKT-019 | L7 | Ordonnancement collectif | TKT-018 | Concurrence, indisponibilité et priorités |
| TKT-020 | L5 | Plan de soins et tâches de suivi | L1,L5 | Propriétaire, résultat tardif, échéance |
| TKT-021 | L1,L11 | Réception atomique d’un rapport | TKT-003,004 | Même version/digest divergent rejeté |
| TKT-022 | L6 | CRUD versionné de catalogues | L2 | Retrait sans perte d’historique |
| TKT-023 | L8 | Diff de modèles et analyse de retrait | L3,L8 | Pas de promotion automatique |
| TKT-024 | L9 | Écrans reliés aux capacités | Tranche correspondante | États erreur/inconnu/reprise persistés |
| TKT-025 | L12 | Matrice de capacité publiée | Tous par incréments | Aucune capacité annoncée sans gate |

## Réutilisation : décision par preuve

Pour chaque candidat déjà mentionné au chapitre 19, conserver un dossier de décision : version exacte, licence, fonction utilisée, déploiement offline, consommation mémoire, test de compatibilité, maintenance, alternative et coût d’intégration. L’existence d’un projet open source ne prouve ni sa gratuité opérationnelle ni son adéquation clinique.

Ports de référence : `TerminologyPort`, `ProtocolPort`, `InferencePort`, `PlanningPort`, `FacilityPort` et `ResultsPort` (noms canoniques du chapitre 13). Une bibliothèque peut être intégrée directement derrière un port ; elle n’impose pas un microservice. Aucun produit externe n’est nécessaire pour les tests synthétiques des frontières ; un double de test est nommé et ne peut être activé comme fournisseur clinique.

## Politique de paramètres

L’IA peut fixer des paramètres techniques réversibles : nombre de workers, limite de pagination déjà contractuelle, durée maximale de job, répertoire local, index SQL. Elle documente leur effet et les mesures. Elle ne choisit pas par commodité une prévalence, un seuil d’action, une utilité clinique ou une fenêtre de sécurité.

Chaque paramètre clinique absent reste absent et produit un code de raison. Un profil engineering peut en fournir une valeur explicitement synthétique ; sa signature/type empêche l’admission dans un profil clinique. Les règles ne doivent pas dépendre de noms de fichiers « test » pour cette séparation.

## Gate par fonction

Une fonction livrée inclut migrations, commande typée, contrôles, reprise après panne, explication et preuve de tests. Le statut de capacité comporte `specified`, `implemented`, `qualified_software`, puis les preuves d’usage prévues au chapitre 01. Les erreurs/permissions font partie de la gate, pas d’une phase optionnelle de durcissement.

## Reste à décider au démarrage du code

Versions exactes et lockfiles ; implémentation d’identité/chiffrement ; fixture externe autorisée pour chaque parser ; premier corpus clinique réel ; politique d’autorisation locale. Le choix du corpus ne bloque pas les tickets purement logiciels. Toutes les versions de format et dépendances réellement retenues remplacent les propositions documentaires dans une ADR datée.
