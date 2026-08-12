import fitz
import os
from datetime import date

PDF_DIR = os.path.join(
    os.path.dirname(__file__), "../../uploads/pdfs")

def get_pdf_path(filename: str) -> str:
    return os.path.join(PDF_DIR, filename)

def get_total_pages(filename: str) -> int:
    try:
        doc = fitz.open(get_pdf_path(filename))
        count = doc.page_count
        doc.close()
        return count
    except Exception as e:
        print(f"PDF page count error: {e}")
        return 0

def get_today_pages(
    filename: str,
    pages_per_day: int,
    level_order: int,
    start_date: date = None,
) -> tuple:
    if start_date is None:
        from datetime import date as _date
        start_date = _date.today()

    today = date.today()
    day_number = (today - start_date).days

    total_pages = get_total_pages(filename)
    if total_pages == 0:
        return (0, 0)

    start_page = (day_number * pages_per_day) % total_pages
    end_page = min(start_page + pages_per_day, total_pages)

    return (start_page, end_page)

def extract_pages_as_pdf(
    filename: str,
    start_page: int,
    end_page: int,
) -> bytes:
    try:
        src = fitz.open(get_pdf_path(filename))
        dst = fitz.open()
        for page_num in range(start_page, end_page):
            if page_num < src.page_count:
                dst.insert_pdf(src, from_page=page_num, to_page=page_num)
        pdf_bytes = dst.tobytes()
        src.close()
        dst.close()
        return pdf_bytes
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return b""

def extract_pages_as_images(
    filename: str,
    start_page: int,
    end_page: int,
    dpi: int = 150,
) -> list:
    import base64
    images = []
    try:
        doc = fitz.open(get_pdf_path(filename))
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        for page_num in range(start_page, end_page):
            if page_num < doc.page_count:
                page = doc[page_num]
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                img_b64 = base64.b64encode(img_bytes).decode()
                images.append({
                    "page": page_num + 1,
                    "data": f"data:image/png;base64,{img_b64}",
                    "width": pix.width,
                    "height": pix.height,
                })
        doc.close()
        return images
    except Exception as e:
        print(f"PDF image extraction error: {e}")
        return []
