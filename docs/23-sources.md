# 23 — Sources et provenance documentaire

## Origine des décisions

Les exigences produit viennent de la conversation fournie : tous publics, cas concrets et urgence comme parcours de référence ; chercheurs contributeurs ; cible incluant traitements ; aucun partenaire/dataset actuel ; trois modes dont payant facultatif ; priorité au code. Les décisions de stack et DTO sont des propositions techniques de cette référence, pas des choix antérieurs prétendument approuvés par l'utilisateur.

## Snapshots consultés

- `Code_snapshot_MediKristal.zip` : README, document fondateur, sources d'information.
- `Code_snapshot_kOA_Digital_Ecosystem(5).zip` : composants, autorité et contrats de septembre 2026.
- `Code_snapshot_kristal-framework(7).zip` et `Code_snapshot_Kristal.zip` : schemas v5, release rc.2, référence et documentation.
- `Code_snapshot_Konnaxion(20260922-111642).zip` : README, AGENTS, autorité documentaire et frontières.

Les fichiers originaux ne sont pas modifiés. `source-snapshots.json` fournit leurs empreintes calculées. Les anciens textes contiennent exemples conceptuels et divergences ; voir chapitre 14. Aucun code Orgo/Koali/kOA-Linux complet n'a été fourni, aucune qualification MediKristal n'est inférée.

## Sources externes primaires consultées

Consultation documentaire le 22 septembre 2026 et dans les tours précédents de cette conversation. La date n'est pas une preuve de validation du logiciel ou de droit de redistribution. Les URL servent à vérifier fonctionnalités et conditions ; les références sont paraphrasées brièvement, les contenus externes ne sont pas redistribués dans ce dossier.

| Source | URL | Utilité |
|---|---|---|
| SNOMED concept model | https://docs.snomed.org/snomed-ct-practical-guides/snomed-ct-starter-guide/6-snomed-ct-concept-model | Concepts et procédures |
| SNOMED licensing | https://www.snomed.org/licensing | Droits distincts du logiciel |
| SNOMED Canada | https://www.snomed.org/members/canada | Distribution canadienne |
| LOINC scope | https://loinc.org/kb/users-guide/introduction/scope-of-loinc | Observations et analyses |
| pCLOCD | https://accelero.infoway-inforoute.ca/en/standards/terminology-standards/pclocd | Référentiel canadien |
| CCDD | https://open.canada.ca/data/dataset/3e0a7b9e-a5e9-4131-bde4-ac685a1f1a38 | Médicaments canadiens |
| ICIS classifications | https://www.cihi.ca/en/submit-data-and-view-standards/codes-classifications-and-terminologies | ICD-10-CA/CCI |
| UMLS | https://www.nlm.nih.gov/research/umls/index.html | Liaison de vocabulaires |
| HPO annotations | https://human-phenotype-ontology.github.io/2018/05/02/annotation-format.html | Format historique de fréquences ; vérifier format courant avant import |
| Orphadata | https://www.orphadata.com/docs/OrphadataFreeAccessProductsDescription.pdf | Maladies rares/phénotypes |
| Cochrane DTA | https://www.cochrane.org/about-us/news/what-are-diagnostic-test-accuracy-reviews | Précision diagnostique |
| AHRQ métriques | https://www.ncbi.nlm.nih.gov/books/NBK98249/ | Sensibilité, spécificité, vraisemblance |
| MIMIC-IV | https://physionet.org/content/mimiciv/3.1/ | Exemple dataset sous accès contrôlé |
| OMS SMART | https://www.who.int/teams/digital-health-and-innovation/smart-guidelines | Structuration de recommandations |
| FHIR ConceptMap R5 | https://hl7.org/fhir/R5/conceptmap.html | Correspondances contextuelles ; ne pas copier champs R5 dans R4 |
| FHIR clinical reasoning | https://www.hl7.org/fhir/clinicalreasoning-module.html | Ressources de connaissance |
| CQL | https://cql.hl7.org/ | Langage et gestion du manque ; épingler version à l'implémentation |
| CQF | https://github.com/cqframework/clinical-reasoning | Composants FHIR/CQL, Apache 2.0 déclaré |
| CQF guide | https://www.cqframework.org/clinical-reasoning/developer-guide/ | Adaptateurs versionnés |
| HAPI FHIR | https://github.com/hapifhir/hapi-fhir | Infrastructure FHIR, Apache 2.0 déclaré |
| Snowstorm | https://github.com/IHTSDO/snowstorm | Serveur terminologique, Apache 2.0 déclaré |
| pgmpy | https://github.com/pgmpy/pgmpy | Moteur probabiliste générique, MIT déclaré |
| OR-Tools | https://github.com/google/or-tools | Solveur local, Apache 2.0 déclaré |
| OR-Tools scheduling | https://developers.google.com/optimization/scheduling | Exemples d'affectation génériques |
| Bahmni appointments | https://github.com/Bahmni/openmrs-module-appointments | Module rendez-vous dépendant OpenMRS |
| LIRICAL license | https://github.com/TheJacksonLaboratory/LIRICAL/blob/master/LICENSE | Licence spécifique restrictive consultée : non retenu comme dépendance libre |
| Biolink Model | https://arxiv.org/abs/2203.13906 | Modèle biomédical à comparer pour relations de recherche |

## Réutilisation et licences

Les licences citées sont celles déclarées dans les dépôts consultés. Épingler et vérifier le fichier de licence de la version réellement intégrée, ses dépendances et ses données. Pas de copie de LIRICAL comme composant libre : la licence consultée limite notamment l'usage au non-commercial et les modifications. L'accès gratuit d'une source n'autorise pas automatiquement un pack redistribuable.

## Limite des recherches

La recherche n'établit pas l'absence mondiale d'un produit similaire, ni la conformance des composants à tous les besoins MediKristal. Aucun pourcentage de code « déjà fait » n'est affirmé. L'intégration et la maintenance doivent être mesurées par prototype.
