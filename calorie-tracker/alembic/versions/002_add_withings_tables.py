"""add withings tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("weight_source", sa.String(), nullable=True))
    op.add_column("user_profiles", sa.Column("weight_measured_at", sa.DateTime(), nullable=True))

    op.create_table(
        "withings_connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("withings_user_id", sa.String(), nullable=True),
        sa.Column("access_token_encrypted", sa.String(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.String(), nullable=False),
        sa.Column("scope", sa.String(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_update_timestamp", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_withings_connections_id"), "withings_connections", ["id"], unique=False)

    op.create_table(
        "withings_measurements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("withings_grpid", sa.String(), nullable=False),
        sa.Column("measured_at", sa.DateTime(), nullable=False),
        sa.Column("remote_created_at", sa.DateTime(), nullable=True),
        sa.Column("remote_modified_at", sa.DateTime(), nullable=True),
        sa.Column("attrib", sa.Integer(), nullable=True),
        sa.Column("category", sa.Integer(), nullable=True),
        sa.Column("device_id", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("fat_free_mass_kg", sa.Float(), nullable=True),
        sa.Column("fat_ratio", sa.Float(), nullable=True),
        sa.Column("fat_mass_kg", sa.Float(), nullable=True),
        sa.Column("muscle_mass_kg", sa.Float(), nullable=True),
        sa.Column("hydration_kg", sa.Float(), nullable=True),
        sa.Column("bone_mass_kg", sa.Float(), nullable=True),
        sa.Column("visceral_fat", sa.Float(), nullable=True),
        sa.Column("bmr", sa.Float(), nullable=True),
        sa.Column("metabolic_age", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "withings_grpid", name="uq_withings_measurements_user_grpid"),
    )
    op.create_index(op.f("ix_withings_measurements_id"), "withings_measurements", ["id"], unique=False)
    op.create_index(op.f("ix_withings_measurements_measured_at"), "withings_measurements", ["measured_at"], unique=False)
    op.create_index(op.f("ix_withings_measurements_user_id"), "withings_measurements", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_withings_measurements_user_id"), table_name="withings_measurements")
    op.drop_index(op.f("ix_withings_measurements_measured_at"), table_name="withings_measurements")
    op.drop_index(op.f("ix_withings_measurements_id"), table_name="withings_measurements")
    op.drop_table("withings_measurements")
    op.drop_index(op.f("ix_withings_connections_id"), table_name="withings_connections")
    op.drop_table("withings_connections")
    op.drop_column("user_profiles", "weight_measured_at")
    op.drop_column("user_profiles", "weight_source")
