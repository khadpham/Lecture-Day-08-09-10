# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** ___________  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Vũ Đức Kiên | Ingestion / Raw Owner | ___ |
| Phạm Đan Kha | Cleaning & Quality Owner | ___ |
| Trần Đặng Quang Huy | Embed & Idempotency Owner | ___ |
| Nguyễn Duy Hiếu | Monitoring / Docs Owner | ___ |

**Ngày nộp:** ___________  
**Repo:** ___________  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

Nhóm triển khai pipeline ETL theo chuỗi ingest -> clean -> validate -> embed -> monitor, với dữ liệu đầu vào là CSV export bẩn mô phỏng nguồn policy/IT helpdesk. Ở bước ingest, pipeline ghi nhận `run_id` và `raw_records` để tạo lineage cơ bản. Bước clean chuẩn hoá schema (đặc biệt `effective_date`, `exported_at`), áp dụng allowlist `doc_id`, loại duplicate, quarantine bản HR stale và các bản ghi không đạt rule mới (text bất thường, exported_at lỗi). Bước validate chạy expectation suite theo mức `warn/halt` để kiểm soát chất lượng trước publish. Nếu pass (hoặc có chủ đích `--skip-validate` trong inject demo), dữ liệu cleaned được embed vào Chroma bằng cơ chế upsert/prune theo `chunk_id` để đảm bảo idempotency. Cuối run, pipeline ghi manifest và kiểm tra freshness SLA để phát hiện stale data phục vụ observability.

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

`python etl_pipeline.py run`

### Sprint 1 — Ingest & schema (completion note)

- Ran: `python etl_pipeline.py run --run-id sprint1`
- Raw ingest: `raw_records=10`
- Cleaning result: `cleaned_records=6`
- Quarantine result: `quarantine_records=4`
- Embed status: `embed_upsert count=6 collection=day10_kb`
- Manifest: `artifacts/manifests/manifest_sprint1.json` generated
- Freshness: `FAIL` (`latest_exported_at=2026-04-10T08:00:00`, `age_hours=121.64`, `sla_hours=24.0`, reason `freshness_sla_exceeded`)

Validation checks:
- `cleaned_rows=6` from `artifacts/cleaned/cleaned_sprint1.csv`
- `quarantine_rows=4` from `artifacts/quarantine/quarantine_sprint1.csv`

Conclusion:
- Sprint 1 DoD achieved (log contains `run_id`, `raw_records`, `cleaned_records`, `quarantine_records`).
- Freshness fail is expected for stale source export and is treated as monitoring signal, while the ETL run remains `PIPELINE_OK`.

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `missing/invalid_exported_at -> quarantine` | `quarantine_records=4` (sprint2-base) | `quarantine_records=5` (sprint2-inject-fix) | `artifacts/logs/run_sprint2-base.log`, `artifacts/logs/run_sprint2-inject-fix.log` |
| `chunk_text_too_long -> quarantine` | Không phát sinh trên base | Phát sinh khi inject dòng text dài (đóng góp vào quarantine tăng) | `artifacts/quarantine/quarantine_sprint2-inject-fix.csv` |
| `chunk_text_contains_control_chars -> quarantine` | Không phát sinh trên base | Phát sinh khi inject control/binary text (nếu có trong inject) | `artifacts/quarantine/quarantine_sprint2-inject-fix.csv` |
| `expectation[exported_at_iso_datetime]` (halt) | `invalid_exported_at_rows=0` | `invalid_exported_at_rows=0` | `artifacts/logs/run_sprint2-base.log`, `artifacts/logs/run_sprint2-inject-fix.log` |
| `expectation[no_duplicate_doc_effective_text]` (halt) | `duplicate_rows=0` | `duplicate_rows=0` | `artifacts/logs/run_sprint2-base.log`, `artifacts/logs/run_sprint2-inject-fix.log` |

**Rule chính (baseline + mở rộng):**

- Baseline: allowlist `doc_id`, chuẩn hoá `effective_date` về `YYYY-MM-DD`, quarantine bản HR cũ trước `2026-01-01`, loại duplicate `chunk_text`, fix refund window `14 -> 7`.
- Rule mở rộng 1: quarantine `missing_exported_at` / `invalid_exported_at_format`.
- Rule mở rộng 2: quarantine `chunk_text_contains_control_chars`.
- Rule mở rộng 3: quarantine `chunk_text_too_long` (ngưỡng > 500 ký tự).
- Kết quả quan sát: base run `quarantine_records=4`, inject run `quarantine_records=5`, cho thấy rule mới có tác động đo được.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Trong kịch bản inject có chủ đích (`--no-refund-fix --skip-validate`), chất lượng retrieval suy giảm thể hiện qua `hits_forbidden=yes` ở câu `q_refund_window` trong `artifacts/eval/after_inject_bad.csv`. Đây là tín hiệu tương đương expectation logic ở tầng retrieval: dữ liệu stale vẫn xuất hiện trong top-k dù top-1 có vẻ đúng. Cách xử lý là chạy lại pipeline chuẩn (bật refund fix, không skip validate), sau đó eval lại trong `artifacts/eval/after_fix.csv` và xác nhận `hits_forbidden=no`.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

