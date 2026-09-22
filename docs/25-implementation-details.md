# 25 — Compléments d'implémentation

## États et transitions détaillées

Une table d'états définit les transitions autorisées ; l'application ne permet pas un PATCH libre de statut. Chaque transition journalise acteur, cause, révision avant/après et politique. Une transition vers le même état avec clé identique est idempotente, une nouvelle intention sur état incompatible est 409.

| Agrégat | Transition | Condition |
|---|---|---|
| Cas | draft→active | Identité/contexte suffisants pour l'ouverture, grant |
| Cas | active↔waiting | Motif et tâches attendues enregistrés |
| Cas | active/waiting→closed | Politique de suivi résultats satisfaite |
| Cas | closed→active | Réouverture motivée et permission |
| Proposition | proposed→accepted/rejected | Décision autorisée, cas frais |
| Proposition | proposed/accepted→superseded | Entrée déterminante modifiée |
| Proposition | accepted→order_requested | Garde d'action réussie et outbox persistée |
| Ordre | requested→accepted/rejected | Accusé authentifié du destinataire |
| Ordre | accepted→in_progress→completed | Événements du propriétaire, pas de minuterie locale |
| Ordre | requested/accepted/in_progress→cancel_requested | Annulation admissible |
| Ordre | cancel_requested→cancelled | Confirmation distante ; refus d'annulation conserve état réel |
| Booking | hold_requested→held | Reçu et expiration présents |
| Booking | held→confirm_requested→confirmed | Bail valide et reçu propriétaire |
| Booking | held→expired | Expiration vérifiée, aucun acte confirmé |
| Opération | queued→running→succeeded/failed | Lease et résultat durable |
| Opération | running→reconciling | Effet externe possible mais réponse inconnue |
| Contribution | submitted→screening→under_review | Précontrôles passés |
| Contribution | under_review→accepted/rejected/changes_requested | Décision de révision autorisée |
| Contribution | changes_requested→submitted | Nouvelle révision, ancienne préservée |
| Contribution | accepted→published | Inclusion dans une release publiée |
| Release | candidate→published | Vérifications de build et décision explicite |
| Release | published→revoked | Retrait motivé et propagation d'impact |

Les événements distants peuvent sauter des états intermédiaires non transmis (ex. completed sans in_progress). L'adaptateur vérifie la légitimité et inscrit une transition observée avec lacune, sans inventer les dates absentes. Les retours contradictoires exigent réconciliation.

## Algorithme de sélection de stratégie

Entrées figées : CaseSnapshot C, Evaluation E, KnowledgeRelease K, ResourceSnapshot R, DecisionPolicy P. Valider E.case_revision=C.revision, versions, finalité, capacité et droits. Construire les actions admissibles via protocoles. Appliquer les contraintes impératives avant de calculer les préférences. Énumérer les stratégies du catalogue borné ; vérifier préparation, délai, ressources, coûts et sorties possibles. Si un modèle de décision complet est disponible, calculer utilités attendues ; sinon produire un front d'options non dominées avec critères manquants.

Ne pas confondre meilleure précision diagnostique et meilleur résultat clinique. La politique précise bénéfices/risques, perspective économique et préférences patient. Si l'information ne peut changer aucune action admissible, signaler son faible apport décisionnel dans le modèle, sans généraliser en « examen inutile » hors de ce modèle.

Résultat : stratégies évaluées, sélection éventuelle, contraintes, critères, inconnus, versions, reasons et limites. Un résultat partiel n'est pas qualifié optimal. Aucun coût patient ou score de mérite ne réduit l'urgence médicale.

## Formulation de réservation

Pour chaque demande i, alternatives a et créneaux t admissibles, variable binaire x(i,a,t). Somme des affectations <=1 pour une demande ; =1 seulement si la politique impose satisfaction et un problème réalisable est établi. Ressources exclusives : intervalles sans chevauchement ; capacités cumulatives : somme des consommations <= capacité. Précédences : début de l'étape suivante après fin et délai requis de la précédente. Contraintes de lieu/transport/préparation attachées à la stratégie. Les demandes non affectées restent visibles avec raison.

