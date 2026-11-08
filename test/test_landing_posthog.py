"""PostHog isolation/privacy/auth/outbox tests; all transport is synthetic."""

import ast
import datetime
import importlib.util
import json
import sqlite3
import sys
from contextlib import closing, contextmanager
from functools import wraps
from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "new site for swipies"
sys.path.insert(0, str(SITE))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ph = load(SITE / "landing_posthog.py", "landing_posthog")
collector = load(SITE / "landing_posthog_collector.py", "landing_posthog_collector")
from landing_admin_api import load_core

reporting = load_core()
BASE = {
    "start": "2025-06-02T00:00:00Z",
    "end": "2025-06-04T00:00:00Z",
    "timezone": "UTC",
    "group": "day",
}
VISITOR = "v_abcdefgh_1748736000000"


def config(**values):
    return ph.Config(
        enabled=True,
        project_id="718705",
        project_token="synthetic-capture-value",
        read_key="synthetic-private-read-value",
        **values,
    )


def responses():
    # Four created accounts across three converting browser IDs, and 15 views
    # across 10 IDs. Deliberately unequal: clicks/events are never users.
    stamp = int(reporting.instant(BASE["start"]).timestamp())
    return [
        [["current", 10, 12, 15, 4, 2], ["previous", 8, 9, 10, 1, 0]],
        [["current", stamp, 7, 9, 4, 2]],
        [["current", "hero_start", 6, 20], ["previous", "hero_start", 4, 7]],
        [["current", "google", "launch", "https://search.example", 6, 9]],
        [["current", "desktop", 7, 9]],
        [[10, 6, 3, 1]],
        [[8, 4, 1, 0]],
    ]


class Network:
    def __init__(self):
        self.calls = []
        self.error = 0
        self.rows = responses()

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        data = {"results": self.rows[(len(self.calls) - 1) % 7]}
        return SimpleNamespace(
            status_code=self.error or 200,
            content=b"{}",
            headers={"Retry-After": "75"},
            json=lambda: data,
        )


def test_generated_queries_distincts_funnel_order_and_no_read_key():
    queries = []
    rows = iter(responses())
    result = ph.build_report(
        reporting.Filters.parse(BASE), lambda sql: (queries.append(sql), next(rows))[1]
    )
    assert result["totals"]["current"]["visitors"] == 10
    assert result["totals"]["current"]["registrations"] == 4
    assert result["totals"]["current"]["registration_conversion"] == 30
    assert result["totals"]["current"]["payment_conversion"] == 10
    assert result["funnel"]["current"][1]["lost"] == 4
    assert result["funnel"]["current"][2]["lost"] == 3
    assert result["ctas"][0][2:] == [6, 20]
    assert len(result["timeline"]) == 4
    assert result["timeline"][1][2:] == [0, 0, 0, 0]
    assert "uniqExactIf" in queries[0] and "UNION ALL" in queries[0]
    assert "timestamp>=c.t2" in queries[5] and "timestamp>=r.t3" in queries[5]
    assert "INTERVAL 7 DAY" in queries[5]
    assert "properties.swipies_internal = false" in queries[0]
    assert "properties.site_area" in queries[5]
    assert "event NOT IN ('$pageview','cta_click')" in queries[5]
    assert "properties.referrer_origin" in queries[3]
    assert "2025-06-02 00:00:00" in queries[0]
    assert "synthetic-private-read-value" not in json.dumps(result)


def test_hourly_dst_buckets_remain_distinct():
    filters = reporting.Filters.parse(
        {
            **BASE,
            "start": "2025-10-25T22:00:00Z",
            "end": "2025-10-26T23:00:00Z",
            "timezone": "Europe/Berlin",
            "group": "hour",
        }
    )
    rows = iter([[], [], [], [], [], [[0, 0, 0, 0]], [[0, 0, 0, 0]]])
    result = ph.build_report(filters, lambda _: next(rows))
    assert len([r for r in result["timeline"] if r[0] == "current"]) == 25
    assert len({r[1] for r in result["timeline"] if r[0] == "current"}) == 25
    assert result["totals"]["current"]["registration_conversion"] is None


def test_cache_rate_limit_and_explicit_stale_data():
    network = Network()
    now = [0.0]
    provider = ph.PostHog(config(), network, lambda: now[0])
    filters = reporting.Filters.parse(BASE)
    first = provider.report(filters)
    assert len(network.calls) == 7 and not first["cached"]
    assert provider.report(filters)["cached"] and len(network.calls) == 7
    now[0] = 61
    network.error = 429
    stale = provider.report(filters)
    assert (
        stale["stale"]
        and stale["retry_after"] == 75
        and stale["updated_at"] == first["updated_at"]
    )
    provider.report(filters)
    assert len(network.calls) == 8
    now[0] = 1000
    with pytest.raises(ph.ProviderError):
        provider.report(filters)


