from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models.user import User
from app.models.circle import Circle, CircleMember
from app.core.dependencies import get_current_user, get_admin_user
from app.services.push_service import send_push
import uuid, re

router = APIRouter()

MAX_MEMBERSHIPS = 2          # own circle counts as one
MAX_JOIN_REQUESTS_PER_DAY = 10
MAX_INVITES_PER_DAY = 20


# ── helpers ───────────────────────────────────────────────────────────────────

def _key(text: str) -> str:
    """Case- and space-insensitive comparison key."""
    return " ".join((text or "").lower().split())

def _format_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if not digits.startswith("1") and len(digits) == 10:
        digits = "1" + digits
    return f"+{digits}"

def _active_count(db: Session, user_id) -> int:
    return db.query(CircleMember).filter(
        CircleMember.user_id == user_id, CircleMember.status == "active").count()

def _today_start():
    return datetime.now(timezone.utc) - timedelta(days=1)

def _user(db, user_id) -> User:
    return db.query(User).filter(User.id == user_id).first()

def _circle_or_404(db, circle_id: str) -> Circle:
    try:
        cid = uuid.UUID(circle_id)
    except ValueError:
        raise HTTPException(404, "Circle not found")
    c = db.query(Circle).filter(Circle.id == cid).first()
    if not c:
        raise HTTPException(404, "Circle not found")
    return c

def _member_row(db, row_id: str) -> CircleMember:
    try:
        rid = uuid.UUID(row_id)
    except ValueError:
        raise HTTPException(404, "Not found")
    row = db.query(CircleMember).filter(CircleMember.id == rid).first()
    if not row:
        raise HTTPException(404, "Not found")
    return row

def _progress(user: User, db: Session) -> float:
    try:
        from app.services.completion_service import calculate_weighted_completion
        return calculate_weighted_completion(user, db)
    except Exception:
        return float(user.completion_rate or 0)


class CreateCircle(BaseModel):
    name: str

class JoinRequest(BaseModel):
    circle_name: str
    owner_name: str

class InviteRequest(BaseModel):
    phone: str


# ── overview ──────────────────────────────────────────────────────────────────

