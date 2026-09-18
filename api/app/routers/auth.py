from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
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
    code_type = "custom"
    code = db.query(SignupCode).filter(
        SignupCode.code == request.signup_code
    ).first()

    if code:
        code_type = code.code_type if hasattr(code, 'code_type') else "custom"
        if hasattr(code_type, 'value'):
            code_type = code_type.value

    if not code or not code.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired signup code"
        )

    phone = format_phone(request.phone)

    # For development — skip Twilio if not configured
    if settings.TWILIO_ACCOUNT_SID == "your_twilio_account_sid":
        return {"message": "OTP sent (dev mode)", "phone": phone, "dev_code": "123456", "code_type": code_type}

    success = send_otp(phone)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP"
        )

    return {"message": "OTP sent successfully", "phone": phone, "code_type": code_type}

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
    from app.models.signup_code import SignupCode, SignupCodeType
    from app.models.program_level import ProgramLevel as PL

    # Default — use whatever was passed
    assigned_level_id = request.program_level_id
    code_type = "custom"

    # Check if program_level_id is actually a signup code
    signup_code = db.query(SignupCode).filter(
        SignupCode.code == request.program_level_id
    ).first()

    if signup_code:
        code_type = signup_code.code_type
        if hasattr(code_type, 'value'):
            code_type = code_type.value

        if code_type == "myseed":
            # Assign shared Seed level
            seed_level = db.query(PL).filter(
                PL.level_type == "seed"
            ).first()
            if seed_level:
                assigned_level_id = str(seed_level.id)

        elif code_type == "myrise":
            # Create personal MyRise level for this user
            personal_level = PL(
                name="MyRise",
                description="Personal MyBuild level",
                order=0,
                level_type="myrise",
                is_active=True,
            )
            db.add(personal_level)
            db.flush()
            assigned_level_id = str(personal_level.id)
    phone = format_phone(request.phone)

    # Check if user already exists
    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        # Return token for existing user
        token = create_access_token({"sub": str(existing.id)})
        # Get level name for existing user
        from app.models.program_level import ProgramLevel as PLExist
        import uuid as _uuid_exist
        exist_level_name = "Seed"
        if existing.program_level_id:
            try:
                lv = db.query(PLExist).filter(
                    PLExist.id == _uuid_exist.UUID(str(existing.program_level_id))
                ).first()
                if lv:
                    exist_level_name = lv.name
            except:
                pass
        return TokenResponse(
            access_token=token,
            user_id=str(existing.id),
            name=existing.name,
            program_level=exist_level_name,
            achievement_level=existing.achievement_level,
            total_points=existing.total_points,
        )

    # Create new user
    user = User(
        name=request.name,
        phone=phone,
        program_level_id=assigned_level_id,
        total_points=0,
        completion_rate=0.0,
    )
    db.add(user)

    # Increment signup code usage
    # (find the code used during send-otp — for now just create user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})

    # Get level name
    from app.models.program_level import ProgramLevel
    level_name = "Seed"
    if user.program_level_id:
        try:
            import uuid as _uuid
            level_id_str = str(user.program_level_id)
            # Try as UUID first
            try:
                lv = db.query(ProgramLevel).filter(
                    ProgramLevel.id == _uuid.UUID(level_id_str)
                ).first()
            except:
                # Try as string match
                lv = db.query(ProgramLevel).filter(
                    ProgramLevel.name == level_id_str
                ).first()
            if lv:
                level_name = lv.name
                print(f"✅ Level found: {lv.name} (type: {lv.level_type})")
            else:
                print(f"❌ Level not found for: {level_id_str}")
                # Query all levels for debug
                all_levels = db.query(ProgramLevel).all()
                print(f"Available levels: {[(str(l.id), l.name) for l in all_levels]}")
        except Exception as e:
            print(f"❌ Level lookup error: {e}")
            level_name = "Seed"

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        name=user.name,
        program_level=level_name,
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

@router.get("/levels")
def get_public_levels(db: Session = Depends(get_db)):
    """Public endpoint — Flutter app uses this on register screen"""
    from app.models.program_level import ProgramLevel
    levels = db.query(ProgramLevel).filter(
        ProgramLevel.is_active == True
    ).order_by(ProgramLevel.order).all()
    return [{"id": str(l.id), "name": l.name, "description": l.description}
            for l in levels]

@router.post("/bootstrap")
def bootstrap(db: Session = Depends(get_db)):
    """Creates the default admin signup code if no codes exist yet"""
    from app.models.signup_code import SignupCode
    existing = db.query(SignupCode).first()
    if existing:
        return {"message": "Already bootstrapped", "code": existing.code}
    code = SignupCode(code="RISE2025", max_uses=1000)
    db.add(code)
    db.commit()
    return {"message": "Bootstrap complete", "code": "RISE2025"}

@router.post("/admin/login")
def admin_login(
    username: str,
    password: str,
    db: Session = Depends(get_db)
):
    if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    from app.services.email_service import generate_otp, store_otp, send_otp_email
    otp = generate_otp()
    store_otp(settings.ADMIN_EMAIL, otp)
    send_otp_email(settings.ADMIN_EMAIL, otp)
    print(f"📧 Admin OTP: {otp}")
    return {"message": "OTP sent (dev: use 123456)", "email": settings.ADMIN_EMAIL}

@router.post("/admin/verify")
def admin_verify(
    code: str,
    db: Session = Depends(get_db)
):
    from app.services.email_service import verify_email_otp
    import os
    is_dev = os.getenv("ENVIRONMENT", "development") != "production"
    if is_dev and code == "123456":
        pass  # Dev bypass
    elif not verify_email_otp(settings.ADMIN_EMAIL, code):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    admin = db.query(User).filter(User.role == UserRole.admin).first()
    if not admin:
        admin = User(name="Admin", phone="admin_portal", role=UserRole.admin, is_active=True)
        db.add(admin)
        db.commit()
        db.refresh(admin)
    token = create_access_token({"sub": str(admin.id)})
    return {"access_token": token, "name": admin.name}

