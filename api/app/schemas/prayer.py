from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
from datetime import datetime

class PrayerName(str, Enum):
    fajr = "fajr"
    dhuhr = "dhuhr"
    asr = "asr"
    maghrib = "maghrib"
    isha = "isha"

class PrayerTimeResponse(BaseModel):
    name: PrayerName
    arabic_name: str
    time: str
    points: int
    is_completed: bool = False

class PrayerCompleteRequest(BaseModel):
    prayer_name: PrayerName

class DailyPrayersResponse(BaseModel):
    date: str
    location: str
    prayers: List[PrayerTimeResponse]
    total_completed: int
    total_points_earned: int
