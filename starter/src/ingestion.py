"""Extract traceable PDF pages and normalize text for embedding."""
import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader
from .models import DocumentPage


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract all physical pages; callers choose the manifest's eligible pages."""
    if not path.is_file():
        raise FileNotFoundError(path)
    result = []
    for number, pdf_page in enumerate(PdfReader(path).pages, start=1):
        text = normalize_text(pdf_page.extract_text() or "")
        result.append(DocumentPage(document_id, source, number, text))
    return result


def normalize_text(text: str) -> str:
    """Keep the wording while removing PDF line-wrap whitespace."""
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()
