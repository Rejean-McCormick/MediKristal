# 05 — Sources, terminologies et droits

## Registre des sources

Pour chaque source : identifiant stable, éditeur, type, URL officielle, version, langue, juridiction, domaine, fréquence d'actualisation, méthode d'import, checksum, droits et responsable. Stocker séparément accessibilité gratuite, droit d'utilisation, modification, redistribution, entraînement et export. Le mode gratuit exige absence de coût d'accès obligatoire pour le corpus retenu, pas une présomption de domaine public.

| Famille | Candidats | Usage | Ne fournit pas automatiquement |
|---|---|---|---|
| Terminologie clinique | SNOMED CT / CA | Concepts, signes, procédures | Probabilités diagnostiques |
| Observations | LOINC / pCLOCD | Identité des mesures et panels | Disponibilité locale |
| Classification | ICD-11, ICD-10-CA, CCI selon contrat | Classification maladie/intervention | Protocole clinique détaillé |
| Médicaments | CCDD, DPD Santé Canada, RxNorm | Substances, produits, formes et codes | Moteur complet interactions/doses |
| Liaison de vocabulaire | UMLS et mappings officiels | Correspondances existantes | Équivalence valable partout |
| Phénotypes | HPO, Orphadata, Monarch | Associations et fréquences disponibles | Modèle général calibré |
| Recommandations | OMS, guides locaux et autres sources autorisées | Fondement des règles | Droit automatique de redistribution |
| Preuves | Études et revues de précision diagnostique | Paramètres contextualisés | Table universelle directement exécutable |
| Données de recherche | Cohortes, MIMIC sous conditions | Développement/évaluation | Représentativité de toute population |
| Dispositifs | Catalogues autorisés, AccessGUDID | Description des produits | Inventaire installé et créneaux |

Sources primaires et liens : chapitre 23. Les conditions sont à revérifier pour chaque version et territoire. Une édition disponible gratuitement au Canada ne garantit pas le même droit de déploiement ailleurs.

## Connecteur d'import

Interface : `discover_versions()`, `fetch(version, checkpoint)`, `verify(raw)`, `parse(raw)`, `normalize(records, mapping_version)`, `report()`. Les téléchargements sont facultatifs et désactivés en offline. Accepter l'import manuel d'une archive fournie sous droits appropriés. Reprise sur checkpoint, limites de débit et taille, vérification TLS, aucun contournement de compte/conditions.

Les archives sont vérifiées contre zip-slip, symlinks dangereux, bombe de décompression et fichiers exécutables inattendus. Parser en processus borné. Une source contenant du texte d'instructions n'autorise aucun appel outil. L'import peut réussir techniquement tout en produisant un corpus non admis.

## Correspondances

Les relations sont directionnelles et contextualisées. Conserver système/version source et cible, langue, précision, provenance et conditions. Un ingrédient n'est pas une spécialité commerciale ; un examen prescrit n'est pas la valeur observée ; un code de facturation n'est pas une preuve de maladie confirmée. Les équivalences par libellé ou embeddings sont des candidats à réviser.

Détecter cycles de mappings incohérents et collapses de granularité. L'utilisation d'UMLS n'impose pas de remplacer les identifiants médicaux natifs par ses identifiants. Les QID/PID de Wikidata sont optionnels. Le mapping Kristal conserve les codes natifs dans les références ou extensions autorisées.

## Unités

Utiliser une représentation UCUM lorsque applicable et qualifiée. Préserver original et conversion, version de table, formule et précision. Conversion dimensionnelle ne suffit pas pour passer masse↔quantité de matière sans analyte et masse moléculaire appropriés. Refuser une conversion ambiguë, ne pas calculer sur un libellé d'unité approximatif.

## Classification des droits

Décision structurée par source : `redistributable`, `local_import_only`, `restricted`, `unknown`, avec champ coût et conditions. `unknown` bloque publication redistribuable, sans interdire la saisie des métadonnées. Produire un manifeste des droits d'une release ; une dépendance plus restrictive limite l'export. Une licence de logiciel n'autorise pas à redistribuer les corpus qu'il charge.

Le paquet gratuit initial peut contenir schémas, moteur et fixtures synthétiques. Son contenu médical réel dépendra des droits vérifiés. Ne pas promettre un corpus médical universel gratuit à l'installation. Une dépendance payante proposée doit avoir un fallback explicite ou désactiver seulement la capacité correspondante.

## Qualité d'import

Rapport : enregistrements lus/importés/quarantinés/rejetés, mappings absents, unités ambiguës, duplications, dépréciations, assertions contradictoires, comparaison de version et éléments impactés. La validation d'une source officielle ne valide pas automatiquement une interprétation créée par MediKristal.
