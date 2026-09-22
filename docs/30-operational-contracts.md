# 30 — Contrats opérationnels complémentaires

## Autorité et version

Les définitions JSON et OpenAPI dans [contracts](../contracts/README.md) sont générées depuis les scripts du dossier `tools/`. La version 0.2.0 ajoute les ressources ci-dessous au noyau 0.1.0. Ces contrats sont cibles et ne revendiquent pas de backend existant. Toutes les routes héritent des conventions du chapitre 13 : tenant issu du contexte autorisé, idempotence des commandes, erreurs typées, pagination et contrôle d’accès.

## Ressources ajoutées

| Objet | Propriétaire | Règles persistantes |
| --- | --- | --- |
| Site | resources | Code externe unique par propriétaire et tenant ; fuseau conservé |
| ManagedResource | resources | Site valide ; type explicite ; retrait distinct de suppression |
| ProcedureEntry | knowledge/catalog | Concept versionné, famille, références d’échantillon et artefacts explicatifs |
| WorkflowRun | pathways | Révision du cas, protocole et autorisation figés ; transitions gardées |
| FollowUpTask | treatment/followup | Cas, propriétaire, échéance, raison et lien à l’origine |
| ResultReceipt | cases | Référence externe stable, empreinte et révision du cas obtenue |
| ImportReport | knowledge | Compteurs, problèmes et références du parsing ; aucune activation implicite |
| CarePlan | treatment | Options sélectionnées et suivi, distincts d’une prescription |

Les objets catalogue référencent les artefacts détaillés au lieu de répéter leur texte dans chaque capacité. `ProcedureEntry` fournit une entrée indexable ; la validité clinique vient de ses artefacts, pas de son existence dans le catalogue.

## Commandes et invariants

### Sites, ressources, capacités et actes

Créer, lister, lire et réviser les sites, ressources et actes. Une révision passe par `If-Match`; l’identité de la ressource et son tenant ne changent pas. `retired` empêche les nouvelles utilisations, mais conserve l’historique. Modifier une ressource ou capacité produit une analyse des réservations futures impactées ; ne pas effacer les réservations pour faire réussir la modification.

Les champs administratifs n’ont pas autorité sur les indications cliniques. Références vers politiques/artefacts inconnus : erreur, pas création automatique. Le serveur résout l’ensemble des identifiants et empêche une référence entre tenants.

### Réception d’un lot de résultats

`ResultBatchInput` contient cas et révision attendue, propriétaire externe, identifiant/version du rapport, digest et observations. L’empreinte est vérifiée sur la représentation canonique convenue par le connecteur ; le digest fourni seul n’est pas une preuve. La transaction applique tout le lot ou met tout le lot en quarantaine ; le premier contrat ne permet pas une acceptation partielle silencieuse.

Même clé externe/version et même digest : retourner le reçu antérieur. Même clé et digest divergent : `source_version_conflict`. Nouvelle version corrigeant un résultat : références `replaces_id` requises pour les éléments remplacés ; conserver ceux non modifiés selon le profil de rapport. Vérifier les liens avant commit. Émettre `results.accepted`, incrémenter la révision du cas une fois, marquer les dépendances périmées et déclencher les réévaluations admissibles.

### Plan de soins et suivi

Un `CarePlan` relie options thérapeutiques sélectionnées, tâches de suivi et statut. Il ne contient pas un ordre exécutoire et ne prouve aucune administration. La création vérifie les options et le cas/révision. Une révision clinique du plan produit une nouvelle révision avec raison.

Une tâche de suivi passe `open → assigned → completed` ou `cancelled`; `assigned → open` est autorisé lors d’une réaffectation explicite. `overdue` est calculé à partir de l’échéance et de l’état actif, pas écrit comme un état final. Une tâche ne devient completed qu’avec une preuve ou une raison recevable, jamais parce qu’une notification a été envoyée. Le responsable doit accepter le transfert selon la politique ; tant que ce n’est pas fait, le responsable actuel conserve la charge.

Un résultat tardif peut ouvrir une tâche après clôture d’un cas. La réouverture ou création d’un nouvel épisode suit une politique explicite ; ne jamais perdre le résultat parce que le cas est fermé. Sans propriétaire assignable, créer un incident opérationnel visible, pas une tâche supposée surveillée.

### Contributions et releases

Lister contributions, comparer candidat/version active et retirer une release font partie des parcours. Un rapport de comparaison fournit corpus/version, métriques, différences de comportement et populations, sans prétendre démontrer la supériorité clinique. Retirer une release bloque les nouvelles exécutions concernées et ouvre une analyse des dépendances actives ; l’historique reste lisible.

## Événements de domaine

L’enveloppe commune du chapitre 13 reste obligatoire. `aggregate_revision` croît pour chaque agrégat ; `event_id` permet la déduplication. Payload minimal : références et raisons codées, pas dossiers complets. Les lecteurs résolvent les données via permissions courantes.

| Événement | Déclencheur | Consommateur principal |
| --- | --- | --- |
| catalog.changed | Révision site/ressource/acte/capacité | Analyse d’impact, invalidation cache |
| results.accepted | Lot de résultats committé | Inférence, workflows, suivi |
| workflow.changed | Transition validée | Interface, reprise worker |
| care_plan.changed | Plan créé ou révisé | Suivi, audit |
| followup.changed | Tâche créée/attribuée/close | Notifications, console responsable |
| import.completed | Parsing/normalisation terminé | Révision des connaissances |
| knowledge.revoked | Retrait admis | Invalidation et analyse des cas |

Les extensions n’imposent pas un broker externe : une outbox SQL et des workers suffisent au premier déploiement. Événements consommés au moins une fois ; aucune promesse d’exactly-once à travers les systèmes externes.

## Erreurs complémentaires

`source_version_conflict`, `workflow_transition_forbidden`, `authorization_scope_mismatch`, `followup_owner_missing`, `catalog_reference_in_use`, `unsupported_profile`, `import_schema_mismatch`, `strategy_incomplete`, `optimization_policy_missing`. Mapper respectivement conflits d’état à 409, préconditions de version à 412, données sémantiquement invalides à 422, permission refusée à 403 et capacités absentes à 503 selon le chapitre 24. Un détail sensible n’est pas rendu à un acteur non autorisé.

## Commandes qui restent à spécifier par intégration

La prévisualisation/import de masse des catalogues, le dépôt binaire de fichiers, l’authentification locale détaillée et les accusés de partenaires demandent leurs contrats de transport dans le lot concerné. Leurs invariants sont définis ici ou dans les chapitres propriétaires ; ils ne sont pas revendiqués comme endpoints déjà couverts par OpenAPI. Les profils FHIR du partenaire et corps des artefacts de stratégie/autorisation sont versionnés séparément. Ne pas remplacer ces contrats manquants par une route JSON libre.
