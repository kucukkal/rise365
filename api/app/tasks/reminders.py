"""Per-user reminders, sent in each user's own time zone and location.

A single job (`tick`) runs every 5 minutes. For each user it works out their local
time and sends whatever is due:
  • Prayer      — once, at the start of each of the 5 daily prayers (user's location)
  • Daily tasks — 9:00 AM (everyone) and 9:00 PM (only if daily tasks are unfinished)
  • Weekly      — Sunday 5:00 PM (only if weekly tasks are unfinished)
  • Monthly     — 28th, 5:00 PM (only if monthly tasks are unfinished)
  • Achievement — Monday 3:45 AM: stores last week's % (the level follows from it)
Each reminder is recorded in Redis, so nothing is sent twice.
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone

import redis

from celery_app import celery
from app.config import settings
from app.database import SessionLocal
from app.models.user import User
from app.models.task import Task, TaskCompletion, TaskFrequency
from app.models.prayer import PrayerLog
from app.services.notification_service import send_notification
from app.services.timeutil import tz_for, day_start_local, to_utc_naive, DEFAULT_TZ

PRAYERS = ["fajr", "dhuhr", "asr", "maghrib", "isha"]
NAMES = {"fajr": "Fajr", "dhuhr": "Dhuhr", "asr": "Asr", "maghrib": "Maghrib", "isha": "Isha"}
WINDOW = timedelta(minutes=15)  # tick runs every 5 min; 15 min tolerates delays

_redis = None


def _r():
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL)
    return _redis


def _once(key: str, ttl_days: int = 3) -> bool:
    """True the first time a key is seen (then remembered for a few days)."""
    return bool(_r().set(f"rise365:reminder:{key}", "1", nx=True, ex=ttl_days * 86400))


def _due(now_local: datetime, target_local: datetime) -> bool:
    return target_local <= now_local < target_local + WINDOW


def _prayer_times(user, local_date: str) -> dict:
    """Today's 5 prayer times for the user's location, cached in Redis per place and day."""
    lat, lng = user.latitude, user.longitude
    tzname = user.timezone or DEFAULT_TZ
    place = f"{round(lat, 3)},{round(lng, 3)}" if lat is not None and lng is not None else "default"
    key = f"rise365:prayertimes:{place}:{tzname}:{local_date}"
    cached = _r().get(key)
    if cached:
        return json.loads(cached)
    from app.services.prayer_service import get_prayer_times
    try:
        res = asyncio.run(get_prayer_times(latitude=lat, longitude=lng, tz=tzname))
        times = {p["name"]: p["time"] for p in res if p["name"] in PRAYERS}
    except Exception as e:
        print(f"reminders: prayer times error for {place}: {e}")
        return {}
    _r().set(key, json.dumps(times), ex=2 * 86400)
    return times


def _pending(db, user, freq: TaskFrequency) -> int:
    """Number of unfinished tasks of this frequency in the user's current period."""
    from app.services.completion_service import get_pool_filter
    from app.routers.tasks import get_period_range
    ids = {r[0] for r in db.query(Task.id).filter(
        Task.is_active == True, Task.frequency == freq, get_pool_filter(user, db)).all()}
    if not ids:
        return 0
    start, _ = get_period_range(freq.value, user=user)
    done = {r[0] for r in db.query(TaskCompletion.task_id).filter(
        TaskCompletion.user_id == user.id, TaskCompletion.period_start >= start).all()}
    return len(ids - done)


