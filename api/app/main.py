from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, users, tasks, prayers, admin

app = FastAPI(
    title=settings.APP_NAME,
    description="Rise365 - Faith-based task and prayer tracking API",
    version="1.0.0",
    debug=settings.DEBUG,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(prayers.router, prefix="/api/v1/prayers", tags=["Prayers"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
