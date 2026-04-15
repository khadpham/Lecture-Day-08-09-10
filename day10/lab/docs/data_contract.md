# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Source Map
| Source System | Description | Expected Refresh | Failure Mode | Monitoring Metric |
| :--- | :--- | :--- | :--- | :--- |
| **HR_Core_DB** | Primary source for employee leave policies and entitlements. | Daily at 00:00 UTC | Stale data export (missing latest policy updates). | `freshness_hours` < 24h |
| **CS_Helpdesk_Wiki** | Source for customer service refund policies and SLAs. | Real-time / Event-driven | Conflicting window periods (e.g., 14 days vs 7 days). | `expectation_halt_count` = 0 |

## 2. Schema Definition (Cleaned Data)
* `doc_id` (String): Unique identifier for the document.
* `policy_type` (String): Categorisation (e.g., HR, CS).
* `effective_date` (ISO-8601 Date): Standardised active date.
* `refund_window_days` (Integer): Allowed refund period in days.
* `content` (String): Text payload for embedding.
---

## 3. Quy tắc quarantine vs drop

> Record bị flag đi đâu? Ai approve merge lại?

---

## 4. Phiên bản & canonical

> Source of truth cho policy refund: file nào / version nào?
