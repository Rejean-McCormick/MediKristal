#!/usr/bin/env python3
"""Read-only verification of shipped MediKristal source hashes and pinned SBOM.

No application imports, database, network access, generated output writes, or
medical-domain validation. This verifies source-package integrity only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from build_manifest import ROOT, included
from build_sbom import _parse_lock, build_payload


def inspect_delivery(root: Path = ROOT) -> list[str]:
    issues: list[str] = []
    manifest_path = root / 'manifest.json'
    sbom_path = root / 'sbom.cdx.json'
    lock_path = root / 'backend/requirements.lock'
    for path in (manifest_path, sbom_path, lock_path):
        if not path.is_file():
            issues.append(f'missing required delivery artifact: {path.relative_to(root)}')
    if issues:
        return issues
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        sbom = json.loads(sbom_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return [f'invalid delivery JSON: {exc}']
    if manifest.get('format') != 'medikristal.delivery-manifest/2':
        issues.append('unsupported delivery-manifest format')
    if manifest.get('api_version') != sbom.get('metadata', {}).get('component', {}).get('version'):
        issues.append('API version and SBOM application version disagree')
    actual = {
        p.relative_to(root).as_posix(): {
            'path': p.relative_to(root).as_posix(),
            'bytes': p.stat().st_size,
            'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
        }
        for p in root.rglob('*') if included(p)
    }
    entries = manifest.get('files', [])
    if not isinstance(entries, list):
        issues.append('manifest files must be an array')
        entries = []
    declared: dict[str, dict] = {}
    for record in entries:
        if not isinstance(record, dict) or not isinstance(record.get('path'), str):
            issues.append('manifest contains an invalid member')
            continue
        rel = record['path']
        path = Path(rel)
        if path.is_absolute() or '..' in path.parts or not (root / path).resolve().is_relative_to(root.resolve()):
            issues.append(f'unsafe manifest path: {rel}')
            continue
        if rel in declared:
            issues.append(f'duplicate manifest entry: {rel}')
        else:
            declared[rel] = record
    for extra in sorted(set(declared) - set(actual)):
        issues.append(f'manifest declares missing or excluded source: {extra}')
    for missing in sorted(set(actual) - set(declared)):
        issues.append(f'unlisted source file: {missing}')
    for key in set(actual) & set(declared):
        if actual[key] != declared[key]:
            issues.append(f'hash or size mismatch: {key}')
    try:
        # The canonical builder defines exactly the lock syntax and SBOM layout.
        # Both derive only from owner source files: no dependency installation.
        # Its fixed ROOT is equal to this checkout when running from this repo.
        if root.resolve() != ROOT.resolve():
            raise ValueError('cannot attest an alternate source root with the canonical SBOM builder')
        expected = build_payload(_parse_lock())
        if expected != sbom:
            issues.append('CycloneDX SBOM differs from exact dependency lock metadata')
    except (OSError, ValueError, SystemExit) as exc:
        issues.append(f'unable to verify dependency lock and SBOM: {exc}')
    return issues


if __name__ == '__main__':
    problems = inspect_delivery()
    for item in problems:
        print('FAIL:', item)
    if not problems:
        print('PASS: full delivery source set, SHA-256 manifest and pinned SBOM agree (engineering evidence only)')
    raise SystemExit(bool(problems))
