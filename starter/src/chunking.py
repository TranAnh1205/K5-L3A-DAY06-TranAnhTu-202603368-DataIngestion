"""Two controlled, page-bounded chunking strategies."""
import hashlib
import re
from .models import Chunk, DocumentPage


def _make_chunk(page: DocumentPage, strategy: str, index: int, text: str) -> Chunk:
    key = f"{strategy}|{page.document_id}|{page.page}|{index}|{text}"
    chunk_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return Chunk(chunk_id, page.document_id, page.source, page.page, text, dict(page.metadata))


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Fixed character windows with overlap, never crossing a PDF page."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("size must be positive and overlap must be smaller than size")
    chunks = []
    step = size - overlap
    for start in range(0, len(page.text), step):
        part = page.text[start : start + size].strip()
        if part:
            chunks.append(_make_chunk(page, "A", len(chunks), part))
        if start + size >= len(page.text):
            break
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group complete sentences into bounded chunks, splitting only long sentences.

    The source PDF has line wraps but no dependable blank paragraph boundaries.
    Sentence boundaries preserve meaning better than character windows here.
    """
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", page.text)
    chunks = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_size:
            if current:
                chunks.append(_make_chunk(page, "B", len(chunks), current))
                current = ""
            for start in range(0, len(sentence), max_size):
                chunks.append(_make_chunk(page, "B", len(chunks), sentence[start : start + max_size]))
        elif len(current) + len(sentence) + (1 if current else 0) <= max_size:
            current = f"{current} {sentence}" if current else sentence
        else:
            chunks.append(_make_chunk(page, "B", len(chunks), current))
            current = sentence
    if current:
        chunks.append(_make_chunk(page, "B", len(chunks), current))
    return chunks
