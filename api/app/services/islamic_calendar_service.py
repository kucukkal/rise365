import httpx
from datetime import datetime, date, timedelta
from typing import Optional, Tuple

async def get_eid_dates(year: int = None) -> dict:
    """Get Eid-ul-Fitr and Eid-ul-Adha dates from Aladhan API"""
    if year is None:
        year = datetime.now().year
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            # Get Hijri calendar for current year
            response = await client.get(
                f"https://api.aladhan.com/v1/islamicYearFromGregorianYear/{year}",
                timeout=10.0
            )
            data = response.json()

            eid_fitr = None
            eid_adha = None

            if data.get('data'):
                for month_data in data['data']:
                    for day in month_data.get('days', []):
                        hijri = day.get('hijri', {})
                        # Eid-ul-Fitr: 1 Shawwal
                        if hijri.get('month', {}).get('number') == 10 and \
                           hijri.get('day') == '1':
                            gregorian = day.get('gregorian', {})
                            eid_fitr = f"{gregorian.get('year')}-{gregorian.get('month', {}).get('number', '').zfill(2)}-{gregorian.get('day', '').zfill(2)}"
                        # Eid-ul-Adha: 10 Dhul Hijja
                        if hijri.get('month', {}).get('number') == 12 and \
                           hijri.get('day') == '10':
                            gregorian = day.get('gregorian', {})
                            eid_adha = f"{gregorian.get('year')}-{gregorian.get('month', {}).get('number', '').zfill(2)}-{gregorian.get('day', '').zfill(2)}"

            return {"eid_fitr": eid_fitr, "eid_adha": eid_adha}
    except Exception as e:
        print(f"Islamic calendar error: {e}")
        # Fallback approximate dates for 2026
        return {
            "eid_fitr": f"{year}-03-20",
            "eid_adha": f"{year}-05-27"
        }

async def get_ramadan_dates(year: int = None) -> dict:
    """Get Ramadan start and end dates"""
    if year is None:
        year = datetime.now().year
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.get(
                f"https://api.aladhan.com/v1/islamicYearFromGregorianYear/{year}",
                timeout=10.0
            )
            data = response.json()
            ramadan_start = None
            ramadan_end = None

            if data.get('data'):
                for month_data in data['data']:
                    for day in month_data.get('days', []):
                        hijri = day.get('hijri', {})
                        gregorian = day.get('gregorian', {})
                        g_date = f"{gregorian.get('year')}-{str(gregorian.get('month', {}).get('number', '')).zfill(2)}-{str(gregorian.get('day', '')).zfill(2)}"
                        # Ramadan = month 9
                        if hijri.get('month', {}).get('number') == 9:
                            if hijri.get('day') == '1' and not ramadan_start:
                                ramadan_start = g_date
                            ramadan_end = g_date

            return {"ramadan_start": ramadan_start, "ramadan_end": ramadan_end}
    except Exception as e:
        print(f"Ramadan dates error: {e}")
        # Approximate 2026 dates
        return {"ramadan_start": f"{year}-02-18", "ramadan_end": f"{year}-03-19"}

async def get_friday_zuhr_time(city: str = "Herndon", country: str = "US") -> str:
    """Get Zuhr prayer time for use as Jummah time"""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.get(
                "https://api.aladhan.com/v1/timingsByCity",
                params={"city": city, "country": country, "method": 2},
                timeout=10.0
            )
            data = response.json()
            zuhr = data["data"]["timings"]["Dhuhr"]
            # Format to HH:MM
            return zuhr.split(" ")[0]
    except:
        return "13:00"

def get_next_occurrence_weekly(day_of_week: int, start_time: str) -> datetime:
    """Get next occurrence of a weekly event"""
    today = date.today()
    days_ahead = day_of_week - today.weekday()
    if days_ahead < 0:
        days_ahead += 7
    elif days_ahead == 0:
        # Check if time has passed today
        h, m = map(int, start_time.split(":"))
        now = datetime.now()
        if now.hour > h or (now.hour == h and now.minute >= m):
            days_ahead = 7
    next_date = today + timedelta(days=days_ahead)
    h, m = map(int, start_time.split(":"))
    return datetime.combine(next_date, datetime.min.time().replace(hour=h, minute=m))

def get_next_occurrence_monthly(
    day_of_month: int = None,
    week_of_month: int = None,
    day_of_week: int = None,
    start_time: str = "09:00"
) -> datetime:
    """Get next occurrence of a monthly event"""
    today = date.today()
    h, m = map(int, start_time.split(":"))

    if day_of_month:
        # Specific day of month (e.g. 24th)
        try:
            candidate = today.replace(day=day_of_month)
            if candidate < today:
                if today.month == 12:
                    candidate = candidate.replace(year=today.year + 1, month=1)
                else:
                    candidate = candidate.replace(month=today.month + 1)
        except:
            candidate = today + timedelta(days=30)
        return datetime.combine(candidate, datetime.min.time().replace(hour=h, minute=m))
    elif week_of_month and day_of_week is not None:
        # Nth weekday (e.g. first Monday)
        import calendar
        month = today.month
        year = today.year
        for _ in range(3):
            first_day = date(year, month, 1)
            first_weekday = first_day.weekday()
            days_to_first = (day_of_week - first_weekday) % 7
            nth_day = 1 + days_to_first + (week_of_month - 1) * 7
            try:
                candidate = date(year, month, nth_day)
                if candidate >= today:
                    return datetime.combine(
                        candidate,
                        datetime.min.time().replace(hour=h, minute=m)
                    )
            except:
                pass
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
    return datetime.now() + timedelta(days=30)
