"""Rerun the real 67-page corpus and verify stable on-disk Qdrant indexes.

Run from starter/: python -m src.check_full_reingest
This intentionally repeats all local embedding work and may take minutes.
"""

import hashlib
import json
import time
from pathlib import Path

from .run import ROOT, STORE_PATH, main as ingest_main
from .store import LocalQdrantStore


OUTPUT = ROOT / "results/full_reingest_check.json"
DIMENSIONS = 384


def snapshot() -> dict[str, dict[str, object]]:
    store = LocalQdrantStore(STORE_PATH, DIMENSIONS)
    try:
        result = {}
        for strategy in "AB":
            collection = store.collection_for(strategy)
            if not store.client.collection_exists(collection):
                raise ValueError(f"Missing collection: {collection}")
            point_ids = []
            offset = None
            while True:
                points, offset = store.client.scroll(
                    collection_name=collection,
                    offset=offset,
                    limit=100,
                    with_payload=False,
                    with_vectors=False,
                )
                point_ids.extend(str(point.id) for point in points)
                if offset is None:
                    break
            point_ids.sort()
            count = store.count(strategy)
            if count != len(point_ids) or len(point_ids) != len(set(point_ids)):
                raise AssertionError(f"Count or IDs inconsistent in {collection}")
            digest = hashlib.sha256("\n".join(point_ids).encode("ascii")).hexdigest()
            result[strategy] = {"collection": collection, "count": count, "sorted_point_ids_sha256": digest}
        return result
    finally:
        store.close()


def main() -> None:
    before = snapshot()
    print(f"Before: A={before['A']['count']}, B={before['B']['count']}", flush=True)
    started = time.perf_counter()
    ingest_main()
    elapsed = round(time.perf_counter() - started, 2)
    after = snapshot()
    if before != after:
        raise AssertionError(f"Full corpus reingest changed point IDs or counts: {before} -> {after}")
    ingest_summary = json.loads((ROOT / "starter/results/ingestion_summary.json").read_text(encoding="utf-8"))
    if after["A"]["count"] != ingest_summary["chunk_counts"]["A"] or after["B"]["count"] != ingest_summary["chunk_counts"]["B"]:
        raise AssertionError("Stored counts do not match ingestion summary")
    result = {
        "scope": "real 67-page World Bank corpus, local Qdrant on-disk store",
        "source_sha256": ingest_summary["source_sha256"],
        "model": ingest_summary["model"],
        "before": before,
        "after": after,
        "same_ids_and_counts": True,
        "elapsed_seconds": elapsed,
        "embedding_cache": False,
        "note": "All document embeddings were recomputed on this pass; this proves stable store IDs/counts, not incremental embedding efficiency.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Full corpus reingest passed in {elapsed}s; wrote {OUTPUT.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
