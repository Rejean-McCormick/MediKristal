#!/usr/bin/env python3
"""Build a deterministic CycloneDX software bill of materials from the pinned lockfile.

The SBOM records exactly what this source distribution declares.  It deliberately does
not invent package licenses or wheel hashes: those belong to the concrete wheelhouse or
container image used for a deployment.  When --verify-installed is supplied, every
locked top-level distribution must be installed at the exact pinned version.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "backend" / "requirements.lock"
OUTPUT = ROOT / "sbom.cdx.json"
PROJECT_VERSION = "0.2.0"
REQ_RE = re.compile(r"^([A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?)==([^\s;]+)$")


def _canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _parse_lock() -> list[tuple[str, str, list[str]]]:
    requirements: list[tuple[str, str, list[str]]] = []
    for number, raw in enumerate(LOCK.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = REQ_RE.fullmatch(line)
        if not match:
            raise SystemExit(f"Unsupported/unpinned requirement at {LOCK}:{number}: {line}")
        raw_name, version = match.groups()
        if "[" in raw_name:
            base, extras = raw_name[:-1].split("[", 1)
            extra_list = sorted(x.strip() for x in extras.split(",") if x.strip())
        else:
            base, extra_list = raw_name, []
        requirements.append((base, version, extra_list))
    if not requirements:
        raise SystemExit("requirements.lock is empty")
    return requirements


def _verify_installed(requirements: list[tuple[str, str, list[str]]]) -> None:
    failures: list[str] = []
    for name, expected, _extras in requirements:
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            failures.append(f"{name}: missing (expected {expected})")
            continue
        if actual != expected:
            failures.append(f"{name}: installed {actual}, expected {expected}")
    if failures:
        raise SystemExit("Installed dependency verification failed:\n- " + "\n- ".join(failures))


def build_payload(requirements: list[tuple[str, str, list[str]]]) -> dict:
    lock_digest = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    serial = uuid.uuid5(uuid.NAMESPACE_URL, f"medikristal:{PROJECT_VERSION}:{lock_digest}")
    components = []
    refs = []
    for name, version, extras in requirements:
        canonical = _canonical_name(name)
        ref = f"pkg:pypi/{canonical}@{version}"
        component = {
            "type": "library",
            "bom-ref": ref,
            "name": name,
            "version": version,
            "purl": ref,
            "properties": [
                {"name": "medikristal:source", "value": "backend/requirements.lock"},
            ],
        }
        if extras:
            component["properties"].append({"name": "medikristal:extras", "value": ",".join(extras)})
        components.append(component)
        refs.append(ref)
    app_ref = f"pkg:pypi/medikristal@{PROJECT_VERSION}"
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": app_ref,
                "name": "medikristal",
                "version": PROJECT_VERSION,
                "purl": app_ref,
            },
            "properties": [
                {"name": "medikristal:requirements-lock-sha256", "value": lock_digest},
                {
                    "name": "medikristal:scope-note",
                    "value": "Declared direct dependencies only; artifact hashes and licenses must come from the deployment wheelhouse/image attestation.",
                },
            ],
        },
        "components": components,
        "dependencies": [{"ref": app_ref, "dependsOn": refs}],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-installed", action="store_true")
    args = parser.parse_args()
    requirements = _parse_lock()
    if args.verify_installed:
        _verify_installed(requirements)
    payload = build_payload(requirements)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"components": len(payload["components"]), "output": OUTPUT.name}))


if __name__ == "__main__":
    main()
