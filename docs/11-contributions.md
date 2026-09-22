# 11 — Contributions scientifiques et gouvernance

## Acteurs

Contributeur, réviseur de méthode, expert du domaine, responsable de publication et administrateur technique. Une université ou un médecin n'est pas automatiquement une autorité globale ; identité et compétence sont vérifiées selon une politique explicite. Un administrateur n'acquiert pas la compétence médicale en modifiant un rôle technique.

## Types de proposition

Mapping, assertion, estimation quantitative, correction de source, modèle, recalibration, protocole alternatif, indication de test, contrainte ressource, explication ou traduction. Chaque proposition vise un artefact/version, présente diff, justification, sources, population, méthode et impacts attendus. Les données patient brutes sont interdites dans le canal public ; des données de recherche autorisées suivent un canal distinct.

## Workflow

États `draft`, `submitted`, `screening`, `under_review`, `changes_requested`, `accepted`, `rejected`, `withdrawn`, `published`. Le passage accepted→published nécessite la construction et admission d'une release ; accepted n'active aucun modèle. Les décisions comportent auteur, date, portée, preuves et éventuels conflits d'intérêt. Les avis contradictoires restent consultables selon droits.

Précontrôles : schéma, source accessible sous droits, absence de données individuelles, duplication, statut rétracté, cohérence statistique et sécurité des pièces jointes. Comparaison : cas de référence, cas limites, sous-groupes, calibration, impact sur actions/coûts/délais, régressions et conséquences des manquants. Un gain moyen ne suffit pas à masquer une dégradation critique.

## Corriger « 90 % en 70 % »

La contribution précise l'événement, la population, l'horizon, le modèle, les données et le changement de paramètres. Elle ne remplace pas une constante d'interface. Les fréquences, probabilités a priori, calibration et probabilité postérieure sont des objets distincts. Comparer ancien/nouveau sur cas figés et données d'évaluation indépendantes quand disponibles. L'interface explique où les deux modèles divergent.

## Parcours alternatif

Un nouvel examen ou ordre d'investigations décrit conditions, performances attendues, risques, effets sur les décisions, ressources et coût total. La publication peut être limitée à une population ou un site. La politique locale choisit une version sans effacer les autres.

## Apprentissage

Les journaux de décisions ne sont pas une vérité terrain automatique. Aucun entraînement sur données individuelles sans autorisation et finalité ; pas d'apprentissage online modifiant le modèle actif. Le processus d'entraînement produit un modèle candidat, sa documentation et les preuves de reproductibilité. Évaluer dérive et biais sans transformer chaque alerte en mise à jour automatique.

## Gouvernance minimale implémentable

Le logiciel peut être développé sans experts déjà recrutés : définir rôles, workflows, signatures et statuts ; livrer des fixtures research/engineering. Ne pas créer de faux experts ou attestations pour débloquer un chemin de démonstration. L'absence de décision clinique reconnue reste visible et bloque seulement les usages qui l'exigent.

## Intégration Orgo

Le workflow local suffit hors écosystème. Si une installation délègue le suivi à Orgo, celui-ci possède ses tâches et cas de travail ; MediKristal conserve propositions et décisions de connaissance. Lier identifiants et reçus. Un `task_completed` externe n'est pas une reconnaissance clinique sans décision de révision structurée et politique satisfaite.
