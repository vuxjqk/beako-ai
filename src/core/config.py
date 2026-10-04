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

# Level of the app's own loggers (beako.*): DEBUG | INFO | WARNING
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Where avatars are stored: local (files under UPLOAD_DIR) | db (in PostgreSQL, for hosts whose
# disk does not survive a restart, such as Render's free plan)
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local").lower()
# Local folder for uploaded files, relative to the working dir (/app in Docker)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
AVATAR_MAX_BYTES = int(os.getenv("AVATAR_MAX_BYTES", str(2 * 1024 * 1024)))

OTP_EXPIRE_MINUTES = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
# Wrong passwords allowed per email (since its last successful login) within LOGIN_LOCK_MINUTES;
# past that the email cannot log in until the oldest failure is LOGIN_LOCK_MINUTES old
LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "10"))
LOGIN_LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "15"))

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
# Load the embedding model at startup (in the background) instead of on the first question
PRELOAD_EMBEDDER = os.getenv("PRELOAD_EMBEDDER", "false").lower() == "true"
# Retrieval for QA (see src/services/retrieval.py; measure changes with python -m src.eval retrieval)
RETRIEVAL_METHOD = os.getenv("RETRIEVAL_METHOD") or "hybrid"  # vector | keyword | hybrid
RETRIEVAL_KEYWORD = os.getenv("RETRIEVAL_KEYWORD", "bm25")  # bm25 | ts
RETRIEVAL_CANDIDATES = int(os.getenv("RETRIEVAL_CANDIDATES", "100"))
RETRIEVAL_RRF_K = int(os.getenv("RETRIEVAL_RRF_K", "60"))
RETRIEVAL_EXACT = os.getenv("RETRIEVAL_EXACT", "false").lower() == "true"
RETRIEVAL_SCOPE = os.getenv("RETRIEVAL_SCOPE") or "boost"  # off | filter | boost
RETRIEVAL_RERANK = os.getenv("RETRIEVAL_RERANK", "")  # cross-encoder model name; empty = off
RETRIEVAL_RERANK_TOP = int(os.getenv("RETRIEVAL_RERANK_TOP", "20"))
# simple (one search + one LLM call) | agent (tool-using loop, 3-6 LLM calls) | auto (route by question)
QA_MODE = os.getenv("QA_MODE") or "agent"
# In auto mode, retry with the agent when the simple path finds nothing
QA_ESCALATE = (os.getenv("QA_ESCALATE") or "false").lower() == "true"
# Agent limits: model calls per question, and prompt size after which it must answer
AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "6"))
AGENT_MAX_CONTEXT_TOKENS = int(os.getenv("AGENT_MAX_CONTEXT_TOKENS", "40000"))

# Guardrails (src/services/guard.py). Per-user limits; admins are exempt from these, not from the budget
QA_USER_PER_MINUTE = int(os.getenv("QA_USER_PER_MINUTE", "5"))
QA_USER_PER_DAY = int(os.getenv("QA_USER_PER_DAY", "100"))
QA_USER_DAILY_TOKENS = int(os.getenv("QA_USER_DAILY_TOKENS", "300000"))
QA_USER_MAX_CONCURRENT = int(os.getenv("QA_USER_MAX_CONCURRENT", "1"))
# System-wide spend per day: past QA_DEGRADE_AT x budget only the cheap simple path runs, past
# the budget questions are refused until the next day. 0 = no cap
QA_DAILY_BUDGET_USD = float(os.getenv("QA_DAILY_BUDGET_USD", "5"))
QA_DEGRADE_AT = float(os.getenv("QA_DEGRADE_AT", "0.8"))
# Days for limits and reports start at midnight in this time zone (a PostgreSQL zone name)
QA_TIMEZONE = os.getenv("QA_TIMEZONE", "UTC")
# Price of LLM_MODEL in USD per million tokens, for cost estimates; check your provider's price page
LLM_PRICE_INPUT_PER_MTOK = float(os.getenv("LLM_PRICE_INPUT_PER_MTOK", "0.5"))
LLM_PRICE_OUTPUT_PER_MTOK = float(os.getenv("LLM_PRICE_OUTPUT_PER_MTOK", "3"))
# Total back-off one question may spend waiting on provider retries, across all its LLM calls
LLM_MAX_TOTAL_RETRY_SECONDS = float(os.getenv("LLM_MAX_TOTAL_RETRY_SECONDS", "45"))
