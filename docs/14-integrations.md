# 14 — FHIR, Kristal et écosystème

## Principe

MediKristal reste propriétaire de ses états métier locaux. Les produits étrangers conservent leurs propres états. Les échanges portent commandes explicites, résultats, snapshots immuables et références ; jamais une base partagée ni une permission d'écrire des tables étrangères.

## FHIR

Baseline de conception de l'adaptateur initial : FHIR R4 4.0.1, à confirmer avec les versions retenues du moteur et de l'établissement au lot L0. R5 est un adaptateur distinct ; ne pas mélanger champs R4/R5. Le noyau conserve des types indépendants de FHIR. Les profils locaux/québécois ne sont pas inventés : importer leur définition exacte avant d'affirmer la conformance.

| Domaine MediKristal | Ressources candidates |
|---|---|
| Identité/contexte | Patient, Encounter, Practitioner, Organization |
| Observations/résultats | Observation, DiagnosticReport, Specimen |
| Conditions documentées | Condition avec statuts appropriés |
| Médicaments/allergies | Medication, MedicationStatement, AllergyIntolerance |
| Demande d'acte | ServiceRequest |
| Prescription autorisée | MedicationRequest |
| Disponibilité/rendez-vous | Schedule, Slot, Appointment |
| Protocoles et règles | PlanDefinition, ActivityDefinition, Library |
| Terminologies | CodeSystem, ValueSet, ConceptMap |
| Traçabilité | Provenance, AuditEvent |

Une hypothèse calculée n'est pas une Condition confirmée. Une proposition de médicament n'est pas MedicationRequest autorisée. Les ressources candidates sont des mappings à qualifier. Lire CapabilityStatement, profils et opérations réels du serveur ; les ressources présentes dans la norme ne prouvent pas leur support distant. Stocker original, références, version et pertes éventuelles de conversion. Un mapping avec perte critique bloque exécution.

CQL/ELM : conserver source, compilation, dépendances terminologiques et version du moteur. Aucun support « tout CQL » sans tests. Les capacités sélectionnées font l'objet de fixtures positives/négatives. Les serveurs Snowstorm/HAPI et CQF sont des composants candidats, pas des dépendances déjà qualifiées de MediKristal.

## Kristal : constat du snapshot

Le snapshot fourni annonce framework `5.0.0-rc.2`, core `5.0`. Le champ commit de release est null ; ne pas inventer un commit définitif. `kristal-reference` implémente notamment identité/vérification Exchange et Runtime Pack. Ce n'est pas la preuve d'une compilation médicale complète.

Le schéma fourni `structured-epistemic-state.schema.json` exige `schema_version`, `artifact_type`, `state_id`, `artifact_status`, `created_at`, `created_by`, `scope`, `assertions`, `provenance`. `scope.domain` doit utiliser `health` pour ce profil. Le document MediKristal ancien utilise un `clinical_epistemic_state` et `medicine` conceptuels : ils ne sont pas directement conformes. Les exemples narratifs Kristal utilisent parfois `created_by.type/id` alors que le schéma attend notamment `agent_type/agent_id`. L'adaptateur suit le schéma exécutable épinglé et signale toute divergence.

## Profil médical proposé

Identifiant proposé `medikristal:medical-knowledge-profile:1` ; ce nom est interne, non un profil déjà approuvé par Kristal. Le profil décrit concepts médicaux natifs, assertions/qualifiers, EvidenceEstimate, références de modèles/protocoles et contraintes de lecture dans les champs/`extensions` autorisés. Les probabilités patient ne deviennent pas une certitude générale d'assertion.

Étapes : sélectionner contenu partageable ; vérifier droits/absence de données individuelles ; mapper vers Structured Epistemic State ; valider avec schéma exact ; canonicaliser selon profil externe ; vérifier identity/provenance ; émettre artefact ; enregistrer reçu. Un export JSON conforme n'est pas automatiquement un Exchange, Runtime Pack ou contenu reconnu. Les tests de chaque étape sont séparés.

Le manifeste MediKristal de connaissance n'est pas renommé Runtime Pack Kristal. Un adaptateur doit construire/vérifier le format natif ou indiquer cette capacité non implémentée. Le runtime local peut consommer sa propre release ; dans un déploiement kOA, `kristal_runtime` reste propriétaire de l'activation de ses Runtime Packs, et MediKristal ne crée pas une seconde autorité sur cet état.

## Frontières kOA

| Produit | Intégration envisagée | Frontière |
|---|---|---|
| Orgo | Révisions, tâches et suivi | Les tâches appartiennent à Orgo ; décisions médicales/épistémiques restent gouvernées explicitement |
| Konnaxion | Contenus éducatifs partageables et collaboration | Aucun vote ni score EkoH ne valide automatiquement une vérité médicale |
| Koali Spaces | Présentation et navigation | L'activation d'un Space n'active aucun pack ni rôle clinique |
| Da’at | Mapping dans le profil kOA | Préserve propriété de la source et sémantique Kristal |
| Interaction Kernel | Transport si profil adopté | Aucun état métier ni autorisation clinique transféré |
| SenTient | Résolution facultative | Les candidats ambigus restent candidats |
| Architect | Rendu facultatif | Préserve chiffres, limites et statuts |
| kOA-Linux | Hébergement/admission | Ne devient pas propriétaire clinique |

Les snapshots kOA et Konnaxion ne sont pas synchrones sur tous les statuts d'intégration ; la carte kOA du 21 septembre mentionne une qualification Konnaxion↔Orgo alors que des documents Konnaxion plus anciens restent prudents. Aucune de ces preuves ne qualifie MediKristal. Les snapshots Orgo, Koali, Da’at et kOA-Linux complets ne sont pas fournis ici : leurs contrats concrets doivent être obtenus pour implémenter les adaptateurs.

## Authentification

OIDC facultatif pour identité fédérée ; rôle évalué localement. Un compte Konnaxion n'est pas un compte clinique habilité. Pas de partage de tables utilisateurs. Export patient vers un autre produit = finalité, destinataire et grant explicites ; le chemin de publication de savoir ne reçoit pas ces données par défaut.
