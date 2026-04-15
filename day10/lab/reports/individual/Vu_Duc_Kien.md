# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Vũ Đức Kiên  
**Vai trò:** Cleaning / Quality Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**


## 1. Tôi phụ trách phần nào? (80–120 từ)

Tôi phụ trách mảng Cleaning & Quality trong pipeline Day 10, tập trung vào việc đảm bảo dữ liệu chỉ được publish sau khi qua chuẩn hóa và kiểm tra nhất quán. Các file tôi làm việc chính gồm `transform/cleaning_rules.py`, `quality/expectations.py`, cùng các artifact kiểm chứng như `artifacts/quarantine/*.csv` và `artifacts/logs/run_*.log`. Tôi phối hợp với thành viên Embed để bảo đảm dữ liệu cleaned có thể upsert idempotent vào Chroma, đồng thời phối hợp với Monitoring/Docs để diễn giải các chỉ báo như `freshness_check`, `quarantine_records`, `hits_forbidden` vào report và runbook.

**File / module:**

- `transform/cleaning_rules.py`
- `quality/expectations.py`
- `artifacts/quarantine/quarantine_sprint2-inject-fix.csv`
- `artifacts/logs/run_sprint2-base.log`, `artifacts/logs/run_sprint2-inject-fix.log`

**Kết nối với thành viên khác:**

Tôi cung cấp đầu ra cleaned/quarantine đã gắn `reason` để nhóm Embed đánh giá ảnh hưởng lên retrieval, và cung cấp số liệu định lượng cho nhóm Monitoring hoàn thiện phần observability trong báo cáo nhóm.

**Bằng chứng (commit / comment trong code):**

Bằng chứng chính nằm ở log chạy thực tế có expectation mới: `expectation[exported_at_iso_datetime]` và `expectation[no_duplicate_doc_effective_text]`, cùng thay đổi số liệu `quarantine_records` giữa run base và run inject.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Quyết định kỹ thuật quan trọng của tôi là đặt kiểm soát chất lượng theo hai tầng: (1) rule clean/quarantine ở mức record và (2) expectation ở mức tập cleaned. Cụ thể, tôi bổ sung ba rule clean mới: quarantine khi `exported_at` thiếu/sai format, khi `chunk_text` chứa control chars, và khi `chunk_text` dài bất thường. Đồng thời, tôi thêm hai expectation `halt`: `exported_at_iso_datetime` và `no_duplicate_doc_effective_text`. Cách thiết kế này giúp dữ liệu lỗi bị chặn sớm ở quarantine, còn expectation đóng vai trò “lưới an toàn cuối” trước publish. Tôi chọn `halt` cho hai expectation mới vì đây là lỗi ảnh hưởng trực tiếp tính truy vết và tính ổn định retrieval. Thực tế ở run `sprint2-base`, cả hai expectation đều `OK`, cho thấy pipeline sạch trong điều kiện bình thường.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

Anomaly đáng chú ý tôi gặp là run inject ban đầu bị lỗi ở bước ghi manifest khi dùng đường dẫn raw tương đối: `--raw data\raw\policy_export_inject.csv`. Triệu chứng là pipeline đã chạy qua expectation, embed xong (`embed_upsert count=8`) nhưng dừng bằng `ValueError` tại `raw_path.relative_to(ROOT)`. Tôi xác định đây là lỗi xử lý path (relative vs absolute), không phải lỗi chất lượng dữ liệu. Cách xử lý vận hành là chạy lại với đường dẫn tuyệt đối `--raw D:/Lecture-Day-08-09-10/day10/lab/data/raw/policy_export_inject.csv`, kết quả run `sprint2-inject-fix` ghi manifest thành công và hoàn tất pipeline. Việc này giúp tôi rút kinh nghiệm rằng ngoài rule dữ liệu, tính ổn định đường dẫn và tính nhất quán artifact cũng là một phần của data observability.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Tôi sử dụng hai loại bằng chứng: log pipeline và eval retrieval.  
Về log, từ `sprint2-base` sang `sprint2-inject-fix`, số liệu thay đổi `raw_records: 10 -> 13`, `quarantine_records: 4 -> 5`, cho thấy rule mới có tác động đo được.  
Về retrieval, trong `artifacts/eval/after_inject_bad.csv`, câu `q_refund_window` có `contains_expected=yes` nhưng `hits_forbidden=yes`, thể hiện context top-k vẫn nhiễm chunk stale. Sau khi chạy lại chuẩn, `artifacts/eval/after_fix.csv` cho cùng câu có `hits_forbidden=no`. Ngoài ra, `q_leave_version` giữ `top1_doc_expected=yes`, chứng minh dữ liệu version hiện hành được ưu tiên đúng.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ bổ sung bộ test tự động cho cleaning/expectation theo từng loại inject (schema drift, malformed datetime, stale policy marker) và tích hợp một lệnh kiểm tra hồi quy trước publish. Mục tiêu là chuyển từ kiểm chứng thủ công bằng log sang cơ chế kiểm thử lặp lại được, giảm rủi ro phát sinh lỗi thầm lặng ở các lần rerun sau.

