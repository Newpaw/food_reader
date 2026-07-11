"""add weight loss coaching data

Revision ID: 003
Revises: 002
Create Date: 2026-07-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("target_weight_kg", sa.Float(), nullable=True))
    op.add_column("user_profiles", sa.Column("desired_weekly_loss_percent", sa.Float(), nullable=True, server_default="0.6"))

    op.add_column("meals", sa.Column("food_description", sa.String(), nullable=True))
    op.add_column("meals", sa.Column("calorie_min", sa.Integer(), nullable=True))
    op.add_column("meals", sa.Column("calorie_max", sa.Integer(), nullable=True))
    op.add_column("meals", sa.Column("confidence", sa.Integer(), nullable=True))
    op.add_column("meals", sa.Column("analysis_json", sa.Text(), nullable=True))
    op.add_column("meals", sa.Column("analysis_model", sa.String(), nullable=True))
    op.add_column("meals", sa.Column("prompt_version", sa.String(), nullable=True))
    op.add_column("meals", sa.Column("confirmed_at", sa.DateTime(), nullable=True))

    op.create_table(
        "meal_corrections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("meal_id", sa.Integer(), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=False),
        sa.Column("after_json", sa.Text(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["meal_id"], ["meals.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meal_corrections_id"), "meal_corrections", ["id"], unique=False)
    op.create_index(op.f("ix_meal_corrections_meal_id"), "meal_corrections", ["meal_id"], unique=False)
    op.create_index(op.f("ix_meal_corrections_user_id"), "meal_corrections", ["user_id"], unique=False)

    op.create_table(
        "daily_checkins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("checkin_date", sa.String(), nullable=False),
        sa.Column("hunger", sa.Integer(), nullable=True),
        sa.Column("energy", sa.Integer(), nullable=True),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("steps", sa.Integer(), nullable=True),
        sa.Column("trained", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "checkin_date", name="uq_daily_checkin_user_date"),
    )
    op.create_index(op.f("ix_daily_checkins_id"), "daily_checkins", ["id"], unique=False)
    op.create_index(op.f("ix_daily_checkins_user_id"), "daily_checkins", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_daily_checkins_user_id"), table_name="daily_checkins")
    op.drop_index(op.f("ix_daily_checkins_id"), table_name="daily_checkins")
    op.drop_table("daily_checkins")
    op.drop_index(op.f("ix_meal_corrections_user_id"), table_name="meal_corrections")
    op.drop_index(op.f("ix_meal_corrections_meal_id"), table_name="meal_corrections")
    op.drop_index(op.f("ix_meal_corrections_id"), table_name="meal_corrections")
    op.drop_table("meal_corrections")
    for column in ["confirmed_at", "prompt_version", "analysis_model", "analysis_json", "confidence", "calorie_max", "calorie_min", "food_description"]:
        op.drop_column("meals", column)
    op.drop_column("user_profiles", "desired_weekly_loss_percent")
    op.drop_column("user_profiles", "target_weight_kg")
