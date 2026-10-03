from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.database import Base
import uuid


class Circle(Base):
    __tablename__ = "circles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(40), nullable=False)
    name_key = Column(String(40), nullable=False, unique=True, index=True)  # lowercase, single spaces
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                      nullable=False, unique=True)  # one circle per owner
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CircleMember(Base):
    __tablename__ = "circle_members"
    __table_args__ = (UniqueConstraint("circle_id", "user_id", name="uq_circle_member"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    circle_id = Column(UUID(as_uuid=True), ForeignKey("circles.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    status = Column(String(20), nullable=False)  # active | requested | invited
    created_at = Column(DateTime(timezone=True), server_default=func.now())
