# Đánh giá câu hỏi tiếng Việt

Câu hỏi: hệ thống QA (agent mode, mặc định) trả lời câu hỏi tiếng Việt kém hơn câu hỏi tiếng Anh bao nhiêu, và kém ở câu nào?

**Cập nhật sau bước 2 (bảng thuật ngữ):** lỗi dịch duy nhất đã hết, tỉ lệ truy xuất trở về ngang tiếng Anh, và chênh lệch còn lại nằm trong vùng nhiễu. Hai lần chạy giống hệt nhau đã khác kết quả ở 11/45 câu dev. Xem mục "Bước 2".

**Kết luận ngắn (lần chạy đầu):** điểm câu có đáp án giảm từ **82,8% xuống 79,9%** (−3,0 điểm), câu ngoài phạm vi vẫn xử lý đúng **15/15**. So từng cặp, 17/82 câu đổi kết quả (10 câu tệ đi, 7 câu tốt lên). Mức dao động này gần bằng mức dao động giữa hai lần chạy tiếng Anh (14 câu đổi), nên phần lớn chênh lệch là nhiễu. Có **một lỗi chắc chắn do ngôn ngữ**: agent dịch "gia hộ" thành *household/butler* (fact-11). Ngoài ra có hai tín hiệu nhỏ nhưng cùng chiều: bằng chứng chuẩn lọt vào ngữ cảnh ít hơn 4 câu (68,7% → 62,7%), và câu multi-hop giảm nhiều nhất.

## Cách làm

- `data/eval/golden_set_vi.json` là bản sao của `golden_set.json` trong đó **chỉ dịch trường `question`**. Bản gốc được giữ ở `question_en` để đọc đối chiếu. `id`, `category`, `split`, `answer`, `key_points` và `evidence` giống hệt bản gốc (đã kiểm bằng script), nên không phải gán nhãn lại và chia dev/test không đổi. Cả 15 câu ngoài phạm vi cũng được dịch.
- Tên riêng giữ cách viết tiếng Anh (Subaru, Emilia, Rem, Ram, Beatrice, Petelgeuse…). Thuật ngữ dùng cách gọi quen thuộc của fan Việt: gia hộ, Kiếm Thánh, Kiếm Quỷ, Bạch Kình, Thánh Địa, Giáo phái Phù thủy, Tổng Giám mục Tội lỗi, và tên các tội Lười biếng, Tham lam, Phẫn nộ, Sắc dục, Bạo thực, Kiêu ngạo. Volume/Chapter đổi thành Tập/Chương. "Interlude" và tên truyện ngắn được giữ nguyên vì đó là nhãn chương trong sách.
- Hai lần chạy dùng cùng code (`25614b7`, `src` `887a5075a7d7`), cùng model `gemini-3.5-flash-lite`, cùng giám khảo và cùng cấu hình truy xuất. Giám khảo vẫn so câu trả lời với **đáp án tiếng Anh**.
  - EN: `20261005-005527-generation-lang-en`
  - VI: `20261005-012550-generation-lang-vi`
- Mức nhiễu tham chiếu: so lần chạy EN cũ `20261004-044909-generation-s6-agent-all-v2` với lần chạy EN mới. Lần chạy cũ dùng code cũ hơn (trước guard và follow-up), nên con số này phản ánh cả nhiễu của LLM lẫn thay đổi code. Hãy coi nó là mức tham khảo, không phải mức nhiễu thuần.

Lệnh chạy (trong container `backend`):

```
python -m src.eval generation --label lang-en --mode agent
python -m src.eval generation --label lang-vi --mode agent --golden data/eval/golden_set_vi.json
```

## Kết quả tổng

| | EN cũ (tham chiếu) | **EN** | **VI** | VI − EN |
|---|---|---|---|---|
| Điểm câu có đáp án (67 câu) | 79,1% | **82,8%** | **79,9%** | −3,0 |
| Đúng | 67,2% | 76,1% | 70,1% | −6,0 |
| Một phần | 23,9% | 13,4% | 19,4% | +6,0 |
| Sai | 1,5% | 4,5% | 3,0% | −1,5 |
| Từ chối nhầm | 7,5% | 6,0% | 7,5% | +1,5 |
| Bằng chứng chuẩn trong ngữ cảnh | 73,1% | 68,7% | 62,7% | −6,0 |
| Trung thực (được hỗ trợ) | 93,5% | 88,9% | 88,7% | −0,2 |
| Ngoài phạm vi xử lý đúng (15 câu) | 100% | 100% | 100% | 0 |
| Điểm dev (47) / test (20) | 79,8 / 77,5 | 81,9 / 85,0 | 80,9 / 77,5 | −1,0 / −7,5 |
| Gọi LLM/câu, token vào/ra | 3,1, 9689/136 | 3,2, 10789/143 | 3,2, 10295/182 | |

