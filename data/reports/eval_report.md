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

Embedding: `BAAI/bge-small-en-v1.5`. Mã `src` là hash của mọi file `src/**/*.py` lúc chạy, nên phân biệt được cả thay đổi chưa commit.

### Kiểm tra tính lặp lại

- 2 lần chạy cùng cấu hình (20261004-021808-retrieval-baseline-vector, 20261004-021815-retrieval-baseline-vector-repeat): kết quả giống hệt nhau ✅
- 2 lần chạy cùng cấu hình (20261004-032513-retrieval-s5-final, 20261004-032527-retrieval-s5-final-repeat): kết quả giống hệt nhau ✅

### Theo loại câu hỏi — 20261004-052529-retrieval-s7-regression-check

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

Độ trễ truy xuất trung bình: 102.0 ms/câu (top 50).

### Thay đổi so với lần trước (20261004-032527-retrieval-s5-final-repeat → 20261004-052529-retrieval-s7-regression-check)

Không câu nào đổi hạng chunk đúng đầu tiên.

### Chi tiết từng câu — 20261004-052529-retrieval-s7-regression-check

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

### Phân loại lỗi — 20261005-033513-generation-lang-en-glossary

Bằng chứng có nằm trong các chunk đưa cho LLM không? Hàng thứ nhất mà sai là lỗi **đọc/suy luận** (sửa prompt/mô hình); hàng thứ hai là lỗi **truy xuất** (sửa giai đoạn tìm kiếm).

| | Đúng | Một phần | Sai | Từ chối | Trả về rỗng |
|---|---|---|---|---|---|
| Bằng chứng có trong ngữ cảnh | 38 | 5 | 1 | 1 | 0 |
| Bằng chứng KHÔNG có trong ngữ cảnh | 11 | 6 | 2 | 3 | 0 |

| Split / loại | n | Đúng | Điểm |
|---|---|---|---|
| dev | 47 | 74.5% | 81.9% |
| test | 20 | 70.0% | 80.0% |
| fact | 35 | 77.1% | 81.4% |
| relationship | 14 | 78.6% | 82.1% |
| multi_hop | 9 | 77.8% | 88.9% |
| summary | 9 | 44.4% | 72.2% |

