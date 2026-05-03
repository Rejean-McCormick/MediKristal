# MediKristal Information Sources

**Purpose:** define the free or no-cost medical information sources that MediKristal can use to build its semantic medical knowledge graph, protocol engine, and offline runtime packs.

> MediKristal should not invent medical knowledge. It should compile, normalize, link, validate, and cite trusted medical sources.

---

## 1. Source Strategy

MediKristal separates medical information into five source categories:

```text
1. Clinical concepts
2. Diseases / diagnoses
3. Tests / observations
4. Medications / treatments
5. Clinical guidelines / protocols
```

Each category should be linked to an official terminology, database, or guideline source whenever possible.

---

## 2. Primary Free / No-Cost Sources

| MediKristal Layer                  | Preferred Source                 | Use in MediKristal                                                              |
| ---------------------------------- | -------------------------------- | ------------------------------------------------------------------------------- |
| Symptoms, signs, clinical concepts | SNOMED CT / SNOMED CT CA         | Standard codes for symptoms, signs, procedures, findings, and clinical concepts |
| Diseases / diagnoses               | ICD-11, SNOMED CT                | Diagnosis classification and condition mapping                                  |
| Tests / observations               | LOINC, pCLOCD                    | Laboratory tests, measurements, clinical observations                           |
| Canadian medications               | CCDD, Health Canada DPD          | Canadian drug names, products, codes, and availability                          |
| International / US medications     | RxNorm                           | Normalized clinical drug names and identifiers                                  |
| Clinical protocols                 | WHO, NICE, CDC, local guidelines | Source material for deterministic rules and protocols                           |
| Rules / logic format               | CQL, FHIR Clinical Reasoning     | Machine-readable clinical decision logic                                        |

---

## 3. SNOMED CT / SNOMED CT CA

**Role in MediKristal:** symptoms, signs, findings, procedures, body structures, clinical concepts, and some conditions.

SNOMED CT is the main source for structured clinical terminology. The Canadian Edition includes Canadian English, Canadian French, and Canadian value sets, and is released quarterly. Canada Health Infoway states that SNOMED CT, LOINC, and Infoway software tools are available at no cost to users with an active Infoway account. ([InfoCentral][1])

Use SNOMED CT for:

```text
symptom:fever
symptom:chest_pain
sign:hypotension
finding:low_oxygen_saturation
procedure:physical_exam
condition:pneumonia
```

**MediKristal usage rule:** SNOMED CT should be the preferred terminology for clinical concepts, but the system must store source version, edition, jurisdiction, and license metadata.

---

## 4. ICD-11

**Role in MediKristal:** disease classification and diagnosis grouping.

ICD-11 is the World Health Organization’s international classification for diagnostic health information. WHO provides an ICD API for programmatic access, and ICD-11 is licensed under Creative Commons Attribution-NoDerivs 3.0 IGO. ([ICD-11][2])

Use ICD-11 for:

```text
diagnosis classification
disease grouping
billing / reporting alignment
mapping conditions to global identifiers
```

**MediKristal usage rule:** ICD-11 should classify diseases, but it should not be the only source for clinical reasoning. Protocol logic should come from guidelines, not from ICD codes alone.

---

## 5. LOINC

**Role in MediKristal:** laboratory tests, observations, measurements, panels, and clinical documents.

LOINC identifies health measurements, observations, and documents. It is available worldwide at no cost, and the LOINC database can be downloaded for free with a LOINC login. ([LOINC][3])

Use LOINC for:

```text
CBC
creatinine
urinalysis
blood glucose
oxygen saturation
blood pressure observations
lab panels
```

**MediKristal usage rule:** LOINC should be the preferred identifier for tests and observations. MediKristal should store units, normal ranges, jurisdictional ranges, and interpretation rules separately.

---

## 6. pCLOCD

**Role in MediKristal:** Canadian laboratory and observation coding.

For Canada-focused deployments, pCLOCD can complement LOINC. Infoway has migrated terminology content such as SNOMED CT CA, pCLOCD, CCDD, and value sets to its FHIR Terminology Server. ([InfoCentral][4])

