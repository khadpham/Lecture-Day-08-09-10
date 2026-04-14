# Báo Cáo Cá Nhân - Lab Day 08: RAG Pipeline

**Họ và tên:** Vũ Đức Kiên  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500-800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong bài lab Day 08, phạm vi đóng góp trực tiếp của tôi tập trung vào Sprint 2, với mục tiêu hoàn thiện baseline RAG từ retrieval đến generation. Cụ thể, tôi triển khai `retrieve_dense()` trong `rag_answer.py` để truy vấn ChromaDB local theo embedding, sau đó chuẩn hóa kết quả thành cấu trúc thống nhất gồm `text`, `metadata`, và `score` phục vụ cho bước generation. Tôi đồng thời hoàn thiện `call_llm()` theo cơ chế provider linh hoạt thông qua biến môi trường, nhằm đảm bảo pipeline có khả năng vận hành trong điều kiện thay đổi nhà cung cấp model. Ngoài ra, tôi bổ sung logic abstain khi không có bằng chứng phù hợp, giúp hệ thống ưu tiên tính an toàn thông tin thay vì sinh câu trả lời phán đoán. Những phần này kết nối trực tiếp kết quả indexing của Sprint 1 với hoạt động tuning và evaluation ở các sprint sau.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau khi thực hiện bài lab, tôi hiểu rõ hơn rằng retrieval là điểm quyết định chất lượng của toàn bộ RAG pipeline, không chỉ là bước tiền xử lý đơn thuần. Trong thực tế, nếu retrieval đưa vào context chưa đủ sát câu hỏi, model có xu hướng trả lời mơ hồ hoặc sai trọng tâm, dù prompt đã được thiết kế grounding. Tôi cũng nhận thấy giá trị của metadata nhất quán (`source`, `section`, `effective_date`) trong việc truy vết và giải thích kết quả: khi output sai, nhóm có thể khoanh vùng nhanh lỗi nằm ở retrieval hay generation. Bên cạnh đó, cơ chế abstain không phải yêu cầu phụ, mà là tiêu chí cốt lõi để hạn chế hallucination, đặc biệt với các câu hỏi ngoài phạm vi tài liệu. Đây là bài học quan trọng về tính tin cậy của hệ thống RAG trong bài toán trợ lý nội bộ.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất tôi gặp phải là khoảng cách giữa trạng thái "code chạy được" và "hệ thống đạt tiêu chí đánh giá". Ở giai đoạn đầu, pipeline có thể truy vấn và trả về source, nhưng câu trả lời vẫn có trường hợp thiếu citation hoặc chưa biểu đạt đúng mức độ chắc chắn khi context không đủ. Một trở ngại khác là vấn đề môi trường vận hành, bao gồm lỗi API key và sai lệch cấu hình provider, gây ảnh hưởng trực tiếp đến khả năng test end-to-end. Ban đầu, tôi giả thuyết rằng chỉ cần hoàn thành TODO là đạt Sprint 2; tuy nhiên, kết quả thực nghiệm cho thấy cần bổ sung guardrail và hậu kiểm output để đáp ứng đúng định nghĩa "grounded answer". Trải nghiệm này giúp tôi thay đổi cách làm: ưu tiên acceptance criteria từ sớm thay vì chỉ tập trung vào pass runtime.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** ERR-403-AUTH là lỗi gì?

**Phân tích:**

Câu hỏi này có giá trị đánh giá cao vì nó kiểm tra trực tiếp khả năng anti-hallucination của pipeline. Từ kết quả chạy thực tế, retrieval vẫn trả về một số chunk từ `support/helpdesk-faq.md` và `it/access-control-sop.md`, nhưng các chunk này không cung cấp bằng chứng trực tiếp về mã lỗi `ERR-403-AUTH`. Điều này cho thấy retrieval đang tìm được văn bản "gần nghĩa", nhưng chưa đạt mức exact-match cho đối tượng mã lỗi cụ thể. Trong bối cảnh này, nếu generation không bị ràng buộc nghiêm, model dễ đưa ra câu trả lời suy đoán dựa trên kiến thức ngoài context. Tuy nhiên, output quan sát được đã theo hướng abstain ("không tìm thấy thông tin"), phù hợp nguyên tắc grounding.

Xét về root-cause, lỗi chính (nếu xảy ra) có xu hướng nằm ở generation policy hơn là indexing: dữ liệu nguồn không chứa thông tin cần trả lời, nên hệ thống phải từ chối một cách rõ ràng. Vì vậy, với nhóm câu hỏi như gq07/gq tương tự, chiến lược đúng không phải tăng độ dài context, mà là cường hóa quy tắc abstain và citation để giảm tối đa rủi ro bịa thông tin.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ thử hai hướng cải tiến cụ thể. Thứ nhất, bổ sung post-check cho generation: nếu câu trả lời factual không có citation thì yêu cầu regenerate với context gọn hơn để tăng độ bám chứng cứ. Thứ hai, tiến hành benchmark riêng cho nhóm query có alias và mã lỗi để so sánh hệ thống dense và hybrid trên cùng bộ test, từ đó chọn retrieval strategy tối ưu cho giai đoạn grading. Hai hướng này có cơ sở trực tiếp từ kết quả chạy thực tế của nhóm.

