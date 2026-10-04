"""The LLM client's error handling, against a fake provider: retries, quotas, empty replies,
cancellation and the request meter."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from src.core import config
from src.services import llm

GEMINI_PER_MINUTE = json.dumps([{"error": {
    "code": 429, "status": "RESOURCE_EXHAUSTED",
    "message": "You exceeded your current quota, please check your plan and billing details.",
    "details": [{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}, {"retryDelay": "1s"}]}}])
GEMINI_PER_DAY = GEMINI_PER_MINUTE.replace("PerMinute", "PerDay")
OPENAI_QUOTA = json.dumps({"error": {"type": "insufficient_quota", "message": "You exceeded your current quota"}})
OK = {"choices": [{"message": {"content": "Hello"}, "finish_reason": "stop"}], "model": "fake-model",
      "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 15}}
EMPTY = {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}],
         "usage": {"prompt_tokens": 10, "completion_tokens": 0, "total_tokens": 10}}


class FakeProvider(BaseHTTPRequestHandler):
    """Answers each request with the next (status, body) in `script`."""
    script: list[tuple[int, object]] = []
    calls = 0

    def do_POST(self):
        FakeProvider.calls += 1
        self.rfile.read(int(self.headers["Content-Length"]))
        status, body = FakeProvider.script.pop(0) if FakeProvider.script else (200, OK)
        data = (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(status)
        if status in (429, 503):
            self.send_header("Retry-After", "0.01")  # retry at once, keeping the tests fast
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def provider(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), FakeProvider)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(config, "LLM_BASE_URL", f"http://127.0.0.1:{server.server_port}/")
    monkeypatch.setattr(config, "LLM_MAX_RETRY_WAIT_SECONDS", 5.0)
    monkeypatch.setattr(config, "LLM_MAX_TOTAL_RETRY_SECONDS", 5.0)
    FakeProvider.script, FakeProvider.calls = [], 0
    yield FakeProvider
    server.shutdown()


@pytest.mark.parametrize("status, body, kind", [
    (429, GEMINI_PER_MINUTE, "rate_limited"),
    (429, GEMINI_PER_DAY, "quota"),
    (429, OPENAI_QUOTA, "quota"),
    (503, "overloaded", "unavailable"),
    (500, "boom", "unavailable"),
    (504, "gateway timeout", "timeout"),
    (401, "bad key", "not_configured"),
    (400, "bad request", "rejected"),
])
def test_http_errors_are_classified(status, body, kind):
    assert llm._http_error(status, body).kind == kind


def test_rate_limit_is_retried(provider):
    provider.script = [(429, GEMINI_PER_MINUTE), (503, "overloaded")]
    assert llm.chat("system", "hi").text == "Hello"
    assert provider.calls == 3


def test_spent_quota_is_not_retried(provider):
    provider.script = [(429, GEMINI_PER_DAY)]
    with pytest.raises(llm.LLMError) as e:
        llm.chat("system", "hi")
    assert e.value.kind == "quota"
    assert provider.calls == 1


def test_retries_are_bounded(provider):
    provider.script = [(503, "overloaded")] * 10
    with pytest.raises(llm.LLMError) as e:
        llm.chat("system", "hi")
    assert e.value.kind == "unavailable"
    assert provider.calls == llm.RETRIES + 1


def test_total_retry_wait_per_question_is_bounded(provider, monkeypatch):
    """Across all the LLM calls of one question, back-offs add up to LLM_MAX_TOTAL_RETRY_SECONDS."""
    monkeypatch.setattr(config, "LLM_MAX_TOTAL_RETRY_SECONDS", 0.015)
    provider.script = [(503, "overloaded")] * 10
    with llm.metered() as meter, pytest.raises(llm.LLMError):
        llm.chat("system", "hi")
    assert provider.calls == 2  # waited 0.01 s once; a second wait would pass 0.015 s
    assert meter.retry_wait_s == pytest.approx(0.01)


def test_empty_reply_is_asked_again_then_reported(provider):
    provider.script = [(200, EMPTY), (200, OK)]
    assert llm.chat("system", "hi").text == "Hello"
    provider.script, provider.calls = [(200, EMPTY)] * 5, 0
    with pytest.raises(llm.LLMError) as e:
        llm.chat("system", "hi")
    assert e.value.kind == "empty"
    assert provider.calls == llm.EMPTY_RETRIES + 1


def test_meter_counts_every_call_including_reasoning_tokens(provider):
    provider.script = [(200, EMPTY), (200, OK)]
    with llm.metered() as meter:
        llm.chat("system", "hi")
    assert meter.calls == 2
    assert meter.prompt_tokens == 20
    # OK reports 2 completion tokens but 15 total for 10 prompt: 5 output were billed (reasoning)
    assert meter.completion_tokens == 0 + 5


def test_cancelled_meter_stops_before_calling(provider):
    cancel = threading.Event()
    cancel.set()
    with llm.metered(cancel), pytest.raises(llm.LLMError) as e:
        llm.chat("system", "hi")
    assert e.value.kind == "cancelled"
    assert provider.calls == 0


def test_unreachable_provider(monkeypatch):
    monkeypatch.setattr(config, "LLM_BASE_URL", "http://127.0.0.1:9/")
    with pytest.raises(llm.LLMError) as e:
        llm.chat("system", "hi")
    assert e.value.kind == "unavailable"
