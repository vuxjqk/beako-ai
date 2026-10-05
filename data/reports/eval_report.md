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

### Phân loại lỗi — 20261005-005527-generation-lang-en

Bằng chứng có nằm trong các chunk đưa cho LLM không? Hàng thứ nhất mà sai là lỗi **đọc/suy luận** (sửa prompt/mô hình); hàng thứ hai là lỗi **truy xuất** (sửa giai đoạn tìm kiếm).

| | Đúng | Một phần | Sai | Từ chối | Trả về rỗng |
|---|---|---|---|---|---|
| Bằng chứng có trong ngữ cảnh | 37 | 7 | 1 | 1 | 0 |
| Bằng chứng KHÔNG có trong ngữ cảnh | 14 | 2 | 2 | 3 | 0 |

| Split / loại | n | Đúng | Điểm |
|---|---|---|---|
| dev | 47 | 74.5% | 81.9% |
| test | 20 | 80.0% | 85.0% |
| fact | 35 | 77.1% | 80.0% |
| relationship | 14 | 85.7% | 89.3% |
| multi_hop | 9 | 77.8% | 88.9% |
| summary | 9 | 55.6% | 77.8% |

- Trung thực (trên 63 câu có trả lời): được hỗ trợ 88.9%, một phần 7.9%, không được hỗ trợ 0.0%, không trích nguồn 3.2%; trích ít nhất một chunk chứa bằng chứng chuẩn 61.9%.
- Câu có đáp án mà LLM trả về rỗng (lỗi phía nhà cung cấp, không phải từ chối): 0.0%.
- Ngoài phạm vi (15 câu): xử lý đúng 100.0%, bịa câu trả lời 0.0%; theo loại: general 100.0%, not_in_text 100.0%, false_premise 100.0%, beyond_corpus 100.0%.
- Chi phí trung bình mỗi câu: 10788.6 token vào, 142.9 token ra (giám khảo thêm 1989.7 token); truy xuất 182.3 ms, LLM 13536.5 ms.
- Cấu hình: `gemini` / `gemini-3.5-flash-lite`, temperature 0.2, tối đa 700 token ra, top 6, chunker `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457).

### Chi tiết từng câu — 20261005-005527-generation-lang-en

| Câu | Kết quả | Bằng chứng trong ngữ cảnh (hạng) | Trung thực | Câu trả lời | Nhận xét giám khảo |
|---|---|---|---|---|---|
| fact-01 | refused | không |  | Not found in the provided passages. |  |
| fact-02 | correct | không | supported | Subaru calls the power that sends him back in time when he dies **Return by Death** [1]. | The system answer correctly identifies the name of the power as 'Return by Death', matching the reference answer, and t… |
| fact-03 | correct | 3 | supported | When Subaru first asks the silver-haired girl her name, she gives her name as “Satella” [3]. | The system answer correctly identifies that she gave the name "Satella", which is supported by the cited passage. |
| fact-04 | correct | 1 | supported | After Subaru saves her, the silver-haired girl tells him that her name is Emilia ("Just Emilia") [1]. Earlier in the volume, she had initia… | The system answer correctly identifies the name as Emilia based on the text, and correctly cites the passages indicatin… |
| fact-05 | correct | 6 | supported | Subaru dies for the third time in Volume 1 when he is stabbed in the back by one of the thugs (Dumber) with a knife as he tries to leave an… | The system answer accurately captures how Subaru dies according to both the reference answer and the cited text. |
| fact-06 | correct | 11 | no_citations | When Subaru was summoned to the other world, his belongings consisted of: * A cell phone * A wallet (filled with video rental store members… | The system answer contains all the correct key points required by the reference answer, but it is rated as unsupported … |
| fact-07 | correct | 3 | supported | Elsa is known as the "Bowel Hunter" [1][3][5]. | The system answer correctly identifies Elsa's nickname as the 'Bowel Hunter', which is supported by the text in the cit… |
| fact-08 | correct | 6, 8, 9 | supported | In Volume 2, Rem uses a spiked iron ball on a long chain (a morning star) against Subaru in the forest [8][9], the same weapon that had pre… | The system answer accurately identifies the weapon as a morning star (spiked iron ball on a long chain) and notes that … |
| fact-09 | incorrect | không | supported | Based on Beatrice's explanation that a curse requires physical contact with the target, Subaru concludes that the source of the curse is lo… | The system answer identifies the village and the shaman as the source of the curse, but misses the key points required … |
| fact-10 | correct | 1, 3 | supported | According to Volume 3's interlude on Rem, Ram lost her horn when she turned around and embraced Rem to shield her, taking the blow for her … | The system answer correctly identifies that Ram shielded Rem and took the blow which severed her horn, and these detail… |
| fact-11 | correct | không | supported | Crusch Karsten possesses the **blessing of wind reading**, which allows her to perceive things invisible to the eye, such as discerning whe… | The system answer correctly identifies the blessing of wind reading, which matches the key points, and all details prov… |
| fact-12 | correct | 2 | supported | Petelgeuse introduces his title to Subaru in the cave by pointing at him with the fingers of both hands, cackling, and declaring: “—Archbis… | The system answer accurately captures the key points from the reference answer (Archbishop of the Witch Cult, Sloth) an… |
| fact-13 | partial | 2, 6, 10 | supported | When Subaru begs Rem to run away with him to start over elsewhere [4], Rem responds with a very sad face, saying, "I cannot run away with y… | The system answer correctly captures Rem's response and Subaru's subsequent statement to her based on the text, but it … |
| fact-14 | correct | 1 | supported | In return for an alliance between Emilia and Crusch, Subaru offers the magic crystal mining rights in the Great Elior Forest, along with in… | The system answer correctly identifies both the magic crystal mining rights in the Great Elior Forest and the White Wha… |
| fact-15 | correct | 7, 8, 15, 17 | supported | The White Whale is brought down when the Great Flugel Tree is felled onto it, crushing its enormous body and pinning it to the ground [7]. … | The system answer accurately identifies that Wilhelm delivered the final blow and the whale was brought down by the Gre… |
| fact-16 | incorrect | 2 | supported | Petelgeuse finally dies after surviving being crushed by a rock slide [2] and slashed by Julius [3]. Clinging desperately to a dragon carri… | The system answer describes a completely different sequence of events (Petelgeuse surviving the rock slide, climbing in… |
| fact-17 | correct | không | supported | Otto Suwen's blessing is the blessing of language, which allows him to hear and understand voices that others cannot, such as conversing wi… | The system answer correctly identifies the blessing of language and its ability to let him hear voices, converse with a… |
| fact-18 | correct | không | supported | Garfiel possesses the **blessing of the earth spirit** [2]. In battle, it requires him to have his feet planted on the ground [2]. It grant… | The system answer correctly identifies the blessing of the earth spirit and its combat effects, including healing and e… |
| fact-19 | correct | không | supported | The barrier around the Sanctuary affects people of mixed blood (half-bloods/demi-humans) and half-elves like Emilia, trapping them inside s… | The system answer accurately identifies who is affected by the barrier, that it traps them inside, and that it causes t… |
| fact-20 | partial | không | supported | The three Trials of the Sanctuary tomb consist of: 1. **The first Trial**: To "face your past" [10, 11]. 2. **The second Trial**: To behold… | The system answer successfully identifies the first two trials using the cited passages, but fails to provide the third… |
| fact-21 | refused | 10 |  | Not found in the provided passages. |  |
| fact-22 | correct | 2 | supported | According to Echidna, the Great Rabbit is a demon beast that can infinitely divide and propagate from a single individual, forming a horde … | The system answer accurately captures all key points from the reference answer (one of the three great demon beasts, a … |
| fact-23 | correct | 2 | supported | Regulus Corneas dies by drowning [1, 2, 4]. After breaking through the stone pavement and sinking deep underground, he is trapped in a narr… | The system answer accurately captures how Regulus dies by drowning underground after being driven into the ground/pavem… |
| fact-24 | correct | 1 | supported | The Archbishop charged with Wrath is Sirius Romanée-Conti [1]. | The system answer correctly provides both the full name (Sirius Romanée-Conti) and the sin (Wrath), and all information… |
| fact-25 | correct | 1, 3 | supported | The Archbishop of Lust introduces herself as Capella Emerada Lugunica [1][2]. | The system answer correctly identifies the full name used by the Archbishop of Lust as Capella Emerada Lugunica, which … |
| fact-26 | correct | 11 | supported | The two Archbishops of the Witch Cult who attack Crusch and Rem's convoy are **Regulus Corneas** (the Archbishop of **Greed**) and **Lye Ba… | The system correctly identified Regulus Corneas (Greed) and Lye Batenkaitos (Gluttony) as the two archbishops, and all … |
| fact-27 | correct | 4 | supported | When Reid Astrea faces the group in the Pleiades Watchtower, he fights using two chopsticks as weapons [1, 2, 5]. | The system answer correctly identifies that Reid Astrea fights with chopsticks, matching both the reference answer and … |
| fact-28 | incorrect | không | supported | When Subaru wakes up with amnesia in the green room of the Pleiades Watchtower in Volume 23, his memories of the moments right before wakin… | The system answer describes a minor, temporary memory gap within the watchtower rather than the major amnesia where Sub… |
| fact-29 | correct | không | supported | When Rem wakes up at the start of Volume 26, her knees buckle and she is unable to stand, as if her thoughts cannot reach her legs [1]. Fur… | The system answer accurately captures the state in which Rem wakes up (unable to stand, memory loss, distrust/loathing … |
| fact-30 | correct | 1, 3 | no_citations | Abel reveals himself to be Vincent Abelks, the seventy-seventh emperor of the Holy Volakian Empire (though currently removed from his thron… | The system answer is correct regarding the light novel's content and contains all key points, but it is unsupported bec… |
| fact-31 | correct | 3 | supported | Natsumi Schwartz is an alias created through cross-dressing and a complete makeover by **Subaru Natsuki** [1, 2]. This persona is created i… | The system answer accurately explains that Natsumi Schwartz is Subaru's female disguise used to bypass guards and enter… |
| fact-32 | correct | 1, 4 | supported | Regulus Corneas represents the sin of **Greed** as an Archbishop of the Witch Cult [1]. | The system answer correctly identifies that Regulus Corneas represents the sin of Greed, which is supported by the cite… |
| fact-33 | correct | 5 | supported | The mock duel on the parade ground of the knights' garrison is utterly one-sided [2, 3, 5]. When Ferris signals the start, Subaru attempts … | The system answer accurately captures the one-sided nature of the duel, the use of wooden swords, and Subaru's persiste… |
| fact-34 | refused | không |  | Not found in the provided passages. |  |
| fact-35 | correct | 2, 7 | supported | Subaru's primary reason for setting out for the Pleiades Watchtower in Volume 21 is to find a way to save Rem [7], who is trapped in a coma… | The system answer accurately identifies the reason for the journey (saving Rem) and the method for crossing the dunes (… |
| rel-01 | correct | 2 | supported | Ram and Rem are twin sisters belonging to the horned demon race [1][2][3][4]. **Ram** is the older twin sister [2][3][4]. | The system answer correctly identifies that Ram and Rem are twin sisters belonging to the horned demon race and that Ra… |
| rel-02 | correct | 5 | supported | Wilhelm van Astrea's wife was Theresia van Astrea (the previous Sword Saint) [5]. Before marrying into the Astrea family, Wilhelm's surname… | The system answer accurately identifies Theresia van Astrea as the previous Sword Saint and Wilhelm's old surname as Tr… |
| rel-03 | correct | 3 | supported | Wilhelm and Theresia are Reinhard's grandparents [1][2]. Reinhard's parents are Heinkel and Louanna [3]. | The system answer correctly identifies Reinhard as the grandson of Wilhelm and Theresia and lists Heinkel and Louanna a… |
| rel-04 | partial | không | supported | Frederica Baumann and Garfiel are brother and sister [1]. Because they are siblings, Frederica is also of mixed blood [1]. They share certa… | The system answer correctly identifies them as brother and sister, but misses the key point that they do not get on wel… |
| rel-05 | correct | không | supported | Beatrice is the daughter of the Witch Echidna [3][5], whom Beatrice refers to as "Mother" [5]. Echidna entrusted Beatrice with the archive … | The system answer accurately identifies Beatrice as Echidna's daughter/mother relationship, mentions the archive of for… |
| rel-06 | correct | 1, 3 | supported | The knights of the candidates for the royal selection announced in Volume 4 are: * **Crusch Karsten:** Felix Argyle (the Blue Knight) [3] *… | The system answer accurately lists all five candidates and their respective knights (including Subaru as Emilia's self-… |
| rel-07 | correct | 8 | supported | Joshua Juukulius is Julius’s younger brother (technically a cousin who was adopted into the family after his father Klein Juukulius passed … | The system answer accurately identifies Joshua's relationship to Julius and explains why Julius doesn't remember him du… |
| rel-08 | correct | 1 | supported | To Emilia, Fortuna is her surrogate mother (though Fortuna also refers to herself as her aunt/sister-in-law's relation in passing) and fami… | The system answer accurately identifies Fortuna as Emilia's mother/surrogate mother and details her death by a chest-pi… |
| rel-09 | correct | không | supported | Subaru's father is Kenichi Natsuki, and his mother is Nahoko Natsuki [2][6]. | The system answer correctly identifies both Subaru's father (Kenichi) and mother (Nahoko), and these names are both sup… |
| rel-10 | refused | không |  | Not found in the provided passages. |  |
| rel-11 | correct | 6, 7, 8 | supported | Beatrice forms a contract with **Subaru Natsuki** in Volume 15 [8]. To persuade her, Subaru tells her: * That while he cannot comprehend he… | The system correctly identifies Subaru Natsuki as the person Beatrice forms a contract with, includes the required phra… |
| rel-12 | correct | không | supported | According to Rem’s interlude in Volume 3, Ram loyally serves Roswaal without asking anything in return [2]. She displays total adoration an… | The system answer accurately captures Ram's adoration, loyalty, and feelings toward Roswaal based on the reference answ… |
| rel-13 | correct | 6 | supported | Shaula is a guardian of the Pleiades Watchtower [2][4] who can transform into a giant black scorpion [2][4] and has a scorpion-tail braid [… | The system answer correctly identifies Shaula as the guardian of the Pleiades Watchtower and states that she believes S… |
| rel-14 | correct | không | supported | Emilia has a pact with Puck [1], and she has also formed pacts with lesser spirits [1][5]. | The system answer correctly identifies Puck as the spirit contracted with Emilia, which matches both the reference and … |
| multi-01 | correct | không | supported | In Volume 1, Subaru's first three deaths occur at the following locations and from the following causes: * **First Death:** Happens at the … | The system correctly identifies the three deaths, their locations, and their causes according to both the novel and the… |
| multi-02 | correct | 11 | supported | In the Mathers domain arc (Volumes 5–9), Subaru faces the Archbishop of **Sloth** (Petelgeuse Romanée-Conti) [1][2], while the White Whale—… | The system correctly identifies the sins involved in both arcs based on the text (Sloth for Volumes 5-9; Wrath, Greed, … |
| multi-03 | partial | 13 | supported | In Volume 1, when Elsa attacks Subaru and Felt in the loot house, **Felt** saves Subaru by leaping up and tackling him out of the way of El… | The system answer correctly identifies who stopped Elsa in Volume 1 (though it mentions Felt saving Subaru initially an… |
| multi-04 | correct | không | partially_supported | Originally, Theresia van Astrea lost her blessing of the Sword Saint [12] and died during the expedition against the White Whale fourteen y… | The system answer accurately captures how Theresia died and what happened in Pristella, but the cited passages do not e… |
| multi-05 | correct | 1, 6 | supported | After the battle against the White Whale, Rem was attacked on the road by the Archbishops of the Seven Deadly Sins, Regulus (Greed) and Lye… | The system answer accurately describes what happened to Rem after the battle against the White Whale using the cited te… |
| multi-06 | correct | 3, 5 | supported | Gluttony’s Authority targets people’s names and memories in different ways [3]: * **Crusch:** Gluttony stole her **own memories**, leaving … | The system answer accurately captures the differences between how Gluttony affected Crusch, Rem, and Julius, and every … |
| multi-07 | correct | 7, 13 | supported | The Witches Subaru meets through Echidna’s tea parties in the Sanctuary, and the sin each represents, are: * **Echidna** – The Witch of Gre… | The system answer correctly lists all the Witches met through Echidna's tea parties along with their respective sins, p… |
| multi-08 | correct | 12 | supported | Following the battle of Pristella, the outcomes for the Archbishops were: * **Sirius Romanée-Conti (Wrath):** Captured alive and bound in c… | The system answer accurately states the outcome for the Archbishops (Regulus killed, Sirius captured) as required by th… |
| multi-09 | partial | 15 | partially_supported | From their hostile duel in Volume 4—where Julius thoroughly beat Subaru to humble his arrogance—their relationship evolves significantly [5… | The system answer captures the evolution of their relationship well, but misses the crucial Volume 9 event (fighting Pe… |
| sum-01 | correct | 17 | supported | Transported suddenly to a fantasy capital, Natsuki Subaru is rescued from thugs by a silver-haired half-elf girl named Emilia (whom he call… | The system answer covers all the key points accurately and every single claim made is directly supported by the provide… |
| sum-02 | correct | không | partially_supported | At Roswaal Manor, Subaru experiences repeated loops using "Return by Death" to overcome a deadly multi-day cycle [3][5]. In his early loops… | The system answer covers the key points and matches the reference answer well, but the final paragraph contains several… |
| sum-03 | partial | 28 | partially_supported | The expeditionary force under Crusch Karsten, with Wilhelm van Astrea as captain and Subaru Natsuki utilizing his knowledge and the Witch's… | The system answer covers most of the battle details well and is mostly supported, but it includes Subaru's knowledge an… |
| sum-04 | correct | không | supported | The Sanctuary arc (Volumes 10–15) follows Subaru and his allies as they travel to the Sanctuary (or Graveyard) to free the half-bloods trap… | The system answer correctly summarizes the Sanctuary arc, hitting all the key narrative points (barrier trapping half-b… |
| sum-05 | partial | 1 | supported | The Witch Cult’s attack on the Water Gate City of Pristella began with a malicious broadcast hijacking the city’s metia system, wherein Cap… | The system answer is faithful to the provided passages, but it misses several major key points required by the referenc… |
| sum-06 | correct | 6, 7 | supported | The journey to the Pleiades Watchtower began as the party traveled east from the manor to the Auguria Dunes [3], switching to a sturdy Gila… | The system answer accurately summarizes the journey to and the start of events in the Pleiades Watchtower (including go… |
| sum-07 | partial | 12, 13, 24, 26, 29, 30, 31, 32, 33 | supported | Wilhelm Trias ran away from his baronial family at fourteen to join the royal army [1, 2]. Immersing himself in the sword, he fought ruthle… | The system answer is faithful to the cited text, but it misses the final key point from the reference answer: Wilhelm t… |
| sum-08 | correct | 1, 2, 3 | supported | Rem was born as an identical twin in a demon village. Because demons prized individual strength and viewed twins—who possessed only one hor… | The system answer accurately summarizes Rem's backstory based on the provided text, capturing all key points such as tw… |
| sum-09 | partial | 4 | partially_supported | Subaru Natsuki is suddenly sent flying from Lugunica across the southern border into the Holy Volakian Empire [3]. He wakes up as a prisone… | The system answer misses the disguise as Natsumi Schwartz, and that specific claim is not supported by the provided tex… |
| oos-01 | refused | – |  | Not found in the provided passages. |  |
| oos-02 | refused | – |  | Not found in the provided passages. |  |
| oos-03 | refused | – |  | Not found in the provided passages. |  |
| oos-04 | refused | – |  | Not found in the provided passages. |  |
| oos-05 | refused | – |  | Not found in the provided passages. |  |
| oos-06 | refused | – |  | Not found in the provided passages. |  |
| oos-07 | refused | – |  | Not found in the provided passages. |  |
| oos-08 | corrected_premise | – |  | Based on the provided passages, Rem did not cut off Ram's horn. Instead, when their village was attacked, an enemy attacked Ram, and Ram sh… | The system correctly points out that Rem did not cut off Ram's horn and explains how Ram actually lost it. |
| oos-09 | refused | – |  | Not found in the provided passages. |  |
| oos-10 | refused | – |  | Not found in the provided passages. |  |
| oos-11 | refused | – |  | Not found in the provided passages. |  |
| oos-12 | refused | – |  | Not found in the provided passages. |  |
| oos-13 | refused | – |  | Not found in the provided passages. |  |
| oos-14 | refused | – |  | Not found in the provided passages. |  |
| oos-15 | corrected_premise | – |  | Subaru is an only child and does not have a younger sister [7]. | The system points out that Subaru is an only child and does not have a younger sister. |

## Bộ câu hỏi khác

Các lần chạy trên một file câu hỏi khác cùng id (vd. bản tiếng Việt). So sánh từng câu với một lần chạy trên `golden_set.json` cùng mã và cấu hình, không so với bảng ở trên.

| Lần chạy | Loại | File câu hỏi | Nhãn | Chế độ | dev Hit@6 / Điểm | Đúng | Từ chối nhầm | Ngoài phạm vi xử lý đúng |
|---|---|---|---|---|---|---|---|---|
| 20261005-012550-generation-lang-vi | generation | `data/eval/golden_set_vi.json` | lang-vi | agent | 79.8% | 70.2% | 7.5% | 100.0% |
