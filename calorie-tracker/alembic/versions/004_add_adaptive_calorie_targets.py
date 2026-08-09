"""add adaptive calorie target settings

Revision ID: 004
Revises: 003
Create Date: 2026-08-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("adaptive_calories_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("user_profiles", sa.Column("adaptive_target_calories", sa.Integer(), nullable=True))
    op.add_column("user_profiles", sa.Column("adaptive_target_updated_on", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "adaptive_target_updated_on")
    op.drop_column("user_profiles", "adaptive_target_calories")
    op.drop_column("user_profiles", "adaptive_calories_enabled")
