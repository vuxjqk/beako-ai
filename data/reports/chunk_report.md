# Báo cáo kiểm tra chunk và embedding

Tạo lúc 2026-10-03 14:19 UTC. Kết quả: **ĐẠT** (13/13 kiểm tra đạt).

- Mô hình embedding: `BAAI/bge-small-en-v1.5` (384 chiều), phiên bản `fastembed==0.8.1; snapshot=aa8f8b060edb00e03bfdd08813a2949946c8ba55`
- Bộ cắt: `v1 target=350 max=450 min=120 scene=175 overlap=80` (đếm token bằng tokenizer của chính mô hình)
- Chỉ mục: HNSW `vector_cosine_ops` trên `embedding`; GIN trên `tsv` (`to_tsvector('simple', heading || text)`, không stemming để khớp đúng tên riêng)

## Kiểm tra

| | Kiểm tra | Ghi chú |
|---|---|---|
| ✅ | Độ phủ: mọi đoạn story (107,628) nằm trong ít nhất một chunk |  |
| ✅ | Đoạn quá dài bị cắt: mọi ký tự đều nằm trong một chunk |  |
| ✅ | Văn bản chunk khớp nguyên văn đoạn nguồn theo vị trí ghi lại |  |
| ✅ | Chunk không vượt ranh giới phần (chương/truyện) |  |
| ✅ | Chỉ có phần kind = 'story' được chunk |  |
| ✅ | Chunk liên tục, đúng thứ tự đọc trong mỗi tập |  |
| ✅ | Không có chunk rỗng |  |
| ✅ | Mọi chunk ≤ 450 token (vừa giới hạn 512 của mô hình) |  |
| ✅ | Chunk < 120 token chỉ khi cả phần ngắn như vậy |  |
| ✅ | Mọi chunk có vector 384 chiều (chuẩn hóa) của BAAI/bge-small-en-v1.5 |  |
| ✅ | Một phiên bản mô hình duy nhất |  |
| ✅ | Truy vấn thử tiếng Anh: đúng chỗ trong top 5 (9/10, cần ≥ 80%) |  |
| ✅ | Truy vấn thử tiếng Việt (chỉ để tham khảo, mô hình tiếng Anh): 1/3 |  |

## Chạy lại không đổi dữ liệu

`book_chunks`: 10,457 dòng, md5 `75ee66b0aad27a0861fbef73c0d82910`, max(xmin) 1735. So với lần kiểm tra trước: **không thay đổi**.

## Số chunk và phân bố độ dài

10,457 chunk, 3,712,511 token (gồm phần chồng lấn). Đích 350, trần 450, sàn cắt 120.

Token mỗi chunk: min 120, p5 223, p25 354, trung vị 363, p75 377, p95 401, max 450; trung bình 355.

| Token | Số chunk | |
|---|---:|---|
| 100–149 | 118 | █ |
| 150–199 | 247 | █ |
| 200–249 | 315 | █ |
| 250–299 | 242 | █ |
| 300–349 | 251 | █ |
| 350–399 | 8,694 | ██████████████████████████████ |
| 400–449 | 589 | ██ |
| 450 | 1 | █ |

Chunk dưới 120 token: không có (section ngắn đã được gộp).

| Tập | Chunk | Token |
|---|---:|---:|
| ln01 | 317 | 114,967 |
| ln02 | 326 | 114,335 |
| ln03 | 312 | 110,856 |
| ln04 | 318 | 113,645 |
| ln05 | 298 | 106,890 |
| ln06 | 306 | 107,795 |
| ln07 | 298 | 105,891 |
| ln08 | 310 | 111,329 |
| ln09 | 354 | 125,505 |
| ln10 | 372 | 133,743 |
| ln11 | 370 | 131,934 |
| ln12 | 376 | 133,019 |
| ln13 | 368 | 129,846 |
| ln14 | 368 | 130,796 |
| ln15 | 375 | 131,366 |
| ln16 | 375 | 134,733 |
| ln17 | 371 | 133,989 |
| ln18 | 331 | 119,451 |
| ln19 | 341 | 122,229 |
| ln20 | 330 | 114,862 |
| ln21 | 338 | 118,128 |
| ln22 | 311 | 110,536 |
| ln23 | 306 | 107,604 |
| ln24 | 295 | 104,862 |
| ln25 | 402 | 138,139 |
| ln26 | 308 | 108,886 |
| ln27 | 289 | 102,584 |
| ln28 | 309 | 110,009 |
| ssc01 | 256 | 91,471 |
| ssc02 | 259 | 93,089 |
| ssc03 | 274 | 96,069 |
| ssc04 | 294 | 103,953 |

