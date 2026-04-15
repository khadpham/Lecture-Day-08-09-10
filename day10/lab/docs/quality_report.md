# Quality report — Lab Day 10 (nhóm)

**run_id:** sprint2-final-repeat-2  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước | Sau | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 10 | 10 | đọc từ `data/raw/policy_export_dirty.csv` |
| cleaned_records | 6 | 6 | sau clean còn 6 dòng publish |
| quarantine_records | 4 | 4 | 4 dòng bị chặn vì stale/unknown/missing |
| Expectation halt? | pass trên clean / fail trên inject | clean: no halt, inject: `refund_no_stale_14d_window` fail | compare `sprint2-final-repeat-2` vs `inject-bad` |

---

## 2. Before / after retrieval (bắt buộc)

> Dẫn tới `artifacts/eval/before_after_eval_sprint2.csv`.

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Trước:** inject snapshot (`artifacts/eval/after_inject_bad.csv`) trả về `policy_refund_v4` nhưng preview vẫn chứa `14 ngày làm việc`, đồng thời `hits_forbidden=yes`.  
**Sau:** clean snapshot (`artifacts/eval/before_after_eval_sprint2.csv`) trả về `policy_refund_v4` với `7 ngày làm việc`, `hits_forbidden=no`.

**Merit (khuyến nghị):** versioning HR — `q_leave_version`  
**Trước:** có record HR 2025 trong raw, nhưng bị quarantine.  
**Sau:** cả clean và inject đều `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`.

---

## 3. Freshness & monitor

Kết quả trên `artifacts/manifests/manifest_inject-bad.json` là `FAIL` vì `latest_exported_at=2026-04-10T08:00:00Z` và run ngày 2026-04-15, vượt SLA 24h. Đây là fail hợp lý cho dữ liệu mẫu: manifest chứng minh pipeline đang đo đúng boundary publish, chứ không phải hệ thống hỏng. Clean run `manifest_sprint2-final-repeat-2.json` cũng fail cùng lý do — đó là dữ liệu mẫu cũ, không phải lỗi code.

---

## 4. Corruption inject (Sprint 3)

Đã chạy `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`. Hành vi inject là giữ lại stale refund 14 ngày trong publish snapshot, khiến expectation `refund_no_stale_14d_window` fail có kiểm soát và retrieval `q_refund_window` hit forbidden. Sau đó clean rerun `sprint2-final-repeat-2` xác nhận snapshot sạch quay về đúng trạng thái.

---

## 5. Hạn chế & việc chưa làm

- Chưa có grading JSONL vì bộ câu grading chưa được mở trong workspace.
- Nếu muốn PASS freshness, cần refresh snapshot raw thay vì dùng dữ liệu mẫu cũ.