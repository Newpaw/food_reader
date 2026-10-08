"""Private Google Health connections and reconciled records."""
from datetime import datetime, timezone

from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint

from .database import Base
from .sql_types import UTCDateTime


class GoogleHealthConnection(Base):
    __tablename__ = "google_health_connections"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    health_user_id = Column(String, nullable=False)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=True)
    scope = Column(Text, nullable=False)
    token_expires_at = Column(UTCDateTime(), nullable=False)
    last_sync_at = Column(UTCDateTime(), nullable=True)


class GoogleHealthOAuthState(Base):
    __tablename__ = "google_health_oauth_states"
    state_hash = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    verifier_encrypted = Column(Text, nullable=False)
    expires_at = Column(UTCDateTime(), nullable=False)


class GoogleHealthRecord(Base):
    __tablename__ = "google_health_records"
    __table_args__ = (UniqueConstraint("user_id", "data_type", "record_key", name="uq_google_health_record"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    data_type = Column(String, nullable=False)
    record_key = Column(String, nullable=False)
    day = Column(String, index=True, nullable=False)
    payload_json = Column(Text, nullable=False)
    synced_at = Column(UTCDateTime(), default=lambda: datetime.now(timezone.utc), nullable=False)
