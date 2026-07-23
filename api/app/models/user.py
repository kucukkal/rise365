from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum

class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    role = Column(Enum(UserRole), default=UserRole.user)
    program_level_id = Column(String(50), nullable=True)
    total_points = Column(Integer, default=0)
    completion_rate = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    fcm_token = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def achievement_level(self):
        if self.completion_rate >= 91: return "Diamond"
        if self.completion_rate >= 81: return "Sapphire"
        if self.completion_rate >= 71: return "Gold"
        if self.completion_rate >= 60: return "Silver"
        if self.completion_rate >= 50: return "Bronze"
        return "Starter"
