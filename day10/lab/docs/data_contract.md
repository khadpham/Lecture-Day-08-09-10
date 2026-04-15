# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| policy_export | CSV export định kỳ từ policy service (`--raw ...csv`) | duplicate row, date sai format (`01/02/2026`), missing `effective_date`, `exported_at` sai format | `quarantine_records`, `invalid_exported_at_rows`, `%invalid_date`, `%duplicate_chunk_id` |
| it_helpdesk_export | CSV export từ IT helpdesk knowledge | stale chunk refund 14 ngày, text quá dài/binary, `doc_id` ngoài allowlist | `hits_forbidden`, `expectation_fail_count`, `unknown_doc_id_count`, `chunk_text_too_long_count` |
---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | Sinh ổn định sau clean từ `doc_id + chunk_text + seq`; dùng làm idempotent key cho embed |
| doc_id | string | Có | Nằm trong allowlist (`policy_refund_v4`, `sla_p1_2026`, `it_helpdesk_faq`, `hr_leave_policy`) |
| chunk_text | string | Có | Đã normalize và qua rule lọc (không rỗng, không control chars, không quá dài bất thường) |
| effective_date | date | Có | Chuẩn `YYYY-MM-DD`; parse từ raw hoặc quarantine nếu sai format |
| exported_at | datetime | Có | Chuẩn ISO datetime; dùng cho freshness check qua manifest |

---

## 3. Quy tắc quarantine vs drop

> Record bị flag đi đâu? Ai approve merge lại?

Record vi phạm được đưa vào `artifacts/quarantine/quarantine_<run_id>.csv` kèm cột `reason` để trace. Nhóm không drop "im lặng"; mọi record lỗi đều có log và evidence. Quy trình approve merge lại: Cleaning/Quality Owner rà `reason`, đối chiếu contract và nguồn canonical, sau đó chỉnh rule hoặc fix nguồn rồi rerun. Các reason chính hiện tại: `unknown_doc_id`, `missing_effective_date`, `invalid_effective_date_format`, `stale_hr_policy_effective_date`, `missing_chunk_text`, `duplicate_chunk_text`, `missing_exported_at`, `invalid_exported_at_format`, `chunk_text_contains_control_chars`, `chunk_text_too_long`.

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?

Source of truth cho policy refund là `policy_refund_v4` (canonical path: `data/docs/policy_refund_v4.txt` trong contract YAML). Rule clean cưỡng bức sửa marker stale `14 ngày làm việc` về `7 ngày làm việc` khi `--no-refund-fix` không bật. Với HR leave policy, cutoff `effective_date >= 2026-01-01` được dùng để loại bản cũ (10 ngày phép) và giữ bản hiện hành 2026 (12 ngày phép).
