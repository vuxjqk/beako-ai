# Giai đoạn 5: thử nghiệm truy xuất

Mỗi dòng là một lần `python -m src.eval retrieval --set ...` (dữ liệu trong `data/eval/runs/`). Quyết định dựa
trên **dev** (47 câu); **test** (20 câu, chọn bằng hash id) chỉ được xem một lần ở cuối để xác nhận.

| Thử nghiệm | dev Hit@6 | dev Hit@20 | dev MRR | ms/câu | Quyết định |
|---|---|---|---|---|---|
| Baseline: vector (HNSW) | 42.5% | 51.1% | 0.245 | 37 | |
| Vector tìm chính xác (không index) | 42.5% | 51.1% | 0.244 | 86 | Bỏ: HNSW không làm mất gì |
| Chỉ từ khóa, Postgres full-text (OR các từ) | 25.5% | 40.4% | 0.146 | 116 | Bỏ: `ts_rank` không có IDF, tên phổ biến lấn át |
| Chỉ từ khóa, BM25 trong bộ nhớ | 36.2% | 55.3% | 0.209 | 16 | |
| Lai vector + full-text (RRF) | 34.0% | 57.5% | 0.271 | 157 | Bỏ |
| **Lai vector + BM25 (RRF k=60)** | 42.5% | 61.7% | 0.287 | 52 | **Giữ** |
| + lọc theo tập/chương nêu trong câu (filter) | 44.7% | 70.2% | 0.310 | 52 | |
| **+ ưu tiên tập/chương nêu trong câu (boost)** | 46.8% | 70.2% | 0.307 | 84 | **Giữ**: như filter nhưng không loại hẳn tập khác (câu nhiều phần như multi-03 cần cả tập khác) |
| + rerank `ms-marco-MiniLM-L-6` top 20 | 42.5% | 70.2% | 0.287 | 2 628 | Bỏ: tệ hơn, chậm |
| + rerank `ms-marco-MiniLM-L-12` top 20 | 42.5% | 70.2% | 0.264 | 4 675 | Bỏ |
| + rerank `jina-reranker-v1-tiny-en` top 20 | 42.5% | 70.2% | 0.298 | 2 245 | Bỏ |
| + rerank `jina-reranker-v1-turbo-en` top 20 | 36.2% | 70.2% | 0.232 | 3 215 | Bỏ |
| + rerank `bge-reranker-base` top 20 | 53.2% | 70.2% | 0.366 | 16 206 | Tốt nhưng 16 giây/câu trên CPU: để dành cho máy GPU (`RETRIEVAL_RERANK=BAAI/bge-reranker-base`) |
| **+ 100 ứng viên mỗi nguồn trước khi hợp nhất** | 48.9% | 74.5% | 0.312 | 113 | **Giữ** |
| + 200 ứng viên | 48.9% | 74.5% | 0.310 | 118 | Không thêm gì |

Cấu hình mặc định mới (`src/core/config.py`): `RETRIEVAL_METHOD=hybrid`, `RETRIEVAL_SCOPE=boost`,
`RETRIEVAL_CANDIDATES=100`, không rerank. Chạy lại hai lần cho cùng vân tay `06ed734073814dfd`.

## Xác nhận trên test và trên câu trả lời

| | Hit@6 | Hit@20 | MRR | Điểm câu trả lời |
|---|---|---|---|---|
| dev, baseline | 42.5% | 51.1% | 0.245 | 50.0% |
| dev, cấu hình mới | 48.9% | 74.5% | 0.312 | 55.3% |
| test, baseline | 55.0% | 75.0% | 0.333 | 47.5% |
| test, cấu hình mới | 55.0% | 70.0% | 0.454 | 62.5% |

Toàn bộ 67 câu: điểm câu trả lời 49.2% → 57.5%, từ chối nhầm 32.8% → 25.4%, trung thực 100%, câu ngoài phạm
vi vẫn 15/15. Trên test, Hit@20 giảm một câu (fact-19 rơi từ hạng 7 xuống 25) nhưng MRR và điểm câu trả lời
tăng rõ; n=20 nên mỗi câu là 5 điểm phần trăm.

## Còn yếu (để giai đoạn 6)

- Multi-hop: dev Hit@6 33% → 17% (ba câu), điểm câu trả lời multi-hop 22% → 28%. Một lần tìm không gom đủ các
  đoạn ở nhiều tập; BM25 với các từ chung ("witches", "sin") còn kéo multi-07 xuống.
- Summary: điểm 33% → 28%, chưa câu nào "đúng". Cần tìm nhiều lần hoặc chỉ mục tóm tắt theo chương.
- Lọc/ưu tiên theo tập dựa vào việc câu hỏi ghi rõ "Volume N"; bộ câu hỏi ghi điều này thường hơn người dùng thật,
  nên mức cải thiện ngoài thực tế sẽ thấp hơn phần đóng góp của bước này (Hit@20 dev 61.7% → 70.2%).
