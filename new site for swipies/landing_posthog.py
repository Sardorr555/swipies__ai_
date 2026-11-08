"""Isolated, opt-in PostHog reporting. No changes to legacy analytics or auth."""

import ipaddress
import json
import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode, urlsplit

from flask import jsonify, redirect, request, send_file

EVENTS = (
    "$pageview",
    "cta_click",
    "pricing_viewed",
    "plan_selected",
    "registration_started",
    "registration_completed",
    "payment_started",
    "payment_completed",
)
ENVIRONMENT_VARIABLES = [
    "POSTHOG_ENABLED",
    "POSTHOG_PROJECT_ID",
    "POSTHOG_PROJECT_TOKEN",
    "POSTHOG_READ_API_KEY",
    "POSTHOG_API_HOST",
    "POSTHOG_INGEST_HOST",
    "POSTHOG_ASSET_HOST",
    "POSTHOG_ENVIRONMENT",
    "POSTHOG_INTERNAL_CIDRS",
    "POSTHOG_INTERNAL_VISITOR_IDS",
    "POSTHOG_STATE_DB",
    "POSTHOG_CACHE_SECONDS",
]
DEFINITIONS = {
    "visitors": "Уникальные анонимные идентификаторы браузеров с просмотром лендинга; не физические люди и не аккаунты.",
    "sessions": "Уникальные $session_id SDK среди просмотров лендинга; сессии без идентификатора не подсчитываются.",
    "pageviews": "События $pageview на лендинге. Клики не считаются просмотрами или пользователями.",
    "registrations": "Уникальные server-события создания аккаунта, подтверждённые записью user. Подтверждение email — отдельный шаг.",
    "payments": "Уникальные server-события PAID. Рекламные депозиты исключены. Не количество нажатий кнопки оплаты.",
    "funnel": "Один browser ID, строго последовательные этапы внутри выбранного периода, не более 7 дней после первого просмотра. Возвраты вне периода не входят.",
    "registration_conversion": "Браузеры, прошедшие просмотр → CTA → регистрацию / браузеры с просмотром лендинга × 100%.",
    "payment_conversion": "Браузеры, прошедшие все четыре этапа / браузеры с просмотром лендинга × 100%.",
    "payment_time": "Время provisioned_at подтверждённого PAID, если оно есть; иначе время первого наблюдения PAID сборщиком. Историческая дата оплаты не выдумывается.",
}


def origin(value):
    value = str(value).rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "PostHog hosts must be HTTPS origins without paths or credentials"
        )
    return value


@dataclass(repr=False)
class Config:
    enabled: bool = False
    project_id: str = ""
    project_token: str = field(default="", repr=False)
    read_key: str = field(default="", repr=False)
    api_host: str = "https://us.posthog.com"
    ingest_host: str = "https://us.i.posthog.com"
    asset_host: str = "https://us-assets.i.posthog.com"
    environment: str = "production"
    internal_cidrs: tuple = ()
    internal_visitors: frozenset = frozenset()
    cache_seconds: int = 60
    state_db: str = ""
    error: str = ""

    @classmethod
    def read(cls, env=None):
        env = os.environ if env is None else env
        try:
            project = env.get("POSTHOG_PROJECT_ID", "").strip()
            if project and not re.fullmatch(r"[0-9]{1,12}", project):
                raise ValueError("Invalid project id")
            return cls(
                enabled=env.get("POSTHOG_ENABLED", "0").lower() in {"1", "true"},
                project_id=project,
                project_token=env.get("POSTHOG_PROJECT_TOKEN", "").strip(),
                read_key=env.get("POSTHOG_READ_API_KEY", "").strip(),
                api_host=origin(env.get("POSTHOG_API_HOST", "https://us.posthog.com")),
                ingest_host=origin(
                    env.get("POSTHOG_INGEST_HOST", "https://us.i.posthog.com")
                ),
                asset_host=origin(
                    env.get("POSTHOG_ASSET_HOST", "https://us-assets.i.posthog.com")
                ),
                environment=env.get("POSTHOG_ENVIRONMENT", "production"),
                internal_cidrs=tuple(
                    ipaddress.ip_network(item.strip())
                    for item in env.get("POSTHOG_INTERNAL_CIDRS", "").split(",")
                    if item.strip()
                ),
                internal_visitors=frozenset(
                    item.strip()
                    for item in env.get("POSTHOG_INTERNAL_VISITOR_IDS", "").split(",")
                    if item.strip()
                ),
                cache_seconds=max(
                    15, min(300, int(env.get("POSTHOG_CACHE_SECONDS", "60")))
                ),
                state_db=env.get("POSTHOG_STATE_DB", ""),
            )
        except (ValueError, TypeError):
            return cls(
                error="Проверьте переменные окружения PostHog: ID проекта, HTTPS-адреса, CIDR и время кэша."
            )

    @property
    def capture_ready(self):
        return (
            self.enabled
            and not self.error
            and self.environment == "production"
            and bool(self.project_id and self.project_token)
        )

    @property
    def reports_ready(self):
        return self.capture_ready and bool(self.read_key)

    def status(self):
        return {
            "enabled": self.enabled,
            "capture_ready": self.capture_ready,
            "reports_ready": self.reports_ready,
            "project_id": self.project_id,
            "api_host": self.api_host,
            "environment": self.environment,
            "error": self.error or None,
            "required_environment": ENVIRONMENT_VARIABLES,
            "setup": [
                "В проекте PostHog выберите регион и сохраните project token отдельно от секретного ключа.",
                "Секретный ключ ограничьте проектом и правом query:read. Храните его в .env сервиса, вне Git и web root.",
                "Включите POSTHOG_ENABLED=1 и POSTHOG_ENVIRONMENT=production только при согласованном выпуске.",
                "Session Replay, autocapture, запись полей и person profiles выключены кодом.",
            ],
        }


