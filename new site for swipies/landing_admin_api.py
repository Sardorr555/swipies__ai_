"""Authenticated comparison/export routes for the separate landing Flask API."""

import importlib.util
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import threading
import time
from urllib.parse import urlencode

from flask import Response, jsonify, request


def load_core():
    folder = Path(__file__).resolve().parent
    candidates = [
        folder / "analytics_reporting.py",
        folder.parent / "api/analytics_reporting.py",
    ]
    for path in candidates:
        if path.is_file():
            import sys

            spec = importlib.util.spec_from_file_location(
                "swipies_landing_reporting_core", path
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module
    raise RuntimeError("Deploy analytics_reporting.py next to the landing API")


def upstream(path, authorization="", method="GET", body=None):
    import requests

    # Fixed platform origin; client input never selects a host or redirects.
    response = requests.request(
        method,
        "https://api.swipies.app" + path,
        headers={
            "Authorization": authorization,
            "User-Agent": "SwipiesLandingAdmin/1.0",
        },
        json=body,
        timeout=(5, 25),
        allow_redirects=False,
    )
    data = (
        response.json()
        if "application/json" in response.headers.get("Content-Type", "")
        else {}
    )
    return response.status_code, data, response.headers


def register_admin_analytics(
    app,
    database,
    platform_request=upstream,
    *,
    landing_authorizer=None,
    platform_reader=None,
    provider_defaults=None,
):
    core = load_core()
    recent = {}
    lock = threading.Lock()

    original_platform_request = platform_request

    def platform_request(path, authorization="", method="GET", body=None):
        if (
            platform_reader is not None
            and landing_authorizer is not None
            and method == "GET"
            and path.startswith(
                ("/api/v1/admin/analytics/periods?", "/api/v1/admin/analytics/users?")
            )
            and landing_authorizer(request)
        ):
            return 200, {"code": 0, "data": platform_reader(path)}, {}
        return original_platform_request(path, authorization, method=method, body=body)

    def body():
        if request.mimetype != "application/json" or (
            request.content_length and request.content_length > 1024 * 1024
        ):
            raise ValueError("Нужен JSON-запрос не более 1 MiB.")
        raw = request.stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("Запрос превышает 1 MiB.")
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError):
            raise ValueError("Некорректный JSON-запрос.") from None
        if not isinstance(value, dict):
            raise ValueError("Нужен объект параметров.")
        return value

    @app.after_request
    def private_analytics_response(response):
        if request.path.startswith("/api/admin/analytics/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def authorize():
        token = request.headers.get("Authorization", "")
        if not token.startswith("Bearer ") or len(token) > 8192:
            raise PermissionError("Войдите под суперпользователем платформы.")
        if landing_authorizer is not None and landing_authorizer(request):
            return token, {"landing_admin": True}
        status, result, _ = platform_request("/api/v1/users/me", token)
        user = result.get("data") if isinstance(result, dict) else None
        if status != 200 or result.get("code") != 0 or not isinstance(user, dict):
            raise PermissionError("Сессия недействительна. Войдите заново.")
        if user.get("is_superuser") not in (True, 1, "1"):
            raise PermissionError("Нужны права суперпользователя.")
        return token, user

    def limit():
        # Bounded per-address expensive reports/exports; no credential in keys.
        address = request.remote_addr or "unknown"
        now = time.monotonic()
        with lock:
            for key in list(recent):
                if now - recent[key][0] >= 60:
                    del recent[key]
            if address not in recent:
                if len(recent) >= 2000:
                    raise ValueError("Сервис занят. Повторите через минуту.")
                recent[address] = [now, 0]
            recent[address][1] += 1
            if recent[address][1] > 120:
                raise ValueError("Слишком много запросов. Повторите через минуту.")

    def rows(table, filters, window=None, search="", maximum=core.MAX_RECORDS):
        campaigns_only = table == "campaigns"
        if campaigns_only:
            table = "visitors"
        if table not in {"visitors", "leads"}:
            raise ValueError("Неизвестная таблица.")
        if table == "leads" and (filters.source or filters.campaign):
            raise ValueError(
                "У заявок нет UTM-атрибуции. Снимите фильтр источника/кампании."
            )
        # SQLite julianday handles historical ISO timestamps with/without Z and
        # offsets consistently; textual date comparison would miss boundaries.
        windows = [window] if window else [filters.current, filters.previous]
        clauses = [
            "("
            + " OR ".join(
                "(julianday(create_date) >= julianday(?) AND julianday(create_date) < julianday(?))"
                for _ in windows
            )
            + ")"
        ]
        parameters = [
            value
            for item in windows
            for value in (core.iso(item.start), core.iso(item.end))
        ]
        if campaigns_only:
            clauses.append(
                "(coalesce(utm_source,'') != '' OR coalesce(utm_medium,'') != '' OR coalesce(utm_campaign,'') != '')"
            )
        if table == "visitors":
            for field, value in [
                ("utm_source", filters.source),
                ("utm_campaign", filters.campaign),
            ]:
                if value:
                    clauses.append(f"casefold(coalesce({field}, '')) = casefold(?)")
                    parameters.append(value)
        if table == "leads":
            clauses.append("coalesce(status, '1') != '0'")
        if search:
            if len(search) > 200:
                raise ValueError("Поисковый запрос слишком длинный.")
            fields = (
                [
                    "ip",
                    "country",
                    "city",
                    "utm_source",
                    "utm_campaign",
                    "page_url",
                    "visitor_id",
                ]
                if table == "visitors"
                else ["name", "company", "email", "phone", "message", "referral_code"]
            )
            escaped = (
                search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            clauses.append(
                "("
                + " OR ".join(
                    f"casefold(coalesce({field}, '')) LIKE ? ESCAPE '\\'"
                    for field in fields
                )
                + ")"
            )
            parameters.extend(["%" + escaped.casefold() + "%"] * len(fields))
        with closing(
            sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
        ) as connection:
            connection.create_function(
                "casefold",
                1,
                lambda value: str(value or "").casefold(),
                deterministic=True,
            )
            connection.row_factory = sqlite3.Row
            selected = [
                dict(row)
                for row in connection.execute(
                    f"SELECT * FROM {table} WHERE {' AND '.join(clauses)} ORDER BY create_date DESC, id DESC LIMIT ?",
                    [*parameters, maximum + 1],
                )
            ]
        if len(selected) > maximum:
            raise ValueError(
                f"Более {maximum:,} записей. Сократите период или уточните поиск."
            )
        return selected

    def build(data, token):
        filters = core.Filters.parse(data.get("filters", {}))
        selected_source = data.get("source", "landing")
        visitors = rows("visitors", filters)
        leads = (
            rows("leads", filters) if not (filters.source or filters.campaign) else []
        )
        current = core.traffic_period(filters.current, filters, visitors, leads)
        previous = core.traffic_period(filters.previous, filters, visitors, leads)
        notes = [
            "Показаны только фактические данные. Начало периода включено, конец исключён.",
            "Проценты конверсий — отношение событий за период, а не когортная аналитика. Уникальные посетители за период не суммируются по временным группам.",
        ]
        if selected_source != "landing":
            try:
                from landing_analytics_providers import provider_periods

                credentials = data.get("credentials") or {}
                if not isinstance(credentials, dict):
                    raise ValueError("Некорректные настройки источника аналитики.")
                defaults = (
                    provider_defaults(selected_source) if provider_defaults else {}
                )
                credentials = {
                    **defaults,
                    **{key: value for key, value in credentials.items() if value},
                }
                provider_current, provider_previous, provider_notes = provider_periods(
                    selected_source, credentials, filters, core
                )
                # Keep independently measured landing leads/consent/scroll; all
                # traffic metrics now come from the selected provider.
                traffic_keys = {
                    key for key, _, _, owner in core.METRICS if owner == "traffic"
                }
                for target, incoming in [
                    (current, provider_current),
                    (previous, provider_previous),
                ]:
                    for key in traffic_keys:
                        target["totals"].pop(key, None)
                        target["unavailable"].pop(key, None)
                        for bucket in target["buckets"]:
                            bucket["values"].pop(key, None)
                    core.merge_period(target, incoming)
                    target["breakdowns"] = incoming["breakdowns"]
                    for values in [
                        target["totals"],
                        *[bucket["values"] for bucket in target["buckets"]],
                    ]:
                        values["lead_rate"] = (
                            round(values["leads"] / values["visits"] * 100, 2)
                            if values.get("visits") and values.get("leads") is not None
                            else None
                        )
                notes.extend(provider_notes)
            except ImportError:
                raise ValueError(
                    "Не установлен модуль аналитики GA4 / Яндекс.Метрики."
                ) from None
        params = {**filters.metadata(), "comparison": "custom"}
        try:
            status, result, _ = platform_request(
                "/api/v1/admin/analytics/periods?" + urlencode(params), token
            )
            platform = result.get("data") if isinstance(result, dict) else None
            if (
                status != 200
                or result.get("code") != 0
                or not isinstance(platform, dict)
            ):
                raise ValueError("Для регистраций и платежей обновите API платформы.")
            core.merge_period(current, platform["current"])
            core.merge_period(previous, platform["previous"])
            notes.extend(platform.get("notes", []))
        except Exception:
            for key, _, _, owner in core.METRICS:
                if owner == "platform":
                    current["unavailable"][key] = previous["unavailable"][key] = (
                        "Данные платформы недоступны. Проверьте подключение и версию API."
                    )
            notes.append(
                "Регистрации и платежи недоступны: они не подменены нулями или данными веб-аналитики."
            )
        return core.assemble(filters, current, previous, selected_source, notes)

    def failure(error):
        if isinstance(error, PermissionError):
            status = 401 if not request.headers.get("Authorization") else 403
            return jsonify(code=1, message=str(error)), status
        if isinstance(error, ValueError):
            return jsonify(code=1, message=str(error)), 400
        return jsonify(
            code=1,
            message="Данные недоступны. Проверьте сервис аналитики и подключение к платформе.",
        ), 503

    @app.post("/api/admin/analytics/login")
    def admin_analytics_login():
        try:
            limit()
            data = body()
            email, password = data.get("email"), data.get("password")
            if (
                not isinstance(email, str)
                or not isinstance(password, str)
                or len(email) > 255
                or len(password) > 8192
            ):
                raise ValueError("Укажите email и пароль платформы.")
            status, result, headers = platform_request(
                "/api/v1/auth/login",
                method="POST",
                body={"email": email, "password": password},
            )
            if (
                status == 200
                and result.get("code") == 0
                and isinstance(result.get("data"), dict)
                and (
                    result["data"].get("requires_2fa")
                    or result["data"].get("requires_activation")
                )
            ):
                return jsonify(code=0, data={"requires_2fa": True, "email": email})
            token = headers.get("Authorization", "")
            if not token.lower().startswith("bearer ") and token:
                token = "Bearer " + token
            if status != 200 or result.get("code") != 0 or not token:
                raise PermissionError("Неверные данные для входа.")
            profile_status, profile, _ = platform_request("/api/v1/users/me", token)
            if (
                profile_status != 200
                or profile.get("code") != 0
                or profile.get("data", {}).get("is_superuser") not in (True, 1, "1")
            ):
                raise PermissionError("Нужен аккаунт суперпользователя платформы.")
            response = jsonify(code=0, data={"authorization": token})
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as error:
            return failure(error)

    @app.post("/api/admin/analytics/verify")
    def admin_analytics_verify():
        try:
            limit()
            data = body()
            email, code = data.get("email"), data.get("code")
            if (
                not isinstance(email, str)
                or len(email) > 255
                or not isinstance(code, str)
                or len(code) != 6
                or not code.isdigit()
            ):
                raise ValueError("Укажите email и шестизначный код из письма.")
            status, result, headers = platform_request(
                "/api/v1/auth/activate",
                method="POST",
                body={"email": email, "code": code},
            )
            token = headers.get("Authorization", "")
            if token and not token.lower().startswith("bearer "):
                token = "Bearer " + token
            if status != 200 or result.get("code") != 0 or not token:
                raise PermissionError("Код недействителен или истёк. Повторите вход.")
            profile_status, profile, _ = platform_request("/api/v1/users/me", token)
            if (
                profile_status != 200
                or profile.get("code") != 0
                or profile.get("data", {}).get("is_superuser") not in (True, 1, "1")
            ):
                raise PermissionError("Нужен аккаунт суперпользователя платформы.")
            return jsonify(code=0, data={"authorization": token})
        except Exception as error:
            return failure(error)

    @app.post("/api/admin/analytics/report")
    def admin_analytics_report():
        try:
            token, _ = authorize()
            limit()
            response = jsonify(code=0, data=build(body(), token))
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as error:
            return failure(error)

    @app.post("/api/admin/analytics/records")
    def admin_analytics_records():
        try:
            token, _ = authorize()
            limit()
            data = body()
            filters = core.Filters.parse(data.get("filters", {}))
            table = data.get("table", "visitors")
            if table == "users":
                parameters = {
                    **filters.metadata(),
                    "comparison": "custom",
                    "search": str(data.get("search", "")),
                    "page": int(data.get("page", 1)),
                }
                status, result, _ = platform_request(
                    "/api/v1/admin/analytics/users?" + urlencode(parameters), token
                )
                if status != 200 or result.get("code") != 0:
                    raise ValueError(
                        "Обновите API платформы для списка пользователей с фильтрами."
                    )
                return jsonify(code=0, **result["data"])
            selected = rows(
                table, filters, filters.current, str(data.get("search", ""))
            )
            page = max(1, int(data.get("page", 1)))
            response = jsonify(
                code=0,
                data=selected[(page - 1) * 100 : page * 100],
                total=len(selected),
                page=page,
                page_size=100,
            )
            response.headers["Cache-Control"] = "no-store"
            return response
        except Exception as error:
            return failure(error)

    @app.post("/api/admin/analytics/export")
    def admin_analytics_export():
        try:
            token, _ = authorize()
            limit()
            data = body()
            filters = core.Filters.parse(data.get("filters", {}))
            kind, format_ = data.get("kind", "report"), data.get("format", "xlsx")
            if kind == "report":
                report = build(data, token)
                sheets = core.report_sheets(report)
            elif kind in {"visitors", "campaigns", "leads"}:
                selected = rows(
                    kind,
                    filters,
                    filters.current,
                    str(data.get("search", "")),
                    core.MAX_EXPORT,
                )
                columns = (
                    [
                        "id",
                        "visitor_id",
                        "ip",
                        "country",
                        "city",
                        "device_type",
                        "browser",
                        "language",
                        "session_duration",
                        "scroll_depth",
                        "utm_source",
                        "utm_medium",
                        "utm_campaign",
                        "cookie_consent",
                        "page_url",
                        "referrer",
                        "create_date",
                    ]
                    if kind in {"visitors", "campaigns"}
                    else [
                        "id",
                        "name",
                        "company",
                        "email",
                        "phone",
                        "message",
                        "status",
                        "referral_code",
                        "create_date",
                    ]
                )
                report = core.assemble(
                    filters,
                    core.blank_period(filters.current, filters),
                    core.blank_period(filters.previous, filters),
                    kind,
                )
                sheets = [
                    ("Параметры", core.report_sheets(report)[0][1]),
                    (
                        "Записи",
                        [
                            columns,
                            *[
                                [row.get(column) for column in columns]
                                for row in selected
                            ],
                        ],
                    ),
                ]
            elif kind == "users":
                selected = []
                for page in range(1, core.MAX_EXPORT // 100 + 2):
                    parameters = {
                        **filters.metadata(),
                        "comparison": "custom",
                        "search": str(data.get("search", "")),
                        "page": page,
                    }
                    status, result, _ = platform_request(
                        "/api/v1/admin/analytics/users?" + urlencode(parameters), token
                    )
                    if status != 200 or result.get("code") != 0:
                        raise ValueError(
                            "Не удалось выгрузить пользователей платформы."
                        )
                    content = result["data"]
                    if content["total"] > core.MAX_EXPORT:
                        raise ValueError(
                            "Более 50 000 пользователей. Сократите период."
                        )
                    selected.extend(content["data"])
                    if len(selected) >= content["total"]:
                        break
                columns = [
                    "id",
                    "email",
                    "nickname",
                    "create_date",
                    "status",
                    "utm_source",
                    "utm_campaign",
                    "referred_by_id",
                ]
                report = core.assemble(
                    filters,
                    core.blank_period(filters.current, filters),
                    core.blank_period(filters.previous, filters),
                    kind,
                )
                sheets = [
                    ("Параметры", core.report_sheets(report)[0][1]),
                    (
                        "Записи",
                        [
                            columns,
                            *[
                                [row.get(column) for column in columns]
                                for row in selected
                            ],
                        ],
                    ),
                ]
            else:
                raise ValueError("Неизвестный тип отчёта.")
            sheets[0][1].extend(
                [
                    ["kind", kind],
                    ["search", str(data.get("search", "")) if kind != "report" else ""],
                ]
            )
            if format_ == "xlsx":
                output, mime = (
                    core.xlsx_bytes(sheets),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            elif format_ == "csv":
                keys = [
                    "start",
                    "end",
                    "compare_start",
                    "compare_end",
                    "timezone",
                    "group",
                    "utm_source",
                    "utm_campaign",
                ]
                metadata = {
                    **filters.metadata(),
                    "search": str(data.get("search", "")) if kind != "report" else "",
                    "kind": kind,
                }
                keys.extend(["search", "kind"])
                values = [metadata[key] for key in keys]
                records = sheets[1][1]
                output, mime = (
                    core.csv_bytes(
                        [records[0] + keys, *[row + values for row in records[1:]]]
                    ),
                    "text/csv; charset=utf-8",
                )
            else:
                raise ValueError("Выберите XLSX или CSV.")
            name = f"swipies_{kind}_{filters.current.start:%Y-%m-%d_%H}-{filters.current.end:%Y-%m-%d_%H}.{format_}"
            return Response(
                output,
                mimetype=mime,
                headers={
                    "Content-Disposition": f'attachment; filename="{name}"',
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )
        except Exception as error:
            return failure(error)
