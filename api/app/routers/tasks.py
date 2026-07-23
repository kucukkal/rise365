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

def get_period_range(frequency: str):
    now = datetime.utcnow()
    if frequency == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
    elif frequency == "weekly":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(weeks=1)
    else:  # monthly
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            end = start.replace(year=now.year + 1, month=1)
        else:
            end = start.replace(month=now.month + 1)
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

    if current_user.program_level_id:
        query = query.filter(
            (Task.program_level_id == current_user.program_level_id) |
            (Task.program_level_id == None)
        )

    tasks = query.all()
    result = []

    for task in tasks:
        freq = task.frequency.value if hasattr(task.frequency, 'value') else task.frequency
        start, end = get_period_range(freq)

        completion = db.query(TaskCompletion).filter(
            and_(
                TaskCompletion.user_id == current_user.id,
                TaskCompletion.task_id == task.id,
                TaskCompletion.period_start >= start,
                TaskCompletion.period_end <= end
            )
        ).first()

        result.append(TaskResponse(
            id=str(task.id),
            title=task.title,
            description=task.description,
            frequency=task.frequency,
            points=task.points,
            info_type=task.info_type,
            info_content=task.info_content,
            is_completed=completion is not None,
            completed_at=completion.completed_at if completion else None
        ))

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
    total_tasks = db.query(Task).filter(Task.is_active == True).count()
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
        program_level_id=uuid.UUID(request.program_level_id) if request.program_level_id else None
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"message": "Task created", "task_id": str(task.id)}
