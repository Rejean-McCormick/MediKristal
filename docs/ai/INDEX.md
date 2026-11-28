<!-- kOA Doc Server · Docs IA · lot 03 · projet : MediKristal · proposition dérivée à valider -->
# Navigation IA — MediKristal

**Objet constaté :** Logiciel de modélisation de connaissances médicales MediKristal, distinct de son LevelUpDiag et de son wiki.

**Frontière de responsabilité :** Le propriétaire MediKristal contrôle le modèle et les données; le diagnostic frère vérifie des aspects logiciels seulement, sans validation clinique.

**Source :** `SmartDump_20261120_221507.zip` → `MediKristal_Code_snapshot.zip` (20 novembre 2026). Le chemin Windows est une déclaration de snapshot, pas une vérification de l'état actuel.

**Statut :** Documentation de navigation dérivée de sources propriétaires, à revoir. Ce document ne vaut ni profil d'ingénierie mesuré, ni certification, ni permission d'exécution.

## Ordre de lecture — fichiers réellement présents dans la capture

1. [`README.md`](../../README.md) — SHA-256 `92855c50a47dc0df…` dans la capture.
2. [`AGENTS.md`](../../AGENTS.md) — SHA-256 `b09ca4f0c306f166…` dans la capture.
3. [`docs/README.md`](../../docs/README.md) — SHA-256 `2062c4af22980d1e…` dans la capture.
4. [`contracts/README.md`](../../contracts/README.md) — SHA-256 `87807e517b6b0822…` dans la capture.
5. [`backend/pyproject.toml`](../../backend/pyproject.toml) — SHA-256 `e5181171de8e7114…` dans la capture.

## Entrée pour le codage

Suivre le [démarrage IA](../DEMARRAGE_IA.md) et le [backlog du système final](../BACKLOG_SYSTEME_FINAL.md). Le premier ticket est MK-SF-01.

## Reprise du 27 novembre 2026

Consulter [l’architecture du système final](../SYSTEME_FINAL.md), [l’état vérifié de la capture](../ETAT_2026-11-27.md) et le chapitre propriétaire du lot ciblé. Les empreintes ci-dessus décrivent la capture du 20 novembre.

## Parcours recommandé pour une intervention assistée par IA

1. Identifier la question, le sous-système concerné et les responsabilités du propriétaire.
2. Lire les documents ci-dessus **dans cet ordre**; consulter les contrats et consignes propriétaires plus récents si le checkout a évolué.
3. Lire les AGENTS du sous-dépôt, identifier contrats, migrations et tests, puis travailler exclusivement sur données synthétiques autorisées.
4. Établir les vérifications effectivement disponibles dans la révision locale, consigner les résultats et ne conclure qu'à l'intérieur du périmètre couvert.
5. Proposer les changements; demander une décision explicite avant toute écriture à effet, déploiement, publication ou promotion de preuves.

## Risque propre à ce dépôt

Aucune conclusion clinique, décision de santé, conformité réglementaire ou validation de données patients ne peut provenir de ces docs IA.

## Compléments

- [`AI_CONTEXT.md`](AI_CONTEXT.md) : règles de travail et frontières de confiance.
- `AGENTS.md` : s'il existe déjà chez le propriétaire, ses consignes priment sur ces propositions; sinon l'overlay peut en ajouter un sans remplacement.
- `PROFIL_INGENIERIE.md` : optionnel, uniquement après exécution réelle de RepoSurveyor sur un dépôt local et accord explicite pour sa copie.
- Le Framework Kristal v11 est un standard documentaire **facultatif** : lire le profil réellement verrouillé, sans imposer de migration.
