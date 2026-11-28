"""Lookup the explicitly selected local public reference index."""
from __future__ import annotations

import re
import sqlite3
from contextlib import closing

from .config import load_settings
from .errors import DomainError


def public_lookup(query: str, limit: int) -> list[dict]:
    index = load_settings().public_reference_index
    if index is None or not index.is_file():
        raise DomainError("capability_unavailable", 503, "Aucun index public n’est configuré.")
    tokens = re.findall(r"[^\W_]+", query)
    fts = " AND ".join(f'"{token}"*' for token in tokens[:10])
    if not fts:
        return []
    try:
        with closing(sqlite3.connect(index.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("""
                SELECT s.source, r.kind, r.code, r.label, s.filename, s.sha256
                FROM record r JOIN source_file s ON r.file_id = s.id
                WHERE r.code = ? COLLATE NOCASE OR r.id IN (SELECT rowid FROM lookup WHERE lookup MATCH ?)
                ORDER BY CASE WHEN r.code = ? COLLATE NOCASE THEN 0 ELSE 1 END, length(r.label), r.id
                LIMIT ?
            """, (query, fts, query, limit))
            return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        raise DomainError("capability_unavailable", 503, "L’index public est illisible.") from exc
