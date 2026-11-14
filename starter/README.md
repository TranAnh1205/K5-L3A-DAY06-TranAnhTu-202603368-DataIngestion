# Pipeline cá nhân Day 06

Pipeline hiện tại đọc báo cáo World Bank trong `../data/manifest.json`, tạo embedding thật bằng FastEmbed local và lưu vector trên đĩa bằng Qdrant local mode. Không cần Docker hoặc API key. Các file `docker-compose.yml` và `init.sql` là lựa chọn PostgreSQL/pgvector của starter gốc, không được sử dụng trong lần chạy này.

## Cài đặt và chạy

Từ thư mục gốc repo, dùng Python 3.11–3.14:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r starter/requirements.txt
python data/prepare_corpus.py
python benchmark/validate.py
cd starter
python -m src.run
python -m src.check_reingest
python -m src.check_full_reingest
```

Lần đầu FastEmbed tải model `BAAI/bge-small-en-v1.5` (384 chiều, tiếng Anh). Lỗi tải model hoặc backend sẽ dừng pipeline; không có fallback sang vector giả. Kết quả bước ingestion ở `starter/results/ingestion_summary.json`; Qdrant bền vững ở `starter/qdrant_storage/` (được Git bỏ qua). Để chạy lại, thực hiện `python -m src.run` từ `starter/`. Script upsert theo ID ổn định và xóa chunk không còn thuộc corpus, nên không tích lũy chunk cũ hay nhân đôi khi dữ liệu thay đổi; C dùng đúng collection B và chỉ thay filter ở lúc truy vấn.

`python -m src.check_reingest` chạy phép thử trên một Qdrant tạm với vector tổng hợp: nạp cùng dữ liệu hai lần, cập nhật một chunk, xóa một chunk cũ, rồi kiểm tra filter. Kết quả lưu ở `../results/reingest_check.json`. Phép thử xác nhận hành vi của store, không thay cho việc chạy lại corpus 67 trang. Pipeline hiện tạo lại embedding cho toàn bộ chunk ở mỗi lần chạy.

`python -m src.check_full_reingest` nạp lại corpus thật và kiểm tra hash của tập point ID cùng số điểm trước/sau ở cả hai collection. Kết quả lần chạy đã lưu ở `../results/full_reingest_check.json`: A 484→484, B 549→549, ID không đổi. Lệnh này vẫn tính lại toàn bộ embedding và tốn vài phút. Model cache snapshot và hash file đã quan sát nằm ở `../results/model_provenance.json`; FastEmbed chưa được cấu hình ép revision đó trên máy khác.

## Cấu hình

| Strategy | Chunk | Retrieval |
| --- | --- | --- |
| A | Cửa sổ 500 ký tự, overlap 50, không vượt trang | Cosine, không filter |
| B | Nhóm câu hoàn chỉnh, tối đa 500 ký tự, không vượt trang | Cosine, không filter |
| C | Dùng nguyên chunk và vector của B | Cosine, lọc `section` khi câu hỏi cung cấp |

Mỗi chunk có `document_id`, `source`, số trang PDF vật lý `page`, `printed_page`, và `section`. `section` lấy trực tiếp từ phần Overview / Part 1 / Part 2 của báo cáo; không suy ra từ trang gold ở lúc retrieval. Model và metric giống nhau giữa ba chiến lược. Qdrant local thực hiện tìm kiếm exact cho corpus nhỏ này.

PDF gốc có ngắt dòng, ký tự lỗi và footnote lẫn trong thân bài. B dùng ranh giới câu vì PDF không có dấu phân đoạn văn bản ổn định. Các giới hạn này cần được xem xét khi chấm coherence và evidence.

## Chạy benchmark và audit

Từ thư mục `starter/`, chạy dev trước rồi mới chạy test:

```powershell
..\.venv\Scripts\python.exe -m src.evaluate --split dev
..\.venv\Scripts\python.exe -m src.evaluate --split test
..\.venv\Scripts\python.exe -m src.audit_draft
```

Kết quả nằm ở `../results/`: trace top-3, bảng số liệu dev/test, lựa chọn chiến lược theo dev, bản nháp nhãn AI và bản xác nhận của học viên. Lần test yêu cầu đã có lựa chọn từ dev và sẽ từ chối nếu benchmark hoặc tiêu chí lựa chọn bị thay đổi. Tiêu chí chọn đã ghi ở `../benchmark/selection_policy.json` trước khi chạy test. Điểm retrieval tự động yêu cầu toàn bộ đoạn gold nằm trong một chunk từ đúng trang; bằng chứng tương đương khác cần được xem và ghi nhãn thủ công. `audit_draft.json` là bản AI ban đầu; `audit_confirmed.json` và `audit_review_pack.md` ghi học viên đã xác nhận ngày 14/11/2026.

Phiếu đã xác nhận: `../results/audit_review_pack.md` (30 mục coherence, 15 mục grounding) và `../benchmark/gold_review.md` (20 câu). `python -m src.build_audit_pack` và `python -m src.build_gold_review` chỉ tạo phiếu mới khi chưa tồn tại; không ghi đè bản đã xác nhận. Nếu thay đổi benchmark/trace hoặc tạo lại nhãn, cần học viên xem và xác nhận lại.
