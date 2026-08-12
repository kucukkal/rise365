from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid

class TaskPdfAssignment(Base):
    __tablename__ = "task_pdf_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    pdf_book_id = Column(UUID(as_uuid=True), ForeignKey("pdf_books.id"), nullable=False)
    level_order = Column(Integer, nullable=False)
    pages_per_day = Column(Integer, default=1)
    start_date_offset = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
