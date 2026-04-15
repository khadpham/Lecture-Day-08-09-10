from typing import List, Dict, Tuple
import re


class ExpectationResult:
    def __init__(self, name: str, passed: bool, severity: str, detail: str):
        self.name = name
        self.passed = passed
        self.severity = severity  # "WARN" or "HALT"
        self.detail = detail


def run_expectations(cleaned_rows: List[Dict]) -> Tuple[List[ExpectationResult], bool]:
    results = []
    halt = False

    # ---------------------------------------------------------
    # EXPECTATION 1: HALT on unpatched 14-day refund policy
    # Logic: Ensures the cleanup rule successfully patched the 14-day window.
    # ---------------------------------------------------------
    stale_refunds = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4"
        and "14 ngày làm việc" in r.get("chunk_text", "")
    ]
    if stale_refunds:
        results.append(
            ExpectationResult(
                "expect_no_14_day_refund",
                False,
                "HALT",
                f"Failed: Found {len(stale_refunds)} chunks still containing stale 14-day policy.",
            )
        )
        halt = True
    else:
        results.append(
            ExpectationResult(
                "expect_no_14_day_refund",
                True,
                "HALT",
                "Passed: No 14-day refund policies found.",
            )
        )

    # ---------------------------------------------------------
    # EXPECTATION 2: HALT on Non-ISO 8601 dates
    # Logic: Validates that Cleaning Rule 2 successfully converted all dates.
    # ---------------------------------------------------------
    invalid_dates = []
    for r in cleaned_rows:
        date_validation = r.get("effective_date", "").strip()
        if date_validation and not re.match(r"^\d{4}-\d{2}-\d{2}$", date_validation):
            invalid_dates.append(r)

    if invalid_dates:
        results.append(
            ExpectationResult(
                "expect_iso_dates",
                False,
                "HALT",
                f"Failed: Found {len(invalid_dates)} rows with non-ISO date formats.",
            )
        )
        halt = True
    else:
        results.append(
            ExpectationResult(
                "expect_iso_dates",
                True,
                "HALT",
                "Passed: All effective dates conform to ISO-8601.",
            )
        )

    # ---------------------------------------------------------
    # EXPECTATION 3: WARN on legacy catalog documents
    # Logic: Flags documents marked as 'legacy' in doc_id to alert the admin, but does not stop the pipeline.
    # ---------------------------------------------------------
    legacy_docs = [r for r in cleaned_rows if "legacy" in r.get("doc_id", "").lower()]
    if legacy_docs:
        results.append(
            ExpectationResult(
                "expect_no_legacy_docs",
                False,
                "WARN",
                f"Warning: Ingested {len(legacy_docs)} legacy documents. Consider pruning from source system.",
            )
        )
    else:
        results.append(
            ExpectationResult(
                "expect_no_legacy_docs",
                True,
                "WARN",
                "Passed: No legacy documents found.",
            )
        )

    return results, halt
