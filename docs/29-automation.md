# 29 — Automatisation autorisée du parcours

## Finalité

Automatiser les tâches prévisibles du parcours, y compris avant consultation lorsque le contexte l’autorise : collecte, recherche de résultats existants, vérification de complétude, propositions et actes couverts par un protocole. Le niveau d’automatisation dépend d’une politique admissible, pas du seul rôle utilisateur ni d’une probabilité élevée.

## Exécution durable

`WorkflowRun` lie cas/révision, protocole, politique d’autorisation, acteur initiateur, niveau d’usage et état. `WorkflowTransition` demande une action explicite avec raison et révision attendue. L’historique des étapes est append-only ; chaque étape conserve ses dépendances, sa clé d’exécution et son reçu éventuel.

| État | Événement/commande | Condition | État suivant |
| --- | --- | --- | --- |
| ready | start | Corpus et préconditions valides | running |
| running | Donnée requise absente | Aucune action exécutable sans elle | waiting_input |
| waiting_input | Observation admissible | Révision contrôlée, modèle encore admissible | running |
| running | Décision humaine nécessaire | Pas de délégation applicable | waiting_review |
| waiting_review | resume | Acteur habilité et validation récente | running |
| running | Demande transmise | Commande autorisée et persistée | waiting_external |
| waiting_external | Reçu/résultat reconnu | Correspondance et version vérifiées | running |
| waiting_external | Réponse ambiguë | État externe non confirmé | reconciling |
| reconciling | État retrouvé | Même identifiant de commande | running ou waiting_external |
| Tout état actif | pause ou dépendance retirée | Motif conservé | paused |
| paused | resume | Tous les guards réévalués | running |
| État actif | cancel | Aucun acte irréversible simulé annulé | cancelled |
| running | Critère d’arrêt satisfait | Tâches résiduelles affectées | completed |
| État actif | Défaillance non récupérable | Incident et propriétaire définis | failed |

Une annulation du workflow n’annule pas automatiquement un ordre externe. Créer les commandes d’annulation nécessaires, les suivre et montrer les actes déjà exécutés. `completed` peut coexister avec des tâches de suivi attribuées ; la clôture du cas applique les règles propres du chapitre 04.

## Guards avant chaque action

Vérifier identité/rattachement du cas, niveau d’usage, protocole et politique admissibles, périmètre de l’acte, compétence/délégation, révision courante, fraîcheur des données, exclusions, consentement lorsque requis, disponibilité et destination. Un résultat inconnu de garde bloque l’exécution et indique l’information attendue. Ne pas lancer d’appel externe depuis un calcul de garde.

Le mode `proposal_only` peut construire le parcours et demander une validation. Le mode `protocol_authorized` peut transmettre les seules commandes déléguées. Le registre d’autorisation identifie l’approbateur, le périmètre, la validité et la révocation. La configuration initiale ne contient aucune délégation clinique.

## Idempotence et concurrence

Clé interne d’étape : `(workflow_id, step_id, activation_number)` ; une boucle crée une activation nouvelle seulement si la condition de progression est satisfaite. Relance après panne conserve l’activation. Transaction locale : vérifier révision, persister l’état et écrire l’outbox. Le worker externe possède sa clé de commande stable et réconcilie les réponses perdues.

Un événement résultat peut arriver avant le reçu d’ordre : conserver la référence externe, tenter la corrélation et mettre en attente les liens incomplets. Deux workers ne passent pas simultanément la même étape grâce au contrôle de révision et au verrou transactionnel. Une correction de résultat invalide les étapes dépendantes, pas l’historique des actes déjà réalisés.

## Responsabilités et escalades

Chaque blocage possède propriétaire, motif, instant et prochaine action. Les délais d’escalade viennent d’une politique versionnée. L’absence d’une telle politique interdit d’affirmer que la surveillance clinique est assurée ; l’interface affiche l’absence de prise en charge. Un acquittement confirme la réception du message, pas la résolution de la situation.

Le patient peut renseigner, corriger, demander une explication et exprimer ses préférences. Les commandes institutionnelles restent sous droits spécifiques. Un infirmier utilise les actions correspondant aux habilitations configurées ; aucune profession ne reçoit automatiquement tous les droits.

## Tests

AT-027, AT-028, AT-031 : redémarrage après commit, doublon d’événement, modèle retiré entre proposition et commande, résultat corrigé pendant validation, ordre en vol lors d’annulation, réception précoce d’un résultat et reprise par un autre acteur. Tester les refus côté serveur, pas seulement les boutons masqués.
