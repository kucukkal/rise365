from pydantic import BaseModel
from typing import Optional

class SendOTPRequest(BaseModel):
    phone: str
    signup_code: str

class VerifyOTPRequest(BaseModel):
    phone: str
    code: str

class RegisterRequest(BaseModel):
    phone: str
    name: str
    program_level_id: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    program_level: str
    achievement_level: str
    total_points: int

class UserResponse(BaseModel):
    id: str
    name: str
    phone: str
    program_level_id: Optional[str]
    achievement_level: str
    total_points: int
    completion_rate: float

    class Config:
        from_attributes = True
