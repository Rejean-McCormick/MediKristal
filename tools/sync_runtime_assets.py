#!/usr/bin/env python3
"""Synchronize repository-owned runtime assets into the installable Python package."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "backend" / "medikristal" / "_assets"


def sync_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> None:
    for name in ("domain.schema.json", "openapi.json", "traceability.json"):
        sync_file(ROOT / "contracts" / name, DEST / "contracts" / name)
    for name in ("index.html", "app.js", "styles.css"):
        sync_file(ROOT / "frontend" / name, DEST / "frontend" / name)
    print("runtime assets synchronized")


if __name__ == "__main__":
    main()
