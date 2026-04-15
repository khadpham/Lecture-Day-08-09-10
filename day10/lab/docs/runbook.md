# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

User/agent trả lời đúng câu hỏi nhưng vẫn chứa context stale, hoặc manifest báo freshness FAIL.

Ví dụ:
- Trả lời policy refund còn “14 ngày” thay vì “7 ngày”.
- Retrieval top-k vẫn chứa chunk HR 2025 thay vì 2026.
- `etl_pipeline.py run` dừng ở expectation halt nếu data đầu vào có lỗi parse / stale.

---

## Detection

Các tín hiệu chính:

- `freshness_check=FAIL` trong log/manifest.
- `expectation[...] FAIL` với severity `halt`.
- `hits_forbidden=yes` trong CSV eval retrieval.
- `quarantine_records` tăng bất thường so với run chuẩn.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` | Xác định `run_id`, `latest_exported_at`, `sla_hours` |
| 2 | Mở `artifacts/quarantine/*.csv` | Xem `reason` nào đang tăng: `unknown_doc_id`, `missing_effective_date`, `duplicate_chunk_text_post_clean` |
| 3 | Chạy `python eval_retrieval.py` | Xác định `contains_expected` / `hits_forbidden` / `top1_doc_expected` |

---

## Mitigation

1. Nếu fail do dữ liệu sạch còn stale: refresh raw snapshot hoặc tăng SLA có chủ đích (chỉ khi policy chấp nhận).
2. Nếu fail do rule/expectation: sửa raw data hoặc cập nhật cleaning rule có kiểm soát.
3. Rerun `python etl_pipeline.py run --run-id <new>` để publish snapshot mới.
4. Nếu cần demo có chủ đích, dùng `--skip-validate` **chỉ** cho inject Sprint 3.

---

## Prevention

Chốt 3 lớp guardrail:

- `cleaning_rules.py`: sanitize + allowlist + normalize date/timestamp.
- `expectations.py`: halt cho timestamp parseable, chunk_id unique, refund stale window.
- `manifest + freshness_check`: monitor publish boundary với SLA rõ ràng.

Owner nên review lại contract mỗi khi thêm nguồn mới hoặc đổi cutoff version.
