"""Minimal chat client for any OpenAI-compatible Chat Completions API.

Gemini and OpenAI both speak this protocol, so switching provider is only a matter of
.env settings (LLM_PROVIDER / LLM_MODEL / LLM_API_KEY, optionally LLM_BASE_URL). The evaluation
judge has its own JUDGE_* settings (see config), so it can sit on another provider.
"""

import json
import re
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from src.core import config

DEFAULT_BASE_URLS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openai": "https://api.openai.com/v1/",
}
RETRIES = 3
RETRY_STATUSES = {429, 500, 502, 503, 504}
# An empty reply (no text, no tool calls) is asked again this many times before giving up
EMPTY_RETRIES = 1
# 429 bodies that mean the account's quota is spent, not a short burst limit: retrying won't help.
# Gemini words both alike ("You exceeded your current quota ... billing"); only the quotaId tells
# a daily quota (GenerateRequestsPerDay...) from the per-minute one (...PerMinute...)
QUOTA_RE = re.compile(r"insufficient_quota|PerDay")


class LLMError(Exception):
    """kind says what went wrong, for the user's message and the request log:
    quota | rate_limited | unavailable | timeout | empty | rejected | not_configured | cancelled | error"""

    def __init__(self, message: str, kind: str = "error"):
        super().__init__(message)
        self.kind = kind


class LLMNotConfigured(LLMError):
    def __init__(self, message: str):
        super().__init__(message, "not_configured")


@dataclass
class Meter:
    """Every LLM call made while it is active (see metered()), including calls of a question
    that failed halfway, so the request log and the budgets see all the spending."""
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    retry_wait_s: float = 0.0
    model: str | None = None
    # Set when nobody is waiting for the answer any more (the client disconnected): the next
    # LLM call, or a retry back-off in progress, raises LLMError(kind="cancelled")
    cancel: threading.Event = field(default_factory=threading.Event)

    def check(self) -> None:
        if self.cancel.is_set():
            raise LLMError("cancelled: the client disconnected", "cancelled")

    def add(self, data: dict, model: str) -> None:
        u = data.get("usage") or {}
        prompt = u.get("prompt_tokens") or 0
        # Thinking models bill reasoning as output; some APIs leave it out of completion_tokens
        output = max(u.get("completion_tokens") or 0, (u.get("total_tokens") or 0) - prompt)
        self.calls += 1
        self.prompt_tokens += prompt
        self.completion_tokens += output
        self.model = data.get("model") or model


_meter: ContextVar[Meter | None] = ContextVar("llm_meter", default=None)


@contextmanager
def metered(cancel: threading.Event | None = None) -> Iterator[Meter]:
    """Count the LLM calls made in this block (in this thread or task); setting `cancel` stops
    the work at its next LLM call."""
    m = Meter(cancel=cancel or threading.Event())
    token = _meter.set(m)
    try:
        yield m
    finally:
        _meter.reset(token)


def _http_error(code: int, body: str) -> LLMError:
    if code == 429:
        kind = "quota" if QUOTA_RE.search(body) else "rate_limited"
    elif code in (500, 502, 503):
        kind = "unavailable"
    elif code == 504:
        kind = "timeout"
    elif code in (401, 403):
        kind = "not_configured"  # bad or revoked key
    else:
        kind = "rejected"
    return LLMError(f"LLM API returned {code}: {body[:500]}", kind)


@dataclass
class Completion:
    text: str
    model: str
    finish_reason: str | None
    usage: dict


@dataclass(frozen=True)
class Endpoint:
    """Where a request goes; prefix names the settings, for error messages."""
    prefix: str
    provider: str
    base_url: str
    api_key: str
    reasoning_effort: str


def _app_endpoint() -> Endpoint:
    return Endpoint("LLM", config.LLM_PROVIDER, config.LLM_BASE_URL, config.LLM_API_KEY, config.LLM_REASONING_EFFORT)


def judge_endpoint() -> Endpoint:
    return Endpoint("JUDGE", config.JUDGE_PROVIDER, config.JUDGE_BASE_URL, config.JUDGE_API_KEY,
                    config.JUDGE_REASONING_EFFORT)


def _base_url(ep: Endpoint) -> str:
    base = ep.base_url or DEFAULT_BASE_URLS.get(ep.provider)
    if not base:
        raise LLMNotConfigured(f"Unknown {ep.prefix}_PROVIDER {ep.provider!r}; set {ep.prefix}_BASE_URL")
    return base.rstrip("/") + "/"


def _retry_after(err: urllib.error.HTTPError, body: str) -> float | None:
    """Seconds the provider asks us to wait: Retry-After header, or Gemini's retryDelay."""
    header = err.headers.get("Retry-After") if err.headers else None
    if header and header.replace(".", "", 1).isdigit():
        return float(header)
    m = re.search(r'"retryDelay":\s*"([\d.]+)s"', body) or re.search(r"retry in ([\d.]+)s", body)
    return float(m.group(1)) + 1 if m else None


