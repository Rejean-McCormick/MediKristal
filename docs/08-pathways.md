# 08 — Protocoles et investigations

## Représentation

Un protocole est un graphe dirigé d'étapes versionnées. Chaque étape possède type, préconditions à trois valeurs (vrai/faux/inconnu), entrées, actions proposées, sorties, transitions et critères d'arrêt. Boucles autorisées seulement avec condition de progression, borne et délai documentés. Un résultat inconnu ne prend pas la branche fausse par défaut.

Privilégier l'exécution d'un sous-ensemble CQL/FHIR qualifié via CQF. Les structures internes décrivent orchestration et autorisation ; elles ne sont pas un nouveau langage médical universel. Les extensions nécessaires sont versionnées et testées. Les calls externes depuis une expression clinique sont interdits ; le moteur reçoit les données figées dont il a besoin.

## Catalogue des actions

`ask` (question ou clarification), `examine` (geste clinique), `test` (analyse/imagerie/exploration), `observe` (réévaluation planifiée), `refer` (orientation), `treat_option` (option thérapeutique). Chacune décrit entrées, cible, délai approprié référencé, ressources, coût si connu, risques, préparation, données produites et responsable attendu. Une action clinique peut être pertinente sans machine.

## Garde d'applicabilité

Le moteur vérifie population, age/temps lorsque pertinents, contexte, ressources minimales, préconditions, exclusions et niveau d'usage. Une alerte d'urgence provient d'un protocole admis ; elle interrompt le classement économique et expose l'action d'escalade définie. En l'absence de corpus adapté, le système ne prétend pas avoir exclu une urgence. L'interface ne formule pas « aucun danger » sur la seule absence de règle déclenchée.

## Valeur attendue de l'information

L'objectif est d'améliorer la décision, pas de maximiser le nombre de tests ni la réduction d'entropie seule. Pour un modèle de décision qualifié, EVSI(test) = somme sur résultats r de P(r|données) × max_action E[U(action, état)|données,r] − max_action E[U(action,état)|données]. La valeur nette soustrait coûts, risques et retard dans une unité cohérente définie par politique. Ne pas soustraire directement dollars, probabilités et heures sans fonction d'utilité documentée.

Lorsque les utilités ou probabilités manquent, présenter une comparaison multicritère et les données manquantes. Un classement ordinal documenté reste possible ; ne pas l'appeler optimum probabiliste. Le critère coût est secondaire aux contraintes cliniques impératives.

## Première implémentation

Comparer des stratégies explicitement définies et validées, avec profondeur et nombre de branches bornés. Les scénarios incluent résultat positif, négatif, indéterminé, prélèvement inutilisable et examen non réalisé. La sélection garde `optimal`, `feasible`, `infeasible` ou `unknown` uniquement si le solveur et le problème le justifient. Un timeout avec solution donne feasible ; sans solution donne unknown, pas infeasible.

Les coûts combinés tiennent compte d'un prélèvement partagé, des consommables, du transport et des duplications, mais aucun partage n'est présumé sans compatibilité de tube, volume, conservation et circuit. Les examens « peu coûteux » ne sont pas ajoutés automatiquement : leur capacité à modifier une décision et leurs effets en aval sont évalués.

## Cycle d'une proposition

`proposed → accepted/rejected/expired/superseded`; accepted→order_requested lorsque les contrôles d'exécution passent. La décision clinique humaine reste distincte de l'ordre transmis. Une mise à jour du cas rend les propositions dépendantes périmées ; réévaluer avant exécution. La proposition contient un intervalle de validité, une source et un cas/revision, jamais seulement un texte.

## Exécution

Mode initial proposal_only. Mode institutionnel protocol_authorized exige version du protocole, politique signée/admissible, périmètre d'actes, acteur habilité ou délégation d'automatisation, exception handling et connecteur qualifié. Toute commande doit vérifier la fraîcheur des entrées, l'état du patient/cas, les droits et les prérequis. Le rôle patient n'autorise pas une prescription ou commande institutionnelle par simple accès API.

## Arrêt et suivi

Chaque parcours décrit quand arrêter les investigations, surveiller, escalader ou changer de voie. Aucun objectif de « certitude à 100 % » universel. Des résultats négatifs concernant d'autres maladies ne confirment pas mécaniquement une maladie non testée. La clôture conserve les hypothèses non résolues, tâches et résultats attendus avec un propriétaire de suivi.
