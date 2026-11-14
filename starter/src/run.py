"""Ingest the verified corpus with controlled A/B/C data strategies.

Step 3 builds the persistent index. Full benchmark evaluation is Step 4.
Run from starter/: python -m src.run
"""

import hashlib
import json
import time
from collections import Counter
from importlib.metadata import version
from pathlib import Path

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .ingestion import load_pdf
from .store import LocalQdrantStore


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/manifest.json"
STORE_PATH = ROOT / "starter/qdrant_storage"
SUMMARY = ROOT / "starter/results/ingestion_summary.json"


def main() -> None:
    started = time.perf_counter()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pdf = ROOT / manifest["local_path"]
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != manifest["snapshot_sha256"]:
        raise ValueError("Source PDF does not match the frozen manifest snapshot")
    all_pages = load_pdf(pdf, manifest["source_id"], manifest["source_path_or_url"])
    selected = {p["physical_page"]: p for p in manifest["pages"]}
    if len(selected) < 30:
        raise ValueError("Corpus has fewer than 30 eligible content pages")
    pages = []
    for page in all_pages:
        entry = selected.get(page.page)
        if entry is None:
            continue
        if len(page.text) != entry["normalized_character_count"]:
            raise ValueError(f"Page {page.page} text changed since manifest creation")
        page.metadata = {"section": entry["section"], "printed_page": entry["printed_page"]}
        pages.append(page)
    if len(pages) != len(selected):
        raise ValueError("Some manifest pages were not found in the PDF")

    chunks_a = [chunk for page in pages for chunk in fixed_size(page, size=500, overlap=50)]
    chunks_b = [chunk for page in pages for chunk in by_paragraph(page, max_size=500)]
    if not chunks_a or not chunks_b:
        raise ValueError("Chunking produced no data")

    model = MyEmbedder()
    store = LocalQdrantStore(STORE_PATH, model.dimensions)
    try:
        vectors_a = model.embed_documents([c.text for c in chunks_a])
        store.replace("A", chunks_a, vectors_a)
        vectors_b = model.embed_documents([c.text for c in chunks_b])
        store.replace("B", chunks_b, vectors_b)
        counts = {strategy: store.count(strategy) for strategy in "ABC"}
        if counts != {"A": len(chunks_a), "B": len(chunks_b), "C": len(chunks_b)}:
            raise ValueError(f"Stored point count mismatch: {counts}")
        # A dev question checks that real vector search and the trusted filter work.
        dev = next(q for q in json.loads((ROOT / "benchmark/questions.json").read_text(encoding="utf-8"))
                   if q["split"] == "dev" and q.get("filter"))
        hits = store.search("C", model.embed_query(dev["question"]), filters=dev["filter"])
        if not hits or any(h["metadata"]["section"] != dev["filter"]["section"] for h in hits):
            raise ValueError("Filtered vector search returned no result or violated its filter")
    finally:
        store.close()

    summary = {
        "source_id": manifest["source_id"],
        "source_sha256": manifest["snapshot_sha256"],
        "included_pages": len(pages),
        "section_page_counts": dict(Counter(p.metadata["section"] for p in pages)),
        "strategy_config": {
            "A": {"chunking": "fixed_characters", "size": 500, "overlap": 50, "filter": False},
            "B": {"chunking": "sentence_groups", "max_size": 500, "overlap": 0, "filter": False},
            "C": {"chunking": "sentence_groups", "max_size": 500, "overlap": 0, "filter": "section_when_provided"},
        },
        "chunk_counts": counts,
        "model": model.model_name,
        "model_dimensions": model.dimensions,
        "embedding_provider": "FastEmbed local ONNX",
        "fastembed_version": version("fastembed"),
        "vector_store": "Qdrant local on-disk",
        "qdrant_client_version": version("qdrant-client"),
        "vector_store_path": str(STORE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "distance": "cosine",
        "search": "exact local",
        "api_cost_usd": 0,
        "ingest_elapsed_seconds": round(time.perf_counter() - started, 2),
        "dev_smoke_query_id": dev["id"],
        "dev_smoke_top3_pages": [h["metadata"]["page"] for h in hits],
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {len(pages)} pages: A={counts['A']}, B=C={counts['B']} chunks")
    print(f"Dev filtered search {dev['id']}: pages {summary['dev_smoke_top3_pages']}")
    print(f"Wrote {SUMMARY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
