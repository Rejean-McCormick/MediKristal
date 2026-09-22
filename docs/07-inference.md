# 07 — Inférence probabiliste

## Séparer recherche d'hypothèses et calcul

La recherche d'hypothèses utilise des relations médicales, règles d'entrée ou modèles de retrieval. Elle produit des candidats et raisons. Elle ne produit pas de pourcentages. Le calcul probabiliste nécessite un modèle distinct, applicable à la population et aux entrées du cas. L'absence d'un modèle n'empêche pas de montrer une relation sourcée, mais impose `not_estimable`.

Types de sorties : `probability`, `score`, `qualitative`. Afficher un score avec unité `%` est interdit. Une probabilité déclare l'événement cible (maladie présente maintenant, événement futur, etc.), horizon, modèle, population et calibration. Un ensemble d'hypothèses non exclusives ne somme pas nécessairement à 1. Le modèle doit déclarer `mutually_exclusive` ou `multi_label`; ne pas forcer une normalisation sur une liste incomplète.

## Types de modèle autorisables

Régression/statistique validée, réseau bayésien, modèle de vraisemblance, règle prédictive publiée, modèle ML calibré et autres adaptateurs qualifiés. Un LLM n'est pas accepté comme oracle de probabilités. Il peut proposer extraction ou hypothèses non exécutoires, marquées comme telles. L'entraînement et le réentraînement sont hors runtime clinique ; ils produisent des candidats révisables.

## Pipeline normatif

1. Fixer snapshot du cas et horloge clinique.
2. Sélectionner modèles admissibles par usage, population, licence et release.
3. Construire les features avec règles de temps, unités, identité et dépendances déclarées.
4. Détecter missingness, conflits, données hors domaine et qualité insuffisante.
5. S'abstenir ou utiliser le traitement des données manquantes prévu dans le modèle ; ne jamais imputer implicitement zéro.
6. Exécuter dans les budgets CPU/mémoire/temps ; garder seed/configuration.
7. Produire résultats, incertitudes, contributions descriptives et limites.
8. Vérifier invariants numériques et joindre qualification/calibration.
9. Persister atomiquement résultat et trace ; signaler cas modifié en parallèle.

## Mise à jour bayésienne

Pour un modèle binaire applicable : odds préalable = p/(1−p), odds postérieure = odds préalable × rapport de vraisemblance, puis p' = odds/(1+odds). Cette identité n'autorise pas à multiplier arbitrairement des rapports de vraisemblance corrélés. Une nouvelle observation met à jour le modèle joint ou recalcule l'ensemble des features ; elle n'est pas ajoutée deux fois à l'état précédent.

Modèle synthétique de test : prévalence fictive 0,10 ; sensibilité fictive 0,80 ; spécificité fictive 0,90. Après résultat positif, p = 0,08/(0,08+0,09) = 0,4705882353. Après résultat négatif, p = 0,02/(0,02+0,81) = 0,0240963855. Ces nombres ne décrivent aucune maladie réelle. Un résultat réimporté identique conserve p, il ne produit pas une seconde multiplication.

Si p=0 ou 1 provient d'un arrondi, ne pas le traiter comme certitude absolue. Les modèles doivent fournir la précision et les bornes ; les calculs utilisent log-odds lorsque nécessaire, gèrent underflow, overflow et NaN. Un échec numérique retourne `model_failed`, jamais 0 %.

## Observations continues et temporelles

Le modèle définit densités, distributions, transformations et seuils. Une valeur continue ne doit pas être binarisée selon un intervalle de référence sans règle explicite. Préserver censures, limites de détection et unité. Les répétitions d'un même analyte forment une série ; les corrélations entre manifestations, maladies et prélèvements sont modélisées ou reconnues comme limitation. Coexistence de maladies, sévérité et temps depuis début ne doivent pas être effacés pour simplifier une interface.

## Calibration et transportabilité

Rapport minimal : provenance des données, population, période, exclusions, split patient/établissement/temps, gestion des manquants, calibration (courbe/Brier/log loss selon modèle), discrimination pertinente, erreurs par sous-groupe, intervalles et limites. Empêcher fuite de données entre apprentissage et évaluation, notamment résultats futurs et diagnostic final utilisé comme feature.

Un diagnostic de facturation ou une absence de code n'est pas automatiquement une vérité clinique. Une mauvaise transportabilité au contexte local produit `out_of_scope` ou une limitation qui interdit la présentation comme probabilité clinique validée. Le seuil d'abstention vient d'une politique documentée. Aucune auto-recalibration à partir des décisions courantes : elles peuvent refléter les propres recommandations du système et créer une boucle biaisée.

## Explication

Conserver observations utilisées/exclues, transformations, modèle, facteurs contributifs et preuves. Une contribution numérique ou SHAP est une explication de modèle, pas une relation causale. Ne pas attribuer une recommandation à une source qui n'a pas été utilisée. Les textes Architect ou LLM ne peuvent renforcer ni la certitude ni l'autorité.

## Critères d'acceptation

Le corpus synthétique couvre positif/négatif/inconnu, duplicata, correction, corrélation déclarée, deux maladies coexistantes, unité invalide, hors population, modèle retiré, timeout et rejeu. Le moteur renvoie des raisons machine lisibles. Un résultat de recherche peut être stocké, mais la barrière d'usage bloque son exécution clinique tant que les conditions ne sont pas remplies.
