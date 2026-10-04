# Giai đoạn 6: agent

Agent (`src/services/agent.py`) có bốn công cụ trên cùng hệ truy xuất của giai đoạn 5: `search` (lọc theo tập,
chương, tuyển tập truyện ngắn), `read_around`, `list_chapters`, `read_chapter` (đọc từng trang 5 đoạn). Giới hạn 6
lần gọi mô hình và 40 000 token ngữ cảnh; hết giới hạn thì buộc trả lời (`tool_choice: none`). Mỗi lần gọi công cụ
và số token được ghi vào `trace` của câu trả lời và của kết quả đánh giá.

## Kết quả (82 câu, `gemini-3.5-flash-lite`, giám khảo cùng mô hình)

| Chế độ | fact | relationship | multi_hop | summary | dev | test | Ngoài phạm vi | Gọi LLM/câu | Token vào/câu | Thời gian/câu |
|---|---|---|---|---|---|---|---|---|---|---|
| simple (giai đoạn 5) | 64.3% | 78.6% | 27.8% | 27.8% | 55.3% | 62.5% | 15/15 | 1 | 2 342 | 1.6 s |
| **agent cho mọi câu** | **84.3%** | **89.3%** | **72.2%** | **50.0%** | **79.8%** | **77.5%** | 15/15 | 3.1 | 9 689 | 6.4 s |
| auto: định tuyến theo câu hỏi (mô phỏng) | 64.3% | 78.6% | 44.4% | 50.0% | 58.5% | 72.5% | 15/15 | 1.4 | 4 079 | 2.6 s |
| auto: simple, từ chối thì chuyển agent (mô phỏng) | 80.0% | 78.6% | 55.6% | 55.6% | 73.4% | 72.5% | 15/15 | 2.3 | 6 779 | 4.4 s |
| auto: định tuyến + chuyển khi từ chối (mô phỏng) | 80.0% | 78.6% | 66.7% | 50.0% | 72.3% | 77.5% | 15/15 | 2.6 | 8 025 | 5.1 s |

Điểm = đúng + 0,5 × một phần. Các dòng "mô phỏng" ghép kết quả từng câu của hai lần chạy thật (simple và agent) theo
chính sách, không gọi LLM thêm (`python -m src.eval combine`).

- Từ chối nhầm: 25.4% → 7.5%. Bằng chứng chuẩn có trong những gì mô hình đọc: 50.7% → 73.1%.
- Trung thực: 93.5% câu trả lời được đoạn trích hỗ trợ hoàn toàn, 6.5% một phần, 0% không được hỗ trợ (simple:
  100%). Câu ngoài phạm vi vẫn 15/15, và với tiền đề sai agent nói rõ tiền đề sai thay vì chỉ "không tìm thấy".
- Chỉ 3/67 câu tệ hơn simple: fact-16, rel-10, sum-02.
- Agent dùng 2–3 lần gọi cho phần lớn câu; 10/82 câu chạm giới hạn 6 bước và bị buộc trả lời. Công cụ được gọi:
  `search` 170 lần, `list_chapters` 13, `read_chapter` 7.
- Bộ định tuyến bằng biểu thức (tóm tắt, so sánh, thay đổi, liệt kê, tiếng Việt) không gửi câu dễ nào sang agent,
  nhưng chỉ bắt được 4/9 câu multi-hop; câu nhiều vế ("Ai ngăn cô ấy… và ai giết cô ấy") lọt qua.

## Quyết định

Đạt điều kiện: summary 27.8% → 50.0%, multi-hop 27.8% → 72.2%, và nhóm câu dễ không tệ đi mà tăng (fact +20, relationship
+11 điểm). Vì agent cho mọi câu tốt hơn mọi chính sách lai trong khi chính sách lai tốt nhất chỉ bớt khoảng 16% số lần
gọi, mặc định là `QA_MODE=agent`. Nếu cần tiết kiệm quota: `QA_MODE=auto` + `QA_ESCALATE=true` (2.3 lần gọi/câu, điểm
73%). `QA_MODE=simple` giữ đường cũ.

Chi phí: khoảng 3 lần gọi và 10 000 token vào mỗi câu, tức gói Gemini free (500 lần gọi/ngày cho flash-lite) đủ khoảng
150 câu/ngày thay vì 500. Thời gian trả lời trung bình 6.4 giây, nên giao diện hỏi đáp (chưa có) cần hiển thị trạng thái
đang xử lý.

Tiếng Việt: câu hỏi tiếng Việt được định tuyến sang agent, agent tự dịch truy vấn sang tiếng Anh và trả lời bằng tiếng
Việt (thử tay ba câu: hai câu trả lời đúng có nguồn, câu tiền đề sai được từ chối). Chưa có câu tiếng Việt trong bộ
đánh giá.

## Còn yếu

- Summary mới 50%: agent hiếm khi đọc cả chương (7 lần `read_chapter` cho 9 câu tóm tắt) và vẫn thiếu ý so với đáp án.
  Chỉ mục tóm tắt theo chương (tạo một lần, khoảng 200 phần truyện) là bước tiếp theo hợp lý; tốn khoảng 200 lần gọi
  LLM với đầu vào dài, nên chạy trên gói trả phí.
- Trung thực giảm nhẹ (4 câu chỉ được hỗ trợ một phần) vì agent tổng hợp từ nhiều đoạn hơn.
- Giám khảo là chính flash-lite; các số trên nên được xem là tương đối giữa các chế độ.
