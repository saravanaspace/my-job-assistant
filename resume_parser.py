from pathlib import Path
import fitz          # PyMuPDF
from docx import Document


def parse_resume(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        doc  = fitz.open(stream=file_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text.strip()

    if ext in (".docx", ".doc"):
        import io
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs).strip()

    raise ValueError(f"Unsupported file type: {ext}. Use PDF or DOCX.")
