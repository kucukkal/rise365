from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum

class PrayerName(str, enum.Enum):
    fajr = "fajr"
    dhuhr = "dhuhr"
    asr = "asr"
    maghrib = "maghrib"
    isha = "isha"

class PrayerLog(Base):
    __tablename__ = "prayer_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    prayer_name = Column(Enum(PrayerName), nullable=False)
    prayer_date = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    points_earned = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
