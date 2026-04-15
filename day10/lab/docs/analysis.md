Chào bạn, dưới đây là báo cáo phân tích, debugging và đánh giá Lab Day 10 theo góc nhìn của một chuyên gia Data/Analyst đối chiếu với SCORING.md.

1. Mục đích và Input/Output của các files/công đoạn chính
Lab Day 10 là hệ thống Data Pipeline end-to-end có nhiệm vụ làm sạch, kiểm định và tích hợp dữ liệu vào Vector DB.

etl_pipeline.py (ETL Entrypoint)

Mục đích: Là file chính điều phối dòng chảy dữ liệu. Nhận cờ chạy pipeline, kích hoạt làm sạch, phân loại, chạy expectation tests, lưu vector DB và ghi metrics vào manifest.
Input: File CSV rác (data/raw/policy_export_dirty.csv).
Output: Xuất log run, ghi dữ liệu vào Chroma DB, tạo manifest summary (artifacts/manifests/), lưu CSV sạch và CSV cách ly (artifacts/cleaned/ & artifacts/quarantine/).
transform/cleaning_rules.py (Data Cleaning & Normalization)

Mục đích: Map data raw sang dạng chuẩn bằng các hàm chuẩn hoá, đồng thời phân tích những dòng vi phạm (quarantine). Nhiệm vụ của sinh viên là thêm vào ≥3 rule mới so với baseline.
Input: List các object JSON/Dict dạng raw parsing.
Output: Trả về bộ tuple (cleaned_rows, quarantine_rows).
quality/expectations.py (Data Quality Gate & Observability)

Mục đích: Xây dựng Data Contract chặn luồng. Sinh viên phải có thêm ≥2 expectations mới kèm phân loại warn / halt.
Input: Dữ liệu sau khi làm sạch (cleaned_rows).
Output: Trả về kết quả đánh giá (test passed / failed) và biến rào chắn should_halt giúp quyết định dừng hay ghi DB.
eval_retrieval.py

Mục đích: Đánh giá hiệu suất truy xuất của Chroma DB, chứng minh lỗi sai lệch nếu không fix phiên bản (trả về đúng doc nhưng sai context version đối với hệ thống LLM). Trả ra file CSV chứa benchmark (artifacts/eval/before_after_eval.csv).
2. Những điểm sai, vi phạm, hoặc chưa tối ưu đã phát hiện
Sau khi phân tích đối chiếu với SCORING.md, có thể chỉ ra các bugs và design flaws rất quan trọng trong code của sinh viên/nhóm:

🔴 Lỗi nghiêm trọng: Tấn công trực tiếp vào Data Idempotency (seq global)

Chi tiết: Bạn dùng hàm sinh vector ID rẩt mong manh. Trong transform/cleaning_rules.py, hàm clean_rows sử dụng biến đếm seq = 0 tăng dần toàn cục làm input cho việc tạo chunk_id (_stable_chunk_id(doc_id, fixed_text, seq)).
Hậu quả: Nếu thứ tự ở file source bị đảo dòng ngẫu nhiên, hoặc có vài dòng giữa file bỗng bị cách ly ở lần chạy thứ 2, toàn bộ lượng seq phía dưới bị lệch 
→
→ sinh ra loạt chunk_id mới mẻ tinh tươm. Vector DB sẽ lưu duplicates cực nhiều thay vì "upsert" (overwrite củ) như đúng thiết kế idempotent, phình tài nguyên không lặp lại được.
Sửa lỗi: Nên đếm seq cục bộ cho riêng từng doc_id, hoặc bỏ seq và tạo hash trực tiếp từ f"{doc_id}_{chunk_text}" nếu có deduplicate.
🟡 Bugs logic Deduplicate: Ghi đè chéo các Policy (Global deduplicate)

Chi tiết: Trong check trùng (rule 7), code dùng set global seen_text để deduplicate key = _norm_text(fixed_text) ở mọi document.
Hậu quả: Nếu 2 loại policy khác biệt hoàn toàn, nhưng chúng tình cờ có nội dung trùng lặp một chunk (chẳng hạn như văn bản pháp lý chung chung "Quy định này có hiệu lực từ ngày ban hành."), thì policy đi sau sẽ bị push nhầm thẳng vào quarantine do lỗi "duplicate_chunk_text_post_clean". Deduplicate phải được scope trên cấp doc_id.
🟡 Lỗi thiết kế Hệ Giám Sát (Redundant Expectations)

Chi tiết: Bạn thêm rule E7 (exported_at_parseable_iso_datetime) để bắt định dạng ngày trong lúc chạy run_expectations.
Hậu quả: Bản chất ngay ở class làm sạch, nếu parse error ở _normalize_exported_at đã bị hàm clean_rows tống đi sang quarantine.csv rồi, thì dòng lỗi đó KHÔNG BAO GIỜ đến được mảng cleaned_rows. E7 của bạn đang kiểm tra lại cái chắc chắn đúng (luôn Passed), vô nghĩa trong context runtime của kiến trúc này do trùng coverage. E7 đáng lẽ nên chạy trên raw, hoặc nếu chạy trên cleaned, nó đóng vai trò check integration bù giờ.
🔴 Trừ điểm nặng theo SCORING (Lỗi Documentation của Toàn Nhóm)

Chi tiết: File reports/group_report.md trống toàn bộ nội dung kịch bản (___). Các phần "Tóm tắt luồng", "metric_impact", "Kịch bản inject" hoàn toàn chép trắng template, không nộp!
Đối chiếu rubric: Giảng viên có note là "Nhóm không điền bảng metric_impact trong reports/group_report.md ... dễ bị trừ khi tranh chấp có làm thật hay không". Việc group report gần như trống có thể khiến nhóm nhận 0 ở mục báo cáo nhóm (mất trắng 15/60 điểm của phần Team), mất đi bằng chứng bảo vệ mình. (Huy có document file cá nhân rất tốt, nhưng gánh vác không nổi thiếu report tổng nhóm).

3. Trạng thái sau khắc phục (cập nhật 2026-04-15)

- `chunk_id` đã được sửa sang hash ổn định theo `doc_id + normalized chunk_text`, không còn phụ thuộc `seq`/thứ tự dòng.
- Dedupe đã scope theo `(doc_id, chunk_text)`, không còn quarantine chéo giữa các document khác nhau.
- Expectation `exported_at_parseable_iso_datetime` đã được bỏ khỏi lớp quality để tránh trùng coverage với bước clean; các gate còn lại vẫn giữ `halt`/`warn` rõ ràng.
- `reports/group_report.md` và 5 báo cáo cá nhân đã được điền đầy đủ, có run_id và bằng chứng before/after.