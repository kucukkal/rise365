from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User
from app.models.task import Task, TaskCompletion, TaskFrequency
from app.schemas.task import TaskResponse, TaskCompleteRequest, CreateTaskRequest
from app.core.dependencies import get_current_user, get_admin_user
import uuid

router = APIRouter()

def _content_last():
    """0 for plain tasks, 1 for PDF/Excel tasks, so plain tasks come first."""
    from sqlalchemy import case, or_
    return case(
        (or_(Task.info_content.like("pdf:%"), Task.info_content.like("excel:%")), 1),
        else_=0,
    )

def get_period_range(frequency: str, use_4am: bool = True):
    now = datetime.utcnow()
    cutoff_hour = 4 if use_4am else 0

    if frequency == "daily":
        start = now.replace(hour=cutoff_hour, minute=0, second=0, microsecond=0)
        if now.hour < cutoff_hour:
            start = start - timedelta(days=1)
        end = start + timedelta(days=1)

    elif frequency == "weekly":
        # Find last Monday at 4 AM
        today_4am = now.replace(hour=cutoff_hour, minute=0, second=0, microsecond=0)
        if now.hour < cutoff_hour:
            today_4am = today_4am - timedelta(days=1)
        days_since_monday = today_4am.weekday()
        start = today_4am - timedelta(days=days_since_monday)
        end = start + timedelta(weeks=1)

    else:  # monthly
        today_4am = now.replace(hour=cutoff_hour, minute=0, second=0, microsecond=0)
        if now.hour < cutoff_hour:
            today_4am = today_4am - timedelta(days=1)
        start = today_4am.replace(day=1)
        if today_4am.month == 12:
            end = start.replace(year=today_4am.year + 1, month=1)
        else:
            end = start.replace(month=today_4am.month + 1)

    return start, end

@router.get("/", response_model=List[TaskResponse])
def get_tasks(
    frequency: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Task).filter(Task.is_active == True)

    if frequency:
        query = query.filter(Task.frequency == frequency)

    # Filter by pool_type based on user's level type
    from app.models.program_level import ProgramLevel
    import uuid as uuid_mod
    user_level_type = "seed"  # default
    if current_user.program_level_id:
        try:
            level = db.query(ProgramLevel).filter(
                ProgramLevel.id == uuid_mod.UUID(str(current_user.program_level_id))
            ).first()
            user_level_type = getattr(level, "level_type", "seed") if level else "seed"
        except:
            pass

    # MySeed users see myseed + both tasks
    # MyRise users see myrise + both tasks
    if user_level_type == "myrise":
        query = query.filter(
            Task.pool_type.in_(["myrise", "both"])
        )
    else:
        # seed or custom — see myseed + both
        query = query.filter(
            Task.pool_type.in_(["myseed", "both"])
        )

    tasks = query.order_by(_content_last(), Task.sort_order, Task.created_at).all()
    result = []

    for task in tasks:
        freq = task.frequency.value if hasattr(task.frequency, 'value') else task.frequency
        start, end = get_period_range(freq, use_4am=True)

        completion = db.query(TaskCompletion).filter(
            and_(
                TaskCompletion.user_id == current_user.id,
                TaskCompletion.task_id == task.id,
                TaskCompletion.period_start >= start,
                TaskCompletion.period_end <= end
            )
        ).first()

        result.append({
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "frequency": task.frequency.value if hasattr(task.frequency, "value") else task.frequency,
            "points": task.points,
            "info_type": task.info_type.value if hasattr(task.info_type, "value") else task.info_type,
            "info_content": task.info_content,
            "pool_type": getattr(task, "pool_type", "myseed") or "myseed",
            "is_completed": completion is not None,
            "completed_at": str(completion.completed_at) if completion else None,
        })

    return result

@router.post("/complete")
def complete_task(
    request: TaskCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == request.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    freq = task.frequency.value if hasattr(task.frequency, 'value') else task.frequency
    start, end = get_period_range(freq)

    existing = db.query(TaskCompletion).filter(
        and_(
            TaskCompletion.user_id == current_user.id,
            TaskCompletion.task_id == task.id,
            TaskCompletion.period_start >= start,
        )
    ).first()

    if existing:
        # Undo completion
        db.delete(existing)
        current_user.total_points = max(0, current_user.total_points - task.points)
        db.commit()
        return {"message": "Task unmarked", "points_lost": task.points, "total_points": current_user.total_points}

    # Mark complete
    completion = TaskCompletion(
        user_id=current_user.id,
        task_id=task.id,
        period_start=start,
        period_end=end
    )
    db.add(completion)
    current_user.total_points += task.points
    _update_completion_rate(current_user, db)
    db.commit()

    return {"message": "Task completed", "points_earned": task.points, "total_points": current_user.total_points}

def _update_completion_rate(user: User, db: Session):
    # Get user level type to filter correct pool
    from app.models.program_level import ProgramLevel
    import uuid as _uuid
    user_level_type = "seed"
    if user.program_level_id:
        try:
            lv = db.query(ProgramLevel).filter(
                ProgramLevel.id == _uuid.UUID(str(user.program_level_id))
            ).first()
            user_level_type = getattr(lv, "level_type", "seed") if lv else "seed"
        except:
            pass

    # Count only tasks relevant to this user
    if user_level_type == "myrise":
        pool_filter = Task.pool_type.in_(["myrise", "both"])
    else:
        pool_filter = Task.pool_type.in_(["myseed", "both"])

    total_tasks = db.query(Task).filter(
        Task.is_active == True,
        pool_filter
    ).count()

    if total_tasks == 0:
        user.completion_rate = 0.0
        return

    now = datetime.utcnow()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    completed = db.query(TaskCompletion).filter(
        and_(
            TaskCompletion.user_id == user.id,
            TaskCompletion.period_start >= start_of_month
        )
    ).count()
    user.completion_rate = round((completed / total_tasks) * 100, 2)

@router.post("/admin/create")
def create_task(
    request: CreateTaskRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    task = Task(
        title=request.title,
        description=request.description,
        frequency=request.frequency,
        points=request.points,
        info_type=request.info_type,
        info_content=request.info_content,
        pool_type=request.pool_type or "myseed",
        sort_order=getattr(request, "sort_order", None) or 100,
        program_level_id=uuid.UUID(request.program_level_id) if request.program_level_id else None
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"message": "Task created", "task_id": str(task.id)}
