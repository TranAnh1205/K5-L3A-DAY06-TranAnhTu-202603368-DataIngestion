"""Check persistent upsert and stale-point removal without embedding downloads.

Run from starter/: python -m src.check_reingest
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import NAMESPACE_URL, uuid5

from .models import Chunk
from .store import LocalQdrantStore


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "results/reingest_check.json"


def chunk(chunk_id: str, text: str, section: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id="synthetic_reingest_probe",
        source="synthetic://reingest-probe",
        page=1,
        text=text,
        metadata={"section": section, "printed_page": 1},
    )


def snapshot(store: LocalQdrantStore) -> dict[str, object]:
    points, offset = store.client.scroll(
        collection_name=store.collection_for("A"),
        limit=100,
        with_payload=True,
        with_vectors=False,
    )
    if offset is not None:
        raise AssertionError("Probe unexpectedly exceeded one page of points")
    return {
        "count": store.count("A"),
        "point_ids": sorted(str(point.id) for point in points),
        "chunk_ids": sorted(point.payload["chunk_id"] for point in points),
        "texts": {point.payload["chunk_id"]: point.payload["text"] for point in points},
    }


def main() -> None:
    # TemporaryDirectory creates a fresh, isolated store and removes it after close().
    with TemporaryDirectory(prefix="day06_reingest_") as location:
        store = LocalQdrantStore(Path(location) / "qdrant", dimensions=2)
        try:
            initial_chunks = [
                chunk("probe:a", "First version", "overview"),
                chunk("probe:b", "Stale record", "part_1_poverty_equity_update"),
            ]
            initial_vectors = [[1.0, 0.0], [0.0, 1.0]]
            store.replace("A", initial_chunks, initial_vectors)
            first = snapshot(store)
            store.replace("A", initial_chunks, initial_vectors)
            repeated = snapshot(store)
            if first != repeated or first["count"] != 2:
                raise AssertionError("Repeating ingest changed point IDs, payloads, or count")

            changed_chunks = [chunk("probe:a", "Updated version", "overview")]
            store.replace("A", changed_chunks, [[1.0, 0.0]])
            changed = snapshot(store)
            if changed["count"] != 1 or changed["chunk_ids"] != ["probe:a"]:
                raise AssertionError("Changed ingest did not delete the stale point")
            if changed["point_ids"] != [str(uuid5(NAMESPACE_URL, "probe:a"))]:
                raise AssertionError("Surviving chunk did not retain its stable point ID")
            if changed["texts"] != {"probe:a": "Updated version"}:
                raise AssertionError("Upsert did not update the surviving chunk payload")
            allowed = store.search("A", [1.0, 0.0], filters={"section": "overview"})
            excluded = store.search("A", [1.0, 0.0], filters={"section": "part_1_poverty_equity_update"})
            if len(allowed) != 1 or allowed[0]["chunk_id"] != "probe:a" or excluded:
                raise AssertionError("Filtered search returned a stale or disallowed point")
        finally:
            store.close()

    result = {
        "probe": "isolated synthetic vectors; not the 67-page benchmark corpus",
        "same_data_reingest": {"before": first["count"], "after": repeated["count"], "ids_unchanged": first["point_ids"] == repeated["point_ids"]},
        "changed_data_reingest": {"before": repeated["count"], "after": changed["count"], "stale_chunk_removed": "probe:b" not in changed["chunk_ids"], "surviving_chunk_updated": changed["texts"]["probe:a"] == "Updated version"},
        "filter_check": {"matching_hits": len(allowed), "excluded_hits": len(excluded)},
        "note": "The production pipeline re-embeds all chunks on each run; this probe verifies store semantics only.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Reingest probe passed; wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
