"""
Comprehensive Test Suite for Swipies MCP Billing, Quotas & Subscription Management.
Tests quota inspection, error diagnostics, catalog, estimation, quote generation,
idempotent payment sessions, and activation checks.
"""
import asyncio
import importlib.util
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from quart import Quart, jsonify, request

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gateway = load("gateway_billing_test", "api/agent_access.py")
billing = load("billing_under_test", "api/agent_billing.py")


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def app():
    app = Quart(__name__)
    app.testing = True

    async def bootstrap(data, address):
        return {"tenant_id": "test-tenant", "created": True}

    gateway.register_agent_access(
        app,
        authenticate=lambda: request.headers.get("Authorization", "").startswith("Bearer "),
        bootstrap=bootstrap,
        origin_allowed=lambda o: True,
    )
    return app


def rpc(app, method, params=None, token="tenant-test-user", ident=1, headers=None):
    async def invoke():
        message = {"jsonrpc": "2.0", "id": ident, "method": method}
        if params is not None:
            message["params"] = params
        hdr = {"Authorization": "Bearer " + token} if token else {}
        hdr.update(headers or {})
        response = await app.test_client().post("/api/v1/agent-access/mcp", headers=hdr, json=message)
        return response.status_code, await response.get_json(), response.headers

    return run(invoke())


# ==========================================
# 1. Account & Limits Inspection Tests
# ==========================================

def test_get_account_limits_structure(app):
    status, res, _ = rpc(
        app,
        "tools/call",
        {"name": "swipies_get_account_limits", "arguments": {"timezone": "Asia/Tashkent"}},
    )
    assert status == 200
    assert not res.get("error")
    data = json.loads(res["result"]["content"][0]["text"])

    # Check Account Details
    assert data["account"]["plan_id"] in ["free", "plus", "pro"]
    assert data["account"]["status"] == "active"
    assert data["account"]["timezone"] == "Asia/Tashkent"

    # Check Credit Balance & Conversion Rules
    assert "balance" in data["credits"]
    assert data["credits"]["conversion_rules"]["tokens_per_credit"] == 1000
    assert data["credits"]["conversion_rules"]["ocr_pages_per_credit"] == 1

    # Check Quotas & Reset Timestamps
    quotas = data["quotas"]
    assert "daily_tokens" in quotas
    assert "monthly_tokens" in quotas
    assert "reset_at" in quotas["daily_tokens"]
    assert "+05:00" in quotas["daily_tokens"]["reset_at"] or "Tashkent" in quotas["daily_tokens"]["reset_at"]
    assert "reset_at" in quotas["monthly_tokens"]

    # Check Breakdown
    assert "embeddings" in data["breakdown"]
    assert "generation" in data["breakdown"]
    assert "indexing" in data["breakdown"]

    # Check BYOK info
    assert "allowed" in data["byok"]
    assert "policy" in data["byok"]


def test_diagnose_swipies_daily_limit_error(app):
    err_msg = "Daily AI token limit reached (50,000 / 50,000). Upgrade your plan to increase limits."
    status, res, _ = rpc(
        app,
        "tools/call",
        {"name": "swipies_get_account_limits", "arguments": {"error_message": err_msg}},
    )
    assert status == 200
    data = json.loads(res["result"]["content"][0]["text"])

    diag = data["error_diagnosis"]
    assert diag["source"] == "swipies"
    assert diag["reason_code"] == "DAILY_TOKEN_LIMIT_REACHED"
    assert diag["limit"] == 50000
    assert diag["used"] == 50000
    assert diag["remaining"] == 0
    assert diag["reset_at"] is not None
    assert "upgrade_plan" in diag["resolution_options"]
    assert "switch_to_byok" in diag["resolution_options"]


def test_diagnose_provider_quota_and_rate_limit(app):
    # Provider 429 Rate limit
    rate_err = "openai.RateLimitError: 429 Too Many Requests, TPM limit reached for model gpt-4o"
    diag1 = billing.diagnose_error(rate_err)
    assert diag1["source"] == "external_provider"
    assert diag1["reason_code"] == "PROVIDER_RATE_LIMITED"
    assert "retry_with_backoff" in diag1["resolution_options"]

    # Provider Insufficient Quota
    quota_err = "Error code: 429 - {'error': {'message': 'You exceeded your current quota, please check your plan and billing details.'}}"
    diag2 = billing.diagnose_error(quota_err)
    assert diag2["source"] == "external_provider"
    assert diag2["reason_code"] == "PROVIDER_QUOTA_EXCEEDED"
    assert "top_up_external_provider" in diag2["resolution_options"]

    # Provider Auth Error
    auth_err = "openai.AuthenticationError: Incorrect API key provided: sk-abcdef1234567890."
    diag3 = billing.diagnose_error(auth_err)
    assert diag3["source"] == "external_provider"
    assert diag3["reason_code"] == "PROVIDER_AUTH_ERROR"
    # Ensure sensitive key was sanitized
    assert "sk-abcdef1234567890" not in diag3["details"]
    assert "[REDACTED_API_KEY]" in diag3["details"]


