from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum

class SignupCodeType(str, enum.Enum):
    myseed = "myseed"
    myrise = "myrise"
    custom = "custom"


class SignupCode(Base):
    __tablename__ = "signup_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False, index=True)
    max_uses = Column(Integer, default=1)
    current_uses = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    code_type = Column(
        String(20),
        default="custom",
        nullable=False,
        server_default="custom"
    )
    description = Column(String(300), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.current_uses >= self.max_uses:
            return False
        return True
