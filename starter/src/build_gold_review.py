"""Prepare a student review sheet for benchmark answer/evidence sufficiency."""

import json

from .ingestion import load_pdf, normalize_text
from .run import ROOT


OUTPUT = ROOT / "benchmark/gold_review.md"


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(f"Refusing to overwrite review notes: {OUTPUT}")
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    questions = json.loads((ROOT / "benchmark/questions.json").read_text(encoding="utf-8"))
    pages = {p.page: p.text for p in load_pdf(ROOT / manifest["local_path"], manifest["source_id"], manifest["source_path_or_url"])}
    lines = [
        "# Kiểm tra gold của bộ câu hỏi",
        "",
        "**Học viên:** Trần Anh Tú · **MSSV:** 202603368 · **Lớp:** L3A",
        "",
        "Phép kiểm tra tự động chỉ xác nhận quote có trên đúng trang. Học viên cần đọc câu hỏi, đáp án và ngữ cảnh để xác nhận quote đủ chứng minh đáp án, kể cả điều kiện và ngoại lệ. Điền vào ô trống; không xem phiếu chưa điền là bằng chứng đã duyệt thủ công.",
        "",
        "Người kiểm tra: ____________________   Ngày: __________", "",
    ]
    for q in questions:
        page_text = pages[q["gold_page"]]
        quote = normalize_text(q["evidence_quote"])
        index = page_text.find(quote)
        if index < 0:
            raise ValueError(f"Gold quote missing on page {q['gold_page']}: {q['id']}")
        context = page_text[max(0, index - 180):min(len(page_text), index + len(quote) + 180)]
        lines.extend([
            f"## {q['id']} · {q['split']} · {q['type']}", "",
            f"**Câu hỏi:** {q['question']}", "",
            f"**Đáp án:** {q['expected_answer']}", "",
            f"**Nguồn:** {manifest['source_path_or_url']} · trang PDF vật lý {q['gold_page']}", "",
            f"**Filter:** `{json.dumps(q.get('filter'), ensure_ascii=False)}`", "",
            "**Quote và ngữ cảnh trên trang:**", "", "```text", context.rstrip(), "```", "",
            "- [ ] Quote trên trang nguồn đủ chứng minh toàn bộ đáp án và điều kiện trong câu hỏi.",
            "- [ ] Filter, nếu có, được nêu trong câu hỏi trước khi retrieval.",
            "- Ghi chú hoặc trang gold tương đương nếu tìm thấy: ____________________", "",
        ])
    lines.extend(["## Xác nhận", "", "- [ ] Đã duyệt cả 20 câu trên PDF.",
                  "- [ ] Đã sửa `benchmark/questions.json` và chạy lại đánh giá nếu có gold sai; ghi rõ nếu thay đổi sau khi xem test.",
                  "- Họ tên: ____________________   Ngày/giờ: ____________________", ""])
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}: {len(questions)} gold review cards")


if __name__ == "__main__":
    main()
