# Báo cáo kiểm tra dữ liệu văn bản Re:ZERO

Tạo lúc 2026-10-03 11:50 UTC. Nguồn: `/data/epub` (32 file epub). Kết quả: **ĐẠT** (30/30 kiểm tra đạt).

## Kiểm tra

| | Kiểm tra | Ghi chú |
|---|---|---|
| ✅ | Thư mục có đúng 32 file epub | 32 file |
| ✅ | volumes.csv khớp thư mục (tên file + sha256) |  |
| ✅ | 28 tập chính đánh số 1–28, 4 Short Story Collection đánh số 1–4 | main=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28] ssc=[1, 2, 3, 4] |
| ✅ | DB có đúng 32 volume, khớp volumes.csv (sha256) | 32 volume trong DB |
| ✅ | Số từ cốt truyện mỗi file (main) nằm trong 0.5×–2× trung vị (70,772) |  |
| ✅ | Số từ cốt truyện mỗi file (short_story_collection) nằm trong 0.5×–2× trung vị (56,823) |  |
| ✅ | Mỗi file có ít nhất 1 phần cốt truyện |  |
| ✅ | Mỗi file có đúng 1 lời bạt (afterword) được gắn nhãn |  |
| ✅ | Không có phần (part) rỗng |  |
| ✅ | Không có đoạn văn rỗng |  |
| ✅ | Không có section chỉ toàn dấu ngắt cảnh / không có chữ | [] |
| ✅ | Không còn rác: HTML tag |  |
| ✅ | Không còn rác: HTML entity |  |
| ✅ | Không còn rác: replacement char |  |
| ✅ | Không còn rác: control char |  |
| ✅ | Không còn rác: mojibake |  |
| ✅ | Không còn rác: lost dash image (“”) |  |
| ✅ | Không còn rác: double space |  |
| ✅ | Không còn rác: edge whitespace |  |
| ✅ | Không còn rác: ASCII ellipsis |  |
| ✅ | Không còn rác: ad text |  |
| ✅ | Không còn rác: URL |  |
| ✅ | Không có ký tự ngoài bảng ký tự cho phép |  |
| ✅ | seq liên tục 1..N trong mỗi file |  |
| ✅ | Thứ tự đoạn trùng thứ tự đọc của epub (spine + vị trí khối) |  |
| ✅ | Số section trong mỗi chương liên tục |  |
| ✅ | Số chương trong mỗi tập liên tục từ 1 |  |
| ✅ | Dấu ngắt cảnh không nằm đầu/cuối section, không lặp đôi |  |
| ✅ | Đối chiếu độc lập: mọi đoạn văn (110,893) có trong epub, đúng thứ tự |  |
| ✅ | Độ phủ: mỗi file nội dung truyện ≥ 97% chữ của epub có trong DB |  |

## Chạy lại không đổi dữ liệu (idempotency)

Dấu vân tay của các bảng (số dòng, md5 nội dung, `max(xmin)` — xmin đổi khi có dòng bị ghi lại):

| Bảng | Số dòng | md5 nội dung | max(xmin) |
|---|---:|---|---:|
| volumes | 32 | `9fa569a72aec5b14085058dadeeb627b` | 1509 |
| book_parts | 408 | `32a524d757078bb9c913590128a576d0` | 1642 |
| book_sections | 1,454 | `dfeac8527b368a50bf174fa02bb2f115` | 1509 |
| book_paragraphs | 111,916 | `8af8d2a5637d8c3edaa1990a3d6ca095` | 1619 |

So với lần verify trước: **không thay đổi**.

## Số liệu từng file

