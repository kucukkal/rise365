from celery_app import celery
from app.database import SessionLocal
from app.models.user import User
from app.models.task import Task, TaskCompletion, TaskFrequency
from app.models.prayer import PrayerLog
from app.services.notification_service import send_multicast, send_notification
from app.services.prayer_service import DISPLAY_NAMES
from datetime import datetime, timedelta
from sqlalchemy import and_
import httpx

OBLIGATORY_PRAYERS = ["fajr", "dhuhr", "asr", "maghrib", "isha"]

PRAYER_DISPLAY = {
    "fajr": "Fajr", "dhuhr": "Dhuhr",
    "asr": "Asr", "maghrib": "Maghrib", "isha": "Isha"
}

def _get_tokens(db, exclude_ids=None):
    q = db.query(User.fcm_token).filter(
        User.fcm_token.isnot(None),
        User.is_active == True
    )
    if exclude_ids:
        q = q.filter(~User.id.in_(exclude_ids))
    return [r[0] for r in q.all() if r[0]]

def _today_start():
    return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

def _get_prayer_times_sync(city="Herndon", country="US"):
    try:
        import asyncio
        from app.services.prayer_service import get_prayer_times
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            get_prayer_times(city=city, country=country)
        )
        loop.close()
        return {p["name"]: p["time"] for p in result if p["name"] in OBLIGATORY_PRAYERS}
    except Exception as e:
        print(f"Prayer times error: {e}")
        return {
            "fajr": "5:12 AM", "dhuhr": "1:07 PM",
            "asr": "4:42 PM", "maghrib": "8:09 PM", "isha": "9:30 PM"
        }

def _parse_time(time_str: str) -> datetime:
    now = datetime.now()
    try:
        t = datetime.strptime(time_str.strip(), "%I:%M %p")
        return now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    except:
        return now

# ── Prayer reminders ──────────────────────────────────────────────────────────

@celery.task
def schedule_daily_prayer_reminders():
    """Runs at midnight — schedules all prayer reminders for today"""
    times = _get_prayer_times_sync()
    for prayer_name, time_str in times.items():
        prayer_dt = _parse_time(time_str)
        now = datetime.now()

        for delay_minutes, reminder_num in [(0, 1), (20, 2), (40, 3)]:
            fire_at = prayer_dt + timedelta(minutes=delay_minutes)
            if fire_at > now:
                countdown = int((fire_at - now).total_seconds())
                send_prayer_reminder.apply_async(
                    args=[prayer_name, reminder_num, time_str],
                    countdown=countdown
                )
    print(f"✅ Prayer reminders scheduled for {datetime.now().strftime('%Y-%m-%d')}")

@celery.task
def send_prayer_reminder(prayer_name: str, reminder_num: int, prayer_time: str):
    """Sends prayer reminder — only to users who haven't completed it"""
    db = SessionLocal()
    today_start = _today_start()
    display = PRAYER_DISPLAY.get(prayer_name, prayer_name)

    try:
        # Find users who completed this prayer
        completed_user_ids = [
            r[0] for r in db.query(PrayerLog.user_id).filter(
                and_(
                    PrayerLog.prayer_name == prayer_name,
                    PrayerLog.prayer_date >= today_start,
                    PrayerLog.is_completed == True,
                )
            ).all()
        ]

        # Get tokens of users who have NOT completed it
        tokens = _get_tokens(db, exclude_ids=completed_user_ids)
        if not tokens:
            return

        # Build message based on reminder number
        if reminder_num == 1:
            title = f"{display} prayer time"
            body = f"It's time for {display} ({prayer_time})"
        elif reminder_num == 2:
            title = f"{display} reminder"
            body = f"{display} prayer — 20 minutes have passed"
        else:
            title = f"Last call — {display}"
            body = f"40 minutes since {display} ({prayer_time}) — don't miss it"

        count = send_multicast(tokens, title, body,
                               {"type": "prayer", "prayer": prayer_name})
        print(f"✅ {display} reminder {reminder_num}: {count}/{len(tokens)} sent")

    finally:
        db.close()

# ── Daily task reminders ──────────────────────────────────────────────────────