@dataclass
class ToolTurn:
    """One assistant turn of a tool-using conversation."""
    message: dict  # the assistant message exactly as returned; send it back unchanged
    tool_calls: list[dict]
    text: str
    model: str
    finish_reason: str | None
    usage: dict


def _post(body: dict, ep: Endpoint | None = None) -> dict:
    ep = ep or _app_endpoint()
    if not ep.api_key:
        raise LLMNotConfigured(f"{ep.prefix}_API_KEY is not set")
    # Thinking models (e.g. Gemini 2.5) otherwise spend the output budget on reasoning
    if ep.reasoning_effort:
        body["reasoning_effort"] = ep.reasoning_effort
    # Newer OpenAI models reject max_tokens; max_completion_tokens is the same limit
    if ep.provider == "openai" and "max_tokens" in body:
        body["max_completion_tokens"] = body.pop("max_tokens")
    req = urllib.request.Request(
        _base_url(ep) + "chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {ep.api_key}"},
        method="POST",
    )
    meter = _meter.get()
    for attempt in range(RETRIES + 1):
        if meter is not None:
            meter.check()
        try:
            with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT_SECONDS) as resp:
                data = json.load(resp)
            if meter is not None:
                meter.add(data, body["model"])
            return data
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            err = _http_error(e.code, raw)
            # Rate limits and "model overloaded" are transient on shared free tiers; wait as
            # long as the provider asks, unless that is longer than a request should hang
            wait = _retry_after(e, raw) or 2 ** attempt * 2
            waited = meter.retry_wait_s if meter is not None else 0.0
            if (e.code in RETRY_STATUSES and err.kind != "quota" and attempt < RETRIES
                    and wait <= config.LLM_MAX_RETRY_WAIT_SECONDS
                    and waited + wait <= config.LLM_MAX_TOTAL_RETRY_SECONDS):
                if meter is not None:
                    meter.retry_wait_s += wait
                    meter.cancel.wait(wait)  # returns early when cancelled; checked at the loop top
                else:
                    time.sleep(wait)
                continue
            raise err from e
        except TimeoutError as e:
            raise LLMError(f"LLM API timed out after {config.LLM_TIMEOUT_SECONDS:g}s", "timeout") from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, TimeoutError):
                raise LLMError(f"LLM API timed out after {config.LLM_TIMEOUT_SECONDS:g}s", "timeout") from e
            raise LLMError(f"LLM API unreachable: {e.reason}", "unavailable") from e
    raise LLMError("LLM API retries exhausted", "unavailable")


def chat(system: str, user: str, *, model: str | None = None, max_tokens: int | None = None,
         temperature: float | None = None, endpoint: Endpoint | None = None) -> Completion:
    """One chat completion; the keyword overrides let the evaluation judge use other settings
    (endpoint=judge_endpoint() sends it to the JUDGE_* provider)."""
    body = {
        "model": model or config.LLM_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_tokens or config.LLM_MAX_OUTPUT_TOKENS,
        "temperature": config.LLM_TEMPERATURE if temperature is None else temperature,
    }
    for attempt in range(EMPTY_RETRIES + 1):
        data = _post(body, endpoint)
        choice = (data.get("choices") or [{}])[0]
        text = ((choice.get("message") or {}).get("content") or "").strip()
        if text:
            return Completion(text, data.get("model", body["model"]), choice.get("finish_reason"),
                              data.get("usage") or {})
    raise LLMError(f"LLM API returned an empty reply (finish_reason={choice.get('finish_reason')})", "empty")


def chat_tools(messages: list[dict], tools: list[dict], *, tool_choice: str = "auto",
               max_tokens: int | None = None) -> ToolTurn:
    """One step of a tool-calling conversation (OpenAI "tools" format). tool_choice="none" asks
    for a text answer; the tools stay declared because the history already contains calls."""
    body = {
        "model": config.LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens or config.LLM_MAX_OUTPUT_TOKENS,
        "temperature": config.LLM_TEMPERATURE,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice
    for attempt in range(EMPTY_RETRIES + 1):
        data = _post(body)
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {"role": "assistant", "content": ""}
        if message.get("tool_calls") or (message.get("content") or "").strip():
            break
    else:
        raise LLMError(f"LLM API returned an empty reply (finish_reason={choice.get('finish_reason')})", "empty")
    message.setdefault("role", "assistant")
    return ToolTurn(message, message.get("tool_calls") or [], (message.get("content") or "").strip(),
                    data.get("model", body["model"]), choice.get("finish_reason"), data.get("usage") or {})