def test_query_budget_retry_after_can_require_a_full_hour():
    now = [0.0]
    calls = []
    status = [429]

    def send(*args, **kwargs):
        calls.append(True)
        return SimpleNamespace(
            status_code=status[0],
            headers={"Retry-After": "3600"},
            content=b"{}",
            json=lambda: {"results": [[1]]},
        )

    provider = ph.PostHog(config(), SimpleNamespace(post=send), lambda: now[0])
    with pytest.raises(ph.ProviderError) as first:
        provider.query("SELECT 1")
    assert first.value.retry_after == 3600
    now[0] = 3599
    with pytest.raises(ph.ProviderError):
        provider.query("SELECT 1")
    assert len(calls) == 1
    now[0] = 3601
    status[0] = 200
    assert provider.query("SELECT 1") == [[1]]


@pytest.mark.parametrize(
    "host",
    [
        "http://us.posthog.com",
        "https://user:private@us.posthog.com",
        "https://us.posthog.com/path",
        "https://us.posthog.com?private=1",
    ],
)
def test_invalid_hosts_are_disabled_without_echoing_input(host):
    cfg = ph.Config.read({"POSTHOG_ENABLED": "1", "POSTHOG_API_HOST": host})
    assert cfg.error and not cfg.capture_ready
    assert host not in cfg.error


def test_self_hosted_origins_and_minimum_scope_instructions():
    cfg = ph.Config.read(
        {
            "POSTHOG_API_HOST": "https://analytics.example.invalid",
            "POSTHOG_INGEST_HOST": "https://capture.example.invalid",
            "POSTHOG_ASSET_HOST": "https://assets.example.invalid",
        }
    )
    assert cfg.api_host == "https://analytics.example.invalid"
    assert "query:read" in str(cfg.status())
    assert "read_key" not in cfg.status() and "project_token" not in cfg.status()


@pytest.fixture
def app(tmp_path):
    database = tmp_path / "journal.sqlite"
    with closing(sqlite3.connect(database)) as db:
        db.execute(
            "CREATE TABLE admin_sessions (token TEXT,username TEXT,expires_at TEXT)"
        )
        expires = (
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)
        ).isoformat()
        db.execute(
            "INSERT INTO admin_sessions VALUES (?,?,?)",
            ("synthetic-owner", "owner", expires),
        )
        db.commit()
    source = ast.parse((SITE / "api.py").read_text(encoding="utf-8"))
    nodes = [
        n
        for n in source.body
        if isinstance(n, ast.FunctionDef)
        and n.name
        in {"get_authenticated_admin", "admin_required", "utc_now", "utc_now_iso"}
    ]

    # Preserve the production auth implementation, but explicitly close the
    # test-owned connection (legacy with-connect otherwise only commits it).
    @contextmanager
    def owned_connection(*args, **kwargs):
        with closing(sqlite3.connect(*args, **kwargs)) as conn, conn:
            yield conn

    ns = {
        "DB_FILE": str(database),
        "sqlite3": SimpleNamespace(connect=owned_connection),
        "datetime": datetime,
        "wraps": wraps,
        "request": request,
        "jsonify": jsonify,
    }
    exec(  # noqa: S102 -- compile only named auth functions from the local repository.
        compile(
            ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
            "real_landing_auth",
            "exec",
        ),
        ns,
    )
    web = Flask(__name__)
    web.testing = True
    network = Network()
    facts_calls = []

    def facts(path):
        facts_calls.append(path)
        return {
            "current": {"totals": {"new_users": 5}},
            "previous": {"totals": {"new_users": 2}},
        }

    ph.register_posthog(
        web,
        database,
        admin_required=ns["admin_required"],
        admin_identity=ns["get_authenticated_admin"],
        platform_reader=facts,
        config=config(state_db=str(tmp_path / "posthog-state.sqlite")),
        transport=network,
        start_collector=False,
    )
    return SimpleNamespace(
        web=web,
        client=web.test_client(),
        database=database,
        network=network,
        facts_calls=facts_calls,
    )


def post(app, path, body):
    return app.client.post(
        path,
        json=body,
        headers={"Authorization": "Bearer synthetic-owner"},
        base_url="https://swipies.app",
    )


