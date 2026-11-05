"""
Circle contest endpoints.
All routes are mounted under /api/v1/circles/{circle_id}/contests
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.database import get_db
from app.models.circle import Circle, CircleMember, CircleContest, CircleContestSnapshot
from app.models.user import User
from app.core.dependencies import get_current_user
from app.services.push_service import send_push
from app.services.contest_scoring import ensure_snapshots, compute_leaderboard

router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _circle_or_404(db: Session, circle_id: str) -> Circle:
    try:
        cid = uuid.UUID(circle_id)
    except ValueError:
        raise HTTPException(404, "Circle not found")
    c = db.query(Circle).filter(Circle.id == cid).first()
    if not c:
        raise HTTPException(404, "Circle not found")
    return c

def _require_member(db: Session, circle: Circle, user: User):
    row = db.query(CircleMember).filter(
        CircleMember.circle_id == circle.id,
        CircleMember.user_id == user.id,
        CircleMember.status == "active",
    ).first()
    if not row:
        raise HTTPException(403, "You are not a member of this circle")

def _active_members(db: Session, circle: Circle) -> list[User]:
    rows = db.query(CircleMember).filter(
        CircleMember.circle_id == circle.id,
        CircleMember.status == "active",
    ).all()
    users = []
    for r in rows:
        u = db.query(User).filter(User.id == r.user_id).first()
        if u:
            users.append(u)
    return users

def _active_contest(db: Session, circle: Circle) -> Optional[CircleContest]:
    return db.query(CircleContest).filter(
        CircleContest.circle_id == circle.id,
        CircleContest.status == "active",
    ).order_by(CircleContest.created_at.desc()).first()

def _auto_complete_contest(contest: CircleContest, db: Session,
                            circle: Circle, members: list[User]):
    """Mark a contest completed if its end_at has passed, and send results notification."""
    now = datetime.now(timezone.utc)
    end = contest.end_at if contest.end_at.tzinfo else \
          contest.end_at.replace(tzinfo=timezone.utc)
    if now > end and contest.status == "active":
        contest.status = "completed"
        db.commit()

        # Build result line for push notification
        leaderboard = compute_leaderboard(contest, members, db)
        if leaderboard["has_winner"]:
            top = leaderboard["ranked"][:3]
            summary = " · ".join(
                f"{r['medal']} {r['name']} ({r['sum_pct']:.0f}%)" for r in top
            )
            body = f"🏁 Contest ended! {summary}"
        else:
            mentions = leaderboard["honorable_mentions"]
            if mentions:
                summary = " · ".join(
                    f"{r['medal']} {r['name']} ({r['sum_pct']:.0f}%)" for r in mentions
                )
                body = f"🏁 Contest ended — No Official Winner\nHonorable mentions: {summary}"
            else:
                body = f"🏁 Contest \"{contest.title}\" ended."

        for u in members:
            send_push(u, f"Contest: {contest.title}", body, {"type": "contest_ended"})


# ── schemas ───────────────────────────────────────────────────────────────────

class CreateContestRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    start_at: datetime          # ISO 8601 with tz
    end_at: datetime            # ISO 8601 with tz
    min_progress_pct: Optional[float] = Field(None, ge=0, le=100)
    min_days: Optional[int] = Field(None, ge=1)


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/{circle_id}/contests")
def create_contest(
    circle_id: str,
    req: CreateContestRequest,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """Owner creates a contest for their circle. Only one active contest at a time."""
    circle = _circle_or_404(db, circle_id)
    if circle.owner_id != me.id:
        raise HTTPException(403, "Only the circle owner can create a contest")

    now = datetime.now(timezone.utc)
    start = req.start_at if req.start_at.tzinfo else req.start_at.replace(tzinfo=timezone.utc)
    end = req.end_at if req.end_at.tzinfo else req.end_at.replace(tzinfo=timezone.utc)

    if end <= start:
        raise HTTPException(400, "end_at must be after start_at")
    if end <= now:
        raise HTTPException(400, "Contest end time must be in the future")

    if _active_contest(db, circle):
        raise HTTPException(400, "This circle already has an active contest. "
                                  "Wait for it to end before starting a new one.")

    contest = CircleContest(
        circle_id=circle.id,
        title=req.title,
        start_at=start,
        end_at=end,
        min_progress_pct=req.min_progress_pct,
        min_days=req.min_days,
        status="active",
    )
    db.add(contest)
    db.commit()
    db.refresh(contest)

    # Notify all active members
    members = _active_members(db, circle)
    rule_desc = ""
    if req.min_progress_pct is not None and req.min_days is not None:
        rule_desc = f"Goal: {int(req.min_progress_pct)}%+ daily for {req.min_days}+ days"
    elif req.min_days is not None:
        rule_desc = f"Goal: be active for {req.min_days}+ days"
    else:
        rule_desc = "Goal: highest total progress over the contest period"

    for u in members:
        if u.id != me.id:
            send_push(
                u,
                f"🏆 New Contest: {req.title}",
                f"{me.name} started a contest in \"{circle.name}\"! {rule_desc}",
                {"type": "contest_started", "contest_id": str(contest.id)},
            )

    return {
        "message": f"Contest \"{req.title}\" created",
        "contest_id": str(contest.id),
    }


@router.get("/{circle_id}/contests/active")
def get_active_contest(
    circle_id: str,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """
    Returns the active (or most-recently-completed) contest for this circle,
    including the full leaderboard. Returns null if no contest exists.
    """
    circle = _circle_or_404(db, circle_id)
    _require_member(db, circle, me)

    # Try active first, then most recent completed
    contest = _active_contest(db, circle)
    if not contest:
        contest = db.query(CircleContest).filter(
            CircleContest.circle_id == circle.id,
        ).order_by(CircleContest.created_at.desc()).first()

    if not contest:
        return {"contest": None}

    members = _active_members(db, circle)

    # Auto-complete if time has passed
    _auto_complete_contest(contest, db, circle, members)

    # Lazy-fill snapshots for completed days
    ensure_snapshots(contest, members, db)

    leaderboard = compute_leaderboard(contest, members, db)

    start = contest.start_at if contest.start_at.tzinfo else \
            contest.start_at.replace(tzinfo=timezone.utc)
    end = contest.end_at if contest.end_at.tzinfo else \
          contest.end_at.replace(tzinfo=timezone.utc)

    return {
        "contest": {
            "id": str(contest.id),
            "title": contest.title,
            "start_at": start.isoformat(),
            "end_at": end.isoformat(),
            "min_progress_pct": contest.min_progress_pct,
            "min_days": contest.min_days,
            "status": contest.status,
            "is_owner": circle.owner_id == me.id,
            "has_winner": leaderboard["has_winner"],
            "ranked": leaderboard["ranked"],
            "honorable_mentions": leaderboard["honorable_mentions"],
        }
    }


@router.delete("/{circle_id}/contests/active")
def cancel_active_contest(
    circle_id: str,
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """Owner can cancel the active contest."""
    circle = _circle_or_404(db, circle_id)
    if circle.owner_id != me.id:
        raise HTTPException(403, "Only the circle owner can cancel a contest")
    contest = _active_contest(db, circle)
    if not contest:
        raise HTTPException(404, "No active contest")
    contest.status = "cancelled"
    db.commit()

    members = _active_members(db, circle)
    for u in members:
        if u.id != me.id:
            send_push(u, "Contest cancelled",
                      f"The contest \"{contest.title}\" in \"{circle.name}\" was cancelled.",
                      {"type": "contest_cancelled"})
    return {"message": f"Contest \"{contest.title}\" cancelled"}