Điểm theo loại câu (EN → VI): fact 80,0 → 80,0; relationship 89,3 → 85,7; **multi_hop 88,9 → 72,2**; summary 77,8 → 77,8.

Số câu mỗi loại rất ít (multi_hop chỉ có 9 câu, test chỉ có 20 câu), nên mỗi câu đổi kết quả làm điểm nhảy 5–11 điểm. Không nên đọc các con số trên như một xu hướng chắc chắn.

## So từng cặp câu

| | Số câu đổi | Tệ đi | Tốt lên |
|---|---|---|---|
| EN → VI | 17/82 | 10 | 7 |
| EN cũ → EN mới (tham chiếu nhiễu) | 14/82 | 4 | 10 |

Số câu đổi kết quả khi đổi ngôn ngữ chỉ nhiều hơn một chút so với khi chạy lại tiếng Anh. Điểm khác là hướng đổi: khi đổi ngôn ngữ, câu tệ đi nhiều hơn câu tốt lên. Chỉ nhìn điểm trung bình (−3 điểm) sẽ che mất việc có 10 câu rớt.

### Câu tệ đi (EN → VI)

| Câu | Split | EN → VI | Nguyên nhân (đã đọc trace và câu trả lời) |
|---|---|---|---|
| fact-11 | dev | correct → **incorrect** | **Lỗi dịch.** Agent hiểu "gia hộ" là *household/butler*, tìm `Crusch Karsten butler household name` rồi `House of Karsten`, và trả lời "Gia hộ của Crusch là Nhà Karsten". Bản EN tìm `blessing divine protection` và trả lời đúng (wind reading). |
| fact-02 | dev | correct → refused | Query đúng (`"Return by Death" Subaru`, tìm 5 lần) nhưng agent vẫn từ chối. Đây là lỗi tìm/đọc, không phải lỗi dịch. |
| fact-35 | dev | correct → refused | Query hơi lệch ý (`why go cure Emilia memory Shaula`), bằng chứng không vào ngữ cảnh. Có thể do hiểu câu hỏi tiếng Việt. |
| multi-04 | dev | correct → refused | 6 lần tìm về cái chết của Theresia nhưng không tìm ra đoạn cần. Bản EN cũng không có bằng chứng trong ngữ cảnh mà vẫn trả lời đúng. |
| fact-19 | test | correct → partial | Thiếu ý "bất tỉnh khi chạm vào kết giới". Bằng chứng không có trong ngữ cảnh ở cả hai lần. |
| fact-23 | dev | correct → partial | Gán nhầm việc đẩy Regulus xuống nước cho Emilia, thiếu vai trò của Reinhard. Ý "chết đuối" vẫn đúng. |
| multi-06 | test | correct → partial | Tìm 4 lần về Julius nhưng không ra đoạn nói Julius chỉ bị ăn tên. |
| multi-08 | dev | correct → partial | Nêu đúng Sirius bị bắt nhưng không nói Regulus đã chết. |
| rel-07 | dev | correct → partial | Thiếu ý "Julius chỉ biết vì Subaru kể lại". |
| sum-06 | test | correct → partial | Thiếu mục đích chuyến đi, tuyến đường bí mật và chi tiết Reid đánh bằng đũa. |

### Câu tốt lên (EN → VI)

fact-01 và fact-34 (refused → correct), fact-16 và fact-09 (incorrect → correct/partial), fact-20, multi-09 và sum-03 (partial → correct).

fact-01, fact-09 và fact-34 cũng là những câu đổi kết quả giữa hai lần chạy EN. Đây là các câu kết quả không ổn định ngay cả khi không đổi ngôn ngữ.

### Ngoài phạm vi

Cả hai lần đều xử lý đúng 15/15. Chỉ có cách xử lý đổi: oos-08 và oos-15 chuyển từ "chỉ ra tiền đề sai" sang "từ chối", còn oos-10 đổi theo chiều ngược lại. Không câu nào bị bịa câu trả lời.

## Đọc tay: giám khảo có chấm sai vì khác ngôn ngữ không?

Đã đọc 18 câu trả lời tiếng Việt cùng nhận xét của giám khảo: cả 7 câu correct → partial/incorrect, và 11 câu khác gồm cả câu được chấm correct lẫn partial (fact-01, 07, 09, 13, 20, 31, 34, rel-05, rel-13, multi-02, sum-04).

