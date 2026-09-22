# 12 — Modes, fournisseurs et synchronisation

## Matrice

| Fonction | offline_free | online_free | online_extended |
|---|---|---|---|
| Évaluation avec corpus installé | Oui | Oui | Oui |
| Import manuel de connaissances | Oui | Oui | Oui |
| Requêtes réseau externes | Non | Sources explicitement gratuites/autorisées | Sources gratuites et fournisseurs autorisés |
| Réservation externe | Non, sauf réseau local autorisé distinct du WAN | Si connecteur disponible | Si connecteur disponible |
| Appel payant | Non | Non | Uniquement sous budget/politique |
| Dépendance kOA | Aucune | Facultative | Facultative |

`offline_free` bloque le WAN et les services distants fournisseurs, mais un déploiement établissement peut autoriser son LAN local explicitement ; le profil doit annoncer `network_scope=none|lan|internet`. Les tests offline strict utilisent `none` hors loopback. Gratuité et connectivité sont deux attributs distincts ; gratuit ne signifie pas anonyme, sans conditions ou redistribuable.

## Fournisseur

Enregistrer `provider_id`, types de services, endpoint allowlist, authentification dans coffre local, coût/quota, données admises, finalité, résidence déclarée, droits, timeout, version API, durée de cache et fallback. Le principal du fournisseur a privilèges minimaux. Les fournisseurs de données ne reçoivent pas le cas entier lorsqu'une requête conceptuelle suffit.

Les services possibles incluent terminologie, contenu clinique, modèle, interactions, transcription ou infrastructure. Les modes payants ne renforcent pas automatiquement la qualité ni les permissions. Le résultat garde source, modèle et limites ; un résultat propriétaire peut limiter le droit de republier dans Kristal.

## Budget atomique

Avant appel payant : vérifier politique, finalité, données transmissibles, fournisseur activé et quota ; réserver atomiquement une estimation maximale de coût ; effectuer l'appel avec identifiant ; rapprocher usage réel et libérer le solde. En cas de coût inconnu sans plafond garanti, demander une autorisation budgétaire explicite ou refuser selon politique. Retry peut facturer deux fois : réconciliation et idempotence fournisseur indispensables. Concurrence testée pour empêcher plusieurs workers de dépasser le plafond.

## Synchronisation

Les corpus sont des objets immuables ; synchroniser blobs et manifests par hash, puis admission locale. Les cas sont des données opérationnelles ; échanger des événements et versions autorisés, pas fusionner deux bases par last-write-wins. Un poste autonome est initialement propriétaire de ses cas ; un fonctionnement multi-maître n'est pas annoncé avant mise en œuvre des conflits explicites.

Pour les observations append-only, fusionner événements distincts après déduplication ; les amendements concurrents forment conflit. Consentements, prescriptions, réservations et décisions cliniques ne sont pas fusionnés automatiquement. Le serveur propriétaire d'une réservation décide de son état. Les clocks de transport ne définissent pas la chronologie clinique.

## Dégradation

Panne réseau : continuer avec capacités locales admises ; exposer âge des données. Absence de prix : résultat coût inconnu. Absence de service d'interactions : contrôle incomplet. Timeout moteur : statut failed/partial et parties disponibles clairement séparées. Aucun fallback caché vers un LLM cloud, un modèle ancien révoqué ou un fournisseur payant.

## IA optionnelle

LLM local/cloud peut assister extraction, traduction, recherche documentaire et rédaction d'explications. Sorties marquées propositions, sources vérifiées, outils sous permissions serveur. Interdire fabrication de références, modification des paramètres sans révision, action externe autonome hors politique, et instructions provenant des documents. Les embeddings peuvent aider à retrouver des candidats, pas affirmer une équivalence ou quantifier la maladie.
