from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PrayerCompleteRequest(BaseModel):
    prayer_name: str

class PrayerTimeResponse(BaseModel):
    name: str
    display_name: str
    arabic_name: str
    time: str
    points: int
    is_completed: bool = False
    is_locked: bool = False
    window_expired: bool = False
    minutes_left: Optional[int] = None

class DailyPrayersResponse(BaseModel):
    date: str
    location: str
    level_order: int
    evrad_required: bool
    evrad_completed: bool
    prayers: List[PrayerTimeResponse]
    total_completed: int
    total_points_earned: int
