"""
Cleaning rules — raw export → cleaned rows + quarantine.

Baseline gồm các failure mode mở rộng (allowlist doc_id, parse ngày, HR stale version).
Sinh viên thêm ≥3 rule mới: mỗi rule phải ghi `metric_impact` (xem README — chống trivial).
"""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Khớp export hợp lệ trong lab (mở rộng khi nhóm thêm doc mới — phải đồng bộ contract).
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_CONTROL_CHARS = re.compile(r"[\u200b\u200c\u200d\ufeff\x00]")
_REFUND_STALE_NOTE = re.compile(
    r"\(\s*ghi chú:.*?(?:policy-v3|sync cũ|migration).*?\)\s*",
    re.IGNORECASE,
)


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _sanitize_text(s: str) -> str:
    return _CONTROL_CHARS.sub("", (s or "").strip())


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int | None = None) -> str:
    """
    Tạo chunk_id ổn định theo nội dung thay vì theo thứ tự dòng.

    `seq` giữ lại để tương thích chữ ký cũ nhưng không còn ảnh hưởng tới ID,
    tránh vỡ idempotency khi input bị reorder hoặc khi một số dòng bị quarantine.
    """
    stable_text = _norm_text(chunk_text)
    h = hashlib.sha256(f"{doc_id}|{stable_text}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{h}"


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


def _normalize_exported_at(raw: str) -> Tuple[str, str]:
    """
    Chuẩn hoá exported_at sang ISO datetime (UTC) dạng YYYY-MM-DDTHH:MM:SSZ.
    Trả về (iso_datetime, error_reason).
    """
    s = _sanitize_text(raw)
    if not s:
        return "", "missing_exported_at"

    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        # Cho phép input ngày thuần, mặc định đầu ngày UTC.
        return f"{s}T00:00:00Z", ""

    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return "", "invalid_exported_at_format"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), ""


def _normalize_refund_text(text: str) -> str:
    """
    Loại ghi chú migration stale (policy-v3/sync cũ) trong chunk refund để giảm nhiễu retrieval.
    """
    cleaned = _REFUND_STALE_NOTE.sub("", text)
    return " ".join(cleaned.split())


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            norm: Dict[str, str] = {}
            for k, v in r.items():
                if k is None:
                    continue
                nk = _sanitize_text(k).lstrip("\ufeff")
                norm[nk] = _sanitize_text(v or "")
            rows.append(norm)
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Trả về (cleaned, quarantine).

    Baseline (mở rộng theo narrative Day 10):
    1) Quarantine: doc_id không thuộc allowlist (export lạ / catalog sai).
    2) Chuẩn hoá effective_date sang YYYY-MM-DD; quarantine nếu không parse được.
    3) Chuẩn hoá exported_at sang ISO datetime; quarantine nếu thiếu/sai định dạng.
    4) Quarantine: chunk hr_leave_policy có effective_date < 2026-01-01 (bản HR cũ / conflict version).
    5) Quarantine: chunk_text rỗng hoặc effective_date rỗng sau chuẩn hoá.
    6) Clean policy_refund_v4: bỏ ghi chú migration stale + fix cửa sổ 14→7 (nếu bật).
    7) Loại trùng nội dung chunk_text *sau clean* (giữ bản đầu).
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[tuple[str, str]] = set()
    cleaned: List[Dict[str, Any]] = []

    for raw in rows:
        doc_id = raw.get("doc_id", "")
        text = raw.get("chunk_text", "")
        eff_raw = raw.get("effective_date", "")
        exported_at = raw.get("exported_at", "")

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "reason": "unknown_doc_id"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        exported_norm, exported_err = _normalize_exported_at(exported_at)
        if exported_err:
            quarantine.append({**raw, "reason": exported_err, "exported_at_raw": exported_at})
            continue

        if doc_id == "hr_leave_policy" and eff_norm < "2026-01-01":
            quarantine.append(
                {
                    **raw,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                }
            )
            continue

        if not text:
            quarantine.append({**raw, "reason": "missing_chunk_text"})
            continue

        fixed_text = " ".join(text.split())
        if doc_id == "policy_refund_v4":
            fixed_text = _normalize_refund_text(fixed_text)

        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if "14 ngày làm việc" in fixed_text:
                fixed_text = fixed_text.replace(
                    "14 ngày làm việc",
                    "7 ngày làm việc",
                )

        key = (doc_id, _norm_text(fixed_text))
        if key in seen_text:
            quarantine.append({**raw, "reason": "duplicate_chunk_text_post_clean"})
            continue
        seen_text.add(key)

        cleaned.append(
            {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_norm,
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
