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

## État de l’intégration Kristal

La spécification 1.1 conserve un historique issu du Framework 5.0.0-rc.2. Ce profil historique ne sert pas de base à un nouvel export. L’API 0.2.0 déclare `kristal_export` et `fhir_partner` non configurés. La route `POST /api/v1/knowledge/exports` vérifie la release puis enregistre une opération échouée avec `capability_unavailable`. Le registre et l’export évolueront ensemble lors de l’implémentation. Voir [l’état du 27 novembre](ETAT_2026-11-27.md).

| Composant du contexte | Version de référence observée | Rôle à la frontière |
| --- | --- | --- |
| Kristal Framework | 11.0.0-draft.4 | Définit les identités sémantiques v11 KQ/KP/KA/KS, leur registre, le crosswalk et les dictionnaires distincts. Le choix du format portable reste une décision de contrat. |
| Kristal Authoring Kit | 4.0.0-draft.4 | Outil d’authoring local. L’adoption de v11 dans un workspace suit sa procédure explicite. |
| Kristal Integration Pack | 0.3.0-alpha.1 | Lecture et validation v11 avec pin exact. Les projections localisées sont dérivées. |
| Arketype | 1.6.0 | La recette `medi-connaissances` décrit une composition hybride candidate pour le savoir, les protocoles et les modèles. Elle sert au design. |

## Premier profil d’export proposé

Traiter `medikristal:medical-knowledge-profile:1` comme un identifiant de travail. Choisir avec le consommateur les objets exportés, le schéma exact, le namespace, le registre d’identités, les fichiers lexicaux et leurs empreintes. Figer la version du mapping. Conserver le code source et sa version. Utiliser un crosswalk pour les correspondances admises. Une ambiguïté reste explicite et bloque le mapping si elle touche une assertion exigée.

Construire une fixture à partir d’une release synthétique et d’une liste de types d’objets autorisés. Écarter cas, identifiants individuels, hypothèses calculées pour un cas et reçus opérationnels, y compris leurs références imbriquées. Vérifier droits, provenance, stabilité du mapping et erreurs avec les outils du profil cible. Rejouer la lecture sur le consommateur choisi, puis archiver la preuve liée à l’empreinte de l’artefact. Tenir distincts export validé, import de workspace, activation d’un Runtime Pack et projection UCKK.

Le graphe sémantique v11 et un format portable tel que `kristal_state` 6.0 suivent des contrats distincts. Le lot n’annonce que la surface effectivement épinglée et testée. Voir [les preuves de sortie du système final](SYSTEME_FINAL.md#ordre-de-réalisation-et-preuves-attendues).

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

Le dossier du 27 novembre fournit du contexte sur les systèmes voisins. Pour brancher un adaptateur, identifier auprès de son propriétaire le contrat exact, le transport, les droits, les versions et les fixtures. Les preuves entre deux autres produits s’appliquent à leur périmètre.

## Authentification

OIDC facultatif pour identité fédérée ; rôle évalué localement. Un compte Konnaxion n'est pas un compte clinique habilité. Pas de partage de tables utilisateurs. Export patient vers un autre produit = finalité, destinataire et grant explicites ; le chemin de publication de savoir ne reçoit pas ces données par défaut.
