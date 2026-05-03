# Foundational Document — Medikristal Architecture

**Working name:** Medikristal
**Type:** medical knowledge architecture, protocol engine, and semantic data format
**Status:** foundational draft
**Purpose:** define an application that orchestrates existing medical knowledge bases — symptoms, diseases, tests, medications/remedies — through a semantic graph, deterministic protocols, and verifiable knowledge artifacts.

This architecture is inspired by your Kristal model: portable, verifiable, traceable, Wikidata/Wikibase-aligned knowledge artifacts that can be executed offline.  It also adopts the Kristal v5 distinction between “working” knowledge and “canonical” promoted knowledge. 

---

## 1. Vision

Medikristal is a system for turning structured medical knowledge into a consultable, verifiable, protocol-driven application.

The goal is **not** to build an AI that guesses diagnoses.
The goal is to build a **deterministic orchestrator** that connects:

```text
Patient → clinical context → symptoms → possible diseases → tests → results → protocols → treatments
```

The system does not replace clinical judgment. It organizes medical knowledge into explicit, traceable, reviewable, versioned, and machine-readable structures.

---

## 2. Core principle

Medicine should be represented as a **relationship graph**, not merely as four separate databases.

The four core databases are:

```text
1. Symptoms / signs
2. Diseases / diagnoses
3. Tests / investigations
4. Medications / remedies / treatments
```

But the system also needs a fifth layer:

```text
5. Patient context
```

Age, sex, pregnancy, allergies, medical history, ethnicity, geography, travel, kidney function, liver function, and risk factors are not symptoms. They are **clinical modifiers**.

So instead of putting “80 years old” inside the symptom database, Medikristal stores it as:

```text
patient_context.age = 80
```

Then protocols use that value to modify recommendations.

Example:

```text
IF age > 75
AND symptom = acute confusion
AND temperature = elevated
THEN increase priority of:
- infection
- sepsis
- pneumonia
- urinary tract infection
- dehydration
- medication adverse effect
```

---

## 3. Short definition

**Medikristal is a structured medical knowledge compilation system that transforms validated medical sources into semantic, versioned, queryable, and protocol-executable artifacts.**

It separates:

```text
Medical knowledge
≠
Clinical protocol
≠
Patient data
≠
Final medical decision
```

---

## 4. General architecture

```text
┌────────────────────────────────────┐
│ Medical sources                    │
│ SNOMED, ICD, LOINC, drug databases,│
│ guidelines, institutional protocols│
└───────────────┬────────────────────┘
                │
                ▼
┌────────────────────────────────────┐
│ Semantic normalization             │
│ codes, synonyms, units, relations  │
└───────────────┬────────────────────┘
                │
                ▼
┌────────────────────────────────────┐
│ Medikristal medical graph          │
│ symptoms ↔ diseases ↔ tests ↔      │
│ treatments ↔ patient context       │
└───────────────┬────────────────────┘
                │
                ▼
┌────────────────────────────────────┐
│ Protocol engine                    │
│ deterministic rules, trees,        │
│ thresholds, contraindications      │
└───────────────┬────────────────────┘
                │
                ▼
┌────────────────────────────────────┐
│ Clinical output                    │
│ possibilities, tests to consider,  │
│ red flags, protocols, sources      │
└────────────────────────────────────┘
```

The engine does not “think.”
It applies explicit, auditable rules.

---

## 5. The five data layers

### 5.1 Patient Context Layer

Contains what is known about the person.

```json
{
  "patient_context": {
    "age": 80,
    "sex": "female",
    "pregnancy_status": "not_applicable",
    "allergies": ["penicillin"],
    "known_conditions": ["chronic_kidney_disease"],
    "medications_current": ["warfarin"],
    "geography": "Quebec",
    "recent_travel": false
  }
}
```

This layer does not contain possible diagnoses.
It contains patient-specific facts.

---

### 5.2 Symptoms / Signs Layer

Contains what the patient reports or what the clinician observes.

```json
{
  "symptom_observation": {
    "code": "symptom:fever",
    "label": "fever",
    "onset": "acute",
    "duration": "2 days",
    "severity": "moderate",
    "certainty": "reported",
    "source": "patient"
  }
}
```

A symptom can be subjective:

```text
pain, fatigue, nausea
```

A sign can be objective:

