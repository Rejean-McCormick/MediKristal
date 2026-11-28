# Profil de qualification du premier déploiement autonome

**Statut** protocole d’ingénierie proposé. Les objectifs chiffrés sont des hypothèses de départ à confirmer sur le matériel retenu. Les mesures restent à exécuter. Les données, comptes, modèles et établissements des essais sont synthétiques.

## Environnement de référence proposé

- Hôte Linux x86-64, 4 vCPU, 8 Gio de RAM et SSD local. Enregistrer modèle CPU, OS, moteur de conteneurs et espace libre mesuré.
- Python 3.12, PostgreSQL 16 selon la version déclarée dans Compose, API et worker issus de la même révision. Capturer les versions et digests réellement utilisés.
- Un tenant de charge et un second tenant pour les refus. Charger 1 000 cas, 20 000 observations et un corpus synthétique versionné de 10 000 objets. Figer les versions du générateur, du corpus et une seed. Tester un et deux workers.
- Profil `offline_free`, périmètre réseau `none` après installation, même hôte et réseau interne nécessaire aux conteneurs. Bloquer les sorties WAN et capturer les tentatives. Vérifier que la politique initiale d’exécution demeure `proposal_only`. Les opérations de réservation de la campagne s’exécutent dans un scénario synthétique dédié avec habilitations de test.

## Campagne

1. **Reproductibilité.** Contrôler intégrité, dépendances et actifs. Rejouer les migrations sur base jetable. Démarrer la topologie Compose avec secrets propres à l’environnement de test et vérifier santé, API, worker et persistance après redémarrage.
2. **Parcours hors WAN.** Sur un tenant, créer, observer, évaluer, proposer, rattacher un résultat synthétique puis amender. Vérifier trace de version et statut périmé. Relire avec un compte autorisé et essayer depuis l’autre tenant et sans grant.
3. **Concurrence et panne.** Répéter au moins 30 fois chaque course en réinitialisant ses fixtures. Exécuter simultanément deux demandes sur la dernière unité, deux livraisons du même événement et une correction pendant une opération. Faire un arrêt après commit avant consommation, puis un deuxième après effet du partenaire fictif avant reçu local. Vérifier états, reçus, déduplication et reprise avec deux workers.
4. **Charge.** Échauffer 2 minutes, mesurer 10 minutes, puis répéter 3 fois avec 10 utilisateurs concurrents simulés. Mélanger 70 % de lectures, 20 % de mutations autorisées et 10 % d’évaluations synthétiques. Paginer les listes. Séparer refus attendus, erreurs serveur, timeouts et résultats métier. Rapporter les percentiles par classe et vérifier les invariants sur l’état final.
5. **Restauration.** Sauvegarder la base, le corpus et les blobs. Restaurer sur une instance isolée. Contrôler les digests, l’état des opérations durables, la reprise du worker et la lecture des preuves après retrait d’une release. Mesurer du lancement de la restauration à la confirmation fonctionnelle.

## Critères de passage proposés

| Domaine | Critère | Preuve |
| --- | --- | --- |
| Intégrité | Manifestes, SBOM, contrats et dépendances cohérents. Suite de référence verte. Seuil de couverture existant de 90 % évalué et rapporté séparément. | Révision, SHA-256, journaux et rapport de couverture. |
| Isolation | Aucun accès hors tenant ou sans grant sur les fixtures de refus. Aucune sortie WAN pendant le parcours strict. | Assertions API et observation réseau. |
| Réservation et reprise | Zéro surbooking et zéro mutation dupliquée dans les courses. Toute ambiguïté reste visible jusqu’à une preuve ou une résolution opérateur. | États, nombre de claims, identifiant stable, reçu et journal d’événements. |
| Lecture | p95 ≤ 500 ms sur listes paginées et lecture de fiche côté API, hors client navigateur. | Distribution par route et volume, avec p50 et p99. |
| Mutation locale | p95 ≤ 1 s, rendu de l’état persisté inclus dans la réponse API. | Durée côté API, taux d’erreurs et contention SQL. |
| Évaluation synthétique | p95 ≤ 2 s sur fixture et modèle de référence. Mesurer séparément les travaux asynchrones. | Durées, modèle exact, variance des trois passes. |
| Charge | Moins de 1 % d’échecs techniques inattendus. Les cas d’accès et de contention attendus ont leur statut contractuel. | Taux par classe et détails des erreurs. |
| Reprise locale | Opération locale prête depuis le commit consommée dans les 60 s après redémarrage du worker sur file de test bornée à 100 événements. | Âge de file, chronologie commit/arrêt/redémarrage/consommation et backlog résiduel. |
| Restauration | Restauration vérifiée en ≤ 30 min sur le jeu de référence. Le point de restauration correspond à la dernière sauvegarde vérifiée et son âge est mesuré. | Chronométrage, checksums, contrôle des cas et des opérations en cours. |

Un écart de performance se traite d’abord par mesure des requêtes, de la contention ou du travail en file. Toute révision des objectifs s’accompagne du contexte et des résultats. Pour qualifier un autre profil, rejouer sa propre campagne. Les seuils ci-dessus concernent l’ingénierie logicielle et ne définissent aucune fenêtre, priorité ni règle clinique.

## Dossier de preuve à conserver

Identifiant de campagne, date, révision, versions et digests, hôte, configuration filtrée, fixtures, commandes, taille et concurrence, résultat attendu, résultat observé, écarts, verdict et responsable. Les preuves incomplètes portent le statut `NOT_RUN` ou `BLOCKED` pour les scénarios concernés.
