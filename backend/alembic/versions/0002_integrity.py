"""integrity, history, access scope, booking claim and worker inbox"""
from alembic import op
import sqlalchemy as sa

revision = "0002_integrity"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mk_entity_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("kind", sa.String(64), nullable=False, index=True),
        sa.Column("entity_id", sa.String(36), nullable=False, index=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "kind", "entity_id", "revision", name="uq_entity_revision"),
    )
    op.create_table(
        "mk_case_access",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("case_id", sa.String(36), nullable=False, index=True),
        sa.Column("principal_id", sa.String(128), nullable=False, index=True),
        sa.Column("grant_kind", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "case_id", "principal_id", name="uq_case_access"),
    )
    op.create_table(
        "mk_reservation_claims",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("capability_id", sa.String(36), nullable=False, index=True),
        sa.Column("slot_id", sa.String(256), nullable=False),
        sa.Column("unit_index", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.String(36), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "capability_id", "slot_id", "unit_index", name="uq_reservation_claim"),
    )
    op.create_table(
        "mk_inbox",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("consumer", sa.String(128), nullable=False, index=True),
        sa.Column("event_id", sa.String(36), nullable=False, index=True),
        sa.Column("payload_digest", sa.String(71), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("consumer", "event_id", name="uq_inbox_consumer_event"),
    )
    with op.batch_alter_table("mk_blobs") as batch_op:
        batch_op.create_unique_constraint("uq_blob_digest", ["tenant_id", "digest"])


def downgrade() -> None:
    with op.batch_alter_table("mk_blobs") as batch_op:
        batch_op.drop_constraint("uq_blob_digest", type_="unique")
    for name in ["mk_inbox", "mk_reservation_claims", "mk_case_access", "mk_entity_revisions"]:
        op.drop_table(name)