Nhóm chạy kịch bản inject có chủ đích bằng lệnh `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`, sau đó đánh giá retrieval bằng `python eval_retrieval.py --out artifacts/eval/after_inject_bad.csv`. Kịch bản này cố ý bỏ rule sửa cửa sổ hoàn tiền `14 -> 7` và bỏ chặn expectation halt để quan sát tác động của dữ liệu stale lên top-k retrieval. Sau đó nhóm chạy lại pipeline chuẩn (có refund fix, validate đầy đủ) và xuất `artifacts/eval/after_fix.csv` để so sánh trực tiếp.

**Kết quả định lượng (từ CSV / bảng):**

- Với câu `q_refund_window`, file `after_inject_bad.csv` cho thấy `contains_expected=yes` nhưng `hits_forbidden=yes`. Điều này nghĩa là dù câu trả lời nhìn “đúng”, context top-k vẫn chứa chunk stale (14 ngày), đúng tinh thần observability phát hiện rủi ro ngữ nghĩa ẩn.
- Sau khi chạy lại pipeline chuẩn, `after_fix.csv` cho cùng câu `q_refund_window` có `hits_forbidden=no`, chứng minh publish boundary đã sạch dữ liệu stale trong top-k.
- Các câu còn lại (`q_p1_sla`, `q_lockout`) giữ ổn định với `contains_expected=yes`, `hits_forbidden=no` ở cả hai kịch bản.
- Với `q_leave_version`, kết quả sau fix có `top1_doc_expected=yes`, xác nhận retrieval trả đúng tài liệu HR hiện hành 2026 và không bị nhiễu bởi version cũ.
- Kết luận: inject có chủ đích làm chất lượng retrieval giảm theo chỉ báo an toàn (`hits_forbidden`), và pipeline chuẩn đã phục hồi chất lượng retrieval đúng kỳ vọng.

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

Nhóm đặt `FRESHNESS_SLA_HOURS=24` theo ngưỡng vận hành nội bộ cho knowledge base hỗ trợ CS/IT. Ở run `sprint1`, manifest ghi `latest_exported_at=2026-04-10T08:00:00`; khi chạy freshness check thì `age_hours=121.64` nên trạng thái `FAIL` với lý do `freshness_sla_exceeded`. Kết quả này phù hợp kỳ vọng vì bộ lab cố ý dùng export cũ để minh hoạ tín hiệu stale data.

Về ý nghĩa vận hành: `PASS` khi tuổi dữ liệu nằm trong SLA và có thể publish bình thường; `WARN` dùng cho các tín hiệu cần theo dõi (ví dụ thiếu trường non-critical hoặc gần ngưỡng SLA tuỳ policy nhóm); `FAIL` khi vượt ngưỡng freshness hoặc vi phạm critical condition, cần mở ticket cho owner nguồn và tạm dừng các tác vụ phụ thuộc dữ liệu mới. Trong pipeline hiện tại, freshness được log ở cuối run để hỗ trợ observability và quyết định vận hành, còn luồng ingest-clean-validate-embed vẫn có thể hoàn tất với `PIPELINE_OK`.

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

Dữ liệu sau embed có thể phục vụ trực tiếp cho hệ multi-agent Day 09 thông qua cùng lớp retrieval (Chroma collection `day10_kb`) và quy trình query top-k hiện có. Điểm khác biệt là Day 10 bổ sung lớp kiểm soát chất lượng trước khi publish: cleaning, expectation halt, quarantine, manifest theo `run_id`, và freshness check. Nhờ vậy agent Day 09 không chỉ “trả lời được” mà còn giảm rủi ro đọc nhầm phiên bản stale (ví dụ policy hoàn tiền 14 ngày). Nếu cần tách môi trường, nhóm có thể tách collection theo stage (`day10_kb_dev`, `day10_kb_prod`) để kiểm soát rollout.

---

## 6. Rủi ro còn lại & việc chưa làm

- Chưa tích hợp cảnh báo tự động (Slack/Email) khi `freshness_check=FAIL`; hiện mới dừng ở log/manifest.
- Chưa có regression test tự động cho toàn bộ rule mới; hiện xác minh chủ yếu bằng run thủ công và file inject.
- Chưa chuẩn hoá quy trình rollback collection khi publish sai dữ liệu (runbook mới ở mức hướng dẫn thủ công).
- Chưa theo dõi chi phí/độ trễ embed theo run_id để tối ưu vận hành khi volume tăng.
- Chưa mở rộng bộ câu hỏi eval/grading cho nhiều biến thể ngôn ngữ, nên độ phủ kiểm thử retrieval còn hạn chế.
