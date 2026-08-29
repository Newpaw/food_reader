"""extend Oura API coverage

Revision ID: 006
Revises: 005
Create Date: 2026-08-29 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


CONNECTION_COLUMNS = [
    ("profile_age", sa.Integer()),
    ("profile_weight_kg", sa.Float()),
    ("profile_height_m", sa.Float()),
    ("profile_biological_sex", sa.String()),
    ("ring_configuration_json", sa.Text()),
    ("ring_battery_level_percent", sa.Integer()),
    ("ring_battery_charging", sa.Boolean()),
    ("ring_battery_in_charger", sa.Boolean()),
    ("ring_battery_updated_at", sa.DateTime(timezone=True)),
]

DAILY_COLUMNS = [
    ("activity_target_meters", sa.Integer()),
    ("activity_meters_to_target", sa.Integer()),
    ("sleep_score_delta", sa.Integer()),
    ("readiness_score_delta", sa.Integer()),
    ("low_battery_alert", sa.Boolean()),
    ("breathing_disturbance_index", sa.Integer()),
    ("pulse_wave_velocity_m_s", sa.Float()),
    ("rest_mode", sa.Boolean()),
    ("sleep_time_recommendation", sa.String()),
    ("sleep_time_status", sa.String()),
    ("optimal_bedtime_start_offset_seconds", sa.Integer()),
    ("optimal_bedtime_end_offset_seconds", sa.Integer()),
    ("optimal_bedtime_timezone_offset_seconds", sa.Integer()),
]


def upgrade() -> None:
    for name, type_ in CONNECTION_COLUMNS:
        op.add_column("oura_connections", sa.Column(name, type_, nullable=True))
    for name, type_ in DAILY_COLUMNS:
        op.add_column("oura_daily_metrics", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(DAILY_COLUMNS):
        op.drop_column("oura_daily_metrics", name)
    for name, _ in reversed(CONNECTION_COLUMNS):
        op.drop_column("oura_connections", name)
