from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, date, timedelta
from app.models.user import User
from app.models.task import Task, TaskCompletion, TaskFrequency
from app.models.prayer import PrayerLog
from app.models.event import Event, EventCompletion
from app.services.prayer_service import PRAYER_POINTS

def get_period_boundaries(user=None):
    """Day starts at 4:00 AM in the user's local time; week on Monday, month on the 1st.
    Returned as naive UTC datetimes."""
    from app.services.timeutil import day_start_local, to_utc_naive
    daily_local = day_start_local(user)
    weekly_local = daily_local - timedelta(days=daily_local.weekday())
    monthly_local = daily_local.replace(day=1)
    return to_utc_naive(daily_local), to_utc_naive(weekly_local), to_utc_naive(monthly_local)

def get_user_level_type(user: User, db: Session) -> str:
    """Get user's level type (seed/myrise/custom)"""
    from app.models.program_level import ProgramLevel
    import uuid as _uuid
    if user.program_level_id:
        try:
            lv = db.query(ProgramLevel).filter(
                ProgramLevel.id == _uuid.UUID(str(user.program_level_id))
            ).first()
            return getattr(lv, "level_type", "seed") if lv else "seed"
        except:
            pass
    return "seed"

def get_pool_filter(user: User, db: Session):
    """Get SQLAlchemy filter for user's task pool"""
    level_type = get_user_level_type(user, db)
    if level_type == "myrise":
        return Task.pool_type.in_(["myrise", "both"])
    return Task.pool_type.in_(["myseed", "both"])

def get_available_points(user: User, db: Session) -> dict:
    """
    Calculate max possible points per period (Option A — independent periods).
    Daily   = today's tasks + today's prayers
    Weekly  = weekly tasks + weekly events only
    Monthly = monthly tasks + monthly events only
    """
    pool_filter = get_pool_filter(user, db)
    level_type = get_user_level_type(user, db)

    from app.models.program_level import ProgramLevel
    import uuid as _uuid
    level_order = 0
    if user.program_level_id:
        try:
            lv = db.query(ProgramLevel).filter(
                ProgramLevel.id == _uuid.UUID(str(user.program_level_id))
            ).first()
            level_order = lv.order if lv else 0
        except:
            pass

    # ── Daily ────────────────────────────────────────────────────────────────
    daily_tasks = db.query(Task).filter(
        Task.is_active == True,
        Task.frequency == TaskFrequency.daily,
        pool_filter
    ).all()
    daily_task_pts = sum(t.points for t in daily_tasks)

    # Prayer points (obligatory always)
    obligatory = ["fajr", "dhuhr", "asr", "maghrib", "isha"]
    prayer_pts = sum(PRAYER_POINTS.get(p, 0) for p in obligatory)

    # Evrad if rank >= 1
    if level_order >= 1:
        prayer_pts += PRAYER_POINTS.get("evrad", 35) * 5

    # Voluntary prayers if rank >= 3
    if level_order >= 3:
        prayer_pts += PRAYER_POINTS.get("duha", 100)
    if level_order >= 4:
        prayer_pts += PRAYER_POINTS.get("awwabin", 100)

    daily_available = daily_task_pts + prayer_pts

    # ── Weekly ───────────────────────────────────────────────────────────────
    weekly_tasks = db.query(Task).filter(
        Task.is_active == True,
        Task.frequency == TaskFrequency.weekly,
        pool_filter
    ).all()
    weekly_task_pts = sum(t.points for t in weekly_tasks)

    # Weekly events (user's + Jummah)
    weekly_events = db.query(Event).filter(
        and_(
            Event.user_id == user.id,
            Event.event_type == "weekly",
            Event.is_active == True,
        )
    ).all()
    weekly_event_pts = sum(e.points for e in weekly_events)
    weekly_event_pts += 150  # Jummah fixed event

    weekly_available = weekly_task_pts + weekly_event_pts

    # ── Monthly ──────────────────────────────────────────────────────────────
    monthly_tasks = db.query(Task).filter(
        Task.is_active == True,
        Task.frequency == TaskFrequency.monthly,
        pool_filter
    ).all()
    monthly_task_pts = sum(t.points for t in monthly_tasks)

    monthly_events = db.query(Event).filter(
        and_(
            Event.user_id == user.id,
            Event.event_type == "monthly",
            Event.is_active == True,
        )
    ).all()
    monthly_event_pts = sum(e.points for e in monthly_events)

    monthly_available = monthly_task_pts + monthly_event_pts

    return {
        "daily": daily_available,
        "weekly": weekly_available,
        "monthly": monthly_available,
        "total": daily_available + weekly_available + monthly_available,
    }