Use pCLOCD for:

```text
Canadian lab terminology
Canadian observation mappings
local laboratory interoperability
```

**MediKristal usage rule:** use pCLOCD when the deployment is Canadian and needs compatibility with Canadian lab systems.

---

## 7. Health Canada Drug Product Database

**Role in MediKristal:** Canadian drug products authorized for sale.

Health Canada’s Drug Product Database lists drugs authorized for sale in Canada, is updated nightly, and includes product availability and product monographs for human drugs. Health Canada also provides a DPD API that returns data in JSON and XML. ([Canada][5])

Use Health Canada DPD for:

```text
Canadian drug products
brand names
active ingredients
DINs
market status
product monographs
human drug availability in Canada
```

**MediKristal usage rule:** DPD should be used for Canadian product availability and official product-level drug information.

---

## 8. Canadian Clinical Drug Data Set

**Role in MediKristal:** Canadian medication terminology.

The Canadian Clinical Drug Data Set provides codes and a consistent naming approach for medications and some medical devices in Canada. It is freely available for use in digital health solutions and application design. ([InfoCentral][6])

Use CCDD for:

```text
standard Canadian medication names
medication coding
clinical drug representation
Canadian e-prescribing interoperability
```

**MediKristal usage rule:** CCDD should be preferred for normalized Canadian medication terminology; DPD should be used for Health Canada product authorization and product details.

---

## 9. RxNorm

**Role in MediKristal:** normalized drug names and identifiers, especially for US or international interoperability.

RxNorm provides normalized names for clinical drugs and links them to many drug vocabularies. The U.S. National Library of Medicine states that it does not charge for RxNorm licensing, although some non-RxNorm source data may require separate licensing. The RxNorm API generally does not require a license, subject to terms of service. ([National Library of Medicine][7])

Use RxNorm for:

```text
normalized clinical drug names
ingredient / strength / dose form modeling
cross-system drug interoperability
mapping medication concepts
```

**MediKristal usage rule:** RxNorm is useful for international interoperability, but Canadian deployments should also use CCDD and Health Canada DPD.

---

## 10. Clinical Guidelines and Protocol Sources

**Role in MediKristal:** source material for deterministic rules.

Terminologies tell MediKristal what things are called. Guidelines tell MediKristal what should be done.

Potential free or public guideline sources include:

| Source                        | Use                                                           |
| ----------------------------- | ------------------------------------------------------------- |
| WHO Guidelines                | global public health and clinical recommendations             |
| NICE / NICE CKS               | primary care summaries and evidence-based guidance            |
| CDC Guidance                  | public health, infection control, infectious disease guidance |
| Local / provincial guidelines | jurisdiction-specific clinical protocols                      |

WHO defines its guidelines as information products containing recommendations for clinical practice or public health policy. NICE provides evidence-based recommendations for health and social care, and NICE CKS provides accessible summaries for primary care. CDC publishes guidance and recommendations across public health and clinical safety domains. ([World Health Organization][8])

**MediKristal usage rule:** guidelines should be transformed into explicit, versioned, source-backed protocol rules. The original source, publication date, jurisdiction, and applicability must always be retained.

---

## 11. Clinical Logic Standards

**Role in MediKristal:** machine-readable protocol execution.

MediKristal should support deterministic protocol logic using standards such as:

```text
FHIR Clinical Reasoning
CQL
PlanDefinition
ActivityDefinition
Library
ValueSet
```

Clinical Quality Language is a domain-specific language focused on clinical quality and decision support artifacts. HL7 FHIR also includes a Clinical Reasoning module for representing and applying clinical knowledge artifacts. ([FHIR Build][9])

**MediKristal usage rule:** protocol logic should eventually be represented in CQL/FHIR-compatible structures where possible, while simple MVP rules may begin as JSON IF/THEN rules.

---

## 12. Source Metadata Required by MediKristal

Every imported source must be recorded with metadata.