@router.get("/mine")
def my_circles(db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    rows = db.query(CircleMember).filter(CircleMember.user_id == me.id).all()
    circles, invitations = [], []
    for r in rows:
        c = db.query(Circle).filter(Circle.id == r.circle_id).first()
        if not c:
            continue
        owner = _user(db, c.owner_id)
        if r.status == "active":
            circles.append({
                "id": str(c.id), "name": c.name,
                "is_owner": c.owner_id == me.id,
                "owner_name": owner.name if owner else "",
                "member_count": db.query(CircleMember).filter(
                    CircleMember.circle_id == c.id, CircleMember.status == "active").count(),
            })
        elif r.status == "invited":
            invitations.append({
                "id": str(r.id), "circle_name": c.name,
                "owner_name": owner.name if owner else "",
                "message": f"{owner.name if owner else 'Someone'} invites you to join the circle \"{c.name}\"",
            })

    requests = []
    owned = db.query(Circle).filter(Circle.owner_id == me.id).first()
    if owned:
        for r in db.query(CircleMember).filter(
                CircleMember.circle_id == owned.id, CircleMember.status == "requested").all():
            u = _user(db, r.user_id)
            if u:
                requests.append({
                    "id": str(r.id), "circle_name": owned.name, "requester_name": u.name,
                    "message": f"{u.name} wants to join your circle \"{owned.name}\"",
                })

    return {
        "circles": circles,
        "invitations": invitations,
        "requests": requests,
        "owns_circle": owned is not None,
        "can_join_more": len(circles) < MAX_MEMBERSHIPS,
        "max_circles": MAX_MEMBERSHIPS,
    }


# ── create ────────────────────────────────────────────────────────────────────

@router.get("/check-name")
def check_name(name: str, db: Session = Depends(get_db), me: User = Depends(get_current_user)):
    key = _key(name)
    return {"available": len(key) >= 3 and
            db.query(Circle).filter(Circle.name_key == key).first() is None}

@router.post("/create")
def create_circle(req: CreateCircle, db: Session = Depends(get_db),
                  me: User = Depends(get_current_user)):
    name = " ".join(req.name.split())
    key = _key(name)
    if not 3 <= len(name) <= 40:
        raise HTTPException(400, "Circle name must be 3–40 characters")
    if db.query(Circle).filter(Circle.owner_id == me.id).first():
        raise HTTPException(400, "You already have a circle. Each person can create one.")
    if _active_count(db, me.id) >= MAX_MEMBERSHIPS:
        raise HTTPException(400, f"You're already in {MAX_MEMBERSHIPS} circles. Leave one to create your own.")
    if db.query(Circle).filter(Circle.name_key == key).first():
        raise HTTPException(400, "That circle name is taken. Please choose another.")
    circle = Circle(name=name, name_key=key, owner_id=me.id)
    db.add(circle)
    db.flush()
    db.add(CircleMember(circle_id=circle.id, user_id=me.id, status="active"))
    db.commit()
    return {"message": f"Circle \"{name}\" created", "id": str(circle.id)}


# ── join request (member → owner) ────────────────────────────────────────────

@router.post("/join-request")
def join_request(req: JoinRequest, db: Session = Depends(get_db),
                 me: User = Depends(get_current_user)):
    since = _today_start()
    if db.query(CircleMember).filter(
            CircleMember.user_id == me.id, CircleMember.status == "requested",
            CircleMember.created_at >= since).count() >= MAX_JOIN_REQUESTS_PER_DAY:
        raise HTTPException(429, "Too many requests today. Please try again tomorrow.")

    not_found = HTTPException(404, "No circle matches that name and owner.")
    circle = db.query(Circle).filter(Circle.name_key == _key(req.circle_name)).first()
    if not circle:
        raise not_found
    owner = _user(db, circle.owner_id)
    if not owner or _key(owner.name) != _key(req.owner_name):
        raise not_found

    existing = db.query(CircleMember).filter(
        CircleMember.circle_id == circle.id, CircleMember.user_id == me.id).first()
    if existing:
        if existing.status == "active":
            raise HTTPException(400, "You're already in this circle.")
        if existing.status == "invited":
            raise HTTPException(400, "You already have an invitation to this circle. Accept it below.")
        raise HTTPException(400, "Your request is already waiting for approval.")
    if _active_count(db, me.id) >= MAX_MEMBERSHIPS:
        raise HTTPException(400, f"You're already in {MAX_MEMBERSHIPS} circles. Leave one to join another.")

    db.add(CircleMember(circle_id=circle.id, user_id=me.id, status="requested"))
    db.commit()
    send_push(owner, "New circle request",
              f"{me.name} wants to join your circle \"{circle.name}\"", {"type": "circle_request"})
    return {"message": f"Request sent to {owner.name}"}


@router.post("/requests/{row_id}/approve")
def approve_request(row_id: str, db: Session = Depends(get_db),
                    me: User = Depends(get_current_user)):
    row = _member_row(db, row_id)
    circle = db.query(Circle).filter(Circle.id == row.circle_id).first()
    if not circle or circle.owner_id != me.id or row.status != "requested":
        raise HTTPException(404, "Request not found")
    requester = _user(db, row.user_id)
    if _active_count(db, row.user_id) >= MAX_MEMBERSHIPS:
        raise HTTPException(400, f"{requester.name} is already in {MAX_MEMBERSHIPS} circles.")
    row.status = "active"
    db.commit()
    send_push(requester, "Request approved", f"You joined the circle \"{circle.name}\"",
              {"type": "circle_joined"})
    return {"message": f"{requester.name} joined {circle.name}"}


@router.post("/requests/{row_id}/decline")
def decline_request(row_id: str, db: Session = Depends(get_db),
                    me: User = Depends(get_current_user)):
    row = _member_row(db, row_id)
    circle = db.query(Circle).filter(Circle.id == row.circle_id).first()
    if not circle or circle.owner_id != me.id or row.status != "requested":
        raise HTTPException(404, "Request not found")
    requester = _user(db, row.user_id)
    db.delete(row)
    db.commit()
    if requester:
        send_push(requester, "Circle request",
                  f"Your request to join \"{circle.name}\" was declined", {"type": "circle_declined"})
    return {"message": "Request declined"}


# ── invitation (owner → user) ────────────────────────────────────────────────

@router.post("/invite")
def invite(req: InviteRequest, db: Session = Depends(get_db),
           me: User = Depends(get_current_user)):
    circle = db.query(Circle).filter(Circle.owner_id == me.id).first()
    if not circle:
        raise HTTPException(400, "Create your own circle first to invite people.")
    if db.query(CircleMember).filter(
            CircleMember.circle_id == circle.id, CircleMember.status == "invited",
            CircleMember.created_at >= _today_start()).count() >= MAX_INVITES_PER_DAY:
        raise HTTPException(429, "Too many invitations today. Please try again tomorrow.")

    generic = {"message": "If this number belongs to a Rise365 user, they'll receive your invitation."}
    target = db.query(User).filter(User.phone == _format_phone(req.phone)).first()
    if not target or target.id == me.id:
        return generic
    if db.query(CircleMember).filter(
            CircleMember.circle_id == circle.id, CircleMember.user_id == target.id).first():
        return generic  # already member / invited / requested

    db.add(CircleMember(circle_id=circle.id, user_id=target.id, status="invited"))
    db.commit()
    send_push(target, "Circle invitation",
              f"{me.name} invites you to join the circle \"{circle.name}\"", {"type": "circle_invite"})
    return generic


@router.post("/invitations/{row_id}/accept")
def accept_invitation(row_id: str, db: Session = Depends(get_db),
                      me: User = Depends(get_current_user)):
    row = _member_row(db, row_id)
    if row.user_id != me.id or row.status != "invited":
        raise HTTPException(404, "Invitation not found")
    if _active_count(db, me.id) >= MAX_MEMBERSHIPS:
        raise HTTPException(400, f"You're already in {MAX_MEMBERSHIPS} circles. Leave one to accept.")
    circle = db.query(Circle).filter(Circle.id == row.circle_id).first()
    row.status = "active"
    db.commit()
    owner = _user(db, circle.owner_id)
    if owner:
        send_push(owner, "Invitation accepted", f"{me.name} joined \"{circle.name}\"",
                  {"type": "circle_joined"})
    return {"message": f"You joined {circle.name}"}


@router.post("/invitations/{row_id}/decline")
def decline_invitation(row_id: str, db: Session = Depends(get_db),
                       me: User = Depends(get_current_user)):
    row = _member_row(db, row_id)
    if row.user_id != me.id or row.status != "invited":
        raise HTTPException(404, "Invitation not found")
    circle = db.query(Circle).filter(Circle.id == row.circle_id).first()
    db.delete(row)
    db.commit()
    owner = _user(db, circle.owner_id) if circle else None
    if owner:
        send_push(owner, "Invitation declined",
                  f"{me.name} declined your invitation to \"{circle.name}\"", {"type": "circle_declined"})
    return {"message": "Invitation declined"}


# ── circle details & management ──────────────────────────────────────────────

@router.get("/{circle_id}")
def circle_detail(circle_id: str, db: Session = Depends(get_db),
                  me: User = Depends(get_current_user)):
    circle = _circle_or_404(db, circle_id)
    mine = db.query(CircleMember).filter(
        CircleMember.circle_id == circle.id, CircleMember.user_id == me.id,
        CircleMember.status == "active").first()
    if not mine:
        raise HTTPException(404, "Circle not found")
    members = []
    for r in db.query(CircleMember).filter(
            CircleMember.circle_id == circle.id, CircleMember.status == "active").all():
        u = _user(db, r.user_id)
        if u:
            members.append({
                "user_id": str(u.id), "name": u.name,
                "progress": round(_progress(u, db)),
                "is_owner": u.id == circle.owner_id,
                "is_me": u.id == me.id,
            })
    members.sort(key=lambda m: -m["progress"])
    return {"id": str(circle.id), "name": circle.name,
            "is_owner": circle.owner_id == me.id, "members": members}


@router.post("/{circle_id}/leave")
def leave_circle(circle_id: str, db: Session = Depends(get_db),
                 me: User = Depends(get_current_user)):
    circle = _circle_or_404(db, circle_id)
    if circle.owner_id == me.id:
        raise HTTPException(400, "You own this circle. Delete it instead of leaving.")
    row = db.query(CircleMember).filter(
        CircleMember.circle_id == circle.id, CircleMember.user_id == me.id).first()
    if not row:
        raise HTTPException(404, "Circle not found")
    db.delete(row)
    db.commit()
    return {"message": f"You left {circle.name}"}


@router.delete("/{circle_id}/members/{user_id}")
def remove_member(circle_id: str, user_id: str, db: Session = Depends(get_db),
                  me: User = Depends(get_current_user)):
    circle = _circle_or_404(db, circle_id)
    if circle.owner_id != me.id:
        raise HTTPException(403, "Only the circle owner can remove members")
    if user_id == str(me.id):
        raise HTTPException(400, "You can't remove yourself. Delete the circle instead.")
    row = db.query(CircleMember).filter(
        CircleMember.circle_id == circle.id,
        CircleMember.user_id == uuid.UUID(user_id)).first()
    if not row:
        raise HTTPException(404, "Member not found")
    was_active = row.status == "active"
    removed = _user(db, row.user_id)
    db.delete(row)
    db.commit()
    if removed and was_active:
        send_push(removed, "Removed from circle",
                  f"You were removed from the circle \"{circle.name}\"", {"type": "circle_removed"})
    return {"message": "Member removed"}


@router.delete("/{circle_id}")
def delete_circle(circle_id: str, db: Session = Depends(get_db),
                  me: User = Depends(get_current_user)):
    circle = _circle_or_404(db, circle_id)
    if circle.owner_id != me.id:
        raise HTTPException(403, "Only the circle owner can delete it")
    name = circle.name
    others = [_user(db, r.user_id) for r in db.query(CircleMember).filter(
        CircleMember.circle_id == circle.id, CircleMember.status == "active",
        CircleMember.user_id != me.id).all()]
    db.query(CircleMember).filter(CircleMember.circle_id == circle.id).delete()
    db.delete(circle)
    db.commit()
    for u in others:
        if u:
            send_push(u, "Circle deleted",
                      f"The circle \"{name}\" was deleted by its owner", {"type": "circle_deleted"})
    return {"message": f"Circle \"{name}\" deleted"}


# ── admin ─────────────────────────────────────────────────────────────────────

@router.get("/admin/all")
def admin_all(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    out = []
    for c in db.query(Circle).order_by(Circle.created_at.desc()).all():
        owner = _user(db, c.owner_id)
        out.append({
            "id": str(c.id), "name": c.name,
            "owner_name": owner.name if owner else "",
            "member_count": db.query(CircleMember).filter(
                CircleMember.circle_id == c.id, CircleMember.status == "active").count(),
            "created_at": str(c.created_at),
        })
    return out

@router.delete("/admin/{circle_id}")
def admin_delete(circle_id: str, db: Session = Depends(get_db),
                 admin: User = Depends(get_admin_user)):
    circle = _circle_or_404(db, circle_id)
    name = circle.name
    members = [_user(db, r.user_id) for r in db.query(CircleMember).filter(
        CircleMember.circle_id == circle.id, CircleMember.status == "active").all()]
    db.query(CircleMember).filter(CircleMember.circle_id == circle.id).delete()
    db.delete(circle)
    db.commit()
    for u in members:
        if u:
            send_push(u, "Circle removed",
                      f"The circle \"{name}\" was removed", {"type": "circle_deleted"})
    return {"message": "Circle removed"}

