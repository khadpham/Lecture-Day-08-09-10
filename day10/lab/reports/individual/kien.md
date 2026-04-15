# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** 2A202600338 - Vũ Đức Kiên  
**Vai trò:** Monitoring / Docs Owner  
**Ngày nộp:** 15/04/2026  

---

## 1. Tôi phụ trách phần nào?

**File / module:**
Tôi chịu trách nhiệm về tính khả quan sát (Observability) ở cấp độ vĩ mô và tài liệu hóa. Tôi quản lý module `monitoring/freshness_check.py`, phân tích file Manifest để tính toán độ trễ SLA. Đồng thời, tôi là người tổng hợp toàn bộ báo cáo nhóm (`group_report.md`), soạn thảo Runbook khắc phục sự cố, Kiến trúc Pipeline, và Data Contract.

**Kết nối với thành viên khác:**
Công việc của tôi là lớp vỏ bọc giám sát bên ngoài, thu thập kết quả log từ ranh giới Ingest (Huy) và chất lượng từ Expectation (Khôi) để giải thích kết quả Retrieval (từ Kha) thành báo cáo nghiệp vụ.

**Bằng chứng (commit / comment trong code):**
Tôi đã hoàn thiện các file trong thư mục `docs/` và thiết lập giới hạn kiểm tra SLA trong file `.env` bằng biến `FRESHNESS_SLA_HOURS=24`.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật của tôi liên quan đến việc định nghĩa Ranh giới Freshness (Độ tươi mới của dữ liệu). Khi tính toán độ trễ, tôi quyết định không lấy thời gian pipeline chạy (`run_timestamp`) để so sánh, mà so sánh trực tiếp giá trị `latest_exported_at` (thời điểm trích xuất từ database của hệ thống gốc) với chuẩn SLA 24 giờ. Quyết định này nhằm phản ánh đúng thực trạng: Cho dù ETL pipeline có chạy thành công 100 lần một ngày, nhưng nếu file CSV nguồn không được cập nhật từ hôm qua, thì hệ thống Knowledge Base vẫn đang chứa dữ liệu cũ và phải báo lỗi `freshness_sla_exceeded`.

---

## 3. Một lỗi hoặc anomaly đã xử lý

**Triệu chứng:** Pipeline báo `freshness_check=FAIL` liên tục ở cuối quá trình chạy, mặc dù dữ liệu đã được làm sạch và đưa vào ChromaDB thành công.
**Chẩn đoán:** Metric in ra `age_hours: 120.902, sla_hours: 24.0, reason: freshness_sla_exceeded`.
**Cách xử lý:** Tôi xác định đây không phải là lỗi code, mà là lỗi của tập dữ liệu mẫu. Tập CSV chứa bản ghi được tạo tĩnh vào ngày "2026-04-10", trong khi hệ thống chạy vào "2026-04-15" (cách nhau 5 ngày). Tôi đã ghi tài liệu vào `runbook.md`, giải thích đây là hành vi hệ thống bắt lỗi chuẩn xác và hướng dẫn Data Owner cách xử lý trên hệ thống thật thay vì tắt cảnh báo.

---

## 4. Bằng chứng trước / sau

Bằng chứng lớn nhất cho tầm quan trọng của hệ thống Observability mà nhóm xây dựng thể hiện ở sự biến đổi của metric `hits_forbidden` trong file eval.
**Câu truy vấn:** `q_refund_window`
**Trước (Run ID inject-bad):** CSV ghi nhận `hits_forbidden=yes` (cả dữ liệu rác và dữ liệu sạch lẫn lộn trong Vector DB).
**Sau (Run ID clean):** CSV ghi nhận `hits_forbidden=no` (DB đã sạch bóng dữ liệu cũ). 

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ viết một script tích hợp Webhook để tự động bắn thông báo lỗi (Alerting) về kênh Slack/Teams của nhóm Data mỗi khi biến `status` trong hàm `freshness_check` trả về giá trị `FAIL` hoặc pipeline bị `HALT`.