## Chọn mô hình embedding

Thử trước khi chạy toàn bộ (2026-10-03): 1.383 chunk của LN7, 12, 13, 19 và 12 truy vấn có đáp án biết trước (9 tiếng Anh, 3 tiếng Việt), CPU 8 nhân trong Docker, không GPU, không API key — nên chỉ xét mô hình chạy cục bộ miễn phí qua fastembed (ONNX).

| Mô hình | Chiều | Tốc độ | Ước tính toàn bộ | hit@1 | hit@5 |
|---|---:|---:|---:|---:|---:|
| **BAAI/bge-small-en-v1.5** (chọn) | 384 | 4,2 chunk/s | ~44 phút | 10/12 | 10/12 |
| BAAI/bge-base-en-v1.5 | 768 | 1,4 chunk/s | ~2 giờ 10 | 10/12 | 11/12 |
| snowflake/snowflake-arctic-embed-m | 768 | 1,4 chunk/s | ~2 giờ 10 | — | — |
| google/embeddinggemma-300m, intfloat/multilingual-e5-large | — | — | — | không nạp được (lỗi ONNX external data) | |

bge-base chỉ hơn 1 truy vấn ở top 5 nhưng chậm gấp 3 lần cho mỗi lần tạo lại; bge-small đủ tốt cho giai đoạn này. Truy vấn tiếng Việt vẫn khớp nhờ tên riêng; giai đoạn sau nên dịch/viết lại câu hỏi sang tiếng Anh trước khi tìm.

## Truy vấn thử (tìm vector, top 3)

Kiểm tra sơ bộ, chưa phải đánh giá chính thức. Truy vấn tiếng Việt chạy trên mô hình tiếng Anh: khớp chủ yếu nhờ tên riêng.

### ✅ “Elsa cuts open Subaru's stomach in the loot house”

Kỳ vọng: main 1 — khớp ở hạng 2

1. `0.745` **LN11 · Chapter 1: Maid, Maid, Maid · §4 · ¶316–325** — “Who would’ve ever thought it’d be Elsa’s blade greeting me. Thanks to that…well, crap, thanks to that I got a Return by Death without learning a damn thing.” Subaru wouldn’t say he had truly come away with absolutely no…
2. `0.743` **LN01 · Chapter 2: A Struggle Too Late · §6 · p.113 · ¶1312–1321** — Subaru began to panic, looking this way and that, listening as hard as he could for any sound. He looked like the prey of a ferocious predator just waiting to be devoured. From Elsa’s perspective, nothing could make her …
3. `0.728` **LN12 · Chapter 3: A Four-Hundred-Year-Old Cry · §6 · ¶1954–1965** — Elsa intercepted the countless arrows bearing down upon her with swings of her black blade, filling the air with wildly dancing sounds of crystals shattering. The fragile arrows fleetingly shimmered as they scattered apa…

### ✅ “Rem confesses her love and Subaru decides to start over from zero”

Kỳ vọng: main 6 / Chapter 5 — khớp ở hạng 1

1. `0.799` **LN06 · Chapter 5: From Zero · §3 · ¶2521–2530** — Subaru could tell that a vortex of uncertainty, bewilderment, and hesitation swirled within her. The various things Subaru had just said were greatly, powerfully, fiercely shaking her heart. The long battle felt like an …
2. `0.794` **LN06 · Chapter 5: From Zero · §1 · ¶2352–2359** — “Tired. Yeah, that’s right… I am.” As Rem’s hand rested on his cheek, he slowly lifted up his hand, pressing it down upon hers. The touch between them made Rem raise her eyebrows in surprise, but Subaru’s haggard voice a…
3. `0.785` **LN06 · Chapter 5: From Zero · §5 · ¶2859–2878** — Rem took the hand Subaru had offered as they exchanged their vows. She let out a small “Ah” as Subaru drew her close, burying her petite body in his chest. He was grateful that there existed a girl so soft, so warm, and …

### ✅ “Wilhelm kills the White Whale and speaks to Theresia”

Kỳ vọng: main 7 / Chapter 5 — khớp ở hạng 1

