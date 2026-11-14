"""Prepare source-linked review cards for student audit; never assign final labels.

Run from starter/: python -m src.build_audit_pack
The output is created once to protect any handwritten review notes.
"""

import json
from pathlib import Path

from .ingestion import load_pdf, normalize_text


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
OUTPUT = RESULTS / "audit_review_pack.md"


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(f"Review pack already exists; refusing to overwrite student notes: {OUTPUT}")
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    questions = {q["id"]: q for q in json.loads((ROOT / "benchmark/questions.json").read_text(encoding="utf-8"))}
    draft = json.loads((RESULTS / "audit_draft.json").read_text(encoding="utf-8"))
    traces = {(row["strategy"], row["id"]): row for row in json.loads((RESULTS / "test_traces.json").read_text(encoding="utf-8"))}
    pages = {p.page: p.text for p in load_pdf(ROOT / manifest["local_path"], manifest["source_id"], manifest["source_path_or_url"])}
    lines = [
        "# Phiếu duyệt audit của học viên",
        "",
        "**Học viên:** Trần Anh Tú · **MSSV:** 202603368 · **Lớp:** L3A",
        "",
        "**Trạng thái:** chưa được học viên xác nhận. Các điểm bên dưới là nhãn AI đề xuất; ô `Điểm sau khi xem` để trống có chủ ý.",
        "",
        "Đọc đoạn PDF ở trang vật lý ghi trong từng mục, so với chunk/trace và thang 0–2 trong GUIDE.md. Điền điểm cuối, lý do nếu sửa, họ tên và ngày. Cập nhật `results/audit_draft.json` và báo cáo nếu điểm thay đổi. Không gọi phiếu này là audit thủ công trước khi hoàn tất.",
        "",
        "Người kiểm tra: ____________________   Ngày: __________   Đã đối chiếu PDF: [ ]",
        "",
        "## A. Coherence — 10 vị trí × 3 cấu hình",
        "",
    ]
    for row in draft["coherence_labels"]:
        page, strategy = row["physical_page"], row["strategy"]
        lines.extend([
            f"### Trang PDF {page} · cấu hình {strategy}", "",
            f"Vị trí nguồn: ký tự {row['source_character_offset']}; anchor: `{row['anchor']}`; chunk ID: `{row['chunk_id']}`.", "",
            "**Chunk cần đọc:**", "", "```text", row["chunk_text"].rstrip(), "```", "",
            f"Điểm đề xuất: **{row['score_0_to_2']}/2** — {row['reason']}", "",
            "- [ ] Đã đối chiếu trang PDF và ngữ cảnh trước/sau chunk.",
            "- Điểm sau khi xem (0/1/2): ____  Lý do nếu sửa: ____________________", "",
        ])
    lines.extend(["## B. Grounding — 5 câu test × 3 cấu hình", ""])
    for row in draft["grounding_labels"]:
        strategy, qid = row["strategy"], row["question_id"]
        q = questions[qid]
        trace = traces[(strategy, qid)]
        page_text = pages[q["gold_page"]]
        quote = normalize_text(q["evidence_quote"])
        position = page_text.find(quote)
        if position < 0:
            raise ValueError(f"Gold quote missing from source page: {qid}")
        context = page_text[max(0, position - 160):min(len(page_text), position + len(quote) + 160)]
        lines.extend([
            f"### {qid} · cấu hình {strategy}", "",
            f"**Câu hỏi:** {q['question']}", "",
            f"**Đáp án kỳ vọng:** {q['expected_answer']}", "",
            f"**Gold:** trang PDF {q['gold_page']}; nguồn: {manifest['source_path_or_url']}", "",
            f"**Quote:** {q['evidence_quote']}", "",
            "**Ngữ cảnh trên trang nguồn:**", "", "```text", context.rstrip(), "```", "",
            f"Filter yêu cầu: `{json.dumps(q.get('filter'), ensure_ascii=False)}`; filter áp dụng: `{json.dumps(trace['filter_applied'], ensure_ascii=False)}`.", "",
        ])
        for hit in trace["hits"]:
            lines.extend([
                f"**Top {hit['rank']}** · PDF trang {hit['metadata']['page']} · section `{hit['metadata']['section']}` · score {hit['score']:.4f} · exact gold: {hit['exact_evidence_hit']}",
                "", "```text", hit["text"].rstrip(), "```", "",
            ])
        lines.extend([
            f"Điểm grounding đề xuất: **{row['score_0_to_2']}/2** — {row['reason']}", "",
            "- [ ] Đã đọc cả top-3 và trang gold; xác nhận bằng chứng đủ/thiếu cho đáp án.",
            "- Điểm sau khi xem (0/1/2): ____  Lý do nếu sửa: ____________________", "",
        ])
    lines.extend(["## C. Metadata", "",
                  "Chương trình đã so 45 hit test với manifest. Học viên kiểm tra URL nguồn, trang vật lý, trang in và section ở vài hit tiêu biểu, đặc biệt câu filter `t02`.", "",
                  "- [ ] Đã xem `results/audit_draft.json` → `metadata_checks` và đối chiếu ít nhất các hit của `t02` với PDF/manifest.",
                  "- Ghi phát hiện hoặc chỉnh sửa: ____________________", "",
                  "## Xác nhận", "",
                  "- [ ] Hoàn tất cả 30 ô coherence và 15 ô grounding.",
                  "- [ ] Sửa nhãn, bảng tổng hợp và báo cáo nếu khác điểm đề xuất.",
                  "- Họ tên: ____________________   Ngày/giờ: ____________________", ""])
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: 30 coherence and 15 grounding review cards")


if __name__ == "__main__":
    main()
