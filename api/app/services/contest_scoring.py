"""
Contest scoring service for Rise365 circle contests.

Scoring rules:
  Rule A  — min_progress_pct AND min_days are both set:
             1st sort: qualifying_days (days where daily_pct >= min_progress_pct) DESC
             2nd sort: sum of all daily_pct over contest window DESC
             A member "achieves" the contest if qualifying_days >= min_days.

  Rule B  — only min_days set (no min_progress_pct):
             Same as Rule A with min_progress_pct = 0.

  Rule C  — neither min_progress_pct nor min_days set:
             Rank purely by sum of all daily_pct DESC.

  No winner fallback (Rules A/B only, when no member reaches min_days):
             Top 3 by sum_pct are "Honorable Mentions". No official winner.
"""

from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.circle import CircleContest, CircleContestSnapshot, CircleMember
from app.models.user import User
from app.models.task import Task, TaskCompletion, TaskFrequency
from app.models.prayer import PrayerLog
from app.services.prayer_service import PRAYER_POINTS


# ── daily progress for a specific calendar date ───────────────────────────────

def _day_window_utc(target_date: date) -> tuple[datetime, datetime]:
    """
    Returns (day_start_utc, day_end_utc) for the 4 AM–4 AM window that
    corresponds to target_date.  We use simple UTC here — good enough for
    a daily contest metric that doesn't need per-user timezone precision.
    """
    day_start = datetime(target_date.year, target_date.month, target_date.day,
                         4, 0, 0)              # 4 AM UTC
    day_end = day_start + timedelta(days=1)   # 4 AM UTC next day
    return day_start, day_end


def calculate_daily_progress_for_date(user: User, db: Session,
                                      target_date: date) -> float:
    """
    Compute daily progress % (0–100) for the given calendar date.
    Uses daily tasks + prayers completed in the 4 AM–4 AM UTC window.
    """
    from app.services.completion_service import get_pool_filter, get_user_level_type
    from app.models.program_level import ProgramLevel
    import uuid as _uuid

    day_start, day_end = _day_window_utc(target_date)

    # ── available daily points ────────────────────────────────────────────────
    pool_filter = get_pool_filter(user, db)
    daily_tasks = db.query(Task).filter(
        Task.is_active == True,
        Task.frequency == TaskFrequency.daily,
        pool_filter,
    ).all()
    daily_task_pts = sum(t.points for t in daily_tasks)

    # Prayer points
    obligatory = ["fajr", "dhuhr", "asr", "maghrib", "isha"]
    prayer_pts = sum(PRAYER_POINTS.get(p, 0) for p in obligatory)
    level_order = 0
    if user.program_level_id:
        try:
            lv = db.query(ProgramLevel).filter(
                ProgramLevel.id == _uuid.UUID(str(user.program_level_id))
            ).first()
            level_order = lv.order if lv else 0
        except Exception:
            pass
    if level_order >= 1:
        prayer_pts += PRAYER_POINTS.get("evrad", 35) * 5
    if level_order >= 3:
        prayer_pts += PRAYER_POINTS.get("duha", 100)
    if level_order >= 4:
        prayer_pts += PRAYER_POINTS.get("awwabin", 100)

    daily_available = daily_task_pts + prayer_pts
    if daily_available == 0:
        return 0.0

    # ── earned daily points ───────────────────────────────────────────────────
    task_completions = db.query(TaskCompletion).filter(
        and_(
            TaskCompletion.user_id == user.id,
            TaskCompletion.completed_at >= day_start,
            TaskCompletion.completed_at < day_end,
        )
    ).all()
    earned_task_pts = 0
    for tc in task_completions:
        task = db.query(Task).filter(Task.id == tc.task_id).first()
        if task and "daily" in (task.frequency.value if hasattr(task.frequency, "value")
                                else str(task.frequency)):
            earned_task_pts += task.points

    prayer_logs = db.query(PrayerLog).filter(
        and_(
            PrayerLog.user_id == user.id,
            PrayerLog.completed_at >= day_start,
            PrayerLog.completed_at < day_end,
            PrayerLog.is_completed == True,
        )
    ).all()
    earned_prayer_pts = sum(log.points_earned or 0 for log in prayer_logs)

    earned = earned_task_pts + earned_prayer_pts
    return round(min(earned / daily_available, 1.0) * 100, 2)


# ── snapshot helper ───────────────────────────────────────────────────────────

