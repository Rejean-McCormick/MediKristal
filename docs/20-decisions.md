# 20 — Décisions d'architecture et points non résolus

## ADR de référence

| ADR | Décision | Motif / conséquence |
|---|---|---|
| 001 | Produit autonome et intégrations optionnelles | Alignement kOA sans dépendance opérationnelle |
| 002 | Monolithe modulaire initial | Réduit exploitation et transactions distribuées |
| 003 | Trois espaces de données | Connaissance, cas et ressources ont des cycles différents |
| 004 | Sémantique explicite sur stockage relationnel initial | Graphe logique sans infrastructure additionnelle prématurée |
| 005 | Modèle probabiliste distinct du retrieval | Empêche confusion similarité/probabilité |
| 006 | Protocoles et inférence distincts | Règle d'action et estimation de maladie ne sont pas identiques |
| 007 | Planification individuelle séparée d'affectation | Préserve indication clinique et concurrence ressources |
| 008 | Propositions séparées d'exécution | Autorisations et reçus vérifiables |
| 009 | Trois profils réseau/coût | Dernière préférence utilisateur remplace interdiction générale du payant |
| 010 | Corpus installables et versions immuables | Offline et reproductibilité |
| 011 | Kristal pour connaissance partageable | Pas de DB patient ou agenda dans Kristal |
| 012 | Pas de nouvelle DSL clinique complète | Évaluer CQL/CQF et compléter seulement les lacunes prouvées |
| 013 | Contributions révisées et modèles candidats | Aucun apprentissage automatique en production |
| 014 | Pas de dépendance LLM obligatoire | Cœur gratuit/local et décisions traçables |
| 015 | Schémas externes épinglés | Une prose approximative ne vaut pas conformance |
| 016 | FHIR R4 comme baseline proposée | Adaptateur versionné, R5 séparé |
| 017 | Aucun corpus clinique inventé | Valeurs synthétiques réservées aux tests |
| 018 | Aucune licence utilisateur imposée ici | La préférence gratuit ne sélectionne pas une licence juridique |

## Décisions techniques laissées à L0

Versions exactes FastAPI/Pydantic/SQLAlchemy, CQF/JDK, pgmpy, OR-Tools, choix bibliothèque JCS, chiffrement et identité locale. L'IA choisit des versions compatibles et documente leurs tests ; elle n'a pas besoin de demander à l'utilisateur chaque détail réversible. Une variation majeure de stack justifie une ADR, pas un mélange accidentel.

## Décisions qui exigent des données réelles

Premier parcours médical ; modèle et population ; paramètres quantitatifs ; seuils d'action ; protocoles et experts/review ; coûts, capacités et destinations ; cadre d'usage et exigences locales. Ces éléments doivent être représentés comme configuration/contenu absent, jamais devinés pour compléter l'application.

## Décisions d'usage non résolues

Licence finale du code ; corpus redistribuables par territoire ; responsabilités de publication ; règles de rétention ; finalité clinique précise et modalités d'autorisation. Le développement peut avancer avec fixtures et capacités limitées. Un assistant de codage ne doit ni attribuer une approbation fictive ni modifier les contrôles pour contourner cette absence.

## Écarts avec les anciens documents

Le document fondateur réduit parfois la logique à un moteur déterministe opposé au probabiliste : nouvelle règle, calcul probabiliste reproductible autorisé. Il présente un Clinical Epistemic State autonome : nouvelle règle, objet interne si nécessaire, mapping explicite vers schéma Kristal. Les « trust tiers » globaux deviennent évaluation de source par fonction et portée. Le compilateur/promotion peuvent réutiliser Kristal, sans dépendance réseau. L'ancienne interdiction de fournisseurs payants est remplacée par trois profils, suite à la clarification utilisateur.

## Portée de l'exhaustivité

Cette référence couvre le système complet envisagé, ses objets, algorithmes, contrats, états, contrôles et développement. Elle ne peut pas contenir toutes les connaissances médicales du monde, tous les contrats d'établissements ni une validation clinique future. Les absences sont identifiées, représentables et bloquent uniquement les capacités concernées. Les DTO et endpoints joints constituent le premier sous-ensemble exécutable de contrat ; l'extension se fait selon les règles du chapitre 13.

## ADR ajoutées en v1.1

| ADR | Décision | Conséquence |
| --- | --- | --- |
| 019 | Contrats 0.2.0 pour opérations administratives et suivi | Un seul OpenAPI généré, pas de routes implicites |
| 020 | Comparaison initiale de stratégies finies | Limites et contraintes explicites avant généralisation |
| 021 | Workflow durable et réévaluation des guards | Aucune délégation héritée indéfiniment d’une ancienne proposition |
| 022 | Suivi possédant un responsable et preuve de clôture | Notification distincte de résolution |
| 023 | Import qualifié par source/version de format | Nouveau format non interprété silencieusement |
| 024 | Interfaces et offline construits avec chaque tranche | L9/L10 consolident au lieu d’introduire tardivement ces capacités |

La documentation 1.1 corrige l’ambiguïté d’« exhaustive » : périmètre fonctionnel global décrit, contrats centraux étendus, contenus cliniques et intégrations locales à qualifier. Les limites restantes sont recensées au chapitre 26.
