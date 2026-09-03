from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.task import Task, TaskFrequency, TaskInfoType
from app.models.pdf_book import PdfBook
from app.models.task_pdf_assignment import TaskPdfAssignment
from app.models.program_level import ProgramLevel
from app.models.excel_content import ExcelTaskContent
from app.core.dependencies import get_current_user, get_admin_user
from app.services.pdf_service import (
    get_total_pages, get_today_pages,
    extract_pages_as_images, PDF_DIR
)
from datetime import date
import os, uuid, io, json

router = APIRouter()

def _get_level_order(user: User, db: Session) -> int:
    if not user.program_level_id:
        return 0
    try:
        level = db.query(ProgramLevel).filter(
            ProgramLevel.id == uuid.UUID(str(user.program_level_id))
        ).first()
        return level.order if level else 0
    except:
        return 0

def _get_today_row(task_id, db: Session) -> Optional[dict]:
    """Get today's Excel row using date-based rotation"""
    rows = db.query(ExcelTaskContent).filter(
        ExcelTaskContent.task_id == task_id,
        ExcelTaskContent.is_active == True,
    ).order_by(ExcelTaskContent.row_number).all()

    if not rows:
        return None

    start_date = date(2025, 1, 1)
    day_number = (date.today() - start_date).days
    idx = day_number % len(rows)
    row = rows[idx]

    return {
        "row_number": row.row_number,
        "content": row.content,
        "information": row.information,
        "total_rows": len(rows),
    }

# ── Admin: Create content task ────────────────────────────────────────────────

