"""Native GA4/Metrika reports. Totals are queried, never summed from unique-user buckets."""

from datetime import datetime, timedelta
import json
from math import isfinite


def number(value):
    result = float(value)
    if not isfinite(result):
        raise ValueError("Источник аналитики вернул некорректное число.")
    return result


def _filter(filters, window, provider):
    local_start, local_end = (
        window.start.astimezone(filters.zone),
        window.end.astimezone(filters.zone),
    )
    if provider == "ga":
        conditions = [
            {
                "filter": {
                    "fieldName": "dateHour",
                    "numericFilter": {
                        "operation": "GREATER_THAN_OR_EQUAL",
                        "value": {"int64Value": local_start.strftime("%Y%m%d%H")},
                    },
                }
            },
            {
                "filter": {
                    "fieldName": "dateHour",
                    "numericFilter": {
                        "operation": "LESS_THAN",
                        "value": {"int64Value": local_end.strftime("%Y%m%d%H")},
                    },
                }
            },
        ]
        for key, value in [
            ("sessionSource", filters.source),
            ("sessionCampaignName", filters.campaign),
        ]:
            if value:
                conditions.append(
                    {
                        "filter": {
                            "fieldName": key,
                            "stringFilter": {
                                "matchType": "EXACT",
                                "value": value,
                                "caseSensitive": False,
                            },
                        }
                    }
                )
        return {"andGroup": {"expressions": conditions}}

    def quoted(value):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

    conditions = [
        "ym:s:dateTime>=" + quoted(local_start.strftime("%Y-%m-%d %H:%M:%S")),
        "ym:s:dateTime<" + quoted(local_end.strftime("%Y-%m-%d %H:%M:%S")),
    ]
    for key, value in [
        ("ym:s:UTMSource", filters.source),
        ("ym:s:UTMCampaign", filters.campaign),
    ]:
        if value:
            conditions.append(key + "==" + quoted(value))
    return " AND ".join(conditions)


def _native_index(period, filters):
    result = {}
    for index, bucket in enumerate(period["buckets"]):
        point = datetime.fromisoformat(bucket["label"])
        key = point.strftime(
            {"hour": "%Y%m%d%H", "day": "%Y%m%d", "month": "%Y%m"}.get(
                filters.group, "%Y%m%d"
            )
        )
        if filters.group == "week":
            year, week, _ = point.isocalendar()
            key = f"{year}{week:02d}"
        if key in result:
            raise ValueError(
                "В этом периоде повторяется час при переходе времени. Для внешней аналитики выберите шаг «День»."
            )
        result[key] = index
    return result


def provider_periods(source, credentials, filters, core):
    if source == "ga":
        return google_periods(credentials, filters, core)
    if source == "ym":
        return yandex_periods(credentials, filters, core)
    raise ValueError("Неизвестный источник аналитики.")


