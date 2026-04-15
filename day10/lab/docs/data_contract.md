# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `data/raw/policy_export_dirty.csv` | File CSV export theo lô (batch) | BOM/header bẩn, thiếu `effective_date`, `doc_id` ngoài allowlist | `raw_records`, `quarantine_records`, `%quarantine` trong `artifacts/logs/run_*.log` |
| `data/docs/policy_refund_v4.txt` (canonical policy) | Mapping theo `doc_id=policy_refund_v4` trong clean/embed | Drift version (14 ngày vs 7 ngày), marker migration cũ còn sót | expectation `refund_no_stale_14d_window`, `refund_no_stale_migration_marker` |
| `data/docs/hr_leave_policy.txt` (canonical HR) | Mapping theo `doc_id=hr_leave_policy` | Conflict version 2025 (10 ngày phép) lẫn với 2026 (12 ngày phép) | quarantine reason `stale_hr_policy_effective_date`, expectation `hr_leave_no_stale_10d_annual` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | ID ổn định từ `doc_id + seq + hash`, dùng làm khóa upsert Chroma |
| doc_id | string | Có | Phải thuộc allowlist trong `cleaning_rules.ALLOWED_DOC_IDS` |
| chunk_text | string | Có | Đã normalize spacing, scrub note migration refund; tối thiểu 8 ký tự |
| effective_date | date | Có | Chuẩn `YYYY-MM-DD` sau clean |
| exported_at | datetime | Có | Parseable ISO datetime, chuẩn hoá UTC (`...Z`) |

---

## 3. Quy tắc quarantine vs drop

> Record bị flag đi đâu? Ai approve merge lại?

- Mọi record vi phạm rule ingest/clean được ghi vào `artifacts/quarantine/quarantine_<run_id>.csv` kèm `reason`.
- `unknown_doc_id`, `missing_effective_date`, `invalid_effective_date_format`, `missing_exported_at`, `invalid_exported_at_format`, `stale_hr_policy_effective_date`, `duplicate_chunk_text_post_clean` → **quarantine** (không publish).
- Không có cơ chế auto-merge từ quarantine. Quy trình xử lý:
	1. Data owner kiểm tra bản ghi trong file quarantine.
	2. Sửa dữ liệu nguồn hoặc cập nhật rule có kiểm soát.
	3. Rerun pipeline với `run_id` mới và kiểm lại expectation.

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?

- Canonical cho refund: `data/docs/policy_refund_v4.txt` (cửa sổ hoàn tiền hợp lệ: **7 ngày làm việc**).
- Canonical cho HR leave: `data/docs/hr_leave_policy.txt` với cutoff hiệu lực `>= 2026-01-01`.
- Trên pipeline publish, vector index phản ánh snapshot cleaned của `run_id` hiện tại (upsert theo `chunk_id` + prune id không còn trong cleaned).