```text
temperature 39°C, oxygen saturation 88%, low blood pressure
```

---

### 5.3 Diseases / Diagnoses Layer

Contains diseases, syndromes, differential diagnoses, and clinical conditions.

```json
{
  "condition": {
    "code": "condition:pneumonia",
    "label": "pneumonia",
    "category": "infectious_disease",
    "typical_symptoms": [
      "symptom:cough",
      "symptom:fever",
      "symptom:dyspnea"
    ],
    "risk_modifiers": [
      "patient_context:age_over_65",
      "condition:copd"
    ]
  }
}
```

A disease is not only a label.
It is linked to symptoms, tests, criteria, treatments, complications, exclusions, and risk modifiers.

---

### 5.4 Tests / Investigations Layer

Contains available tests, their indications, limits, and interpretation rules.

```json
{
  "test": {
    "code": "test:chest_xray",
    "label": "chest X-ray",
    "type": "imaging",
    "used_for": ["condition:pneumonia"],
    "indicated_when": [
      "symptom:dyspnea",
      "symptom:fever",
      "sign:low_oxygen_saturation"
    ],
    "contraindications": [],
    "interpretation_model": "protocol:pneumonia_initial_workup"
  }
}
```

Tests are not just names.
They have conditions of use.

---

### 5.5 Medications / Remedies / Treatments Layer

Contains medications, non-drug treatments, doses, contraindications, interactions, and adjustments.

```json
{
  "treatment": {
    "code": "drug:amoxicillin",
    "label": "amoxicillin",
    "type": "antibiotic",
    "treats": ["condition:pneumonia"],
    "contraindicated_if": ["allergy:penicillin"],
    "dose_adjustment_if": ["condition:chronic_kidney_disease"],
    "interaction_risks": ["drug:warfarin"]
  }
}
```

The “remedies” database should include:

```text
medications
doses
forms
contraindications
interactions
dose adjustments
non-drug treatments
protocol references
```

---

## 6. The semantic graph

The core of the system is a graph.

```text
Fever
  may_indicate → Pneumonia
  may_indicate → Urinary tract infection
  may_indicate → Meningitis

Pneumonia
  typical_symptom → Cough
  typical_symptom → Fever
  initial_test → Chest X-ray
  initial_test → Oxygen saturation
  possible_treatment → Antibiotic
  urgent_if → Low oxygen saturation

Amoxicillin
  treats → Bacterial pneumonia
  contraindicated_if → Penicillin allergy
  adjust_dose_if → Kidney impairment
```

This graph can be represented in an RDF / Wikidata / Wikibase-like format.

Conceptual example:

```text
Q:Fever
P:may_indicate
Q:Pneumonia

Q:Pneumonia
P:recommended_test
Q:Chest_Xray

Q:Amoxicillin
P:contraindicated_if
Q:Penicillin_allergy
```

---

## 7. Foundational data format

The base unit of Medikristal is the:

```text
Clinical Epistemic State
```

This is the medical equivalent of Kristal v5’s **Structured Epistemic State**: a structured, versioned, traceable object that carries uncertainty, status, and provenance. 

### 7.1 Minimal example

```json
{
  "artifact_type": "clinical_epistemic_state",
  "artifact_version": "0.1",
  "artifact_id": "sha256:...",
  "scope": {
    "domain": "medicine",
    "subdomain": "respiratory",
    "jurisdiction": "CA-QC",
    "language": "en"
  },
  "status": "draft",
  "certainty": "partial",
  "created_at": "2026-05-02T00:00:00Z",
  "created_by": "authority:medikristal-core",
  "assertions": [],
  "provenance": [],
  "review_refs": [],
  "policy_refs": []
}
```

---

## 8. Medical assertion

A medical assertion is a verifiable medical relationship.

```json
{
  "assertion_id": "assertion:pneumonia-fever-001",
  "subject": "condition:pneumonia",
  "predicate": "has_common_symptom",
  "object": "symptom:fever",
  "qualifiers": {
    "population": "adult",
    "frequency": "common",
    "certainty": "high"
  },
  "provenance_refs": ["source:guideline-001"],
  "status": "under_review"
}
```

Each assertion must be:

```text
structured
sourced
versioned
reviewable
validatable
revocable if outdated
```

---

## 9. Deterministic medical protocol