| File | Loại | Phần truyện | Phần khác | Section | Đoạn (tổng) | Ngắt cảnh | Từ (truyện) | Có số trang |
|---|---|---:|---:|---:|---:|---:|---:|---|
| ln01 | chính | 7 | 5 | 38 | 2,806 | 6 | 73,549 | có |
| ln02 | chính | 6 | 5 | 48 | 3,756 | 15 | 68,408 | — |
| ln03 | chính | 8 | 4 | 43 | 3,464 | 15 | 68,812 | có |
| ln04 | chính | 7 | 4 | 39 | 3,245 | 9 | 69,283 | có |
| ln05 | chính | 6 | 5 | 35 | 3,039 | 12 | 66,584 | — |
| ln06 | chính | 6 | 5 | 36 | 3,138 | 67 | 66,334 | — |
| ln07 | chính | 6 | 5 | 31 | 3,114 | 53 | 65,647 | — |
| ln08 | chính | 5 | 8 | 31 | 3,166 | 42 | 68,263 | — |
| ln09 | chính | 10 | 7 | 42 | 3,647 | 78 | 76,866 | — |
| ln10 | chính | 6 | 8 | 37 | 3,733 | 26 | 80,036 | — |
| ln11 | chính | 6 | 8 | 38 | 3,980 | 27 | 78,343 | — |
| ln12 | chính | 6 | 8 | 52 | 3,860 | 39 | 81,218 | — |
| ln13 | chính | 8 | 8 | 42 | 3,972 | 32 | 77,915 | có |
| ln14 | chính | 7 | 7 | 43 | 3,817 | 21 | 79,692 | có |
| ln15 | chính | 11 | 7 | 53 | 3,971 | 58 | 80,805 | — |
| ln16 | chính | 5 | 7 | 31 | 3,702 | 11 | 81,995 | — |
| ln17 | chính | 5 | 7 | 26 | 3,766 | 22 | 82,336 | có |
| ln18 | chính | 6 | 7 | 30 | 3,118 | 28 | 77,581 | — |
| ln19 | chính | 7 | 7 | 33 | 3,570 | 30 | 77,298 | — |
| ln20 | chính | 8 | 7 | 42 | 3,879 | 72 | 69,897 | có |
| ln21 | chính | 7 | 7 | 42 | 4,027 | 27 | 71,646 | có |
| ln22 | chính | 8 | 7 | 34 | 3,739 | 37 | 67,498 | có |
| ln23 | chính | 7 | 7 | 39 | 3,912 | 41 | 65,158 | có |
| ln24 | chính | 6 | 5 | 33 | 3,618 | 37 | 61,907 | có |
| ln25 | chính | 10 | 5 | 76 | 4,913 | 60 | 83,439 | có |
| ln26 | chính | 6 | 5 | 36 | 3,807 | 18 | 66,260 | có |
| ln27 | chính | 7 | 5 | 36 | 3,647 | 15 | 59,586 | có |
| ln28 | chính | 6 | 5 | 34 | 3,507 | 20 | 67,270 | có |
| ssc01 | SSC | 4 | 6 | 38 | 2,180 | 14 | 56,235 | có |
| ssc02 | SSC | 6 | 5 | 37 | 2,385 | 17 | 54,577 | có |
| ssc03 | SSC | 5 | 5 | 41 | 2,677 | 29 | 57,411 | có |
| ssc04 | SSC | 4 | 5 | 42 | 2,761 | 19 | 63,388 | có |
| **Tổng** | | 212 | 196 | 1258 | 111,916 | 997 | 2,265,237 | |

Nhãn phần (`book_parts.kind`): `story` 212, `toc` 46, `afterword` 32, `newsletter` 32, `copyright` 32, `preview` 30, `ad` 22, `front_matter` 2.

## Độ dài bất thường (để xem xét, không phải lỗi)

Trung vị độ dài section truyện: 8,842 ký tự.

Section truyện ngắn hơn 200 ký tự (11):
- ReZero Starting Life in Another World - LN 12.epub — Chapter 5, section 10: 33 ký tự — ““—Behold the unknowable present.””
- ReZero Starting Life in Another World - LN 12.epub — Chapter 5, section 12: 33 ký tự — ““—Behold the unknowable present.””
- ReZero Starting Life in Another World - LN 12.epub — Chapter 5, section 13: 33 ký tự — ““—Behold the unknowable present.””
- ReZero Starting Life in Another World - LN 12.epub — Chapter 5, section 14: 33 ký tự — ““—Behold the unknowable present.””
- ReZero Starting Life in Another World - LN 12.epub — Chapter 5, section 15: 33 ký tự — ““—Behold the unknowable present.””
- ReZero Starting Life in Another World - LN 12.epub — Chapter 5, section 16: 33 ký tự — ““—Behold the unknowable present.””
- ReZero Starting Life in Another World - LN 12.epub — Chapter 5, section 17: 33 ký tự — ““—Behold the unknowable present.””
- ReZero Starting Life in Another World - LN 12.epub — Chapter 5, section 18: 33 ký tự — ““—Behold the unknowable present.””
- ReZero Starting Life in Another World - LN 12.epub — Chapter 5, section 19: 33 ký tự — ““—Behold the unknowable present.””
- ReZero Starting Life in Another World - LN 20.epub — Chapter 5, section 1: 110 ký tự — “How surprised would you be if I told you that I fell for you from the moment we first laid eyes on each other?”
- ReZero Starting Life in Another World - LN 25.epub — Chapter 2, section 10: 168 ký tự — ““Fine, huh?” / “That’s right. It’ll be fine.” / “Because I know you’re really something.” / “…True, yeah. There is one t”

