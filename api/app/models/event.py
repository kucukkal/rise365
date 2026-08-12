from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Time, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid

class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # NULL = fixed event
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(20), nullable=False)  # weekly, monthly, fixed
    fixed_type = Column(String(20), nullable=True)   # jummah, eid_fitr, eid_adha

    # Weekly events
    day_of_week = Column(Integer, nullable=True)     # 0=Monday, 6=Sunday

    # Monthly events
    day_of_month = Column(Integer, nullable=True)    # 1-31 for specific day
    week_of_month = Column(Integer, nullable=True)   # 1-4 for nth weekday
    monthly_pattern = Column(String(20), nullable=True)  # specific_day, weekly_day, nth_weekday

    # Common
    start_time = Column(String(10), nullable=True)   # HH:MM format
    points = Column(Integer, default=20)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EventCompletion(Base):
    __tablename__ = "event_completions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    event_date = Column(Date, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    points_earned = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
