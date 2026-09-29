from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database import get_db
from app.models.user import User
from app.models.task import Task, TaskFrequency
from app.models.user_task import UserTask
from app.models.signup_code import SignupCodeType
from app.core.dependencies import get_current_user
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter()

class UserTaskCreate(BaseModel):
    task_id: str
    pages_per_day: int = 1
    frequency: str = "daily"

class UserTaskUpdate(BaseModel):
    pages_per_day: Optional[int] = None
    frequency: Optional[str] = None

def _is_myrise_user(user: User, db: Session) -> bool:
    """Check if user signed up with MyRise/MyBuild code"""
    return getattr(user, 'level_type', None) == 'myrise' or \
           (user.program_level_id and
            _get_level_type(str(user.program_level_id), db) == 'myrise')

def _get_level_type(level_id: str, db: Session) -> str:
    from app.models.program_level import ProgramLevel
    try:
        level = db.query(ProgramLevel).filter(
            ProgramLevel.id == uuid.UUID(level_id)
        ).first()
        return getattr(level, 'level_type', 'seed') if level else 'seed'
    except:
        return 'seed'

def _count_daily_tasks(user_id, db: Session) -> int:
    return db.query(UserTask).filter(
        and_(
            UserTask.user_id == user_id,
            UserTask.frequency == "daily",
            UserTask.is_active == True,
        )
    ).count()

@router.get("/my-tasks")
def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get MyRise user's selected tasks"""
    user_tasks = db.query(UserTask).filter(
        and_(
            UserTask.user_id == current_user.id,
            UserTask.is_active == True,
        )
    ).all()

    result = []
    for ut in user_tasks:
        task = db.query(Task).filter(Task.id == ut.task_id).first()
        if task:
            result.append({
                "id": str(ut.id),
                "task_id": str(task.id),
                "title": task.title,
                "pages_per_day": ut.pages_per_day,
                "frequency": ut.frequency,
                "points": task.points,
                "sort_order": getattr(task, "sort_order", 100),
                "has_content": (task.info_content or "").startswith(("pdf:", "excel:")),
                "is_completed": False,
            })
    result.sort(key=lambda r: (r["has_content"], r["sort_order"]))
    return result

@router.get("/available-tasks")
def get_available_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tasks available for MyRise users to add"""
    tasks = db.query(Task).filter(
        and_(
            Task.is_active == True,
            Task.pool_type.in_(['myrise', 'both'])
        )
    ).all()

    # Get already selected task IDs
    selected_ids = {
        str(ut.task_id) for ut in db.query(UserTask).filter(
            and_(
                UserTask.user_id == current_user.id,
                UserTask.is_active == True,
            )
        ).all()
    }

    return [{
        "id": str(t.id),
        "title": t.title,
        "points": t.points,
        "is_selected": str(t.id) in selected_ids,
    } for t in tasks]

@router.post("/my-tasks")
def add_my_task(
    request: UserTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a task to MyRise user's list"""
    task = db.query(Task).filter(
        and_(
            Task.id == uuid.UUID(request.task_id),
            Task.is_active == True,
            Task.pool_type.in_(['myrise', 'both'])
        )
    ).first()

    if not task:
        raise HTTPException(404, "Task not found or not available")

    # Check if already added
    existing = db.query(UserTask).filter(
        and_(
            UserTask.user_id == current_user.id,
            UserTask.task_id == uuid.UUID(request.task_id),
            UserTask.is_active == True,
        )
    ).first()

    if existing:
        raise HTTPException(400, "Task already added")

    user_task = UserTask(
        user_id=current_user.id,
        task_id=uuid.UUID(request.task_id),
        pages_per_day=request.pages_per_day,
        frequency=request.frequency,
    )
    db.add(user_task)
    db.commit()
    db.refresh(user_task)

    return {
        "id": str(user_task.id),
        "message": f"{task.title} added to your tasks",
    }

@router.put("/my-tasks/{user_task_id}")
def update_my_task(
    user_task_id: str,
    request: UserTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update pages/frequency for a MyRise user's task"""
    user_task = db.query(UserTask).filter(
        and_(
            UserTask.id == uuid.UUID(user_task_id),
            UserTask.user_id == current_user.id,
            UserTask.is_active == True,
        )
    ).first()

    if not user_task:
        raise HTTPException(404, "Task not found")

    if request.pages_per_day is not None:
        user_task.pages_per_day = request.pages_per_day
    if request.frequency is not None:
        # Check if changing from daily would violate minimum
        if user_task.frequency == "daily" and \
           request.frequency != "daily":
            daily_count = _count_daily_tasks(current_user.id, db)
            if daily_count <= 2:
                raise HTTPException(
                    400,
                    "Cannot change — you need at least 2 daily tasks"
                )
        user_task.frequency = request.frequency

    db.commit()
    return {"message": "Task updated"}

@router.delete("/my-tasks/{user_task_id}")
def delete_my_task(
    user_task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a task from MyRise user's list"""
    user_task = db.query(UserTask).filter(
        and_(
            UserTask.id == uuid.UUID(user_task_id),
            UserTask.user_id == current_user.id,
            UserTask.is_active == True,
        )
    ).first()

    if not user_task:
        raise HTTPException(404, "Task not found")

    # Check minimum daily tasks
    if user_task.frequency == "daily":
        daily_count = _count_daily_tasks(current_user.id, db)
        if daily_count <= 2:
            raise HTTPException(
                400,
                "Cannot remove — you need at least 2 daily tasks"
            )

    user_task.is_active = False
    db.commit()
    return {"message": "Task removed"}

@router.post("/questionnaire")
def submit_questionnaire(
    q1: bool,  # Prays 5 daily prayers
    q2: bool,  # Performs Evrad/Zikr
    q3: bool,  # Within 45 minutes
    q4: int,   # Voluntary prayers: 0, 1, 2+
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Determine rank based on prayer questionnaire"""
    # Determine rank
    if not q1 or not q2:
        rank = 0
    elif not q3:
        rank = 1
    elif q4 == 0:
        rank = 2
    elif q4 == 1:
        rank = 3
    else:
        rank = 4

    # Update THIS user's personal MyRise level order
    from app.models.program_level import ProgramLevel
    if current_user.program_level_id:
        try:
            level = db.query(ProgramLevel).filter(
                ProgramLevel.id == uuid.UUID(
                    str(current_user.program_level_id)),
                ProgramLevel.level_type == "myrise"
            ).first()
            if level:
                level.order = rank
                db.commit()
                print(f"✅ {current_user.name} rank set to {rank}")
        except Exception as e:
            print(f"Rank update error: {e}")

    rank_names = {
        0: "MyRise — Beginner",
        1: "MyRise — Dedicated",
        2: "MyRise — Committed",
        3: "MyRise — Advanced",
        4: "MyRise — Elite",
    }

    return {
        "rank": rank,
        "rank_name": rank_names[rank],
        "message": f"Your rank is set to {rank_names[rank]}",
    }