Section dài hơn 8× trung vị (0):

Đoạn văn dài hơn 2,500 ký tự (2):
- ReZero Starting Life in Another World - LN 12.epub seq 3679 (story): 8,273 ký tự — ““The Return by Death that you possess is an incredible Authority. You do not comprehend how it is tr…”
- ReZero Starting Life in Another World - LN 19.epub seq 3091 (story): 7,009 ký tự — “Impossible, impossible, impossible. What’s happening. It doesn’t make any sense. Why am I being pers…”

## Đọc thử ngẫu nhiên

12 đoạn chọn ngẫu nhiên (seed 2026), mỗi đoạn kèm đoạn trước và sau để kiểm tra thứ tự. Vị trí để mở sách đối chiếu: file, chương, section, số trang in (nếu epub có), file XHTML và chỉ số khối trong file.

### ReZero Starting Life in Another World - LN 05.epub · Chapter 1 “A Decaying Mind” · section 5 · không có số trang · `chapter001d.xhtml` khối 58 · seq 610

> &nbsp;&nbsp; “…Miss Crusch?”
>
> **→** “It is. Is there something odd about…? Ah, I see, this is the first time you have seen me in an outfit unrelated to my duties. I imagine it has startled you.”
>
> &nbsp;&nbsp; Crusch seemed to realize what had unsettled him. The outfit she normally wore that resembled an army uniform was gone; in its place, she wore a nightgown with thin, dark fabric and a cape over the shoulders. Unlike the scrupulously buttoned-up military uniform, the nightgown showed off her very feminine physique with every step, greatly altering the aura she projected.
>

### ReZero Starting Life in Another World - LN 05.epub · Chapter 5 “Acedia” · section 7 · không có số trang · `chapter005d.xhtml` khối 8 · seq 2779

> &nbsp;&nbsp; Subaru rotated his scraped ankles. Each step sent pain running through him fierce enough to make his mind go blank. If he ignored that, not a problem. His legs were more than enough to support him while he carried Rem’s remains.
>
> **→** He tossed the broken crucifix sword against a wall. The impact made the lagmite ore in the wall glow, bathing the cavern in pale light. Subaru felt like his eyes were burning. With Rem in his arms, he gazed at her face, not having seen it in the light for over a day.
>
> &nbsp;&nbsp; Tears gently fell from his eyes.
>

### ReZero Starting Life in Another World - LN 10.epub · Chapter 2 “The Road to the Sanctuary” · section 3 · không có số trang · `Text/chapter002_b.xhtml` khối 208 · seq 1080

> &nbsp;&nbsp; “—Ah? Hey?!”
>
> **→** The instant he stepped forward, the blue, shining crystal emitted an even stronger light that enveloped Subaru’s entire body.
>
> &nbsp;&nbsp; He had no time to regret his choice of priorities. The next instant, the world vanished.
>

### ReZero Starting Life in Another World - LN 13.epub · Chapter 5 “Otto Suwen” · section 3 · trang 174 · `Text/chapter016.xhtml` khối 132 · seq 2560

> &nbsp;&nbsp; The quantity of voices Otto’s eardrums picked up from within the forest’s expanses was…vast.
>
> **→** Countless living creatures existed in the sky, in the trees, in the soil, in the rocks. He heard all their voices.
>
> &nbsp;&nbsp; The problem was that he could not simply listen to the great throng of voices and nothing more. The blessing of language compelled Otto to understand them. In other words, Otto’s brain was working to process and interpret all the voices of living creatures coursing through it. This, too, was beyond its limit—
>

### ReZero Starting Life in Another World - LN 17.epub · Chapter 2 “A Showdown of Fire and Ice” · section 2 · trang 65 · `Text/chapter008.xhtml` khối 44 · seq 901

> &nbsp;&nbsp; When Lachins eventually pushed them back, his fellows immediately tripped over their own legs, causing them to tumble downward. Caring nothing for them, the rest of the crowd walked right over the two fallen while moving inexorably forward. It was a frightening sight.
>
> **→** “I don’t think they’re feeling pain from all that adrenaline, but it’d be pretty dangerous without that, right?”
>
> &nbsp;&nbsp; “Given the way they are, it doesn’t seem strange for them to trample one another to death.”
>

### ReZero Starting Life in Another World - LN 20.epub · Chapter 3 “A Warrior’s Acclaim” · section 2 · trang 107 · `Text/chapter009.xhtml` khối 8 · seq 1609

