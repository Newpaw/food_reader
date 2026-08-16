"""expand Oura daily metrics

Revision ID: 005
Revises: 004
Create Date: 2026-08-16 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


COLUMNS = [
    ("activity_target_calories", sa.Integer()),
    ("average_met_minutes", sa.Float()),
    ("equivalent_walking_distance_m", sa.Float()),
    ("sedentary_seconds", sa.Integer()),
    ("resting_seconds", sa.Integer()),
    ("low_activity_seconds", sa.Integer()),
    ("medium_activity_seconds", sa.Integer()),
    ("high_activity_seconds", sa.Integer()),
    ("non_wear_seconds", sa.Integer()),
    ("inactivity_alerts", sa.Integer()),
    ("temperature_deviation_c", sa.Float()),
    ("temperature_trend_deviation_c", sa.Float()),
    ("time_in_bed_seconds", sa.Integer()),
    ("awake_seconds", sa.Integer()),
    ("light_sleep_seconds", sa.Integer()),
    ("deep_sleep_seconds", sa.Integer()),
    ("rem_sleep_seconds", sa.Integer()),
    ("sleep_latency_seconds", sa.Integer()),
    ("sleep_efficiency", sa.Float()),
    ("average_heart_rate_bpm", sa.Float()),
    ("average_breaths_per_minute", sa.Float()),
    ("bedtime_start", sa.String()),
    ("bedtime_end", sa.String()),
    ("spo2_average_percent", sa.Float()),
    ("resilience_level", sa.String()),
    ("vascular_age_years", sa.Float()),
    ("vo2_max", sa.Float()),
    ("heart_rate_average_bpm", sa.Float()),
    ("heart_rate_min_bpm", sa.Float()),
    ("heart_rate_max_bpm", sa.Float()),
    ("heart_rate_samples", sa.Integer()),
    ("details_json", sa.Text()),
]


def upgrade() -> None:
    for name, type_ in COLUMNS:
        op.add_column("oura_daily_metrics", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(COLUMNS):
        op.drop_column("oura_daily_metrics", name)