def google_periods(credentials, filters, core):
    import requests

    property_id = str(credentials.get("property_id", "")).strip()
    if not property_id.isdigit() or not 1 <= len(property_id) <= 20:
        raise ValueError("В настройках укажите числовой GA4 Property ID.")
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        info = credentials.get("service_account_key", "")
        if isinstance(info, str):
            info = json.loads(info)
        identity = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
        )
        identity.refresh(Request())
    except Exception:
        raise ValueError(
            "Проверьте ключ сервисного аккаунта GA4 в настройках."
        ) from None
    headers = {"Authorization": "Bearer " + identity.token}
    notes = []
    native = {
        "hour": "dateHour",
        "day": "date",
        "week": "isoYearIsoWeek",
        "month": "yearMonth",
    }[filters.group]
    metric_names = [
        "totalUsers",
        "sessions",
        "screenPageViews",
        "bounceRate",
        "averageSessionDuration",
        "keyEvents",
    ]

    def fetch(window):
        period = core.blank_period(window, filters)
        indexed = _native_index(period, filters)
        common = {
            "dateRanges": [
                {
                    "startDate": window.start.astimezone(filters.zone).strftime(
                        "%Y-%m-%d"
                    ),
                    "endDate": (window.end - timedelta(microseconds=1))
                    .astimezone(filters.zone)
                    .strftime("%Y-%m-%d"),
                }
            ],
            "dimensionFilter": _filter(filters, window, "ga"),
            "keepEmptyRows": True,
        }
        report = lambda dimensions, metrics, limit=50000: {
            **common,
            "dimensions": [{"name": item} for item in dimensions],
            "metrics": [{"name": item} for item in metrics],
            "limit": str(limit),
        }
        events = report([native, "eventName"], ["eventCount"])
        events["dimensionFilter"] = {
            "andGroup": {
                "expressions": [
                    common["dimensionFilter"],
                    {
                        "filter": {
                            "fieldName": "eventName",
                            "inListFilter": {"values": ["demo_click", "sales_click"]},
                        }
                    },
                ]
            }
        }
        queries = [report([], metric_names), report([native], metric_names), events]
        breakdown_names = [
            "sessionDefaultChannelGroup",
            "deviceCategory",
            "language",
            "pagePath",
        ]
        queries.extend(
            report(
                [name], ["totalUsers" if name != "pagePath" else "screenPageViews"], 30
            )
            for name in breakdown_names
        )
        for query in queries[3:]:
            query["orderBys"] = [
                {"metric": {"metricName": query["metrics"][0]["name"]}, "desc": True}
            ]
        reports = []
        for offset in range(0, len(queries), 5):
            response = requests.post(
                f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:batchRunReports",
                headers=headers,
                json={"requests": queries[offset : offset + 5]},
                timeout=(5, 30),
                allow_redirects=False,
            )
            if response.status_code != 200:
                raise ValueError(
                    "GA4 не вернул отчёт. Проверьте доступ к ресурсу и совместимость фильтров."
                )
            reports.extend(response.json().get("reports", []))
        if len(reports) != len(queries):
            raise ValueError("GA4 вернул неполный набор отчётов.")
        for item in reports:
            metadata = item.get("metadata", {})
            if metadata.get("timeZone") and metadata["timeZone"] != filters.zone.key:
                raise ValueError(
                    "Часовой пояс ресурса GA4: "
                    + metadata["timeZone"]
                    + ". Выберите его в фильтре часового пояса."
                )
            if metadata.get("subjectToThresholding") or metadata.get(
                "samplingMetadatas"
            ):
                notes.append(
                    "GA4 применяет пороги конфиденциальности или семплирование; часть данных может быть недоступна."
                )
        if any(int(item.get("rowCount", 0)) > 50000 for item in reports[:3]):
            raise ValueError("Слишком много строк GA4. Увеличьте временной шаг.")

        def values(row):
            numbers = [number(item["value"]) for item in row.get("metricValues", [])]
            if len(numbers) != len(metric_names):
                raise ValueError("GA4 вернул неполные метрики.")
            return dict(
                zip(
                    [
                        "visitors",
                        "visits",
                        "views",
                        "bounce_rate",
                        "avg_duration",
                        "goals",
                    ],
                    numbers,
                )
            )

        zeros = dict.fromkeys(
            ["visitors", "visits", "views", "goals", "demo_clicks", "sales_clicks"], 0
        )
        period["totals"] = {**zeros, "bounce_rate": None, "avg_duration": None}
        if reports[0].get("rows"):
            period["totals"].update(values(reports[0]["rows"][0]))
            period["totals"]["bounce_rate"] *= 100
        for bucket in period["buckets"]:
            bucket["values"] = {**zeros, "bounce_rate": None, "avg_duration": None}
        for row in reports[1].get("rows", []):
            key = row["dimensionValues"][0]["value"]
            if key not in indexed:
                raise ValueError("GA4 вернул временную группу вне выбранного периода.")
            mapped = values(row)
            mapped["bounce_rate"] *= 100
            period["buckets"][indexed[key]]["values"].update(mapped)
        for row in reports[2].get("rows", []):
            key, event = [item["value"] for item in row["dimensionValues"]]
            if key not in indexed:
                raise ValueError("GA4 вернул событие вне выбранного периода.")
            name = {"demo_click": "demo_clicks", "sales_click": "sales_clicks"}[event]
            amount = number(row["metricValues"][0]["value"])
            period["buckets"][indexed[key]]["values"][name] += amount
            period["totals"][name] += amount
        for entry in [
            period["totals"],
            *[bucket["values"] for bucket in period["buckets"]],
        ]:
            entry["goal_rate"] = (
                entry["goals"] / entry["visits"] * 100 if entry["visits"] else None
            )
        for key, item in zip(
            ["channels", "devices", "languages", "pages"], reports[3:]
        ):
            period["breakdowns"][key] = [
                {
                    "name": row["dimensionValues"][0]["value"],
                    "value": number(row["metricValues"][0]["value"]),
                }
                for row in item.get("rows", [])
            ]
        return period

    return fetch(filters.current), fetch(filters.previous), list(dict.fromkeys(notes))


