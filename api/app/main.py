from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.routers import auth, users, tasks, prayers, admin, pdfs, user_tasks, events, quotes, content_tasks
from app.routers import settings as app_settings_router
import os

app = FastAPI(
    title=settings.APP_NAME,
    description="Rise365 API",
    version="1.0.0",
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(prayers.router, prefix="/api/v1/prayers", tags=["Prayers"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(pdfs.router, prefix="/api/v1/pdfs", tags=["PDFs"])
app.include_router(user_tasks.router, prefix="/api/v1/user-tasks", tags=["User Tasks"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(app_settings_router.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(quotes.router, prefix="/api/v1/quotes", tags=["Quotes"])
app.include_router(content_tasks.router, prefix="/api/v1/content-tasks", tags=["Content Tasks"])

static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/admin")
def admin_portal():
    return FileResponse(os.path.join(static_path, "admin.html"))

@app.get("/")
def root():
    return {"app": settings.APP_NAME, "status": "running",
            "admin": "http://localhost:8000/admin"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    """Auto-create default signup codes and levels on fresh database"""
    from app.database import SessionLocal
    from app.models.signup_code import SignupCode, SignupCodeType
    from app.models.program_level import ProgramLevel
    db = SessionLocal()
    try:
        # ── Signup codes ──────────────────────────────────────────────
        existing_codes = db.query(SignupCode).first()
        if not existing_codes:
            myseed_code = SignupCode(
                code="MySeed",
                max_uses=10000,
                code_type=SignupCodeType.myseed,
                description="Default path — fixed tasks and admin-controlled rank"
            )
            mybuild_code = SignupCode(
                code="MyBuild",
                max_uses=10000,
                code_type=SignupCodeType.myrise,
                description="Personalized path — choose your own tasks and rank"
            )
            db.add(myseed_code)
            db.add(mybuild_code)
            db.commit()
            print("✅ Default signup codes MySeed and MyBuild created")

        # ── System levels ─────────────────────────────────────────────
        seed_level = db.query(ProgramLevel).filter(
            ProgramLevel.level_type == "seed"
        ).first()
        if not seed_level:
            seed_level = ProgramLevel(
                name="Seed",
                description="MySeed path — admin-controlled tasks and rank",
                order=0,
                level_type="seed",
                is_active=True,
            )
            db.add(seed_level)
            print("✅ Seed level created")

        myrise_level = db.query(ProgramLevel).filter(
            ProgramLevel.level_type == "myrise"
        ).first()
        if not myrise_level:
            myrise_level = ProgramLevel(
                name="MyRise",
                description="MyBuild path — user-controlled tasks and rank",
                order=0,
                level_type="myrise",
                is_active=True,
            )
            db.add(myrise_level)
            print("✅ MyRise level created")

        db.commit()
    finally:
        db.close()

@app.on_event("startup")
async def promote_first_user():
    """Auto-promote first registered user to admin if no admins exist"""
    import asyncio
    await asyncio.sleep(1)
    from app.database import SessionLocal
    from app.models.user import User, UserRole
    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(
            User.role == UserRole.admin
        ).first()
        if not admin_exists:
            first_user = db.query(User).order_by(User.created_at).first()
            if first_user:
                first_user.role = UserRole.admin
                db.commit()
                print(f"✅ {first_user.name} auto-promoted to admin")
    finally:
        db.close()
