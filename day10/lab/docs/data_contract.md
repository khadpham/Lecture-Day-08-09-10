# Data contract — Lab Day 10

> Được mở rộng và đồng bộ từ cấu hình `contracts/data_contract.yaml`.

---

## 1. Bản đồ Nguồn (Source Map)

| Hệ thống nguồn (Source System) | Mô tả | Tần suất cập nhật (Expected Refresh) | Dạng lỗi rủi ro (Failure Mode) | Chỉ số giám sát (Monitoring Metric) |
| :--- | :--- | :--- | :--- | :--- |
| **HR_Core_DB** | Nguồn chính lưu trữ các chính sách nhân sự và ngày phép của nhân viên. | Hàng ngày lúc 00:00 UTC | Xuất dữ liệu cũ/lỗi thời (thiếu bản cập nhật chính sách mới nhất của năm 2026). | `freshness_hours` < 24h |
| **CS_Helpdesk_Wiki** | Nguồn lưu trữ chính sách hoàn tiền và SLA cho dịch vụ khách hàng. | Thời gian thực (Event-driven) | Xung đột thời hạn chính sách trong cùng một luồng xuất (ví dụ: tồn tại cả 14 ngày và 7 ngày). | `expectation_halt_count` = 0 |

---

## 2. Định nghĩa Schema (Dữ liệu đã làm sạch - Cleaned Data)

Tất cả dữ liệu sau khi qua ranh giới Validate phải đáp ứng cấu trúc sau trước khi được phép đưa vào ChromaDB:
* `doc_id` (String): Mã định danh duy nhất của tài liệu.
* `chunk_text` / `content` (String): Nội dung văn bản chi tiết để tạo vector (Tuyệt đối không được rỗng).
* `effective_date` (String): Ngày chính sách bắt đầu có hiệu lực, bị ép buộc chuẩn hóa theo định dạng **ISO-8601 (YYYY-MM-DD)**.
* `exported_at` (String): Thời điểm xuất dữ liệu từ hệ thống nguồn, dùng để tính toán SLA Freshness.
* `quarantine_reason` (String - *Chỉ có ở file cách ly*): Lý do bản ghi không đạt chuẩn (ví dụ: "Empty chunk_text" hoặc "Exact duplicate chunk").

---

## 3. Quy tắc quarantine vs drop

* **Quarantine (Cách ly):** Bất kỳ bản ghi nào vi phạm các luật làm sạch (ví dụ: dòng không có nội dung, chính sách HR của năm 2025 đã cũ, trùng lặp exact-match) sẽ **không bị xóa (drop) hoàn toàn** một cách âm thầm. Thay vào đó, chúng được đưa vào tệp `artifacts/quarantine/quarantine_*.csv` kèm theo cột `quarantine_reason` để lưu vết.
* **Quy trình xử lý & Merge lại:** Nhóm Data Engineering không tự ý sửa trực tiếp trên file thô rồi merge. Hệ thống sẽ báo cáo số liệu `quarantine_records` cho Data Owner của hệ thống nguồn (Admin hệ thống HR hoặc CS). Data Owner phải sửa dữ liệu tận gốc (trên CMS/Database). Sau khi sửa, luồng cronjob tự động xuất file mới và pipeline chạy lại sẽ tự động ingest dữ liệu sạch đó.

---

## 4. Phiên bản & canonical (Bản chuẩn)

* **Source of Truth (Nguồn chân lý) cho Hệ thống:** Tệp tin `artifacts/cleaned/cleaned_*.csv` được sinh ra từ lần chạy pipeline thành công gần nhất (Exit code 0) chính là "canonical version" duy nhất cho Knowledge Base. Vector DB chỉ được phép đồng bộ từ tệp này.
* **Giải quyết xung đột phiên bản:**
  * **Policy Refund (CS):** Phiên bản `policy_refund_v4` quy định "7 ngày làm việc" là bản canonical. Các phiên bản cũ chứa "14 ngày" sẽ bị vá hoặc hệ thống tự động `HALT`.
  * **Leave Policy (HR):** Phiên bản áp dụng cho năm 2026 (nhân viên dưới 3 năm được 12 ngày phép) là bản canonical. Bản 2025 lập tức bị flag và đưa vào quarantine.