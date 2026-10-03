from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery = Celery(
    "rise365",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.reminders"],
)

celery.conf.update(
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        # One job every 5 minutes. It checks each user's own local time and
        # location, and sends prayer / task reminders and the weekly level update
        # when they're due (see app/tasks/reminders.py).
        "reminders-tick": {
            "task": "app.tasks.reminders.tick",
            "schedule": crontab(minute="*/5"),
        },
    },
)
