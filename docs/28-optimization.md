# 28 — Politique d’optimisation et comparaison des stratégies

## Deux problèmes, deux résultats

Le plan individuel sélectionne les actions qui peuvent améliorer une décision pour un cas. L’ordonnanceur collectif affecte les ressources aux demandes admissibles de plusieurs cas. Un changement de prix ou de créneau ne modifie jamais l’estimation de maladie. Il peut modifier le parcours faisable, avec explication.

Le premier moteur compare un ensemble fini de stratégies référencées dans un protocole ; il n’invente pas de nouvelles séquences cliniques. Pour chaque stratégie : étapes, branches observables, délais, ressources, coûts partagés, condition d’arrêt et décisions terminales. Les résultats `indeterminate`, `unusable_sample`, `not_performed` sont des branches explicites.

## Données et politique

`OptimizationPolicy` référence scope, modèle d’utilité facultatif, priorité des critères, règles de coût, contraintes impératives, stratégie de départage, limites du solveur et admission. L’objet est un artefact versionné, pas une configuration libre saisie par un administrateur de machines. Le corps opérationnel de chaque politique doit être validé par son moteur et son schéma versionné avant utilisation.

| Donnée manquante | Comportement |
| --- | --- |
| Modèle probabiliste applicable | Comparaison qualitative ; aucune EVSI numérique |
| Utilités des décisions | Front de Pareto sur critères disponibles ; aucun gain clinique monétisé inventé |
| Prix | Marquer coût inconnu ; ne pas classer comme gratuit |
| Capacité ou fraîcheur | Plan théorique seulement ; ne pas promettre de réservation |
| Fenêtre clinique admissible | Proposition à revoir ; pas d’affectation clinique automatisée |
| Branche possible non modélisée | Stratégie incomplète ; exclue du calcul d’optimum revendiqué |

Les trois modes réseau utilisent le même modèle de décision lorsque les mêmes artefacts et entrées sont disponibles. Un service payant peut ajouter une capacité ; il ne change pas l’autorité d’un protocole.

## Algorithme de comparaison

1. Figer cas, connaissances, politique, coûts et disponibilités avec leurs dates.
2. Énumérer les stratégies du protocole compatibles avec la population et les observations.
3. Rejeter celles qui violent les contraintes impératives ; conserver les raisons.
4. Dédupliquer les étapes déjà réalisées seulement si leur validité clinique et temporelle est explicitement admise.
5. Construire les branches conditionnelles avec le modèle joint ; ne pas multiplier des tests corrélés comme indépendants.
6. Calculer les coûts incrémentaux, délai et utilité selon les données disponibles.
7. Produire classement ou ensemble non dominé. Un résultat peut rester incomparable.
8. Tester la sensibilité aux coûts/délais incertains ; indiquer les conditions qui changeraient le choix.
9. Publier hypothèses, limites et validité. Recalculer avant commande si une dépendance a changé.

Si chaque branche et utilité sont définies, la valeur d’une stratégie est la somme des probabilités de ses feuilles multipliées par l’utilité de leur décision terminale, moins les pénalités déjà exprimées dans cette même unité. Les coûts d’étapes sont pondérés par la probabilité d’atteindre l’étape. Éviter de compter deux fois le coût d’un prélèvement partagé.

## Exemple économique synthétique

Exemple de logiciel, sans maladie réelle : stratégie A coûte 500 unités monétaires et s’exécute immédiatement ; B commence par un test à 20 unités puis utilise A dans 30 % des branches. Coût attendu de B : `20 + 0.30 × 500 = 170`. Cette comparaison n’autorise à choisir B que si ses décisions terminales, risques et délais respectent la politique. Le 30 % est un paramètre fictif de branche, pas une estimation clinique.

Un ajout à 0,25 unité monétaire est un coût marginal, pas une justification clinique. Le moteur doit pouvoir choisir de ne pas ajouter cet examen, par exemple si aucune branche ne modifie la décision ou si sa pénalité totale excède son bénéfice dans le modèle. L’exemple utilisateur « forte probabilité mais test coûteux » devient donc une comparaison explicite de stratégies, jamais la règle « exclure les autres maladies suffit à confirmer ».

## Affectation collective

Variables : présence de chaque affectation, créneau, ressource et site ; contraintes : fenêtres admises, personnel, capacité, préparation, transport, précédences et compatibilités. Les délais cliniques sont fournis par les politiques, pas dérivés du prix. Le premier solveur n’autorise pas la préemption d’un acte commencé.

Politique de départage technique : à admissibilité et priorité clinique identiques, ordre de réception puis identifiant stable. La promotion liée à l’attente exige une politique clinique explicite ; elle n’est pas un incrément arbitraire de score. Le temps d’attente est mesuré depuis la demande éligible, avec pauses justifiées distinctes.

Pour les objectifs lexicographiques, résoudre chaque niveau en préservant l’optimum prouvé du précédent. En timeout, conserver la meilleure solution admissible et son statut ; ne pas déclarer les niveaux inférieurs optimaux si le précédent ne l’est pas. Toute pondération alternative doit documenter unités et valeurs. Limites techniques CPU/temps sont des paramètres de déploiement, jamais des seuils cliniques.

Les solutions restent des propositions jusqu’à confirmation par les propriétaires. Un ordonnanceur interétablissements n’obtient pas un verrou global par lecture de calendriers. Il réserve avec réconciliation et peut devoir recalculer après refus.

## Réexécution et stabilité

En cas de panne, changement de priorité ou résultat nouveau : marquer le plan dépassé, recalculer les dépendances concernées et expliquer le diff. Minimiser les déplacements inutiles est un critère secondaire configurable. Un créneau confirmé est conservé jusqu’au résultat du remplacement, selon le protocole de réservation du chapitre 09. Un plan théorique et un plan confirmé ont des identifiants et statuts distincts.

## Critères d’acceptation

Voir AT-026 à AT-029 au chapitre 33 : coût partagé, arbre conditionnel, modèle absent, changement de prix sans changement de probabilité, priorité stable, capacité insuffisante et timeout. L’oracle économique ne constitue ni un modèle clinique ni un test d’OR-Tools intégré.

## Sortie structurée pour logiciels consommateurs

Chaque comparaison expose `StrategyEstimate` et ses `CriterionEstimate` avec état, unité et sources. Les critères inconnus ont une valeur nulle, jamais zéro. La sortie comprend aussi snapshots de coûts et bornes de validité. Les quatre champs complémentaires de `Plan` sont requis par le contrôle sémantique lorsqu’un calcul économique est revendiqué, même s’ils restent optionnels au niveau JSON pour lire le contrat antérieur. Le front non dominé peut avoir plusieurs stratégies et `selected_strategy_ref=null`.
