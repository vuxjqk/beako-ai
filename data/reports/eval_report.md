# Báo cáo đánh giá

Tạo bởi `python -m src.eval report` từ mọi lần chạy trong `data/eval/runs/`. Bộ câu hỏi: `data/eval/golden_set.json`, 82 câu (fact 35, relationship 14, multi_hop 9, summary 9, out_of_scope 15).

Cách chạy (trong container `backend`):

```
python -m src.eval retrieval --label <mô tả thay đổi>   # nhanh, không tốn quota: chạy sau mỗi thay đổi
python -m src.eval generation --label <mô tả>           # gọi LLM: chạy khi cần
python -m src.eval report                               # dựng lại báo cáo này
```

## Giới hạn của phép đo

- Vị trí bằng chứng không vét cạn: một sự kiện nhắc lại ở nhiều tập (vd. Puck là tinh linh của Emilia) có thể được trả lời đúng từ đoạn khác. Câu "Đúng" nằm ở hàng "bằng chứng KHÔNG có trong ngữ cảnh" là dấu hiệu nên bổ sung vị trí vào bộ câu hỏi; chỉ số truy xuất vì vậy là cận dưới.
- Giám khảo mặc định là chính mô hình sinh câu trả lời, nên có thể dễ dãi với chính nó; khi so sánh mô hình, giữ cố định `--judge-model`. Với bộ nhỏ, đọc cột nhận xét để kiểm tra lại.
- Span recall coi mọi vị trí của một câu là bắt buộc; với câu có vị trí thay thế (multi-06), Hit@k phản ánh đúng hơn.
- Đổi bộ câu hỏi làm đổi `golden_set.sha256`; chỉ so sánh các lần chạy cùng hash.

## Truy xuất

Không gọi LLM. Một chunk được coi là đúng khi khoảng đoạn văn của nó giao với một vị trí bằng chứng (cùng tập). Hit@k: có chunk đúng trong top k. MRR: trung bình 1/hạng của chunk đúng đầu tiên (0 nếu không có trong top độ sâu). Span recall@20: tỉ lệ vị trí bằng chứng của câu hỏi được phủ trong top 20 (câu nhiều phần cần đủ mọi phần). All spans@20: tỉ lệ câu được phủ đủ mọi phần.

Chỉ số được tách theo split: **dev** dùng để chọn cấu hình, **test** chỉ để xác nhận thay đổi đã chọn (không tinh chỉnh theo test).

