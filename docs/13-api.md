# 13 — API, événements et adaptateurs

## Contrat HTTP

Base `/api/v1`. JSON UTF-8, identifiants opaques, dates UTC, tenant résolu depuis principal et grant. Authentification bearer OIDC lorsque configuré ou jeton/session local ; pas d'IdP distant obligatoire. Une session navigateur exige cookie protégé et CSRF pour mutations ; l'OpenAPI décrit le transport bearer. `/capabilities` publie les fonctions disponibles sans secrets.

Le fichier `contracts/openapi.json` est le contrat transport v0.2, non la preuve d'un serveur existant. Il référence les DTO de `contracts/domain.schema.json`. Les descriptions par opération définissent permission, préconditions et effets. Toute fonctionnalité cible absente du contrat v0.2 doit être ajoutée par évolution de contrat avant implémentation publique, jamais exposée comme endpoint non documenté.

## Concurrence et idempotence

Les commandes créatrices exigent `Idempotency-Key`. Conserver tuple tenant/principal/route/key, hash canonicalisé de la requête et réponse initiale. Même demande = même ressource ; demande différente = 409. Le registre opérationnel conserve la clé aussi longtemps que l'opération peut être rejouée ; ne pas purger une réservation active par un TTL arbitraire.

Les mutations d'entités existantes exigent `If-Match` avec révision obtenue via ETag. Absence = 428, divergence = 412. Comparer transactionnellement, y compris opérations fondées sur évaluation. `GET` ne déclenche pas de mutation clinique. Les évaluations peuvent être asynchrones : POST retourne 202 et Operation, puis GET operation fournit état et result_ref. 202 n'est pas un résultat clinique.

## Erreurs et pagination

Erreur structurée `type,title,status,code,detail,correlation_id,field_errors,retryable`. Pas de donnée sensible dans detail. 401 authentification, 403 droit, 404 objet inaccessible/inexistant sans fuite, 409 conflit métier, 412 révision, 422 structure/sémantique, 428 précondition, 429 quota, 503 capacité indisponible. Les états `insufficient_data` ou `out_of_scope` d'une évaluation sont des résultats métier réussis, pas des 500.

Listes : curseur opaque signé contenant filtre, tri et snapshot/watermark, limite 1..100, next_cursor ou null. Ordre stable par date et id. Rejeter réutilisation du curseur avec autre filtre/tenant. Export massif est un job autorisé, pas une pagination sans limite.

## API applicative attendue

Cas : créer/lire, ajouter observation, amender, transitionner, demander évaluation et consulter résultats. Connaissances : consulter releases, chercher concepts/assertions, ingérer source autorisée, construire/activer release. Parcours : demander comparaison, accepter/refuser proposition. Ressources : administrer capacités/coûts, consulter disponibilité, demander/confirmer/annuler réservation. Contributions : soumettre, réviser, demander publication. Fournisseurs : configurer politique, lire consommation ; secrets ne sont jamais retournés.

Les changements d'activation ou publication sont des commandes explicites. Le client ne peut pas PATCH une propriété `clinically_validated=true`.

## Événements

Enveloppe : event_id UUID, event_type namespacé/versionné, tenant_id, occurred_at, aggregate_type/id/revision, correlation_id, causation_id, classification, payload_ref/digest, producer. Types initiaux : `medikristal.observation.recorded.v1`, `.observation.amended.v1`, `.evaluation.completed.v1`, `.proposal.superseded.v1`, `.booking.updated.v1`, `.knowledge.published.v1`, `.knowledge.revoked.v1`, `.contribution.updated.v1`.

Transport interne at-least-once ; inbox déduplique event_id et vérifie digest. Ordre garanti seulement par aggregate_revision et consommateur ; gérer trous et événements hors ordre par attente/relecture propriétaire. Pas de données patient dans les événements de connaissances publics. Dead-letter avec raison et reprise auditée. Les webhooks sont authentifiés, signés, horodatés et protégés contre rejeu ; bloquer destinations non autorisées et SSRF.

## Ports d'adaptateurs

| Port | Méthodes minimales | Sortie |
|---|---|---|
| TerminologyPort | lookup, expand, translate, validate_code | Résultats versionnés, ambiguïtés, provenance |
| EvidencePort | fetch_snapshot, list_versions | Snapshot et droits |
| InferencePort | validate_model, evaluate, explain | Résultats typés et trace |
| ProtocolPort | validate, evaluate | Étapes admissibles, inconnus, propositions |
| PlanningPort | compare_strategies, allocate | Faisabilité, hypothèses, objectifs et limites |
| FacilityPort | list_capabilities, availability, hold, confirm, cancel, reconcile | Reçu et état propriétaire |
| ResultsPort | ingest, acknowledge, reconcile | Résultat normalisé ou quarantaine |
| PublicationPort | export, verify, submit, receipt | Référence d'artefact et statut |
| ProviderPort | estimate_cost, invoke, reconcile_usage | Résultat et consommation |

Tous prennent un contexte non clinique : principal/grant, tenant, correlation, deadline, versions et classification. Pas de secrets dans objets de domaine. Les appels fonctionnels utilisent DTO typés ; un port ne retourne pas du texte à parser librement comme preuve d'exécution.

## Contrat d'un modèle externe

Requête = modèle/digest, CaseSnapshot minimisé, features, evaluation_time et paramètres de reproductibilité. Réponse = applicability, hypotheses, missing_inputs, warnings, model_version, engine_version, evidence_refs et trace. La validation serveur rejette une probabilité sans provenance ou un modèle non demandé. Un fournisseur ne choisit pas silencieusement un autre modèle.

## Compatibilité

Ajout compatible : champ optionnel avec comportement défini ; changement d'enum, sens, unité, obligation ou permission = revue de compatibilité. Les consommateurs doivent refuser un statut inconnu pour une action exécutable et peuvent l'afficher en lecture seule. Ne pas ignorer silencieusement des fields critiques. Version de schéma, version de modèle et version de contenu sont indépendantes.

## Précisions du contrat 0.2

Les nouvelles opérations et événements sont définis au [chapitre 30](30-operational-contracts.md). Un `If-Match` sur une route de création imbriquée dans un cas vise la révision du cas. Pour une transition workflow, il vise le workflow et le corps fournit aussi `case_revision` à contrôler. Pour révision d’un catalogue, plan de soins ou tâche, il vise cet objet. Toute commande basée sur un cas même sans en-tête doit contrôler transactionnellement le `case_revision` du corps quand celui-ci existe.

Les mutations d’objets retournent l’ETag de la ressource renvoyée ; la réception de résultats retourne la révision du cas dans le reçu. Le client peut relire le cas pour obtenir son ETag. Les listes de connaissances acceptent des filtres documentés ; un code qualifié est `system|code`, avec encodage HTTP normal de sa valeur.

Les noms courts d’événements des chapitres 26–33 sont des noms logiques. Le nom transport est `medikristal.<nom>.v1`. `knowledge.published` et `knowledge.revoked` restent les noms canoniques ; les révocations de release du chapitre 30 emploient donc `knowledge.revoked`. Les droits des consommateurs restent vérifiés lors de la résolution des références.
