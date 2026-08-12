from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid

class Quote(Base):
    __tablename__ = "quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(Text, nullable=False)
    source = Column(String(300), nullable=True)  # e.g. "Quran 2:286", "Sahih Bukhari"
    category = Column(String(20), default="general")  # quran, hadith, motivational, general
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