class ProviderError(Exception):
    def __init__(self, message, retry_after=60):
        super().__init__(message)
        self.retry_after = retry_after


class PostHog:
    def __init__(self, config, transport=None, clock=time.monotonic):
        self.config = config
        self.transport, self.clock = transport, clock
        self.cache, self.lock, self.cooldown = OrderedDict(), threading.Lock(), 0

    def query(self, sql):
        if self.clock() < self.cooldown:
            raise ProviderError(
                "PostHog ограничил частоту запросов. Повторите позже.",
                int(self.cooldown - self.clock()) + 1,
            )
        try:
            if self.transport is None:
                import requests

                self.transport = requests
            response = self.transport.post(
                self.config.api_host
                + "/api/projects/"
                + self.config.project_id
                + "/query/",
                headers={
                    "Authorization": "Bearer " + self.config.read_key,
                    "Content-Type": "application/json",
                },
                json={"query": {"kind": "HogQLQuery", "query": sql}, "async": False},
                timeout=(3, 20),
                allow_redirects=False,
            )
            if response.status_code == 429:
                raw = str(response.headers.get("Retry-After", "60"))
                retry = max(15, min(3600, int(raw) if raw.isdigit() else 60))
                self.cooldown = self.clock() + retry
                raise ProviderError(
                    "PostHog ограничил частоту запросов. Повторите позже.", retry
                )
            if response.status_code in (401, 403):
                raise ProviderError(
                    "PostHog отклонил доступ. Проверьте регион, проект и право query:read."
                )
            if response.status_code != 200:
                raise ProviderError(
                    "PostHog временно не вернул отчёт. Существующая аналитика продолжает работать."
                )
            if len(response.content) > 5 * 1024 * 1024:
                raise ProviderError("Отчёт PostHog слишком большой. Сократите период.")
            data = response.json()
            if (
                not isinstance(data, dict)
                or not isinstance(data.get("results"), list)
                or data.get("hasMore")
                or data.get("is_truncated")
            ):
                raise ProviderError(
                    "PostHog вернул неполный отчёт. Сократите период или повторите позже."
                )
            return data["results"]
        except ProviderError:
            raise
        except Exception:  # noqa: BLE001 -- redact all optional-provider failures.
            raise ProviderError(
                "Нет связи с PostHog. Попробуйте обновить страницу позже."
            ) from None

    def report(self, filters):
        key = json.dumps(filters.metadata(), sort_keys=True)
        with self.lock:
            cached = self.cache.get(key)
            if cached and self.clock() - cached[0] < self.config.cache_seconds:
                return {**cached[1], "cached": True, "stale": False}
            try:
                result = build_report(filters, self.query)
            except ProviderError as error:
                if cached and self.clock() - cached[0] < 900:
                    return {
                        **cached[1],
                        "cached": True,
                        "stale": True,
                        "warning": str(error),
                        "retry_after": error.retry_after,
                    }
                raise
            self.cache[key] = (self.clock(), result)
            self.cache.move_to_end(key)
            while len(self.cache) > 16:
                self.cache.popitem(last=False)
            return {**result, "cached": False, "stale": False}


