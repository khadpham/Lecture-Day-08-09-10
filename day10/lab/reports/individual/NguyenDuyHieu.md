# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Duy Hiếu  
**Vai trò:** Ingestion / Raw Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào?

**File / module:**

- `etl_pipeline.py` phần ingest và ghi log/run_id
- `transform/cleaning_rules.py` phần `load_raw_csv`
- `artifacts/logs/run_sprint1.log`

**Kết nối với thành viên khác:**

Tôi phụ trách đầu vào raw và phần lineage đầu tiên của pipeline. Việc của tôi là đảm bảo CSV bẩn vẫn đọc được ổn định, header được sanitize, và `run_id` luôn nhất quán giữa log, cleaned/quarantine CSV và manifest. Nhờ ingest sạch, phần cleaning và quality phía sau mới có thể tách đúng record lỗi thay vì đổ lỗi nhầm sang embed hay monitoring.

**Bằng chứng (commit / comment trong code):**

`run_sprint1.log` ghi `run_id=sprint1`, `raw_records=10`, `cleaned_records=6`, `quarantine_records=4`.

---

## 2. Một quyết định kỹ thuật

Tôi chọn làm ingest thật “mỏng” nhưng không bao giờ đọc raw theo kiểu thả nổi. Mọi key đều phải được sanitize ngay khi `DictReader` đọc vào, vì chỉ cần BOM hoặc control char lọt qua là downstream sẽ nhìn thấy field sai tên. Ingest không nên thông minh hơn cleaning; nó chỉ cần nhất quán, ghi log rõ và tạo artifact ổn định. Cách này giúp các bước sau phân biệt được lỗi do input, lỗi do clean, và lỗi do embed.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly lớn nhất ở tầng ingest là raw file 10 dòng nhưng chỉ 6 dòng được publish. `run_sprint1.log` cho thấy rõ `quarantine_records=4`. Bốn record bị loại vì những reason thật sự có ý nghĩa: `unknown_doc_id`, `missing_effective_date`, `stale_hr_policy_effective_date`, và `duplicate_chunk_text_post_clean`. Tôi không cố giữ tất cả dòng lại để làm số đẹp, vì quarantine là tín hiệu quan trọng của data observability.

---

## 4. Bằng chứng trước / sau

`run_sprint1.log`: `raw_records=10`, `quarantine_records=4`  
`quarantine_sprint1.csv`: có `reason=unknown_doc_id` và `reason=missing_effective_date`  
Hai dòng này chứng minh ingest không nuốt raw bừa bãi mà tách đúng các record lỗi ra khỏi đường publish.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ viết thêm một test nhỏ cho `load_raw_csv` để bảo đảm header có BOM/control char vẫn được normalize thành key chuẩn. Tôi cũng muốn thêm check cho `run_id` để toàn bộ artifact trong cùng một run luôn mang chung prefix, giúp debugging nhanh hơn.
