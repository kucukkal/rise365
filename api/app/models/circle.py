from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Float, Integer, Date
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


class CircleContest(Base):
    __tablename__ = "circle_contests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    circle_id = Column(UUID(as_uuid=True), ForeignKey("circles.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    title = Column(String(100), nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    # Scoring rules — nullable means "not set"
    min_progress_pct = Column(Float, nullable=True)   # e.g. 80.0 → days must be ≥ 80%
    min_days = Column(Integer, nullable=True)          # e.g. 6 → need ≥ 6 qualifying days
    status = Column(String(20), nullable=False, default="active")  # active | completed | cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CircleContestSnapshot(Base):
    """One row per member per day during a contest — records daily progress %."""
    __tablename__ = "circle_contest_snapshots"
    __table_args__ = (UniqueConstraint("contest_id", "user_id", "snapshot_date",
                                       name="uq_contest_snapshot"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contest_id = Column(UUID(as_uuid=True), ForeignKey("circle_contests.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False)   # the calendar date (UTC)
    daily_pct = Column(Float, nullable=False, default=0.0)  # 0–100
    created_at = Column(DateTime(timezone=True), server_default=func.now())
