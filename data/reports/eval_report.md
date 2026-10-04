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

### Điểm theo loại câu và split, từng lần chạy

| Lần chạy | Chế độ | fact | relationship | multi_hop | summary | dev | test | Ngoài phạm vi |
|---|---|---|---|---|---|---|---|---|
| 20261004-021903-generation-baseline | simple | 52.9% | 67.9% | 22.2% | 33.3% | 50.0% | 47.5% | 100.0% |
| 20261004-032603-generation-s5-hybrid-boost-cand100 | simple | 64.3% | 78.6% | 27.8% | 27.8% | 55.3% | 62.5% | 100.0% |
| 20261004-044909-generation-s6-agent-all-v2 | agent | 84.3% | 89.3% | 72.2% | 50.0% | 79.8% | 77.5% | 100.0% |
| 20261004-050946-generation-s6-sim-route | auto (route, simulated) | 64.3% | 78.6% | 44.4% | 50.0% | 58.5% | 72.5% | 100.0% |
| 20261004-050949-generation-s6-sim-escalate | auto (escalate, simulated) | 80.0% | 78.6% | 55.6% | 55.6% | 73.4% | 72.5% | 100.0% |
| 20261004-050951-generation-s6-sim-route-escalate | auto (route+escalate, simulated) | 80.0% | 78.6% | 66.7% | 50.0% | 72.3% | 77.5% | 100.0% |

### Phân loại lỗi — 20261004-050951-generation-s6-sim-route-escalate

Bằng chứng có nằm trong các chunk đưa cho LLM không? Hàng thứ nhất mà sai là lỗi **đọc/suy luận** (sửa prompt/mô hình); hàng thứ hai là lỗi **truy xuất** (sửa giai đoạn tìm kiếm).

| | Đúng | Một phần | Sai | Từ chối | Trả về rỗng |
|---|---|---|---|---|---|
| Bằng chứng có trong ngữ cảnh | 31 | 11 | 0 | 1 | 0 |
| Bằng chứng KHÔNG có trong ngữ cảnh | 7 | 12 | 2 | 3 | 0 |

| Split / loại | n | Đúng | Điểm |
|---|---|---|---|
| dev | 47 | 55.3% | 72.3% |
| test | 20 | 60.0% | 77.5% |
| fact | 35 | 71.4% | 80.0% |
| relationship | 14 | 57.1% | 78.6% |
| multi_hop | 9 | 44.4% | 66.7% |
| summary | 9 | 11.1% | 50.0% |

- Trung thực (trên 63 câu có trả lời): được hỗ trợ 93.7%, một phần 6.3%, không được hỗ trợ 0.0%, không trích nguồn 0.0%; trích ít nhất một chunk chứa bằng chứng chuẩn 60.3%.
- Câu có đáp án mà LLM trả về rỗng (lỗi phía nhà cung cấp, không phải từ chối): 0.0%.
- Ngoài phạm vi (15 câu): xử lý đúng 100.0%, bịa câu trả lời 0.0%; theo loại: general 100.0%, not_in_text 100.0%, false_premise 100.0%, beyond_corpus 100.0%.
- Chi phí trung bình mỗi câu: 8024.8 token vào, 112.7 token ra (giám khảo thêm 1843.2 token); truy xuất 205.5 ms, LLM 4920.9 ms.
- Cấu hình: `gemini` / `gemini-3.5-flash-lite`, temperature 0.2, tối đa 700 token ra, top 6, chunker `v1 target=350 max=450 min=120 scene=175 overlap=80` (10457).

### Chi tiết từng câu — 20261004-050951-generation-s6-sim-route-escalate