- **Không thấy câu nào bị trừ điểm vì viết bằng tiếng Việt.** Mỗi câu partial đều thiếu thật một key point khi đối chiếu với đáp án tiếng Anh, và giám khảo nêu đúng ý bị thiếu.
- **Không thấy giám khảo chấm dễ sai.** Các câu correct có đủ key point (vd. fact-20 nêu đủ ba thử thách, multi-02 nêu đủ năm tội). Thuật ngữ dịch như "Bạo thực"/"Phàm ăn" và "Thợ săn nội tạng" được giám khảo khớp đúng với Gluttony và Bowel Hunter.
- **Vấn đề nhỏ:** 17/82 nhận xét của giám khảo được viết bằng tiếng Việt, vì prompt chấm không quy định ngôn ngữ cho phần giải thích. Verdict không bị ảnh hưởng, nhưng cột nhận xét trong report bị trộn hai ngôn ngữ.

## Đọc tay: bản dịch

Đã rà 17 câu nhiều tên riêng và thuật ngữ nhất (fact-01, 10, 12, 15, 22, 24, 26, 27, 35, rel-02, 05, 10, multi-02, 07, sum-09, oos-08, 14) bằng cách đặt cạnh bản gốc. Không có tên riêng nào bị dịch sai. Mỗi câu dịch giữ đúng các ràng buộc của câu gốc (tập, chương, tiền đề sai của câu ngoài phạm vi).

Agent dịch truy vấn sang tiếng Anh ở 167/170 lần tìm kiếm. Ba lần còn giữ tiếng Việt đều ở oos-11 (`Puck khế ước Subaru Emilia`). Câu này vẫn được từ chối đúng.

## Phát hiện khác

- **Câu từ chối vẫn là tiếng Anh.** Cả 63 câu có trả lời đều viết bằng tiếng Việt, nhưng 19 câu từ chối đều là nguyên văn `Not found in the provided passages.` Agent phải trả đúng chuỗi này thì hệ thống mới nhận ra đó là từ chối (`found`), nên người dùng hỏi tiếng Việt sẽ nhận câu từ chối bằng tiếng Anh.
- Câu trả lời tiếng Việt dài hơn (trung bình 182 token ra so với 143). Token vào và số lần gọi LLM gần như không đổi.
- Hash bộ câu hỏi của lần chạy EN mới (`9ea32464c642`) khác với các lần chạy cũ (`abd3887b94c3`) dù nội dung giống hệt. Lý do là trên Windows, Git checkout file với xuống dòng CRLF. Hệ quả: `regress` không ghép được các lần chạy cũ với lần chạy mới.

## Bước 2: bảng thuật ngữ Việt → Anh trong prompt agent

Prompt agent (`src/services/agent.py`, `GLOSSARY`) có thêm 34 cặp thuật ngữ: gia hộ = divine protection/blessing, Bạch Kình = White Whale, Thánh Địa = Sanctuary, Kiếm Thánh = Sword Saint, Tổng Giám mục = Archbishop, tên bảy tội, v.v.

Bảng chỉ chứa thuật ngữ, không chứa sự kiện. Mục "Tử Vong Hồi Quy = Return by Death" bị bỏ vì nó chính là đáp án của fact-02. Bảng cũng được loại khỏi bộ phát hiện lộ prompt (`guard.leaks_prompt`), để câu trả lời liệt kê các tội kèm tên tiếng Anh không bị chặn nhầm (có test riêng).

Các lần chạy, cùng code và cùng prompt:

- G1 `20261005-023444-generation-lang-vi-glossary-dev`: chạy trên dev để tinh chỉnh. Khi `--resume`, do lỗi harness, run này **chạy luôn cả test** (`--resume` bỏ qua `--only`; lỗi đã được sửa). Phần test của G1 không được dùng khi quyết định.
- G2 `20261005-030534-generation-lang-vi-glossary`: lần chạy thứ hai để tách nhiễu và xác nhận trên test. Run này dừng ở 64/82 câu vì hết quota ngày của gói miễn phí (500 lượt). Còn thiếu sum-07, sum-08, sum-09 và 15 câu ngoài phạm vi; chạy tiếp được bằng `--resume`.

Các số dưới đây chỉ tính 64 câu có đáp án mà cả bốn lần chạy đều có kết quả (45 dev, 19 test):

| | EN | VI | VI + bảng (G1) | VI + bảng (G2) |
|---|---|---|---|---|
| Điểm dev (45) | 82,2% | 81,1% | 86,7% | 84,4% |
| Điểm test (19) | 86,8% | 78,9% | (78,9%)\* | 81,6% |
| Bằng chứng chuẩn trong ngữ cảnh | 43/64 | 40/64 | 43/64 | 43/64 |
| Từ chối nhầm / sai | 4 / 3 | 5 / 2 | 2 / 3 | 2 / 3 |
| Truy vấn tìm kiếm còn tiếng Việt | – | 3/170 | 1/179 | 0/140 |

\* Phần test của G1 là ngoài ý muốn, ghi lại để đủ dữ liệu.

