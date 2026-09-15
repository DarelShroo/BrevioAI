"""FASE 1: structured 429 observability."""

import json
from unittest.mock import MagicMock

import httpx
import pytest
from openai import RateLimitError

from core.brevio.services.provider_quota.observability import (
    extract_rate_limit_signals,
    log_provider_429,
    parse_duration_seconds,
    parse_retry_after_headers,
    parse_retry_delay_from_body,
    sanitize_scope_for_log,
)


def test_parse_retry_after_ms_preferred():
    ms, sec, wait = parse_retry_after_headers(
        {"retry-after-ms": "1500", "retry-after": "9"}
    )
    assert ms == 1500.0
    assert sec == 9.0
    assert wait == 1.5


def test_parse_retry_after_seconds():
    ms, sec, wait = parse_retry_after_headers({"Retry-After": "3"})
    assert ms is None
    assert sec == 3.0
    assert wait == 3.0


def test_extract_from_rate_limit_error_with_googleish_body():
    req = httpx.Request(
        "POST",
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    )
    resp = httpx.Response(
        429,
        request=req,
        headers={"retry-after-ms": "2000", "x-request-id": "abc"},
        json={
            "error": {
                "code": 429,
                "message": "Resource exhausted",
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {
                        "quotaMetric": "generate_content_requests",
                        "quotaId": "GenerateRequestsPerMinutePerProject",
                        "reason": "RATE_LIMIT_EXCEEDED",
                    }
                ],
            }
        },
    )
    err = RateLimitError("rate limited", response=resp, body=resp.json())
    signals = extract_rate_limit_signals(err)
    assert signals.status_code == 429
    assert signals.wait_seconds == 2.0
    assert signals.quota_metric == "generate_content_requests"
    assert signals.quota_id == "GenerateRequestsPerMinutePerProject"
    assert signals.reason is not None


def test_extract_without_response():
    signals = extract_rate_limit_signals(Exception("429 Too Many Requests"))
    assert signals.status_code == 429


def test_sanitize_scope_never_looks_like_key():
    assert sanitize_scope_for_log("platform") == "platform"
    assert sanitize_scope_for_log("cred:abc") == "cred:abc"
    assert sanitize_scope_for_log("sk-" + "x" * 48) == "redacted"


def test_log_provider_429_no_api_key(caplog):
    import logging

    signals = extract_rate_limit_signals(Exception("429"))
    with caplog.at_level(logging.WARNING):
        log_provider_429(
            signals=signals,
            provider="google",
            model="gemini-3.1-flash-lite",
            quota_scope_id="platform",
            phase="MAP",
            chunk_id="1",
            retry_number=0,
            extra={"api_key": "SECRET_SHOULD_NOT_APPEAR"},
        )
    assert "SECRET_SHOULD_NOT_APPEAR" not in caplog.text
    assert "provider_429" in caplog.text
    assert "platform" in caplog.text


def test_parse_duration_seconds():
    assert parse_duration_seconds("32s") == 32.0
    assert parse_duration_seconds("500ms") == 0.5
    assert parse_duration_seconds({"seconds": 1, "nanos": 500_000_000}) == 1.5


def test_retry_delay_from_list_wrapped_provider_body():
    body = [
        {
            "error": {
                "code": 429,
                "message": (
                    "You exceeded your current quota. Please retry in 32.206199412s."
                ),
                "status": "RESOURCE_EXHAUSTED",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                        "violations": [
                            {
                                "quotaMetric": (
                                    "generativelanguage.googleapis.com/"
                                    "generate_content_free_tier_requests"
                                ),
                                "quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier",
                            }
                        ],
                    },
                    {
                        "@type": "type.googleapis.com/google.rpc.RetryInfo",
                        "retryDelay": "32s",
                    },
                ],
            }
        }
    ]
    wait = parse_retry_delay_from_body(body)
    assert wait is not None
    assert abs(wait - 32.206199412) < 1e-6

    req = httpx.Request("POST", "https://example.com/v1/chat/completions")
    resp = httpx.Response(429, request=req)
    err = RateLimitError("429 Too Many Requests", response=resp, body=body)
    signals = extract_rate_limit_signals(err)
    assert signals.status_code == 429
    assert signals.wait_seconds is not None
    assert signals.wait_seconds >= 32.0
    assert signals.quota_metric == (
        "generativelanguage.googleapis.com/generate_content_free_tier_requests"
    )
    assert signals.quota_id == "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"


def test_openai_retry_after_header_still_wins_if_larger():
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    resp = httpx.Response(
        429,
        request=req,
        headers={"retry-after": "8"},
        json={"error": {"message": "rate limited", "type": "rate_limit_exceeded"}},
    )
    err = RateLimitError("429", response=resp, body=resp.json())
    signals = extract_rate_limit_signals(err)
    assert signals.wait_seconds == 8.0
