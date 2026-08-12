from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.app_setting import AppSetting
from app.core.dependencies import get_admin_user, get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

DEFAULT_SETTINGS = {
    "taraweeh_motivation_phrase": "Last year you completed {count} Taraweeh nights. Let us do better this Ramadan!",
    "taraweeh_first_year_phrase": "This is your first Ramadan with Rise365. Aim for all 30 Taraweeh nights!",
    "myseed_title": "MySeed Path",
    "myseed_description": "Start gently with a simple, sustainable routine. Just the essentials. Plant your seed of goodness with signup code MySeed",
    "myrise_title": "MyBuild Path",
    "myrise_description": "Create a routine that matches your goals and builds upon MySeed. Build your rise with signup code MyBuild",
    "welcome_message": "Welcome to Rise 365! How would you like to begin your journey? Every journey starts with a single step. Choose the path that feels right for you today.",
}

def _get_setting(db: Session, key: str) -> str:
    setting = db.query(AppSetting).filter(
        AppSetting.key == key).first()
    if setting:
        return setting.value
    return DEFAULT_SETTINGS.get(key, "")

def _set_setting(db: Session, key: str, value: str,
                 description: str = None):
    setting = db.query(AppSetting).filter(
        AppSetting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = AppSetting(key=key, value=value,
                             description=description)
        db.add(setting)
    db.commit()

class SettingUpdate(BaseModel):
    value: str

@router.get("/signup-info")
def get_signup_info(db: Session = Depends(get_db)):
    """Public endpoint for login screen"""
    return {
        "welcome_message": _get_setting(db, "welcome_message"),
        "myseed_title": _get_setting(db, "myseed_title"),
        "myseed_description": _get_setting(db, "myseed_description"),
        "myrise_title": _get_setting(db, "myrise_title"),
        "myrise_description": _get_setting(db, "myrise_description"),
    }

@router.get("/")
def get_settings(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    settings = db.query(AppSetting).all()
    result = dict(DEFAULT_SETTINGS)
    for s in settings:
        result[s.key] = s.value
    return result

@router.put("/{key}")
def update_setting(
    key: str,
    request: SettingUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    if key == "taraweeh_motivation_phrase" and "{count}" not in request.value:
        raise HTTPException(
            status_code=400,
            detail="The phrase must include {count}"
        )
    _set_setting(db, key, request.value)
    return {"message": f"Setting '{key}' updated"}

@router.get("/taraweeh-motivation")
async def get_taraweeh_motivation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get last year's Taraweeh count and motivational phrase"""
    from app.models.event import Event, EventCompletion
    from sqlalchemy import and_, func
    from datetime import date

    last_year = date.today().year - 1
    last_year_start = date(last_year, 1, 1)
    last_year_end = date(last_year, 12, 31)

    taraweeh = db.query(Event).filter(
        Event.fixed_type == "taraweeh",
        Event.is_active == True
    ).first()

    last_year_count = 0
    if taraweeh:
        last_year_count = db.query(
            func.count(EventCompletion.id)
        ).filter(
            and_(
                EventCompletion.user_id == current_user.id,
                EventCompletion.event_id == taraweeh.id,
                EventCompletion.event_date >= last_year_start,
                EventCompletion.event_date <= last_year_end,
            )
        ).scalar() or 0

    if last_year_count == 0:
        phrase = _get_setting(db, "taraweeh_first_year_phrase")
    else:
        template = _get_setting(db, "taraweeh_motivation_phrase")
        phrase = template.replace("{count}", str(last_year_count))

    return {
        "last_year_count": last_year_count,
        "phrase": phrase,
        "last_year": last_year,
    }
