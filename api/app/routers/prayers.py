from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.prayer import PrayerLog
from app.models.program_level import ProgramLevel
from app.core.dependencies import get_current_user
from app.services.prayer_service import get_prayer_times, PRAYER_POINTS, DISPLAY_NAMES, EVRAD_POINTS
from pydantic import BaseModel

router = APIRouter()

class PrayerCompleteRequest(BaseModel):
    prayer_name: str

def _get_level_order(user: User, db: Session) -> int:
    if not user.program_level_id:
        return 0
    try:
        import uuid as _uuid
        level = db.query(ProgramLevel).filter(
            ProgramLevel.id == _uuid.UUID(str(user.program_level_id))
        ).first()
        return level.order if level else 0
    except:
        return 0

def _today_start(user=None):
    """Start of the user's prayer day: 4:00 AM in their own time zone (as UTC)."""
    from app.services.timeutil import day_start_local, to_utc_naive
    return to_utc_naive(day_start_local(user))

@router.get("/today")
async def get_today_prayers(
    city: str = "Herndon",
    country: str = "US",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today_start = _today_start(current_user)
    level_order = _get_level_order(current_user, db)

    completed_logs = db.query(PrayerLog).filter(
        and_(
            PrayerLog.user_id == current_user.id,
            PrayerLog.prayer_date >= today_start,
            PrayerLog.is_completed == True
        )
    ).all()

    completed_names = {log.prayer_name for log in completed_logs}
    total_points = sum(log.points_earned for log in completed_logs)

    prayers = await get_prayer_times(
        city=city,
        country=country,
        level_order=level_order,
        completed_names=completed_names,
        latitude=getattr(current_user, "latitude", None),
        longitude=getattr(current_user, "longitude", None),
        tz=getattr(current_user, "timezone", None),
    )

    # Count only main prayers (not evrad entries)
    main_prayers = [p for p in prayers]
    completed_count = sum(1 for p in main_prayers if p["is_completed"])

    return {
        "date": __import__("app.services.timeutil", fromlist=["local_now"]).local_now(current_user).strftime("%A, %B %d"),
        "location": getattr(current_user, "location_label", None) or f"{city}, {country}",
        "level_order": level_order,
        "prayers": prayers,
        "total_completed": completed_count,
        "total_points_earned": total_points,
    }

@router.post("/complete")
def complete_prayer(
    request: PrayerCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today_start = _today_start(current_user)
    prayer_name = request.prayer_name
    level_order = _get_level_order(current_user, db)
    is_evrad = prayer_name.endswith("_evrad")

    # If completing main prayer, check evrad done first (level 1+)
    if not is_evrad and level_order >= 1:
        evrad_name = f"{prayer_name}_evrad"
        evrad_done = db.query(PrayerLog).filter(
            and_(
                PrayerLog.user_id == current_user.id,
                PrayerLog.prayer_name == evrad_name,
                PrayerLog.prayer_date >= today_start,
                PrayerLog.is_completed == True,
            )
        ).first()
        if not evrad_done:
            base_name = prayer_name.replace("_evrad", "")
            display = DISPLAY_NAMES.get(base_name, base_name)
            raise HTTPException(
                status_code=400,
                detail=f"Complete Evrad-u Ezkar / Zikr for {display} first"
            )

    # Check existing
    existing = db.query(PrayerLog).filter(
        and_(
            PrayerLog.user_id == current_user.id,
            PrayerLog.prayer_name == prayer_name,
            PrayerLog.prayer_date >= today_start,
        )
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        from app.services.completion_service import calculate_total_points
        live_points = calculate_total_points(current_user, db)
        return {"message": f"{prayer_name} unmarked", "total_points": live_points}

    from app.services.completion_service import calculate_total_points
    points = EVRAD_POINTS if is_evrad else PRAYER_POINTS.get(prayer_name, 10)
    log = PrayerLog(
        user_id=current_user.id,
        prayer_name=prayer_name,
        prayer_date=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        points_earned=points,
        is_completed=True,
    )
    db.add(log)
    db.commit()

    display = DISPLAY_NAMES.get(prayer_name.replace("_evrad", ""), prayer_name)
    return {
        "message": f"{display} {'Evrad' if is_evrad else ''} completed",
        "points_earned": points,
        "total_points": calculate_total_points(current_user, db),
    }
