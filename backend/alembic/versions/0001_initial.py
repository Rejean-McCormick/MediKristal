"""initial MediKristal persistence"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("mk_entities",
        sa.Column("id",sa.String(36),primary_key=True), sa.Column("tenant_id",sa.String(36),nullable=False,index=True),
        sa.Column("kind",sa.String(64),nullable=False,index=True), sa.Column("owner",sa.String(32),nullable=False,index=True),
        sa.Column("revision",sa.Integer(),nullable=False), sa.Column("parent_id",sa.String(36),nullable=True,index=True),
        sa.Column("status",sa.String(64),nullable=True,index=True), sa.Column("foreign_key",sa.String(512),nullable=True,index=True),
        sa.Column("data",sa.JSON(),nullable=False), sa.Column("created_at",sa.DateTime(timezone=True),nullable=False), sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","kind","id",name="uq_entity_tenant_kind_id"))
    op.create_table("mk_idempotency",
        sa.Column("id",sa.String(36),primary_key=True),sa.Column("tenant_id",sa.String(36),nullable=False,index=True),sa.Column("principal_id",sa.String(128),nullable=False,index=True),
        sa.Column("route",sa.String(200),nullable=False,index=True),sa.Column("key",sa.String(200),nullable=False),sa.Column("request_hash",sa.String(71),nullable=False),
        sa.Column("status_code",sa.Integer(),nullable=False),sa.Column("etag",sa.String(64),nullable=True),sa.Column("response_json",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","principal_id","route","key",name="uq_idempotency_scope"))
    op.create_table("mk_external_versions",
        sa.Column("id",sa.String(36),primary_key=True),sa.Column("tenant_id",sa.String(36),nullable=False,index=True),sa.Column("namespace",sa.String(120),nullable=False,index=True),
        sa.Column("foreign_id",sa.String(256),nullable=False),sa.Column("foreign_version",sa.String(256),nullable=False),sa.Column("digest",sa.String(71),nullable=False),
        sa.Column("entity_id",sa.String(36),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint("tenant_id","namespace","foreign_id","foreign_version",name="uq_external_version"))
    op.create_table("mk_outbox",
        sa.Column("event_id",sa.String(36),primary_key=True),sa.Column("tenant_id",sa.String(36),nullable=False,index=True),sa.Column("event_type",sa.String(160),nullable=False,index=True),
        sa.Column("aggregate_type",sa.String(64),nullable=False),sa.Column("aggregate_id",sa.String(36),nullable=False,index=True),sa.Column("aggregate_revision",sa.Integer(),nullable=False),
        sa.Column("correlation_id",sa.String(36),nullable=False,index=True),sa.Column("payload",sa.JSON(),nullable=False),sa.Column("payload_digest",sa.String(71),nullable=False),
        sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),sa.Column("delivered",sa.Boolean(),nullable=False,server_default=sa.false()))
    op.create_table("mk_configuration",
        sa.Column("tenant_id",sa.String(36),primary_key=True),sa.Column("revision",sa.Integer(),nullable=False),sa.Column("data",sa.JSON(),nullable=False),sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("mk_audit",
        sa.Column("id",sa.String(36),primary_key=True),sa.Column("tenant_id",sa.String(36),nullable=False,index=True),sa.Column("principal_id",sa.String(128),nullable=False,index=True),
        sa.Column("action",sa.String(160),nullable=False,index=True),sa.Column("target_kind",sa.String(64),nullable=True),sa.Column("target_id",sa.String(36),nullable=True),
        sa.Column("correlation_id",sa.String(36),nullable=False,index=True),sa.Column("detail",sa.JSON(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("mk_blobs",
        sa.Column("id",sa.String(36),primary_key=True),sa.Column("tenant_id",sa.String(36),nullable=False,index=True),sa.Column("digest",sa.String(71),nullable=False,index=True),
        sa.Column("media_type",sa.String(128),nullable=False),sa.Column("classification",sa.String(64),nullable=False),sa.Column("content",sa.LargeBinary(),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))


def downgrade() -> None:
    for name in ["mk_blobs","mk_audit","mk_configuration","mk_outbox","mk_external_versions","mk_idempotency","mk_entities"]:
        op.drop_table(name)
