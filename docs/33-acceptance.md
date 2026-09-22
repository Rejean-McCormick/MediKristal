# 33 — Scénarios d’acceptation et preuve de réalisation

Ces scénarios sont des spécifications à implémenter sur l’application. Ils complètent T01–T36 du chapitre 18. Aucun PASS documentaire ne les marque comme exécutés. Les valeurs et cas de test restent synthétiques.

| Test | Exigence | Mise en situation et résultat attendu | Lot |
| --- | --- | --- | --- |
| AT-001 | MK-001 | Installer le corpus synthétique et bloquer le WAN ; exécuter cas→évaluation→proposition. Le parcours aboutit sans appel externe ni kOA. | L0 |
| AT-002 | MK-002 | Changer de profil offline à gratuit connecté puis étendu ; le fournisseur payant reste interdit tant que sa politique et son budget ne l’autorisent pas. | L10 |
| AT-003 | MK-003 | Ouvrir le même cas sous patient, professionnel habilité, chercheur sans grant et admin ressources. Seuls les accès explicitement autorisés sont accordés. | L9 |
| AT-004 | MK-004 | Importer deux versions d’une source ; l’ancienne observation retrouve toujours sa version et son brut, même après activation de la nouvelle release. | L2 |
| AT-005 | MK-005 | Soumettre un mapping plus large ; il reste qualifié comme tel et ne satisfait pas une recherche exigeant une équivalence exacte. | L2 |
| AT-006 | MK-006 | Fournir un score de similarité sans modèle probabiliste ; aucun pourcentage clinique ne sort. Le modèle synthétique binaire donne son oracle documenté. | L3 |
| AT-007 | MK-007 | Corriger un résultat utilisé par un plan ; ancienne version conservée, dépendances périmées et réévaluation créée sans double comptage. | L1 |
| AT-008 | MK-008 | Comparer une question, une surveillance et un test sous un protocole synthétique. L’action n’utilisant pas de machine reste sélectionnable. | L6 |
| AT-009 | MK-009 | Comparer coût nul déclaré et coût absent ; seul le premier vaut zéro. Deux perspectives distinctes ne sont pas additionnées. | L6 |
| AT-010 | MK-010 | Deux demandes tentent le dernier créneau. Une seule confirmation est admise ; timeout après création distante déclenche recherche du reçu, sans double réservation. | L7 |
| AT-011 | MK-011 | Allergie requise inconnue : option needs_information. Créer un plan ne produit aucune prescription ou administration implicite. | L5 |
| AT-012 | MK-012 | Déposer une correction de modèle puis la réviser ; le modèle actif ne change pas avant construction, admission et activation séparées. | L8 |
| AT-013 | MK-013 | Importer puis exporter une fixture du profil partenaire ; l’unité, la date et la version sont conservées ou la perte est déclarée et bloque le profil concerné. | L11 |
| AT-014 | MK-014 | Exporter une connaissance synthétique vers le schéma Kristal épinglé ; vérifier la conformance et l’absence de contenu patient. | L11 |
| AT-015 | MK-015 | Rejouer un UUID connu depuis un autre tenant ; aucun contenu ni existence sensible ne fuit, y compris via listes et messages d’erreur. | L1 |
| AT-016 | MK-016 | Rejouer mêmes entrées, modèles, horloge et seed ; obtenir le même résultat selon la tolérance documentée. Modifier un artefact change son digest. | L3 |
| AT-017 | MK-017 | Deux appels concurrents réservent le dernier budget ; un seul passe. Facturation incertaine conserve la réserve jusqu’à réconciliation. | L10 |
| AT-018 | MK-018 | Retirer le modèle applicable ; afficher non couvert ou insufficient_data, sans probabilité zéro ni affirmation de sécurité. | L3 |
| AT-019 | MK-019 | Une suite de tests logiciels verte ne change jamais le statut clinique. La capacité expose ses preuves et limites réelles. | L12 |
| AT-020 | MK-020 | Remplacer un adaptateur par un autre conforme au port sur fixtures ; le noyau ne dépend pas de ses types internes et la compatibilité est mesurée. | L0 |
| AT-021 | MK-021 | Créer acte et composants de panel distincts ; empêcher un cycle de composition et une substitution non admise. | L2 |
| AT-022 | MK-022 | Changer prix et moyen de paiement en gardant les données cliniques ; probabilité et priorité clinique restent identiques. | L7 |
| AT-023 | MK-023 | Passer en mode payant sous rôle patient ; aucune permission de prescription ou commande institutionnelle supplémentaire. | L10 |
| AT-024 | MK-024 | Révoquer une release en cours d’usage ; bloquer nouvelles exécutions concernées, conserver historique et ouvrir analyse d’impact. | L8 |
| AT-025 | MK-025 | Un client sans interface web récupère connaissance sourcée, évaluation expliquée et suivi autorisé ; les permissions restent propres à chaque niveau. | L11 |
| AT-026 | MK-026 | Sur arbre synthétique B=20 puis A=500 dans 30 % des branches, calculer 170. Une contrainte impérative violée exclut B malgré le prix ; timeout ne donne pas optimal. | L6 |
| AT-027 | MK-027 | Panne après outbox puis reprise : une seule activation d’étape. Révocation de délégation avant envoi empêche la commande. | L4 |
| AT-028 | MK-028 | Recevoir un résultat après clôture ; une tâche durable avec responsabilité est créée ou un incident propriétaire manquant est visible. Notification envoyée ne clôt pas la tâche. | L5 |
| AT-029 | MK-029 | Retirer une machine réservée ; conserver réservation et historique, signaler impact et déclencher replanification autorisée. | L6 |
| AT-030 | MK-030 | Une colonne requise disparaît : import en échec/quarantaine sans modification du corpus actif ; reprendre un fichier valide ne duplique aucune ligne. | L2 |
| AT-031 | MK-031 | Simuler timeout puis recharger l’écran ; montrer reconciling et la commande durable, jamais succès inventé ni renvoi aveugle. | L9 |
| AT-032 | MK-032 | Retirer une référence d’opération ou de test dans la matrice : le contrôle documentaire échoue ; aucune gate logicielle n’est inférée du contrôle documentaire. | L12 |

## Dossier de preuve

Chaque scénario exécuté produit : commit, versions contrats/artefacts, environnement, commande, entrées synthétiques, résultat attendu/réel, verdict et limites. Les tests de concurrence enregistrent l’issue des deux acteurs. Les tests d’accès incluent une assertion d’absence de fuite. Les tests réseau vérifient les appels observés, pas seulement une variable de configuration.

Un scénario échoué ou non exécuté reste FAIL ou NOT_RUN. Il ne devient SKIP acceptable que si la capacité correspondante est explicitement désactivée et annoncée comme telle. Aucun indicateur de couverture documentaire ne doit être affiché comme taux de réussite clinique.

## Contrôles exécutés dans ce dépôt

Le script `tools/validate_reference.py` vérifie les fichiers, les références, les exemples et la traçabilité documentaire. Les oracles numériques vérifient de petits calculs fictifs ; ils ne testent aucun moteur clinique ou solveur intégré. Voir le rapport à la racine.
