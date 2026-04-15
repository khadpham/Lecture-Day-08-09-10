# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** 2A202600253 - Phạm Đan Kha  
**Vai trò:** Embed Owner  
**Ngày nộp:** 15/04/2026  

---

## 1. Tôi phụ trách phần nào?

**File / module:**
Là người phụ trách Embed cho pipeline này, trách nhiệm chính của tôi là quản lý giao tiếp giữa các artifact dữ liệu đã được làm sạch và vector store ChromaDB cục bộ. Tôi trực tiếp quản lý hàm `cmd_embed_internal` trong `etl_pipeline.py`, đảm bảo rằng việc nạp các chunk văn bản vào collection `day10_kb` diễn ra trơn tru, mang tính idempotent (không thay đổi trạng thái khi chạy nhiều lần) và phản ánh hoàn hảo kết quả mới nhất từ nhóm làm sạch dữ liệu.

**Kết nối với thành viên khác:**
Tôi nhận đầu ra (`cleaned_csv`) từ ranh giới Transform của Hiếu và ranh giới Expectation của Khôi. Dữ liệu này được tôi chuyển hóa thành Knowledge Base, phục vụ trực tiếp cho quá trình truy xuất của Agent ở hạ nguồn (Day 09).

**Bằng chứng (commit / comment trong code):**
Đoạn log `embed_upsert count=7 collection=day10_kb` và các đoạn code tính toán `prev_ids - set(ids)` trong file `etl_pipeline.py`.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất của tôi là thiết lập cơ chế **Idempotent Upserts và Cắt tỉa (Pruning)**. Một yêu cầu cốt lõi về data observability là việc chạy lại pipeline không được làm phình to database (vector bloat). Nếu chỉ dùng hàm `.add()`, các lần chạy lại sẽ nhân bản các chunk giống nhau, phá hủy độ chính xác truy xuất. 

Tôi triển khai chiến lược idempotent qua hai bước. Đầu tiên, dùng hàm `.upsert()` của ChromaDB, ánh xạ `chunk_id` duy nhất từ CSV thành ID nội bộ của vector store (để ghi đè khi có thay đổi nội dung/metadata thay vì nhân bản). Thứ hai, tôi đưa vào cơ chế cắt tỉa: script tính toán sự khác biệt giữa các vector ID hiện có và `chunk_id` đầu vào mới (`prev_ids - set(ids)`). Bất kỳ ID cũ nào không còn tồn tại trong dữ liệu sạch sẽ bị chủ động xóa (`col.delete()`). Điều này đảm bảo vector index luôn là một bản snapshot hoàn hảo của ranh giới phát hành (publish boundary).

---

## 3. Một lỗi hoặc anomaly đã xử lý

**Triệu chứng & Phát hiện:** Trong lần chạy đầu tiên của giai đoạn embedding, pipeline sinh ra một log cảnh báo khá đáng sợ từ thư viện `sentence-transformers`: `embeddings.position_ids | UNEXPECTED`. 
**Cách xử lý:** Ban đầu, triệu chứng này trông giống như một lỗi nghiêm trọng trong quá trình tải trọng số (weights) của mô hình. Tuy nhiên, sau khi điều tra kiến trúc, tôi nhận định đây là một cảnh báo vô hại (benign artifact) khi tải mô hình `all-MiniLM-L6-v2` từ Hugging Face Hub bằng phiên bản thư viện hiện tại. Vì kiến trúc mô hình chủ động bỏ qua các position ID này khi nạp vào context, tôi đã đưa ra quyết định có cơ sở là ghi chú nó vào Runbook như một cảnh báo (WARN) thay vì code thêm luật để dừng pipeline (HALT). Quá trình embedding thực tế vẫn tiến hành thành công.

---

## 4. Bằng chứng trước / sau

Sự thành công của logic embedding và cơ chế Pruning được chứng minh rõ ràng qua dữ liệu đánh giá:
**Từ file `before_after_eval.csv`:**
Đối với truy vấn `q_refund_window`, ở lần chạy `inject-bad` (khi chưa xóa fix lỗi và chưa prune), file đánh giá báo `hits_forbidden=yes` do lẫn lộn vector 14 ngày. Nhưng sau khi hệ thống của tôi chạy bản chuẩn (Clean), vector rác đã bị xóa sạch hoàn toàn khỏi ChromaDB, trả về `contains_expected=yes` VÀ `hits_forbidden=no`. Hơn nữa, log hệ thống ghi nhận đúng `embed_upsert count=7`, đồng bộ chính xác với số record của ranh giới Clean.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ thay thế phiên bản ChromaDB lưu trữ qua file cục bộ bằng một persistent client kết nối với một server vector database chuyên dụng (như Milvus hoặc Qdrant chạy qua Docker). Hiện tại, lưu DB ở `./chroma_db` phục vụ tốt cho prototype, nhưng trong môi trường production có nhiều Data Scientist cùng chạy ETL đồng thời, chúng ta sẽ dễ gặp xung đột khóa tệp (file-locking). Một server tập trung sẽ khắc phục điều này và cải thiện khả năng tích hợp CI/CD.