from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, date
from app.database import get_db
from app.models.user import User
from app.models.prayer import PrayerLog, PrayerName
from app.schemas.prayer import PrayerCompleteRequest, DailyPrayersResponse
from app.core.dependencies import get_current_user
from app.services.prayer_service import get_prayer_times, ARABIC_NAMES, PRAYER_POINTS

router = APIRouter()

@router.get("/today")
async def get_today_prayers(
    city: str = "Herndon",
    country: str = "US",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prayer_times = await get_prayer_times(city, country)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    completed_logs = db.query(PrayerLog).filter(
        and_(
            PrayerLog.user_id == current_user.id,
            PrayerLog.prayer_date >= today_start,
            PrayerLog.is_completed == True
        )
    ).all()

    completed_names = {log.prayer_name.value for log in completed_logs}
    total_points = sum(log.points_earned for log in completed_logs)

    for prayer in prayer_times:
        prayer["is_completed"] = prayer["name"] in completed_names

    return {
        "date": datetime.utcnow().strftime("%A, %B %d"),
        "location": f"{city}, {country}",
        "prayers": prayer_times,
        "total_completed": len(completed_names),
        "total_points_earned": total_points
    }

@router.post("/complete")
def complete_prayer(
    request: PrayerCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    existing = db.query(PrayerLog).filter(
        and_(
            PrayerLog.user_id == current_user.id,
            PrayerLog.prayer_name == request.prayer_name,
            PrayerLog.prayer_date >= today_start,
        )
    ).first()

    if existing:
        # Undo
        current_user.total_points = max(0, current_user.total_points - existing.points_earned)
        db.delete(existing)
        db.commit()
        return {"message": "Prayer unmarked", "prayer": request.prayer_name}

    points = PRAYER_POINTS.get(request.prayer_name.value, 10)
    log = PrayerLog(
        user_id=current_user.id,
        prayer_name=request.prayer_name,
        prayer_date=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        points_earned=points,
        is_completed=True
    )
    db.add(log)
    current_user.total_points += points
    db.commit()

    return {
        "message": "Prayer completed",
        "prayer": request.prayer_name,
        "points_earned": points,
        "total_points": current_user.total_points
    }
