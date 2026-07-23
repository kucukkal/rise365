from fastapi import APIRouter
router = APIRouter()

@router.get("/test")
def test():
    return {"router": "admin", "status": "ok"}
