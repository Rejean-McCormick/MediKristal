#!/usr/bin/env python3
"""Build a reproducible SHA-256 manifest for the deliverable source tree.

The manifest deliberately excludes itself, caches, VCS metadata and generated binary
artifacts. Run it after contract/document validation so the hashes describe the exact
files being shipped.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {'.git', '.pytest_cache', '__pycache__', '.venv', 'venv', 'dist', 'build'}
EXCLUDED_FILES = {'manifest.json', '.coverage'}
EXCLUDED_SUFFIXES = {'.pyc', '.pyo', '.zip', '.whl'}


def included(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS or part.endswith('.egg-info') for part in rel.parts[:-1]):
        return False
    if rel.name in EXCLUDED_FILES or rel.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def main() -> None:
    files = []
    for path in sorted(ROOT.rglob('*')):
        if not included(path):
            continue
        data = path.read_bytes()
        files.append({
            'path': path.relative_to(ROOT).as_posix(),
            'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(),
        })
    payload = {
        'format': 'medikristal.delivery-manifest/2',
        'document_version': '1.1',
        'api_version': '0.2.0',
        'files': files,
    }
    (ROOT / 'manifest.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'files': len(files)}))


if __name__ == '__main__':
    main()
