# 03 — Dictionnaire des données et persistance

## Conventions

Identifiants métier opaques UUID ; identifiants conceptuels = triplet `system`, `code`, `version`. Une étiquette traduite n'est jamais une clé. Les identifiants étrangers sont namespacés par propriétaire et tenant. Dates ISO 8601 UTC avec fuseau ; préserver fuseau local, précision et date clinique d'origine. Distinguer `effective_at` (moment clinique), `recorded_at` (saisie), `received_at` (réception) et `superseded_at`.

Toute entité opérationnelle possède `id`, `tenant_id`, `revision`, `created_at`, `updated_at`. La révision est un entier croissant. Les tables multi-tenant ont index et clés étrangères composites incluant tenant ; une UUID connue n'autorise pas l'accès. Les snapshots et publications sont immuables et référencés par digest. Les champs structurés exigent un schéma ; JSONB n'autorise pas un modèle implicite libre.

Les nombres d'argent sont des entiers en unité monétaire mineure avec devise ISO, jamais des floats. Les valeurs de laboratoire gardent la précision textuelle initiale, leur unité et une valeur normalisée lorsque la conversion est autorisée. `null`, champ omis, absence clinique et valeur zéro ont des significations distinctes.

## Objets d'identité et contexte

`Subject` contient pseudonyme local, liens d'identité externes protégés, attributs démographiques utiles et leur provenance. Ne pas supposer qu'un compte utilisateur est le patient. `Encounter` contient cas, lieu, type de rencontre, intervalle et équipe. `ConsentRecord` contient finalité, périmètre, destinataire, validité et révocation ; ce n'est pas l'unique base possible d'accès institutionnel. `AccessGrant` exprime la justification et les droits effectifs locaux.

Les attributs sensibles (grossesse, caractéristiques physiologiques, sexe pertinent à un calcul) ne sont pas déduits automatiquement d'un prénom, d'un genre déclaré ou d'une absence de donnée. Stocker uniquement les attributs requis par le modèle, avec source et état inconnu.

## Cas et observations

`ClinicalCase` : subject_ref, encounter_ref facultatif, lifecycle, revision, intended_use, language, context_refs, active_release_ref. Le cas n'est pas le diagnostic.

`Observation` : concept, type (`symptom`, `sign`, `measurement`, `history`, `exposure`, `medication`, `allergy`, `test_result`, `patient_report`), assertion_presence (`present`, `absent`, `unknown`, `not_assessed`), valeur typée éventuelle, unité, temps clinique, source, auteur, statut, liens foreign/sample/order, méthode, qualité, dépendances, original_payload_ref. Absence = information explicite, pas champ vide.

Valeurs : quantity (valeur/unité), coded (concept), boolean, text, interval, ratio. Un résultat censuré `<x` conserve son comparateur ; ne pas le remplacer par x ou x/2. L'intervalle de référence du laboratoire est une métadonnée, pas un seuil diagnostique universel.

`ObservationAmendment` : observation originale, nouvelle version, raison, auteur et instant. `CaseSnapshot` inclut toutes les versions actives requises et le contexte figé. Une suppression d'affichage n'efface pas la traçabilité légitime ; la politique de rétention gouverne suppression ou anonymisation effective.

## Connaissances

`SourceSnapshot` : éditeur, URI, date/version, bytes_digest, license_decision_ref, contenu brut, méthode d'acquisition.

`ConceptMapping` : concept source/cible, relation (`equivalent`, `broader`, `narrower`, `related`, `unmapped`), direction, contexte, provenance, auteur, statut, validité. L'équivalence n'est ni symétrisée ni transitive automatiquement entre mappings contextuels.

`MedicalAssertion` : sujet, prédicat typé, objet, qualifiers, sources, certainty, validation et recognition séparés. Types de prédicats : association, fréquence, causalité documentée, indication, exclusion, interaction, contre-indication ; ne pas fusionner ces sens dans `related_to` pour l'inférence.

`EvidenceEstimate` : cible, estimand, mesure (`prevalence`, `sensitivity`, `specificity`, `likelihood_ratio_positive`, `likelihood_ratio_negative`, `conditional_probability`, `effect_size`), valeur, intervalle avec type/niveau, effectifs, population, setting, référence diagnostique, seuil, temps, biais/limitations, extraction/review_refs. Les dénominateurs sont nécessaires lorsqu'ils sont disponibles. Une fréquence HPO n'est pas une probabilité postérieure.

