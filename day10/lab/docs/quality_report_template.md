# Quality report — Lab Day 10 (nhóm)

**run_id:** 2026-04-15T08-53Z  
**Ngày:** 15/04/2026

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (Inject Bad) | Sau (Clean Run) | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 10 | 10 | Tổng số bản ghi thô từ CSV export. |
| cleaned_records | 7 | 7 | Số bản ghi vượt qua ranh giới Validate. |
| quarantine_records | 3 | 3 | Số bản ghi bị cách ly (Rỗng, Trùng, HR 2025). |
| Expectation halt? | YES (FAIL) | NO (OK) | Bản chạy lỗi vi phạm chính sách 14 ngày. |

---

## 2. Before / after retrieval (bắt buộc)

Dữ liệu được đối chiếu giữa `artifacts/eval/after_inject_bad.csv` và `artifacts/eval/before_after_eval.csv`.

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Trước (Sau khi Inject Bad):** `q_refund_window,...,yes,yes,,3`  
> **Giải thích:** Hệ thống tìm thấy thông tin 7 ngày (`contains_expected=yes`) nhưng context vẫn chứa cả thông tin 14 ngày cũ (`hits_forbidden=yes`), gây nhiễu cho Agent.

**Sau (Sau khi chạy Clean):** `q_refund_window,...,yes,no,,3`  
> **Giải thích:** Nhờ logic Prune trong ranh giới Embed, vector cũ đã bị xóa bỏ hoàn toàn. Context hiện tại sạch 100% (`hits_forbidden=no`).

**Merit (khuyến nghị):** versioning HR — `q_leave_version`  
**Trước:** Hệ thống truy xuất lẫn lộn giữa chính sách 10 ngày (2025) và 12 ngày (2026) do không có ranh giới cách ly năm.  
**Sau:** Chỉ truy xuất chính xác phiên bản 2026 (`top1_doc_matches=true`). Dữ liệu 2025 đã bị đẩy vào `quarantine` thành công.

---

## 3. Freshness & monitor

* **Kết quả:** FAIL  
* **Chi tiết:** `age_hours: 120.902`, `sla_hours: 24.0`.  
* **Giải thích SLA:** Nhóm chọn SLA 24 giờ để đảm bảo các chính sách nhân sự và CS luôn được cập nhật hàng ngày. Kết quả FAIL là hợp lý do tệp dữ liệu mẫu được xuất từ ngày 10/04/2026 (tĩnh), trong khi pipeline chạy vào ngày 15/04/2026.

---

## 4. Corruption inject (Sprint 3)

Nhóm đã thực hiện cố ý làm hỏng dữ liệu bằng lệnh:  
`python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`  

* **Cách làm hỏng:** Sử dụng cờ `--no-refund-fix` để giữ nguyên lỗi chính sách 14 ngày và dùng `--skip-validate` để ép pipeline không dừng lại dù vi phạm Expectation HALT.  
* **Cách phát hiện:** Hệ thống giám sát đã bắt được lỗi ngay lập tức qua log: `expectation[expect_no_14_day_refund] FAIL (HALT)`. Việc phát hiện này chứng minh các ranh giới kiểm định hoạt động cực kỳ hiệu quả.

---

## 5. Hạn chế & việc chưa làm

- Hiện tại hệ thống mới chỉ kiểm tra logic trên 10 dòng dữ liệu mẫu, cần stress-test với bộ dữ liệu lớn hơn (>1000 chunks) để đánh giá hiệu năng của hàm Prune ID.
- Chưa tích hợp thông báo đẩy (push notification) qua Telegram/Slack khi Freshness SLA bị vi phạm.