# 09 — Ressources, coûts et ordonnancement

## Capacités plutôt que machines seules

Une capacité = acte + site + équipement compatible + personnel/compétences + consommables + conditions patient + intervalle. Une IRM disponible sans équipe ou sans protocole approprié n'est pas une capacité exploitable. Une analyse requiert prélèvement, tube/volume, chaîne de transport, automate/réactif, validation et transmission. Réserver toutes les ressources requises ou déclarer la demande non confirmée.

L'administrateur configure inventaire, horaires, maintenance, indisponibilités, durée de préparation/examen/nettoyage, capacités parallèles et coûts. Il ne fixe pas seul les indications ou priorités cliniques. Les droits `resource_admin` et `clinical_policy_approver` sont distincts.

## Disponibilité

Chaque snapshot comprend propriétaire, méthode (saisie/import/API), instant d'observation, validité et confiance opérationnelle. Un slot est `free`, `held`, `booked`, `unavailable` ou `unknown`. La date de réception d'une copie ne rafraîchit pas la date de source. Un patient accepte les contraintes de déplacement et préférences ; ne pas optimiser en supposant une mobilité inexistante.

## Ordonnancement

Entrées : demandes cliniquement admissibles, fenêtres acceptables référencées, durée, précédences, ressources alternatives, compétences, disponibilité, localisation, préparation et préférences. Contraintes impératives : compatibilité, absence de collision, exclusions patient, délais cliniques autorisés, interdépendances et droits. Les priorités viennent d'une politique clinique admissible. Aucun score de réputation, de paiement ou de participation Konnaxion ne fixe l'urgence.

Objectif par défaut conceptuel : satisfaire contraintes impératives ; minimiser violations autorisées explicitement dans un scénario d'analyse ; comparer délais, déplacement, coût et utilisation selon politique. Toute relaxation est visible, et une solution violant une contrainte non relaxable est rejetée. Le système ne doit jamais masquer une impossibilité sous un créneau « optimal ».

Le planificateur individuel propose des parcours ; le planificateur collectif attribue la capacité. Les substitutions d'examens doivent être admises médicalement avant l'optimisation. OR-Tools peut résoudre l'affectation, mais n'apporte pas les règles médicales.

## Coûts et budgets

Chaque prix indique devise, nature, perspective et date. Maintenir les montants des composants pour éviter le double comptage. Coût nul doit être déclaré explicitement ; coût manquant = unknown. Pas de conversion de devise implicite ; une table de change versionnée est nécessaire si comparaison autorisée. Le budget fournisseur payant appartient au module intégrations, distinct du coût d'un examen clinique.

Présenter une analyse de sensibilité lorsque plusieurs coûts/délais sont incertains. Un changement mineur de prix ne doit pas faire disparaître une contrainte clinique. Le résultat du plan inclut hypothèses de coût, disponibilité, objectifs, faisabilité, bound/gap si fourni par solveur et durée de calcul.

## Réservation : machine d'état

`proposed → hold_requested → held → confirm_requested → confirmed`. Branches : held→expired/cancel_requested ; confirmed→cancel_requested→cancelled ; demande→rejected ; réponse ambiguë→reconciling. `confirmed` exige un reçu du propriétaire. Un hold est un bail avec expiration, pas une réservation définitive. Si le fournisseur ne possède pas de hold, documenter une opération atomique de réservation sans simuler held.

La commande porte un identifiant d'idempotence stable et le digest de la demande. Les essais répétés identiques retournent le même résultat. Une clé réutilisée avec un payload divergent produit `idempotency_conflict`. Timeout après envoi : rechercher la réservation par identifiant client avant tout nouvel envoi. Pas de double réservation pour contourner une réponse inconnue.

Réservations locales : transaction et contrainte SQL sur chevauchement. Réservations externes : le système externe tranche les collisions, MediKristal reflète son reçu. Une annulation locale avant confirmation de l'annulation distante demeure `cancel_requested`.

## Replanification

Maintenance, personnel absent ou résultat modifiant l'indication déclenchent impact et propositions alternatives. Préserver le créneau existant jusqu'à sécurisation de la substitution quand la politique le prévoit. Ne pas déplacer silencieusement un patient déjà informé. Notification, acceptation nécessaire et raison font partie de l'opération.

## Équité

Auditer attentes, refus et reports par catégories pertinentes, avec données minimisées et gouvernance. Pas d'optimisation du taux d'utilisation au détriment des fenêtres de sécurité ou de l'accessibilité. Les limites de données doivent être visibles ; un catalogue partiel d'établissements n'est pas une vue exhaustive du Québec.

## Tests de concurrence obligatoires

Deux demandes simultanées pour un seul slot ; hold expirant à la confirmation ; timeout après création distante ; annulation reçue avant confirmation ; horloge différente ; panne entre commit et outbox ; replanification d'une ressource partagée ; devis expiré ; coût inconnu. Ces tests précèdent toute revendication de réservation fiable.