@router.post("/create")
async def create_content_task(
    task_name: str = Form(...),
    frequency: str = Form("daily"),
    points: int = Form(10),
    pool_type: str = Form("myseed"),
    program_level_id: Optional[str] = Form(None),
    assignments_json: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Create a task with optional file attachment.
    File type is auto-detected:
      .pdf  → PDF rotating task
      .xlsx → Excel rotating task
      None  → Fixed content task (uses info_type/info_content)
    """
    # Step 1 — Create the base task
    freq_map = {
        "daily": TaskFrequency.daily,
        "weekly": TaskFrequency.weekly,
        "monthly": TaskFrequency.monthly,
    }
    task = Task(
        title=task_name,
        frequency=freq_map.get(frequency, TaskFrequency.daily),
        points=points,
        pool_type=pool_type,
        program_level_id=program_level_id or None,
        info_type=TaskInfoType.text,
        info_content=None,
    )
    db.add(task)
    db.flush()

    # Step 2 — Handle file if provided
    if file and file.filename:
        filename = file.filename.lower()
        file_content = await file.read()

        if filename.endswith('.pdf'):
            # ── PDF task ──────────────────────────────────────────────
            saved_name = f"{uuid.uuid4()}_{file.filename}"
            # Save locally for immediate use
            os.makedirs(PDF_DIR, exist_ok=True)
            filepath = os.path.join(PDF_DIR, saved_name)
            with open(filepath, "wb") as f_out:
                f_out.write(file_content)
            # Also upload to R2 for production
            try:
                from app.services.r2_service import upload_pdf
                upload_pdf(file_content, saved_name)
            except Exception as e:
                print(f"⚠️ R2 upload failed (continuing): {e}")

            total_pages = get_total_pages(saved_name)
            book = PdfBook(
                title=task_name,
                filename=saved_name,
                total_pages=total_pages,
                language="ar"
            )
            db.add(book)
            db.flush()

            # Assign per level
            if assignments_json:
                try:
                    assignments = json.loads(assignments_json)
                    for a in assignments:
                        db.add(TaskPdfAssignment(
                            task_id=task.id,
                            pdf_book_id=book.id,
                            level_order=int(a["level_order"]),
                            pages_per_day=int(a["pages_per_day"]),
                        ))
                except:
                    # Default: 1 page for all levels
                    db.add(TaskPdfAssignment(
                        task_id=task.id,
                        pdf_book_id=book.id,
                        level_order=0,
                        pages_per_day=1,
                    ))
            else:
                db.add(TaskPdfAssignment(
                    task_id=task.id,
                    pdf_book_id=book.id,
                    level_order=0,
                    pages_per_day=1,
                ))

            task.info_content = f"pdf:{book.id}"
            task.info_type = TaskInfoType.text

        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            # ── Excel task ────────────────────────────────────────────
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_content))
            ws = wb.active
            row_num = 1
            added = 0

            for row in ws.iter_rows(min_row=2, values_only=True):
                content_val = str(row[0]).strip() if row[0] else None
                if not content_val or content_val == 'None':
                    continue
                info_val = str(row[1]).strip() \
                    if len(row) > 1 and row[1] else None
                if info_val == 'None':
                    info_val = None

                db.add(ExcelTaskContent(
                    task_id=task.id,
                    row_number=row_num,
                    content=content_val,
                    information=info_val,
                ))
                row_num += 1
                added += 1

            task.info_content = f"excel:{task.id}"
            task.info_type = TaskInfoType.text

    db.commit()

    return {
        "message": f"Task '{task_name}' created",
        "task_id": str(task.id),
        "type": "pdf" if (file and file.filename and
                          file.filename.lower().endswith('.pdf'))
                else "excel" if (file and file.filename)
                else "fixed",
    }

@router.get("/list")
def list_content_tasks(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """List all tasks with their content type"""
    tasks = db.query(Task).filter(Task.is_active == True).all()
    result = []
    for t in tasks:
        content_type = "fixed"
        extra = {}

        if t.info_content and t.info_content.startswith("pdf:"):
            content_type = "pdf"
            try:
                book_id = t.info_content.split(":")[1]
                book = db.query(PdfBook).filter(
                    PdfBook.id == uuid.UUID(book_id)
                ).first()
                if book:
                    extra = {
                        "pdf_title": book.title,
                        "total_pages": book.total_pages,
                        "filename": book.filename,
                    }
            except:
                pass

        elif t.info_content and t.info_content.startswith("excel:"):
            content_type = "excel"
            row_count = db.query(ExcelTaskContent).filter(
                ExcelTaskContent.task_id == t.id,
                ExcelTaskContent.is_active == True,
            ).count()
            extra = {
                "total_rows": row_count,
                "filename": t.info_content,
            }

        result.append({
            "id": str(t.id),
            "title": t.title,
            "frequency": t.frequency.value
                if hasattr(t.frequency, "value") else t.frequency,
            "points": t.points,
            "pool_type": getattr(t, "pool_type", "myseed"),
            "content_type": content_type,
            **extra,
        })
    return result

@router.delete("/{task_id}")
def delete_content_task(
    task_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    task = db.query(Task).filter(
        Task.id == uuid.UUID(task_id)).first()
    if not task:
        raise HTTPException(404, "Task not found")
    task.is_active = False
    db.commit()
    return {"message": "Task removed"}

# ── User: Get today's content for a task ─────────────────────────────────────

@router.get("/today/{task_id}")
def get_today_content(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get today's content for any task type"""
    task = db.query(Task).filter(
        Task.id == uuid.UUID(task_id),
        Task.is_active == True,
    ).first()
    if not task:
        raise HTTPException(404, "Task not found")

    info_content = task.info_content or ""

    # PDF task
    if info_content.startswith("pdf:"):
        try:
            book_id = info_content.split(":")[1]
            book = db.query(PdfBook).filter(
                PdfBook.id == uuid.UUID(book_id)).first()
            if not book:
                raise HTTPException(404, "PDF not found")

            level_order = _get_level_order(current_user, db)
            assignment = db.query(TaskPdfAssignment).filter(
                TaskPdfAssignment.task_id == uuid.UUID(task_id),
                TaskPdfAssignment.level_order == level_order,
                TaskPdfAssignment.is_active == True,
            ).first()

            if not assignment:
                # Fall back to level 0
                assignment = db.query(TaskPdfAssignment).filter(
                    TaskPdfAssignment.task_id == uuid.UUID(task_id),
                    TaskPdfAssignment.is_active == True,
                ).first()

            if not assignment:
                raise HTTPException(404, "No PDF assignment for your level")

            start_page, end_page = get_today_pages(
                book.filename, assignment.pages_per_day, level_order)
            images = extract_pages_as_images(
                book.filename, start_page, end_page)

            return {
                "task_id": task_id,
                "content_type": "pdf",
                "pdf_title": book.title,
                "today_pages": f"{start_page + 1}–{end_page}",
                "total_pages": book.total_pages,
                "images": images,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, str(e))

    # Excel task
    elif info_content.startswith("excel:"):
        row = _get_today_row(uuid.UUID(task_id), db)
        if not row:
            raise HTTPException(404, "No Excel content for this task")
        return {
            "task_id": task_id,
            "content_type": "excel",
            "content": row["content"],
            "information": row["information"],
            "row_number": row["row_number"],
            "total_rows": row["total_rows"],
        }

    # Fixed content task
    else:
        return {
            "task_id": task_id,
            "content_type": "fixed",
            "content": task.info_content,
            "info_type": task.info_type.value
                if hasattr(task.info_type, "value") else task.info_type,
        }