1. `0.781` **LN07 · Chapter 5: Wilhelm Van Astrea · §7 · ¶2440–2449** — “It’s over, Theresia. It’s finally…” Atop the head of the immobile White Whale, Wilhelm turned his face skyward. When the treasured sword fell from his hand, he brought that hand up to cover his face, and with a quiverin…
2. `0.746` **LN07 · Chapter 5: Wilhelm Van Astrea · §7–8 · ¶2448–2467** — Finally, after the passage of decades, Wilhelm had voiced the words with which he should have answered her question so long ago. Atop the corpse of the White Whale, his sword fallen from his grasp, the Sword Devil cried …
3. `0.733` **LN07 · Chapter 3: The Battle of the White Whale · §5 · ¶1556–1568** — “Ryaaaaa—!” …Wilhelm intervened, flying in with a vertical slash. Driving his blade in, Wilhelm ran up the White Whale’s flank. As Wilhelm cut through the bloody mist, the kitten siblings appeared alongside, straddling t…

### ✅ “Petelgeuse Romanée-Conti says his brain trembles”

Kỳ vọng: main 5, main 6, main 7, main 8 — khớp ở hạng 1

1. `0.623` **LN08 · Chapter 1: A Beeline Toward Sloth · §4–5 · ¶375–383** — “I am Petelgeuse Romanée-Conti—Archbishop of the Seven Deadly Sins of the Witch Cult, entruuuusted with Sloth!” With spittle on the tip of his outstretched tongue, the madman—Petelgeuse—laughed, proudly invoking his name…
2. `0.617` **LN05 · Chapter 5: Acedia · §2 · ¶2343–2352** — “Hmm… That doesn’t seem to be a reply.” The man roused his own body, their rivalry disintegrating with a whimper. The man pulled his thumb out of his lips as he seemed to remember something, with no sign of a dampening m…
3. `0.601` **LN05 · Chapter 5: Acedia · §3 · ¶2360–2370** — “—” It was a whisper like the sound of an insect’s wings, reaching only Petelgeuse. Once he listened to it, Petelgeuse’s wild laughter vanished. He set aside all jest and tilted his head to form a right angle. “Iiis that…

### ✅ “Echidna explains why she wants Subaru's Return by Death and offers a contract”

Kỳ vọng: main 12 / Chapter 6 — khớp ở hạng 1

1. `0.756` **LN12 · Chapter 6: The Witches’ Tea Party · §3 · ¶3674–3678** — And faced with that sharp gaze, Echidna let a little sigh trickle out as she said, “To grasp the future you desire, you must accept sacrifices along the way. —You simply lacked the resolve for that, Subaru Natsuki.” “—!!…
2. `0.745` **LN13 · Chapter 1: The Sounds That Make You Want to Cry · §4 · p.32 · ¶529–543** — “——” “Since you do not understand what to do, how about letting me lead you by the hand? I promise, I will bring you to the future you desire without fail.” This spoken, Echidna stretched her hand out to Subaru. If he to…
3. `0.735` **LN13 · Chapter 2: Ignoring the Odds · §4 · p.64 · ¶967–980** — His qualifications had been stripped away. They had been taken back. They had been lost. But that also meant— “If she wishes it, Echidna could reissue your qualifications or anything else. If you have put her in an ill m…

### ✅ “Otto's divine protection lets him hear the voices of animals”

Kỳ vọng: main 13 / Chapter 5 — khớp ở hạng 1

1. `0.750` **LN13 · Chapter 5: Otto Suwen · §3 · p.174 · ¶2561–2568** — The problem was that he could not simply listen to the great throng of voices and nothing more. The blessing of language compelled Otto to understand them. In other words, Otto’s brain was working to process and interpre…
2. `0.736` **LN13 · Chapter 5: Otto Suwen · §2–3 · p.173 · ¶2546–2561** — “—!!!” —In the distance, from the direction of the trap he had left behind, he heard an angry, bestial roar reverberate through the sky. With that as the prompt, Otto continued to run as he unleashed his own blessing—dev…
3. `0.717` **LN13 · Chapter 5: Otto Suwen · §1 · p.165 · ¶2427–2438** — —To the young Otto Suwen, the world was a cradle straight out of hell. * * * “xxxxxxx” “●・●・●・●” “***! ****—!!” Unceasingly, twenty-four hours a day, Otto continued to hear incomprehensible voices. Sometimes, they were w…

### ✅ “Beatrice chooses Subaru and forms a contract with him in the burning mansion”

Kỳ vọng: main 15 / Chapter 7 — khớp ở hạng 1

