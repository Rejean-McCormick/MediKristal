# Patterns retenus pour MediKristal

Les numéros renvoient aux guides joints « Senior Architecture Patterns » et « Senior Interface UX Patterns ». Leur application au dépôt suit les décisions du [chapitre 20](20-decisions.md) et les tickets du [backlog](BACKLOG_SYSTEME_FINAL.md).

| Pattern | Décision de conception | Preuve attendue |
| --- | --- | --- |
| 31 · Monolithe modulaire | Une version applicative, une base transactionnelle, un processus API et un worker issus du même code. Propriété explicite des mutations de cas, savoir et ressources. Extraire une règle de route lorsqu’un ticket a besoin de la tester ou de la réutiliser. | Contrats HTTP et tests métier préservés. Une révision d’un module traverse ses entrées publiques. |
| 10 · Ports et adaptateurs | Réutiliser les ports existants pour les dépendances avec un comportement alternatif réel. Le noyau reçoit ses types métier. | Même suite de contrat sur adaptateur synthétique et adaptateur cible lorsque disponible. |
| 08 · Couche de traduction | Mapping FHIR/Kristal indépendant de l’API interne, versions et empreintes épinglées. Conserver original ou référence intègre, pertes et provenance. Bloquer les pertes critiques. | Tests de mapping, version inconnue, résultat ambigu, perte, absence de données individuelles dans l’export de savoir. |
| 15 et 16 · Idempotence et outbox | Mutation et événement dans une transaction. Rejeu déterministe sur même clé et contenu. Consommation locale dédupliquée. Pour un effet distant, commande durable et reçu du propriétaire. | Commit puis crash, consommation concurrente, répétition de clé avec autre contenu, réponse distante perdue. |
| 04 et 06 · Dégradation et budgets de temps | Une panne de connecteur laisse le corpus local admissible consultable. La requête interactive et l’opération durable ont chacune leur budget technique. Après un délai dépassé, l’effet externe peut rester inconnu. | Essai hors WAN, connecteur indisponible, délai dépassé, lecture et réconciliation de l’opération existante. |
| 01, 02, 03 et 05 · Protection des connecteurs | Au premier connecteur réseau réel, définir par fournisseur délai, limites de concurrence et débit, erreurs éligibles au retry, plafond d’essais et circuit breaker si les défaillances le justifient. Un retry d’écriture dépend de la preuve d’idempotence ou de l’état autoritatif. | Une panne ou saturation de fournisseur préserve les opérations locales. La charge et les délais restent bornés. |
| 27 et 29 · Santé et mesure | Vérifier séparément processus, dépendances nécessaires et capacités métier. Mesurer latence, erreurs, âge de file et réconciliations sans données individuelles. | Campagne du [profil de qualification](PROFIL_QUALIFICATION.md). |

### Cohérence et reprise

Le worker actuel consomme les événements locaux avec inbox et verrouillage. Son gestionnaire d’événements local est un point d’extension. L’envoi partenaire demande un flux durable distinct de la consommation locale. Persister l’intention avant l’envoi, joindre un identifiant stable au partenaire quand il le supporte et enregistrer l’issue avec le reçu de référence. Après crash ou timeout entre envoi et enregistrement du reçu, rechercher l’effet par cet identifiant. Garder l’état et les claims selon la politique tant que l’issue est ambiguë. Si le partenaire ne permet aucune vérification, rendre la résolution opérateur explicite. Une annulation confirmée dépend du propriétaire de la réservation.

Une saga est pertinente lorsqu’un parcours doit coordonner plusieurs autorités et que chaque compensation a un contrat réel. Les révisions append-only du dépôt assurent l’historique et le replay ciblé. Les projections relationnelles sont une option de lecture si les mesures le justifient. Event Sourcing, CQRS avec stockage distinct et sharding restent des décisions conditionnelles à passer par une ADR et une mesure.

### Organisation de l’interface

Les patterns UX-05, 07, 09, 11, 15 et 17 placent le cas au centre du travail professionnel, séparent l’administration des ressources et conservent le contexte à la reprise. Appliquer UX-12 aux détails de provenance et UX-14 à la validation par scénario. Les critères concrets figurent au [chapitre 31](31-ui-acceptance.md).
