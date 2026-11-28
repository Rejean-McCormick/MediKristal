# Backlog de réalisation du système final

Les identifiants `MK-SF` servent à ordonner les changements dans le dépôt actuel. Ils complètent les lots L0–L13 et les tickets TKT historiques. Les références AT relient chaque livraison aux scénarios du [chapitre 33](33-acceptance.md). À l’ouverture d’un ticket, vérifier les comportements déjà couverts et limiter le changement à l’écart observé.

| Ticket | Dépendances | Livraison | Exigences et acceptation |
| --- | --- | --- | --- |
| **MK-SF-01** | Checkout complet ou écart documenté | Intégrité du socle et exécution reproductible | MK-001, MK-019, MK-032 · AT-001, 019, 032 |
| **MK-SF-02** | MK-SF-01 | Campagne PostgreSQL et reprise locale | MK-010, MK-016, MK-027 · AT-010, 016, 027 |
| **MK-SF-03** | MK-SF-01 pour les tests, MK-SF-02 pour la qualification | Fiche de cas et reprise de l’opération | MK-003, MK-007, MK-015, MK-028, MK-031 · AT-003, 007, 015, 028, 031 |
| **MK-SF-04** | MK-SF-02, MK-SF-03 | Commande distante simulée, réconciliation et protection des claims | MK-010, MK-027, MK-031 · AT-010, 027, 031 |
| **MK-SF-05** | MK-SF-01 et choix du profil consommateur | Premier export local de savoir synthétique | MK-004, MK-014, MK-024, MK-025 · AT-004, 014, 024, 025 |
| **MK-SF-06** | MK-SF-03, MK-SF-05 pour les projections | Revue, révocation et projection bilingue | MK-004, MK-005, MK-012, MK-024 · AT-004, 005, 012, 024 |
| **MK-SF-07** | MK-SF-02 à MK-SF-04 par tranche | Comparaison et ordonnanceur sous concurrence | MK-008, MK-009, MK-022, MK-026, MK-029 · AT-008, 009, 022, 026, 029 |
| **MK-SF-08** | MK-SF-04, contrat partenaire et droits | Connecteurs réseau et modes | MK-002, MK-013, MK-017, MK-023 · AT-002, 013, 017, 023 |
| **MK-SF-09** | MK-SF-02 à MK-SF-08 selon le profil | Exploitation, restauration et régression de performance | MK-019, MK-020, MK-032 · AT-019, 020, 032 |

## MK-SF-01 — Reproduire le socle

- **Entrées** · Checkout propriétaire, SBOM, manifeste, verrou, procédure CI, archives fournies. Lire [l’audit](ETAT_2026-11-27.md).
- **Travail** · Vérifier présence et SHA-256 du verrou. Comparer les fichiers déclarés aux fichiers suivis. Pour `ZmartZnap.pyw`, établir si le fichier fait partie de la livraison dans le checkout propriétaire avant de corriger les règles d’inclusion. Comparer les actifs source aux actifs embarqués. Inventorier les versions de Python, des dépendances et de pytest effectivement utilisées.
- **Tests** · Intégrité, syntaxe, suite applicative, parité des routes, vérification documentaire et tests unitaires du diagnostic sur sa propre révision. Une archive incomplète produit un état bloqué pour la preuve d’intégrité.
- **Sortie** · Commandes rejouables et rapport d’écart avant/après. Le ticket se ferme quand les artefacts et contrôles du checkout complet concordent. Références : [démarrage](DEMARRAGE_IA.md), [qualification](PROFIL_QUALIFICATION.md).

## MK-SF-02 — Prouver les transactions et la reprise

- **Entrées** · Migrations Alembic, fixture synthétique et PostgreSQL isolé. Partir des tests de concurrence et d’intégrité existants. Le harnais SQLite sert à la régression locale.
- **Travail** · Vérifier upgrade et downgrade sur base jetable. Lancer des acteurs avec des sessions et processus distincts. Couvrir le dernier créneau, le double traitement du même événement et la reprise après commit interrompu avant consommation. Contrôler la version, le nombre de claims et l’état de l’inbox/outbox.
- **Sortie** · Au plus un claim de capacité pour la dernière unité, un traitement local par événement et consommateur, aucune perte d’événement commité. Vérifier l’issue des deux acteurs et enregistrer la preuve. Références : [architecture](02-architecture.md), [exploitation](17-operations.md), [tests](18-tests.md).

## MK-SF-03 — Fiche de cas et reprise

- **Entrées** · Interface de référence, API des cas, observations, évaluations, propositions, opérations et suivis. Le périmètre initial est la fiche professionnelle synthétique.
- **Travail** · Réutiliser les objets, écrans et routes pertinents. Donner un point d’entrée à la fiche depuis les cas autorisés. Garder cas, contexte, révision et opération sélectionnée à la reprise. Lire l’état durable après rechargement, contrôles d’accès compris. Lier la correction d’une observation à l’état périmé de l’évaluation. Utiliser les états et critères du [chapitre 31](31-ui-acceptance.md).
- **Sortie** · Reprendre le même cas sans réémettre la dernière mutation. Une navigation directe refuse la lecture hors périmètre. L’écran reste utilisable au clavier et expose l’état, sa fraîcheur et l’action suivante. Reporter le résultat vers AT-031.

