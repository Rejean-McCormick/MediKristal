from __future__ import annotations

import time
from sqlalchemy import select

from .db import OutboxEvent, SessionLocal


def drain_once(limit: int = 100) -> int:
    """Consume local outbox events.

    This reference worker only marks events delivered after durable local handling.
    External delivery belongs to explicit adapters and is never inferred from this loop.
    """
    with SessionLocal() as session:
        rows = session.execute(
            select(OutboxEvent).where(OutboxEvent.delivered.is_(False)).order_by(OutboxEvent.occurred_at).limit(limit).with_for_update(skip_locked=True)
        ).scalars().all()
        for row in rows:
            row.delivered = True
        session.commit()
        return len(rows)


def main() -> None:
    while True:
        count = drain_once()
        time.sleep(0.1 if count else 1.0)


if __name__ == "__main__":
    main()
