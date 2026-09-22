# 22 — Scénarios de bout en bout

## S1 — Parcours autonome synthétique

Créer tenant engineering, utilisateur autorisé et cas synthétique. Installer une release synthétique valide. Ajouter symptôme SYN-S1, contexte fictif et test SYN-T1 du modèle binaire du chapitre 07. Demander évaluation à la révision exacte ; obtenir posterior 0,4705882353 après positif. L'explication montre prior, paramètre, source synthétique et limites. Le patient fictif reçoit une proposition explicative ; aucune prescription réelle n'est possible. Export de la connaissance synthétique autorisé ; export du cas par le canal de corpus refusé.

## S2 — Coût et disponibilité

Deux stratégies fictives admises en engineering. A : résultat plus rapide, coût supérieur ; B : coût inférieur et délai plus long. Fournir coût dans même devise/perspective, contraintes de temps explicites. Le plan compare et expose hypothèses. Modifier le coût : l'ordre de préférence peut changer, les probabilités diagnostiques restent identiques. Supprimer coût B : comparer avec incertitude, jamais assimiler B à gratuit. Supprimer toutes ressources admissibles : infeasible et orientation vers résolution humaine, pas réservation fictive.

## S3 — Résultat corrigé

Évaluation E1 sur case_revision=4. Un résultat est amendé, cas passe à 5. E1 reste consultable et stale ; ses propositions sont superseded. Une commande fondée sur E1 est refusée. E2 sur révision 5 utilise la nouvelle version et explique la différence. Un import tardif de l'ancien résultat ne remplace pas l'amendement.

## S4 — Réservation ambiguë

Envoyer clé K au simulateur de réservation ; il crée le booking mais la réponse expire. Operation devient reconciling. Le worker recherche K et récupère le reçu ; exactement une réservation est créée. Un deuxième POST avec K et payload différent retourne 409. Si aucun lookup/idempotence fiable n'existe chez le fournisseur, maintenir uncertain et demander résolution plutôt que répéter.

## S5 — Mode gratuit / payant

Provider P désactivé en online_free ; toute tentative payante est refusée sans appel. En online_extended, enveloppe budgétaire autorisée, réservation atomique avant appel. Deux appels concurrents ne peuvent consommer une même enveloppe au-delà du plafond. P indisponible : capacité dégradée, données locales gardées, aucune substitution silencieuse vers un autre fournisseur.

## S6 — Contribution scientifique

Une proposition modifie un paramètre du modèle synthétique pour une population différente. Comparer modèles sur fixtures, conserver deux populations, accepter la revue mais ne pas activer. Construire release candidate ; vérifier droits et dépendances ; publier engineering_only ; activer localement. Les évaluations historiques utilisent toujours leur ancien modèle. Une proposition avec faux label clinique sans preuves est rejetée.

## S7 — Patient / professionnel

Le patient peut saisir son symptôme et voir les limites. Il tente l'API orders directement : refus même si bouton caché contourné. Un professionnel habilité utilise une politique autorisée mais le cas a changé : refus stale. Après réévaluation et droits vérifiés, demande à un connecteur de test ; état accepted distinct de performed.

## S8 — Révocation hors ligne

Release R admise avec liste de révocation connue. Couper réseau ; une nouvelle révocation existe ailleurs mais n'est pas connue localement. Le système affiche date connue et applique politique locale de fraîcheur sans prétendre « aucune révocation mondiale ». À reconnexion, nouvelle liste retire R ; bloquer nouveaux usages concernés et lister cas actifs à réviser.

## S9 — Échec partiel d'analyse groupée

Un panel produit deux analytes finaux, un préliminaire et un échantillon rejeté. Conserver état par composant. Ne pas marquer tout panel normal ou complet. Le protocole utilise seulement les entrées autorisées ; les données manquantes apparaissent. L'ordonnance de répétition éventuelle reste une proposition nécessitant ses contrôles.

## S10 — Modèle inconnu et monde incomplet

Symptômes hors couverture ; le moteur trouve des associations mais pas de modèle valide. Résultat qualitative/not_estimable, aucune normalisation forcée des candidats à 100 %. Le système peut expliquer la couverture et demander une évaluation adaptée. Il ne conclut pas que les maladies absentes de la base sont exclues.