def test_existing_native_auth_protects_page_and_all_methods(app):
    for path in [
        "/api/admin/posthog/status",
        "/api/admin/posthog/report",
        "/api/admin/posthog/open",
    ]:
        response = (
            app.client.get(path)
            if path.endswith("status")
            else app.client.post(path, json={"filters": BASE})
        )
        assert response.status_code == 401
    assert app.client.get("/admin/posthog").status_code == 302
    response = post(app, "/api/admin/posthog/open", {})
    assert response.status_code == 200
    cookie = response.headers["Set-Cookie"]
    assert (
        "HttpOnly" in cookie
        and "Secure" in cookie
        and "SameSite=Strict" in cookie
        and "Path=/admin/posthog" in cookie
    )
    page = app.client.get("/admin/posthog", base_url="https://swipies.app")
    assert page.status_code == 200
    page.close()
    with closing(sqlite3.connect(app.database)) as db:
        db.execute("DELETE FROM admin_sessions")
        db.commit()
    assert (
        app.client.get("/admin/posthog", base_url="https://swipies.app").status_code
        == 302
    )
    assert post(app, "/api/admin/posthog/report", {"filters": BASE}).status_code == 401


def test_comparison_reads_existing_source_once_and_marks_payments_unavailable(app):
    before = app.database.read_bytes()
    response = post(app, "/api/admin/posthog/report", {"filters": BASE})
    assert response.status_code == 200, response.json
    data = response.json["data"]
    assert data["comparison"]["current"]["registrations"]["system"] == 5
    assert data["comparison"]["current"]["registrations"]["difference"] == -1
    assert data["comparison"]["current"]["payments"]["system"] is None
    assert data["comparison"]["current"]["payments"]["difference"] is None
    assert data["comparison"]["current"]["payments"]["unavailable"]
    assert len(app.facts_calls) == 1 and "timezone=UTC" in app.facts_calls[0]
    assert app.database.read_bytes() == before
    assert response.headers["Cache-Control"] == "no-store"
    assert "synthetic-private-read-value" not in response.get_data(as_text=True)
    assert app.network.calls[0][1]["headers"]["Authorization"].startswith("Bearer ")
    assert app.network.calls[0][1]["allow_redirects"] is False


def test_browser_config_never_exposes_private_read_key(app):
    response = app.client.get(
        "/api/posthog/config", headers={"Origin": "https://api.swipies.app"}
    )
    assert response.json["project_token"] == "synthetic-capture-value"
    assert "synthetic-private-read-value" not in response.get_data(as_text=True)
    assert response.headers["Access-Control-Allow-Origin"] == "https://api.swipies.app"


def test_consent_receipt_is_scoped_bounded_and_not_a_conversion(app):
    data = {"visitor_id": VISITOR, "granted": True}
    assert app.client.post("/api/posthog/consent", json=data).status_code == 403
    headers = {"Origin": "https://swipies.app"}
    assert (
        app.client.post(
            "/api/posthog/consent",
            json={**data, "email": "never@example.invalid"},
            headers=headers,
        ).status_code
        == 400
    )
    assert (
        app.client.post("/api/posthog/consent", json=data, headers=headers).status_code
        == 200
    )
    worker = app.web.extensions["swipies_posthog_collector"]
    assert worker.state.status()["sent"] == 0 and worker.state.status()["pending"] == 0
    assert worker.state.allowed(VISITOR, worker.clock() + 1)
    assert (
        app.client.post(
            "/api/posthog/consent", json={**data, "granted": False}, headers=headers
        ).status_code
        == 200
    )
    assert not worker.state.allowed(VISITOR, worker.clock() + 1)


def test_disabled_module_shows_setup_without_network_or_state(tmp_path):
    web = Flask(__name__)
    network = Network()

    def authorized(fn):
        return fn

    ph.register_posthog(
        web,
        tmp_path / "journal.sqlite",
        admin_required=authorized,
        admin_identity=lambda _: True,
        platform_reader=lambda _: None,
        config=ph.Config(),
        transport=network,
    )
    result = (
        web.test_client()
        .post("/api/admin/posthog/report", json={"filters": BASE})
        .json["data"]
    )
    assert result["state"] == "setup" and not network.calls
    assert not (tmp_path / "posthog-state.sqlite").exists()
    assert web.test_client().get("/api/posthog/config").json == {
        "enabled": False,
        "internal": False,
    }


def test_provider_failure_does_not_break_existing_pages(app):
    @app.web.get("/existing")
    def existing():
        return "existing page"

    app.network.error = 503
    response = post(app, "/api/admin/posthog/report", {"filters": BASE})
    assert response.status_code == 503 and "Retry-After" in response.headers
    assert app.client.get("/existing").get_data(as_text=True) == "existing page"
    assert "synthetic-private-read-value" not in response.get_data(as_text=True)


@pytest.mark.parametrize(
    "bad",
    [
        {"group": "month"},
        {"timezone": "UTC'; SELECT private"},
        {"start": "2099-01-01T00:00:00Z"},
        {"utm_source": "unexpected"},
    ],
)
def test_invalid_filters_never_become_provider_sql(app, bad):
    response = post(app, "/api/admin/posthog/report", {"filters": {**BASE, **bad}})
    assert response.status_code == 400 and not app.network.calls


