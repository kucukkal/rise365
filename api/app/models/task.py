from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum

class TaskFrequency(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"

class TaskInfoType(str, enum.Enum):
    none = "none"
    text = "text"
    image = "image"
    video = "video"

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    frequency = Column(Enum(TaskFrequency), nullable=False)
    points = Column(Integer, default=10)
    info_type = Column(Enum(TaskInfoType), default=TaskInfoType.none)
    info_content = Column(Text, nullable=True)
    pool_type = Column(String(20), default="myseed", nullable=False, server_default="myseed")
    program_level_id = Column(UUID(as_uuid=True), ForeignKey("program_levels.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TaskCompletion(Base):
    __tablename__ = "task_completions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