@celery.task
def send_daily_task_reminder(period: str):
    """9 AM: all users. 9 PM: only users with incomplete tasks"""
    db = SessionLocal()
    today_start = _today_start()

    try:
        daily_tasks = db.query(Task).filter(
            Task.frequency == TaskFrequency.daily,
            Task.is_active == True
        ).all()

        if not daily_tasks:
            return

        if period == "morning":
            tokens = _get_tokens(db)
            print(f"📱 Found {len(tokens)} users with FCM tokens")
            print(f"📋 Found {len(daily_tasks)} daily tasks")
            if not tokens:
                print("⚠️  No FCM tokens found — no notifications sent")
                return
            title = "Rise365 — Good morning!"
            body = f"You have {len(daily_tasks)} daily tasks today. Let's rise!"
            count = send_multicast(tokens, title, body, {"type": "daily_morning"})
            print(f"✅ Daily morning: {count}/{len(tokens)} sent")

        else:  # evening — only uncompleted
            all_users = db.query(User).filter(
                User.fcm_token.isnot(None),
                User.is_active == True
            ).all()

            for user in all_users:
                completed_ids = {
                    r[0] for r in db.query(TaskCompletion.task_id).filter(
                        and_(
                            TaskCompletion.user_id == user.id,
                            TaskCompletion.period_start >= today_start,
                        )
                    ).all()
                }
                pending = [t for t in daily_tasks if t.id not in completed_ids]
                if pending and user.fcm_token:
                    send_notification(
                        user.fcm_token,
                        "Rise365 — Evening check-in",
                        f"You have {len(pending)} daily task{'s' if len(pending)>1 else ''} still to complete",
                        {"type": "daily_evening"}
                    )
    finally:
        db.close()

# ── Weekly task reminders ─────────────────────────────────────────────────────

@celery.task
def send_weekly_task_reminder(day: str):
    """Monday: all users. Friday/Sunday: only uncompleted"""
    db = SessionLocal()
    now = datetime.utcnow()
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)

    try:
        weekly_tasks = db.query(Task).filter(
            Task.frequency == TaskFrequency.weekly,
            Task.is_active == True
        ).all()

        if not weekly_tasks:
            return

        if day == "monday":
            tokens = _get_tokens(db)
            send_multicast(tokens,
                "Rise365 — New week!",
                f"A fresh week begins. You have {len(weekly_tasks)} weekly tasks",
                {"type": "weekly_monday"})
        else:
            day_labels = {"friday": "Friday", "sunday": "Sunday"}
            all_users = db.query(User).filter(
                User.fcm_token.isnot(None),
                User.is_active == True
            ).all()

            for user in all_users:
                completed_ids = {
                    r[0] for r in db.query(TaskCompletion.task_id).filter(
                        and_(
                            TaskCompletion.user_id == user.id,
                            TaskCompletion.period_start >= week_start,
                        )
                    ).all()
                }
                pending = [t for t in weekly_tasks if t.id not in completed_ids]
                if pending and user.fcm_token:
                    suffix = "last day" if day == "sunday" else day_labels[day]
                    send_notification(
                        user.fcm_token,
                        f"Rise365 — {day_labels[day]} reminder",
                        f"{len(pending)} weekly task{'s' if len(pending)>1 else ''} still pending — {suffix} to finish",
                        {"type": f"weekly_{day}"}
                    )
    finally:
        db.close()

# ── Monthly task reminders ────────────────────────────────────────────────────

@celery.task
def send_monthly_task_reminder(period: str):
    """1st: all users. 14th/28th: only uncompleted"""
    db = SessionLocal()
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    try:
        monthly_tasks = db.query(Task).filter(
            Task.frequency == TaskFrequency.monthly,
            Task.is_active == True
        ).all()

        if not monthly_tasks:
            return

        if period == "start":
            tokens = _get_tokens(db)
            send_multicast(tokens,
                "Rise365 — New month!",
                f"A new month begins. {len(monthly_tasks)} monthly tasks assigned",
                {"type": "monthly_start"})
        else:
            labels = {"mid": ("14th", "halfway through"),
                      "end": ("28th", "3 days left")}
            day_label, time_label = labels.get(period, ("", ""))

            all_users = db.query(User).filter(
                User.fcm_token.isnot(None),
                User.is_active == True
            ).all()

            for user in all_users:
                completed_ids = {
                    r[0] for r in db.query(TaskCompletion.task_id).filter(
                        and_(
                            TaskCompletion.user_id == user.id,
                            TaskCompletion.period_start >= month_start,
                        )
                    ).all()
                }
                pending = [t for t in monthly_tasks if t.id not in completed_ids]
                if pending and user.fcm_token:
                    send_notification(
                        user.fcm_token,
                        f"Rise365 — {day_label} of the month",
                        f"{time_label.capitalize()} — {len(pending)} monthly task{'s' if len(pending)>1 else ''} still to complete",
                        {"type": f"monthly_{period}"}
                    )
    finally:
        db.close()