def _user_tick(db, u: User, now: datetime, dry_run: bool) -> int:
    now_l = now.astimezone(tz_for(u))
    today = now_l.date().isoformat()
    uid = str(u.id)

    def at(h, m=0):
        return now_l.replace(hour=h, minute=m, second=0, microsecond=0)

    def send(kind, key, title, body, data):
        if dry_run:
            print(f"   [would send] {u.name}: {title} — {body}")
            return 1
        if not u.fcm_token or not _once(f"{uid}:{kind}:{key}"):
            return 0
        send_notification(u.fcm_token, title, body, data)
        return 1

    sent = 0

    # Prayers — once, at the start of each prayer time
    times = _prayer_times(u, today)
    day_start = to_utc_naive(day_start_local(u))
    done = {r[0] for r in db.query(PrayerLog.prayer_name).filter(
        PrayerLog.user_id == u.id, PrayerLog.prayer_date >= day_start,
        PrayerLog.is_completed == True).all()}
    for p in PRAYERS:
        t = times.get(p)
        if not t:
            continue
        try:
            tt = datetime.strptime(t.strip(), "%I:%M %p")
        except ValueError:
            continue
        if p not in done and _due(now_l, at(tt.hour, tt.minute)):
            sent += send("prayer", f"{today}:{p}", f"{NAMES[p]} prayer time",
                         f"It's time for {NAMES[p]} ({t})",
                         {"type": "prayer", "tab": "prayer", "prayer": p})

    # Daily tasks — 9 AM everyone, 9 PM only if unfinished
    if _due(now_l, at(9)):
        sent += send("daily_am", today, "Rise365 — Good morning",
                     "Your daily tasks are ready. Let's rise!",
                     {"type": "daily_morning", "tab": "tasks", "frequency": "daily"})
    if _due(now_l, at(21)):
        k = _pending(db, u, TaskFrequency.daily)
        if k:
            sent += send("daily_pm", today, "Rise365 — Evening check-in",
                         f"You have {k} daily task{'s' if k > 1 else ''} left today",
                         {"type": "daily_evening", "tab": "tasks", "frequency": "daily"})

    # Weekly — Sunday 5 PM, only if unfinished
    if now_l.weekday() == 6 and _due(now_l, at(17)):
        k = _pending(db, u, TaskFrequency.weekly)
        if k:
            sent += send("weekly", today, "Rise365 — Weekly tasks",
                         f"{k} weekly task{'s' if k > 1 else ''} left. The week ends tonight.",
                         {"type": "weekly_sunday", "tab": "tasks", "frequency": "weekly"})

    # Monthly — 28th 5 PM, only if unfinished
    if now_l.day == 28 and _due(now_l, at(17)):
        k = _pending(db, u, TaskFrequency.monthly)
        if k:
            sent += send("monthly", today, "Rise365 — Monthly tasks",
                         f"{k} monthly task{'s' if k > 1 else ''} left this month",
                         {"type": "monthly_end", "tab": "tasks", "frequency": "monthly"})

    # Weekly achievement — Monday 3:45 AM local, just before the new week starts at 4 AM
    if now_l.weekday() == 0 and _due(now_l, at(3, 45)):
        if dry_run:
            print(f"   [would update] {u.name}: weekly achievement level")
        elif _once(f"{uid}:achievement:{today}", ttl_days=8):
            from app.services.completion_service import calculate_weighted_completion
            u.completion_rate = calculate_weighted_completion(u, db)
            db.commit()

    return sent


@celery.task(name="app.tasks.reminders.tick")
def tick(now_utc: str = None, dry_run: bool = False) -> int:
    """Send everything that's due. now_utc / dry_run are for testing only."""
    now = (datetime.fromisoformat(now_utc).replace(tzinfo=timezone.utc)
           if now_utc else datetime.now(timezone.utc))
    db = SessionLocal()
    total = 0
    try:
        for u in db.query(User).filter(User.is_active == True).all():
            try:
                total += _user_tick(db, u, now, dry_run)
            except Exception as e:
                db.rollback()
                print(f"reminders: error for user {u.id}: {e}")
    finally:
        db.close()
    if total:
        print(f"reminders: {total} sent")
    return total


def preview() -> None:
    """Print each user's location, time zone and today's prayer times (for testing)."""
    db = SessionLocal()
    try:
        for u in db.query(User).filter(User.is_active == True).all():
            now_l = datetime.now(tz_for(u))
            times = _prayer_times(u, now_l.date().isoformat())
            print(f"{u.name:20} {u.location_label or 'default (Herndon)':22} "
                  f"{(u.timezone or DEFAULT_TZ):22} now {now_l:%H:%M}  "
                  + "  ".join(f"{NAMES[p]} {times.get(p, '?')}" for p in PRAYERS)
                  + ("" if u.fcm_token else "   (no push token)"))
    finally:
        db.close()
