from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, date, timedelta
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.event import Event, EventCompletion
from app.core.dependencies import get_current_user
from app.services.islamic_calendar_service import (
    get_eid_dates, get_friday_zuhr_time,
    get_next_occurrence_weekly, get_next_occurrence_monthly,
    get_ramadan_dates
)
from pydantic import BaseModel
import uuid

router = APIRouter()

MYSEED_LIMITS = {"weekly": 3, "monthly": 1}
MYRISE_LIMITS = {"weekly": 5, "monthly": 3}

TARAWEEH_PHRASES = {
    0:  "Begin your Taraweeh journey tonight! 🌙",
    1:  "MashaAllah! First Taraweeh completed! 🌙",
    3:  "3 nights of devotion! Keep going! ⭐",
    5:  "Amazing! 5 Taraweeh prayers! You're building a habit! 🌟",
    7:  "One week of Taraweeh! SubhanAllah! ✨",
    10: "10 nights! You're halfway through! Keep it up! 🏅",
    15: "15 Taraweeh! You're on fire! 🔥",
    20: "Incredible! 20 nights of standing in prayer! 💫",
    23: "The last 10 nights begin — Laylatul Qadr is near! 🤲",
    27: "Night 27 — seek Laylatul Qadr tonight! 🌠",
    29: "Almost there! One more Taraweeh left! 🏆",
    30: "Alhamdulillah! All 30 Taraweeh completed! 🎉",
}

def _get_taraweeh_phrase(count: int) -> str:
    best = 0
    for k in TARAWEEH_PHRASES:
        if count >= k:
            best = k
    return TARAWEEH_PHRASES[best]

def _get_user_limits(user: User, db: Session) -> dict:
    if user.program_level_id:
        from app.models.program_level import ProgramLevel
        try:
            level = db.query(ProgramLevel).filter(
                ProgramLevel.id == uuid.UUID(str(user.program_level_id))
            ).first()
            if level and getattr(level, 'level_type', 'seed') == 'myrise':
                return MYRISE_LIMITS
        except:
            pass
    return MYSEED_LIMITS

def _should_show_event(event: Event, today: date,
                       is_completed: bool) -> bool:
    """Apply disappear rules"""
    if is_completed:
        return False  # Always hide completed events

    if event.event_type == "weekly":
        # Show for 3 days after the event day
        if event.day_of_week is not None:
            days_since = (today.weekday() - event.day_of_week) % 7
            return days_since <= 3
        return True

    elif event.event_type == "monthly":
        # Show for 7 days after the event
        return True  # Router handles date filtering

    elif event.event_type == "fixed":
        if event.fixed_type == "taraweeh":
            return True  # Always show during Ramadan
        return True  # Fixed events always show if today matches

    return True

def _format_event(event: Event, is_completed: bool = False,
                  extra: dict = None) -> dict:
    days = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",
            4:"Friday",5:"Saturday",6:"Sunday"}
    weeks = {1:"First",2:"Second",3:"Third",4:"Fourth"}

    schedule = ""
    if event.event_type == "weekly" and event.day_of_week is not None:
        schedule = f"Every {days.get(event.day_of_week,'')} at {event.start_time}"
    elif event.event_type == "monthly":
        if event.monthly_pattern == "specific_day":
            schedule = f"{event.day_of_month}th of every month at {event.start_time}"
        elif event.monthly_pattern == "weekly_day":
            schedule = f"Every {days.get(event.day_of_week,'')} of every month at {event.start_time}"
        elif event.monthly_pattern == "nth_weekday":
            schedule = f"{weeks.get(event.week_of_month,'')} {days.get(event.day_of_week,'')} of every month at {event.start_time}"
    elif event.event_type == "fixed":
        if event.fixed_type == "jummah":
            schedule = f"Every Friday at {event.start_time}"
        elif event.fixed_type == "ramadan_start":
            schedule = f"Maghrib: {event.start_time}"
        elif event.fixed_type == "taraweeh":
            schedule = f"Isha: {event.start_time} (every night of Ramadan)"
        elif event.fixed_type in ("eid_fitr","eid_adha"):
            schedule = "Annual Islamic holiday at 08:00"

    result = {
        "id": str(event.id),
        "name": event.name,
        "description": event.description,
        "event_type": event.event_type,
        "fixed_type": event.fixed_type,
        "schedule": schedule,
        "start_time": event.start_time,
        "day_of_week": event.day_of_week,
        "day_of_month": event.day_of_month,
        "week_of_month": event.week_of_month,
        "monthly_pattern": event.monthly_pattern,
        "points": event.points,
        "is_completed": is_completed,
        "is_fixed": event.user_id is None,
    }
    if extra:
        result.update(extra)
    return result

class EventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    event_type: str
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    week_of_month: Optional[int] = None
    monthly_pattern: Optional[str] = None
    start_time: str = "09:00"

class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    week_of_month: Optional[int] = None
    monthly_pattern: Optional[str] = None
    start_time: Optional[str] = None

@router.get("/today")
async def get_today_events(
    city: str = "Herndon",
    country: str = "US",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    today_weekday = today.weekday()
    events = []

    # ── Get Islamic dates ────────────────────────────────────────────────────
    eid_dates = await get_eid_dates(today.year)
    ramadan_dates = await get_ramadan_dates(today.year)

    ramadan_start = None
    ramadan_end = None
    if ramadan_dates.get("ramadan_start"):
        try:
            ramadan_start = date.fromisoformat(ramadan_dates["ramadan_start"])
            ramadan_end = date.fromisoformat(ramadan_dates["ramadan_end"])
        except:
            pass

    # ── Ramadan countdown banner (only within 30 days before Ramadan) ────────
    ramadan_banner = None
    if ramadan_start:
        days_until = (ramadan_start - today).days
        if 0 < days_until <= 30:
            ramadan_banner = {
                "type": "ramadan_coming",
                "days_until": days_until,
                "title": f"Ramadan is coming in {days_until} day{'s' if days_until > 1 else ''}!",
                "phrase": "Prepare your heart and routine for the blessed month.",
            }
        elif days_until <= 0 and ramadan_end and today <= ramadan_end:
            ramadan_banner = {
                "type": "ramadan_here",
                "days_until": 0,
                "title": "Glad tidings! Ramadan is here.",
                "phrase": "Ramadan Mubarak! May Allah accept your fasting and prayers.",
            }

    # ── Start of Ramadan ─────────────────────────────────────────────────────
    if ramadan_start:
        day_before_ramadan = ramadan_start - timedelta(days=1)
        if today == day_before_ramadan:
            # Get Maghrib time
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    r = await client.get(
                        "https://api.aladhan.com/v1/timingsByCity",
                        params={"city": city, "country": country, "method": 2},
                        timeout=10.0
                    )
                    maghrib = r.json()["data"]["timings"]["Maghrib"].split(" ")[0]
            except:
                maghrib = "18:00"

            ramadan_event = db.query(Event).filter(
                Event.fixed_type == "ramadan_start",
                Event.is_active == True
            ).first()

            if not ramadan_event:
                ramadan_event = Event(
                    name="Start of Ramadan",
                    description="Ramadan Mubarak! The blessed month begins tonight.",
                    event_type="fixed",
                    fixed_type="ramadan_start",
                    start_time=maghrib,
                    points=100,
                )
                db.add(ramadan_event)
                db.commit()
                db.refresh(ramadan_event)
            else:
                ramadan_event.start_time = maghrib
                db.commit()

            completion = db.query(EventCompletion).filter(
                and_(EventCompletion.user_id == current_user.id,
                     EventCompletion.event_id == ramadan_event.id,
                     EventCompletion.event_date == today)
            ).first()

            is_completed = completion is not None
            if not is_completed:
                events.append(_format_event(ramadan_event, is_completed=False))

    # ── Taraweeh ─────────────────────────────────────────────────────────────
    if ramadan_start and ramadan_end:
        day_before_ramadan = ramadan_start - timedelta(days=1)
        day_before_eid = ramadan_end - timedelta(days=1)  # Day before last fasting = 2 days before Eid

        if day_before_ramadan <= today <= day_before_eid:
            # Get Isha time
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    r = await client.get(
                        "https://api.aladhan.com/v1/timingsByCity",
                        params={"city": city, "country": country, "method": 2},
                        timeout=10.0
                    )
                    isha = r.json()["data"]["timings"]["Isha"].split(" ")[0]
            except:
                isha = "21:30"

            taraweeh = db.query(Event).filter(
                Event.fixed_type == "taraweeh",
                Event.is_active == True
            ).first()

            if not taraweeh:
                taraweeh = Event(
                    name="Taraweeh Prayer",
                    description="Night prayer during Ramadan",
                    event_type="fixed",
                    fixed_type="taraweeh",
                    start_time=isha,
                    points=150,
                )
                db.add(taraweeh)
                db.commit()
                db.refresh(taraweeh)
            else:
                taraweeh.start_time = isha
                db.commit()

            completion = db.query(EventCompletion).filter(
                and_(EventCompletion.user_id == current_user.id,
                     EventCompletion.event_id == taraweeh.id,
                     EventCompletion.event_date == today)
            ).first()

            # Count total Taraweeh attended this Ramadan
            taraweeh_count = db.query(func.count(EventCompletion.id)).filter(
                and_(EventCompletion.user_id == current_user.id,
                     EventCompletion.event_id == taraweeh.id,
                     EventCompletion.event_date >= day_before_ramadan)
            ).scalar() or 0

            phrase = _get_taraweeh_phrase(taraweeh_count)
            is_completed = completion is not None

            events.append(_format_event(
                taraweeh,
                is_completed=is_completed,
                extra={
                    "taraweeh_count": taraweeh_count,
                    "taraweeh_phrase": phrase,
                    "is_taraweeh": True,
                }
            ))

    # ── Friday Jummah ────────────────────────────────────────────────────────
    if today_weekday == 4:
        zuhr_time = await get_friday_zuhr_time(city, country)
        jummah = db.query(Event).filter(
            Event.fixed_type == "jummah",
            Event.is_active == True
        ).first()

        if not jummah:
            jummah = Event(
                name="Jummah Prayer",
                description="Friday congregational prayer",
                event_type="fixed",
                fixed_type="jummah",
                day_of_week=4,
                start_time=zuhr_time,
                points=150,
            )
            db.add(jummah)
            db.commit()
            db.refresh(jummah)
        else:
            jummah.start_time = zuhr_time
            db.commit()

        completion = db.query(EventCompletion).filter(
            and_(EventCompletion.user_id == current_user.id,
                 EventCompletion.event_id == jummah.id,
                 EventCompletion.event_date == today)
        ).first()

        if not completion:
            events.append(_format_event(jummah, is_completed=False))

    # ── Eid events ───────────────────────────────────────────────────────────
    for eid_type, eid_date_str in eid_dates.items():
        if eid_date_str:
            try:
                eid_date = date.fromisoformat(eid_date_str)
                days_since = (today - eid_date).days
                if 0 <= days_since <= 3:
                    eid_event = db.query(Event).filter(
                        Event.fixed_type == eid_type,
                        Event.is_active == True
                    ).first()

                    if not eid_event:
                        name = "Eid-ul-Fitr" if eid_type == "eid_fitr" \
                            else "Eid-ul-Adha"
                        eid_event = Event(
                            name=name,
                            description=f"Blessed {name} celebration",
                            event_type="fixed",
                            fixed_type=eid_type,
                            start_time="08:00",
                            points=150,
                        )
                        db.add(eid_event)
                        db.commit()
                        db.refresh(eid_event)

                    completion = db.query(EventCompletion).filter(
                        and_(EventCompletion.user_id == current_user.id,
                             EventCompletion.event_id == eid_event.id,
                             EventCompletion.event_date == today)
                    ).first()

                    if not completion:
                        events.append(_format_event(eid_event, is_completed=False))
            except:
                pass

    # ── User events for today ────────────────────────────────────────────────
    user_events = db.query(Event).filter(
        and_(Event.user_id == current_user.id, Event.is_active == True)
    ).all()

    for event in user_events:
        is_today = False
        if event.event_type == "weekly":
            if event.day_of_week == today_weekday:
                is_today = True
        elif event.event_type == "monthly":
            if event.monthly_pattern == "specific_day":
                is_today = event.day_of_month == today.day
            elif event.monthly_pattern == "weekly_day":
                is_today = event.day_of_week == today_weekday
            elif event.monthly_pattern == "nth_weekday":
                week_num = (today.day - 1) // 7 + 1
                is_today = (event.day_of_week == today_weekday and
                            event.week_of_month == week_num)

        if is_today:
            completion = db.query(EventCompletion).filter(
                and_(EventCompletion.user_id == current_user.id,
                     EventCompletion.event_id == event.id,
                     EventCompletion.event_date == today)
            ).first()

            if not completion:  # Only show uncompleted
                events.append(_format_event(event, is_completed=False))

    # ── Upcoming user events ─────────────────────────────────────────────────
    upcoming = []
    for event in user_events:
        try:
            if event.event_type == "weekly" and event.day_of_week is not None:
                next_occ = get_next_occurrence_weekly(
                    event.day_of_week, event.start_time or "09:00")
                days_until = (next_occ.date() - today).days
                if 1 <= days_until <= 7:
                    upcoming.append({
                        **_format_event(event),
                        "days_until": days_until,
                        "next_occurrence": next_occ.strftime("%A at %I:%M %p"),
                    })
        except:
            pass

    return {
        "today": events,
        "upcoming": upcoming,
        "date": today.strftime("%A, %B %d"),
        "ramadan_banner": ramadan_banner,
    }

@router.get("/my-events")
def get_my_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    events = db.query(Event).filter(
        and_(Event.user_id == current_user.id, Event.is_active == True)
    ).all()

    limits = _get_user_limits(current_user, db)
    weekly_count = sum(1 for e in events if e.event_type == "weekly")
    monthly_count = sum(1 for e in events if e.event_type == "monthly")

    return {
        "events": [_format_event(e) for e in events],
        "limits": limits,
        "weekly_count": weekly_count,
        "monthly_count": monthly_count,
        "can_add_weekly": weekly_count < limits["weekly"],
        "can_add_monthly": monthly_count < limits["monthly"],
    }

@router.post("/my-events")
def create_event(
    request: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    limits = _get_user_limits(current_user, db)
    existing = db.query(Event).filter(
        and_(Event.user_id == current_user.id,
             Event.event_type == request.event_type,
             Event.is_active == True)
    ).count()

    limit = limits.get(request.event_type, 0)
    if existing >= limit:
        raise HTTPException(
            400,
            f"Maximum {limit} {request.event_type} events allowed for your plan"
        )

    event = Event(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        event_type=request.event_type,
        day_of_week=request.day_of_week,
        day_of_month=request.day_of_month,
        week_of_month=request.week_of_month,
        monthly_pattern=request.monthly_pattern,
        start_time=request.start_time,
        points=20,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"id": str(event.id), "message": f"Event '{request.name}' created!"}

@router.put("/my-events/{event_id}")
def update_event(
    event_id: str,
    request: EventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(
        and_(Event.id == uuid.UUID(event_id),
             Event.user_id == current_user.id,
             Event.is_active == True)
    ).first()
    if not event:
        raise HTTPException(404, "Event not found")

    if request.name: event.name = request.name
    if request.description is not None:
        event.description = request.description
    if request.day_of_week is not None: event.day_of_week = request.day_of_week
    if request.day_of_month is not None: event.day_of_month = request.day_of_month
    if request.week_of_month is not None: event.week_of_month = request.week_of_month
    if request.monthly_pattern: event.monthly_pattern = request.monthly_pattern
    if request.start_time: event.start_time = request.start_time
    db.commit()
    return {"message": "Event updated"}

@router.delete("/my-events/{event_id}")
def delete_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(
        and_(Event.id == uuid.UUID(event_id),
             Event.user_id == current_user.id,
             Event.is_active == True)
    ).first()
    if not event:
        raise HTTPException(404, "Event not found")
    event.is_active = False
    db.commit()
    return {"message": "Event removed"}

@router.post("/complete/{event_id}")
def complete_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    event = db.query(Event).filter(
        Event.id == uuid.UUID(event_id),
        Event.is_active == True,
    ).first()
    if not event:
        raise HTTPException(404, "Event not found")

    today = date.today()
    existing = db.query(EventCompletion).filter(
        and_(EventCompletion.user_id == current_user.id,
             EventCompletion.event_id == event.id,
             EventCompletion.event_date == today)
    ).first()

    if existing:
        current_user.total_points = max(
            0, current_user.total_points - existing.points_earned)
        db.delete(existing)
        db.commit()
        return {"message": "Event unchecked",
                "total_points": current_user.total_points}

    completion = EventCompletion(
        user_id=current_user.id,
        event_id=event.id,
        event_date=today,
        completed_at=datetime.utcnow(),
        points_earned=event.points,
    )
    db.add(completion)
    current_user.total_points += event.points
    db.commit()

    return {
        "message": f"{event.name} completed! +{event.points} pts",
        "points_earned": event.points,
        "total_points": current_user.total_points,
    }