def test_sensitive_headers_and_tokens_redacted_in_diagnosis():
    raw_error = "Authorization: Bearer swipies_secret_token_12345 failed with key=ragflow-testapikey99"
    diag = billing.diagnose_error(raw_error)
    assert "swipies_secret_token_12345" not in diag["details"]
    assert "ragflow-testapikey99" not in diag["details"]
    assert "REDACTED" in diag["details"]


# ==========================================
# 2. Plan Catalog Tests
# ==========================================

def test_list_plans_catalog(app):
    status, res, _ = rpc(
        app,
        "tools/call",
        {"name": "swipies_list_plans", "arguments": {"currency": "ALL"}},
    )
    assert status == 200
    data = json.loads(res["result"]["content"][0]["text"])

    plans = {p["id"]: p for p in data["plans"]}
    assert "free" in plans
    assert "plus" in plans
    assert "pro" in plans
    assert "self_hosted" in plans

    # Check Plus pricing: $20 / 199,000 UZS
    assert plans["plus"]["price_usd"] == 20.00
    assert plans["plus"]["price_uzs"] == 199000
    assert plans["plus"]["quotas"]["daily_tokens"] == 500000
    assert plans["plus"]["branding"]["unbranded_outputs"] is True

    # Check Pro pricing: $40 / 399,000 UZS
    assert plans["pro"]["price_usd"] == 40.00
    assert plans["pro"]["price_uzs"] == 399000
    assert plans["pro"]["quotas"]["daily_tokens"] == 2000000
    assert plans["pro"]["byok"]["allowed"] is True

    # Check Addons
    addons = {a["id"]: a for a in data["addons"]}
    assert "credit_pack_10k" in addons
    assert addons["credit_pack_10k"]["price_usd"] == 10.00
    assert addons["credit_pack_10k"]["price_uzs"] == 100000
    assert addons["credit_pack_10k"]["token_equivalent"] == 10000000

    # Check Terms & BYOK Policy
    assert "zero consumption" in data["byok_policy"]["quota_impact"].lower()
    assert "annual_discount" in data["terms"]


def test_list_plans_currency_filter(app):
    status, res, _ = rpc(
        app,
        "tools/call",
        {"name": "swipies_list_plans", "arguments": {"currency": "USD"}},
    )
    assert status == 200
    data = json.loads(res["result"]["content"][0]["text"])
    for p in data["plans"]:
        assert "price_usd" in p
        assert "price_uzs" not in p


# ==========================================
# 3. Workload Estimation Tests
# ==========================================

def test_estimate_dataset_workload_7_books(app):
    # Benchmark: 7 books = ~1,680,000 raw tokens
    status, res, _ = rpc(
        app,
        "tools/call",
        {"name": "swipies_estimate_dataset_plan", "arguments": {"tokens": 1680000}},
    )
    assert status == 200
    data = json.loads(res["result"]["content"][0]["text"])

    workload = data["workload_analysis"]
    assert workload["raw_tokens"] == 1680000
    # Overlap overhead is 15% (1.15 multiplier)
    assert workload["chunk_overlap_percentage"] == "15%"
    assert workload["total_embedding_tokens"] == 1932000  # 1,680,000 * 1.15
    assert workload["estimated_chunks"] > 3000

    # Check feasibility comparison across tiers
    timeline = data["processing_timeline_by_plan"]
    assert "38.6 days" in timeline["free"] or "days" in timeline["free"]
    assert "3.9 days" in timeline["plus"] or "days" in timeline["plus"]
    assert "1.0 day" in timeline["pro"]

    # Recommended options should propose Pro for 1-day processing
    recs = data["recommended_options"]
    assert any(r["target_plan"] == "pro" for r in recs)

    # Disclaimer and assumptions
    assert "±15%" in data["variance_margin"]
    assert len(data["assumptions"]) >= 3
    assert "not a guaranteed fixed cost" in data["disclaimer"].lower()


# ==========================================
# 4. Purchase Sequence Tests
# ==========================================

