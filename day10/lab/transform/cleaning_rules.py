import csv
import re
from typing import List, Dict, Tuple


def load_raw_csv(path) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_cleaned_csv(path, rows):
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def write_quarantine_csv(path, rows):
    # Ensure we include the quarantine_reason column
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    if "quarantine_reason" not in fieldnames:
        fieldnames.append("quarantine_reason")

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clean_rows(
    rows: List[Dict], apply_refund_window_fix: bool = True
) -> Tuple[List[Dict], List[Dict]]:
    cleaned = []
    quarantine = []
    seen_hashes = set()

    for row in rows:
        # ---------------------------------------------------------
        # NEW RULE 1: Quarantine Empty Chunks
        # Logic: Records with no textual content are useless for vector embeddings.
        # Targets: Row 5 in the raw CSV.
        # ---------------------------------------------------------
        if not row.get("chunk_text") or not row["chunk_text"].strip():
            row["quarantine_reason"] = "Empty chunk_text"
            quarantine.append(row)
            continue

        # ---------------------------------------------------------
        # NEW RULE 2: Date Format Normalisation
        # Logic: Converts DD/MM/YYYY into standard ISO-8601 (YYYY-MM-DD).
        # Targets: Row 10 in the raw CSV.
        # ---------------------------------------------------------
        eff_date = row.get("effective_date", "").strip()
        if re.match(r"^\d{2}/\d{2}/\d{4}$", eff_date):
            parts = eff_date.split("/")
            row["effective_date"] = f"{parts[2]}-{parts[1]}-{parts[0]}"

        # ---------------------------------------------------------
        # NEW RULE 3: Quarantine Stale HR Policies (Version Conflict)
        # Logic: Quarantines HR policies strictly from 2025 to avoid RAG conflicts with 2026 data.
        # Targets: Row 7 in the raw CSV.
        # ---------------------------------------------------------
        if row.get("doc_id") == "hr_leave_policy" and row.get(
            "effective_date", ""
        ).startswith("2025"):
            row["quarantine_reason"] = "Stale HR Policy (2025 version superseded)"
            quarantine.append(row)
            continue

        # ---------------------------------------------------------
        # NEW RULE 4: Exact Deduplication
        # Logic: Prevents vector bloat by hashing doc_id and chunk_text.
        # Targets: Row 2 in the raw CSV.
        # ---------------------------------------------------------
        row_hash = hash(f"{row.get('doc_id')}_{row.get('chunk_text')}")
        if row_hash in seen_hashes:
            row["quarantine_reason"] = "Exact duplicate chunk"
            quarantine.append(row)
            continue
        seen_hashes.add(row_hash)

        # ---------------------------------------------------------
        # BASELINE RULE: Fix the 14-day refund window policy migration error.
        # Targets: Row 3 in the raw CSV.
        # ---------------------------------------------------------
        if apply_refund_window_fix and "14 ngày làm việc" in row.get("chunk_text", ""):
            row["chunk_text"] = row["chunk_text"].replace(
                "14 ngày làm việc", "7 ngày làm việc"
            )

        cleaned.append(row)

    return cleaned, quarantine
