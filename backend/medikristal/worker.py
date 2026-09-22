from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import delete, select

from .db import Entity, InboxEvent, OutboxEvent, ReservationClaim, SessionLocal, utcnow
from .store import update_row
from .util import digest, uuid4


CONSUMER = "medikristal.local-domain-worker.v1"


def _handle_local_event(_session, _row: OutboxEvent) -> None:
    """Apply asynchronous local projections only.

    Mutations that must be atomic with an API command stay in that command transaction.
    External effects are never issued here without a configured adapter and durable command.
    The inbox still records every consumed event so replays are observable and deduplicated.
    """
    return None


def expire_holds_once(limit: int = 100) -> int:
    """Expire locally held capacity whose authoritative hold deadline has passed.

    Reconciliation states are deliberately excluded: an ambiguous remote outcome keeps its
    capacity claim until a separate reconciliation proves that it can be released.
    """
    now = datetime.now(timezone.utc)
    expired = 0
    with SessionLocal() as session:
        rows = session.execute(select(Entity).where(
            Entity.kind == "Booking",
            Entity.status.in_(["held", "confirm_requested"]),
        ).order_by(Entity.updated_at, Entity.id).limit(limit).with_for_update(skip_locked=True)).scalars().all()
        for row in rows:
            raw_deadline = row.data.get("hold_expires_at")
            if not raw_deadline:
                continue
            try:
                deadline = datetime.fromisoformat(str(raw_deadline).replace("Z", "+00:00"))
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                deadline = deadline.astimezone(timezone.utc)
            except ValueError:
                # Invalid persisted deadlines are not guessed. They remain visible for an
                # operator instead of releasing capacity on an invented interpretation.
                continue
            if deadline > now:
                continue
            item = update_row(row, status="expired")
            session.execute(delete(ReservationClaim).where(
                ReservationClaim.tenant_id == row.tenant_id,
                ReservationClaim.booking_id == row.id,
            ))
            payload = {"status": "expired", "reason": "hold_expired"}
            session.add(OutboxEvent(
                event_id=uuid4(), tenant_id=row.tenant_id,
                event_type="medikristal.booking.updated.v1",
                aggregate_type="Booking", aggregate_id=row.id,
                aggregate_revision=item["revision"], correlation_id=uuid4(),
                payload=payload, payload_digest=digest(payload), occurred_at=utcnow(), delivered=False,
            ))
            expired += 1
        session.commit()
    return expired


def drain_once(limit: int = 100) -> int:
    """Consume outbox rows with an inbox dedupe record in the same transaction."""
    processed = 0
    with SessionLocal() as session:
        rows = session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.delivered.is_(False))
            .order_by(OutboxEvent.occurred_at, OutboxEvent.event_id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).scalars().all()
        for row in rows:
            seen = session.execute(select(InboxEvent).where(
                InboxEvent.consumer == CONSUMER,
                InboxEvent.event_id == row.event_id,
            )).scalar_one_or_none()
            if seen is None:
                values = {
                    "id": uuid4(), "consumer": CONSUMER, "event_id": row.event_id,
                    "payload_digest": row.payload_digest, "processed_at": utcnow(),
                }
                dialect = session.get_bind().dialect.name
                if dialect == "postgresql":
                    from sqlalchemy.dialects.postgresql import insert as dialect_insert
                elif dialect == "sqlite":
                    from sqlalchemy.dialects.sqlite import insert as dialect_insert
                else:
                    raise RuntimeError(f"Unsupported inbox claim dialect: {dialect}")
                result = session.execute(
                    dialect_insert(InboxEvent)
                    .values(**values)
                    .on_conflict_do_nothing(index_elements=["consumer", "event_id"])
                )
                # The claim and local effect share the outer transaction. If the effect
                # raises, both roll back; if another worker already owns the claim, this
                # worker skips the effect without poisoning its transaction.
                if result.rowcount == 1:
                    _handle_local_event(session, row)
            row.delivered = True
            processed += 1
        session.commit()
    return processed


def main() -> None:
    while True:
        expired = expire_holds_once()
        count = drain_once()
        time.sleep(0.1 if (count or expired) else 1.0)


if __name__ == "__main__":
    main()
