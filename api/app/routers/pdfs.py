from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.pdf_book import PdfBook
from app.models.task_pdf_assignment import TaskPdfAssignment
from app.models.program_level import ProgramLevel
from app.core.dependencies import get_current_user, get_admin_user
from app.services.pdf_service import (
    get_total_pages, get_today_pages,
    extract_pages_as_pdf, extract_pages_as_images, PDF_DIR
)
import os, uuid, json

router = APIRouter()

# ── Admin: Upload PDF ─────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_pdf(
    title: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    os.makedirs(PDF_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(PDF_DIR, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    total_pages = get_total_pages(filename)
    book = PdfBook(title=title, filename=filename,
                   total_pages=total_pages, language="ar")
    db.add(book)
    db.commit()
    db.refresh(book)
    return {"id": str(book.id), "title": title,
            "total_pages": total_pages, "message": f"PDF uploaded — {total_pages} pages"}

@router.get("/")
def list_pdfs(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    books = db.query(PdfBook).filter(PdfBook.is_active == True).all()
    return [{"id": str(b.id), "title": b.title,
             "total_pages": b.total_pages, "filename": b.filename}
            for b in books]

# ── Admin: Create PDF Task (unified) ─────────────────────────────────────────

@router.post("/create-pdf-task")
async def create_pdf_task(
    task_name: str = Form(...),
    frequency: str = Form("daily"),
    points: int = Form(10),
    pdf_title: str = Form(""),
    assignments_json: str = Form(...),
    pdf_book_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    from app.models.task import Task, TaskFrequency, TaskInfoType

    # Step 1 — Handle PDF source
    book_id = None
    if pdf_book_id and pdf_book_id.strip():
        book_id = uuid.UUID(pdf_book_id)
    elif file and file.filename:
        os.makedirs(PDF_DIR, exist_ok=True)
        filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = os.path.join(PDF_DIR, filename)
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        total = get_total_pages(filename)
        book = PdfBook(
            title=pdf_title or task_name,
            filename=filename,
            total_pages=total,
            language="ar"
        )
        db.add(book)
        db.flush()
        book_id = book.id
    else:
        raise HTTPException(400, "Upload a PDF file or select an existing one")

    # Step 2 — Create task
    freq_map = {
        "daily": TaskFrequency.daily,
        "weekly": TaskFrequency.weekly,
        "monthly": TaskFrequency.monthly,
    }
    task = Task(
        title=task_name,
        frequency=freq_map.get(frequency, TaskFrequency.daily),
        points=points,
        info_type=TaskInfoType.text,
        info_content=f"pdf:{book_id}",
    )
    db.add(task)
    db.flush()

    # Step 3 — Create level assignments
    assignments = json.loads(assignments_json)
    for a in assignments:
        assignment = TaskPdfAssignment(
            task_id=task.id,
            pdf_book_id=book_id,
            level_order=int(a["level_order"]),
            pages_per_day=int(a["pages_per_day"]),
        )
        db.add(assignment)

    db.commit()
    return {
        "message": f"PDF task '{task_name}' created",
        "task_id": str(task.id),
        "pdf_book_id": str(book_id),
        "assignments": len(assignments),
    }

# ── Admin: List PDF tasks ─────────────────────────────────────────────────────

@router.get("/tasks")
def list_pdf_tasks(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    from app.models.task import Task
    tasks = db.query(Task).filter(
        Task.is_active == True,
        Task.info_content.like("pdf:%")
    ).all()

    result = []
    for task in tasks:
        assignments = db.query(TaskPdfAssignment).filter(
            TaskPdfAssignment.task_id == task.id,
            TaskPdfAssignment.is_active == True,
        ).order_by(TaskPdfAssignment.level_order).all()

        level_info = []
        for a in assignments:
            book = db.query(PdfBook).filter(
                PdfBook.id == a.pdf_book_id).first()
            level_info.append({
                "level_order": a.level_order,
                "pages_per_day": a.pages_per_day,
                "pdf_title": book.title if book else "Unknown",
                "total_pages": book.total_pages if book else 0,
            })

        result.append({
            "id": str(task.id),
            "title": task.title,
            "frequency": task.frequency.value
                if hasattr(task.frequency, "value") else task.frequency,
            "points": task.points,
            "level_assignments": level_info,
        })
    return result

@router.delete("/tasks/{task_id}")
def delete_pdf_task(
    task_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    from app.models.task import Task
    task = db.query(Task).filter(Task.id == uuid.UUID(task_id)).first()
    if not task:
        raise HTTPException(404, "Task not found")
    task.is_active = False
    db.commit()
    return {"message": "PDF task removed"}

# ── Admin: Assign PDF to task per level ──────────────────────────────────────

@router.post("/assign")
def assign_pdf(
    task_id: str,
    pdf_book_id: str,
    level_order: int,
    pages_per_day: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    existing = db.query(TaskPdfAssignment).filter(
        TaskPdfAssignment.task_id == uuid.UUID(task_id),
        TaskPdfAssignment.level_order == level_order,
        TaskPdfAssignment.is_active == True,
    ).first()
    if existing:
        existing.is_active = False
    a = TaskPdfAssignment(
        task_id=uuid.UUID(task_id),
        pdf_book_id=uuid.UUID(pdf_book_id),
        level_order=level_order,
        pages_per_day=pages_per_day,
    )
    db.add(a)
    db.commit()
    return {"message": f"Level {level_order}: {pages_per_day} page(s)/day"}

# ── User: Get today's pages ───────────────────────────────────────────────────

@router.get("/today/{task_id}")
def get_today_task_pages(
    task_id: str,
    as_images: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    level_order = 0
    if current_user.program_level_id:
        try:
            lv = db.query(ProgramLevel).filter(
                ProgramLevel.id == uuid.UUID(
                    str(current_user.program_level_id))
            ).first()
            level_order = lv.order if lv else 0
        except:
            level_order = 0

    assignment = db.query(TaskPdfAssignment).filter(
        TaskPdfAssignment.task_id == uuid.UUID(task_id),
        TaskPdfAssignment.level_order == level_order,
        TaskPdfAssignment.is_active == True,
    ).first()

    if not assignment:
        raise HTTPException(404,
            f"No PDF assigned for level {level_order}")

    book = db.query(PdfBook).filter(
        PdfBook.id == assignment.pdf_book_id).first()
    if not book:
        raise HTTPException(404, "PDF book not found")

    start_page, end_page = get_today_pages(
        book.filename, assignment.pages_per_day, level_order)

    if as_images:
        images = extract_pages_as_images(
            book.filename, start_page, end_page)
        return {
            "task_id": task_id,
            "pdf_title": book.title,
            "level_order": level_order,
            "pages_per_day": assignment.pages_per_day,
            "today_pages": f"{start_page + 1}–{end_page}",
            "total_pages": book.total_pages,
            "images": images,
        }
    else:
        pdf_bytes = extract_pages_as_pdf(
            book.filename, start_page, end_page)
        return Response(content=pdf_bytes,
                        media_type="application/pdf")
