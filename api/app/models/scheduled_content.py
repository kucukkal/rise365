from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid

class ScheduledContent(Base):
    __tablename__ = "scheduled_contents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_template_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    info_type = Column(String(20), default="text")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
