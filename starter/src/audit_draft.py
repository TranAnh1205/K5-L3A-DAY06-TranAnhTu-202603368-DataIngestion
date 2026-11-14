"""Build a reviewable AI-assisted audit draft from frozen test traces.

The student must inspect these proposed labels against the PDF before submission.
"""

import json
from collections import Counter
from pathlib import Path

from qdrant_client import QdrantClient, models

from .ingestion import load_pdf


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"

# Proposed grounding scores after reading the complete top-3 trace for each test question.
GROUNDING = {
    "A": {"t01": (1, "The gold-page chunk stops during the three-group list; the full answer is missing."),
          "t02": (1, "Top-3 gives a DOU urban-cluster comparison, but not the requested DB town rate."),
          "t03": (2, "Rank 2 contains the flood-risk passage with its welfare mechanism and source."),
          "t04": (2, "Rank 1 contains both 2025 housing targets and their urban/rural conditions."),
          "t05": (1, "Rank 1 stops after the 19 percent migrant figure, before the non-migrant comparison.")},
    "B": {"t01": (0, "Top-3 discusses monitoring and recovery but does not identify the three groups."),
          "t02": (1, "Top-3 gives a DOU comparison, not the requested DB town rate."),
          "t03": (2, "Rank 3 contains the complete flood-risk passage."),
          "t04": (2, "Rank 2 contains both housing targets and the 2025 context."),
          "t05": (2, "Rank 1 contains both migrant and non-migrant rates.")},
    "C": {"t01": (0, "No filter was requested; top-3 does not name the three groups."),
          "t02": (2, "Filtered rank 2 contains the DB town and urban-core comparison."),
          "t03": (2, "Rank 3 contains the complete flood-risk passage."),
          "t04": (2, "Rank 2 contains both housing targets and the 2025 context."),
          "t05": (2, "Rank 1 contains both migrant and non-migrant rates.")},
}

# Same pre-defined sample: character 240 on the first ten eligible PDF pages.
COHERENCE = {
    "A": {11: (1, "Ends mid-sentence at 'easily'."), 12: (1, "Ends mid-word at 'reduc'."),
          13: (1, "Ends before completing the sentence about job vulnerability."),
          14: (1, "Ends mid-list at 'urban'."), 15: (1, "Ends mid-word at 'far'."),
          16: (1, "Ends mid-phrase at 'In the case o'."), 18: (1, "Ends mid-word at 'non'."),
          19: (1, "Ends mid-word after introducing income sources."),
          20: (1, "Ends mid-sentence at 'by'."), 21: (1, "Ends mid-word at 'V'.")},
    "B": {11: (2, "The labor-shift idea ends at a sentence boundary."),
          12: (2, "The spending examples are complete sentences."),
          13: (2, "The mobility and incomplete transformation statements are complete."),
          14: (1, "The page starts with a sentence fragment despite a clean ending."),
          15: (2, "Rural-development statements retain their context."),
          16: (1, "The page starts with 'risk, among other trends', an inherited fragment."),
          18: (2, "The poverty-measurement sentence is complete and traceable."),
          19: (2, "The Part 1 introduction ends at a sentence boundary."),
          20: (2, "The first paragraph is understandable despite a footnote marker."),
          21: (2, "The inequality comparison is expressed in complete sentences.")},
}


def main() -> None:
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    traces = json.loads((RESULTS / "test_traces.json").read_text(encoding="utf-8"))
    page_info = {p["physical_page"]: p for p in manifest["pages"]}
    source_pages = {p.page: p for p in load_pdf(ROOT / manifest["local_path"], manifest["source_id"], manifest["source_path_or_url"])}
    client = QdrantClient(path=str(ROOT / "starter/qdrant_storage"))
    try:
        coherence = []
        for item in manifest["pages"][:10]:
            page = item["physical_page"]
            anchor = source_pages[page].text[240:270]
            for strategy in "ABC":
                base = "A" if strategy == "A" else "B"
                collection = "day06_fixed_a" if base == "A" else "day06_sentences_b"
                points, _ = client.scroll(
                    collection_name=collection,
                    scroll_filter=models.Filter(must=[models.FieldCondition(key="page", match=models.MatchValue(value=page))]),
                    limit=100, with_payload=True,
                )
                matches = [p for p in points if anchor in p.payload["text"]]
                if len(matches) != 1:
                    raise ValueError(f"Expected one matching chunk for {strategy}/{page}, got {len(matches)}")
                score, reason = COHERENCE[base][page]
                coherence.append({"strategy": strategy, "physical_page": page, "source_character_offset": 240,
                                  "anchor": anchor, "chunk_id": matches[0].payload["chunk_id"],
                                  "chunk_text": matches[0].payload["text"], "score_0_to_2": score, "reason": reason})
    finally:
        client.close()

    metadata = []
    grounding = []
    for trace in traces:
        strategy, qid = trace["strategy"], trace["id"]
        score, reason = GROUNDING[strategy][qid]
        grounding.append({"strategy": strategy, "question_id": qid, "score_0_to_2": score,
                          "reason": reason, "top3_chunk_ids": [h["chunk_id"] for h in trace["hits"]]})
        for hit in trace["hits"]:
            m = hit["metadata"]
            info = page_info[m["page"]]
            valid = (m["document_id"] == manifest["source_id"]
                     and m["source"] == manifest["source_path_or_url"]
                     and m["printed_page"] == info["printed_page"]
                     and m["section"] == info["section"])
            metadata.append({"strategy": strategy, "question_id": qid, "rank": hit["rank"],
                             "chunk_id": hit["chunk_id"], "page": m["page"],
                             "section": m["section"], "source_and_metadata_match_manifest": valid})
    if not all(row["source_and_metadata_match_manifest"] for row in metadata):
        raise ValueError("Metadata mismatch found")
    summary = {}
    for strategy in "ABC":
        c = [x["score_0_to_2"] for x in coherence if x["strategy"] == strategy]
        g = [x["score_0_to_2"] for x in grounding if x["strategy"] == strategy]
        m = [x for x in metadata if x["strategy"] == strategy]
        filtered = [x for x in traces if x["strategy"] == strategy and x["filter_requested"]]
        summary[strategy] = {
            "coherence": {"n": len(c), "mean_out_of_2": sum(c) / len(c), "score_counts": dict(Counter(c))},
            "grounding": {"n": len(g), "mean_out_of_2": sum(g) / len(g), "score_counts": dict(Counter(g))},
            "metadata_correct": {"n": sum(x["source_and_metadata_match_manifest"] for x in m), "N": len(m)},
            "filter_compliance": (
                {"n": sum(all(h["metadata"]["section"] == t["filter_requested"]["section"] for h in t["hits"]) for t in filtered), "N": len(filtered)}
                if strategy == "C" else "not_applied"
            ),
        }
    artifact = {"status": "AI-assisted draft; student review required", "coherence_sample_rule": "First 10 eligible physical pages, character offset 240; same anchors across strategies.",
                "coherence_labels": coherence, "grounding_labels": grounding, "metadata_checks": metadata, "summary": summary,
                "limitations": ["Coherence sample emphasizes page beginnings and may not represent all chunks.",
                                "Metadata checks compare trace fields to the manifest; source-page visual spot checks remain for the student.",
                                "Equivalent evidence on unlisted pages has not been fully adjudicated."]}
    output = RESULTS / "audit_draft.json"
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}: 30 coherence, 15 grounding, 45 metadata records")
    print(summary)


if __name__ == "__main__":
    main()
