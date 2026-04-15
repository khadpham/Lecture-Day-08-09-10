# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Phạm Đan Kha  
**Vai trò:** Cleaning & Quality Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào?

**File / module:**

- `transform/cleaning_rules.py`
- `quality/expectations.py`
- `artifacts/quarantine/quarantine_sprint2-final-repeat-2.csv`
- `artifacts/logs/run_inject-bad.log`

**Kết nối với thành viên khác:**

Tôi phụ trách phần làm sạch và quality gate. Sau khi đọc phân tích lỗi trong `analysis.md`, tôi sửa hai vấn đề quan trọng: chunk_id không còn dựa vào `seq` theo thứ tự dòng, và dedupe không còn quét chéo giữa các `doc_id`. Nhờ vậy, cleaning trở nên ổn định hơn và không còn tạo false-positive hay id vỡ khi reorder input.

**Bằng chứng (commit / comment trong code):**

Python snippet kiểm tra cho thấy `order_independent_id_set: True` và `cross_doc_duplicate_quarantine_count: 0`.

---

## 2. Một quyết định kỹ thuật

Tôi giữ `halt` cho các expectation ảnh hưởng trực tiếp đến publish boundary: refund stale window, chunk_id unique, effective_date ISO. Mục tiêu là để pipeline dừng ngay khi dữ liệu có nguy cơ làm agent đọc sai version. Còn những rule quan sát chất lượng nhẹ hơn thì để `warn` để nhóm vẫn có tín hiệu observability mà không bị chặn toàn bộ luồng. Quyết định này giúp phân biệt rõ “data lỗi nghiêm trọng” và “data có dấu hiệu cần theo dõi”.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Khi chạy `inject-bad` với `--no-refund-fix`, expectation `refund_no_stale_14d_window` fail rõ ràng: `violations=1`. Đây là anomaly mình dùng để chứng minh quality gate thực sự có tác dụng, vì cùng một raw dataset nhưng chỉ cần bỏ fix refund là retrieval có thể dính context stale. Tôi không sửa bằng cách bỏ luôn check; thay vào đó, tôi để fail có kiểm soát và giữ log làm bằng chứng.

---

## 4. Bằng chứng trước / sau

`artifacts/eval/before_after_eval_sprint2.csv`: `q_refund_window ... hits_forbidden=no`  
`artifacts/eval/after_inject_bad.csv`: `q_refund_window ... hits_forbidden=yes`  
Sự khác biệt này xảy ra chỉ vì one-line decision ở pipeline, nhưng ảnh hưởng lên người dùng cuối thì rất lớn.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ viết một test regression cho `run_expectations` để kiểm tra riêng `chunk_id_unique` và các rule refund. Tôi cũng muốn thêm một fixture nhỏ để chứng minh cross-doc duplicate text không còn bị quarantine nhầm.