> &nbsp;&nbsp; Hearing Garfiel’s wheezing words, his sister took the mirror from their little brother’s hand and activated it. There was a faint light in the mirror as it connected to another mirror.
>
> **→** “Wh-what should I say?”
>
> &nbsp;&nbsp; “Hold it…here… I’ll…”
>

### ReZero Starting Life in Another World - LN 20.epub · Chapter 6 “The Results of the Battle for Pristella” · section 4 · trang 184 · `Text/chapter019.xhtml` khối 31 · seq 2871

> &nbsp;&nbsp; There was a genuine and attentive affection for Subaru in her words.
>
> **→** Sirius understood that he and Petelgeuse were different. But even understanding that, she was overwriting reality with a convenient delusion.
>
> &nbsp;&nbsp; Swearing to be there to greet Petelgeuse, who was sleeping inside Subaru.
>

### ReZero Starting Life in Another World - LN 22.epub · Chapter 2 “A White Sky Asterism” · section 4 · trang 69 · `Text/chapter006.xhtml` khối 148 · seq 1110

> &nbsp;&nbsp; —The measure of wrongdoing lay in none other than the heart of the criminal themselves.
>
> **→** Even if no one witnessed it, a criminal’s heart still knew their sin.
>
> &nbsp;&nbsp; For good, she still did not know. Good was more difficult. There was no compass for good. She could not find a sure guide.
>

### ReZero Starting Life in Another World - LN 23.epub · Chapter 6 “Re:ZERO -Life Starts in Another World-” · section 4 · trang 208 · `Text/chapter024.xhtml` khối 147 · seq 3383

> &nbsp;&nbsp; One hand holding Subaru’s, she held the other out in front of her.
>
> **→** The next instant, he felt something invisible flowing out of his body and into Beatrice. His head clouded from the loss of that massive amount of something. In exchange, Beatrice’s palm exerted a tremendous force against the streak of white closing in on them.
>
> &nbsp;&nbsp; “——”
>

### ReZero Starting Life in Another World - LN 24.epub · Chapter 4 “Five Obstacles” · section 4 · trang 140 · `Text/chapter017.xhtml` khối 322 · seq 2295

> &nbsp;&nbsp; “—Thanks for the meal!”
>
> **→** “If a hot babe was sayin’ it, that’d be one thing, but no one wants to hear that comin’ outta you.”
>
> &nbsp;&nbsp; In an instant, Batenkaitos, who approached with his mouth wide open, violently shifted to the side.
>

### ReZero Starting Life in Another World - LN 25.epub · Chapter 5 “Mental Death” · section 1 · trang 129 · `Text/chapter011.xhtml` khối 31 · seq 2194

> &nbsp;&nbsp; “It would be really bad if we get too far away from the tower and the authority cuts out! Sorry for adding so many limitations, but please work with me!”
>
> **→** “—! When this is over, I swear I’m gonna… Argh!”
>
> &nbsp;&nbsp; Meili pursed her lips pursed as her face reddened.
>

### ReZero Starting Life in Another World Short Story Collection, Vol. 3.epub ·  “My Fair Bad Lady” · section 8 · trang 21 · `Text/chapter003.xhtml` khối 229 · seq 272

> &nbsp;&nbsp; Naturally, Ram conveniently didn’t mention whether those would be tears of joy or bitterness.
>
> **→** Just as their conversation was winding down, the double doors to the dining hall flew open. It was time for the grand entrance of the star of the night—the chef supreme.
>
> &nbsp;&nbsp; “So sorry to keep you in anticipation. Is everyone here?”
>

## Ghi chú về nguồn

- Các trang chỉ có ảnh (bìa, tranh minh họa, trang tiêu đề) không có chữ nên không có dòng nào trong DB.
- Dấu gạch dài “——” trong nhiều tập là ảnh nội dòng; độ dài được khôi phục theo bề rộng ảnh (ảnh phổ biến nhất của mỗi tập = “——”). Hai ảnh chữ đặc biệt được chép tay: LN25 `chi.jpg` = “菜月・昴”, LN13 `Art_1.jpg` = “●・●・●・●”.
- Chỉ những tập có mốc trang dày đặc trong epub mới có `page`; các tập khác để trống.
- LN22: phần preview mở đầu giữa câu vì câu đầu nằm trong ảnh minh họa của sách.
- Phần không phải cốt truyện được gắn nhãn qua `book_parts.kind` (afterword, preview, copyright, toc, newsletter, ad, front_matter); lọc truyện bằng `kind = 'story'`.
