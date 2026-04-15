# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** AICB-P1 Group 113  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Nguyễn Duy Hiếu | Ingestion / Raw Owner | ___ |
| Phạm Đan Kha | Cleaning & Quality Owner | ___ |
| Phan Anh Khôi | Embed & Idempotency Owner | ___ |
| Trần Đăng Quang Huy | Retrieval Eval / Sprint 3 Evidence | ___ |
| Vũ Đức Kiên | Monitoring / Docs Owner | ___ |

**Ngày nộp:** 2026-04-15  
**Repo:** https://github.com/khadpham/Lecture-Day-08-09-10.git  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

Pipeline của nhóm đi theo chuỗi: raw CSV `data/raw/policy_export_dirty.csv` → ingest/sanitize → clean/quarantine → expectation gate → embed Chroma → manifest → freshness check. Sau khi đọc `analysis.md`, nhóm đã sửa hai lỗi đáng chú ý: `chunk_id` không còn phụ thuộc thứ tự dòng và dedupe không còn quét chéo giữa các `doc_id`. Nhờ đó, rerun cùng dữ liệu clean không sinh duplicate vector mới, còn document khác nhau nhưng có boilerplate giống nhau cũng không bị quarantine nhầm. Đây là phần quan trọng nhất để bảo đảm publish boundary và idempotency.

Run chính dùng trong report:
- clean snapshot: `run_id=sprint2-final-repeat-2`
- inject snapshot: `run_id=inject-bad`

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

`python etl_pipeline.py run --run-id sprint2-final-repeat-2`

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `stable_chunk_id_from_content` (rule) | ID cũ phụ thuộc `seq`, dễ vỡ khi reorder | `order_independent_id_set: True` khi đảo input; IDs giữ nguyên theo nội dung | Python snippet kiểm tra `clean_rows` |
| `doc_scoped_duplicate_text` (rule) | Dedupe global có thể quarantine chéo doc | `cross_doc_duplicate_quarantine_count: 0` với 2 doc khác nhau nhưng cùng boilerplate | Python snippet kiểm tra `clean_rows` |
| `refund_stale_note_scrub` (rule) | Chunk refund còn note migration cũ | Clean snapshot còn 7 ngày; inject preview lộ 14 ngày khi tắt fix | `artifacts/eval/before_after_eval_sprint2.csv`, `artifacts/eval/after_inject_bad.csv` |
| `refund_no_stale_14d_window` (expectation, halt) | Không có gate chặn stale refund | Clean: `violations=0`; inject: `violations=1` | `artifacts/logs/run_sprint2-final-repeat-2.log`, `artifacts/logs/run_inject-bad.log` |
| `chunk_id_unique` (expectation, halt) | Chưa có guard cho idempotent upsert | Clean + inject đều `duplicate_chunk_id_count=0` | `artifacts/logs/run_sprint2-final-repeat-2.log`, `artifacts/logs/run_inject-bad.log` |

**Rule chính (baseline + mở rộng):**

- Baseline: allowlist `doc_id`, chuẩn hoá `effective_date`, quarantine HR stale, fix refund 14→7, dedupe.
- Mở rộng/Sprint 3 fix:
  - chunk_id hash theo `doc_id + normalized chunk_text`, không phụ thuộc thứ tự dòng;
  - dedupe theo cặp `(doc_id, chunk_text)` để tránh quarantine chéo;
  - scrub note migration stale trong refund text.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Khi chạy `inject-bad` với `--no-refund-fix --skip-validate`, expectation `refund_no_stale_14d_window` fail có kiểm soát: `violations=1`. Nhóm không lờ đi fail này mà giữ log như bằng chứng rằng guardrail có tác dụng thật. Sau đó clean rerun `sprint2-final-repeat-2` xác nhận snapshot sạch đã quay về trạng thái đúng.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

Sprint 3 dùng `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate` để cố ý giữ lại stale refund 14 ngày trong publish snapshot. Đây là test có chủ đích cho publish boundary: pipeline vẫn có thể embed nếu người vận hành bỏ qua halt, nên quality gate phải thật sự đáng tin.

**Kết quả định lượng (từ CSV / bảng):**

- Clean snapshot `artifacts/eval/before_after_eval_sprint2.csv`: `q_refund_window` → `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_id=policy_refund_v4`
- Inject snapshot `artifacts/eval/after_inject_bad.csv`: `q_refund_window` → `contains_expected=yes`, `hits_forbidden=yes`, `top1_doc_id=policy_refund_v4`
- `q_leave_version` trên cả hai file vẫn `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`

Kết luận: sửa refund fix là khác biệt nhỏ ở code nhưng tác động lớn lên retrieval; top-1 vẫn đúng doc, nhưng context bên trong đã sai phiên bản.

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

SLA của nhóm là 24 giờ theo `FRESHNESS_SLA_HOURS`. Cả manifest sạch và inject đều fail freshness vì `latest_exported_at=2026-04-10T08:00:00Z` trong khi run ở ngày 2026-04-15, tức data mẫu đã cũ hơn khoảng 121 giờ. Fail này hợp lý: pipeline đang cảnh báo đúng rằng snapshot không còn fresh cho production. Vì vậy, freshness fail không phải lỗi code, mà là output đúng của monitor.

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

Có. Snapshot sạch được embed vào collection riêng `day10_kb` để Day 09 tiếp tục truy retrieval. Điểm quan trọng là Day 10 đứng trước Day 09 một lớp: nó đảm bảo không còn chunk refund stale, không còn HR 2025 lạc vào index, và rerun idempotent không làm collection phình thêm. Tách collection riêng cũng giúp tránh đè corpus demo khác.

---

## 6. Rủi ro còn lại & việc chưa làm

- Chưa có grading JSONL vì lớp chưa mở bộ câu grading.
- Freshness vẫn fail vì data mẫu đã cũ; muốn PASS thì phải dùng snapshot mới hơn hoặc tăng SLA có chủ đích.
- Nếu thêm nguồn mới, phải đồng bộ `ALLOWED_DOC_IDS`, `contracts/data_contract.yaml`, và source map trong docs.
