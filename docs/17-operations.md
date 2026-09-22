# 17 — Installation et exploitation

## Profils de déploiement

Poste autonome : UI locale, API loopback, worker, PostgreSQL et corpus installés ; réseau externe bloqué pour test strict. Établissement : services auto-hébergés sur LAN, authentification locale/OIDC, stockage protégé, adaptateurs des systèmes autorisés. Fédération : plusieurs installations propriétaires échangeant artefacts et messages, sans base patient centrale imposée. Service public en ligne : isolation par utilisateur/tenant, protections anti-abus et permissions adaptées ; ce profil n'est pas un raccourci d'exécution clinique.

## Installation reproductible

Distribuer images et dépendances lockées, SBOM, migrations, checksums, configuration exemple sans secrets et corpus synthétique. Le paquet offline inclut les images nécessaires ou une procédure d'import local ; `docker pull` n'est pas une étape obligatoire après installation offline. Aucun check de licence ou analytics WAN obligatoire dans le cœur gratuit.

La configuration minimale : tenant initial, profil réseau, stockage, DB, clés d'identité/signature, rétention, politique d'usage, corpus autorisés et limites techniques. Le mode clinique reste désactivé tant que les artefacts/politiques requis ne sont pas admis. Les secrets sont initialisés par l'opérateur, jamais préremplis avec des valeurs universelles.

## Santé et disponibilité

Liveness = processus actif ; readiness = accès DB/stockage et migrations compatibles ; capabilities = modules et corpus effectivement utilisables. Une panne CQF peut laisser consultation et saisie disponibles. Health endpoint ne révèle pas endpoints privés, secrets, versions vulnérables détaillées ou données patient à un public non autorisé.

## Jobs

Queue persistante avec `queued/running/succeeded/failed/cancelled`, lease_until, heartbeat, attempt, next_retry et résultat. Une tâche reprise vérifie son idempotence. Backoff borné avec jitter pour dépendances externes ; pas de retry automatique pour 4xx permanents, erreur de licence ou refus clinique. Annulation ne garantit pas annulation d'une opération externe déjà envoyée : réconcilier.

## Observabilité

Métriques : latence par type d'opération, backlog, import/quarantaine, abstention, modèle hors domaine, résultats périmés, taux d'échec fournisseur, âge des disponibilités, conflits réservations, coût fournisseur, erreurs de pack. Ne pas mettre patient_id, texte symptôme ou diagnostic dans labels métriques. Les mesures de qualité clinique sont séparées, sous politique de données.

## Sauvegarde et reprise

Sauvegarder DB, fichiers immuables, métadonnées et secrets nécessaires via procédure protégée. Définir RPO/RTO par déploiement ; les valeurs ne sont pas connues ici. Tester restauration isolée, réconciliation des opérations en vol et accès aux anciennes releases. Une sauvegarde non restaurée n'est pas une preuve de reprise. Les bookings externes doivent être relus après restauration pour éviter répétition d'ordres déjà exécutés.

## Migration et rollback

Migrations expand/contract lorsque nécessaire ; aucune suppression immédiate d'un champ utilisé par ancienne version. Backfill borné et vérifiable, journal, sauvegarde appropriée. Le rollback applicatif n'annule ni acte médical ni message reçu par un tiers. Une migration irréversible exige procédure de restauration et interruption contrôlée. Le rollback de connaissances est indépendant de celui du code.

## Incidents

Contenu retiré : bloquer nouvelles utilisations selon politique, identifier évaluations/ordres affectés, notifier propriétaires. Fuite soupçonnée : isoler accès, préserver preuves, appliquer procédure du déploiement. Fournisseur payant anormal : circuit breaker, bloquer nouveaux appels, réconcilier budget. Collision de réservation : montrer état incertain, ne pas confirmer localement. Aucune de ces procédures ne doit supprimer les traces pour masquer l'incident.

## Performance

Établir benchmarks à partir des parcours : recherche terminologique, création de cas, snapshot, inférence, import, planification et export. Les objectifs chiffrés sont des SLO à fixer à L0 selon hardware et population ; la documentation ne prétend pas des performances mesurées. Le timeout médical admissible ne se déduit pas d'un SLO technique ; c'est le protocole qui définit l'urgence et l'escalade.
