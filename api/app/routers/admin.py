from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.program_level import ProgramLevel
from app.core.dependencies import get_admin_user

router = APIRouter()

# ─── Program Levels ──────────────────────────────────────────────────────────

@router.get("/levels")
def get_levels(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    levels = db.query(ProgramLevel).filter(
        ProgramLevel.is_active == True
    ).order_by(ProgramLevel.order).all()

    seen_myrise = False
    result = []
    for l in levels:
        level_type = getattr(l, "level_type", "custom") or "custom"
        is_system = level_type in ("seed", "myrise")
        # Personal MyBuild levels (named after each user) aren't listed here
        if level_type == "myrise" and l.description == "Personal MyBuild level":
            continue
        # Only show one MyRise entry
        if level_type == "myrise":
            if seen_myrise:
                continue
            seen_myrise = True
        result.append({
            "id": str(l.id),
            "name": l.name,
            "description": l.description,
            "order": l.order,
            "level_type": level_type,
            "is_system": is_system,
        })
    return result

@router.post("/levels")
def create_level(
    name: str,
    description: str = "",
    order: int = 0,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    existing = db.query(ProgramLevel).filter(
        ProgramLevel.name == name,
        ProgramLevel.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Level name already exists")
    level = ProgramLevel(name=name, description=description, order=order)
    db.add(level)
    db.commit()
    db.refresh(level)
    return {"id": str(level.id), "name": level.name,
            "message": "Level created successfully"}

@router.delete("/levels/{level_id}")
def delete_level(
    level_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    level = db.query(ProgramLevel).filter(
        ProgramLevel.id == level_id
    ).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    level.is_active = False
    db.commit()
    return {"message": "Level removed"}

# ─── Users ───────────────────────────────────────────────────────────────────

@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    from collections import Counter
    name_counts = Counter((u.name or "").strip().lower() for u in users)

    def display_name(u):
        n = u.name or ""
        if name_counts[n.strip().lower()] > 1 and u.phone:
            return f"{n} (…{u.phone[-4:]})"
        return n

    return [{
        "id": str(u.id),
        "name": u.name,
        "display_name": display_name(u),
        "first_name": getattr(u, "first_name", None),
        "last_name": getattr(u, "last_name", None),
        "phone": u.phone,
        "program_level_id": u.program_level_id,
        "achievement_level": u.achievement_level,
        "total_points": u.total_points,
        "role": u.role.value,
        "is_active": u.is_active,
        "created_at": str(u.created_at)
    } for u in users]

@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.admin:
        raise HTTPException(status_code=400,
                            detail="Cannot remove an admin user")
    db.delete(user)
    db.commit()
    return {"message": f"{user.name} has been removed"}

@router.post("/users/{user_id}/make-admin")
def make_admin(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = UserRole.admin
    db.commit()
    return {"message": f"{user.name} is now an admin"}

# ─── Tasks (Admin view — all tasks, no level filter) ─────────────────────────

@router.get("/tasks")
def get_all_tasks(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    from app.models.task import Task
    tasks = db.query(Task).filter(Task.is_active == True).order_by(
        Task.sort_order, Task.created_at).all()
    return [{
        "id": str(t.id),
        "title": t.title,
        "description": t.description,
        "frequency": t.frequency.value if hasattr(t.frequency, 'value') else t.frequency,
        "points": t.points,
        "info_type": t.info_type.value if hasattr(t.info_type, 'value') else t.info_type,
        "info_content": t.info_content,
        "program_level_id": str(t.program_level_id) if t.program_level_id else None,
        "pool_type": getattr(t, "pool_type", "myseed") or "myseed",
        "sort_order": getattr(t, "sort_order", 100),
    } for t in tasks]

@router.delete("/tasks/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    from app.models.task import Task
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_active = False
    db.commit()
    return {"message": "Task removed"}

@router.put("/users/{user_id}/level")
def update_user_level(
    user_id: str,
    level_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.program_level_id = level_id
    db.commit()
    return {"message": f"{user.name}'s level updated"}