A protocol is a rule or decision tree.

```json
{
  "protocol_id": "protocol:adult_pneumonia_initial_assessment",
  "protocol_version": "1.0",
  "applies_to": {
    "age_min": 18,
    "suspected_conditions": ["condition:pneumonia"]
  },
  "triggers": [
    {
      "if": [
        { "symptom": "symptom:fever" },
        { "symptom": "symptom:cough" },
        { "symptom": "symptom:dyspnea" }
      ],
      "then": [
        { "recommend_test": "test:oxygen_saturation" },
        { "recommend_test": "test:chest_xray" },
        { "consider_condition": "condition:pneumonia" }
      ]
    }
  ],
  "red_flags": [
    {
      "if": [
        { "sign": "sign:oxygen_saturation_low" },
        { "patient_context": "age_over_75" }
      ],
      "then": [
        { "urgency": "urgent_evaluation" }
      ]
    }
  ],
  "provenance_refs": ["source:guideline-001"],
  "status": "under_review"
}
```

The protocol must not be hidden in free text.
It must be machine-readable.

---

## 10. Working knowledge vs canonical knowledge

Medikristal should support three levels:

```text
1. Draft / working
2. Locally validated
3. Canonical / promoted
```

This is a central Kristal v5 idea: an artifact may be compiled before it is canonical, but promotion to canonical status is a separate governed step. 

Medical example:

```text
The relationship “fever → pneumonia” may exist in the graph.

But it can have a status:
- draft
- under_review
- disputed
- working_accepted
- canonical
- revoked
```

This allows the system to grow without pretending that everything is fully validated from the start.

---

## 11. Trust statuses

Every medical element should have a status.

```text
draft              preliminary
under_review       being reviewed
partial            incomplete
disputed           contested
working_accepted   accepted for internal use
promoted           promoted by policy
canonical          canonical for a given trust surface
revoked            withdrawn
```

The key distinction is:

```text
exists in the system
≠
trusted for clinical use
≠
canonical medical knowledge
```

---

## 12. Complete pipeline

```text
1. Import medical sources
   guidelines, drug databases, terminologies, protocols

2. Normalize
   synonyms, codes, units, languages, jurisdictions

3. Create assertions
   symptom → disease
   disease → test
   test → interpretation
   disease → treatment
   medication → contraindication

4. Compile into a working artifact
   usable graph, not necessarily canonical

5. Validate
   schemas, sources, coherence, conflicts, safety

6. Review
   humans, experts, governance rules

7. Promote
   artifact becomes canonical for a defined context

8. Distribute
   executable pack, local or offline

9. Use
   protocol engine + clinical interface

10. Continuously revise
   new sources, errors, changed recommendations
```

---

## 13. Protocol engine

The protocol engine receives:

```text
patient_context
+ symptoms
+ signs
+ test results
+ current medications
+ allergies
```

It queries:

```text
medical graph
+ protocols
+ contraindications
+ emergency rules
```

It outputs:

```text
diagnoses to consider
tests to consider
red flags
possible treatments
contraindications
interactions
justification
sources
```

Example:

```text
Input:
- age: 80
- fever
- confusion
- hypotension

Output:
- red flag: possible sepsis
- tests to consider: complete vital signs, lactate, CBC, cultures, urinalysis, imaging depending on source
- possible diagnoses: urinary tract infection, pneumonia, sepsis, dehydration, medication adverse effect
- urgency: rapid medical evaluation
- justification: protocol X, source Y
```

---

## 14. What Medikristal is not

Medikristal is not:

```text
an AI that invents diagnoses
a replacement for physicians
a closed proprietary medical database
a simple medical wiki
a medical chatbot
an opaque probabilistic engine
```

Medikristal is:

```text
a structured medical knowledge system
a relationship engine
a rule engine
a medical artifact compiler
a traceability and protocol system
```

---

## 15. Offline execution

The system should be able to run without requiring a live server for every query.

Kristal already defines the idea of runtime packs: compiled, indexed, offline-executable knowledge artifacts. 

In Medikristal, a device could contain:

```text
symptom pack
disease pack
test pack
medication pack
protocol pack
search index
validation rules
```

This enables use in low-connectivity settings, rural clinics, field medicine, institutional networks, or offline-first deployments.

---

## 16. Validation

