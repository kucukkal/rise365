from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base

class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    description = Column(String(300), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(),
                        server_default=func.now())
