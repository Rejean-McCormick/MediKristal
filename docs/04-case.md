# 04 — Cycle du cas et observations

## Machine d'état du cas

États : `draft`, `active`, `waiting`, `closed`, `cancelled`. Transitions autorisées : draft→active/cancelled ; active→waiting/closed/cancelled ; waiting→active/closed/cancelled ; closed→active via commande de réouverture motivée ; cancelled terminal. Toute transition exige permission et révision attendue. L'état d'un ordre ou d'un diagnostic reste indépendant.

## Ingestion

1. Authentifier source et principal ; établir le tenant côté serveur.
2. Valider structure, identité du sujet, lien au cas et droits.
3. Rechercher doublon source/identifiant/version. Un doublon identique retourne l'objet existant ; un contenu divergent au même identifiant produit conflit.
4. Préserver données brutes dans un stockage protégé, puis normaliser selon versions épinglées.
5. Vérifier unités et temporalité. Un résultat ambigu est stockable en quarantaine mais inutilisable pour inférence automatique.
6. Créer la version d'observation, incrémenter le cas et écrire outbox atomiquement.
7. Marquer les évaluations dépendantes comme périmées ; programmer une réévaluation selon politique.

Les informations textuelles extraites par IA restent `proposed` jusqu'à vérification nécessaire. Elles ne remplacent pas un résultat instrumenté. « Pas de mention d'allergie » n'est pas « absence d'allergie ». Une absence de réponse ne déclenche pas une valeur clinique par défaut.

## Temporalité

Chaque feature a une politique de sélection : dernière valeur admissible, maximum dans une fenêtre, tendance, valeur avant intervention, ou ensemble. Cette politique appartient au modèle versionné. La valeur la plus récente n'est pas toujours pertinente. Un résultat post-traitement ne peut pas servir de prédicteur prétraitement dans une évaluation rétrospective sans déclaration. Fixer l'instant d'évaluation au lieu de laisser chaque règle appeler l'horloge système.

Conserver dates partielles, approximations et contradictions ; ne pas fabriquer une heure. Les fuseaux et changements d'heure sont testés dans les plannings. Un dispositif dont l'horloge est incertaine marque ses observations.

## Correction et conflit

Une observation a statut `preliminary`, `final`, `amended`, `entered_in_error` ou `proposed`. La version remplacée reste référencée. `entered_in_error` est exclu des nouveaux snapshots ; les traces historiques indiquent qu'elles reposaient sur une donnée retirée. Si deux sources se contredisent, ne pas écraser par date de réception : présenter conflit, appliquer une règle de résolution déclarée ou s'abstenir.

Une fusion d'identités patient est un processus autorisé distinct : garder les anciennes références et revérifier les liens ; pas de fusion probabiliste automatique de dossiers. Un résultat sans correspondance patient certaine est mis en quarantaine.

## Évaluation atomique

L'évaluation capture `case_revision`, `knowledge_release_id`, contexte temporel, politiques, modèles et features normalisées. Si le cas change pendant le calcul, le résultat reste consultable mais porte `stale=true` ; aucune commande d'action fondée sur cette évaluation ne peut s'exécuter sans revalidation. Le worker ne réécrit pas l'historique pour s'aligner sur le nouveau cas.

## Circuit résultats et suivi

Les résultats peuvent être partiels, corrigés ou disponibles par analyte. Le rapport groupé ne bloque pas l'ingestion d'un élément exploitable. Chaque résultat critique identifié par un protocole admis produit une tâche/notification durable avec acquittement, propriétaire et politique d'escalade. Le délai et le destinataire d'escalade sont configurés cliniquement ; ce dossier ne les invente pas. Aucun résultat attendu ne disparaît à la clôture : il reste dans une file de suivi ou la clôture est bloquée selon politique.

## Révision humaine

Une décision humaine ne remplace pas silencieusement la prédiction du modèle. Conserver résultat calculé et décision séparément. Un désaccord est enregistré avec raison structurée et commentaire. Il peut alimenter une proposition de recherche par export autorisé, jamais un apprentissage clinique immédiat.

## Sorties minimales

Le dossier expose chronologie, observations actives/corrigées, informations manquantes, couverture, évaluations datées, actions proposées et décisions. L'utilisateur peut inspecter pourquoi une hypothèse est proposée. Pour le patient, traduire les termes sans supprimer les limites ou fabriquer un diagnostic confirmé.
