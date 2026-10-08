"""Add Google Health connection, one-use OAuth state and private data store."""
import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("google_health_connections",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("health_user_id", sa.String(), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text()),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)))
    op.create_table("google_health_oauth_states",
        sa.Column("state_hash", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("verifier_encrypted", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("google_health_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("data_type", sa.String(), nullable=False),
        sa.Column("record_key", sa.String(), nullable=False),
        sa.Column("day", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "data_type", "record_key", name="uq_google_health_record"))
    op.create_index("ix_google_health_records_user_id", "google_health_records", ["user_id"])
    op.create_index("ix_google_health_records_day", "google_health_records", ["day"])


def downgrade():
    op.drop_table("google_health_records")
    op.drop_table("google_health_oauth_states")
    op.drop_table("google_health_connections")
