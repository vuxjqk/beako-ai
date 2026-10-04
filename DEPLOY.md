# Triển khai Beako AI (miễn phí)

| Phần | Dịch vụ | Ghi chú |
|---|---|---|
| Database | **Neon** (Postgres 18 + pgvector) | Gói Free 1 GB; dữ liệu sách ~135 MB |
| Backend (FastAPI) | **Render**, `render.yaml` | Gói Free 512 MB; ngủ sau 15 phút không có request, lần đầu vào lại mất ~1 phút |
| Frontend (Next.js) | **Vercel** | Gói Hobby; gọi backend qua `/api` (rewrite) nên cookie đăng nhập là first-party |

Cập nhật về sau: sửa code ở máy → push lên `main` → GitHub Actions chạy test → Render và Vercel tự deploy.
Không sửa code trực tiếp trên server.

Chạy ở máy vẫn như cũ (`docker compose up`): compose chạy `--reload`, lưu avatar ra đĩa và dùng
`data/models`. Các thiết lập dành cho host chỉ bật qua biến môi trường trong `render.yaml`.

## 1. Neon (database)

1. Tạo project ở <https://console.neon.tech>: Postgres 17 trở lên, region **AWS Asia Pacific (Singapore)** (cùng vùng với Render).
2. Lấy connection string **không có `-pooler`** (tắt "Connection pooling" khi copy), dạng
   `postgresql://USER:PASSWORD@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`.
3. Tạo schema và chép dữ liệu sách từ máy (stack local phải đang chạy):

   ```sh
   # schema (cũng tự chạy mỗi lần backend trên Render khởi động)
   docker compose exec -e DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST/neondb?sslmode=require' backend alembic upgrade head
   # sách: volumes, parts, sections, paragraphs, chunks (không chép tài khoản/hội thoại ở máy)
   TARGET_URL='postgresql://USER:PASSWORD@HOST/neondb?sslmode=require' sh scripts/publish_book_data.sh
   # tài khoản admin, mật khẩu ngẫu nhiên in ra một lần
   docker compose exec -e DATABASE_URL='postgresql+psycopg://...' backend python -m src.seed admin you@example.com "Tên bạn"
   ```

   Lưu ý: SQLAlchemy cần tiền tố `postgresql+psycopg://`; `psql`/script chép dữ liệu dùng `postgresql://`.

   Nếu dùng Neon CLI (`neon link`): nó ghi `DATABASE_URL` của Neon **đè lên `.env`**, làm bản chạy ở máy
   chuyển sang Neon. Chuyển các dòng đó sang `.env.neon` (không commit) và trả `DATABASE_URL` của
   `.env` về `postgresql+psycopg://<user>:<password>@db:5432/<db>`; với `neon deploy` dùng `--no-env-pull`.
   Trong `.env.neon`, `DATABASE_URL_UNPOOLED` là kết nối trực tiếp cần dùng.

## 2. Email (mã OTP đăng ký, quên mật khẩu)

Mailpit chỉ dùng ở máy. Cần một SMTP thật, ví dụ Gmail với App Password
(<https://myaccount.google.com/apppasswords>, cần bật xác minh 2 bước):
`SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_SECURITY=starttls`, `SMTP_USERNAME=<gmail>`,
`SMTP_PASSWORD=<app password>`, `SMTP_FROM=Beako <gmail của bạn>`.

## 3. Render (backend)

1. <https://dashboard.render.com> → **New → Blueprint** → chọn repo `beako-ai` (nhánh `main`).
2. Render đọc `render.yaml` và hỏi các giá trị bí mật:
   - `DATABASE_URL`: chuỗi Neon ở bước 1 **với tiền tố `postgresql+psycopg://`**
   - `LLM_API_KEY`: khóa Gemini
   - `GOOGLE_CLIENT_ID`: như trong `.env` ở máy (để trống nếu không dùng đăng nhập Google)
   - `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`: bước 2
3. Đợi deploy xong, mở `https://<tên-service>.onrender.com/health` → `{"status":"ok","database":"ok"}`.

Các thiết lập đã có sẵn trong `render.yaml`: lưu avatar trong database (Render Free không có ổ đĩa
lâu dài), model embedding nằm sẵn trong image (không tải lại mỗi lần khởi động), `COOKIE_SECURE=true`,
ngân sách $5/ngày, ngày tính theo giờ Việt Nam. Chỉnh giá `LLM_PRICE_*` theo bảng giá model.
Render chỉ deploy khi GitHub Actions của commit đã xanh (`autoDeployTrigger: checksPass`).

## 4. Vercel (frontend)

1. <https://vercel.com/new> → import repo `beako-ai`.
2. **Root Directory**: `frontend` (Framework: Next.js, tự nhận).
3. Environment Variables (cho cả Production và Preview):
   - `BACKEND_URL` = `https://<tên-service>.onrender.com` (không có `/` cuối) — được đọc **lúc build**,
     đổi giá trị thì phải Redeploy
   - `NEXT_PUBLIC_GOOGLE_CLIENT_ID` = như `GOOGLE_CLIENT_ID` (hoặc bỏ trống)
4. Deploy, mở `https://<project>.vercel.app`.

## 5. Google Sign-In (nếu dùng)

Google Cloud Console → Credentials → OAuth Client → **Authorized JavaScript origins**: thêm
`https://<project>.vercel.app`.

## Kiểm tra sau khi deploy

- Đăng nhập bằng admin, đổi mật khẩu trong Cài đặt.
- Hỏi một câu và xem các bước "Đang tìm…" hiện dần (streaming qua Vercel → Render).
- Đăng ký tài khoản mới để thử email OTP.
- Trang Quản trị → Chi phí & chất lượng.