`ModelManifest` : modèle, type, paramètres, entrées, features, populations, exclusions, monde diagnostique, dépendances, version moteur, preuves d'évaluation, calibration, abstention, horloge, seed, précision et droits. Une définition manquante interdit l'utilisation probabiliste clinique.

`ProtocolManifest` : identifiant/version, entrée, population, préconditions, étapes, transitions, actions, exceptions, arrêt, red flags sourcés, validation et dépendances.

## Décisions dérivées

`Evaluation` : snapshot du cas, snapshot des ressources utilisé ou null, release de connaissances, modèles exécutés, application status, hypothesis_results, missing_inputs, conflicts, limitations, explanation_graph, durée, moteur et hash de replay.

`HypothesisResult` : concept, type (`probability`, `score`, `qualitative`), valeur ou null, intervalle, target_event, horizon, population, model_ref, calibration_ref, scope_status, evidence_refs et reason_codes. Les probabilités sont entre 0 et 1 ; un score n'est pas soumis à cette borne et ne s'affiche jamais avec `%`.

`ActionProposal` : kind (`ask`, `examine`, `test`, `observe`, `refer`, `treat_option`), cible, indication, prérequis, contre-indications, horizon, raisons, alternatives, version du cas, état et expiry. `Decision` : proposition choisie/refusée/modifiée, acteur, justification, politique et révision du cas.

`CarePlan` : propositions ordonnées ou branchées, conditions de transition, horizons et statut. `TreatmentOption` référence le médicament/substance/procédure, objectif, preuves, contrôles et modèle de calcul éventuel ; une option n'est pas une ordonnance.

## Ressources et opérations

`DiagnosticProcedure` : acte prescriptible, anatomie, méthode, protocole, contraste, prélèvement, préparation, durée et résultat attendu. `ResourceCapability` lie cet acte à un site, équipement compatible, personnel, horaires et consommables. `AvailabilitySnapshot` a source, captured_at, valid_until, slots/capacity et mode confirmed/estimated.

`CostQuote` : objet tarifé, montant, devise, type (`marginal`, `average`, `tariff`, `patient_out_of_pocket`), perspective, composants, intervalle de validité, site et source. Inconnu n'est pas gratuit.

`ServiceOrder` : acteur autorisant, proposition, version du cas, destinataire, prescription/commande native éventuelle, statut externe et corrélation. `Booking` : ordre, capacité, créneau, propriétaire, identifiant étranger, lease et statut. `Specimen` : type, collecte, transport, réception, qualité et identifiants de traçage. Le suivi d'échantillon est minimal et consomme le LIS propriétaire.

`IntegrationOperation` : destination, payload_digest, idempotency_key, état, attempts, last_error, retry_after, remote_receipt. `ProviderUsage` : réservation budgétaire, fournisseur, usage estimé/réel, devise, principal et statut.

## Tables et contraintes prioritaires

Tables par module dans un schéma SQL séparé ou préfixe stable. Contraintes : unicité `(tenant, source_system, foreign_id, foreign_version)` pour les imports ; unicité `(tenant, principal_scope, route, idempotency_key)` pour commandes ; non-chevauchement des réservations locales sur ressource exclusive avec intervalle SQL ; `start < end` ; coûts >= 0 ; probabilités bornées ; source et destination d'une FK appartiennent au même tenant sauf corpus explicitement global autorisé.

Index : cas + effective_at ; ordre + statut ; concepts par system/code/version ; sources par digest ; opérations par next_attempt/status ; disponibilité par site/acte/intervalle. Pour les recherches nominatives, politique de confidentialité distincte et index non partagé entre tenants. Les archives ont rétention et partitionnement temporel ; pas d'effacement d'un corpus encore référencé sans stratégie d'archivage.

## Sémantique des contrats structurés

Le JSON Schema joint impose la forme des DTO v0.2. Les entités détaillées ici définissent la cible complète. Certains agrégats utilisent une référence plutôt que répéter toutes les structures. Les comparaisons de dates, autorisations, intégrité référentielle, validité des unités, absence de PHI dans un export et adéquation clinique ne peuvent pas être prouvées par le seul schéma : elles exigent les validateurs applicatifs décrits dans les tests.
