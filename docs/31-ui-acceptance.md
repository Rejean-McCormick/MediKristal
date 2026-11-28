# 31 — Contrats des interfaces et états visibles

## Règles communes

Les interfaces lisent les capacités réelles du serveur. Une fonction non installée, un corpus non applicable ou un droit absent produit une explication adaptée ; aucun écran ne fabrique des résultats. Les mutations montrent `sending`, `accepted_pending`, `confirmed`, `failed` ou `reconciling` selon leur vrai état. Recharger la page retrouve l’état durable.

Un conflit de révision présente les modifications concurrentes et propose de recharger/réexaminer. Il ne renvoie pas automatiquement la commande avec la nouvelle révision. Les valeurs originales et converties restent consultables. Les états `unknown`, `absent`, `not_assessed` et `not_estimable` ont des libellés distincts.

## Matrice écran/action

| Écran | Lecture | Commande | Critère de réception |
| --- | --- | --- | --- |
| Accueil patient | Capacités et cas autorisés | Créer cas | Aucune identité d’un autre patient exposée |
| Recueil | Observations et manquants | Ajouter/amender | « Je ne sais pas » ne devient pas non |
| Hypothèses | Évaluation et trace | Demander évaluation | Scores et probabilités distincts ; statut périmé visible |
| Prochaines actions | Propositions et plan | Accepter/refuser | Acceptation distincte de commande envoyée |
| Résultats | Observations/rapports | Import autorisé | Quarantaine, correction et date clinique visibles |
| Parcours professionnel | Workflows et ordres | Démarrer/pause/reprise | Habilitation serveur et garde de révision |
| Traitements/suivi | Options, plans et tâches | Planifier/attribuer/terminer | Aucune dispensation implicite |
| Catalogue administratif | Sites, ressources, actes | Créer/réviser | Diff et impact sur réservations avant retrait |
| Coûts | Devis et validité | Créer nouvelle version | Devise/perspective/nature obligatoires |
| Disponibilité | Snapshots et réservations | Saisie/annulation | Âge de la source et propriétaire affichés |
| Atelier scientifique | Sources, preuves, contributions | Soumettre/réviser | Aucun bouton ne contourne la publication admissible |
| Exploitation | Jobs, erreurs et suivi | Reprise permise | Réconciliation avant renvoi d’un ordre ambigu |

## Cas particuliers

Patient sans compte institutionnel : espace personnel pseudonyme selon politique locale ; il n’accède pas au calendrier interne complet ni aux cas d’autres patients. Les contraintes de mobilité et préférences peuvent influencer les propositions sans changer l’urgence clinique.

Professionnel sur poste partagé : la sélection du cas et l’identité de session sont toujours visibles. Une expiration de session préserve les commandes déjà acceptées sur le serveur mais ne confirme pas un brouillon local. Un changement de patient vide les données en mémoire de l’écran précédent.

Hors ligne : afficher date du corpus et capacités indisponibles. Pour le premier déploiement, « hors ligne » signifie serveur local sans WAN ; ce n’est pas une promesse de réplication multi-appareils ou de commandes institutionnelles conservées indéfiniment dans un navigateur. Une PWA avec synchronisation clinique exige un lot distinct et une politique de conflits.

## Accessibilité et langue

Tester clavier, lecteur d’écran, zoom, état de focus après erreur et messages non dépendants de la couleur. Français et anglais partagent codes canoniques ; les textes cliniques traduits indiquent leur version et validation. Les unités changent d’affichage sans altérer la valeur d’origine ni la précision.

## Critères transversaux

Pas de secret ni PHI dans URL, télémétrie navigateur ou capture d’erreur. Les téléchargements sont autorisés et audités. Les notifications externes ne contiennent pas de résultat clinique par défaut ; leur message renvoie vers une consultation authentifiée. Les détails techniques (digest, solveur) restent dans la vue d’explication professionnelle/administrative.

## Fiche de cas professionnelle

**Parcours dominant** · ouvrir un cas autorisé → comprendre ce qui a changé → consigner ou corriger → examiner la dernière évaluation applicable → suivre une action et son résultat. Le cas est la destination stable. Les sections partagent le contexte et les permissions du cas sélectionné.

| Surface | Contenu prioritaire | Action dans le contexte |
| --- | --- | --- |
| Liste de cas autorisés | États utiles au rôle, dernière mise à jour et éléments nécessitant une reprise | Ouvrir le cas |
| En-tête du cas | Identité minimale, révision, contexte de session et alertes de fraîcheur | Actualiser la fiche pour examiner un conflit |
| Observations et résultats | Valeur, provenance, date pertinente, correction et résultat attendu | Consigner ou corriger avec les gardes serveur |
| Évaluation | Dernière évaluation, statut de couverture, versions et état périmé | Demander une nouvelle évaluation autorisée |
| Actions et suivi | Proposition, opération, état de réservation, reçu et tâche assignée | Ouvrir le détail ou vérifier l’état de l’opération existante |

Les détails de preuve s’ouvrent dans le même contexte. L’espace scientifique s’organise autour de la source, de la contribution ou de la release. Les réglages globaux et l’exploitation ont leur destination dédiée. Vue patient, professionnelle et administrative partagent la signification des états et exposent les seules données autorisées.

### États à projeter

L’interface récupère l’état métier auprès de l’objet propriétaire. Pour une réservation, l’`Operation` décrit la commande et le `Booking` porte l’état de la réservation. Pour une évaluation le cas reste la source du contexte et la validité est liée aux révisions.

| Signal observable | Affichage et action suivante |
| --- | --- |
| Requête en cours d’envoi | Envoyer une fois. En cas de perte de réponse, chercher l’opération existante lorsque sa référence est connue. Conserver la même clé pour un rejeu contractuellement sûr. |
| HTTP 202 avec opération durable | Afficher que la demande est enregistrée, puis lire son état. Le statut HTTP ne définit pas l’issue de la réservation. |
| Réservation `held` ou `confirm_requested` | Afficher maintien local ou confirmation demandée selon le cas. Donner la prochaine action permise. |
| `reconciling` ou état ancien | Afficher « Confirmation inconnue » avec date ou dernière observation. « Vérifier l’état » relit l’opération ou la réservation existante. Une réconciliation mutative, si ajoutée au contrat, suit son autorisation propre. |
| `confirmed`, `cancelled`, `expired` ou `rejected` | Afficher l’état confirmé par la source de référence et les actions permises. |
| Correction ou conflit | Signaler l’évaluation périmée ou la révision en conflit. Proposer une relecture avant toute nouvelle commande. |
| Accès indisponible ou session expirée | Masquer les données de la session précédente, demander de reprendre la session et revalider les droits avant la lecture. |

### Vérification de la reprise

Avec un cas synthétique, atteindre l’état `reconciling`, quitter la fiche puis revenir depuis la liste. Vérifier la persistance du cas, de la révision et de l’identifiant d’opération. L’action « Vérifier l’état » ne recrée aucune demande. Corriger ensuite une observation, vérifier l’ancienne évaluation devenue périmée et lancer une nouvelle évaluation autorisée. Rejouer le scénario avec une autre session, un autre tenant, le clavier seul et un réseau interrompu. Voir [MK-SF-03 et MK-SF-04](BACKLOG_SYSTEME_FINAL.md).
