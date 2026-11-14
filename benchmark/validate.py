"""Check the frozen question set and each gold quote against the source PDF."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifest.json"
QUESTIONS = ROOT / "benchmark/questions.json"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    pdf = ROOT / manifest["local_path"]
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == manifest["snapshot_sha256"]
    reader = PdfReader(pdf)
    pages = {p["physical_page"]: p for p in manifest["pages"]}
    assert len(questions) >= 20
    assert len({q["id"] for q in questions}) == len(questions)
    counts = Counter(q["split"] for q in questions)
    assert counts["dev"] >= 15 and counts["test"] >= 5, counts
    assert set(counts) == {"dev", "test"}
    filters = Counter()
    required = {
        "id", "split", "question", "expected_answer", "gold_source_id", "gold_page", "evidence_quote"
    }
    for q in questions:
        assert required <= q.keys(), q["id"]
        assert all(q[k] for k in required), q["id"]
        assert q["gold_source_id"] == manifest["source_id"], q["id"]
        assert q["gold_page"] in pages, q["id"]
        text = re.sub(r"\s+", " ", reader.pages[q["gold_page"] - 1].extract_text() or "").strip()
        assert q["evidence_quote"] in text, f"Gold quote not on page: {q['id']}"
        if "filter" in q:
            assert q["filter"] == {"section": pages[q["gold_page"]]["section"]}, q["id"]
            assert "part " in q["question"].lower(), q["id"]
            filters[q["split"]] += 1
    assert sum(filters.values()) >= 3 and filters["test"] >= 1, filters
    print(f"Validated {len(questions)} questions: {counts['dev']} dev, {counts['test']} test, {sum(filters.values())} with filters ({filters['test']} test)")


if __name__ == "__main__":
    main()