## MK-SF-04 — Réconcilier un effet distant simulé

- **Entrées** · `FacilityPort`, opérations, claims, idempotence et worker existants. Ajouter un double qui peut enregistrer un effet puis rendre la réponse indisponible, et qui permet de relire son état par identifiant.
- **Travail** · Persister une intention avec sa corrélation, conserver le claim en état ambigu puis lire le reçu de référence. Utiliser la même corrélation à la reprise. Dans la capture, `confirm_booking` accepte `reconciling` et sa branche d’expiration peut libérer le claim. Couvrir cet écart dans le test de régression avant d’ajouter tout envoi distant. Après un effet possiblement émis, l’expiration locale du hold ne suffit pas à résoudre l’issue. Pour toute transition, vérifier tenant, grant et révision selon le contrat. Préserver les réservations antérieures et leur historique.
- **Sortie** · Preuve API + interface sur perte de réponse, crash, rejeu et deux acteurs. Le serveur confirme seulement sur preuve du partenaire fictif. Couvrir reçu absent, état encore inconnu et annulation confirmée selon le [modèle opérationnel](30-operational-contracts.md). Les retries d’écriture restent bornés par le contrat du port.

## MK-SF-05 — Exporter une release synthétique

- **Entrées** · Fixture de release, route d’export, port de publication et schéma consommateur. La première décision du ticket fige le consommateur, le format, le namespace, l’identité, les fichiers et les SHA-256. L’échange peut commencer par des fixtures locales des snapshots.
- **Travail** · Faire passer une assertion et sa provenance par le mapping. Sélectionner les seuls objets de savoir partageables. Valider droits, version, références et données imbriquées. Rejouer validation et lecture côté consommateur. Conserver résultat, avertissements et digest dans le dossier de preuve.
- **Sortie** · Même entrée et mêmes versions donnent le même artefact selon le profil. Relancer avec référence de cas, profil inconnu, perte critique ou release retirée bloque l’export. La capacité indique sa portée exacte. Voir [les intégrations](14-integrations.md).

## Premier incrément de consultation de MK-SF-06

Le [lot public est indexé et consultable en ligne de commande](IMPORTER_REFERENTIELS_PUBLICS.md). Commencer le branchement Web par un lecteur local en lecture seule. Configurer explicitement le chemin de l’index, limiter et paginer les résultats, retourner source, type, code, libellé et empreinte. Tester succès par DIN et par libellé, résultat vide, index absent et accès autorisé. Vérifier que l’index absent laisse l’application autonome disponible et que la recherche ne déclenche aucune mutation du corpus ni du cas. Cette tranche technique peut avancer indépendamment de l’export Kristal de MK-SF-05.

## MK-SF-06 à MK-SF-09 — Extensions par tranche

| Ticket | Frontière et travail | Validation |
| --- | --- | --- |
| MK-SF-06 | Réutiliser `importers.py`, les sources, releases et contributions. Livrer revue et retrait sur un petit corpus synthétique. Ajouter lecture `fr-CA` et `en-CA` à identité partagée. | Une révocation bloque les nouvelles utilisations concernées et localise l’impact. Revue, repli et libellé manquant sont observables. [Savoir](06-knowledge.md) · [Contributions](11-contributions.md) |
| MK-SF-07 | Étendre `planning.py` par stratégies finies puis affectations. Deux ressources fictives et un conflit de capacité avant tout solveur additionnel. | Coût inconnu distinct de zéro, prix sans effet sur l’inférence, contrainte impérative respectée, statut explicite en timeout. [Optimisation](28-optimization.md) |
| MK-SF-08 | Un port et un partenaire par changement. FHIR et diffusion suivent leurs contrats propres. Compiler permissions, limites, délais, budgets et profils réseau dans les tests. | Rejeu consommateur, perte déclarée, refus de droits, absence de WAN en offline strict, budget réconcilié en cas d’incertitude. [Modes](12-modes.md) · [Intégrations](14-integrations.md) |
| MK-SF-09 | Distribuer le paquet du profil, capturer les versions et réaliser restauration et campagne de charge. Publier l’état des capacités au niveau réellement prouvé. | Rapports complets sur révision exacte, restauration démontrée, critères de performance évalués et qualification indépendante. [Exploitation](17-operations.md) · [Profil](PROFIL_QUALIFICATION.md) |

Le lot L13 relève d’un dossier distinct par finalité, population et environnement. Ses droits, contenus, responsables et décisions d’usage doivent provenir des propriétaires compétents. Les tranches d’ingénierie avancent avec les fixtures synthétiques.
