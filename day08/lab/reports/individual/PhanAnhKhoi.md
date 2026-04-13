# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phan Anh Khôi
**Vai trò trong nhóm:** Eval Owner
**Ngày nộp:** 13/04.2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm? 
Tôi chủ yếu làm sprint 2 và sprint 4, chịu trách nhiệm xử lý luồng RAG trong rag_answer.py và evaluation trong eval.py.
> - Cụ thể bạn implement hoặc quyết định điều gì?
Tôi đã implement toàn bộ các hàm tính scorecard và a/b testing trong eval.py, implement phần rerank và chọn embedding model trong rag_answer.py.
> - Công việc của bạn kết nối với phần của người khác như thế nào?
Tôi tạo ra các module trong eval.py để test kết quả Retrieval Owner tạo ra trong rag_answer.py bằng 4 metrics. Tôi cũng phụ trách tạo reranker để xếp lại thứ tự các doc retrieve được bởi code của Retrieval Owner. Khi hoàn thành, Tech Lead merge code của tôi vào hệ thống.

_________________

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

Sau khi làm bài lab, tôi đã thực sự hiểu rõ hơn về A/B testing, thuật ngữ tôi đã thấy nhiều trong JD nhưng chưa từng thử trước đây. A/B testing là thử thay đổi từng tham số một và quan sát xem có cải thiện hay không. Nếu phiên bản thay đổi tốt hơn baseline, nó được chấp nhận, không thì reject; chúng ta sẽ không thay đổi nhiều tham số một lúc rồi quan sát hiệu quả vì điều đó làm rất khó đánh giá tác động của từng tham số.

_________________

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Lỗi mất nhiều thời gian debug nhất là một số lỗi xuất hiện khi làm việc với git. Khi cố gắng pull request, tôi không rõ cú pháp và đã pull request nhầm lên repo đề bài. Sau đó, tôi cũng gặp một số vấn đề liên quan đến merge code. Phải mất đến 30 phút để tôi hoàn thành pull request.

_________________

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** 
q07: Approval Matrix để cấp quyền hệ thống là tài liệu nào?

**Phân tích:**
Câu hỏi yêu cầu phải retrieve đúng từ khóa Approval Matrix. Nếu chỉ sử dụng dense, kết quả trả ra không đủ tốt, tài liệu có thông tin không nằm trong top 3 và cosine similarity mặt bằng chung là rất thấp. Giải pháp là hybrid search với BM25 để cải thiện khả năng match từ khóa. Variant có cải thiện, doc có chứa thông tin liên quan là top 1 với similarity cao.
_________________

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Tôi sẽ thử X vì kết quả eval cho thấy Y."
Nếu có thêm thời gian, tôi sẽ thử các chiến thuật cải thiện query, như multiquery hay HyDE giúp query match tốt hơn với tài liệu có sẵn, cải thiện khả năng retrieve. Tôi cũng muốn thử đặt threshold (không chấp nhận các docs có similarity thấp hơn một mức nào đó) để cải thiện tốt hơn khả năng handle những tài liệu không có trong database.

_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
