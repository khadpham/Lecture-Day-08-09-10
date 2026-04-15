# Kiến trúc pipeline — Lab Day 10

**Nhóm:** _______________  
**Cập nhật:** _______________

---

## 1. Sơ đồ luồng (bắt buộc có 1 diagram: Mermaid / ASCII)

```
raw export (CSV/API/…)  →  clean  →  validate (expectations)  →  embed (Chroma)  →  serving (Day 08/09)
```

> Vẽ thêm: điểm đo **freshness**, chỗ ghi **run_id**, và file **quarantine**.

# Pipeline Architecture & Data Boundaries

## 1. High-Level Architecture
Our ETL pipeline is designed to be idempotent, observable, and strict regarding data quality before any text reaches the LLM retrieval engine.

```mermaid
graph TD
    A[Raw CSV Export] -->|Ingest Boundary| B(etl_pipeline.py)
    B --> C{Cleaning Rules}
    C -->|Quarantine| D[Quarantine CSV]
    C -->|Cleaned| E{Expectations Suite}
    E -->|HALT| F[Pipeline Abort]
    E -->|WARN / PASS| G[Cleaned CSV]
    G -->|Embed Boundary| H[(ChromaDB: day10_kb)]
---

## 2. Ranh giới trách nhiệm

| Thành phần | Input | Output | Owner nhóm |
|------------|-------|--------|--------------|
| Ingest | … | … | … |
| Transform | … | … | … |
| Quality | … | … | … |
| Embed | … | … | … |
| Monitor | … | … | … |

---

## 3. Idempotency & rerun

> Mô tả: upsert theo `chunk_id` hay strategy khác? Rerun 2 lần có duplicate vector không?

---

## 4. Liên hệ Day 09

> Pipeline này cung cấp / làm mới corpus cho retrieval trong `day09/lab` như thế nào? (cùng `data/docs/` hay export riêng?)

---

## 5. Rủi ro đã biết

- …
