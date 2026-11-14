# Day 06 · Data Ingestion Engineering

> Bài làm cá nhân của Trần Anh Tú (202603368, L3A): 67 trang báo cáo World Bank, FastEmbed + Qdrant local, ba cấu hình A/B/C, benchmark 20 câu và kết quả dev/test. Xem [hướng dẫn chạy](starter/README.md), [manifest](data/manifest.json), [benchmark](benchmark/README.md), [kết quả](results/README.md) và [báo cáo cá nhân](report/individual/202603368_TranAnhTu.md). Audit trong báo cáo là nhãn AI đề xuất, cần học viên xác nhận trước khi nộp.

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Pipeline đã hiện thực trong `starter/src/` và dùng Qdrant local, không cần Docker. Chạy từ thư mục gốc repo trên PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r starter\requirements.txt
.\.venv\Scripts\python.exe data\prepare_corpus.py
.\.venv\Scripts\python.exe benchmark\validate.py
cd starter
..\.venv\Scripts\python.exe -m src.run
..\.venv\Scripts\python.exe -m src.check_reingest
..\.venv\Scripts\python.exe -m src.evaluate --split dev
..\.venv\Scripts\python.exe -m src.evaluate --split test
..\.venv\Scripts\python.exe -m src.audit_draft
```

Lần đầu tải model cần mạng. Chạy dev trước test để chốt chiến lược; test sẽ từ chối nếu benchmark hoặc quy tắc chọn thay đổi. PDF gốc và kho vector local được Git bỏ qua; người chấm có thể tải lại PDF từ nguồn trong manifest. Xem [hướng dẫn chi tiết](starter/README.md).

Minh chứng nạp lặp corpus thật ở [results/full_reingest_check.json](results/full_reingest_check.json). Học viên duyệt đáp án/quote bằng [benchmark/gold_review.md](benchmark/gold_review.md) và nhãn audit bằng [results/audit_review_pack.md](results/audit_review_pack.md) trước khi nộp; các ô xác nhận hiện để trống.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup pipeline FastEmbed + Qdrant local | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) là ví dụ định dạng từ repo đề bài; corpus thật của bài làm nằm trong [manifest](data/manifest.json). Không xây chatbot vì đề không yêu cầu.