- Trung thực (trên 63 câu có trả lời): được hỗ trợ 92.1%, một phần 7.9%, không được hỗ trợ 0.0%, không trích nguồn 0.0%; trích ít nhất một chunk chứa bằng chứng chuẩn 68.2%.
- Câu có đáp án mà LLM trả về rỗng (lỗi phía nhà cung cấp, không phải từ chối): 0.0%.
- Ngoài phạm vi (15 câu): xử lý đúng 100.0%, bịa câu trả lời 0.0%; theo loại: general 100.0%, not_in_text 100.0%, false_premise 100.0%, beyond_corpus 100.0%.
- Chi phí trung bình mỗi câu: 10901.2 token vào, 141 token ra (giám khảo thêm 1950.3 token); truy xuất 177.3 ms, LLM 7044.7 ms.
- Cấu hình: `gemini` / `gemini-3.5-flash-lite`, temperature 0.2, tối đa 700 token ra, top 6, chunker `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457).

### Chi tiết từng câu — 20261005-033513-generation-lang-en-glossary

| Câu | Kết quả | Bằng chứng trong ngữ cảnh (hạng) | Trung thực | Câu trả lời | Nhận xét giám khảo |
|---|---|---|---|---|---|
| fact-01 | correct | 6, 9 | supported | In Volume 1, Chapter 2, Subaru is killed in the loot house by **Elsa** [4][6][9]. She slashes open his abdomen with a large blade/kukri kni… | The system answer correctly identifies Elsa as the killer and describes how she killed him using a kukri knife to slice… |
| fact-02 | correct | 1 | supported | Subaru names the power "Return by Death" [1]. | The system answer correctly identifies the name Subaru gives to his power, and this claim is fully supported by the cit… |
| fact-03 | correct | 3 | supported | When Subaru first asks the silver-haired girl her name, she gives her name as **Satella** [3]. | The system answer correctly identifies the name given as Satella, which matches both the reference answer and the cited… |
| fact-04 | correct | 2 | supported | After Subaru saves her at the end of Volume 1, the silver-haired girl tells him her real name is Emilia (specifically, "Just Emilia") [2]. | The system answer correctly identifies the name 'Emilia' ('Just Emilia') as requested, and this information is fully su… |
| fact-05 | incorrect | không | supported | In Volume 1, Chapter 3, Subaru's third death in the alley occurs after he encounters the three thugs again [1]. As he stands in the dead-en… | The system answer misses the key point that Subaru was stabbed in the back by one of the thugs, which is the actual cau… |
| fact-06 | correct | 5 | supported | When Subaru was summoned to the other world, his belongings consisted of: - A cell phone (which looked like it would run out of batteries s… | The system answer includes all the necessary key points and extra details, and every claim is directly supported by the… |
| fact-07 | correct | 3 | supported | Elsa is known by the nickname the **Bowel Hunter** (or "Bowel Hunter" Gramhilde) [1][3]. | The system answer correctly identifies Elsa's nickname as the 'Bowel Hunter' and is fully supported by the provided tex… |
| fact-08 | correct | 6, 8, 9 | supported | Rem uses a spiked iron ball on a long chain, also known as a "morning star" [6, 8, 9]. | The system answer correctly identifies the weapon as a morning star, specifically a spiked iron ball on a long chain, w… |
| fact-09 | incorrect | không | supported | Subaru concludes that the source of the curse is a shaman located in Earlham Village [6]. He deduces this after learning from Beatrice that… | The system answer claims Subaru concluded the source was a shaman located in the village, which is a step in his reason… |
| fact-10 | refused | không |  | Not found in the provided passages. |  |
| fact-11 | refused | không |  | Not found in the provided passages. |  |
| fact-12 | correct | 2 | supported | In the cave, Petelgeuse introduces his title to Subaru by pointing at him with the fingers of both hands, cackling, and stating: “—Archbish… | The system answer accurately captures the key points (Archbishop of Sin and Sloth) required by the reference answer, an… |
| fact-13 | partial | 2 | supported | When Subaru asks Rem to run away with him to the west or north, telling her that he is weak and that no one needs him [4][7], Rem gently re… | The system answer correctly identifies how Rem responds and quotes her, but it misses the second part of the question r… |
| fact-14 | correct | 2 | supported | In return for an alliance between Emilia and Crusch, Subaru offers information on the exact time and place the White Whale will appear (alo… | The system answer accurately identifies both the magic crystal mining rights in the Great Elior Forest and the informat… |
| fact-15 | correct | 10 | supported | The White Whale is brought down by luring it to the giant Flugel's Tree, where the massive tree is toppled so that its great weight crashes… | The system answer accurately identifies Wilhelm van Astrea and the Flugel Tree as the method used to defeat the White W… |
| fact-16 | correct | 1, 3 | supported | In Volume 9, Petelgeuse is ultimately defeated when Julius runs him through with his rainbow-aurora sword, which scorches his evil spirit a… | The system answer accurately captures all key points from the reference answer (Julius striking him with a rainbow swor… |
| fact-17 | correct | 1, 2 | supported | Otto Suwen possesses the "blessing of language" (also referred to as a language blessing) [1, 3]. It allows him to converse and communicate… | The system answer accurately captures the essence of Otto's blessing of language as detailed in the reference answer an… |
| fact-18 | correct | không | supported | Garfiel possesses the **blessing of the earth spirit** (also referred to as the blessing of the earth) [6, 7]. In battle, it provides him w… | The system answer accurately identifies the blessing of the earth spirit and its effects (healing and terrain manipulat… |
| fact-19 | partial | không | supported | The barrier around the Sanctuary affects those who carry mixed human and demi-human blood (half-bloods), trapping them inside so that they … | The system answer correctly identifies who is affected (people with mixed blood) and what it does (traps them inside), … |
| fact-20 | correct | không | supported | Based on the provided passages, the three Trials of the Sanctuary tomb consist of: 1. **The first Trial:** To "face your past" [5, 6, 7]. 2… | The system answer correctly identifies the three parts of the trials as described in the text, capturing the first tria… |
| fact-21 | refused | 8 |  | Not found in the provided passages. |  |
| fact-22 | correct | 2 | supported | According to Echidna, the Great Rabbit is a demon beast that can infinitely divide from a single individual, with all of them sharing the s… | The system answer accurately identifies the Great Rabbit as one of the three great demon beasts, notes that it is a hor… |
| fact-23 | correct | 3, 5 | supported | In Volume 19, Regulus Corneas is defeated by Reinhard and ends up plunging deep underground [2][5]. After Reinhard strikes him down from th… | The system answer accurately identifies how Regulus dies in Volume 19 (driven underground by Reinhard, trapped while dr… |
| fact-24 | correct | 1 | supported | The Archbishop charged with Wrath is Sirius Romanée-Conti [1][3]. | The system answer correctly identifies the Archbishop's full name and her sin of Wrath, both of which are supported by … |
| fact-25 | correct | không | supported | The Archbishop of Lust introduces herself as **Capella Emerada Lugunica** [2]. | The system answer correctly identifies the full name 'Capella Emerada Lugunica', which is present both in the reference… |
| fact-26 | correct | không | supported | The two Archbishops of the Seven Deadly Sins who attack Crusch and Rem's convoy are **Regulus** (the Archbishop of Greed) and **Batenkaitos… | The system answer correctly identifies Regulus (Greed) and Batenkaitos (Gluttony) as the two Archbishops, and these fac… |
| fact-27 | correct | 5 | supported | When Reid Astrea, the first Sword Saint, faces the group in the Pleiades Watchtower, he famously fights using mere chopsticks (or small woo… | The system answer correctly identifies that Reid Astrea fights with chopsticks and provides details that are fully supp… |
| fact-28 | correct | 11 | supported | When Subaru wakes up with amnesia in the Pleiades Watchtower in Volume 23, his last memory before arriving in the fantasy world is stepping… | The system answer accurately identifies that Subaru's last memory is stepping out of the convenience store and that he … |
| fact-29 | correct | 2 | supported | When Rem wakes up at the start of Volume 26 (having already woken from her long slumber), she has lost her memories, not even knowing who s… | The system answer accurately captures that Rem wakes up with amnesia, distrusts Subaru due to the Witch's scent, and at… |
| fact-30 | correct | 1 | supported | In Volume 27, Abel reveals himself to be Vincent Abelks, the seventy-seventh emperor of the Holy Volakian Empire, who was removed from his … | The system answer accurately identifies Abel as Vincent Abelks, the seventy-seventh emperor of Volakia who was removed … |
| fact-31 | correct | 3 | supported | Natsumi Schwartz is a cross-dressing alter ego/persona of Natsuki Subaru [1, 2]. The persona is created in Volume 27 as a deceptive strateg… | The system answer accurately identifies Natsumi Schwartz as Subaru's cross-dressing persona and explains that it was cr… |
| fact-32 | correct | 1, 5 | supported | Regulus Corneas represents the sin of **Greed** (Tham lam) as an Archbishop of the Witch Cult [1, 2]. | The system answer correctly identifies Regulus Corneas as the Archbishop of Greed, which aligns with both the reference… |
| fact-33 | correct | 5 | supported | Prompted by Julius to settle their dispute, Subaru and Julius head to the knights' garrison parade square for a mock duel using wooden wast… | The system answer accurately captures all the key points from the reference answer (one-sided defeat, wooden wasters, S… |
| fact-34 | correct | 4 | supported | During his fight against the Archbishop of Gluttony, Roy Alphard, in Pristella, Julius was heavily outmatched and defeated in combat [12]. … | The system answer accurately captures all the key points from the reference answer (name eaten by Gluttony, forgotten b… |
| fact-35 | partial | không | partially_supported | Subaru's group sets out for the Pleiades Watchtower in the Auguria Dunes because it is the location of the Sage, whose wisdom they seek [2]… | The system answer correctly identifies why they set out for the tower (to seek the Sage's wisdom, though it misses the … |
| rel-01 | correct | 4 | supported | Ram and Rem are twin sisters belonging to the demon (oni) race [1, 3, 4]. Ram is the older twin sister, and Rem is the younger twin sister … | The system answer accurately states that Ram and Rem are twin sisters of the demon race and that Ram is the older twin.… |
| rel-02 | correct | 3 | supported | Wilhelm van Astrea's wife was Theresia van Astrea (the previous Sword Saint) [3][5]. Before marrying into the Astrea family, Wilhelm's surn… | The system answer accurately identifies Wilhelm's wife as Theresia van Astrea (the previous Sword Saint) and his former… |
| rel-03 | correct | 1 | supported | Reinhard van Astrea is the grandson of Wilhelm van Astrea and Theresia van Astrea [1]. His parents are Heinkel (Wilhelm and Theresia's son)… | The system answer accurately states the relationships and parents based on the reference answer and key points, and all… |
| rel-04 | partial | không | supported | Frederica Baumann and Garfiel Tinsel are older sister and younger brother [1][4]. They share the same mother, Lisha, but have different fat… | The system correctly identifies them as older sister and younger brother, but misses the key point about their relation… |
| rel-05 | correct | 7, 8, 9 | supported | Beatrice is Echidna's daughter [1], created by her as an artificial spirit. Echidna left Beatrice the task of acting as the guardian of an … | The system answer accurately captures Beatrice's relationship to Echidna and the task she was given, and all details ar… |
| rel-06 | correct | 1, 2 | supported | The royal candidates and their respective knights are: * **Crusch Karsten:** Felix Argyle (the Blue Knight) [2] * **Priscilla Bariel:** Al … | The system answer accurately identifies all five royal candidates and their respective knights, matching the key points… |
| rel-07 | incorrect | 9 | partially_supported | Joshua Juukulius is Julius Juukulius's younger brother [6]. Julius does not remember him because Joshua's name and existence were consumed … | The system answer claims that Julius forgot Joshua because *Joshua's* name was eaten, whereas according to the referenc… |
| rel-08 | correct | 1 | supported | Fortuna is Emilia’s aunt by blood, but she raised Emilia in the Great Elior Forest as her surrogate mother [5]. In Emilia's memories, Fortu… | The system answer accurately identifies Fortuna's relationship to Emilia and describes her death via Geuse's Unseen Han… |
| rel-09 | correct | không | supported | Subaru's father is named Kenichi Natsuki, and his mother is named Nahoko Natsuki [1][2][5]. | The system answer correctly identifies both Kenichi and Nahoko as Subaru's parents, and these facts are fully supported… |
| rel-10 | refused | không |  | Not found in the provided passages. |  |
| rel-11 | correct | 6, 7 | supported | In Volume 15, Beatrice forms a contract with **Subaru Natsuki** [5][6]. To persuade her to take his hand and leave her four-century-long lo… | The system answer accurately identifies Subaru Natsuki, includes the key phrase 'Pick me', states she becomes a contrac… |
| rel-12 | correct | không | supported | According to Volume 3's interlude, Ram serves Roswaal loyally without asking anything in return [1]. When Roswaal refers to Ram and her sis… | The system answer accurately reflects Ram's deep adoration and loyalty toward Roswaal as depicted in the Volume 3 inter… |
| rel-13 | correct | 6 | supported | Shaula is the self-proclaimed "Scorpion" and guardian of the Pleiades Watchtower who has lived there for four hundred years [1, 2, 4, 6]. S… | The system answer correctly identifies Shaula as the guardian of the Pleiades Watchtower and states she believes Subaru… |
| rel-14 | correct | không | supported | Emilia is contracted with the cat spirit Puck, who is also a Great Spirit [1][4][5]. | The system correctly identifies Puck as the cat spirit contracted with Emilia and notes he is a Great Spirit, matching … |
| multi-01 | partial | không | supported | In Volume 1, Subaru's first three deaths happen and are caused as follows: * **First death:** It happens in the loot cellar (loot house), c… | The system answer incorrectly states that the first death was caused by Elsa's blade, which contradicts the reference a… |
| multi-02 | correct | 7 | supported | In the Mathers domain arc (Volumes 5–9), Subaru faces the Witch Cult Archbishop representing **Sloth** (Petelgeuse Romanée-Conti) [5]. In c… | The system answer accurately identifies Petelgeuse as Sloth for Volumes 5-9, and lists Sirius (Wrath), Regulus (Greed),… |
| multi-03 | partial | 13 | partially_supported | In Volume 1, when Elsa attacks the loot house, Felt and Subaru are first saved from her initial strike when Felt leaps up and tackles Subar… | The system answer correctly identifies Reinhard stopping her in Volume 1 based on the reference, but misses who finally… |
| multi-04 | correct | không | partially_supported | Originally, Theresia van Astrea lost her life during the expedition to slay the White Whale fourteen years prior to the main story, when sh… | The system answer covers all the necessary factual points for correctness, but the cited passages do not mention the Wi… |
| multi-05 | correct | 2 | supported | After the battle against the White Whale, Rem was attacked by the Archbishops of the Seven Deadly Sins representing Gluttony (Lye Batenkait… | The system answer accurately captures all key points (attacked by Gluttony/Greed, name/memories eaten, forgotten by eve… |
| multi-06 | correct | 3, 5 | supported | Gluttony’s Authority targets memories and names in different ways: * **Crusch:** Gluttony ate her own memories [3], leaving her with memory… | The system answer accurately captures the differences in how Gluttony affected Crusch, Rem, and Julius according to the… |
| multi-07 | correct | 9, 12, 17 | supported | Through Echidna's tea parties in the Sanctuary, Subaru meets the Witches representing the following sins: * **Echidna**: Greed [5, 17] * **… | The system answer lists all the correct Witches and their respective sins, which matches the reference answer. All clai… |
| multi-08 | correct | không | supported | Based on the provided passages, following the battle of Pristella: - **Sirius Romanée-Conti** (the Archbishop of Wrath) was captured alive … | The system answer accurately identifies that Sirius was captured and Regulus was killed based on the text, while also m… |
| multi-09 | correct | 14 | supported | Following their harsh public duel in Volume 4—where Julius ruthlessly beat Subaru to teach him humility and earn his respect—their relation… | The system answer accurately covers all key points from the reference answer (Volume 4 duel, Volume 9 fighting Petelgeu… |
| sum-01 | correct | 7, 8 | supported | Natsume Subaru, an ordinary high schooler, is suddenly summoned to a fantasy capital. After being saved by a silver-haired half-elf girl wh… | The system answer accurately captures all the key events of Volume 1, including the summoning, badge retrieval, repeate… |
| sum-02 | correct | không | supported | At Roswaal Manor, Subaru experiences repeated loops (Return by Death) after dying multiple times from curses and mysterious attacks [1][3].… | The system answer accurately summarizes Subaru's experiences at Roswaal Manor in Volumes 2 and 3 based on the key point… |
| sum-03 | partial | 2, 4 | supported | The battle against the White Whale began with a preemptive strike led by Subaru and Rem, followed by the main expeditionary force engaging … | The system answer covers the battle details well based on the passages, but misses the crucial context of the alliance … |
| sum-04 | correct | không | partially_supported | The Sanctuary arc (Volumes 10–15) follows Subaru and his allies as they travel to the Sanctuary (the domain of Roswaal Mathers) in order to… | The system answer covers the key points of the arc accurately compared to the reference, but several major claims (such… |
| sum-05 | partial | 2 | supported | The Witch Cult attacked the water gate city of Pristella, seizing control towers and threatening to submerge the city [1]. Led by multiple … | The system answer correctly identifies the attack and the Archbishops involved, but misses several specific key points … |
| sum-06 | partial | không | supported | Subaru and his companions—including Emilia, Beatrice, Anastasia, Julius, Meili, and Ram—journeyed to the impassable Auguria Dunes to reach … | The system answer is faithful to the cited passages, but it misses several key plot points from the prompt's reference … |
| sum-07 | partial | 12, 13, 21, 22, 23 | supported | Volume 7, Chapter 5 tells the story of Wilhelm van Astrea and his late wife, Theresia [1][23]. Wilhelm ran away from his noble family at ag… | The system answer covers their meeting, Wilhelm's background, and the White Whale scene, but misses major narrative poi… |
| sum-08 | correct | 1, 2, 3 | supported | Rem and her older sister Ram were born as twin demons [1][2]. Among the demon race, twins were considered abominations because they were bo… | The system answer accurately captures all the key elements of Rem's backstory outlined in the reference answer, and eve… |
| sum-09 | partial | không | supported | Subaru finds himself transported across the border into the Holy Volakian Empire [1], a lawless country where the strong rule and violence … | The system answer covers how the adventure begins and is fully supported by the cited passages, but it misses several k… |
| oos-01 | refused | – |  | Not found in the provided passages. |  |
| oos-02 | refused | – |  | Not found in the provided passages. |  |
| oos-03 | refused | – |  | Not found in the provided passages. |  |
| oos-04 | refused | – |  | Not found in the provided passages. |  |
| oos-05 | refused | – |  | Not found in the provided passages. |  |
| oos-06 | refused | – |  | Not found in the provided passages. |  |
| oos-07 | refused | – |  | Not found in the provided passages. |  |
| oos-08 | refused | – |  | Not found in the provided passages. |  |
| oos-09 | refused | – |  | Not found in the provided passages. |  |
| oos-10 | refused | – |  | Not found in the provided passages. |  |
| oos-11 | refused | – |  | Not found in the provided passages. |  |
| oos-12 | refused | – |  | Not found in the provided passages. |  |
| oos-13 | refused | – |  | Not found in the provided passages. |  |
| oos-14 | refused | – |  | Not found in the provided passages. |  |
| oos-15 | refused | – |  | Not found in the provided passages. |  |

## Bộ câu hỏi khác

Các lần chạy trên một file câu hỏi khác cùng id (vd. bản tiếng Việt). So sánh từng câu với một lần chạy trên `golden_set.json` cùng mã và cấu hình, không so với bảng ở trên.

| Lần chạy | Loại | File câu hỏi | Nhãn | Chế độ | dev Hit@6 / Điểm | Đúng | Từ chối nhầm | Ngoài phạm vi xử lý đúng |
|---|---|---|---|---|---|---|---|---|
| 20261005-012550-generation-lang-vi | generation | `data/eval/golden_set_vi.json` | lang-vi | agent | 79.8% | 70.2% | 7.5% | 100.0% |
| 20261005-023444-generation-lang-vi-glossary-dev | generation | `data/eval/golden_set_vi.json` | lang-vi-glossary-dev | agent | 84.3% | 76.1% | 3.0% | 100.0% |
| 20261005-030534-generation-lang-vi-glossary | generation | `data/eval/golden_set_vi.json` | lang-vi-glossary | agent | 83.6% | 74.6% | 3.0% | 100.0% |
