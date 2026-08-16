from datetime import datetime, timezone

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from .database import Base
from .sql_types import UTCDateTime


class OuraConnection(Base):
    __tablename__ = "oura_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    oura_user_id = Column(String, nullable=True, index=True)
    access_token_encrypted = Column(String, nullable=False)
    refresh_token_encrypted = Column(String, nullable=False)
    scope = Column(String, nullable=True)
    token_expires_at = Column(UTCDateTime(), nullable=True)
    last_sync_at = Column(UTCDateTime(), nullable=True)
    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class OuraDailyMetric(Base):
    __tablename__ = "oura_daily_metrics"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_oura_daily_metrics_user_day"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    day = Column(String, index=True, nullable=False)

    activity_score = Column(Integer, nullable=True)
    active_calories = Column(Integer, nullable=True)
    total_calories = Column(Integer, nullable=True)
    steps = Column(Integer, nullable=True)
    activity_target_calories = Column(Integer, nullable=True)
    average_met_minutes = Column(Float, nullable=True)
    equivalent_walking_distance_m = Column(Float, nullable=True)
    sedentary_seconds = Column(Integer, nullable=True)
    resting_seconds = Column(Integer, nullable=True)
    low_activity_seconds = Column(Integer, nullable=True)
    medium_activity_seconds = Column(Integer, nullable=True)
    high_activity_seconds = Column(Integer, nullable=True)
    non_wear_seconds = Column(Integer, nullable=True)
    inactivity_alerts = Column(Integer, nullable=True)

    readiness_score = Column(Integer, nullable=True)
    temperature_deviation_c = Column(Float, nullable=True)
    temperature_trend_deviation_c = Column(Float, nullable=True)

    sleep_score = Column(Integer, nullable=True)
    total_sleep_seconds = Column(Integer, nullable=True)
    time_in_bed_seconds = Column(Integer, nullable=True)
    awake_seconds = Column(Integer, nullable=True)
    light_sleep_seconds = Column(Integer, nullable=True)
    deep_sleep_seconds = Column(Integer, nullable=True)
    rem_sleep_seconds = Column(Integer, nullable=True)
    sleep_latency_seconds = Column(Integer, nullable=True)
    sleep_efficiency = Column(Float, nullable=True)
    average_hrv_ms = Column(Float, nullable=True)
    lowest_heart_rate_bpm = Column(Integer, nullable=True)
    average_heart_rate_bpm = Column(Float, nullable=True)
    average_breaths_per_minute = Column(Float, nullable=True)
    bedtime_start = Column(String, nullable=True)
    bedtime_end = Column(String, nullable=True)

    stress_high_seconds = Column(Integer, nullable=True)
    recovery_high_seconds = Column(Integer, nullable=True)

    workout_count = Column(Integer, nullable=False, default=0)
    workout_calories = Column(Float, nullable=False, default=0.0)
    workout_seconds = Column(Integer, nullable=False, default=0)

    spo2_average_percent = Column(Float, nullable=True)
    resilience_level = Column(String, nullable=True)
    vascular_age_years = Column(Float, nullable=True)
    vo2_max = Column(Float, nullable=True)
    heart_rate_average_bpm = Column(Float, nullable=True)
    heart_rate_min_bpm = Column(Float, nullable=True)
    heart_rate_max_bpm = Column(Float, nullable=True)
    heart_rate_samples = Column(Integer, nullable=True)

    # Compact structured context from Oura (contributors, workout details, tags,
    # sessions and other optional metrics). Large time-series arrays are never
    # persisted here; they are reduced to decision-useful daily summaries first.
    details_json = Column(Text, nullable=True)

    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
