.PHONY: test validate manifest run worker migrate token

PYTHON ?= python

validate:
	$(PYTHON) tools/build_contracts.py
	$(PYTHON) tools/validate_reference.py
	$(PYTHON) tools/sync_runtime_assets.py
	$(PYTHON) tools/build_sbom.py
	$(PYTHON) tools/build_manifest.py

manifest:
	$(PYTHON) tools/build_manifest.py

test:
	PYTHONPATH="$(CURDIR)/backend:$(CURDIR)" pytest -q

run:
	PYTHONPATH="$(CURDIR)/backend" uvicorn medikristal.app:app --host 0.0.0.0 --port 8000 --reload

worker:
	PYTHONPATH="$(CURDIR)/backend" $(PYTHON) -m medikristal.worker

migrate:
	cd backend && alembic upgrade head

token:
	@echo 'Example: MEDIKRISTAL_AUTH_SECRET=... PYTHONPATH=backend python -m medikristal.token_cli --tenant <uuid> --principal dev --permission "*"'
