from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DEFAULT_TZ = "America/New_York"  # Herndon, VA — used until a user sets a location


def tz_for(user=None) -> ZoneInfo:
    name = getattr(user, "timezone", None) or DEFAULT_TZ
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo(DEFAULT_TZ)


def local_now(user=None) -> datetime:
    return datetime.now(tz_for(user))


def to_utc_naive(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def day_start_local(user=None, hour: int = 4) -> datetime:
    """Start of the user's current day (4:00 AM local by default)."""
    now = local_now(user)
    start = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if now < start:
        start -= timedelta(days=1)
    return start
