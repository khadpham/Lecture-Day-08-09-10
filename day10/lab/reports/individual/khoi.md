# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** 2A202600276 - Phan Anh Khôi  
**Vai trò:** Quality / Expectation Owner  
**Ngày nộp:** 15/04/2026  

---

## 1. Tôi phụ trách phần nào?

**File / module:**
Nhiệm vụ của tôi là thiết lập ranh giới kiểm định chất lượng (Validation Gate). Tôi phụ trách file `quality/expectations.py`, viết và quản lý hàm `run_expectations` để rà soát dữ liệu đã qua bước làm sạch. Nếu dữ liệu vi phạm SLA nghiêm trọng, hàm của tôi sẽ phát tín hiệu `HALT` để báo cho file gốc dừng toàn bộ pipeline.

**Kết nối với thành viên khác:**
Bộ luật của tôi hoạt động như một giám khảo đối với kết quả đầu ra của Hiếu (Cleaning). Nếu luật của Hiếu có sai sót (ví dụ chưa vá lỗi 14 ngày), bộ Expectation của tôi sẽ ngăn chặn không cho Đan Kha (Embed) đưa dữ liệu bẩn vào DB.

**Bằng chứng (commit / comment trong code):**
Tôi đã viết 2 luật Expectation mới: `expect_iso_dates` sử dụng Regex `r"^\d{4}-\d{2}-\d{2}$"` và `expect_no_legacy_docs`.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật mang tính chiến lược của tôi là phân ranh giới rõ ràng giữa cảnh báo `WARN` và dừng hệ thống `HALT`. Khi viết luật kiểm tra các tài liệu cũ (`expect_no_legacy_docs`), tôi phát hiện một số chunk có `doc_id` chứa từ khóa "legacy". Mặc dù đây là nội dung không tối ưu, nhưng cấu trúc văn bản không sai. Do đó, tôi gán nó mức độ `WARN` — in cảnh báo ra log để báo cho admin nhưng vẫn cho pipeline chạy tiếp. Ngược lại, với lỗi định dạng ngày không chuẩn ISO, tôi chọn `HALT` vì nó sẽ làm sập tính năng RAG filter bằng thời gian ở hạ nguồn. Quyết định này giúp pipeline vừa nghiêm ngặt vừa linh hoạt.

---

## 3. Một lỗi hoặc anomaly đã xử lý

**Triệu chứng & Phát hiện:** Trong Sprint 3, nhóm cố tình tắt hàm vá lỗi hoàn tiền (chạy với cờ `--no-refund-fix`). Lúc này, chính sách 14 ngày lỗi thời vẫn lọt qua bước làm sạch. 
**Metric phát hiện:** Hàm `expect_no_14_day_refund` của tôi đã phát hiện và quét chuỗi "14 ngày làm việc". Nó lập tức kích hoạt lỗi và đẩy trạng thái thành `HALT`.
**Cách xử lý:** Trong file log `inject-bad`, hệ thống ghi nhận `expectation[expect_no_14_day_refund] FAIL (HALT) :: Failed: Found 1 chunks still containing stale 14-day policy`. Đây là sự cố bắt lỗi có chủ đích, chứng minh hàng rào phòng thủ của hệ thống hoạt động hoàn hảo.

---

## 4. Bằng chứng trước / sau

Bằng chứng rõ nhất là sự thay đổi trạng thái của hệ thống Expectation khi hệ thống được chạy với các cờ (flags) khác nhau.
**Run ID (Inject Bad):** `expectation[expect_no_14_day_refund] FAIL (HALT)`
**Run ID (Clean):** `expectation[expect_no_14_day_refund] OK (HALT) :: Passed`
Việc chỉ số này chuyển từ FAIL sang OK chứng tỏ hệ thống giám sát chất lượng có độ nhạy rất cao với dữ liệu bẩn.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, thay vì tự viết các câu lệnh `if/else` để kiểm tra Regex thủ công, tôi sẽ tích hợp thư viện `Pydantic` để validate schema (kiểu dữ liệu) hoặc sử dụng thư viện `Great Expectations` chuẩn công nghiệp để có báo cáo HTML tự động.