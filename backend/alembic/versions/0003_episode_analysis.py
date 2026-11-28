"""Persist separately governed episode statistics."""
from alembic import op
import sqlalchemy as sa

revision = "0003_episode_analysis"
down_revision = "0002_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mk_episode_analysis",
        sa.Column("episode_id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("outcome_kind", sa.String(32), nullable=False),
        sa.Column("model_ref", sa.String(71), nullable=False),
        sa.Column("forecast_percent", sa.Integer()),
        sa.Column("verified_positive", sa.Boolean()),
    )
    op.create_index("ix_mk_episode_analysis_tenant_id", "mk_episode_analysis", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("mk_episode_analysis")
