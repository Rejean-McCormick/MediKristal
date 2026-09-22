#!/usr/bin/env python3
"""Stage an import file in MediKristal quarantine storage and print its opaque reference."""
from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import select

from medikristal.db import Blob, SessionLocal, utcnow
from medikristal.importers import raw_digest
from medikristal.util import uuid4


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--media-type", default="text/csv")
    args = parser.parse_args()
    content = args.file.read_bytes()
    digest = raw_digest(content)
    with SessionLocal() as db:
        existing = db.execute(select(Blob).where(Blob.tenant_id == args.tenant, Blob.digest == digest)).scalar_one_or_none()
        if existing is None:
            existing = Blob(
                id=uuid4(), tenant_id=args.tenant, digest=digest, media_type=args.media_type,
                classification="quarantine", content=content, created_at=utcnow(),
            )
            db.add(existing)
            db.commit()
        print(f"blob:{existing.id}")
        print(digest)


if __name__ == "__main__":
    main()
