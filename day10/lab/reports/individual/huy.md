# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** 2A202600292 - Trần Đặng Quang Huy  
**Vai trò:** Ingestion Owner  
**Ngày nộp:** 15/04/2026  

---

## 1. Tôi phụ trách phần nào?

**File / module:**
Tôi chịu trách nhiệm chính ở ranh giới Ingestion (Đầu vào) của hệ thống. Tôi quản lý hàm `cmd_run` trong tệp `etl_pipeline.py`, đảm bảo việc đọc file `data/raw/policy_export_dirty.csv`, khởi tạo các thư mục artifacts (`logs`, `manifests`, `quarantine`), và đặc biệt là sinh ra `run_id` cùng file `manifest.json` để theo dõi toàn bộ vòng đời của dữ liệu.

**Kết nối với thành viên khác:**
Dữ liệu raw và `run_id` tôi khởi tạo là đầu vào bắt buộc để Hiếu (Cleaning) xử lý dữ liệu và Đan Kha (Embed) gắn metadata vào Vector DB.

**Bằng chứng (commit / comment trong code):**
Trong `etl_pipeline.py`, tôi xử lý logic sinh ID: `run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%MZ")` và log lại `raw_records=10` ngay từ ranh giới đầu tiên.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật cốt lõi của tôi là cách thiết kế và lưu trữ file Manifest (`manifest_<run_id>.json`). Thay vì chỉ in log ra màn hình terminal, tôi quyết định ghi mọi thông số (bao gồm cờ bypass như `skipped_validate`, số lượng `raw_records`, `cleaned_records` và `latest_exported_at`) vào một file JSON tĩnh. Quyết định này đóng vai trò như một "hộp đen máy bay" cho Data Pipeline. Nếu hệ thống LLM ở Day 09 trả lời sai, chúng ta không cần mò mẫm chạy lại code, mà chỉ cần mở manifest của lần chạy đó để kiểm tra xem ranh giới Ingestion có nhận đủ số dòng hay không, hay có ai vô tình chạy bằng cờ `--skip-validate` trên production hay không.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Trong quá trình khởi tạo Ingestion, tôi nhận thấy anomaly về việc quản lý đường dẫn file thô. Ban đầu, nếu không có file CSV, Python sẽ quăng lỗi `FileNotFoundError` khiến toàn bộ ứng dụng crash một cách thiếu kiểm soát, không kịp ghi log. 
Tôi đã xử lý bằng cách thêm khối kiểm tra tính toàn vẹn của đường dẫn (`raw_path.is_file()`) ngay đầu pipeline. Nếu phát hiện thiếu file, thay vì crash, hệ thống sẽ in ra lỗi chuẩn `sys.stderr` và trả về `exit code 1` một cách gọn gàng. Nhờ vậy, quá trình chạy CI/CD (nếu có) sẽ nhận diện được lỗi hạ tầng mà không bị treo.

---

## 4. Bằng chứng trước / sau

Bằng chứng cho hệ thống log Ingestion của tôi nằm ở đầu ra terminal và file manifest của lần chạy chuẩn:
**Run ID:** `2026-04-15T08-53Z`
**Log Ingestion:**
```text
run_id=2026-04-15T08-53Z
raw_records=10
manifest_written=artifacts\manifests\manifest_2026-04-15T08-53Z.json
Số liệu này chứng minh luồng đọc file thô đã hoạt động hoàn hảo và bàn giao đúng 10 bản ghi cho ranh giới Transform. 
```

## 5. Cải tiến tiếp theo
Nếu có thêm 2 giờ, tôi sẽ viết một hàm kết nối API hoặc đọc trực tiếp từ bảng cơ sở dữ liệu PostgreSQL thay vì đọc từ file CSV tĩnh RAW_DEFAULT. Điều này sẽ mô phỏng chính xác hơn ranh giới Ingestion trong một hệ thống thực tế.


---