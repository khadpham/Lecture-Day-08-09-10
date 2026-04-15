# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** 2A202600153 - Nguyễn Duy Hiếu  
**Vai trò:** Cleaning Owner  
**Ngày nộp:** 15/04/2026  

---

## 1. Tôi phụ trách phần nào?

**File / module:**
Tôi phụ trách toàn bộ ranh giới Transform (Làm sạch). Tôi trực tiếp viết file `transform/cleaning_rules.py`, xử lý logic của hàm `clean_rows` để nhận dạng và cách ly (quarantine) các bản ghi chứa dữ liệu bẩn từ đầu vào 10 bản ghi thô.

**Kết nối với thành viên khác:**
Dữ liệu `cleaned` và `quarantine` do tôi xuất ra là nguồn sống trực tiếp cho Khôi (Quality) chạy bộ kiểm định Expectation và Kha (Embed) đẩy vào ChromaDB.

**Bằng chứng (commit / comment trong code):**
Tôi đã viết 3 luật mới (non-trivial): (1) Quarantine Empty Chunks, (2) Date Format Normalisation, (3) Exact Deduplication. Đoạn code tiêu biểu là việc dùng hàm `hash()` để bắt trùng lặp.

---

## 2. Một quyết định kỹ thuật

Quyết định khó nhất của tôi là chọn định dạng lưu trữ file cách ly (format quarantine). Bất kỳ bản ghi nào bị loại (ví dụ: dòng số 7 là policy HR 2025) không được phép biến mất âm thầm. Tôi quyết định can thiệp vào lược đồ (schema) của tệp cách ly bằng cách tự động gắn thêm cột `quarantine_reason` vào `quarantine_csv`. Quyết định này ép hệ thống phải ghi rõ lý do (ví dụ: "Stale HR Policy" hay "Empty chunk_text"). Việc này giúp Data Owner của hệ thống HR/CS thượng nguồn biết chính xác tại sao dữ liệu của họ bị từ chối để tiến hành sửa chữa tận gốc, đảm bảo tính Data Contract.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Triệu chứng: Khi kiểm tra dữ liệu mẫu, tôi phát hiện dòng số 2 và dòng số 1 có nội dung `chunk_text` và `doc_id` giống hệt nhau. Nếu để nguyên, Vector DB sẽ bị phình to (bloat) và LLM sẽ bị thiên lệch do truy xuất ra 2 vector trùng lặp.
Metric phát hiện: Bằng mắt thường trên file thô, và sau đó được tự động hóa.
Cách fix: Tôi xây dựng logic `Exact Deduplication`. Hệ thống tạo một mã băm `row_hash = hash(f"{doc_id}_{chunk_text}")` và lưu vào `seen_hashes`. Khi dòng số 2 đi qua, mã hash bị trùng, nó ngay lập tức bị gán `quarantine_reason = "Exact duplicate chunk"` và bị đẩy ra khỏi ranh giới sạch.

---

## 4. Bằng chứng trước / sau

Bằng chứng cho sự hiệu quả của các luật làm sạch là sự thay đổi của biến `quarantine_records` giữa các lần chạy.
**Run ID:** `2026-04-15T08-53Z`
**Log Output:**
```text
cleaned_records=7
quarantine_records=3
cleaned_csv=artifacts\cleaned\cleaned_2026-04-15T08-53Z.csv
Từ 10 records thô, hệ thống của tôi đã cách ly thành công 1 dòng rỗng, 1 dòng HR 2025 và 1 dòng trùng lặp, đẩy chỉ số quarantine_records từ 0 lên 3 một cách chuẩn xác.
```
---

## 5. Cải tiến tiếp theo
Nếu có thêm 2 giờ, tôi sẽ nâng cấp hàm Deduplication từ "Exact Match" (so sánh chuỗi/hash tuyệt đối) thành "Semantic Deduplication" (so sánh độ tương đồng nhúng - cosine similarity) để bắt được cả những câu viết khác nhau nhưng có chung ý nghĩa.


---