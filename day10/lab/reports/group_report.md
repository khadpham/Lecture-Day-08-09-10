# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** E403 - nhóm 72  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email/MSSV |
|-----|------------------|-------|
| Trần Đặng Quang Huy | Ingestion / Raw Owner | 2A202600292 |
| Nguyễn Duy Hiếu | Cleaning Owner | 2A202600153 |
| Phan Anh Khôi | Quality / Expectation Owner | 2A202600276 |
| Phạm Đan Kha | Embed & Idempotency Owner | 2A202600253 |
| Vũ Đức Kiên | Monitoring / Docs Owner | 2A202600338 |

**Ngày nộp:** 15/04/2026  
**Repo:** (https://github.com/khadpham/Lecture-Day-08-09-10/tree/main/day10/lab)

---

## 1. Pipeline tổng quan

Nguồn raw của hệ thống là tệp CSV tĩnh `data/raw/policy_export_dirty.csv`, mô phỏng một luồng trích xuất dữ liệu thô từ hệ thống cơ sở dữ liệu cốt lõi của bộ phận HR và CS Helpdesk. Tệp này cố tình chứa các dữ liệu nhiễu như: dòng thiếu nội dung, trùng lặp chính xác, sai định dạng ngày tháng, và chứa các chính sách lỗi thời (14 ngày thay vì 7 ngày).

**Tóm tắt luồng (End-to-End):**
Hệ thống bắt đầu bằng việc đọc file CSV và lập tức ghi nhận số dòng thô (`raw_records`) cùng `run_id` (được sinh từ timestamp hoặc truyền tay). Dữ liệu sau đó đi qua ranh giới Transform để chạy các luật làm sạch (loại bỏ và đưa vào file quarantine). Dữ liệu sạch tiếp tục bị chặn lại ở ranh giới Validation để chạy bộ Expectation. Nếu không có lỗi `HALT`, dữ liệu cuối cùng mới được phép đi qua ranh giới Embed để thực hiện quá trình `upsert` và `prune` (xóa rác) vào ChromaDB. Toàn bộ tiến trình được ghi vào tệp manifest.

**Lệnh chạy một dòng (End-to-End chuẩn):**
```bash
python etl_pipeline.py run && python eval_retrieval.py --out artifacts/eval/before_after_eval.csv
```

---

## 2. Cleaning & expectation

Nhóm không chỉ sử dụng baseline mà đã thiết kế thêm **3 rule làm sạch mới** (bắt dòng rỗng, cách ly HR 2025, hash deduplication) và **2 expectation mới** (validate ngày ISO 8601 mức độ HALT, cảnh báo tài liệu legacy mức độ WARN). Các luật này thực sự làm thay đổi số liệu đầu ra chứ không mang tính đối phó (trivial).

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
| :--- | :--- | :--- | :--- |
| **Rule: Quarantine Empty** | Raw có 1 dòng rỗng (`chunk_text`="") | `quarantine_records` tăng thêm 1 | Log clean run: `quarantine_records=3` |
| **Rule: Quarantine 2025 HR** | Raw có 1 bản policy năm 2025 | `quarantine_records` tăng thêm 1 | Log clean run: `quarantine_records=3` |
| **Rule: Exact Deduplication** | Raw có 2 dòng nội dung giống hệt | `quarantine_records` tăng thêm 1 | Log clean run: `quarantine_records=3` |
| **Expectation: No 14-day refund (HALT)** | Clean pipeline: 0 lỗi, OK (HALT) | Inject bad (bỏ fix): 1 lỗi, FAIL (HALT) | Log `inject-bad`: `Failed: Found 1 chunks still containing stale 14-day policy.` |
| **Expectation: No legacy docs (WARN)** | Không có cảnh báo ở source system | Bắt được 1 lỗi, báo FAIL (WARN) | Log clean & bad: `Warning: Ingested 1 legacy documents.` |

**Rule chính (baseline + mở rộng):**
Bộ rule bao gồm việc chuẩn hóa toàn bộ ngày tháng về định dạng ISO-8601 (YYYY-MM-DD), vá cứng chuỗi văn bản "14 ngày làm việc" thành "7 ngày làm việc", và mã hóa băm (`hash()`) các nội dung để đảm bảo không một vector trùng lặp nào được phép tiến tới hàm Embed.

**Ví dụ 1 lần expectation fail và cách xử lý:**
Trong quá trình test (Sprint 3), nhóm truyền cờ `--no-refund-fix` để giữ nguyên lỗi chính sách 14 ngày. Ngay lập tức, hàm validation bắt được chuỗi "14 ngày" và văng log: `expectation[expect_no_14_day_refund] FAIL (HALT)`. Cách xử lý đúng quy trình: Nhóm tháo cờ bypass ra và chạy lại pipeline chuẩn. Lúc này, luật Transform chạy trước đã vá chuỗi 14 thành 7 ngày, giúp ranh giới Validation trả về `OK (HALT)` và hệ thống vận hành tiếp.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent

Bằng chứng mạnh mẽ nhất cho hệ thống Observability của nhóm nằm ở kết quả đánh giá (Evaluation) sau khi tiêm mã độc (Inject Corruption) ở Sprint 3.

**Kịch bản inject:**
Nhóm cố tình làm hỏng Vector DB bằng cách chạy lệnh: 
`python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`
Lệnh này ép hệ thống bỏ qua việc vá lỗi văn bản và cấm pipeline dừng lại dù Expectation kêu gọi `HALT`. Hậu quả là chính sách 14 ngày cũ bị đẩy thẳng vào ChromaDB.

**Kết quả định lượng (từ CSV / bảng):**
Sau khi Inject, nhóm sử dụng file câu hỏi chuẩn và sinh ra `artifacts/eval/after_inject_bad.csv`. Đối với câu truy vấn `q_refund_window`:
* **Trước (Inject Bad):** LLM báo `contains_expected=yes` VÀ `hits_forbidden=yes`. Dữ liệu 14 ngày cũ đã xuất hiện trong top-k context. Agent nếu đọc context này sẽ bị nhiễu và trả lời sai SLA cho khách.
* **Sau (Clean Run):** Nhóm chạy lại pipeline chuẩn. Cơ sở dữ liệu được làm sạch và cắt tỉa (prune) các vector ID cũ. Kết quả trong `before_after_eval.csv` chuyển thành `contains_expected=yes` VÀ `hits_forbidden=no`. Context hoàn toàn sạch sẽ, hệ thống an toàn tuyệt đối cho Agent sử dụng.

---

## 4. Freshness & monitoring

Nhóm cấu hình biến môi trường `FRESHNESS_SLA_HOURS=24` (SLA là 24 giờ). 
* **PASS:** Cảnh báo ổn định, file gốc vừa được hệ thống HR/CS xuất ra trong vòng 24 giờ qua.
* **WARN:** Dữ liệu đang chuẩn bị hết hạn SLA.
* **FAIL:** Dữ liệu nguồn đã quá cũ. Trên manifest mẫu báo `FAIL` (age_hours: 120.902) do file `policy_export_dirty.csv` mô phỏng ngày xuất là mùng 10/04/2026, trong khi ngày chúng ta chạy pipeline là 15/04/2026. Báo cáo FAIL ở đây chứng tỏ hệ thống đo đạc hoạt động hoàn toàn chính xác theo nguyên lý thiết kế.

---

## 5. Liên hệ Day 09

Hệ thống ETL của Lab Day 10 đóng vai trò là "màng lọc tinh" cho hệ thống Multi-Agent (CS + IT Helpdesk) được xây dựng ở Day 09. Thay vì để Agent Day 09 kết nối vào các tệp tài liệu tĩnh chứa đầy rác và mâu thuẫn (như việc 1 nhân sự dưới 3 năm vừa được nghỉ 10 ngày lại vừa được 12 ngày), chúng ta sẽ cấu hình cho Agent truy xuất trực tiếp vào collection `day10_kb`. Ranh giới Embed Idempotent đảm bảo Agent luôn luôn nhận được luồng dữ liệu "Single Source of Truth" duy nhất.

---

## 6. Rủi ro còn lại & việc chưa làm

- Cơ sở dữ liệu ChromaDB hiện lưu ở tệp cục bộ (`./chroma_db`), rủi ro cao gây ra lỗi khóa tệp (file-locking) nếu nhiều người trong team chạy script đồng thời. Cần nâng cấp lên Vector Database trên Docker.
- Luật phát hiện trùng lặp hiện tại chỉ là Exact Match (khớp tuyệt đối chuỗi). Chưa có khả năng phát hiện trùng lặp theo ngữ nghĩa (Semantic Deduplication).
- Thiếu cơ chế Webhook/Alert. Hiện tại pipeline `HALT` chỉ in ra terminal; cần tính năng tự động bắn tin nhắn về kênh Slack/Teams cho Data Owner.