Validation must be explicit.

There are several levels:

```text
Structural validation:
the file follows the schema

Semantic validation:
the relationships make sense

Clinical validation:
the source is acceptable

Safety validation:
no dangerous recommendation without conditions

Protocol validation:
rules are complete and non-contradictory
```

Examples:

```text
ERROR:
medication recommended despite known allergy

WARNING:
test recommended but unavailable in this jurisdiction

INFO:
protocol applies only to adults
```

---

## 17. Governance

Medikristal must separate roles.

```text
Author:
proposes an assertion or protocol

Validator:
checks structure and consistency

Clinical expert:
approves or rejects clinical content

Promoter:
grants canonical status

Distributor:
publishes runtime packs

User:
consults protocols
```

This follows the Kristal v5 separation of responsibilities: workflow/control plane, truth/artifact plane, and distribution/runtime plane. 

---

## 18. Module architecture

```text
Medikristal Core
│
├── Terminology Resolver
│   ├── synonyms
│   ├── medical codes
│   └── multilingual alignment
│
├── Medical Graph Store
│   ├── symptoms
│   ├── diseases
│   ├── tests
│   ├── medications
│   └── relations
│
├── Protocol Engine
│   ├── IF/THEN rules
│   ├── decision trees
│   ├── red flags
│   └── contraindications
│
├── Validation Engine
│   ├── schema validation
│   ├── SHACL/ShEx-style validation
│   ├── clinical coherence
│   └── conflict detection
│
├── Promotion System
│   ├── review
│   ├── approval
│   ├── canonical status
│   └── revocation
│
├── Runtime Pack Compiler
│   ├── symptom pack
│   ├── disease pack
│   ├── test pack
│   ├── medication pack
│   └── protocol pack
│
└── Clinical UI
    ├── patient input
    ├── protocol consultation
    ├── justification
    └── sources
```

---

## 19. Example query

### Input

```json
{
  "patient_context": {
    "age": 80,
    "sex": "male",
    "known_conditions": ["condition:chronic_kidney_disease"],
    "current_medications": ["drug:warfarin"]
  },
  "observations": [
    { "type": "symptom", "code": "symptom:fever" },
    { "type": "symptom", "code": "symptom:confusion" },
    { "type": "sign", "code": "sign:hypotension" }
  ]
}
```

### Output

```json
{
  "red_flags": [
    {
      "code": "red_flag:possible_sepsis",
      "urgency": "urgent",
      "reason": "fever + confusion + hypotension in older adult"
    }
  ],
  "conditions_to_consider": [
    "condition:sepsis",
    "condition:urinary_tract_infection",
    "condition:pneumonia",
    "condition:dehydration",
    "condition:adverse_drug_event"
  ],
  "tests_to_consider": [
    "test:vital_signs",
    "test:cbc",
    "test:creatinine",
    "test:urinalysis",
    "test:blood_culture",
    "test:chest_xray"
  ],
  "treatment_warnings": [
    {
      "code": "warning:renal_dose_adjustment",
      "reason": "known chronic kidney disease"
    },
    {
      "code": "warning:drug_interaction_check",
      "reason": "current warfarin use"
    }
  ]
}
```

---

## 20. Recommended MVP

The MVP should not attempt to cover all of medicine.

Possible first domains:

```text
Option A: urinary tract infections
Option B: respiratory symptoms
Option C: chest pain
Option D: medications and contraindications in older adults
Option E: clinical red flags and initial tests
```

The strongest MVP would likely be:

```text
Medikristal — Red Flags + Initial Tests
```

This is useful, bounded, and safer than immediately recommending treatments.

---

## 21. Foundational rules

1. **No recommendation without a source.**

2. **No source without a version.**

3. **No rule without a status.**

4. **No canonical content without promotion.**

5. **No opaque protocol.**

6. **No automated final medical decision.**

7. **Every output must be justifiable.**

8. **Every artifact must be versioned.**

9. **Every contradiction must be visible.**

10. **The system must separate knowledge, protocol, patient context, and clinical decision.**

---

## 22. One-sentence summary

**Medikristal is a semantic medical knowledge architecture that compiles relationships between symptoms, diseases, tests, treatments, and patient context into verifiable artifacts, then applies deterministic protocols to guide clinical investigation without replacing medical judgment.**
