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
