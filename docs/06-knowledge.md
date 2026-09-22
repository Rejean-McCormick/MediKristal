# 06 — Connaissances, preuves et publications

## Architecture sémantique

La couche de liaison porte concepts, correspondances et assertions typées. Elle est sémantique par ses significations explicites, indépendamment du stockage SQL, RDF ou graphe. Elle respecte les terminologies médicales plutôt que de tout réduire à des identifiants maison.

Séparer quatre statuts : intégrité de l'artefact, état de révision, force/incertitude de la preuve, autorisation d'utilisation dans un contexte. Une signature prouve un émetteur/intégrité, pas une vérité clinique. Une fréquence de manifestation n'est pas une recommandation de test. Un protocole institutionnel peut être pertinent dans son établissement sans reconnaissance universelle.

## Preuve quantitative

Une fiche indique la question, population, inclusion/exclusion, setting, prévalence ou recrutement, méthode, test index, standard de référence, seuil, fenêtre temporelle, nombres, estimateur, intervalle, biais, financement/conflits documentés, source et extraction. Une valeur extraite automatiquement est une proposition. Les tableaux 2×2 TP/FP/FN/TN sont conservés lorsqu'ils existent ; les estimations dérivées enregistrent la formule.

Ne pas moyenner arbitrairement deux études. Les synthèses sont des objets distincts avec méthode, sélection et dépendances. Détecter publications reposant sur une même cohorte pour éviter le double comptage. Préserver désaccords et hétérogénéité ; le modèle choisit ses paramètres selon un protocole explicite.

## Release de connaissances

États `draft → reviewing → candidate → published → deprecated/revoked`. `reviewing → draft` si correction ; `candidate → reviewing` si défaut ; révocation terminale pour l'identité publiée, une version corrigée crée une nouvelle identité. Une publication technique peut être `engineering_only` ; published ne signifie pas clinique.

Le manifeste contient : identifiant, version, schema_version, liste des fichiers avec tailles/hashes, concepts/associations, modèles, protocoles, versions des sources, mapping versions, preuves et rapports de qualification, limitations, droits, minimum runtime, signature et dépendances. Les exécutables/plugins ne sont pas acceptés comme simples données : ils exigent une filière logicielle distincte, revue et sandbox.

## Construction et identité

La release MediKristal est `medikristal.knowledge-release/1`, distincte d'un Runtime Pack Kristal. Son identité est SHA-256 sur un manifeste canonique JCS dont sont exclus `release_id`, `signatures` et `built_at`; les fichiers sont référencés par leurs hashes, pas chargés dans la cible de hash. Chemins relatifs normalisés POSIX, sans traversée, tri lexicographique ; identifiants, tableau des fichiers et métadonnées déterministes. Pas de normalisation Unicode implicite pour une canonicalisation Kristal. Les versions originales et transformations sont conservées.

Adopter une implémentation JCS éprouvée ; le script documentaire joint ne prétend pas implémenter JCS. Tout export Kristal utilise le profil natif et les vectors du framework, jamais ce profil MediKristal substitué silencieusement.

## Admission et activation

Vérifier hash/signature, confiance de la clé, compatibilité, droits, couverture, qualification requise et politique locale. Installer en staging, vérifier tous les fichiers, puis basculer atomiquement le pointeur local. Les évaluations actives gardent leur ancienne référence. Un rollback produit un reçu et respecte révocations ; il ne peut pas réactiver un contenu retiré sans politique explicite autorisant un usage archivistique isolé.

Offline : vérifier la liste de révocation locale, son âge et la politique de fraîcheur. Ne pas promettre de connaître une révocation survenue sans réseau. Chaque sortie affiche l'état de fraîcheur lorsqu'il affecte son utilisation. Politique possible : consultation historique permise mais nouvelles actions exécutables bloquées après expiration ; le délai est une décision du déploiement, pas inventé ici.

## Graphe d'impact

Maintenir les dépendances Source→Mapping/Assertion→Model/Protocol→Release→Evaluation→Proposal. Changement ou retrait d'une source produit une liste d'impacts. Les cas historiques restent consultables ; les cas actifs concernés peuvent recevoir une tâche de réévaluation. Ne pas republier automatiquement une révision sans contrôles.

## Consultation

API de recherche par concept, assertion, population, juridiction, source, version et statut. Les lecteurs peuvent sélectionner corpus recherche ou admis ; le moteur clinique applique la politique serveur et ne se laisse pas déverrouiller par un filtre UI. Chaque élément expose provenance, limites et version.