def scenario(tmp_path, network_status=200):
    now = [1748736000.0]
    state = collector.State(tmp_path / "state.sqlite", lambda: now[0])
    state.consent(VISITOR, True)
    user = {
        "id": "private-user-row",
        "visitor_id": VISITOR,
        "create_time": int((now[0] + 1) * 1000),
        "is_superuser": False,
    }
    order = {
        "id": "private-order-row",
        "visitor_id": VISITOR,
        "create_time": int((now[0] + 2) * 1000),
        "is_superuser": False,
        "purpose": "subscription_upgrade",
        "status": "pending",
        "plan_id": "pro",
    }
    facts = {"users": [user], "ledger": [], "orders": [order]}
    sent = []
    status = [network_status]

    def send(url, **kwargs):
        sent.append(kwargs["json"])
        return SimpleNamespace(status_code=status[0], headers={})

    worker = collector.Collector(
        config(),
        tmp_path / "journal.sqlite",
        state=state,
        facts=lambda _: facts,
        transport=SimpleNamespace(post=send),
        clock=lambda: now[0],
    )
    now[0] += 10
    return SimpleNamespace(
        now=now, state=state, facts=facts, sent=sent, worker=worker, status=status
    )


def test_confirmed_conversions_are_once_and_no_private_user_payment_content(tmp_path):
    s = scenario(tmp_path)
    s.worker.tick()
    s.worker.tick()
    assert [row["event"] for row in s.sent] == [
        "registration_completed",
        "payment_started",
    ]
    s.facts["orders"][0]["status"] = "paid"
    s.worker.tick()
    s.worker.tick()
    assert [row["event"] for row in s.sent].count("payment_completed") == 1
    body = json.dumps(s.sent)
    for private in [
        "private-user-row",
        "private-order-row",
        "synthetic-private-read-value",
        "email",
        "password",
    ]:
        assert private not in body
    assert all(row["properties"]["swipies_origin"] == "server" for row in s.sent)
    assert all(
        row["properties"]["$geoip_disable"] and row["properties"]["$ip"] is None
        for row in s.sent
    )


def test_retries_reuse_the_same_native_posthog_uuid(tmp_path):
    s = scenario(tmp_path, 503)
    s.worker.tick()
    assert s.state.status()["pending"] == 2
    ident = s.sent[0]["uuid"]
    s.status[0] = 200
    s.now[0] += 100
    s.worker.tick()
    assert s.sent[1]["uuid"] == ident and s.sent[1]["properties"]["$insert_id"] == ident
    assert s.state.status()["pending"] == 0


def test_mirrored_ledger_does_not_duplicate_checkout_or_paid_event(tmp_path):
    s = scenario(tmp_path)
    s.worker.tick()
    s.facts["orders"][0]["external_transaction_id"] = "gateway-private"
    s.facts["ledger"] = [
        {
            **s.facts["orders"][0],
            "id": "ledger-private",
            "transaction_id": "gateway-private",
            "status": "PAID",
        }
    ]
    s.worker.tick()
    s.facts["orders"][0]["status"] = "paid"
    s.worker.tick()
    assert [row["event"] for row in s.sent].count("payment_started") == 1
    assert [row["event"] for row in s.sent].count("payment_completed") == 1
    assert "gateway-private" not in json.dumps(s.sent)


def test_no_preconsent_backfill_or_postrevocation_pending_delivery(tmp_path):
    s = scenario(tmp_path, 503)
    s.worker.tick()
    s.state.consent(VISITOR, False)
    assert s.state.status()["cancelled"] == 2
    s.now[0] += 100
    s.status[0] = 200
    s.worker.tick()
    assert len(s.sent) == 1
    s.state.consent(VISITOR, True)
    s.worker.tick()
    assert len(s.sent) == 1
    assert not s.state.enqueue(
        "registration_completed", ["old"], VISITOR, s.now[0] - 1, {}
    )


def test_internal_accounts_and_ads_deposits_are_excluded(tmp_path):
    s = scenario(tmp_path)
    s.facts["users"][0]["is_superuser"] = True
    s.facts["orders"][0]["purpose"] = "advertiser_deposit"
    s.facts["orders"][0]["status"] = "PAID"
    s.worker.tick()
    assert not s.sent


def test_capture_disabled_never_queries_platform(tmp_path):
    state = collector.State(tmp_path / "state.sqlite")
    worker = collector.Collector(
        ph.Config(),
        tmp_path / "journal.sqlite",
        state=state,
        facts=lambda _: (_ for _ in ()).throw(AssertionError("must not query")),
    )
    worker.tick()
    assert state.status()["pending"] == 0
