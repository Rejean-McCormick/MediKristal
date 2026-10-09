# MediKristal

**Independent medical-knowledge and diagnostic-pathway orchestration platform.** MediKristal models observations, hypotheses, investigations, resources and treatment options. It exposes software contracts to external systems, including Kristal/kOA adapters, while remaining independently runnable.

**Current engineering baseline:** specification 1.1, reference software package/API 0.2.0. The software exposes 80 contract operations and a documented synthetic reference implementation; **clinical validity, regulatory clearance, medical knowledge completeness and authorization for clinical use are not claimed**.

## Start here

- [Developer-agent instructions](AGENTS.md)
- [Documentation index](docs/README.md) — structured project reference
- [Vision and requirements](docs/01-vision.md), [architecture](docs/02-architecture.md), [data model](docs/03-data.md)
- [Delivery plan](docs/19-delivery.md), [API contracts](docs/13-api.md), [error invariants](docs/24-errors.md), [testing criteria](docs/18-tests.md)
- [Implementation status](IMPLEMENTATION.md), [software validation](APP_VALIDATION.md), [documentation validation](VALIDATION.md)

## Repository layout

| Path | Responsibility |
| --- | --- |
| `contracts/` | Schemas and API definitions |
| `examples/` | Synthetic JSON examples |
| `backend/` | FastAPI, persistence, migrations and worker |
| `frontend/` | Reference web interface |
| `deploy/` | Docker Compose topology |
| `tests/` | Synthetic application tests |
| `tools/` | Contract generation and documentary checks |
| `source-snapshots.json` | Source provenance |
| `manifest.json` | Delivered-file fingerprints |

## Run the reference implementation

From the repository root:

```sh
cp deploy/.env.example deploy/.env
# Set a new application secret and PostgreSQL password in deploy/.env.
cd deploy
docker compose up --build
```

The reference API and interface use `http://localhost:8000`. See [implementation notes](IMPLEMENTATION.md) for authentication setup and security/environment limits. Avoid using synthetic demonstration data to make clinical decisions.

## Source and contract authority

Requirements/decisions and the project's structured contracts are authoritative for intended software behavior; examples and visualizations are illustrative. External native formats remain owned by their respective standards. Separate semantic knowledge, probabilistic inference and resource planning rather than treating them as interchangeable.

The documented implementation can be described as engineering-software implemented; the labels `qualified_software`, `clinically_validated` and `authorized_for_use` require **additional independent evidence**.

## Verification

```sh
python tools/build_contracts.py
python tools/validate_reference.py
```

These validate selected documents, links, examples and a supported schema subset; they are not a replacement for full schema checks, application test suites or clinical validation. See [validation report](VALIDATION.md). `make validate` or `make manifest` regenerates the delivered-file manifest after configured checks.

Read the [changelog](CHANGELOG.md), [functional coverage](docs/26-coverage.md) and [acceptance scenarios](docs/33-acceptance.md) for the specification 1.1 scope, including 107 schema definitions and 80 operations.
