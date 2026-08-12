from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery = Celery(
    "rise365",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.notifications"]
)

celery.conf.update(
    timezone="US/Eastern",
    enable_utc=True,
    beat_schedule={
        # ── Prayer reminders — at prayer time only ────────────────────
        "schedule-prayer-reminders": {
            "task": "app.tasks.notifications.schedule_daily_prayer_reminders",
            "schedule": crontab(hour=0, minute=5),
        },
        # ── Daily tasks ───────────────────────────────────────────────
        "daily-tasks-morning": {
            "task": "app.tasks.notifications.send_daily_task_reminder",
            "schedule": crontab(hour=9, minute=0),
            "args": ["morning"],
        },
        "daily-tasks-evening": {
            "task": "app.tasks.notifications.send_daily_task_reminder",
            "schedule": crontab(hour=21, minute=0),
            "args": ["evening"],
        },
        # ── Weekly tasks ──────────────────────────────────────────────
        "weekly-tasks-monday": {
            "task": "app.tasks.notifications.send_weekly_task_reminder",
            "schedule": crontab(hour=9, minute=0, day_of_week=1),
            "args": ["monday"],
        },
        "weekly-tasks-sunday": {
            "task": "app.tasks.notifications.send_weekly_task_reminder",
            "schedule": crontab(hour=9, minute=0, day_of_week=0),
            "args": ["sunday"],
        },
        # ── Monthly tasks ─────────────────────────────────────────────
        "monthly-tasks-start": {
            "task": "app.tasks.notifications.send_monthly_task_reminder",
            "schedule": crontab(hour=9, minute=0, day_of_month=1),
            "args": ["start"],
        },
        "monthly-tasks-end": {
            "task": "app.tasks.notifications.send_monthly_task_reminder",
            "schedule": crontab(hour=9, minute=0, day_of_month=28),
            "args": ["end"],
        },
        # ── Achievement update — Monday 9 AM ──────────────────────────
        "update-weekly-achievements": {
            "task": "app.tasks.notifications.update_weekly_achievements",
            "schedule": crontab(hour=9, minute=0, day_of_week=1),
        },
        # ── Ramadan reminders ─────────────────────────────────────────
        "schedule-ramadan-reminders": {
            "task": "app.tasks.notifications.schedule_ramadan_reminders",
            "schedule": crontab(hour=0, minute=15),
        },
        "schedule-event-reminders": {
            "task": "app.tasks.notifications.schedule_event_reminders",
            "schedule": crontab(hour=0, minute=10),
        },
        # ── Monthly tasks ─────────────────────────────────────────────
        "monthly-tasks-day-1": {
            "task": "app.tasks.notifications.send_monthly_task_reminder",
            "schedule": crontab(hour=9, minute=0, day_of_month=1),
            "args": ["start"],
        },
        "monthly-tasks-day-14": {
            "task": "app.tasks.notifications.send_monthly_task_reminder",
            "schedule": crontab(hour=9, minute=0, day_of_month=14),
            "args": ["mid"],
        },
        "monthly-tasks-day-28": {
            "task": "app.tasks.notifications.send_monthly_task_reminder",
            "schedule": crontab(hour=9, minute=0, day_of_month=28),
            "args": ["end"],
        },
    }
)