| Lần chạy | Nhãn | Commit / mã `src` | Cấu hình truy xuất | Chunker (số chunk) | dev Hit@6 | dev Hit@20 | dev MRR | dev Span recall@20 | test Hit@6 | test Hit@20 | test MRR | ms/câu | Vân tay kết quả |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261004-021808-retrieval-baseline-vector | baseline-vector | `f88f8c1` / `0299fd135dac` | `vector` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 42.5% | 51.1% | 0.245 | 42.7% | 55.0% | 75.0% | 0.333 | 49.3 | `e8a5152d5039bcc5` |
| 20261004-021815-retrieval-baseline-vector-repeat | baseline-vector-repeat | `f88f8c1` / `0299fd135dac` | `vector` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 42.5% | 51.1% | 0.245 | 42.7% | 55.0% | 75.0% | 0.333 | 36.3 | `e8a5152d5039bcc5` |
| 20261004-023106-retrieval-baseline-vector-final-code | baseline-vector-final-code | `f88f8c1` / `55b9eb5eb3d4` | `vector` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 42.5% | 51.1% | 0.245 | 42.7% | 55.0% | 75.0% | 0.333 | 44.6 | `e8a5152d5039bcc5` |
| 20261004-024425-retrieval-s5-baseline | s5-baseline | `918b630` / `26fdc1345ee3` | `vector` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 42.5% | 51.1% | 0.245 | 42.7% | 55.0% | 75.0% | 0.333 | 36.9 | `e8a5152d5039bcc5` |
| 20261004-024437-retrieval-s5-exact_true | s5-exact_true | `918b630` / `26fdc1345ee3` | `vector exact=True` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 42.5% | 51.1% | 0.244 | 42.7% | 55.0% | 75.0% | 0.333 | 86.0 | `6d6a5e61b71fb295` |
| 20261004-024448-retrieval-s5-method_keyword-keyword_bm25 | s5-method_keyword-keyword_bm25 | `918b630` / `26fdc1345ee3` | `keyword` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 36.2% | 55.3% | 0.209 | 43.2% | 50.0% | 75.0% | 0.253 | 15.9 | `4db861300df3ff28` |
| 20261004-024454-retrieval-s5-method_keyword-keyword_ts | s5-method_keyword-keyword_ts | `918b630` / `26fdc1345ee3` | `keyword keyword=ts` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 25.5% | 40.4% | 0.146 | 29.6% | 20.0% | 45.0% | 0.112 | 116.2 | `ae67b9760a4ea7fd` |
| 20261004-024509-retrieval-s5-method_hybrid-keyword_bm25 | s5-method_hybrid-keyword_bm25 | `918b630` / `26fdc1345ee3` | `hybrid` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 42.5% | 61.7% | 0.287 | 50.9% | 55.0% | 75.0% | 0.405 | 56.0 | `79019ae6306c0cb3` |
| 20261004-024517-retrieval-s5-method_hybrid-keyword_ts | s5-method_hybrid-keyword_ts | `918b630` / `26fdc1345ee3` | `hybrid keyword=ts` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 34.0% | 57.5% | 0.271 | 45.5% | 40.0% | 70.0% | 0.260 | 157.4 | `83281a676293c81d` |
| 20261004-024716-retrieval-s5-method_hybrid | s5-method_hybrid | `918b630` / `a74908051339` | `hybrid` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 42.5% | 61.7% | 0.287 | 50.9% | 55.0% | 75.0% | 0.405 | 51.8 | `79019ae6306c0cb3` |
| 20261004-024726-retrieval-s5-method_hybrid-scope_filter | s5-method_hybrid-scope_filter | `918b630` / `a74908051339` | `hybrid scope=filter` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 44.7% | 70.2% | 0.310 | 59.4% | 55.0% | 75.0% | 0.431 | 52.3 | `90221820ec627462` |
| 20261004-024736-retrieval-s5-method_hybrid-scope_boost | s5-method_hybrid-scope_boost | `918b630` / `a74908051339` | `hybrid scope=boost` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 46.8% | 70.2% | 0.307 | 59.4% | 55.0% | 75.0% | 0.456 | 83.5 | `d9a076061fcafbe0` |
| 20261004-024816-retrieval-s5-hybrid-boost-rerank-ms-marco-MiniLM-L-6-v2 | s5-hybrid-boost-rerank-ms-marco-MiniLM-L-6-v2 | `918b630` / `a74908051339` | `hybrid scope=boost rerank=Xenova/ms-marco-MiniLM-L-6-v2` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 42.5% | 70.2% | 0.287 | 59.4% | 60.0% | 75.0% | 0.422 | 2627.7 | `b8df77b9a7568a8c` |
| 20261004-025141-retrieval-s5-hybrid-boost-rerank-ms-marco-MiniLM-L-12-v2 | s5-hybrid-boost-rerank-ms-marco-MiniLM-L-12-v2 | `918b630` / `a74908051339` | `hybrid scope=boost rerank=Xenova/ms-marco-MiniLM-L-12-v2` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 42.5% | 70.2% | 0.264 | 59.4% | 55.0% | 75.0% | 0.409 | 4675.1 | `566ad48af8255503` |
| 20261004-025900-retrieval-s5-hybrid-boost-rerank-bge-base | s5-hybrid-boost-rerank-bge-base | `918b630` / `a74908051339` | `hybrid scope=boost rerank=BAAI/bge-reranker-base` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 53.2% | 70.2% | 0.366 | 59.4% | 60.0% | 75.0% | 0.441 | 16205.9 | `1c82988f1612c2d7` |
| 20261004-031744-retrieval-s5-hybrid-boost-rerank-jina-reranker-v1-tiny-en | s5-hybrid-boost-rerank-jina-reranker-v1-tiny-en | `918b630` / `2735d3152870` | `hybrid scope=boost rerank=jinaai/jina-reranker-v1-tiny-en` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 42.5% | 70.2% | 0.298 | 59.4% | 60.0% | 75.0% | 0.446 | 2245.1 | `667259dc7036518f` |
| 20261004-032036-retrieval-s5-hybrid-boost-rerank-jina-reranker-v1-turbo-en | s5-hybrid-boost-rerank-jina-reranker-v1-turbo-en | `918b630` / `2735d3152870` | `hybrid scope=boost rerank=jinaai/jina-reranker-v1-turbo-en` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 36.2% | 70.2% | 0.232 | 59.4% | 60.0% | 75.0% | 0.408 | 3215.1 | `45aedf8a2f72f69c` |
| 20261004-032426-retrieval-s5-hybrid-boost-cand100 | s5-hybrid-boost-cand100 | `918b630` / `2735d3152870` | `hybrid candidates=100 scope=boost` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 48.9% | 74.5% | 0.312 | 62.0% | 55.0% | 70.0% | 0.454 | 113.0 | `06ed734073814dfd` |
| 20261004-032445-retrieval-s5-hybrid-boost-cand200 | s5-hybrid-boost-cand200 | `918b630` / `2735d3152870` | `hybrid candidates=200 scope=boost` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 48.9% | 74.5% | 0.310 | 61.3% | 55.0% | 75.0% | 0.453 | 117.7 | `e885f0b9f5e41884` |
| 20261004-032513-retrieval-s5-final | s5-final | `918b630` / `11543d3f548c` | `hybrid candidates=100 scope=boost` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 48.9% | 74.5% | 0.312 | 62.0% | 55.0% | 70.0% | 0.454 | 98.3 | `06ed734073814dfd` |
| 20261004-032527-retrieval-s5-final-repeat | s5-final-repeat | `918b630` / `11543d3f548c` | `hybrid candidates=100 scope=boost` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 48.9% | 74.5% | 0.312 | 62.0% | 55.0% | 70.0% | 0.454 | 125.7 | `06ed734073814dfd` |
| 20261004-052529-retrieval-s7-regression-check | s7-regression-check | `be8eb11` / `c92a2c822e9c` | `hybrid candidates=100 scope=boost` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 48.9% | 74.5% | 0.312 | 62.0% | 55.0% | 70.0% | 0.454 | 102.0 | `06ed734073814dfd` |
| 20261005-045129-retrieval-baseline-lf | baseline-lf | `e008c7d` / `d4a5057c4267` | `hybrid candidates=100 scope=boost` | `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457) | 48.9% | 74.5% | 0.312 | 62.0% | 55.0% | 70.0% | 0.454 | 83.9 | `06ed734073814dfd` |

Embedding: `BAAI/bge-small-en-v1.5`. Mã `src` là hash của mọi file `src/**/*.py` lúc chạy, nên phân biệt được cả thay đổi chưa commit.

### Kiểm tra tính lặp lại

- 2 lần chạy cùng cấu hình (20261004-021808-retrieval-baseline-vector, 20261004-021815-retrieval-baseline-vector-repeat): kết quả giống hệt nhau ✅
- 2 lần chạy cùng cấu hình (20261004-032513-retrieval-s5-final, 20261004-032527-retrieval-s5-final-repeat): kết quả giống hệt nhau ✅

### Theo loại câu hỏi — 20261005-045129-retrieval-baseline-lf

| Split | Loại | n | Hit@6 | Hit@20 | MRR | Span recall@6 | Span recall@20 | All spans@20 |
|---|---|---|---|---|---|---|---|---|
| dev | fact | 25 | 64.0% | 84.0% | 0.439 | 53.3% | 81.3% | 80.0% |
| dev | relationship | 10 | 40.0% | 70.0% | 0.171 | 35.0% | 60.0% | 50.0% |
| dev | multi_hop | 6 | 16.7% | 50.0% | 0.054 | 5.6% | 13.9% | 0.0% |
| dev | summary | 6 | 33.3% | 66.7% | 0.276 | 15.3% | 32.9% | 16.7% |
| dev | overall | 47 | 48.9% | 74.5% | 0.312 | 38.5% | 62.0% | 55.3% |
| test | fact | 10 | 70.0% | 70.0% | 0.530 | 53.3% | 53.3% | 40.0% |
| test | relationship | 4 | 50.0% | 50.0% | 0.375 | 37.5% | 50.0% | 50.0% |
| test | multi_hop | 3 | 33.3% | 100.0% | 0.381 | 22.2% | 42.2% | 0.0% |
| test | summary | 3 | 33.3% | 66.7% | 0.378 | 20.0% | 40.0% | 0.0% |
| test | overall | 20 | 55.0% | 70.0% | 0.454 | 40.5% | 49.0% | 30.0% |

Độ trễ truy xuất trung bình: 83.9 ms/câu (top 50).

### Thay đổi so với lần trước (20261004-052529-retrieval-s7-regression-check → 20261005-045129-retrieval-baseline-lf)

Không câu nào đổi hạng chunk đúng đầu tiên.

### Chi tiết từng câu — 20261005-045129-retrieval-baseline-lf

Hạng của chunk đúng đầu tiên, và hạng đầu tiên phủ từng vị trí bằng chứng (– = không có trong top 50).

| Câu | Split | Loại | Hạng đầu | Hạng theo vị trí | Câu hỏi |
|---|---|---|---|---|---|
| fact-01 | dev | fact | 13 | 13 | In Volume 1, Chapter 2, Subaru goes back to the loot house and is killed there. Who kills… |
| fact-02 | dev | fact | 1 | 1 | What name does Subaru give to the power that sends him back in time when he dies? |
| fact-03 | dev | fact | 9 | 9 | When Subaru first asks the silver-haired girl her name in Volume 1, what name does she gi… |
| fact-04 | dev | fact | 3 | 3 | At the end of Volume 1, after Subaru saves her, what real name does the silver-haired gir… |
| fact-05 | dev | fact | 6 | 6 | How does Subaru die for the third time in Volume 1, in the alley in Chapter 3? |
| fact-06 | dev | fact | 11 | 11 | What belongings did Subaru have with him when he was summoned to the other world? |
| fact-07 | test | fact | 2 | 6 / 2 | What nickname is the assassin Elsa known by, as identified by Reinhard in Volume 1? |
| fact-08 | dev | fact | 9 | 13 / 9 | In Volume 2, what weapon does Rem use against Subaru in the forest, the same weapon that … |
| fact-09 | dev | fact | 4 | 4 | In Volume 3, what does Subaru conclude was the source of the curse that kept killing peop… |
| fact-10 | dev | fact | 1 | 1 | According to Rem's interlude in Volume 3, how did Ram lose her horn? |
| fact-11 | dev | fact | 7 | 7 | What is the name of Crusch Karsten's blessing (divine protection)? |
| fact-12 | dev | fact | 1 | 1 | How does Petelgeuse Romanée-Conti introduce his title to Subaru in the cave in Volume 5? |
| fact-13 | test | fact | 2 | 2 / – / 25 | In Volume 6, Subaru begs Rem to run away with him. How does Rem respond, and what does Su… |
| fact-14 | test | fact | 1 | 1 | In Volume 7, what does Subaru offer Crusch in return for an alliance between Emilia and C… |
| fact-15 | dev | fact | 1 | 1 / 14 | Who delivers the final blow to the White Whale, and how is the whale brought down? |
| fact-16 | dev | fact | 1 | 1 | How does Petelgeuse finally die in Volume 9? |
| fact-17 | test | fact | 5 | – / 5 | What does Otto Suwen's blessing allow him to do? |
| fact-18 | test | fact | 31 | – / 31 | What blessing does Garfiel have, and what does it give him in battle? |
| fact-19 | test | fact | 25 | 40 / 25 | Who is affected by the barrier around the Sanctuary, and what does it do to them? |
| fact-20 | dev | fact | 21 | 21 | What are the three Trials of the Sanctuary tomb? |
| fact-21 | test | fact | 33 | 33 | How is Elsa killed during the attack on Roswaal Manor in Volume 15? |
| fact-22 | dev | fact | 2 | 2 | According to Echidna, what is the Great Rabbit and who left it behind? |
| fact-23 | dev | fact | 4 | 5 / 4 | How does Regulus Corneas die in Volume 19? |
| fact-24 | test | fact | 1 | 1 | What is the full name and sin of the Archbishop who introduces herself at the end of Volu… |
| fact-25 | test | fact | 1 | 2 / 1 | What full name does the Archbishop of Lust use to introduce herself in Volume 17? |
| fact-26 | dev | fact | – | – | Which two Archbishops attack Crusch and Rem's convoy as it returns with the White Whale's… |
| fact-27 | test | fact | 1 | – / 1 | What does Reid Astrea, the first Sword Saint, fight with when he faces the group in the P… |
| fact-28 | dev | fact | – | – | When Subaru wakes up with amnesia in the Pleiades Watchtower in Volume 23, what is the la… |
| fact-29 | dev | fact | 6 | 11 / 6 | In what state does Rem wake up at the start of Volume 26? |
| fact-30 | dev | fact | 1 | 1 | Who does Abel reveal himself to be in Volume 27? |
| fact-31 | dev | fact | 1 | 1 | Who is Natsumi Schwartz, and why is that persona created in Volume 27? |
| fact-32 | dev | fact | 1 | 5 / 7 / 1 | Which sin does Regulus Corneas represent as an Archbishop of the Witch Cult? |
| fact-33 | dev | fact | 5 | 5 / 14 / 19 | How does the mock duel between Subaru and Julius at the knights' training ground in Volum… |
| fact-34 | dev | fact | 27 | 27 | What happened to Julius after his fight with the Archbishop of Gluttony, Roy Alphard, in … |
| fact-35 | dev | fact | 2 | 2 / – / 33 | Why does Subaru's group set out for the Sage's Pleiades Watchtower in Volume 21, and how … |
| rel-01 | dev | relationship | 5 | 5 | How are Ram and Rem related, and which of them is older? |
| rel-02 | dev | relationship | 6 | 6 / – | Who was Wilhelm van Astrea's wife, and what was Wilhelm's surname before he married into … |
| rel-03 | test | relationship | 1 | 1 | How is Reinhard van Astrea related to Wilhelm and Theresia, and who are his parents? |
| rel-04 | dev | relationship | 38 | – / 38 | What is the relationship between Frederica Baumann and Garfiel? |
| rel-05 | dev | relationship | 23 | 29 / 23 / – | What is Beatrice's relationship to the Witch Echidna, and what task did Echidna leave her? |
| rel-06 | dev | relationship | 2 | 2 | In the royal selection announced in Volume 4, who is the knight of each candidate? |
| rel-07 | dev | relationship | 10 | 10 | Who is Joshua Juukulius to Julius, and why does Julius not remember him? |
| rel-08 | dev | relationship | 2 | 2 | Who is Fortuna to Emilia, and how does Fortuna die in Emilia's memories of the Elior Fore… |
| rel-09 | test | relationship | – | – | What are the names of Subaru's father and mother, as seen during his first Trial in the S… |
| rel-10 | test | relationship | 2 | 2 / 20 | In the short story "Felt, Starting the Royal Selection from Zero", who is Old Man Rom to … |
| rel-11 | dev | relationship | 14 | 48 / 14 | Who does Beatrice form a contract with in Volume 15, and what does he say to persuade her? |
| rel-12 | dev | relationship | 10 | 10 | What are Ram's feelings toward Roswaal, according to Rem's interlude in Volume 3? |
| rel-13 | dev | relationship | – | – / – | Who is Shaula, and who does she believe Subaru is? |
| rel-14 | test | relationship | – | – / – / – | Which spirit is contracted with Emilia? |
| multi-01 | dev | multi_hop | 6 | – / – / 6 | In Volume 1 Subaru dies three times before the loop in which he survives. Where does each… |
| multi-02 | test | multi_hop | 15 | – / – / – / 15 / – | Compare the Witch Cult Archbishops Subaru faces in the Mathers domain arc (Volumes 5–9) w… |
| multi-03 | dev | multi_hop | 30 | 30 / – | Elsa tries to kill Subaru and Felt in Volume 1. Who stops her that time, and who finally … |
| multi-04 | dev | multi_hop | 16 | – / – / 34 / 16 | How did Theresia van Astrea originally die, and what happened to her in Pristella? |
| multi-05 | dev | multi_hop | – | – / – | What happened to Rem after the battle against the White Whale? |
| multi-06 | test | multi_hop | 1 | 30 / 1 / 5 | Compare what Gluttony took from Crusch, from Rem and from Julius. |
| multi-07 | test | multi_hop | 13 | 15 / 47 / – / 13 / – | Name the Witches Subaru meets through Echidna's tea parties in the Sanctuary and the sin … |
| multi-08 | dev | multi_hop | – | – / – | What was the outcome for the Archbishops after the battle of Pristella: which were killed… |
| multi-09 | dev | multi_hop | 16 | 16 / – / – / – | How does the relationship between Subaru and Julius change from their duel in Volume 4 to… |
| sum-01 | dev | summary | 21 | 21 / 45 / – / – / – | Summarize the events of Volume 1 (Arc 1). |
| sum-02 | dev | summary | – | – / – / – / – / – | Summarize what happens to Subaru at Roswaal Manor in Volumes 2 and 3. |
| sum-03 | dev | summary | 19 | – / 19 / – | Summarize the battle against the White Whale in Volume 7. |
| sum-04 | test | summary | 44 | – / – / – / 44 / – / – | Summarize the Sanctuary arc (Volumes 10–15). |
| sum-05 | dev | summary | 19 | – / – / 19 / – / – / – / – | Summarize the Witch Cult's attack on the water city of Pristella (Volumes 16–20). |
| sum-06 | test | summary | 9 | 20 / 9 / – / – / – | Summarize the journey to and the start of events in the Pleiades Watchtower (Volumes 21–2… |
| sum-07 | test | summary | 1 | 5 / 9 / 26 / 2 / 1 | Summarize the story of Wilhelm and Theresia told in Volume 7, Chapter 5. |
| sum-08 | dev | summary | 1 | 16 / 4 / 1 | Summarize Rem's backstory as told in her interlude in Volume 3. |
| sum-09 | dev | summary | 2 | – / 2 / 13 / – | Summarize how Subaru's adventure in the Volakian Empire begins (Volumes 26–27). |

## Sinh câu trả lời

Chạy toàn bộ `/qa` (truy xuất top `QA_TOP_K` + LLM), sau đó một LLM chấm: **đúng** so với đáp án chuẩn (đúng / một phần / sai; điểm = đúng + 0,5 × một phần), **trung thực** chỉ so với các đoạn được trích. Từ chối nhầm: câu có đáp án nhưng hệ thống trả lời không tìm thấy. Câu ngoài phạm vi được tính là xử lý đúng khi hệ thống từ chối hoặc chỉ ra tiền đề sai.

Lần chạy *mô phỏng* (`python -m src.eval combine`) ghép kết quả từng câu của một lần chạy simple và một lần chạy agent theo chính sách định tuyến, không gọi LLM thêm.

| Lần chạy | Nhãn | Chế độ | Truy xuất | Mô hình | Prompt | Giám khảo | Đủ | Điểm | Đúng | Một phần | Sai | Từ chối nhầm | Bằng chứng trong ngữ cảnh | Trung thực | Trích chunk đúng | Ngoài phạm vi xử lý đúng | Gọi LLM/câu | Token vào/ra | Tổng ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261004-021903-generation-baseline | baseline | simple | `vector` | `gemini-3.5-flash-lite` | `3293f3463740` | `gemini-3.5-flash-lite` | ✅ | 49.2% | 37.3% | 23.9% | 4.5% | 32.8% | 46.3% | 97.7% | 59.1% | 100.0% | 1 | 2334.9/50.7 | 1330.9 |
| 20261004-032603-generation-s5-hybrid-boost-cand100 | s5-hybrid-boost-cand100 | simple | `hybrid candidates=100 scope=boost` | `gemini-3.5-flash-lite` | `3293f3463740` | `gemini-3.5-flash-lite` | ✅ | 57.5% | 43.3% | 28.4% | 3.0% | 25.4% | 50.7% | 100.0% | 64.0% | 100.0% | 1 | 2341.7/55.4 | 1562 |
| 20261004-044909-generation-s6-agent-all-v2 | s6-agent-all-v2 | agent | `hybrid candidates=100 scope=boost` | `gemini-3.5-flash-lite` | `3293f3463740` | `gemini-3.5-flash-lite` | ✅ | 79.1% | 67.2% | 23.9% | 1.5% | 7.5% | 73.1% | 93.5% | 71.0% | 100.0% | 3.1 | 9689/136.2 | 6418.5 |
| 20261004-050946-generation-s6-sim-route | s6-sim-route | auto (route, simulated) | `hybrid candidates=100 scope=boost` | `gemini-3.5-flash-lite` | `3293f3463740` | `gemini-3.5-flash-lite` | ✅ | 62.7% | 47.8% | 29.8% | 3.0% | 19.4% | 56.7% | 94.4% | 63.0% | 100.0% | 1.4 | 4079/79.8 | 2625.1 |
| 20261004-050949-generation-s6-sim-escalate | s6-sim-escalate | auto (escalate, simulated) | `hybrid candidates=100 scope=boost` | `gemini-3.5-flash-lite` | `3293f3463740` | `gemini-3.5-flash-lite` | ✅ | 73.1% | 53.7% | 38.8% | 3.0% | 4.5% | 61.2% | 95.3% | 57.8% | 100.0% | 2.3 | 6778.9/105.1 | 4402.9 |
| 20261004-050951-generation-s6-sim-route-escalate | s6-sim-route+escalate | auto (route+escalate, simulated) | `hybrid candidates=100 scope=boost` | `gemini-3.5-flash-lite` | `3293f3463740` | `gemini-3.5-flash-lite` | ✅ | 73.9% | 56.7% | 34.3% | 3.0% | 6.0% | 64.2% | 93.7% | 60.3% | 100.0% | 2.6 | 8024.8/112.7 | 5126.4 |
| 20261005-005527-generation-lang-en | lang-en | agent | `hybrid candidates=100 scope=boost` | `gemini-3.5-flash-lite` | `47b906aee31d` | `gemini-3.5-flash-lite` | ✅ | 82.8% | 76.1% | 13.4% | 4.5% | 6.0% | 68.7% | 88.9% | 61.9% | 100.0% | 3.2 | 10788.6/142.9 | 13718.8 |
| 20261005-033513-generation-lang-en-glossary | lang-en-glossary | agent | `hybrid candidates=100 scope=boost` | `gemini-3.5-flash-lite` | `47b906aee31d` | `gemini-3.5-flash-lite` | ✅ | 81.3% | 73.1% | 16.4% | 4.5% | 6.0% | 67.2% | 92.1% | 68.2% | 100.0% | 3.2 | 10901.2/141 | 7221.9 |
| 20261005-050459-generation-nav-en-1 | nav-en-1 | agent | `hybrid candidates=100 scope=boost` | `gemini-3.5-flash-lite` | `47b906aee31d` | `gemini-3.5-flash-lite` | ✅ | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% | – | 2 | 5264.5/100 | 3581 |
| 20261005-050617-generation-nav-en-2 | nav-en-2 | agent | `hybrid candidates=100 scope=boost` | `gemini-3.5-flash-lite` | `47b906aee31d` | `gemini-3.5-flash-lite` | ✅ | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% | 100.0% | 100.0% | 100.0% | – | 4 | 17687.5/175.5 | 6327.5 |
| 20261005-092219-generation-luna-en-1 | luna-en-1 | agent | `hybrid candidates=100 scope=boost` | `gpt-6-luna` | `47b906aee31d` | `gemini-3.1-flash-lite` | ✅ | 75.4% | 61.2% | 28.4% | 7.5% | 3.0% | 73.1% | 69.2% | 61.5% | 86.7% | 3.6 | 19170.7/195.4 | 8235.9 |
| 20261005-094842-generation-luna-en-2 | luna-en-2 | agent | `hybrid candidates=100 scope=boost` | `gpt-6-luna` | `47b906aee31d` | `gemini-3.1-flash-lite` | ✅ | 78.4% | 64.2% | 28.4% | 6.0% | 1.5% | 77.6% | 71.2% | 65.1% | 93.3% | 3.8 | 18596.8/195.1 | 8154.6 |

### Điểm theo loại câu và split, từng lần chạy

| Lần chạy | Chế độ | fact | relationship | multi_hop | summary | dev | test | Ngoài phạm vi |
|---|---|---|---|---|---|---|---|---|
| 20261004-021903-generation-baseline | simple | 52.9% | 67.9% | 22.2% | 33.3% | 50.0% | 47.5% | 100.0% |
| 20261004-032603-generation-s5-hybrid-boost-cand100 | simple | 64.3% | 78.6% | 27.8% | 27.8% | 55.3% | 62.5% | 100.0% |
| 20261004-044909-generation-s6-agent-all-v2 | agent | 84.3% | 89.3% | 72.2% | 50.0% | 79.8% | 77.5% | 100.0% |
| 20261004-050946-generation-s6-sim-route | auto (route, simulated) | 64.3% | 78.6% | 44.4% | 50.0% | 58.5% | 72.5% | 100.0% |
| 20261004-050949-generation-s6-sim-escalate | auto (escalate, simulated) | 80.0% | 78.6% | 55.6% | 55.6% | 73.4% | 72.5% | 100.0% |
| 20261004-050951-generation-s6-sim-route-escalate | auto (route+escalate, simulated) | 80.0% | 78.6% | 66.7% | 50.0% | 72.3% | 77.5% | 100.0% |
| 20261005-005527-generation-lang-en | agent | 80.0% | 89.3% | 88.9% | 77.8% | 81.9% | 85.0% | 100.0% |
| 20261005-033513-generation-lang-en-glossary | agent | 81.4% | 82.1% | 88.9% | 72.2% | 81.9% | 80.0% | 100.0% |
| 20261005-050459-generation-nav-en-1 | agent | 100.0% | 100.0% | – | – | 100.0% | 100.0% | – |
| 20261005-050617-generation-nav-en-2 | agent | 100.0% | 100.0% | – | – | 100.0% | 100.0% | – |
| 20261005-092219-generation-luna-en-1 | agent | 85.7% | 75.0% | 61.1% | 50.0% | 75.5% | 75.0% | 86.7% |
| 20261005-094842-generation-luna-en-2 | agent | 84.3% | 85.7% | 66.7% | 55.6% | 76.6% | 82.5% | 93.3% |

### Phân loại lỗi — 20261005-094842-generation-luna-en-2

Bằng chứng có nằm trong các chunk đưa cho LLM không? Hàng thứ nhất mà sai là lỗi **đọc/suy luận** (sửa prompt/mô hình); hàng thứ hai là lỗi **truy xuất** (sửa giai đoạn tìm kiếm).

| | Đúng | Một phần | Sai | Từ chối | Trả về rỗng |
|---|---|---|---|---|---|
| Bằng chứng có trong ngữ cảnh | 35 | 15 | 2 | 0 | 0 |
| Bằng chứng KHÔNG có trong ngữ cảnh | 8 | 4 | 2 | 1 | 0 |

| Split / loại | n | Đúng | Điểm |
|---|---|---|---|
| dev | 47 | 59.6% | 76.6% |
| test | 20 | 75.0% | 82.5% |
| fact | 35 | 77.1% | 84.3% |
| relationship | 14 | 71.4% | 85.7% |
| multi_hop | 9 | 44.4% | 66.7% |
| summary | 9 | 22.2% | 55.6% |

- Trung thực (trên 66 câu có trả lời): được hỗ trợ 71.2%, một phần 27.3%, không được hỗ trợ 1.5%, không trích nguồn 0.0%; trích ít nhất một chunk chứa bằng chứng chuẩn 65.1%.
- Câu có đáp án mà LLM trả về rỗng (lỗi phía nhà cung cấp, không phải từ chối): 0.0%.
- Ngoài phạm vi (15 câu): xử lý đúng 93.3%, bịa câu trả lời 6.7%; theo loại: general 66.7%, not_in_text 100.0%, false_premise 100.0%, beyond_corpus 100.0%.
- Chi phí trung bình mỗi câu: 18596.8 token vào, 195.1 token ra (giám khảo thêm 1577.5 token); truy xuất 174 ms, LLM 7980.5 ms.
- Cấu hình: `openai` / `gpt-6-luna`, temperature 0.2, tối đa 700 token ra, top 6, chunker `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457).

