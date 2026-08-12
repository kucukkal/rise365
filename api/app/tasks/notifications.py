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
                               {"type": "prayer", "prayer": prayer_name, "tab": "prayer"})
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
            users_with_tokens = db.query(User).filter(
                User.fcm_token.isnot(None),
                User.is_active == True,
                User.role == "user",
            ).all()

            if not users_with_tokens:
                print("⚠️  No FCM tokens found")
                return

            # Send personalized count per user based on their pool type
            from app.models.program_level import ProgramLevel
            import uuid as _uuid
            sent = 0
            for user in users_with_tokens:
                # Get user level type
                user_level_type = "seed"
                if user.program_level_id:
                    try:
                        lv = db.query(ProgramLevel).filter(
                            ProgramLevel.id == _uuid.UUID(str(user.program_level_id))
                        ).first()
                        user_level_type = getattr(lv, "level_type", "seed") if lv else "seed"
                    except:
                        pass

                # Filter tasks by pool type
                if user_level_type == "myrise":
                    user_tasks = [t for t in daily_tasks
                                  if getattr(t, "pool_type", "myseed") in ("myrise", "both")]
                else:
                    user_tasks = [t for t in daily_tasks
                                  if getattr(t, "pool_type", "myseed") in ("myseed", "both")]

                if not user_tasks:
                    continue

                title = "Rise365 — Good morning!"
                body = f"You have {len(user_tasks)} daily task{'s' if len(user_tasks) > 1 else ''} today. Let's rise!"
                send_notification(user.fcm_token, title, body, {
                    "type": "daily_morning",
                    "tab": "tasks",
                    "frequency": "daily"
                })
                sent += 1
            print(f"✅ Daily morning: {sent} personalized notifications sent")

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
                        {"type": "daily_evening", "tab": "tasks", "frequency": "daily"}
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
                {"type": "weekly_monday", "tab": "tasks", "frequency": "weekly"})
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
                {"type": "monthly_start", "tab": "tasks", "frequency": "monthly"})
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
                        {"type": f"monthly_{period}", "tab": "tasks", "frequency": "monthly"}
                    )
    finally:
        db.close()

# ── Event reminders ───────────────────────────────────────────────────────────

@celery.task
def schedule_event_reminders():
    """Schedule reminders for upcoming events — runs daily at midnight"""
    from app.models.event import Event
    from app.services.islamic_calendar_service import (
        get_next_occurrence_weekly, get_next_occurrence_monthly
    )
    import asyncio

    db = SessionLocal()
    try:
        events = db.query(Event).filter(Event.is_active == True).all()
        now = datetime.now()

        for event in events:
            next_occ = None
            try:
                if event.event_type == "weekly" and event.day_of_week is not None:
                    next_occ = get_next_occurrence_weekly(
                        event.day_of_week, event.start_time or "09:00")
                elif event.event_type == "monthly":
                    next_occ = get_next_occurrence_monthly(
                        day_of_month=event.day_of_month,
                        week_of_month=event.week_of_month,
                        day_of_week=event.day_of_week,
                        start_time=event.start_time or "09:00"
                    )
                elif event.event_type == "fixed":
                    if event.fixed_type == "jummah":
                        next_occ = get_next_occurrence_weekly(
                            4, event.start_time or "13:00")
            except:
                continue

            if not next_occ:
                continue

            # Schedule reminders
            if event.event_type == "fixed" and event.fixed_type == "jummah":
                # Jummah: 1hr before only
                for hours_before in [1]:
                    fire_at = next_occ - timedelta(hours=hours_before)
                    if fire_at > now:
                        countdown = int((fire_at - now).total_seconds())
                        send_event_reminder.apply_async(
                            args=[str(event.id), hours_before, "hours"],
                            countdown=countdown
                        )
            elif event.event_type == "fixed" and event.fixed_type in ("eid_fitr", "eid_adha"):
                # Eid: 3 days, 1 day before
                for days_before in [3, 1]:
                    fire_at = next_occ - timedelta(days=days_before)
                    if fire_at > now:
                        countdown = int((fire_at - now).total_seconds())
                        send_event_reminder.apply_async(
                            args=[str(event.id), days_before, "days"],
                            countdown=countdown
                        )
            else:
                # User events: 1 day before, 2 hours before
                for reminder in [(1, "days"), (2, "hours")]:
                    amount, unit = reminder
                    if unit == "days":
                        fire_at = next_occ - timedelta(days=amount)
                    else:
                        fire_at = next_occ - timedelta(hours=amount)
                    if fire_at > now:
                        countdown = int((fire_at - now).total_seconds())
                        send_event_reminder.apply_async(
                            args=[str(event.id), amount, unit],
                            countdown=countdown
                        )

        print(f"✅ Event reminders scheduled for {len(events)} events")
    finally:
        db.close()

