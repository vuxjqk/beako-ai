import os

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
# Must be true in production (HTTPS); false lets cookies work on http://localhost
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
# Path the browser sends the refresh-token cookie to: "/auth" when the API is called
# directly, "/api/auth" when the frontend proxies it under /api
REFRESH_COOKIE_PATH = os.getenv("REFRESH_COOKIE_PATH", "/auth")

# OAuth client ID(s) the frontend uses for Google Sign-In; comma-separated if several
GOOGLE_CLIENT_IDS = [c.strip() for c in os.getenv("GOOGLE_CLIENT_ID", "").split(",") if c.strip()]

# Local folder for uploaded files, relative to the working dir (/app in Docker)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
AVATAR_MAX_BYTES = int(os.getenv("AVATAR_MAX_BYTES", str(2 * 1024 * 1024)))

OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))

SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.environ["SMTP_FROM"]
# "starttls" (port 587), "ssl" (port 465) or "none" (local dev server)
SMTP_SECURITY = os.getenv("SMTP_SECURITY", "starttls").lower()

# Question answering. Any OpenAI-compatible Chat Completions API works: LLM_PROVIDER picks
# the default endpoint (gemini | openai), LLM_BASE_URL overrides it
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.8-flash")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "700"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
# Empty = don't send; "none"/"low" keeps thinking models from eating the output budget
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
# Longest provider-requested back-off (429/503) a request will sit through before failing
LLM_MAX_RETRY_WAIT_SECONDS = float(os.getenv("LLM_MAX_RETRY_WAIT_SECONDS", "20"))
QA_TOP_K = int(os.getenv("QA_TOP_K", "6"))