```json
{
  "source_id": "source:loinc",
  "source_name": "LOINC",
  "source_type": "terminology",
  "publisher": "Regenstrief Institute",
  "version": "2.82",
  "jurisdiction": "international",
  "access_model": "free_with_account",
  "license": "LOINC license",
  "retrieved_at": "2026-05-02",
  "used_for": ["tests", "observations", "measurements"]
}
```

Minimum required fields:

```text
source_id
source_name
publisher
version
license_or_terms
retrieved_at
jurisdiction
language
used_for
```

---

## 13. Source Trust Tiers

MediKristal should classify sources by trust tier.

```text
Tier 1 — Official terminology or government source
Examples: SNOMED CT, ICD-11, LOINC, Health Canada DPD, CCDD, RxNorm

Tier 2 — Official guideline source
Examples: WHO, NICE, CDC, provincial guidelines

Tier 3 — Institutional protocol
Examples: hospital-specific order sets, clinic protocols

Tier 4 — Working / draft source
Examples: internal mappings, experimental rules, community proposals
```

Only Tier 1 and Tier 2 sources should be eligible for canonical clinical content by default.

---

## 14. What These Sources Do Not Provide

These databases do **not** automatically create a complete diagnostic engine.

They provide:

```text
standard names
codes
identifiers
classifications
drug records
test identifiers
guideline text
```

MediKristal must still create and validate:

```text
symptom-to-disease relationships
disease-to-test rules
test interpretation rules
contraindication logic
red flag rules
clinical protocols
jurisdiction-specific workflows
```

---

## 15. Foundational Rule

**MediKristal must never treat a database entry as a clinical recommendation unless that recommendation is backed by a guideline, protocol, or validated clinical rule.**

Terminology is not protocol.

```text
SNOMED / ICD / LOINC / RxNorm / CCDD = names and codes
Guidelines / protocols / CQL rules = clinical action
MediKristal = orchestration, validation, traceability, execution
```

---

## 16. Recommended First Source Stack

For a Canadian-first MVP:

```text
Clinical concepts: SNOMED CT CA
Diseases: ICD-11 + SNOMED CT CA
Tests: LOINC + pCLOCD
Medications: CCDD + Health Canada DPD
Protocols: WHO + NICE + Canadian/provincial guidelines
Logic: JSON rules first, then CQL/FHIR Clinical Reasoning
```

For an international MVP:

```text
Clinical concepts: SNOMED CT
Diseases: ICD-11
Tests: LOINC
Medications: RxNorm
Protocols: WHO + NICE + CDC
Logic: JSON rules first, then CQL/FHIR Clinical Reasoning
```

---

## 17. One-Sentence Summary

**MediKristal uses free or no-cost official medical terminologies, drug databases, and guideline sources as raw knowledge inputs, then normalizes them into versioned semantic artifacts and deterministic clinical protocols with full source traceability.**

[1]: https://infocentral.infoway-inforoute.ca/en/standards/canadian/snomed-ct?utm_source=chatgpt.com "SNOMED CT CA / SNOMED CT - InfoCentral"
[2]: https://icd.who.int/?utm_source=chatgpt.com "ICD-11"
[3]: https://loinc.org/?utm_source=chatgpt.com "LOINC: Home"
[4]: https://infocentral.infoway-inforoute.ca/en/tools/standards-tools/terminology-gateway?utm_source=chatgpt.com "Terminology Gateway - InfoCentral - Canada Health Infoway"
[5]: https://www.canada.ca/en/health-canada/services/drugs-health-products/drug-products/drug-product-database.html?utm_source=chatgpt.com "Drug Product Database: Access the database"
[6]: https://infocentral.infoway-inforoute.ca/en/standards/canadian/ccdd?utm_source=chatgpt.com "Canadian Clinical Drug Data Set - InfoCentral"
[7]: https://www.nlm.nih.gov/research/umls/rxnorm/index.html?utm_source=chatgpt.com "RxNorm - National Library of Medicine - NIH"
[8]: https://www.who.int/publications/who-guidelines?utm_source=chatgpt.com "WHO Guidelines"
[9]: https://build.fhir.org/ig/HL7/cql/?utm_source=chatgpt.com "Clinical Quality Language (CQL)"