1. `0.753` **LN15 · Chapter 7: —Pick Me · §5–6 · ¶2440–2452** — She was scared that her feelings, which had been shoved aside by arbitrary logic and unthinkable emotions, might be forced to the surface. No matter how many times you come, I will continue to refuse you. After all, you …
2. `0.746` **LN12 · Chapter 2: I’ve Already Seen Hell · §7 · ¶1197–1207** — That, to Subaru, was hope. Of course, there were many unnatural aspects to Beatrice’s demeanor toward him. But the biggest issue had been held at bay. For the moment, that was enough. “If there’s a way to save Beatrice a…
3. `0.740` **SSC02 · Librarian Beatrice’s Reluctant Promise · §3 · p.105 · ¶1355–1360** — “Mm-hm, she’s all set,” Puck confirmed. “Lia is really excited to play. She’s already running in the mansion.” With a yawn about to escape from his mouth, Puck informed them that everything was good to go. With that, Sub…

### ✅ “Regulus Corneas hides his heart inside his wives with the Lion's Heart”

Kỳ vọng: main 19 — khớp ở hạng 1

1. `0.799` **LN19 · Chapter 6: Regulus Corneas · §2 · ¶3092–3104** — “Ghyaaaaaagh!” Up and up. Cloaked in a terrible, buffeting wind, Regulus’s body ascended into the night sky. He had activated his Lion Heart the moment the attack struck his crotch, stopping time for his body and becomin…
2. `0.792` **LN19 · Chapter 6: Regulus Corneas · §2 · ¶3210–3226** — He could activate Lion Heart as many times as he wanted, but he didn’t have something that would help him keep breathing. And it was necessary to wait a few seconds before activating Lion Heart again. Death was drawing n…
3. `0.786` **LN19 · Chapter 6: Regulus Corneas · §2 · ¶3202–3211** — “Glug.” Of course, Regulus would never know that fact as he drowned. As the water assaulted him, and terrified by the pressure of the liquid flooding his lungs, he desperately tried to escape. But there was no room to fl…

### ❌ “Subaru wakes up in the watchtower with no memories”

Kỳ vọng: main 23 / Chapter 1, Chapter 2 — không có trong top 10

1. `0.776` **LN21 · Chapter 3: The Watchtower Baptism · §1 · p.120 · ¶1856–1865** — As if she had never existed. “Agh…” Without her support, Subaru collapsed to the ground, unable to move. Without a reason to move. Pierced by the unfathomable white streak, Subaru’s insides were completely destroyed. And…
2. `0.775` **LN21 · Chapter 3: The Watchtower Baptism · §3 · p.136 · ¶2120–2127** — Subaru couldn’t finish his question as he felt a floating sensation and his feet left the ground. The world twisted chaotically, fraying and breaking apart like a sheet of paper being torn to pieces. Cracks formed in the…
3. `0.757` **LN21 · Chapter 5: The Watchtower Guardian · §3–4 · p.201 · ¶3205–3221** — At least we can communicate. But just as Subaru thought that, his brain reached its limit. Feeling the cold sand beneath him, Subaru slipped into unconsciousness without saying anything. All he could do was hold the girl…

### ✅ “Subaru has lost all his memories and doesn't recognize Emilia or Beatrice”

Kỳ vọng: main 23 / Chapter 1, Chapter 2 — khớp ở hạng 1

1. `0.744` **LN23 · Chapter 2: Who Are You? · §1–2 · p.49 · ¶796–813** — With that hypothesis of his ability in mind, Subaru looked at both of them. They looked at each other and then nodded. Seeing how serious they looked, Subaru hesitated for just a moment before continuing. “I don’t know i…
2. `0.729` **LN12 · Chapter 3: A Four-Hundred-Year-Old Cry · §2 · ¶1501–1510** — How did he plan to find Beatrice, presumably in the archive of forbidden books even at that very moment, and bring her out with him? “If she really wants to hide, there’s no way I’ll find her no matter what plan I come u…
3. `0.726` **LN02 · Chapter 5: The Morning He Yearned For · §11 · ¶3506–3518** — Like I don’t know anything about them, he would have said, but Subaru’s words died on his tongue. His repeated loops had given him more than two weeks of time with them. Subaru could have responded that he’d forged memor…

### ❌ “Rem tỏ tình với Subaru và cậu quyết định bắt đầu lại từ con số không” (tiếng Việt)

Kỳ vọng: main 6 / Chapter 5 — khớp ở hạng 6

