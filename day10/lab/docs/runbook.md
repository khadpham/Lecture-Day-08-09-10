# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

> User / agent thấy gì? (VD: trả lời “14 ngày” thay vì 7 ngày)

- Agent trả lời đúng top-1 nhưng context top-k vẫn chứa chunk stale (ví dụ refund 14 ngày).
- Pipeline run có thể `PIPELINE_OK` nhưng freshness báo `FAIL`, nghĩa là dữ liệu đã cũ so với SLA.
- Grading/eval xuất hiện `hits_forbidden=yes` cho các câu nhạy cảm version (điển hình `q_refund_window`).

---

## Detection

> Metric nào báo? (freshness, expectation fail, eval `hits_forbidden`)

- Log pipeline: `expectation[...]` để xác định fail theo severity `halt` hay `warn`.
- Manifest freshness: `python etl_pipeline.py freshness --manifest <path>` để xem PASS/WARN/FAIL.
- Retrieval eval: `python eval_retrieval.py --out artifacts/eval/<name>.csv`, tập trung cột `hits_forbidden`.
- Quarantine volume: theo dõi `quarantine_records` và file `artifacts/quarantine/quarantine_<run_id>.csv`.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` (`latest_exported_at`, `run_id`, `skipped_validate`) | Xác định run nào publish, freshness có vượt SLA không |
| 2 | Mở `artifacts/quarantine/*.csv` theo `run_id` | Biết record nào bị loại, lý do gì (`reason`) |
| 3 | Chạy `python eval_retrieval.py --out artifacts/eval/current_check.csv` | So sánh `contains_expected` và `hits_forbidden` theo từng câu |
| 4 | Đối chiếu log `artifacts/logs/run_<run_id>.log` | Xác nhận expectation nào fail/halt, pipeline có `PIPELINE_OK` hay `PIPELINE_HALT` |

---

## Mitigation

> Rerun pipeline, rollback embed, tạm banner “data stale”, …

- Trường hợp stale refund hoặc version conflict: chạy lại pipeline chuẩn (không dùng `--no-refund-fix`, không `--skip-validate`).
- Nếu cần demo/điều tra, tách run_id rõ ràng (`inject-bad`, `after-fix`) để không nhầm evidence.
- Khi freshness FAIL kéo dài: thông báo owner nguồn và gắn trạng thái “data stale” cho kênh sử dụng retrieval.
- Nếu publish sai nghiêm trọng: rerun từ raw sạch để overwrite snapshot index (upsert + prune sẽ đồng bộ lại).

---

## Prevention

> Thêm expectation, alert, owner — nối sang Day 11 nếu có guardrail.

- Duy trì expectation `halt` cho rule critical (refund window, date schema, exported_at format).
- Thiết lập alert tự động khi `freshness_check=FAIL` hoặc `hits_forbidden=yes` trong eval định kỳ.
- Bắt buộc ghi `run_id` trong mọi evidence (log, manifest, eval) để truy vết nhanh.
- Mở rộng test inject định kỳ (schema drift, stale version, malformed text) trước mỗi đợt publish.