def test_create_quote_pro_monthly(app):
    status, res, _ = rpc(
        app,
        "tools/call",
        {"name": "swipies_create_subscription_quote", "arguments": {"plan_id": "pro", "currency": "UZS"}},
    )
    assert status == 200
    quote = json.loads(res["result"]["content"][0]["text"])

    assert quote["quote_id"].startswith("quote_")
    assert quote["plan_id"] == "pro"
    assert quote["pricing"]["currency"] == "UZS"
    assert quote["pricing"]["total_uzs"] == 399000
    assert quote["terms"]["auto_renew"] is True
    assert quote["terms"]["period_days"] == 30
    assert quote["valid_for_seconds"] == 900
    assert "swipies_create_payment_session" in quote["confirmation_required"]


def test_create_payment_session_requires_write_scope(app):
    # Get quote first
    quote = billing.create_subscription_quote(
        {"tenant_id": "tenant-test", "user_id": "user-test"},
        {"plan_id": "plus", "currency": "UZS"},
    )

    # Try creating payment session with read-only principal
    read_only_principal = {
        "tenant_id": "tenant-test",
        "user_id": "user-test",
        "scopes": ["swipies:read"],
        "authorization": "Bearer ro-token",
    }
    with pytest.raises(PermissionError) as exc_info:
        billing.create_payment_session(
            read_only_principal,
            {
                "quote_id": quote["quote_id"],
                "idempotency_key": "idemp_test_key_001",
                "user_confirmed": True,
            },
        )
    assert "Write permission" in str(exc_info.value)


def test_create_payment_session_requires_user_confirmation(app):
    quote = billing.create_subscription_quote(
        {"tenant_id": "tenant-test", "user_id": "user-test"},
        {"plan_id": "plus", "currency": "UZS"},
    )
    write_principal = {
        "tenant_id": "tenant-test",
        "user_id": "user-test",
        "scopes": ["swipies:read", "swipies:write"],
        "authorization": "Bearer rw-token",
    }

    # Attempt without explicit user confirmation
    with pytest.raises(ValueError) as exc_info:
        billing.create_payment_session(
            write_principal,
            {
                "quote_id": quote["quote_id"],
                "idempotency_key": "idemp_test_key_002",
                "user_confirmed": False,
            },
        )
    assert "User confirmation is required" in str(exc_info.value)


def test_create_payment_session_and_idempotency(app):
    quote = billing.create_subscription_quote(
        {"tenant_id": "tenant-test", "user_id": "user-test"},
        {"plan_id": "pro", "currency": "UZS"},
    )
    write_principal = {
        "tenant_id": "tenant-test",
        "user_id": "user-test",
        "scopes": ["swipies:read", "swipies:write"],
        "authorization": "Bearer rw-token",
    }
    idemp_key = "idemp_unique_key_12345"

    # First call: creates payment session
    sess1 = billing.create_payment_session(
        write_principal,
        {
            "quote_id": quote["quote_id"],
            "idempotency_key": idemp_key,
            "user_confirmed": True,
        },
    )
    assert sess1["status"] == "pending"
    assert "/v1/payment/checkout/" in sess1["checkout_url"]
    assert sess1["amount_uzs"] == 399000

    # Repeat call with exact same idempotency key: should return existing session
    sess2 = billing.create_payment_session(
        write_principal,
        {
            "quote_id": quote["quote_id"],
            "idempotency_key": idemp_key,
            "user_confirmed": True,
        },
    )
    # The session ID and checkout URL must match without creating a duplicate order
    assert sess2["payment_session_id"] == sess1["payment_session_id"]
    assert sess2["checkout_url"] == sess1["checkout_url"]


def test_payment_status_check(app):
    write_principal = {
        "tenant_id": "tenant-test",
        "user_id": "user-test",
        "scopes": ["swipies:read", "swipies:write"],
        "authorization": "Bearer rw-token",
    }
    quote = billing.create_subscription_quote(
        write_principal,
        {"plan_id": "plus", "currency": "UZS"},
    )
    sess = billing.create_payment_session(
        write_principal,
        {
            "quote_id": quote["quote_id"],
            "idempotency_key": "idemp_status_check_key_01",
            "user_confirmed": True,
        },
    )

    # Check status via MCP tool
    status, res, _ = rpc(
        app,
        "tools/call",
        {"name": "swipies_check_payment_status", "arguments": {"order_id": sess["order_id"]}},
    )
    assert status == 200
    data = json.loads(res["result"]["content"][0]["text"])

    assert data["order_id"] == sess["order_id"]
    assert data["status"] in ["pending", "waiting_otp", "paid"]
    assert "subscription_activated" in data
