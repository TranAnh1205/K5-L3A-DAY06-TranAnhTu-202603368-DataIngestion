"""Conservative, reproducible retrieval scoring; human labels stay separate."""
from typing import Any

from .ingestion import normalize_text


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]], strategy: str) -> dict[str, Any]:
    """A hit must have the gold document/page and contain its full quoted evidence."""
    quote = normalize_text(question["evidence_quote"])
    ranked = []
    for rank, hit in enumerate(hits, 1):
        metadata = hit["metadata"]
        source_page_match = (
            metadata.get("document_id") == question["gold_source_id"]
            and metadata.get("page") == question["gold_page"]
        )
        full_evidence = quote in normalize_text(hit["text"])
        ranked.append({
            "rank": rank,
            "chunk_id": hit["chunk_id"],
            "text": hit["text"],
            "score": hit["score"],
            "metadata": metadata,
            "gold_source_page_match": source_page_match,
            "full_gold_evidence_in_chunk": full_evidence,
            "exact_evidence_hit": source_page_match and full_evidence,
        })
    return {
        "strategy": strategy,
        "id": question["id"],
        "split": question["split"],
        "question": question["question"],
        "expected_answer": question["expected_answer"],
        "gold_source_id": question["gold_source_id"],
        "gold_page": question["gold_page"],
        "evidence_quote": question["evidence_quote"],
        "filter_requested": question.get("filter"),
        "filter_applied": question.get("filter") if strategy == "C" else None,
        "hits": ranked,
        "hit_at_1": bool(ranked and ranked[0]["exact_evidence_hit"]),
        "evidence_hit_at_3": any(h["exact_evidence_hit"] for h in ranked[:3]),
        "scoring_method": "exact quote in a single chunk on the recorded gold document and page",
        "manual_equivalence_review": "pending",
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Report integer numerators/denominators, separately by strategy and split."""
    result = {}
    for strategy in "ABC":
        rows = [trace for trace in traces if trace["strategy"] == strategy]
        if not rows:
            continue
        split = rows[0]["split"]
        if any(row["split"] != split for row in rows):
            raise ValueError("Do not mix dev and test in one summary")
        n = len(rows)
        hit1 = sum(row["hit_at_1"] for row in rows)
        hit3 = sum(row["evidence_hit_at_3"] for row in rows)
        filter_rows = [row for row in rows if row["filter_requested"]]
        filter_ok = sum(
            all(
                hit["metadata"].get("section") == row["filter_requested"]["section"]
                for hit in row["hits"]
            )
            for row in filter_rows
        ) if strategy == "C" else None
        result[strategy] = {
            "split": split,
            "questions": n,
            "hit_at_1": {"n": hit1, "N": n, "rate": hit1 / n},
            "evidence_hit_at_3": {"n": hit3, "N": n, "rate": hit3 / n},
            "filter_compliance": (
                {"n": filter_ok, "N": len(filter_rows)} if strategy == "C" else "not_applied"
            ),
        }
    return result
