# Kiểm tra nhãn audit trước khi nộp

Bản dưới là nhãn **AI đề xuất**. Học viên mở `test_traces.json` và PDF gốc, đối chiếu từng chunk/trang, rồi ghi ngày và tên người kiểm tra. Chỉ sau khi kiểm tra mới mô tả đây là audit thủ công trong báo cáo.

Phiếu chi tiết [audit_review_pack.md](audit_review_pack.md) hiển thị toàn văn 30 chunk coherence và top-3 của 15 lượt grounding, kèm ô để ghi điểm sau khi xem. Bảng dưới chỉ là bản tóm tắt.

## Grounding: 5 câu test × 3 cấu hình

| Câu | A | B | C |
| --- | --- | --- | --- |
| t01 | 1/2 — The gold-page chunk stops during the three-group list; the full answer is missing. | 0/2 — Top-3 discusses monitoring and recovery but does not identify the three groups. | 0/2 — No filter was requested; top-3 does not name the three groups. |
| t02 | 1/2 — Top-3 gives a DOU urban-cluster comparison, but not the requested DB town rate. | 1/2 — Top-3 gives a DOU comparison, not the requested DB town rate. | 2/2 — Filtered rank 2 contains the DB town and urban-core comparison. |
| t03 | 2/2 — Rank 2 contains the flood-risk passage with its welfare mechanism and source. | 2/2 — Rank 3 contains the complete flood-risk passage. | 2/2 — Rank 3 contains the complete flood-risk passage. |
| t04 | 2/2 — Rank 1 contains both 2025 housing targets and their urban/rural conditions. | 2/2 — Rank 2 contains both housing targets and the 2025 context. | 2/2 — Rank 2 contains both housing targets and the 2025 context. |
| t05 | 1/2 — Rank 1 stops after the 19 percent migrant figure, before the non-migrant comparison. | 2/2 — Rank 1 contains both migrant and non-migrant rates. | 2/2 — Rank 1 contains both migrant and non-migrant rates. |

## Coherence: cùng 10 vị trí nguồn

Mẫu là ký tự 240 trên 10 trang nội dung đầu; C dùng lại chunk của B. Toàn văn chunk và lý do chấm nằm trong `audit_draft.json`.

| Trang PDF vật lý | A /2 | B /2 | C /2 |
| ---: | ---: | ---: | ---: |
| 11 | 1 | 2 | 2 |
| 12 | 1 | 2 | 2 |
| 13 | 1 | 2 | 2 |
| 14 | 1 | 1 | 1 |
| 15 | 1 | 2 | 2 |
| 16 | 1 | 1 | 1 |
| 18 | 1 | 2 | 2 |
| 19 | 1 | 2 | 2 |
| 20 | 1 | 2 | 2 |
| 21 | 1 | 2 | 2 |

## Metadata và xác nhận

- [ ] Xem `audit_draft.json`: 45 dòng `metadata_checks`, xác nhận URL nguồn, trang vật lý, trang in và `section` theo `data/manifest.json`.
- [ ] Xem lại 15 nhãn grounding và lý do ở trên trong `results/test_traces.json`; chỉnh nhãn nếu cần.
- [ ] Xem lại 30 nhãn coherence và chunk tương ứng trong `results/audit_draft.json`; chỉnh nhãn nếu cần.
- [ ] Ghi trong báo cáo ai đã kiểm tra nhãn, ngày kiểm tra và những chỉnh sửa.
- [ ] Sau khi xác nhận, tạo commit/tag cuối và đẩy repo lên GitHub; nộp link theo kênh lớp.
