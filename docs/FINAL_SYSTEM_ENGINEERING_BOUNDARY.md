# Final-system boundary: MediKristal as an independent medical-domain application

**Status:** `TARGET_DESIGN` with a **synthetic engineering implementation observed in this source snapshot**. **API:** MediKristal `0.2.0`. **Scope:** FC-20 (medical domain), FC-18 (independent software diagnostics), FC-14 (identity/policy) of the kOA Digital Ecosystem architecture.

## Current owner responsibilities

MediKristal owns its application cases, observations, hypotheses, investigations, resources, contributions, synthetic releases, API access rules and durable operational receipts. External adapters may supply reviewed input, but they do not acquire permission to change MediKristal's authoritative data. The default supported use of this distribution is **engineering**, not clinical care. Models and examples operate in the synthetic `urn:medikristal:synthetic` namespace. External partner FHIR, network providers and Kristal export are not proven available in the standalone distribution.

LevelUpDiag-MediKristal is an **independent verifier**. It can inspect an exact MediKristal checkout/ZIP, perform isolated software checks and issue exact-input diagnostic findings. It cannot approve clinical use, authorize publication, deploy a host or grant access to patient information. Diagnostic PASS, coverage percentage and bundle integrity are not clinical qualification or regulatory certification.

## Owner-to-diagnostic interface

| Input/observable | Authoritative owner | Verifier responsibility | Forbidden interpretation |
|---|---|---|---|
| `backend/requirements.lock` | MediKristal release engineer | Check exact pins, extras and linkage to SBOM | A pinned package equals a secure production supply chain |
| `sbom.cdx.json` | MediKristal release engineer | Verify complete lock-derived direct dependencies and SHA-256 of lock bytes | SBOM proves deployment wheel integrity or supplier licensing |
| `manifest.json` | MediKristal release engineer | Verify the **complete** source set and SHA-256, including rejection of omitted files | A partial manifest with correct listed hashes is complete |
| `contracts/*`, `examples/*` | MediKristal contracts owner | Match counts, references, permissions and packaged assets | Valid JSON certifies clinical correctness |
| `/api/v1/capabilities` | MediKristal runtime | Confirm `supported_uses = ["engineering"]`, nonempty limitations and partner states remain `not_configured`/`unavailable` | Any capability may be described as clinically qualified |
| `tests/` and synthetic runtime | MediKristal application | Execute named tests against a pinned checkout and report full/partial/blocked results | A historical test count is fresh evidence |
| Actual PostgreSQL/Docker/partner environment | Authorized operations and clinical institution | Separate environment-specific campaign if provided | An offline smoke test implies production readiness |

**Source archive note:** the snapshot supplied for this branch omitted `backend/requirements.lock`. Its original 142-byte content was exactly reconstructed by combining the pinned CycloneDX component list and its `psycopg[binary]` extra. The recovered file matches the **original source delivery manifest SHA-256** `56d068e00244920e327ef271eb378cc51e92269d18f85e84f4fc9578405ff30e`. This is an integrity recovery, not an upgrade of dependencies.

## Minimum final acceptance

1. Owner source dependency lock, SBOM and source manifest pass the read-only `python tools/check_delivery_integrity.py` check.
2. Independent LevelUpDiag checks verify both manifest **completeness** and the absence of prohibited/unsupported clinical claims in the actual isolated capabilities response.
3. Product behavioral/permission tests use synthetic fixtures without real patient data and include malformed import, wrong tenant, absent external adapters and uncertain external effect paths.
4. No owner grants real-patient use, clinical performance assertions, regulatory readiness or public release permission based on this engineering evidence alone.
5. Real partner integration and clinical pathways require separate owner-approved contracts, consent/privacy and domain qualification; absent contracts remain `TBD` rather than automatically wired to Orgo, Kristal, FHIR or Konfid.

## Remaining major qualification steps

- Verify the dependency lock and full application suite in the declared Python 3.12 toolchain. An offline snapshot does not establish the current remote Git revision.
- Run a real PostgreSQL multi-process concurrency/recovery campaign and approved Docker deployment profile.
- Obtain independent security and clinical governance review, including intended use, clinical validation and privacy controls, before patient-facing deployment.
- If future MediKristal→Kristal/other adapter contracts are approved, add pinned producer/consumer fixtures and explicit enforcing policy at both ends.

## Current measured release blocker (2026-11-09)

The 73 application tests passed in the local synthetic harness. Fresh code coverage is **87.24% global (API 86.25%)**, below LevelUpDiag's explicit **90% minimum**; **release readiness remains unqualified**. Fresh documentary validation has **208 PASS / 0 FAIL**, not the older 211 count. These are local observations in Python 3.13.5 with installed dependencies not asserted to match the complete Python 3.12 locked environment.
