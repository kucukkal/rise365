from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.quote import Quote
from app.core.dependencies import get_admin_user
from pydantic import BaseModel
from typing import Optional
import uuid
import io

router = APIRouter()

class QuoteCreate(BaseModel):
    text: str
    source: Optional[str] = None
    category: Optional[str] = "general"

# ── Public ────────────────────────────────────────────────────────────────────

@router.get("/random")
def get_random_quote(
    db: Session = Depends(get_db),
):
    """Get a random active quote"""
    quote = db.query(Quote).filter(
        Quote.is_active == True
    ).order_by(func.random()).first()

    if not quote:
        # Default quote if none in database
        return {
            "text": "The best of people are those who are most beneficial to others.",
            "source": "Prophet Muhammad ﷺ",
            "category": "hadith",
        }

    return {
        "id": str(quote.id),
        "text": quote.text,
        "source": quote.source,
        "category": quote.category,
    }

# ── Admin ─────────────────────────────────────────────────────────────────────

@router.get("/admin/all")
def get_all_quotes(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    quotes = db.query(Quote).filter(
        Quote.is_active == True
    ).order_by(Quote.created_at.desc()).all()
    return [{
        "id": str(q.id),
        "text": q.text[:80] + "..." if len(q.text) > 80 else q.text,
        "source": q.source,
        "category": q.category,
    } for q in quotes]

@router.post("/admin/add")
def add_quote(
    request: QuoteCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    quote = Quote(
        text=request.text,
        source=request.source,
        category=request.category or "general",
    )
    db.add(quote)
    db.commit()
    return {"message": "Quote added", "id": str(quote.id)}

@router.delete("/admin/{quote_id}")
def delete_quote(
    quote_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    quote = db.query(Quote).filter(
        Quote.id == uuid.UUID(quote_id)
    ).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    quote.is_active = False
    db.commit()
    return {"message": "Quote removed"}

@router.post("/admin/upload")
async def upload_quotes(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user)
):
    """
    Upload quotes from Excel (.xlsx) or PDF file.

    Excel format (columns):
      A: Quote text (required)
      B: Source (optional) — e.g. "Quran 2:286", "Sahih Bukhari"
      C: Category (optional) — quran, hadith, motivational, general

    PDF format:
      Each line = one quote
      Optionally: "Quote text | Source | Category"
    """
    filename = file.filename.lower()
    content = await file.read()
    added = 0
    errors = []

    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        # Parse Excel
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content))
            ws = wb.active

            for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    text = str(row[0]).strip() if row[0] else None
                    if not text or text == 'None':
                        continue
                    source = str(row[1]).strip() if len(row) > 1 and row[1] else None
                    category = str(row[2]).strip().lower() if len(row) > 2 and row[2] else "general"
                    if category not in ("quran", "hadith", "motivational", "general"):
                        category = "general"

                    quote = Quote(text=text, source=source, category=category)
                    db.add(quote)
                    added += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")

            db.commit()
        except Exception as e:
            raise HTTPException(400, f"Excel parse error: {str(e)}")

    elif filename.endswith('.pdf'):
        # Parse PDF using PyMuPDF
        try:
            import fitz
            doc = fitz.open(stream=content, filetype="pdf")
            lines = []
            for page in doc:
                text = page.get_text()
                lines.extend(text.split('\n'))
            doc.close()

            for line_num, line in enumerate(lines, start=1):
                line = line.strip()
                if not line or len(line) < 10:
                    continue
                try:
                    parts = [p.strip() for p in line.split('|')]
                    text = parts[0]
                    source = parts[1] if len(parts) > 1 else None
                    category = parts[2].lower() if len(parts) > 2 else "general"
                    if category not in ("quran", "hadith", "motivational", "general"):
                        category = "general"

                    quote = Quote(text=text, source=source, category=category)
                    db.add(quote)
                    added += 1
                except Exception as e:
                    errors.append(f"Line {line_num}: {str(e)}")

            db.commit()
        except Exception as e:
            raise HTTPException(400, f"PDF parse error: {str(e)}")

    else:
        raise HTTPException(400, "Only .xlsx or .pdf files are supported")

    return {
        "message": f"{added} quotes imported successfully",
        "added": added,
        "errors": errors[:10] if errors else [],
    }

@router.get("/admin/template")
def download_template():
    """Returns the expected Excel format as JSON for reference"""
    return {
        "format": "Excel (.xlsx)",
        "columns": {
            "A": "Quote text (required)",
            "B": "Source (optional) — e.g. Quran 2:286, Sahih Bukhari, Ali ibn Abi Talib",
            "C": "Category (optional) — quran / hadith / motivational / general"
        },
        "example_rows": [
            ["The best of people are those most beneficial to others.", "Prophet Muhammad ﷺ", "hadith"],
            ["Indeed, with hardship comes ease.", "Quran 94:6", "quran"],
            ["Knowledge is a treasure, but practice is the key to it.", "Ali ibn Abi Talib", "motivational"],
        ]
    }
