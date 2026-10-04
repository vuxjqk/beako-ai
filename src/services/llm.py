"""Minimal chat client for any OpenAI-compatible Chat Completions API.

Gemini and OpenAI both speak this protocol, so switching provider is only a matter of
.env settings (LLM_PROVIDER / LLM_MODEL / LLM_API_KEY, optionally LLM_BASE_URL).
"""

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from src.core import config

DEFAULT_BASE_URLS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openai": "https://api.openai.com/v1/",
}
RETRIES = 3
RETRY_STATUSES = {429, 500, 503}


class LLMError(Exception):
    pass


class LLMNotConfigured(LLMError):
    pass


@dataclass
class Completion:
    text: str
    model: str
    finish_reason: str | None
    usage: dict


def _base_url() -> str:
    base = config.LLM_BASE_URL or DEFAULT_BASE_URLS.get(config.LLM_PROVIDER)
    if not base:
        raise LLMNotConfigured(f"Unknown LLM_PROVIDER {config.LLM_PROVIDER!r}; set LLM_BASE_URL")
    return base.rstrip("/") + "/"


def _retry_after(err: urllib.error.HTTPError, body: str) -> float | None:
    """Seconds the provider asks us to wait: Retry-After header, or Gemini's retryDelay."""
    header = err.headers.get("Retry-After") if err.headers else None
    if header and header.replace(".", "", 1).isdigit():
        return float(header)
    m = re.search(r'"retryDelay":\s*"([\d.]+)s"', body) or re.search(r"retry in ([\d.]+)s", body)
    return float(m.group(1)) + 1 if m else None


def chat(system: str, user: str, *, model: str | None = None, max_tokens: int | None = None,
         temperature: float | None = None) -> Completion:
    """One chat completion; the keyword overrides let the evaluation judge use other settings."""
    if not config.LLM_API_KEY:
        raise LLMNotConfigured("LLM_API_KEY is not set")
    body = {
        "model": model or config.LLM_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_tokens or config.LLM_MAX_OUTPUT_TOKENS,
        "temperature": config.LLM_TEMPERATURE if temperature is None else temperature,
    }
    # Thinking models (e.g. Gemini 2.5) otherwise spend the output budget on reasoning
    if config.LLM_REASONING_EFFORT:
        body["reasoning_effort"] = config.LLM_REASONING_EFFORT
    req = urllib.request.Request(
        _base_url() + "chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.LLM_API_KEY}"},
        method="POST",
    )
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT_SECONDS) as resp:
                data = json.load(resp)
            break
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            # Rate limits and "model overloaded" are transient on shared free tiers; wait as
            # long as the provider asks, unless that is longer than a request should hang
            wait = _retry_after(e, raw) or 2 ** attempt * 2
            if e.code in RETRY_STATUSES and attempt < RETRIES and wait <= config.LLM_MAX_RETRY_WAIT_SECONDS:
                time.sleep(wait)
                continue
            raise LLMError(f"LLM API returned {e.code}: {raw[:500]}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise LLMError(f"LLM API unreachable: {e}") from e

    choice = (data.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    return Completion(text.strip(), data.get("model", body["model"]),
                      choice.get("finish_reason"), data.get("usage") or {})