| Câu | Kết quả | Bằng chứng trong ngữ cảnh (hạng) | Trung thực | Câu trả lời | Nhận xét giám khảo |
|---|---|---|---|---|---|
| fact-01 | correct | không | supported | In Volume 1, Chapter 2, Subaru is killed by **Elsa** (the Bowel Hunter) at the loot house [2, 4, 7]. She slashes his stomach open with a la… | The system answer correctly identifies Elsa as the killer and mentions that she slashes his stomach with a blade, align… |
| fact-02 | correct | 1 | supported | Subaru calls the power "Return by Death" [1]. | The system answer correctly identifies the name Subaru gives to his power as "Return by Death," which is fully supporte… |
| fact-03 | incorrect | không | supported | She gives the name Emilia, adding, "Just Emilia" [1]. | The system answer says the girl gives the name Emilia, which is supported by the cited passage, but the reference answe… |
| fact-04 | correct | 3 | supported | The silver-haired girl tells Subaru that her name is Emilia (specifically, "Just Emilia") [3]. | The system answer correctly identifies the name given by the girl as Emilia ('Just Emilia') based on the text and the r… |
| fact-05 | correct | 9 | supported | In Volume 1, Chapter 3, as Subaru tries to push past the three thugs in the alley, his legs suddenly twist and he falls to his knees [8, 9]… | The system answer correctly includes all key points regarding Subaru's third death, and all statements are directly sup… |
| fact-06 | partial | không | supported | Subaru had his cell phone, which was his priciest and most useful possession from home, along with a few other personal belongings [1]. | The system answer mentions the cell phone and 'other personal belongings' which are present in the passage, but it is i… |
| fact-07 | correct | 2, 6 | supported | Elsa is known by the alias "Bowel Hunter" (or Elsa "The Bowel Hunter" Gramhilde) [1][2][6]. | The system answer correctly identifies Elsa's nickname as the 'Bowel Hunter' and matches the details provided in the te… |
| fact-08 | partial | không | supported | Based on the provided passages, Rem uses an iron ball against Subaru [1][5]. Specifically, during the second loop, Subaru died from debilit… | The system answer identifies the weapon as an 'iron ball', which is mentioned in the passages, but it misses the specif… |
| fact-09 | correct | 4 | supported | Based on the provided passages, Subaru concludes that the casters of the curse were the demon beasts (specifically, a puppy/demon beast tha… | The system answer correctly identifies that the curse came from the demon beast/puppy that bit Subaru, referencing the … |
| fact-10 | correct | 1, 2 | supported | According to Rem's interlude, Ram lost her horn when it was severed by a flash of steel to the side of her head while she was shielding Rem… | The system answer accurately captures how Ram lost her horn while shielding Rem and taking a blow, and all details are … |
| fact-11 | correct | không | supported | Crusch Karsten's blessing (divine protection) is the **blessing of wind reading**, which allows her to discern falsehoods and judge that wh… | The system answer correctly identifies Crusch's blessing as the blessing of wind reading, which is fully supported by t… |
| fact-12 | correct | 1, 3 | supported | Petelgeuse introduces his title by staying bent over after bowing, twisting only his head to face forward, and stating: "—Archbishop of Sin… | The system answer correctly identifies Petelgeuse's title as the Archbishop of Sin of the Witch Cult entrusted with Slo… |
| fact-13 | partial | 2, 3 | supported | Rem responds with a very sad face, saying, “I cannot run away with you, Subaru,” and explains that when talking about the future, people ne… | The system answer correctly provides Rem's response based on the text, but fails to state what Subaru tells her afterwa… |
| fact-14 | correct | 1 | supported | In return for an alliance between Emilia and Crusch, Subaru offers the magic crystal mining rights in the Great Elior Forest in addition to… | The system answer includes all key points from the reference answer and matches the text provided in the cited passage. |
| fact-15 | correct | 1 | supported | Based on the provided passages, a great tree crashes straight into the White Whale from above, pressing it down and immobilizing it under i… | The system answer correctly identifies that Wilhelm delivered the final blow and explains how the whale was brought dow… |
| fact-16 | correct | 1 | supported | Based on the provided passages, Petelgeuse meets his end after being struck by Julius's rainbow-colored sword blow, which scorches the accu… | The system answer correctly identifies that Julius's rainbow sword struck Petelgeuse and that he was crushed by a rock … |
| fact-17 | correct | 5 | supported | Otto Suwen's blessing allows him to understand the voices and language of living creatures (such as Zodda bugs, family land dragons, and cr… | The system answer accurately identifies Otto's blessing (the blessing of language/understanding voices and language of … |
| fact-18 | correct | không | supported | Based on the provided passages, Garfiel possesses the blessing of the earth spirit [3]. In battle, this blessing gives him the following ab… | The system answer correctly identifies the blessing as the blessing of the earth spirit and lists its combat abilities,… |
| fact-19 | partial | không | supported | Based on the provided passages, the barrier around the Sanctuary affects people who carry mixed human and demi-blood (mixed-blood people), … | The system answer correctly identifies people of mixed blood and that the barrier traps them inside, but misses the key… |
| fact-20 | partial | không | supported | The three Trials of the Sanctuary tomb consist of: 1. **Facing the past** [9]. 2. **Beholding the unknowable present** (a Trial to make the… | The system answer correctly identifies the first two trials based on the text, but fails to actually state what the thi… |
| fact-21 | refused | 4 |  | Not found in the provided passages. |  |
| fact-22 | correct | 2 | supported | According to Echidna, the Great Rabbit is a demon beast that can infinitely divide from a single individual, meaning they all began from th… | The system answer accurately captures all the key points from the reference answer and is fully backed by the provided … |
| fact-23 | correct | 4, 5 | supported | Regulus Corneas dies by drowning [3][4]. After breaking through the stone pavement and sinking deep underground, he is trapped as the city … | The system answer accurately describes how Regulus dies (drowning underground after sinking deep into the ground) and i… |
| fact-24 | correct | 1, 3 | supported | The full name of the Archbishop is Sirius Romanée-Conti, and she is charged with Wrath [1][2][3]. | The system answer correctly identifies Sirius Romanée-Conti and her sin (Wrath), matching the reference answer, and all… |
| fact-25 | correct | 1, 2, 6 | supported | The Archbishop of Lust introduces herself as Capella Emerada Lugunica [1][3][4]. | The system correctly identified the full name Capella Emerada Lugunica used by the Archbishop of Lust in Volume 17, whi… |
| fact-26 | refused | không |  | Not found in the provided passages. |  |
| fact-27 | correct | 4 | supported | When Reid Astrea faces the group in the Pleiades Watchtower, he fights using a pair of wooden chopsticks as his weapons [1, 2, 5]. | The system answer correctly identifies that Reid Astrea fights using a pair of wooden chopsticks as weapons, which is e… |
| fact-28 | incorrect | không | supported | Based on the provided passages, after Subaru leaves Emilia and the others to check if he has a cheat ability and concludes he is powerless … | The system answer incorrectly identifies the last thing Subaru remembers based on the immediate context of his recent a… |
| fact-29 | correct | 6 | supported | When Rem wakes up, she has the same symptoms that Crusch had: because her memories were stolen, she has forgotten herself and does not know… | The system answer accurately captures that Rem wakes up with memory loss (not knowing herself or Subaru) and aligns wit… |
| fact-30 | correct | 1 | supported | Abel reveals himself to be the seventy-seventh emperor of the Holy Volakian Empire [1]. | The system answer correctly identifies Abel as the seventy-seventh emperor of the Holy Volakian Empire, which matches b… |
| fact-31 | correct | 1 | supported | Natsumi Schwartz is an alias and persona created by Subaru Natsuki, who cross-dresses and transforms himself into this identity [1][4]. The… | The system answer accurately identifies Natsumi Schwartz as Subaru in disguise and explains the reasoning based on the … |
| fact-32 | correct | 1, 5 | supported | Regulus Corneas represents the sin of Greed as an Archbishop of the Witch Cult [1][2][3][5]. | The system answer correctly identifies the sin of Greed for Regulus Corneas, which matches the reference answer and is … |
| fact-33 | correct | 5 | supported | The mock duel between Subaru and Julius at the parade square of the knights' garrison is excessively one-sided, turning into a severe beati… | The system answer accurately describes the one-sided mock duel between Subaru and Julius based on the text, capturing t… |
| fact-34 | correct | 6 | supported | During the battle in Pristella, Julius fought Roy Alphard, the Archbishop of Gluttony [1, 5, 8]. Alphard ultimately overpowered Julius, sha… | The system answer covers all the required key points accurately and every single claim is fully supported by the provid… |
| fact-35 | partial | 2 | supported | Based on the provided passages, the reason Subaru's group sets out for the Pleiades Watchtower is not explicitly detailed. However, the pas… | The system correctly explains how they plan to cross the dunes using Anastasia's secret path (supported by the text), b… |
| rel-01 | correct | 5 | supported | Ram and Rem are twin sisters [1][5]. Ram is the older twin, and Rem is the younger twin [5]. | The system answer accurately states that Ram and Rem are twin sisters and that Ram is the older twin, which matches bot… |
| rel-02 | correct | 6 | supported | Wilhelm van Astrea's wife was Theresia van Astrea (the previous Sword Saint) [6]. Before marrying into the Astrea family, his surname was T… | The system answer correctly identifies Theresia van Astrea as the previous Sword Saint and Trias as Wilhelm's former su… |
| rel-03 | correct | 1 | supported | Based on the provided passages, Reinhard van Astrea is the grandson of Wilhelm and Theresia [1]. His parents are Heinkel (Wilhelm and There… | The system answer accurately identifies Reinhard as the grandson of Wilhelm and Theresia and correctly lists his parent… |
| rel-04 | partial | không | supported | Frederica and Garfiel are older sister and younger brother (siblings) [1][3][6]. | The system answer correctly identifies them as older sister and younger brother, but misses the key point that they do … |
| rel-05 | partial | không | supported | Beatrice is like a daughter to Echidna (or her daughter) [1], and Echidna is deeply related to her birth [6]. Echidna also made a pact with… | The system answer correctly identifies Beatrice's relationship to Echidna (as a daughter/like a daughter) and mentions … |
| rel-06 | correct | 2, 4 | supported | Based on the provided passages, the knights of the candidates for the royal selection are: * **Crusch Karsten:** Felix Argyle (the Blue Kni… | The system answer accurately identifies the knights for each of the royal candidates based on the text, and every claim… |
| rel-07 | partial | không | supported | Joshua Juukulius is Julius’s younger brother [6]. Regarding why Julius does not remember him, the provided passages do not contain enough i… | The system correctly identified Joshua as Julius's younger brother based on the text, but failed to explain why Julius … |
| rel-08 | correct | 2 | supported | Fortuna is Emilia's surrogate mother, who also described herself as a mother figure and the younger sister of Emilia's father [1][6]. In Em… | The system answer accurately identifies Fortuna as Emilia's surrogate mother/mother figure and details her death by Geu… |
| rel-09 | partial | không | supported | Based on the provided passages, the name of Subaru's father is Kenichi Natsuki [2]. The passages do not contain the name of Subaru's mother… | The system answer correctly identifies the father's name (Kenichi Natsuki) based on the passage, but misses the mother'… |
| rel-10 | partial | 2 | supported | Based on the provided passages, Old Man Rom is Felt's surrogate father and the only family she could trust wholeheartedly (also referred to… | The system answer correctly identifies Rom's relationship to Felt and that they live in a mansion, but it fails to spec… |
| rel-11 | partial | không | supported | Beatrice forms a contract with Subaru [2]. To persuade her, Subaru says, “Beatrice—please save me” [1]. He also tells her that he can make … | The system answer correctly identifies Subaru and captures part of what he says to persuade her, but misses the crucial… |
| rel-12 | correct | không | supported | Based on the provided passages, Ram regards Roswaal as her lord and master, a man to whom she has given her soul [5]. She displays docility… | The system answer accurately captures Ram's adoration, loyalty, and feelings toward Roswaal as depicted in the text, an… |
| rel-13 | correct | không | supported | Based on the provided passages: * **Who Shaula is:** Shaula is the name of a star that is part of the constellation Scorpio [1][3], and she… | The system correctly identifies who Shaula is and who she believes Subaru is (her master, Flugel, based on the context … |
| rel-14 | correct | không | supported | Based on the provided texts, Emilia has a pact with the spirit Puck [3]. She also has formed pacts with lesser spirits [1, 5]. | The system answer correctly identifies Puck as the spirit contracted with Emilia, which is supported by the cited passa… |
| multi-01 | partial | 6 | supported | Based on the provided passages, the locations and causes of Subaru's first three deaths are: * **First death:** Happens when he and Satella… | The system correctly identifies the locations and general causes for the three deaths using the text, but misses specif… |
| multi-02 | correct | không | supported | In the Mathers domain arc (Volumes 5–9), the Witch Cult Archbishop Subaru faces is **Sloth** (Petelgeuse Romanée-Conti) [1], with **Greed**… | The system answer accurately identifies all the Archbishops and sins for both arcs, and all the claims are supported di… |
| multi-03 | partial | 12 | supported | In Volume 1, when Elsa attacks Subaru and Felt in the loot house, **Felt** saves Subaru by tackling him out of the path of Elsa's blade [1]… | The system answer correctly states that Elsa is not killed in Volume 1, but it fails to answer who stops her in Volume … |
| multi-04 | partial | 18 | partially_supported | Originally, Theresia van Astrea did not die during her first battle because she refused to fight [9], but she later died during the battle … | The system answer misses the key point that Reinhard cut her down in Pristella (which is omitted from the cited text). … |
| multi-05 | correct | 1, 9, 11 | supported | After the battle against the White Whale, while traveling with Crusch's forces, Rem was ambushed by the Witch Cult Archbishops Regulus Corn… | The system answer accurately describes what happened to Rem based on the text and all facts are supported by the provid… |
| multi-06 | correct | 3, 5 | supported | Based on the provided passages, Gluttony's Authority affects its victims differently: * **Crusch:** Gluttony stole her own memories, leavin… | The system answer accurately compares the effects of Gluttony on Crusch, Rem, and Julius according to both the referenc… |
| multi-07 | correct | 10 | supported | Subaru meets the following Witches during the tea parties in the Sanctuary, along with the sin each represents: * **Echidna** – Witch of Gr… | The system answer correctly lists all six Witches and their corresponding sins, and every claim is directly supported b… |
| multi-08 | refused | không |  | Not found in the provided passages. |  |
| multi-09 | partial | không | supported | From their brutal public duel in Volume 4—where Julius thoroughly beat a reckless and hostile Subaru to teach him his place—their relations… | The system answer correctly tracks their relationship evolution into Pristella, but misses the crucial post-Pristella d… |
| sum-01 | correct | 7 | partially_supported | Natsuki Subaru is abruptly summoned to a fantasy royal capital. Shortly after arriving, he is attacked by thugs, but a silver-haired half-e… | The correctness is correct as it hits all key points of the volume. However, the faithfulness is partially supported be… |
| sum-02 | refused | không |  | Not found in the provided passages. |  |
| sum-03 | partial | 11, 17, 19 | supported | In Volume 7, the battle against the White Whale begins with a successful preemptive strike led by Subaru and Rem, who draw the beast out an… | The system answer gives a good summary of the battle itself using the cited passages, but it completely misses the cruc… |
| sum-04 | partial | không | partially_supported | The Sanctuary arc (Volumes 10–15) follows Subaru and his companions as they travel to the Sanctuary—a domain tied to Emilia’s heritage and … | The system answer is missing several key points required by the prompt (such as Beatrice's contract and Garfiel killing… |
| sum-05 | partial | 3 | supported | The Witch Cult—led by four Archbishops of the Seven Deadly Sins: Sirius (Wrath), Regulus (Greed), Capella (Lust), and Lye/Alphard (Gluttony… | The system answer correctly identifies the four Archbishops involved in the attack based on the text, but misses severa… |
| sum-06 | partial | không | supported | The group traveled across the Auguria Dunes toward the Pleiades Watchtower, facing heavy miasma, the three-times-daily sandstorms known as … | The system answer is faithful to the provided text passages, but it is missing several key elements required by the pro… |
| sum-07 | partial | 12, 13 | supported | Wilhelm, a younger son of the Trias family, ran away from home at fourteen after an argument and joined the royal army during the Demi-huma… | The system answer only summarizes the first half of the chapter (Wilhelm's background and meeting Theresia), completely… |
| sum-08 | partial | 1, 2, 3 | partially_supported | According to Volume 3's interlude and related chapters, Rem's backstory centers on her upbringing as a demon twin [1][2]. The demon race re… | The system answer correctly identifies the core elements of Rem's backstory, but citation [12] and [13] (from Chapter 4… |
| sum-09 | partial | 11 | supported | Subaru Natsuki is suddenly transported across the southern border from Lugunica into the Holy Volakian Empire, along with Rem, who has lost… | The system answer is faithful to the provided passages, but it misses one of the key points required by the question/re… |
| oos-01 | refused | – |  | Not found in the provided passages. |  |
| oos-02 | refused | – |  | Not found in the provided passages. |  |
| oos-03 | refused | – |  | Not found in the provided passages. |  |
| oos-04 | refused | – |  | Not found in the provided passages. |  |
| oos-05 | refused | – |  | Not found in the provided passages. |  |
| oos-06 | refused | – |  | Not found in the provided passages. |  |
| oos-07 | corrected_premise | – |  | The premise of the question is false: Emilia did not become an Archbishop of the Witch Cult. Instead, she was targeted by the Archbishop of… | The system answer explicitly points out that the premise of the question is false because Emilia never became an Archbi… |
| oos-08 | refused | – |  | Not found in the provided passages. |  |
| oos-09 | refused | – |  | Not found in the provided passages. |  |
| oos-10 | refused | – |  | Not found in the provided passages. |  |
| oos-11 | refused | – |  | Not found in the provided passages. |  |
| oos-12 | refused | – |  | Not found in the provided passages. |  |
| oos-13 | refused | – |  | Not found in the provided passages. |  |
| oos-14 | refused | – |  | Not found in the provided passages. |  |
| oos-15 | refused | – |  | Not found in the provided passages. |  |
