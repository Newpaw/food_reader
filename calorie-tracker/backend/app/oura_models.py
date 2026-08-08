from datetime import datetime, timezone

from sqlalchemy import Column, Float, ForeignKey, Integer, String, UniqueConstraint

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

    readiness_score = Column(Integer, nullable=True)
    sleep_score = Column(Integer, nullable=True)
    total_sleep_seconds = Column(Integer, nullable=True)
    average_hrv_ms = Column(Float, nullable=True)
    lowest_heart_rate_bpm = Column(Integer, nullable=True)

    stress_high_seconds = Column(Integer, nullable=True)
    recovery_high_seconds = Column(Integer, nullable=True)

    workout_count = Column(Integer, nullable=False, default=0)
    workout_calories = Column(Float, nullable=False, default=0.0)
    workout_seconds = Column(Integer, nullable=False, default=0)

    created_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
