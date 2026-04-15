# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Trần Đặng Quang Huy  
**Vai trò:** Retrieval Eval / Sprint 3 Evidence  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào?

**File / module:**

- `etl_pipeline.py` (`--no-refund-fix`, `--skip-validate`)
- `eval_retrieval.py`
- `artifacts/logs/run_inject-bad.log`
- `artifacts/eval/after_inject_bad.csv`

**Kết nối với thành viên khác:**

Tôi phụ trách phần chứng minh trước/sau ở Sprint 3. Mục tiêu là tạo một case đủ rõ để mọi người thấy rằng chỉ cần tắt refund fix thì retrieval đã bị dính context stale. Phần này nối cleaning với monitoring: cùng một raw dataset, cùng một collection, nhưng chỉ khác cờ pipeline là kết quả trả lời có thể đổi từ sạch sang bẩn. Đây là bằng chứng thực tế cho data observability.

**Bằng chứng (commit / comment trong code):**

`run_inject-bad.log` có `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`; `after_inject_bad.csv` có `q_refund_window ... hits_forbidden=yes`.

---

## 2. Một quyết định kỹ thuật

Tôi chủ động để `refund_no_stale_14d_window` là `halt`, nhưng khi demo inject thì lại dùng `--skip-validate`. Nghe có vẻ ngược đời, nhưng chính điều đó mới chứng minh được hai tầng khác nhau: quality gate phát hiện lỗi thật, còn người vận hành vẫn có thể bỏ qua cảnh báo nếu cố tình. Lab cần nhìn thấy hậu quả của quyết định đó trên retrieval, không chỉ nhìn một dòng log.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Khi chạy `inject-bad`, triệu chứng rõ nhất là câu `q_refund_window` vẫn tìm đúng doc `policy_refund_v4` nhưng preview trả về lại chứa “14 ngày làm việc” và `hits_forbidden=yes`. Metric phát hiện lỗi là dòng `expectation[refund_no_stale_14d_window] FAIL` trong log. Tôi giữ nguyên artifact fail này để làm bằng chứng rằng context stale thực sự đi vào retrieval nếu bỏ fix.

---

## 4. Bằng chứng trước / sau

`before_after_eval_sprint2.csv`: `q_refund_window ... hits_forbidden=no`  
`after_inject_bad.csv`: `q_refund_window ... hits_forbidden=yes`  
Sự khác biệt xảy ra chỉ vì one-line decision ở pipeline, nhưng ảnh hưởng lên người dùng cuối thì rất lớn.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ thêm một cột `scenario` vào file eval để clean và inject nằm cùng một bảng, giúp đọc nhanh hơn khi trình bày với giảng viên. Tôi cũng muốn thêm một test nhỏ để tự động check `hits_forbidden` cho câu refund.
