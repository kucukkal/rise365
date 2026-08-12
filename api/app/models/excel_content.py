from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid

class ExcelTaskContent(Base):
    __tablename__ = "excel_task_contents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    row_number = Column(Integer, nullable=False)   # 1-based
    content = Column(Text, nullable=False)          # Column A
    information = Column(Text, nullable=True)       # Column B
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