Objectifs multi-critères documentés et éventuellement lexicographiques. Ne pas donner un coefficient arbitraire permettant à une économie de quelques dollars de dominer une urgence. Les tests utilisent des unités synthétiques et coefficients fictifs marqués ; les déploiements requièrent une politique admissible.

## Protocole, exécution et packaging

Chaque étape est identifiée et typée : input, evaluate, propose_action, wait_result, review, terminate. Les conditions référencent expressions versionnées (`library_ref`, `expression_name`) et non du code Python arbitraire. Les transitions traitent true/false/unknown/error explicitement. La compilation vérifie références résolues, absence de cycle non borné, action terminale atteignable, modèles/licences et compatibilité. Une demande attendue possède correlation et échéance issue du protocole ; un timeout technique de worker ne décide pas du délai clinique.

Un TreatmentOption inclut résultats des checks (pass/fail/unknown/not_applicable), références sources, exigences non satisfaites et version du cas. `not_applicable` requiert justification ; il ne sert pas à dissimuler une dépendance non implémentée. Le calcul de dose est un port séparé, avec unités, entrées, arrondi, limites et preuve de validation ; aucun fallback de dose par défaut.

## Contrats de configuration

La configuration est validée au démarrage : mode, network_scope, intended_use, execution_policy, provider_allowlist, paths/DB/secret references, quotas, modèle de droits et trust roots. `online_free` interdit provider.paid=true ; `offline_free` interdit WAN même si une clé existe ; `online_extended` n'active aucun fournisseur tout seul. `clinical_execution` exige politiques d'action admises. Un changement de mode écrit audit et reconstruit capabilities ; les opérations en vol gardent leur politique d'origine ou sont suspendues si elle est révoquée.

Valeurs de départ : offline_free, network_scope=none, intended_use=engineering, execution_policy=proposal_only, paid_budget=0. Les secrets sont des références, pas des valeurs en clair dans le fichier de configuration partagé.

## Administration API et limites du noyau initial

Le contrat joint inclut les commandes métier centrales. La gestion complète des comptes, délégations, consentements, pièces jointes, import FHIR établissement et catalogues volumineux doit suivre les mêmes invariants et être étendue avant leur livraison. Choisir une bibliothèque d'identité ou un IdP compatible ne dispense pas des grants locaux. Les uploads utilisent une autorisation dédiée, une limite de taille, un stockage de quarantaine et un identifiant opaque ; `uploaded_file_ref` ne doit jamais accepter un chemin arbitraire du serveur.

Les profils FHIR et adaptateurs IK/Koali précis ne sont pas fournis par les snapshots MediKristal. Les types internes n'autorisent pas à inventer leurs routes. Cette limite est un point de raccordement documenté, pas un stub qui retourne succès.

## Journal d'explication et reproductibilité

Le graphe de trace est acyclique et référence toutes les transformations nécessaires. Vérifier parent_ids existants, absence de cycle, données autorisées et correspondance des modèles. Le digest de replay porte snapshot normalisé, références de connaissances/modèles/politiques, version moteur, instant clinique, seed, paramètres numériques et, pour la planification, snapshot ressources/coûts. Ne pas inclure les identifiants de log ou dates d'exécution techniques sans effet sémantique.

L'égalité bit à bit est requise pour identités de packs selon canonicalisation ; pour modèles numériques, tolérance et environnement sont déclarés. Une tolérance ne permet pas de changer de décision près d'un seuil sans test et explication. Un rejeu n'effectue jamais les commandes externes historiques.

## Export, suppression et fin de vie

Exporter un cas exige finalité et destinataire ; exporter connaissance exige absence de données individuelles et droits. Suppression d'identité, anonymisation, archivage et retrait de publication sont quatre opérations distinctes. Une révocation de consentement bloque les usages concernés selon politique sans prétendre annuler des actes déjà réalisés. Les modèles dérivés de données sensibles peuvent conserver des restrictions ; leur statut n'est pas automatiquement public parce que les poids sont numériques.
