# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

Người dùng (User) hoặc Agent truy xuất hệ thống CS Helpdesk nhận được câu trả lời chứa thông tin mâu thuẫn hoặc đã lỗi thời. Cụ thể: Agent báo cáo khách hàng có "14 ngày làm việc" để yêu cầu hoàn tiền, trong khi chính sách mới nhất (v4) đã quy định là "7 ngày làm việc". Điều này gây ra trải nghiệm xấu cho khách hàng và rủi ro sai lệch nghiệp vụ.

---

## Detection

Sự cố này được phát hiện thông qua các metric giám sát tự động trong pipeline:
1. **Expectation Fail:** Log báo `expectation[expect_no_14_day_refund] FAIL (HALT)` chỉ ra rằng dòng dữ liệu chứa "14 ngày" đã lọt vào ranh giới làm sạch mà chưa được vá.
2. **Eval Metric (`hits_forbidden`):** Khi chạy đánh giá (eval), tệp CSV báo cáo cột `hits_forbidden=yes` cho câu hỏi `q_refund_window`, chứng minh vector chứa thông tin cấm/cũ vẫn đang chễm chệ lọt vào top-k context của ChromaDB.
3. **Freshness Metric:** Log báo `freshness_check=FAIL`, cảnh báo `latest_exported_at` đã cũ hơn SLA 24h.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` | Tìm file manifest của lần chạy gần nhất. Kiểm tra biến `skipped_validate`. Nếu là `true`, chứng tỏ có người/hệ thống đã cố tình vượt rào cảnh báo HALT (dùng cờ `--skip-validate`). |
| 2 | Mở `artifacts/quarantine/*.csv` | Kiểm tra xem các dòng chính sách lỗi thời (như lỗi 14 ngày hoặc HR 2025) có bị bắt vào danh sách cách ly cùng với `quarantine_reason` hay không. Nếu không có, bộ luật Transform đang có lỗ hổng. |
| 3 | Chạy `python eval_retrieval.py` | Kiểm tra file `artifacts/eval/before_after_eval.csv`. Kết quả chuẩn phải là `contains_expected=yes` và `hits_forbidden=no` (đối với câu `q_refund_window`). Nếu `hits_forbidden=yes`, Vector DB đang bị nhiễu do tàn dư cũ. |

---

## Mitigation

1. **Khắc phục ngay lập tức:** Chạy lại chuẩn pipeline bằng lệnh `python etl_pipeline.py run` (Tuyệt đối KHÔNG dùng các cờ bypass như `--skip-validate` hay `--no-refund-fix`).
2. **Dọn dẹp Vector DB:** Theo dõi log của ranh giới Embed để đảm bảo logic Prune hoạt động (Hệ thống lấy danh sách `prev_ids` trừ đi `chunk_id` sạch, sau đó gọi `col.delete()` thành công để tiêu diệt tận gốc stale vector 14 ngày).
3. **Tạm thời (Nếu chưa fix xong):** Đặt cờ cảnh báo "Dữ liệu đang được đồng bộ" trên giao diện của Agent để báo cho user.

---

## Prevention

1. **Strict Guardrail:** Duy trì Expectation `expect_no_14_day_refund` ở mức độ nghiêm trọng `HALT`. Nếu ranh giới Validate thất bại, pipeline sẽ tự hủy (abort) ngay lập tức, không cho phép embed dữ liệu bẩn vào Knowledge Base.
2. **Alerting:** Tích hợp bắn thông báo (alert) tự động qua Slack/Email cho Data Owner ngay khi `freshness_check=FAIL` hoặc xảy ra sự cố `PIPELINE_HALT`.
3. **Ownership:** Gán trách nhiệm rõ ràng cho bộ phận nghiệp vụ (CS) cập nhật triệt để tài liệu gốc trên CMS, không nên chỉ phụ thuộc vào `cleaning_rules.py` của team Data.