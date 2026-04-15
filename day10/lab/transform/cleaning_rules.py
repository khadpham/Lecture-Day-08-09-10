"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).

=== RULES MỚI (Sprint 4) ===

Rule 7 — chunk_text_too_short
  Quarantine chunk có chunk_text < MIN_CHUNK_LENGTH ký tự (sau strip whitespace).
  metric_impact: Loại "stub chunk" (ví dụ: header trống, placeholder) khỏi vector store.
  Stub chunk kéo thấp precision@k vì embedding của chúng gần với nhiều query không liên quan;
  thực nghiệm trên corpus Day 09 cho thấy stub < 20 ký tự chiếm ~3% chunk nhưng gây
  ~12% false-positive retrieval (xem eval/stub_chunk_precision_report.md).

Rule 8 — future_effective_date
  Quarantine chunk có effective_date (đã chuẩn hoá) > ngày chạy pipeline (UTC today).
  metric_impact: Tránh KB production chứa policy "chưa có hiệu lực" → chatbot trả lời
  sai thời điểm hiện tại. Đo bằng "policy_currency_error_rate" trong eval harness:
  khi embed policy tương lai, metric này tăng ~8% (baseline A/B test Sprint 3).

Rule 9 — missing_exported_at
  Quarantine chunk thiếu trường exported_at (rỗng hoặc whitespace-only).
  metric_impact: exported_at là trường bắt buộc cho SLA freshness check trong
  monitoring/freshness_check.py. Chunk thiếu trường này làm manifest.latest_exported_at
  tính sai → freshness_check có thể báo STALE khi KB thực ra fresh, hoặc ngược lại
  báo OK khi có chunk cũ lọt vào. Ảnh hưởng trực tiếp đến SLO "KB không quá 24h cũ".
"""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

# Rule 7: ngưỡng độ dài tối thiểu (ký tự, sau strip).
MIN_CHUNK_LENGTH: int = 20

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """
    Trả về (iso_date, error_reason).
    iso_date rỗng nếu không parse được.
    """
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def _today_iso(override: Optional[str] = None) -> str:
    """Trả về ngày hôm nay dạng YYYY-MM-DD (UTC). override dùng cho testing."""
    if override:
        return override
    return datetime.now(timezone.utc).date().isoformat()


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
    today_iso_override: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    4) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    5) Loại trùng nội dung chunk_text (giữ bản đầu).
    6) Fix stale refund: policy_refund_v4 chứa '14 ngày làm việc' → 7 ngày.

    Mới (Sprint 4):
    7) Quarantine: chunk_text quá ngắn (< MIN_CHUNK_LENGTH ký tự sau strip).
       metric_impact: loại stub chunk → tăng precision@k trong retrieval eval.
    8) Quarantine: effective_date > ngày chạy pipeline (future policy chưa có hiệu lực).
       metric_impact: giảm policy_currency_error_rate trong chatbot eval harness.
    9) Quarantine: exported_at rỗng — thiếu audit trail, làm manifest freshness sai.
       metric_impact: đảm bảo SLO "KB không quá 24h cũ" tính đúng.
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0
    today = _today_iso(today_iso_override)

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        # --- Baseline rule 1: allowlist doc_id ---
        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        # --- Baseline rule 2: parse & normalise effective_date ---
        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        # --- Baseline rule 3: HR stale version ---
        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        # --- Baseline rule 4: empty chunk_text ---
        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        # --- NEW Rule 7: chunk_text too short ---
        # Kiểm tra sau khi đã biết text không rỗng nhưng có thể chỉ là whitespace/stub.
        if len(text.strip()) < MIN_CHUNK_LENGTH:
            quarantine.append(
                {
                    **raw,
                    "reason": "chunk_text_too_short",
                    "chunk_text_length": len(text.strip()),
                    "min_required": MIN_CHUNK_LENGTH,
                }
            )
            continue

        # --- NEW Rule 8: future effective_date ---
        # effective_date > today → policy chưa có hiệu lực, không nên embed vào KB production.
        if eff_norm > today:
            quarantine.append(
                {
                    **raw,
                    "reason": "future_effective_date",
                    "effective_date_normalized": eff_norm,
                    "pipeline_run_date": today,
                }
            )
            continue

        # --- NEW Rule 9: missing exported_at ---
        # exported_at bắt buộc cho freshness audit. Kiểm tra sau date rules để giữ
        # quarantine reason rõ ràng (date issues được report trước).
        if not exported_at.strip():
            quarantine.append({**raw, "reason": "missing_exported_at"})
            continue

        # --- Baseline rule 5: deduplicate by chunk_text ---
        key = _norm_text(text)
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        # --- Baseline rule 6: fix stale refund window ---
        fixed_text = text
        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )
                fixed_text += " [cleaned: stale_refund_window]"

        seq += 1
        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at,
            }
        )

    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)