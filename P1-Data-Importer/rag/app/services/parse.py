import io
from pypdf import PdfReader
from docx import Document

def parse_pdf(raw: bytes) -> str:
    try:
        r = PdfReader(io.BytesIO(raw))
        if getattr(r, "is_encrypted", False):
            try:
                r.decrypt("")
            except Exception:
                return ""
        pages = []
        for p in r.pages:
            pages.append(p.extract_text() or "")
        return "\n".join(pages).strip()
    except Exception:
        return ""

def parse_docx(raw: bytes) -> str:
    try:
        d = Document(io.BytesIO(raw))
        return "\n".join([p.text for p in d.paragraphs]).strip()
    except Exception:
        return ""
