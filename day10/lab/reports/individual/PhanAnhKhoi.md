# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Phan Anh Khôi  
**Vai trò:** Embed & Idempotency Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào?

**File / module:**

- `etl_pipeline.py` phần `cmd_embed_internal`
- `artifacts/logs/run_sprint2-final-repeat-2.log`
- `artifacts/logs/run_inject-bad.log`
- `artifacts/eval/before_after_eval_sprint2.csv`

**Kết nối với thành viên khác:**

Tôi phụ trách lớp embed và tính idempotency của Chroma collection. Sau khi cleaning xuất ra cleaned CSV, nhiệm vụ của tôi là đảm bảo `chunk_id` trở thành khóa ổn định để rerun không sinh duplicate vector. Tôi cũng phải prune các ID không còn trong snapshot hiện tại để tránh “vector mồi cũ”. Điều này là cực kỳ quan trọng vì Day 09 và Day 10 đều phụ thuộc vào retrieval; chỉ một chunk stale còn sót cũng đủ làm agent đọc nhầm version.

**Bằng chứng (commit / comment trong code):**

Snippet kiểm tra cho thấy `order_independent_id_set: True`. Khi rerun clean snapshot sau khi collection đã ổn định, log không còn thêm vector mới ngoài `embed_upsert count=6`.

---

## 2. Một quyết định kỹ thuật

Tôi chọn `upsert + prune` thay vì `add` vì lab này cần chứng minh publish boundary, không chỉ ingest một lần. `upsert` giúp rerun cùng dữ liệu không nhân bản vector, còn prune giúp xóa ID lạc hậu khi snapshot thay đổi. Cách này hợp với Chroma persistent collection và làm cho pipeline đúng nghĩa idempotent.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Lỗi trước đây là `chunk_id` phụ thuộc vào `seq` theo thứ tự dòng, nên chỉ cần reorder input là ID thay đổi. Sau fix, ID được hash từ `doc_id + normalized chunk_text`, vì vậy rerun với cùng nội dung không còn phụ thuộc dòng đứng trước hay sau. Một lần chạy clean sau inject vẫn có thể prune 1 stale vector cũ, nhưng khi clean snapshot ổn định rồi, rerun tiếp theo giữ nguyên ID và không còn phình collection.

---

## 4. Bằng chứng trước / sau

`run_sprint2-final-repeat-2.log`: `embed_upsert count=6`  
`before_after_eval_sprint2.csv`: `q_leave_version ... top1_doc_expected=yes`  
Hai bằng chứng này cho thấy embed vừa idempotent vừa giữ đúng snapshot sạch để retrieval đọc chính xác version 2026.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ viết một bài kiểm tra tự động đếm số ID trong collection sau rerun để chứng minh bằng số liệu rằng collection không phình ra. Tôi cũng muốn thêm một smoke test cho prune boundary để phát hiện sớm vector cũ còn sót.
