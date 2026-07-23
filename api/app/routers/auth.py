from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.signup_code import SignupCode
from app.schemas.auth import SendOTPRequest, VerifyOTPRequest, RegisterRequest, TokenResponse
from app.core.security import create_access_token
from app.services.twilio_service import send_otp, verify_otp
from app.config import settings
import re

router = APIRouter()

def format_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if not digits.startswith('1') and len(digits) == 10:
        digits = '1' + digits
    return f'+{digits}'

@router.post("/send-otp")
def send_otp_endpoint(request: SendOTPRequest, db: Session = Depends(get_db)):
    # Validate signup code
    code = db.query(SignupCode).filter(
        SignupCode.code == request.signup_code.upper()
    ).first()

    if not code or not code.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired signup code"
        )

    phone = format_phone(request.phone)

    # For development — skip Twilio if not configured
    if settings.TWILIO_ACCOUNT_SID == "your_twilio_account_sid":
        return {"message": "OTP sent (dev mode)", "phone": phone, "dev_code": "123456"}

    success = send_otp(phone)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP"
        )

    return {"message": "OTP sent successfully", "phone": phone}

@router.post("/verify-otp")
def verify_otp_endpoint(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    phone = format_phone(request.phone)

    # Dev mode bypass
    if settings.TWILIO_ACCOUNT_SID == "your_twilio_account_sid":
        if request.code != "123456":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP (dev mode: use 123456)"
            )
        return {"message": "OTP verified", "phone": phone, "verified": True}

    verified = verify_otp(phone, request.code)
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )

    return {"message": "OTP verified", "phone": phone, "verified": True}

@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    phone = format_phone(request.phone)

    # Check if user already exists
    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        # Return token for existing user
        token = create_access_token({"sub": str(existing.id)})
        return TokenResponse(
            access_token=token,
            user_id=str(existing.id),
            name=existing.name,
            program_level=existing.program_level_id or "",
            achievement_level=existing.achievement_level,
            total_points=existing.total_points,
        )

    # Create new user
    user = User(
        name=request.name,
        phone=phone,
        program_level_id=request.program_level_id,
        total_points=0,
        completion_rate=0.0,
    )
    db.add(user)

    # Increment signup code usage
    # (find the code used during send-otp — for now just create user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        name=user.name,
        program_level=user.program_level_id or "",
        achievement_level=user.achievement_level,
        total_points=user.total_points,
    )

@router.post("/admin/create-signup-code")
def create_signup_code(
    code: str,
    max_uses: int = 1,
    db: Session = Depends(get_db)
):
    existing = db.query(SignupCode).filter(SignupCode.code == code.upper()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Code already exists")

    signup_code = SignupCode(
        code=code.upper(),
        max_uses=max_uses,
    )
    db.add(signup_code)
    db.commit()
    db.refresh(signup_code)

    return {"message": "Signup code created", "code": signup_code.code, "max_uses": max_uses}