def ensure_snapshots(contest: CircleContest, member_users: list[User],
                     db: Session) -> None:
    """
    For every completed contest day that lacks a snapshot, compute and store one.
    'Completed day' = any calendar date < today whose day_end_utc has passed.
    Called lazily when the leaderboard is fetched.
    """
    today = datetime.now(timezone.utc).date()
    start_date = contest.start_at.date() if contest.start_at.tzinfo else \
                 contest.start_at.replace(tzinfo=timezone.utc).date()
    end_date = min(
        contest.end_at.date() if contest.end_at.tzinfo else
        contest.end_at.replace(tzinfo=timezone.utc).date(),
        today - timedelta(days=1),   # only completed days
    )

    if start_date > end_date:
        return  # no completed days yet

    for user in member_users:
        # Which dates already have a snapshot for this user?
        existing = {
            row.snapshot_date
            for row in db.query(CircleContestSnapshot).filter(
                CircleContestSnapshot.contest_id == contest.id,
                CircleContestSnapshot.user_id == user.id,
            ).all()
        }
        d = start_date
        while d <= end_date:
            if d not in existing:
                pct = calculate_daily_progress_for_date(user, db, d)
                db.add(CircleContestSnapshot(
                    contest_id=contest.id,
                    user_id=user.id,
                    snapshot_date=d,
                    daily_pct=pct,
                ))
            d += timedelta(days=1)

    db.commit()


# ── scoring ───────────────────────────────────────────────────────────────────

def compute_leaderboard(contest: CircleContest, member_users: list[User],
                        db: Session) -> dict:
    """
    Returns a leaderboard dict:
    {
      "has_winner": bool,
      "ranked": [{ user_id, name, qualifying_days, sum_pct, rank,
                   is_achiever, medal, daily_scores: {date_str: pct} }],
      # when has_winner is False:
      "honorable_mentions": [same shape, top 3],
    }
    """
    today = datetime.now(timezone.utc).date()
    min_pct: float = contest.min_progress_pct if contest.min_progress_pct is not None else 0.0
    min_days: Optional[int] = contest.min_days

    results = []
    for user in member_users:
        # Collect snapshots (completed days)
        snapshots = {
            row.snapshot_date: row.daily_pct
            for row in db.query(CircleContestSnapshot).filter(
                CircleContestSnapshot.contest_id == contest.id,
                CircleContestSnapshot.user_id == user.id,
            ).all()
        }

        # Add live today if contest still active
        contest_end = contest.end_at if contest.end_at.tzinfo else \
                      contest.end_at.replace(tzinfo=timezone.utc)
        if contest.status == "active" and datetime.now(timezone.utc) <= contest_end:
            start_date = contest.start_at.date() if contest.start_at.tzinfo else \
                         contest.start_at.replace(tzinfo=timezone.utc).date()
            if start_date <= today:
                live_pct = calculate_daily_progress_for_date(user, db, today)
                snapshots[today] = live_pct

        qualifying_days = sum(1 for pct in snapshots.values() if pct >= min_pct)
        sum_pct = round(sum(snapshots.values()), 2)

        results.append({
            "user_id": str(user.id),
            "name": user.name,
            "qualifying_days": qualifying_days,
            "sum_pct": sum_pct,
            "daily_scores": {str(d): pct for d, pct in sorted(snapshots.items())},
        })

    # ── apply scoring rules ───────────────────────────────────────────────────
    if min_days is not None:
        # Rules A / B
        results.sort(key=lambda x: (-x["qualifying_days"], -x["sum_pct"]))
        achievers = [r for r in results if r["qualifying_days"] >= min_days]
        has_winner = len(achievers) > 0
    else:
        # Rule C
        results.sort(key=lambda x: -x["sum_pct"])
        achievers = results
        has_winner = True

    # Assign rank + medal
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, r in enumerate(results, start=1):
        r["rank"] = i
        r["medal"] = medals.get(i, "")
        r["is_achiever"] = r in achievers

    if has_winner:
        return {"has_winner": True, "ranked": results, "honorable_mentions": []}

    # No winner — honorable mentions (top 3 by sum_pct)
    top3 = sorted(results, key=lambda x: -x["sum_pct"])[:3]
    for i, r in enumerate(top3, start=1):
        r["rank"] = i
        r["medal"] = medals.get(i, "")
    return {
        "has_winner": False,
        "ranked": results,
        "honorable_mentions": top3,
    }