def yandex_periods(credentials, filters, core):
    import requests

    counter = str(credentials.get("counter_id", "")).strip()
    token = str(credentials.get("oauth_token", "")).strip()
    if not counter.isdigit() or not token or len(token) > 8192:
        raise ValueError(
            "Укажите ID счётчика и OAuth-токен Яндекс.Метрики в настройках."
        )
    metrics = "ym:s:users,ym:s:visits,ym:s:pageviews,ym:s:bounceRate,ym:s:avgVisitDurationSeconds,ym:s:sumGoalReachesAny"
    notes = []

    def fetch(window):
        period = core.blank_period(window, filters)
        offsets = {
            datetime.fromisoformat(bucket["label"]).utcoffset()
            for bucket in period["buckets"]
        }
        if len(offsets) > 1:
            raise ValueError(
                "Для Яндекс.Метрики при переходе летнего времени выберите UTC: API принимает фиксированный сдвиг."
            )
        expected_offset = window.start.astimezone(filters.zone).strftime("%z")
        expected_offset = expected_offset[:3] + ":" + expected_offset[3:]
        common = {
            "ids": counter,
            "metrics": metrics,
            "date1": window.start.astimezone(filters.zone).strftime("%Y-%m-%d"),
            "date2": (window.end - timedelta(microseconds=1))
            .astimezone(filters.zone)
            .strftime("%Y-%m-%d"),
            "filters": _filter(filters, window, "ym"),
            "accuracy": "full",
            "lang": "en",
            "timezone": expected_offset,
        }

        def query(endpoint="data", **extra):
            response = requests.get(
                "https://api-metrika.yandex.net/stat/v1/" + endpoint,
                headers={"Authorization": "OAuth " + token},
                params={**common, **extra},
                timeout=(5, 30),
                allow_redirects=False,
            )
            if response.status_code != 200:
                raise ValueError(
                    "Яндекс.Метрика не вернула отчёт. Проверьте счётчик, права и фильтры."
                )
            result = response.json()
            expected = window.start.astimezone(filters.zone).strftime("%z")
            expected = expected[:3] + ":" + expected[3:]
            actual = result.get("query", {}).get("timezone")
            if actual and actual != expected:
                raise ValueError(
                    "Часовой пояс счётчика Яндекс.Метрики: UTC"
                    + actual
                    + ". Выберите соответствующий пояс в фильтре."
                )
            if result.get("sampled"):
                notes.append(
                    "Яндекс.Метрика применяет семплирование; показанные числа могут быть оценкой провайдера."
                )
            return result

        summary = query()
        timeline = query("data/bytime", group=filters.group)

        def mapped(values):
            if len(values) != 6:
                raise ValueError("Яндекс.Метрика вернула неполные метрики.")
            return dict(
                zip(
                    [
                        "visitors",
                        "visits",
                        "views",
                        "bounce_rate",
                        "avg_duration",
                        "goals",
                    ],
                    [number(value) if value is not None else None for value in values],
                )
            )

        period["totals"].update(mapped(summary.get("totals", [])))
        intervals = timeline.get("time_intervals")
        series = timeline.get("data", [])
        arrays = series[0].get("metrics", []) if series else timeline.get("totals", [])
        if not isinstance(intervals, list):
            # /bytime documents metric arrays for every native calendar group;
            # some API versions omit time_intervals. Reconstruct only when the
            # exact expected length matches; never align by an arbitrary offset.
            day_start = window.start.astimezone(filters.zone).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = (window.end - timedelta(microseconds=1)).astimezone(
                filters.zone
            ).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            native_buckets = core.buckets(
                core.Window(core.instant(day_start), core.instant(day_end)), filters
            )
            intervals = [[bucket["label"], bucket["end"]] for bucket in native_buckets]
        if len(arrays) != 6 or any(
            not isinstance(items, list) or len(items) != len(intervals)
            for items in arrays
        ):
            raise ValueError(
                "Яндекс.Метрика вернула неполный временной ряд. Измените шаг или проверьте интеграцию."
            )
        indexed = _native_index(period, filters)
        assigned = set()
        for bucket in period["buckets"]:
            bucket["values"].update(
                dict.fromkeys(["visitors", "visits", "views", "goals"], 0)
            )
        for index, interval in enumerate(intervals):
            point = datetime.fromisoformat(str(interval[0]).replace(" ", "T"))
            if point.tzinfo is None:
                point = point.replace(tzinfo=filters.zone)
            key = point.strftime(
                {"hour": "%Y%m%d%H", "day": "%Y%m%d", "month": "%Y%m"}.get(
                    filters.group, "%Y%m%d"
                )
            )
            if filters.group == "week":
                year, week, _ = point.isocalendar()
                key = f"{year}{week:02d}"
            if key not in indexed:
                continue
            if key in assigned:
                raise ValueError(
                    "Яндекс.Метрика вернула повторяющиеся временные группы."
                )
            assigned.add(key)
            period["buckets"][indexed[key]]["values"].update(
                mapped([items[index] for items in arrays])
            )
        if assigned != set(indexed):
            raise ValueError(
                "Яндекс.Метрика не вернула все выбранные временные группы."
            )
        for entry in [
            period["totals"],
            *[bucket["values"] for bucket in period["buckets"]],
        ]:
            entry["goal_rate"] = (
                entry.get("goals", 0) / entry["visits"] * 100
                if entry.get("visits")
                else None
            )
        for key in ("demo_clicks", "sales_clicks"):
            period["unavailable"][key] = (
                "Для этих кликов в Метрике нужны отдельно настроенные цели; распределение не выдумывается."
            )
        for key, dimension in [
            ("channels", "ym:s:trafficSource"),
            ("devices", "ym:s:deviceCategory"),
            ("languages", "ym:s:browserLanguage"),
            ("pages", "ym:s:startURL"),
        ]:
            count_metric = "ym:s:pageviews" if key == "pages" else "ym:s:users"
            result = query(
                dimensions=dimension,
                metrics=count_metric,
                limit=30,
                sort="-" + count_metric,
            )
            period["breakdowns"][key] = [
                {"name": row["dimensions"][0]["name"], "value": row["metrics"][0]}
                for row in result.get("data", [])
            ]
        return period

    return fetch(filters.current), fetch(filters.previous), list(dict.fromkeys(notes))
