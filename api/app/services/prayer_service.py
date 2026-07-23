import httpx
from datetime import datetime

ARABIC_NAMES = {
    "fajr": "الفجر",
    "dhuhr": "الظهر",
    "asr": "العصر",
    "maghrib": "المغرب",
    "isha": "العشاء"
}

PRAYER_POINTS = {
    "fajr": 15,
    "dhuhr": 10,
    "asr": 10,
    "maghrib": 10,
    "isha": 10
}

async def get_prayer_times(city: str = "Herndon", country: str = "US"):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.aladhan.com/v1/timingsByCity",
                params={
                    "city": city,
                    "country": country,
                    "method": 2  # ISNA method
                }
            )
            data = response.json()
            timings = data["data"]["timings"]

            prayers = []
            for name in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
                key = name.lower()
                prayers.append({
                    "name": key,
                    "arabic_name": ARABIC_NAMES[key],
                    "time": timings[name],
                    "points": PRAYER_POINTS[key],
                    "is_completed": False
                })
            return prayers
    except Exception as e:
        print(f"Prayer times error: {e}")
        # Fallback times
        return [
            {"name": "fajr", "arabic_name": "الفجر", "time": "5:12 AM", "points": 15, "is_completed": False},
            {"name": "dhuhr", "arabic_name": "الظهر", "time": "1:07 PM", "points": 10, "is_completed": False},
            {"name": "asr", "arabic_name": "العصر", "time": "4:42 PM", "points": 10, "is_completed": False},
            {"name": "maghrib", "arabic_name": "المغرب", "time": "8:09 PM", "points": 10, "is_completed": False},
            {"name": "isha", "arabic_name": "العشاء", "time": "9:30 PM", "points": 10, "is_completed": False},
        ]