def quote(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def build_report(filters, query):
    """All SQL is generated server-side from validated periods; no caller SQL."""
    from landing_admin_api import load_core

    core = load_core()
    timestamp = lambda when: (
        "toDateTime("
        + quote(when.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"))
        + ", 'UTC')"
    )
    common = "swipies_environment = 'production' AND swipies_internal = false AND swipies_schema = '1'"
    # Explicit JSON properties, no person names or private event content.
    common = "properties." + common.replace(" AND swipies_", " AND properties.swipies_")
    interval = "toStartOfHour" if filters.group == "hour" else "toStartOfDay"
    branches = [
        f"SELECT event,timestamp,distinct_id,uuid,properties,{quote(name)} AS period FROM events WHERE {common} AND timestamp >= {timestamp(window.start)} AND timestamp < {timestamp(window.end)}"
        for name, window in (
            ("current", filters.current),
            ("previous", filters.previous),
        )
    ]
    shared = "WITH base AS (" + " UNION ALL ".join(branches) + ") "
    summary = query(
        shared
        + "SELECT period, uniqExactIf(distinct_id,event='$pageview' AND properties.site_area='landing'), uniqExactIf(toString(properties.$session_id),event='$pageview' AND properties.site_area='landing' AND notEmpty(toString(properties.$session_id))), countIf(event='$pageview' AND properties.site_area='landing'), uniqExactIf(uuid,event='registration_completed'), uniqExactIf(uuid,event='payment_completed') FROM base GROUP BY period"
    )
    timeline = query(
        shared
        + f"SELECT period, toUnixTimestamp({interval}(toTimeZone(timestamp,{quote(filters.zone.key)}))) AS bucket, uniqExactIf(distinct_id,event='$pageview' AND properties.site_area='landing'), countIf(event='$pageview' AND properties.site_area='landing'), uniqExactIf(uuid,event='registration_completed'), uniqExactIf(uuid,event='payment_completed') FROM base GROUP BY period,bucket ORDER BY bucket LIMIT 18000"
    )
    ctas = query(
        shared
        + "SELECT period, properties.cta_id, uniqExact(distinct_id), count() FROM base WHERE event='cta_click' GROUP BY period,properties.cta_id ORDER BY count() DESC LIMIT 100"
    )
    acquisition = query(
        shared
        + "SELECT period, properties.utm_source, properties.utm_campaign, properties.referrer_origin, uniqExact(distinct_id), count() FROM base WHERE event='$pageview' AND properties.site_area='landing' GROUP BY period,properties.utm_source,properties.utm_campaign,properties.referrer_origin ORDER BY count() DESC LIMIT 100"
    )
    devices = query(
        shared
        + "SELECT period, properties.device_type, uniqExact(distinct_id), count() FROM base WHERE event='$pageview' AND properties.site_area='landing' GROUP BY period,properties.device_type ORDER BY count() DESC LIMIT 30"
    )
    funnel = []
    for name, window in (("current", filters.current), ("previous", filters.previous)):
        scoped = f"SELECT distinct_id,timestamp,event FROM events WHERE {common} AND timestamp >= {timestamp(window.start)} AND timestamp < {timestamp(window.end)} AND (event NOT IN ('$pageview','cta_click') OR properties.site_area='landing')"
        rows = query(
            "WITH b AS ("
            + scoped
            + "), l AS (SELECT distinct_id,min(timestamp) t1 FROM b WHERE event='$pageview' GROUP BY distinct_id), c AS (SELECT l.distinct_id,l.t1,min(b.timestamp) t2 FROM l INNER JOIN b ON b.distinct_id=l.distinct_id WHERE b.event='cta_click' AND b.timestamp>=l.t1 AND b.timestamp<=l.t1+INTERVAL 7 DAY GROUP BY l.distinct_id,l.t1), r AS (SELECT c.distinct_id,c.t1,min(b.timestamp) t3 FROM c INNER JOIN b ON b.distinct_id=c.distinct_id WHERE b.event='registration_completed' AND b.timestamp>=c.t2 AND b.timestamp<=c.t1+INTERVAL 7 DAY GROUP BY c.distinct_id,c.t1), p AS (SELECT r.distinct_id,min(b.timestamp) t4 FROM r INNER JOIN b ON b.distinct_id=r.distinct_id WHERE b.event='payment_completed' AND b.timestamp>=r.t3 AND b.timestamp<=r.t1+INTERVAL 7 DAY GROUP BY r.distinct_id) SELECT (SELECT count() FROM l),(SELECT count() FROM c),(SELECT count() FROM r),(SELECT count() FROM p)"
        )
        if len(rows) != 1 or len(rows[0]) != 4:
            raise ProviderError("PostHog не вернул полную воронку.")
        funnel.append((name, [int(value) for value in rows[0]]))
    totals = {
        name: dict.fromkeys(
            ("visitors", "sessions", "pageviews", "registrations", "payments"), 0
        )
        for name in ("current", "previous")
    }
    for row in summary:
        if len(row) != 6 or row[0] not in totals:
            raise ProviderError("PostHog вернул неверные итоги.")
        totals[row[0]] = dict(zip(totals[row[0]], (int(value) for value in row[1:])))
    funnels = {}
    for name, values in funnel:
        if any(value < 0 for value in values) or any(
            b > a for a, b in pairwise(values)
        ):
            raise ProviderError("PostHog вернул несогласованную воронку.")
        funnels[name] = [
            {
                "stage": stage,
                "visitors": value,
                "lost": values[index - 1] - value if index else None,
                "from_previous_percent": round(value / values[index - 1] * 100, 2)
                if index and values[index - 1]
                else None,
            }
            for index, (stage, value) in enumerate(
                zip(("Лендинг", "CTA", "Регистрация", "Оплата"), values)
            )
        ]
        for key, index in (("registration_conversion", 2), ("payment_conversion", 3)):
            totals[name][key] = (
                round(values[index] / values[0] * 100, 2) if values[0] else None
            )
    indexed = {}
    for row in timeline:
        if len(row) != 6 or row[0] not in totals:
            raise ProviderError("PostHog вернул неверный временной ряд.")
        key = (row[0], int(row[1]))
        if key in indexed:
            raise ProviderError("PostHog вернул повторяющиеся временные группы.")
        indexed[key] = [int(value) for value in row[2:]]
    timeline = []
    for name, window in (("current", filters.current), ("previous", filters.previous)):
        for bucket in core.buckets(window, filters):
            # A missing group in a complete aggregation is an observed zero.
            # Provider errors/truncation never reach this point or become zeros.
            key = (name, int(core.instant(bucket["label"]).timestamp()))
            timeline.append([name, bucket["label"], *indexed.pop(key, [0, 0, 0, 0])])
    if indexed:
        raise ProviderError("PostHog вернул временные группы вне выбранных периодов.")
    metrics = [
        {
            "key": key,
            "current": value,
            "previous": totals["previous"][key],
            "change": core.delta(
                value,
                totals["previous"][key],
                "percent" if key.endswith("conversion") else "number",
            ),
        }
        for key, value in totals["current"].items()
    ]
    return {
        "filters": filters.metadata(),
        "totals": totals,
        "metrics": metrics,
        "funnel": funnels,
        "timeline": timeline,
        "ctas": ctas,
        "acquisition": acquisition,
        "devices": devices,
        "definitions": DEFINITIONS,
        "updated_at": core.iso(datetime.now(UTC)),
        "empty": all(not total["pageviews"] for total in totals.values()),
        "breakdowns_limit": "Топ-списки могут не включать редкие значения; пропуск не означает ноль.",
    }


def register_posthog(
    app,
    database,
    *,
    admin_required,
    platform_reader,
    admin_identity,
    client_ip=None,
    config=None,
    transport=None,
    start_collector=True,
):
    config = config or Config.read()
    provider = PostHog(config, transport)
    from landing_admin_api import load_core

    core = load_core()
    assets = Path(__file__).resolve().parent
    collector = None
    consent_limits = OrderedDict()
    consent_lock = threading.Lock()
    if config.capture_ready:
        try:
            from landing_posthog_collector import Collector

            collector = Collector(config, database, transport=transport)
        except Exception:  # noqa: BLE001 -- optional module must not block the site.
            app.logger.warning(
                "PostHog collector unavailable; existing services remain enabled"
            )

    @app.after_request
    def private_posthog_headers(response):
        if request.path.startswith(
            ("/api/admin/posthog/", "/api/posthog/", "/admin/posthog")
        ):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/admin/posthog")
    @app.get("/admin/posthog/")
    def posthog_page():
        token = request.cookies.get("swipies_posthog_admin", "")
        if (
            not token
            or len(token) > 8192
            or not admin_identity(
                SimpleNamespace(headers={"Authorization": "Bearer " + token})
            )
        ):
            return redirect("/admin.html")
        return send_file(assets / "posthog.html")

    @app.post("/api/admin/posthog/open")
    @admin_required
    def posthog_open():
        raw = request.headers.get("Authorization", "")
        token = (
            raw.split(" ", 1)[1]
            if raw.startswith(("Bearer ", "Token "))
            else request.headers.get("X-Admin-Token", "")
        ).strip()
        if not token or len(token) > 8192:
            return jsonify(code=1, message="Invalid administrator session"), 401
        response = jsonify(code=0)
        response.set_cookie(
            "swipies_posthog_admin",
            token,
            max_age=300,
            secure=True,
            httponly=True,
            samesite="Strict",
            path="/admin/posthog",
        )
        return response

    @app.get("/api/posthog/config")
    def posthog_config():
        internal = False
        try:
            address = ipaddress.ip_address(
                client_ip() if client_ip else request.remote_addr
            )
            internal = any(address in network for network in config.internal_cidrs)
        except ValueError:
            pass
        result = {
            "enabled": config.capture_ready and collector is not None and not internal,
            "internal": internal,
        }
        if result["enabled"]:
            result.update(
                project_token=config.project_token,
                project_id=config.project_id,
                api_host=config.ingest_host,
                asset_host=config.asset_host,
                allowed_hosts=["swipies.app", "www.swipies.app", "api.swipies.app"],
                environment="production",
            )
        response = jsonify(result)
        if request.headers.get("Origin") in (
            "https://swipies.app",
            "https://www.swipies.app",
            "https://api.swipies.app",
        ):
            response.headers["Access-Control-Allow-Origin"] = request.headers["Origin"]
            response.headers["Vary"] = "Origin"
        return response

    @app.route("/api/posthog/consent", methods=["POST", "OPTIONS"])
    def posthog_consent():
        allowed = request.headers.get("Origin") in (
            "https://swipies.app",
            "https://www.swipies.app",
            "https://api.swipies.app",
        )
        if not allowed:
            return jsonify(code=1, message="Origin not allowed"), 403
        if request.method == "OPTIONS" or not collector:
            response = app.response_class(status=204)
        else:
            address = client_ip() if client_ip else request.remote_addr
            now = time.monotonic()
            with consent_lock:
                count, at = consent_limits.get(address, (0, now))
                if now - at >= 60:
                    count, at = 0, now
                consent_limits[address] = (count + 1, at)
                consent_limits.move_to_end(address)
                while len(consent_limits) > 2000:
                    consent_limits.popitem(last=False)
            if count >= 30:
                return jsonify(code=1, message="Too many consent requests"), 429
            if not request.is_json or (request.content_length or 0) > 512:
                return jsonify(code=1, message="Invalid consent receipt"), 400
            try:
                raw = request.stream.read(513)
                if len(raw) > 512:
                    raise ValueError("Body too large")
                data = json.loads(raw)
            except (ValueError, UnicodeError):
                return jsonify(code=1, message="Invalid consent receipt"), 400
            if (
                not isinstance(data, dict)
                or set(data) != {"visitor_id", "granted"}
                or not isinstance(data["granted"], bool)
                or not isinstance(data["visitor_id"], str)
            ):
                return jsonify(code=1, message="Invalid consent receipt"), 400
            if data["visitor_id"] in config.internal_visitors:
                return jsonify(code=1, message="Internal traffic excluded"), 403
            try:
                collector.state.consent(data["visitor_id"], data["granted"])
            except ValueError:
                return jsonify(code=1, message="Invalid anonymous identity"), 400
            response = jsonify(code=0)
        response.headers["Access-Control-Allow-Origin"] = request.headers["Origin"]
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Vary"] = "Origin"
        return response

    @app.get("/api/admin/posthog/status")
    @admin_required
    def posthog_status():
        return jsonify(
            code=0,
            data={
                **config.status(),
                "collector": {**collector.state.status(), "error": collector.error}
                if collector
                else None,
            },
        )

    @app.post("/api/admin/posthog/report")
    @admin_required
    def posthog_report():
        if not config.reports_ready:
            return jsonify(code=0, data={"state": "setup", **config.status()})
        if not request.is_json or (request.content_length or 0) > 16384:
            return jsonify(code=1, message="Нужен JSON-запрос не более 16 KiB."), 400
        try:
            raw = request.stream.read(16385)
            if len(raw) > 16384:
                raise ValueError("Body too large")
            data = json.loads(raw)
            filters = core.Filters.parse(data.get("filters", {}))
            if filters.group not in {"hour", "day"}:
                raise ValueError("Invalid grouping for PostHog")
            if filters.source or filters.campaign:
                raise ValueError(
                    "На этой странице поддерживаются только фильтры периода и часового пояса."
                )
            report = provider.report(filters)
            comparison = {}
            try:
                facts = platform_reader(
                    "/api/v1/admin/analytics/periods?"
                    + urlencode({**filters.metadata(), "comparison": "custom"})
                )
            except Exception:  # noqa: BLE001 -- system comparison is optional.
                facts = None
            for name, window in (
                ("current", filters.current),
                ("previous", filters.previous),
            ):
                try:
                    if facts is None:
                        raise ValueError("System facts unavailable")
                    count = facts[name]["totals"].get("new_users")
                    comparison[name] = {
                        "registrations": {
                            "posthog": report["totals"][name]["registrations"],
                            "system": count,
                            "difference": report["totals"][name]["registrations"]
                            - count
                            if count is not None
                            else None,
                            "definition": "Созданные аккаунты по create_time, без изменения источника данных.",
                        },
                        "payments": {
                            "posthog": report["totals"][name]["payments"],
                            "system": None,
                            "difference": None,
                            "unavailable": "Существующий отчёт считает PAID по дате создания записи. Время подтверждения оплаты в нём не гарантировано, поэтому события оплаты за период напрямую не сопоставимы.",
                        },
                    }
                except (KeyError, TypeError, ValueError):
                    comparison[name] = {
                        "unavailable": "Данные системы недоступны. Значения не подменены нулями."
                    }
            return jsonify(
                code=0,
                data={
                    **report,
                    "state": "ready",
                    "comparison": comparison,
                    "comparison_notes": [
                        "Блокировщики и отсутствие согласия исключают часть посетителей из PostHog.",
                        "Доставка событий и обработка PostHog могут запаздывать.",
                        "Разные идентификаторы, события и правила датирования дают расхождения.",
                        "Новая интеграция не содержит событий до её включения; исторические значения не дорисовываются.",
                    ],
                },
            )
        except (ValueError, TypeError, AttributeError):
            return jsonify(code=1, message="Проверьте даты и часовой пояс."), 400
        except ProviderError as error:
            response = jsonify(
                code=1, message=str(error), retry_after=error.retry_after
            )
            response.status_code = 503
            response.headers["Retry-After"] = str(error.retry_after)
            return response
        except Exception:  # noqa: BLE001 -- keep provider details and secrets private.
            return jsonify(code=1, message="Отчёт PostHog временно недоступен."), 503

    if collector:
        if start_collector:
            threading.Thread(
                target=collector.run, daemon=True, name="posthog-outbox"
            ).start()
        app.extensions["swipies_posthog_collector"] = collector
    app.extensions["swipies_posthog"] = provider
