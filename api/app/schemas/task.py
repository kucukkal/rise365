from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime

class TaskFrequency(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"

class TaskInfoType(str, Enum):
    none = "none"
    text = "text"
    image = "image"
    video = "video"

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    frequency: TaskFrequency
    points: int
    info_type: TaskInfoType
    info_content: Optional[str]
    is_completed: bool = False
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TaskCompleteRequest(BaseModel):
    task_id: str

class CreateTaskRequest(BaseModel):
    sort_order: int = 100
    title: str
    description: Optional[str] = None
    frequency: TaskFrequency
    points: int = 10
    info_type: TaskInfoType = TaskInfoType.none
    info_content: Optional[str] = None
    program_level_id: Optional[str] = None
