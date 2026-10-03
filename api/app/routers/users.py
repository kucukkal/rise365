from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.core.dependencies import get_current_user

router = APIRouter()

@router.get("/me")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.program_level import ProgramLevel
    level_name = None
    if current_user.program_level_id:
        try:
            import uuid as _uuid
            lv = db.query(ProgramLevel).filter(
                ProgramLevel.id == _uuid.UUID(str(current_user.program_level_id))
            ).first()
            if lv:
                level_name = "MyRise" if lv.level_type == "myrise" else lv.name
        except:
            level_name = str(current_user.program_level_id)

    # Calculate live weighted completion % and current period points
    try:
        from app.services.completion_service import (
            calculate_weighted_completion, calculate_total_points
        )
        live_pct = calculate_weighted_completion(current_user, db)
        live_points = calculate_total_points(current_user, db)
        print(f"✅ {current_user.name}: {live_pct}% | {live_points} pts")
    except Exception as e:
        print(f"❌ Completion calc error: {e}")
        import traceback
        traceback.print_exc()
        live_pct = current_user.completion_rate
        live_points = current_user.total_points

    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "first_name": getattr(current_user, "first_name", None),
        "last_name": getattr(current_user, "last_name", None),
        "location_label": getattr(current_user, "location_label", None),
        "zip_code": getattr(current_user, "zip_code", None),
        "city": getattr(current_user, "city", None),
        "state": getattr(current_user, "state", None),
        "timezone": getattr(current_user, "timezone", None),
        "phone": current_user.phone,
        "program_level_id": current_user.program_level_id,
        "program_level": level_name or "Level 1",
        "achievement_level": current_user.achievement_level,
        "total_points": live_points,
        "completion_rate": live_pct,
    }

@router.put("/fcm-token")
def update_fcm_token(
    fcm_token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.fcm_token = fcm_token
    db.commit()
    return {"message": "FCM token updated"}

@router.get("/progress")
def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {
        "total_points": current_user.total_points,
        "completion_rate": current_user.completion_rate,
        "achievement_level": current_user.achievement_level,
        "next_level": _get_next_level(current_user.achievement_level),
        "points_to_next": _points_to_next(current_user.completion_rate)
    }

def _get_next_level(current: str) -> str:
    levels = ["Starter", "Bronze", "Silver", "Gold", "Sapphire", "Diamond"]
    idx = levels.index(current) if current in levels else 0
    return levels[idx + 1] if idx < len(levels) - 1 else "Max Level"

def _points_to_next(rate: float) -> str:
    if rate < 50: return f"{50 - rate:.1f}% more to Bronze"
    if rate < 60: return f"{60 - rate:.1f}% more to Silver"
    if rate < 71: return f"{71 - rate:.1f}% more to Gold"
    if rate < 81: return f"{81 - rate:.1f}% more to Sapphire"
    if rate < 91: return f"{91 - rate:.1f}% more to Diamond"
    return "Maximum level reached!"


@router.delete("/me")
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Apple guideline 5.1.1(v): users can delete their account in the app."""
    from fastapi import HTTPException
    from app.models.user import UserRole
    from app.services.account_service import delete_user_account
    if current_user.role == UserRole.admin:
        raise HTTPException(400, "Admin accounts can't be deleted from the app")
    delete_user_account(db, current_user)
    return {"message": "Your account and data have been deleted"}


class LocationUpdate(BaseModel):
    zip_code: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


@router.put("/me/location")
def update_location(
    req: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.services.location_service import resolve_location, LocationLookupError
    try:
        loc = resolve_location(req.zip_code, req.city, req.state)
    except LocationLookupError:
        raise HTTPException(503, "Location lookup is unavailable right now. Please try again.")
    if not loc:
        raise HTTPException(400, "We couldn't find that location. Please check the ZIP code, or the city and state.")
    for k, v in loc.items():
        setattr(current_user, k, v)
    db.commit()
    return {"message": "Location updated", "location_label": loc["location_label"]}