**Nhiễu lớn hơn chênh lệch cần đo.** G1 và G2 cùng code, cùng prompt, nhưng khác kết quả ở **11/45 câu dev**. Với mức dao động này, một lần chạy đơn lẻ không phân biệt được chênh lệch 3–5 điểm. Vì vậy kết luận dưới đây dựa trên các câu cho **cùng kết quả ở cả hai lần chạy**:

- **Câu đúng ở EN nhưng rớt ở cả G1 lẫn G2:** chỉ có 3 câu, đều là partial vì thiếu một ý: fact-06 (dev, thiếu "ví tiền"), fact-19 (test, thiếu "bất tỉnh khi chạm kết giới") và sum-06 (test, thiếu mục đích và tuyến đường). Trace cho thấy query của cả ba đều là tiếng Anh đúng ý. Fact-19 và sum-06 cũng đã partial ở lần chạy VI đầu tiên, nên đây là hai ứng viên đáng xem nếu muốn tìm lỗi riêng của tiếng Việt.
- **Câu sai ở EN nhưng đúng ở cả G1 lẫn G2:** cũng 3 câu (fact-01, fact-16, fact-20). Tính theo cách đếm này, sau khi có bảng thuật ngữ thì chênh lệch do ngôn ngữ xấp xỉ 0.
- **fact-11**, lỗi dịch duy nhất ở lần chạy đầu, đã hết: cả hai lần đều tìm `Crusch Karsten divine protection`. G2 trả lời đúng (wind reading); G1 từ chối vì không tìm ra đoạn cần, tức là không còn trả lời sai.
- Trong 10 câu rớt ở lần chạy VI đầu tiên, 7 câu đúng ở ít nhất một lần chạy có bảng thuật ngữ.
- Tỉ lệ bằng chứng lọt vào ngữ cảnh trở về đúng mức của EN (43/64 ở cả hai lần, so với 40/64 khi chưa có bảng). Agent không còn tìm kiếm bằng tiếng Việt.
- Câu ngoài phạm vi: G1 xử lý đúng 15/15 với prompt mới. G2 chưa chạy tới phần này.

**Kết luận:** bảng thuật ngữ sửa được lỗi dịch duy nhất đã thấy và đưa khả năng truy xuất của câu hỏi tiếng Việt về ngang tiếng Anh. Trên test, điểm vẫn thấp hơn EN khoảng 5 điểm, nhưng mức này nằm trong vùng nhiễu: chỉ 2 câu test (fact-19, sum-06) rớt ổn định.

**Chưa kiểm:** prompt mới chưa được chạy lại với bộ câu tiếng Anh. Bảng thuật ngữ không nên ảnh hưởng câu tiếng Anh, nhưng prompt đã đổi, nên cần một lần chạy EN (khoảng 330 lượt) để chắc chắn không có hồi quy.

## Đề xuất

1. ~~Thêm bảng thuật ngữ vào prompt agent.~~ Đã làm, xem phần trên.
2. Khi quota hồi:
   - Chạy tiếp G2 bằng `--resume` để đủ 82 câu, khoảng 70 lượt.
   - Chạy bộ tiếng Anh với prompt mới để kiểm hồi quy.
3. **Mỗi so sánh nên chạy ít nhất 2 lần.** Mức dao động 11/45 câu giữa hai lần chạy giống hệt nhau lớn hơn hầu hết các thay đổi đang muốn đo. Cũng có thể hạ `LLM_TEMPERATURE` (đang là 0,2) khi chạy eval.
4. **Trả câu từ chối theo ngôn ngữ của câu hỏi** ở phía API: vẫn nhận diện bằng chuỗi `NOT_FOUND`, nhưng hiển thị cho người dùng bản tiếng Việt.
5. Thêm vào prompt giám khảo yêu cầu viết phần `explanation` bằng tiếng Anh, để report đồng nhất.
6. Thêm `*.json text eol=lf` vào `.gitattributes` để hash của bộ câu hỏi không phụ thuộc hệ điều hành. Sau đó cần chạy lại baseline.

## Thay đổi trong code

- `python -m src.eval retrieval|generation --golden FILE`: chạy trên file câu hỏi khác có cùng id. Đường dẫn file được ghi vào `golden_set.path` của mỗi lần chạy, và `--resume` tự dùng lại file mà lần chạy đó đã bắt đầu. Danh sách `--only` được lưu trong header và cũng được `--resume` dùng lại.
- `src/services/agent.py`: thêm `GLOSSARY` vào prompt agent. `src/services/guard.py` loại bảng này khỏi bộ phát hiện lộ prompt.
- `eval_report.md`: các lần chạy trên file câu hỏi khác được liệt kê ở mục riêng "Bộ câu hỏi khác", để không lẫn với các bảng so sánh trên `golden_set.json`.
