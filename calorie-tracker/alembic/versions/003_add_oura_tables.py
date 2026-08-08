"""add oura integration tables

Revision ID: 003
Revises: 002
Create Date: 2026-08-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oura_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("oura_user_id", sa.String(), nullable=True),
        sa.Column("access_token_encrypted", sa.String(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.String(), nullable=False),
        sa.Column("scope", sa.String(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_oura_connections_id"), "oura_connections", ["id"], unique=False)
    op.create_index(op.f("ix_oura_connections_oura_user_id"), "oura_connections", ["oura_user_id"], unique=False)

    op.create_table(
        "oura_daily_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.String(), nullable=False),
        sa.Column("activity_score", sa.Integer(), nullable=True),
        sa.Column("active_calories", sa.Integer(), nullable=True),
        sa.Column("total_calories", sa.Integer(), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("readiness_score", sa.Integer(), nullable=True),
        sa.Column("sleep_score", sa.Integer(), nullable=True),
        sa.Column("total_sleep_seconds", sa.Integer(), nullable=True),
        sa.Column("average_hrv_ms", sa.Float(), nullable=True),
        sa.Column("lowest_heart_rate_bpm", sa.Integer(), nullable=True),
        sa.Column("stress_high_seconds", sa.Integer(), nullable=True),
        sa.Column("recovery_high_seconds", sa.Integer(), nullable=True),
        sa.Column("workout_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("workout_calories", sa.Float(), nullable=False, server_default="0"),
        sa.Column("workout_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "day", name="uq_oura_daily_metrics_user_day"),
    )
    op.create_index(op.f("ix_oura_daily_metrics_id"), "oura_daily_metrics", ["id"], unique=False)
    op.create_index(op.f("ix_oura_daily_metrics_user_id"), "oura_daily_metrics", ["user_id"], unique=False)
    op.create_index(op.f("ix_oura_daily_metrics_day"), "oura_daily_metrics", ["day"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_oura_daily_metrics_day"), table_name="oura_daily_metrics")
    op.drop_index(op.f("ix_oura_daily_metrics_user_id"), table_name="oura_daily_metrics")
    op.drop_index(op.f("ix_oura_daily_metrics_id"), table_name="oura_daily_metrics")
    op.drop_table("oura_daily_metrics")
    op.drop_index(op.f("ix_oura_connections_oura_user_id"), table_name="oura_connections")
    op.drop_index(op.f("ix_oura_connections_id"), table_name="oura_connections")
    op.drop_table("oura_connections")