def get_earned_points(user: User, db: Session) -> dict:
    """
    Calculate points earned in current period windows.
    Uses 4 AM cutoff for all periods.
    """
    daily_start, weekly_start, monthly_start = get_period_boundaries(user)
    now = datetime.utcnow()

    # ── Daily earned ─────────────────────────────────────────────────────────
    # Task completions since 4 AM today
    daily_task_completions = db.query(TaskCompletion).filter(
        and_(
            TaskCompletion.user_id == user.id,
            TaskCompletion.completed_at >= daily_start.replace(tzinfo=None),
        )
    ).all()

    daily_task_pts = 0
    for tc in daily_task_completions:
        task = db.query(Task).filter(Task.id == tc.task_id).first()
        if task:
            freq = task.frequency.value if hasattr(task.frequency, 'value') \
                else str(task.frequency)
            if 'daily' in freq:
                daily_task_pts += task.points

    # Prayer completions since 4 AM today
    from sqlalchemy import func
    prayer_logs = db.query(PrayerLog).filter(
        and_(
            PrayerLog.user_id == user.id,
            PrayerLog.completed_at >= daily_start.replace(tzinfo=None),
            PrayerLog.is_completed == True,
        )
    ).all()
    daily_prayer_pts = sum(log.points_earned or 0 for log in prayer_logs)

    daily_earned = daily_task_pts + daily_prayer_pts

    # ── Weekly earned ────────────────────────────────────────────────────────
    weekly_task_completions = db.query(TaskCompletion).filter(
        and_(
            TaskCompletion.user_id == user.id,
            TaskCompletion.completed_at >= weekly_start.replace(tzinfo=None),
        )
    ).all()

    weekly_task_pts = 0
    for tc in weekly_task_completions:
        task = db.query(Task).filter(Task.id == tc.task_id).first()
        if task:
            freq = task.frequency.value if hasattr(task.frequency, 'value') \
                else str(task.frequency)
            if 'weekly' in freq:
                weekly_task_pts += task.points

    weekly_event_completions = db.query(EventCompletion).filter(
        and_(
            EventCompletion.user_id == user.id,
            EventCompletion.event_date >= weekly_start.date(),
        )
    ).all()

    weekly_event_pts = 0
    for ec in weekly_event_completions:
        event = db.query(Event).filter(Event.id == ec.event_id).first()
        if event and event.event_type in ("weekly", "fixed"):
            weekly_event_pts += ec.points_earned or 0

    weekly_earned = weekly_task_pts + weekly_event_pts

    # ── Monthly earned ───────────────────────────────────────────────────────
    monthly_task_completions = db.query(TaskCompletion).filter(
        and_(
            TaskCompletion.user_id == user.id,
            TaskCompletion.completed_at >= monthly_start.replace(tzinfo=None),
        )
    ).all()

    monthly_task_pts = 0
    for tc in monthly_task_completions:
        task = db.query(Task).filter(Task.id == tc.task_id).first()
        if task:
            freq = task.frequency.value if hasattr(task.frequency, 'value') \
                else str(task.frequency)
            if 'monthly' in freq:
                monthly_task_pts += task.points

    monthly_event_completions = db.query(EventCompletion).filter(
        and_(
            EventCompletion.user_id == user.id,
            EventCompletion.event_date >= monthly_start.date(),
        )
    ).all()

    monthly_event_pts = 0
    for ec in monthly_event_completions:
        event = db.query(Event).filter(Event.id == ec.event_id).first()
        if event and event.event_type == "monthly":
            monthly_event_pts += ec.points_earned or 0

    monthly_earned = monthly_task_pts + monthly_event_pts

    return {
        "daily": daily_earned,
        "weekly": weekly_earned,
        "monthly": monthly_earned,
        "total": daily_earned + weekly_earned + monthly_earned,
    }

def calculate_weighted_completion(user: User, db: Session) -> float:
    """
    Weighted completion % with dynamic weights from available points.
    Weight_i = available_i / total_available
    Final % = sum(weight_i × earned_i/available_i) × 100
    """
    available = get_available_points(user, db)
    earned = get_earned_points(user, db)

    total_available = available["total"]
    if total_available == 0:
        return 0.0

    daily_w = available["daily"] / total_available
    weekly_w = available["weekly"] / total_available
    monthly_w = available["monthly"] / total_available

    daily_pct = min(earned["daily"] / available["daily"], 1.0) \
        if available["daily"] > 0 else 0
    weekly_pct = min(earned["weekly"] / available["weekly"], 1.0) \
        if available["weekly"] > 0 else 0
    monthly_pct = min(earned["monthly"] / available["monthly"], 1.0) \
        if available["monthly"] > 0 else 0

    final = (daily_w * daily_pct +
             weekly_w * weekly_pct +
             monthly_w * monthly_pct) * 100

    return round(min(final, 100.0), 2)

def calculate_total_points(user: User, db: Session) -> int:
    """
    Total points = current period earned points only (resets with each period).
    Daily resets at 4 AM, weekly on Monday 4 AM, monthly on 1st 4 AM.
    """
    earned = get_earned_points(user, db)
    return earned["total"]

def get_achievement_level(pct: float) -> str:
    if pct >= 91: return "Diamond"
    if pct >= 81: return "Sapphire"
    if pct >= 71: return "Gold"
    if pct >= 60: return "Silver"
    if pct >= 50: return "Bronze"
    return "Starter"

def update_weekly_achievement(user: User, db: Session):
    """Called every Monday at 4 AM — updates achievement level"""
    pct = calculate_weighted_completion(user, db)
    new_level = get_achievement_level(pct)
    old_level = user.achievement_level
    user.achievement_level = new_level
    user.completion_rate = pct
    db.commit()
    print(f"✅ {user.name}: {pct:.1f}% → {new_level} (was {old_level})")