1. `0.680` **LN06 · Chapter 6: The Card That’s Been Dealt · §2 · ¶2985–2991** — “Rem.” Subaru sat up straight and stared at Rem. Then, as Rem, detecting that the atmosphere had changed, lifted her face and looked at him, he said, “Please tell me what Roswaal ordered you to stay in the royal capital …
2. `0.672` **LN26 · Chapter 1: Baptism · §1 · p.20 · ¶333–352** — The boy—Subaru Natsuki—nodded over and over. “Yeah, that’s right, Rem. I’m your hero. I’ll always…” “——” “Rem?” While trying to control the quivering in his own voice, Subaru strained to hear Rem’s. Perhaps because her t…
3. `0.662` **LN20 · Chapter 7: Ripples on the Surface · §6 · p.239 · ¶3726–3734** — “I’m okay, Subaru. I finished saying my farewells to Grandmother— So I am fine.” “I…see… Well, if you say so.” Subaru withdrew his concern. He could not say for sure what Reinhard was feeling, but if he was going to say …

### ❌ “Beatrice ký khế ước với Subaru” (tiếng Việt)

Kỳ vọng: main 15 / Chapter 7 — không có trong top 10

1. `0.710` **LN18 · Chapter 4: The Stars Etched into History · §2 · ¶2083–2090** — “—Sorry to interject yet again, but if I may.” But before Subaru could say anything, Otto raised his hand. Seeing that, Subaru guessed he was thinking of revealing that Beatrice was an artificial spirit. He had been abou…
2. `0.710` **LN12 · Chapter 3: A Four-Hundred-Year-Old Cry · §4 · ¶1739–1755** — Her words became a blade, became fire, became steel, wounding Subaru’s heart one after the next. In various forms, in various meanings, she tormented Subaru with every suffering she had endured. And Beatrice was only sho…
3. `0.709` **LN15 · Chapter 8: Faces Fashioned from Snow · §1 · ¶2941–2951** — Beatrice spoke such endearing words as she strengthened her grip on Subaru’s hand. Squeezing her palm back, Subaru glared at the menace before them, as if to tell Beatrice it was time to let loose. Devouring the fragment…

### ✅ “Otto có thể nghe tiếng nói của động vật” (tiếng Việt)

Kỳ vọng: main 13 / Chapter 5 — khớp ở hạng 3

1. `0.638` **SSC04 · Otto’s Bittersweet Merchant’s Log · §1 · p.179 · ¶2290–2299** — “Rather noisy, isn’t it, Young Master?” The young man on the loading platform tilted his head curiously at the familiar voice. “You think so?” He was slight of frame, with ash-colored hair. Though he had a frail air abou…
2. `0.638` **SSC04 · Otto’s Bittersweet Merchant’s Log · §3 · p.192 · ¶2462–2470** — Otto carried basic medical supplies in the carriage, so he could handle simple first aid. That was what he had meant when he said that. But the next thing he knew— “Gwuh?!” He crouched in the grass, then sensed a presenc…
3. `0.629` **LN13 · Chapter 5: Otto Suwen · §1 · p.172 · ¶2512–2526** — Thanks to that person, Otto was about to say, but when he lifted his face, he realized. The dog-man before his eyes had a look of surprise trained toward Otto. Without Otto understanding what the reaction meant, the dog-…

## Tìm theo từ khóa (tên riêng)

- **Petelgeuse** — 310 chunk chứa từ khóa; top 3: LN09 · Chapter 4: The End of Sloth · §3 · ¶1980–1995; LN09 · Chapter 5: —A Tale About That, and Nothing More · §5 · ¶2347–2359; LN05 · Chapter 5: Acedia · §3 · ¶2416–2426
- **Ryuzu Meyer** — 42 chunk chứa từ khóa; top 3: LN14 · Chapter 2: The Beginning of the Sanctuary and of Ruin · §1 · p.49 · ¶680–691; LN12 · Chapter 2: I’ve Already Seen Hell · §4 · ¶851–861; LN14 · Chapter 2: The Beginning of the Sanctuary and of Ruin · §9–10 · p.85 · ¶1181–1192
- **Pandora** — 56 chunk chứa từ khóa; top 3: LN14 · Chapter 4: The Eternal Freezing of the Great Elior Forest · §1 · p.152 · ¶2064–2079; LN14 · Chapter 4: The Eternal Freezing of the Great Elior Forest · §1 · p.146 · ¶1965–1980; LN14 · Chapter 4: The Eternal Freezing of the Great Elior Forest · §1 · p.147 · ¶1990–2003
- **Al Aldebaran** — 51 chunk chứa từ khóa; top 3: SSC01 · The Day I Stopped Being the Aldebaran Star · §5 · p.144 · ¶1663–1667; SSC01 · The Day I Stopped Being the Aldebaran Star · §7 · p.155 · ¶1784–1793; SSC01 · The Day I Stopped Being the Aldebaran Star · §7 · p.154 · ¶1773–1785

