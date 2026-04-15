# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Vũ Đức Kiên  
**Vai trò:** Monitoring / Docs Owner  
**Ngày nộp:** 2026-04-15  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào?

**File / module:**

- `docs/pipeline_architecture.md`
- `docs/runbook.md`
- `docs/quality_report.md`
- `monitoring/freshness_check.py`

**Kết nối với thành viên khác:**

Tôi phụ trách phần monitoring và tài liệu vận hành. Nhiệm vụ của tôi là biến các log, manifest và eval CSV thành một câu chuyện rõ ràng: freshness là gì, vì sao FAIL trên data mẫu vẫn là đúng, và khi nào cần rerun pipeline. Không có phần này, nhóm có thể chạy được code nhưng không giải thích được behavior của hệ thống trước giảng viên.

**Bằng chứng (commit / comment trong code):**

`docs/pipeline_architecture.md`, `docs/runbook.md`, `docs/quality_report.md` đều được điền; `manifest_sprint2-final-repeat-2.json` và `manifest_inject-bad.json` đều có freshness fail đúng SLA.

---

## 2. Một quyết định kỹ thuật

Tôi chọn đo freshness ở publish boundary thay vì chỉ nhìn raw ingest, vì data sạch về schema vẫn có thể cũ về thời gian. Nếu không tách hai khái niệm này, nhóm rất dễ nhầm “clean” với “fresh”. Việc ghi SLA 24h trong manifest và runbook giúp mọi người hiểu ngay rằng FAIL ở đây không nhất thiết là bug, mà có thể là cảnh báo đúng do snapshot mẫu đã cũ.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly lớn nhất ở monitoring là freshness vẫn FAIL ở cả clean lẫn inject, với age khoảng 121 giờ > SLA 24h. Đây không phải lỗi code mà là đặc tính của dữ liệu mẫu. Tôi đã viết rõ vào runbook để tránh mọi người hiểu nhầm pipeline hỏng. Nói cách khác, monitoring phải giúp diễn giải tín hiệu, không chỉ in PASS/FAIL.

---

## 4. Bằng chứng trước / sau

`manifest_sprint2-final-repeat-2.json`: `freshness_check=FAIL`, `age_hours=121.136`  
`manifest_inject-bad.json`: `freshness_check=FAIL`, `age_hours=121.115`  
Hai manifest này đều fail theo cùng lý do: snapshot mẫu cũ hơn SLA, nhưng đó là đúng hành vi của monitor.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ thêm một bảng PASS/WARN/FAIL ngay trong runbook với ví dụ dòng log thực tế, để người mới vào nhóm chỉ cần đọc là hiểu cách diễn giải freshness và không panic khi thấy FAIL trên data mẫu.
