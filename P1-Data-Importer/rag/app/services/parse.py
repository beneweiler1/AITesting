import io
from pypdf import PdfReader
from docx import Document

def parse_pdf(raw: bytes) -> str:
    r = PdfReader(io.BytesIO(raw))
    pages = []
    for p in r.pages:
        pages.append(p.extract_text() or "")
    return "\n".join(pages)

def parse_docx(raw: bytes) -> str:
    d = Document(io.BytesIO(raw))
    return "\n".join([p.text for p in d.paragraphs])