### Chi tiết từng câu — 20261005-094842-generation-luna-en-2

| Câu | Kết quả | Bằng chứng trong ngữ cảnh (hạng) | Trung thực | Câu trả lời | Nhận xét giám khảo |
|---|---|---|---|---|---|
| fact-01 | correct | 6 | supported | Elsa Granhiert kills Subaru. She slashes his abdomen with a kukri, then uses a second kukri to cut deeply through it, spilling his blood an… | The system answer accurately identifies the killer and the method, and all claims are directly supported by the provide… |
| fact-02 | correct | không | supported | He calls it **Return by Death**. [1] | The system correctly identifies the name of the power, and the cited passage confirms that Subaru refers to it as 'Retu… |
| fact-03 | incorrect | không | supported | She tells him, “Emilia. Just Emilia.” [1] | The system answer is factually incorrect regarding the events of Volume 1, as the girl gives the name 'Satella' when fi… |
| fact-04 | correct | 1 | supported | She tells him her name is **Emilia**—“Just Emilia.” [1] | The system answer correctly identifies the name Emilia and is fully supported by the provided text. |
| fact-05 | correct | 5, 6 | supported | Subaru is stabbed in the back by Dumber as he tries to push past the thugs and leave the alley. The knife damages his guts; the thugs turn … | The system answer accurately identifies the cause of death and the perpetrator, and all details provided are directly s… |
| fact-06 | correct | không | supported | Subaru had a wallet, a cell phone, corn-soup chips, and cup ramen with him. He was wearing a tracksuit and sneakers. [1] | The system answer correctly identifies the items Subaru had with him and is fully supported by the provided text. |
| fact-07 | correct | 4 | partially_supported | Reinhard identifies Elsa as **“the Bowel Hunter.”** [1] | While the system answer correctly identifies the nickname, the cited passage shows Elsa referring to herself as the 'Bo… |
| fact-08 | correct | 6, 7, 8, 9 | supported | Rem uses a **morning star**—a spiked iron ball attached to a long chain. [6][8] | The system answer accurately identifies the weapon as a morning star and describes it as a spiked iron ball on a chain,… |
| fact-09 | correct | 9 | supported | Subaru concludes that the curse came from the demon beast puppy that bit him in the village—not from a human shaman. The puppy’s bite sprea… | The system answer correctly identifies the puppy as the source of the curse and is fully supported by the provided text… |
| fact-10 | partial | 1, 4 | partially_supported | Ram lost her horn when an attacker struck her head with a blade. She had turned to shield Rem and took the blow instead, severing her horn.… | The system answer correctly identifies that Ram shielded Rem and had her horn severed, but it fails to mention the vill… |
| fact-11 | correct | 6 | supported | Crusch Karsten’s blessing is called the **Divine Protection of Wind Reading** (also rendered in the text as the “blessing of wind reading”)… | The system correctly identifies the blessing as the Divine Protection of Wind Reading, which is directly supported by t… |
| fact-12 | correct | 1, 3 | supported | He first apologizes for not having introduced himself, then bows and says, “I am Petelgeuse Romanée-Conti—” He twists his head toward Subar… | The system answer accurately captures the required key points and is fully supported by the provided text from Volume 5. |
| fact-13 | incorrect | 2 | supported | Rem sadly refuses: “I cannot run away with you, Subaru.” She says that if they fled, she’d be leaving behind the Subaru she loves most. [2]… | The system answer fails to address the second half of the question regarding what Subaru tells Rem after her refusal, a… |
| fact-14 | correct | 2 | supported | Subaru offers the Emilia camp’s magic-crystal mining rights in the Great Elior Forest, along with information about when and where the Whit… | The system answer accurately identifies both key points required by the reference answer and is fully supported by the … |
| fact-15 | partial | 13 | partially_supported | Wilhelm delivers the final blow. The White Whale is first pinned beneath the Great Tree, which crashes down onto it; though the impact does… | The system answer is missing the key point that the whale was cut in two, as the cited passage only describes Wilhelm s… |
| fact-16 | partial | 1 | partially_supported | After Petelgeuse abandons possession of Subaru and returns to his own body, Julius impales him with his sword, leaving him bleeding and una… | The system answer correctly identifies the sword strike and the rockslide, but it fails to include the key point that P… |
| fact-17 | correct | 1, 2 | supported | Otto’s blessing of language lets him understand the voices of living creatures. He can communicate with them and enlist their help—for exam… | The system answer accurately identifies the blessing of language and its function of communicating with living creature… |
| fact-18 | correct | không | supported | Garfiel has the **blessing of the earth spirit**. It enhances his healing and lets him manipulate the ground within the reach of his limbs.… | The system correctly identifies the blessing and its effects, and all claims are directly supported by the provided tex… |
| fact-19 | partial | 3 | partially_supported | The barrier affects people with sufficiently mixed human and demi-human blood—those whose mixed blood is “thick” enough. It holds them capt… | The system answer correctly identifies who is affected and the effect of being held captive, but it fails to mention th… |
| fact-20 | partial | không | supported | The three Trials are: 1. **Face your past.** [6] 2. **Behold the unknowable present**—a Trial that makes someone’s spoken lies come true. [… | The system correctly identifies the first two trials but fails to identify the third trial, claiming the passages do no… |
| fact-21 | correct | 12 | supported | Garfiel ultimately kills Elsa by hurling the massive Rock Pig at her. She watches it coming and does not try to escape; the impact smashes … | The system answer accurately identifies Garfiel as the killer and the method of the Rock Pig, and all details provided … |
| fact-22 | correct | 2 | supported | Echidna says the Great Rabbit is a demon beast—one of the three great demon beasts and a “negative legacy” left by Daphne, the Witch of Glu… | The system answer accurately identifies the Great Rabbit as one of the three great demon beasts, a horde, and a negativ… |
| fact-23 | correct | 4 | supported | After Reinhard’s attack sent Regulus through the pavement and underground, water from the canal he had destroyed poured into the narrow tun… | The system answer accurately identifies the key points of Regulus's death and is fully supported by the provided text p… |
| fact-24 | correct | 7, 10 | supported | The Archbishop is **Sirius Romanée-Conti**, charged with **Wrath**. [7] | The system answer correctly identifies the name and sin as requested, and both facts are explicitly stated in the provi… |
| fact-25 | correct | 2, 3 | supported | She introduces herself as **Capella Emerada Lugunica**. [1] | The system correctly identified the name provided in the text and the citation directly supports the claim. |
| fact-26 | correct | không | supported | The two Archbishops were **Lye Batenkaitos of Gluttony** and **Regulus Corneas of Greed**. [3] | The system correctly identified both Archbishops and their respective sins, and all information provided is directly su… |
| fact-27 | correct | 1 | supported | He fights with chopsticks—one in each hand—rather than a sword. [8] | The system answer correctly identifies that Reid uses chopsticks and is supported by the provided text. |
| fact-28 | incorrect | không | supported | The last thing Subaru remembers is heading back to the room after checking whether he had any special ability. He recalls concluding that h… | The system answer is factually incorrect because it describes Subaru's immediate confusion upon waking up in the Watcht… |
| fact-29 | correct | 5, 9 | partially_supported | Rem wakes up with amnesia: she doesn’t recognize Subaru and doesn’t even know who she is. Her legs are also too weak for her to stand, appa… | The system correctly identifies Rem's amnesia and wariness. However, the claim regarding the cause of her leg weakness … |
| fact-30 | correct | 2 | supported | Abel reveals that he is Vincent Abelks, the seventy-seventh emperor of the Holy Volakian Empire, though he has been removed from the throne… | The system answer accurately identifies Abel as the 77th emperor of Volakia and notes his removal from the throne, both… |
| fact-31 | correct | 7 | supported | Natsumi Schwartz is Subaru’s female disguise. In Volume 27, he adopts it so he can pass through Guaral’s gates without being recognized, th… | The system answer accurately identifies the persona and the reason for its creation while remaining fully supported by … |
| fact-32 | correct | 1, 5 | supported | Regulus Corneas represents **Greed** as an Archbishop of the Witch Cult. [1] | The system answer correctly identifies Regulus Corneas as the Archbishop of Greed, which is explicitly stated in the pr… |
| fact-33 | correct | 5, 10 | supported | Subaru and Julius agree to a mock duel after Subaru insults Julius and refuses to apologize. Subaru tries to gain an advantage with a trick… | The system answer accurately captures all key points and is fully supported by the provided text passages. |
| fact-34 | correct | 7 | supported | Julius was badly injured in the fight, but Ricardo’s spirit healed him. [11] Afterward, Gluttony had eaten Julius’s name: Julius still reme… | The system answer accurately covers all key points and is fully supported by the provided citations. |
| fact-35 | correct | 3, 16 | supported | Subaru’s personal reason for making the dangerous journey is to bring Rem back; he vows to help her while she is still sleeping. [16] The g… | The system correctly identifies the motivations for the journey and the method for crossing the dunes, with all claims … |
| rel-01 | correct | 3 | supported | Ram and Rem are twin sisters. Ram is the older twin; Rem is the younger. [3] | The system answer correctly identifies the twins and their birth order, and all claims are directly supported by the pr… |
| rel-02 | partial | 2 | supported | Wilhelm’s wife was Theresia van Astrea. Before marrying into the Astrea family, his surname was Trias. [2] | The system answer is faithful to the provided passage, but it failed to include the key point that Theresia was the pre… |
| rel-03 | correct | 16 | supported | Reinhard is Wilhelm and Theresia’s grandson: they had a son, Heinkel, who married Louanna, and Reinhard is their son. [16] | The system answer accurately identifies the familial relationships and parents as requested, and all information is dir… |
| rel-04 | partial | không | supported | Frederica is Garfiel’s older sister; Garfiel is her younger brother. [1] | The system answer correctly identifies the sibling relationship but fails to mention that they do not get along, which … |
| rel-05 | partial | 4 | partially_supported | Beatrice is Echidna’s daughter—Echidna calls her “Mother” and Beatrice “Betty.” [5] Echidna left her to guard the archive of forbidden book… | The system answer correctly identifies the relationship and the task, but it fails to mention the 'four hundred years' … |
| rel-06 | correct | 1, 2 | partially_supported | The knights associated with each royal candidate are: - **Crusch Karsten** — Felix Argyle, the Blue Knight. - **Priscilla Bariel** — Al. - … | The system answer is factually correct regarding the candidates and their knights, but the claim regarding Emilia and S… |
| rel-07 | partial | 2, 3 | partially_supported | Joshua is Julius’s younger brother [1]. Julius does not remember him because Gluttony’s power ate Julius’s name, causing others to forget h… | The system incorrectly states that Julius's name was eaten; the passages indicate that Joshua's name was eaten, causing… |
| rel-08 | correct | 3 | supported | Fortuna is Emilia’s aunt—the younger sister of Emilia’s father—and the woman who raised her as a surrogate mother. Emilia regarded her as h… | The system correctly identifies Fortuna as Emilia's aunt and surrogate mother while acknowledging Emilia viewed her as … |
| rel-09 | correct | không | supported | Subaru’s father is **Kenichi Natsuki**, and his mother is **Nahoko Natsuki**. [13][15] | The system correctly identified both parents' names, and both names are explicitly mentioned in the provided passages. |
| rel-10 | correct | 3 | supported | Old Man Rom is Felt’s surrogate father and the family she trusts wholeheartedly. [6] They’re living at the Astrea family mansion. [3][7] | The system correctly identified Rom as Felt's surrogate father/family and confirmed they are living at the Astrea famil… |
| rel-11 | correct | 7, 8 | supported | Beatrice forms a contract with **Subaru Natsuki**. He persuades her by asking her to choose him: he can’t promise to be with her for four h… | The system answer correctly identifies Subaru, the specific phrase used, and the outcome of the contract, all of which … |
| rel-12 | correct | không | supported | Ram is deeply devoted to Roswaal: she says she serves him loyally without asking anything in return and declares, “I am yours, Master Roswa… | The system answer accurately captures Ram's adoration and devotion to Roswaal as described in the reference and support… |
| rel-13 | correct | 9 | supported | Shaula is the Pleiades Watchtower’s guardian, who has waited there for centuries. She says her master is the Sage Flugel and believes Subar… | The system answer accurately identifies Shaula's role and her belief regarding Subaru's identity, with all claims being… |
| rel-14 | correct | không | unsupported | Emilia’s contracted spirit is Puck, the Great Spirit. [1] | While the answer is factually correct according to the series, the provided passage mentions Puck and Emilia (Lia) but … |
| multi-01 | partial | 9 | partially_supported | 1. **First death:** In the loot cellar, where Elsa kills Subaru by slashing open his abdomen. [2][11] 2. **Second death:** Also in the loot… | The system correctly identifies the locations and culprits for the first two deaths, but it fails to accurately describ… |
| multi-02 | correct | không | supported | In the Mathers domain, the sin involved was **Sloth**: Subaru faces Petelgeuse, the Archbishop entrusted with Sloth. [12][13] In Pristella,… | The system correctly identifies the Archbishops involved in both arcs and provides support for its claims using the pro… |
| multi-03 | incorrect | 11 | partially_supported | In Volume 1, Felt first saves Subaru by tackling him out of Elsa’s attack, but Elsa then cuts Felt down. [3][1] Reinhard arrives and stops … | The system incorrectly identifies the volume and method of Elsa's death, contradicting the reference answer and the act… |
| multi-04 | partial | 7, 8, 16, 17 | partially_supported | Theresia originally disappeared during the White Whale expedition: after the battle turned chaotic in the fog, she realized she had lost th… | The system failed to mention that she was killed by the White Whale, and the cited passages do not contain the informat… |
| multi-05 | partial | 6, 9 | partially_supported | Rem survived the White Whale battle and returned with the expeditionary force. Later, on the journey back, she and Crusch were attacked by … | The system answer is partially correct but misses the key detail that her name and memories were eaten. It is only part… |
| multi-06 | correct | 2, 6, 10 | supported | Gluttony affected each differently: - **Crusch:** her **own memories** were eaten; she could no longer remember her past or the people she … | The system accurately identifies the differences in how Gluttony affected Crusch, Rem, and Julius, and all claims are d… |
| multi-07 | correct | 6, 8, 9, 13, 15, 22 | supported | Subaru meets these six Witches at the Sanctuary tea parties: - **Echidna** — Greed [3][22] - **Typhon** — Pride [6] - **Minerva** — Wrath [… | The system correctly identifies all six Witches and their respective sins, and every claim is directly supported by the… |
| multi-08 | correct | 39 | supported | After the battle, **Regulus (Greed) was killed**: he drowned underground after being buried by his own ability’s counterattack [23][39]. **… | The system correctly identifies the status of the Archbishops based on the provided text and accurately notes that the … |
| multi-09 | partial | 17, 18, 20 | partially_supported | In Volume 4, Subaru and Julius are openly hostile: Julius looks down on Subaru and rejects him as a knight, while Subaru insults Julius and… | The system answer correctly identifies the relationship shift after Pristella, but it fails to include the required key… |
| sum-01 | correct | 17, 26, 28, 31 | supported | Subaru Natsuki is suddenly transported from modern Japan to a fantasy world, where he meets a silver-haired girl searching for her stolen b… | The system answer covers all required key points accurately and all claims are directly supported by the provided text … |
| sum-02 | partial | không | partially_supported | At Roswaal Manor, Subaru’s peaceful first week ends when he suddenly returns to its first day. He suspects his deaths in earlier loops were… | The system answer misses the specific detail that Rem kills Subaru with her morning star, which is a required key point… |
| sum-03 | partial | không | supported | In Volume 7, Subaru’s warning lets Crusch’s force prepare for the White Whale’s appearance. When it emerges, Rem strikes first with powerfu… | The system answer fails to mention the alliance with Crusch, the mining rights, the Great Flugel Tree, or the fact that… |
| sum-04 | refused | không |  | Not found in the provided passages. |  |
| sum-05 | partial | 4, 18 | supported | The Witch Cult seized Pristella’s city hall and all four water-control towers, giving them the power to open the floodgates and drown the c… | The system answer fails to mention the deaths or captures of the Archbishops (Regulus, Sirius) and the reanimation of T… |
| sum-06 | partial | 8 | partially_supported | After the costly battle in Pristella, Subaru’s group set out east to seek the Sage in the Auguria Dunes, hoping to find a way to restore wh… | The system answer misses several key points required by the prompt (memory loss, Reid's chopsticks) and includes a clai… |
| sum-07 | partial | 1, 2, 3, 5, 6, 7, 10 | partially_supported | Wilhelm, a young soldier devoted entirely to swordsmanship, repeatedly met Theresia in a flower garden. Their conversations gradually grew … | The system answer claims Wilhelm defeated Theresia and took her sword, which contradicts the cited passages where she d… |
| sum-08 | correct | 1, 2, 3, 4, 5 | supported | Rem and her twin sister Ram were born into the oni tribe at a time when twins were considered ill-omened and were supposed to be killed. Th… | The system answer accurately covers all required key points and is fully supported by the provided text passages. |
| sum-09 | partial | 4 | partially_supported | After the events at the Pleiades Watchtower, Subaru, Rem, and Louis are whisked away to a meadow far from Auguria. Rem has lost her memorie… | The system answer is missing the key point about Subaru disguising himself as Natsumi Schwartz; while it mentions he be… |
| oos-01 | refused | – |  | Not found in the provided passages. |  |
| oos-02 | refused | – |  | Not found in the provided passages. |  |
| oos-03 | answered | – |  | O(n²) | The system provided an answer based on outside knowledge regarding computer science rather than declining the question … |
| oos-04 | refused | – |  | Not found in the provided passages. |  |
| oos-05 | refused | – |  | Not found in the provided passages. |  |
| oos-06 | refused | – |  | Not found in the provided passages. |  |
| oos-07 | corrected_premise | – |  | Emilia did not become an Archbishop of the Witch Cult. The passages show her being mistaken for Satella, the Witch of Jealousy, by the Holy… | The system correctly identifies that the premise of the question is false and clarifies Emilia's actual status. |
| oos-08 | corrected_premise | – |  | Rem didn’t cut off Ram’s horn deliberately. During the attack, Ram shielded Rem and was struck by a weapon that severed her horn. Rem’s fir… | The system correctly identifies that Rem did not cut off the horn and explains the actual circumstances of the event. |
| oos-09 | refused | – |  | Not found in the provided passages. |  |
| oos-10 | corrected_premise | – |  | Subaru defeated Petelgeuse Romanée-Conti, the Archbishop of Sloth—not an Archbishop of Pride. [7] | The system correctly identified that the premise of the question was false by clarifying that the Archbishop of Sloth w… |
| oos-11 | corrected_premise | – |  | Volume 1 doesn’t say that Puck formed a contract with Subaru. It describes Puck as Emilia’s spirit and shows him helping her and Subaru dur… | The system correctly identifies that the premise of the question is false by clarifying that Puck is Emilia's spirit an… |
| oos-12 | refused | – |  | Not found in the provided passages. |  |
| oos-13 | corrected_premise | – |  | The royal selection has not yet produced a winner in the passages provided. Emilia and the other candidates are still competing for the thr… | The system correctly identifies that the royal selection is ongoing and has not yet concluded, effectively addressing t… |
| oos-14 | refused | – |  | Not found in the provided passages. |  |
| oos-15 | refused | – |  | Not found in the provided passages. |  |

## Bộ câu hỏi khác

Các lần chạy trên một file câu hỏi khác cùng id (vd. bản tiếng Việt). So sánh từng câu với một lần chạy trên `golden_set.json` cùng mã và cấu hình, không so với bảng ở trên.

| Lần chạy | Loại | File câu hỏi | Nhãn | Chế độ | dev Hit@6 / Điểm | Đúng | Từ chối nhầm | Ngoài phạm vi xử lý đúng |
|---|---|---|---|---|---|---|---|---|
| 20261005-012550-generation-lang-vi | generation | `data/eval/golden_set_vi.json` | lang-vi | agent | 79.8% | 70.2% | 7.5% | 100.0% |
| 20261005-023444-generation-lang-vi-glossary-dev | generation | `data/eval/golden_set_vi.json` | lang-vi-glossary-dev | agent | 84.3% | 76.1% | 3.0% | 100.0% |
| 20261005-030534-generation-lang-vi-glossary | generation | `data/eval/golden_set_vi.json` | lang-vi-glossary | agent | 83.6% | 74.6% | 3.0% | 100.0% |
| 20261005-050538-generation-nav-vi-1 | generation | `data/eval/golden_set_vi.json` | nav-vi-1 | agent | 100.0% | 100.0% | 0.0% | – |
| 20261005-050701-generation-nav-vi-2 | generation | `data/eval/golden_set_vi.json` | nav-vi-2 | agent | 100.0% | 100.0% | 0.0% | – |
| 20261005-082639-generation-luna-smoke-vi | generation | `data/eval/golden_set_vi.json` | luna-smoke-vi | agent | 62.5% | 50.0% | 0.0% | 0.0% |
| 20261005-082826-generation-luna-vi-1 | generation | `data/eval/golden_set_vi.json` | luna-vi-1 | agent | 79.1% | 68.7% | 0.0% | 86.7% |
| 20261005-085430-generation-luna-vi-2 | generation | `data/eval/golden_set_vi.json` | luna-vi-2 | agent | 80.6% | 68.7% | 0.0% | 93.3% |
