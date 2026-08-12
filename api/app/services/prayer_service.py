import httpx
from datetime import datetime, timedelta

PRAYER_ORDER = ["fajr", "duha", "dhuhr", "asr", "maghrib", "awwabin", "isha", "qiyam"]
EVRAD_POINTS = 20

DISPLAY_NAMES = {
    "fajr": "Fajr", "duha": "Salat-ul Duha", "dhuhr": "Dhuhr",
    "asr": "Asr", "maghrib": "Maghrib", "awwabin": "Ṣalāt al-Awwābīn",
    "isha": "Isha", "qiyam": "Qiyam al-Layl",
}

ARABIC_NAMES = {
    "fajr": "الفجر", "duha": "الضحى", "dhuhr": "الظهر", "asr": "العصر",
    "maghrib": "المغرب", "awwabin": "الأوابين", "isha": "العشاء", "qiyam": "قيام الليل",
}

PRAYER_POINTS = {
    "fajr": 150, "duha": 100, "dhuhr": 150, "asr": 150,
    "maghrib": 150, "awwabin": 100, "isha": 150, "qiyam": 100,
    "evrad": 35,
}

def _format_time(time_str: str) -> str:
    try:
        t = datetime.strptime(time_str.split(" ")[0], "%H:%M")
        return t.strftime("%I:%M %p").lstrip("0")
    except:
        return time_str

def _add_minutes(time_str: str, minutes: int) -> str:
    try:
        t = datetime.strptime(time_str.split(" ")[0], "%H:%M")
        t += timedelta(minutes=minutes)
        return t.strftime("%I:%M %p").lstrip("0")
    except:
        return time_str

def _window_expired(prayer_time_str: str, window_minutes: int = 45) -> bool:
    try:
        t = datetime.strptime(prayer_time_str.split(" ")[0], "%H:%M")
        now = datetime.now()
        prayer_dt = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        diff = (now - prayer_dt).total_seconds() / 60
        return diff > window_minutes
    except:
        return False

def _minutes_left(prayer_time_str: str, window_minutes: int = 45) -> int:
    try:
        t = datetime.strptime(prayer_time_str.split(" ")[0], "%H:%M")
        now = datetime.now()
        prayer_dt = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        diff = (now - prayer_dt).total_seconds() / 60
        return max(0, int(window_minutes - diff))
    except:
        return window_minutes

async def get_prayer_times(
    city: str = "Herndon",
    country: str = "US",
    level_order: int = 0,
    completed_names: set = None,
):
    if completed_names is None:
        completed_names = set()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.aladhan.com/v1/timingsByCity",
                params={"city": city, "country": country, "method": 2},
                timeout=10.0,
            )
            data = response.json()
            timings = data["data"]["timings"]
            times = {
                "fajr":    _format_time(timings["Fajr"]),
                "duha":    _add_minutes(timings.get("Sunrise", "06:00"), 30),
                "dhuhr":   _format_time(timings["Dhuhr"]),
                "asr":     _format_time(timings["Asr"]),
                "maghrib": _format_time(timings["Maghrib"]),
                "awwabin": _add_minutes(timings["Maghrib"], 5),
                "isha":    _format_time(timings["Isha"]),
                "qiyam":   _add_minutes(timings.get("Isha", "21:30"), 90),
            }
    except Exception as e:
        print(f"Prayer times API error: {e}")
        times = {
            "fajr": "5:12 AM", "duha": "7:15 AM", "dhuhr": "1:07 PM",
            "asr": "4:42 PM", "maghrib": "8:09 PM", "awwabin": "8:14 PM",
            "isha": "9:30 PM", "qiyam": "11:00 PM",
        }

    prayers = []
    for name in PRAYER_ORDER:
        evrad_name = f"{name}_evrad"
        evrad_required = level_order >= 1
        evrad_completed = evrad_name in completed_names if evrad_required else False
        is_completed = name in completed_names

        # Locked if evrad not done yet (level 1+)
        is_locked = evrad_required and not evrad_completed and not is_completed

        # Level 2+: 45 min window
        window_expired = False
        minutes_left = None
        if level_order >= 2 and not is_completed:
            window_expired = _window_expired(times[name])
            if window_expired:
                is_locked = True
            else:
                ml = _minutes_left(times[name])
                if ml < 45:
                    minutes_left = ml

        prayers.append({
            "name": name,
            "display_name": DISPLAY_NAMES[name],
            "arabic_name": ARABIC_NAMES[name],
            "time": times[name],
            "points": PRAYER_POINTS[name],
            "is_completed": is_completed,
            "is_locked": is_locked,
            "window_expired": window_expired,
            "minutes_left": minutes_left,
            "evrad_name": evrad_name,
            "evrad_required": evrad_required,
            "evrad_completed": evrad_completed,
            "evrad_points": EVRAD_POINTS,
        })

    return prayers