@celery.task
def send_event_reminder(event_id: str, amount: int, unit: str):
    """Send reminder for an event"""
    from app.models.event import Event
    db = SessionLocal()
    try:
        event = db.query(Event).filter(
            Event.id == uuid.UUID(event_id)
        ).first()
        if not event:
            return

        # Get tokens
        if event.user_id:
            user = db.query(User).filter(
                User.id == event.user_id,
                User.fcm_token.isnot(None)
            ).first()
            tokens = [user.fcm_token] if user else []
        else:
            tokens = _get_tokens(db)

        if not tokens:
            return

        if unit == "hours":
            time_str = f"{amount} hour{'s' if amount > 1 else ''}"
        else:
            time_str = f"{amount} day{'s' if amount > 1 else ''}"

        title = f"Rise365 — {event.name}"
        body = f"{event.name} starts in {time_str}"

        if amount == 2 and unit == "hours":
            body = f"⏰ {event.name} starts in 2 hours — don't forget!"
        elif amount == 1 and unit == "days":
            body = f"📅 {event.name} is tomorrow!"
        elif amount == 3 and unit == "days":
            body = f"📌 {event.name} is in 3 days"
        elif amount == 7 and unit == "days":
            body = f"🌙 {event.name} is one week away — start preparing!"

        count = send_multicast(tokens, title, body,
                               {"type": "event", "event_id": event_id})
        print(f"✅ Event reminder sent: {event.name} — {time_str} — {count} sent")
    finally:
        db.close()

@celery.task
def schedule_ramadan_reminders():
    """Schedule Ramadan start and Taraweeh reminders"""
    import asyncio
    from app.services.islamic_calendar_service import get_ramadan_dates

    loop = asyncio.new_event_loop()
    ramadan_dates = loop.run_until_complete(get_ramadan_dates())
    loop.close()

    now = datetime.now()
    today = now.date()

    try:
        ramadan_start = date.fromisoformat(ramadan_dates["ramadan_start"])
    except:
        return

    day_before = ramadan_start - timedelta(days=1)

    # Ramadan start reminders: 1 week, 3 days, 1 day before
    for days_before in [7, 3, 1]:
        fire_date = day_before - timedelta(days=days_before - 1)
        fire_dt = datetime.combine(fire_date, datetime.min.time().replace(
            hour=9, minute=0))
        if fire_dt > now:
            countdown = int((fire_dt - now).total_seconds())
            send_ramadan_reminder.apply_async(
                args=["ramadan_start", days_before],
                countdown=countdown
            )

    # Taraweeh reminders: 3hr and 1hr before each night
    if today <= day_before:
        fire_at_3hr = datetime.combine(day_before, datetime.min.time()
            .replace(hour=18, minute=30))
        fire_at_1hr = datetime.combine(day_before, datetime.min.time()
            .replace(hour=20, minute=30))

        for fire_at, hours in [(fire_at_1hr, 1)]:
            if fire_at > now:
                countdown = int((fire_at - now).total_seconds())
                send_taraweeh_reminder.apply_async(
                    args=[hours],
                    countdown=countdown
                )

    print("✅ Ramadan reminders scheduled")

@celery.task
def send_ramadan_reminder(reminder_type: str, days_before: int):
    db = SessionLocal()
    try:
        tokens = _get_tokens(db)
        if not tokens:
            return

        if reminder_type == "ramadan_start":
            if days_before == 7:
                title = "Rise365 — Ramadan is coming! 🌙"
                body = "One week until Ramadan! Start preparing your heart and routine."
            elif days_before == 3:
                title = "Rise365 — Ramadan in 3 days! 🌙"
                body = "3 days to go! Set your intentions and prepare for the blessed month."
            else:
                title = "Rise365 — Ramadan starts tomorrow! 🌙"
                body = "Ramadan Mubarak! The blessed month begins tonight at Maghrib."

        count = send_multicast(tokens, title, body,
                               {"type": "event", "fixed_type": "ramadan_start"})
        print(f"✅ Ramadan reminder sent: {count} notifications")
    finally:
        db.close()

@celery.task
def send_taraweeh_reminder(hours_before: int):
    db = SessionLocal()
    try:
        tokens = _get_tokens(db)
        if not tokens:
            return

        title = "Rise365 — Taraweeh tonight! 🤲"
        if hours_before == 3:
            body = "Taraweeh prayer starts in 3 hours. Don't miss the night prayer of Ramadan!"
        else:
            body = "Taraweeh begins in 1 hour! Get ready for your nightly worship."

        count = send_multicast(tokens, title, body,
                               {"type": "event", "fixed_type": "taraweeh"})
        print(f"✅ Taraweeh reminder ({hours_before}hr): {count} sent")
    finally:
        db.close()

# ── Monthly achievement level update ─────────────────────────────────────────

@celery.task
def update_monthly_achievements():
    """Run on last day of month — update achievement levels for all users"""
    from app.services.completion_service import update_monthly_achievement
    from app.models.user import UserRole
    db = SessionLocal()
    try:
        users = db.query(User).filter(
            User.role == UserRole.user,
            User.is_active == True,
        ).all()
        print(f"Updating achievements for {len(users)} users...")
        for user in users:
            try:
                update_monthly_achievement(user, db)
            except Exception as e:
                print(f"❌ Error for {user.name}: {e}")
        print("✅ Monthly achievements updated!")
    finally:
        db.close()

@celery.task
def update_weekly_achievements():
    """Run every Monday at 4 AM — update achievement levels for all users"""
    from app.services.completion_service import update_weekly_achievement
    from app.models.user import UserRole
    db = SessionLocal()
    try:
        users = db.query(User).filter(
            User.role == UserRole.user,
            User.is_active == True,
        ).all()
        print(f"Updating weekly achievements for {len(users)} users...")
        for user in users:
            try:
                update_weekly_achievement(user, db)
            except Exception as e:
                print(f"❌ Error for {user.name}: {e}")
        print("✅ Weekly achievements updated!")
    finally:
        db.close()
