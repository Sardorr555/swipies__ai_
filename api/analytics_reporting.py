"""Bounded, timezone-aware factual comparisons for the landing admin.

Pure standard-library code; the standalone landing service can deploy this file
next to api.py. It never provisions accounts or changes financial records.
"""

from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO
from math import isfinite
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import csv
import json
import re

UTC = timezone.utc
MAX_RECORDS = 250000
MAX_EXPORT = 50000
METRICS = [
    ("visitors", "Посетители", "number", "traffic"),
    ("visits", "Сессии", "number", "traffic"),
    ("new_users", "Новые регистрации", "number", "platform"),
    ("revenue_uzs", "Выручка, UZS", "money", "platform"),
    ("paid_payments", "Успешные платежи", "number", "platform"),
    ("paying_users", "Платящие пользователи", "number", "platform"),
    ("checkouts", "Попытки оплаты", "number", "platform"),
    ("payment_rate", "Конверсия оплаты", "percent", "platform"),
    ("avg_payment_uzs", "Средний платёж, UZS", "money", "platform"),
    ("leads", "Заявки с лендинга", "number", "landing"),
    ("lead_rate", "Заявки / сессии", "percent", "landing"),
    ("views", "Просмотры страниц", "number", "traffic"),
    ("goals", "Достижения целей", "number", "traffic"),
    ("goal_rate", "Цели / сессии", "percent", "traffic"),
    ("demo_clicks", "Клики: начать работу", "number", "traffic"),
    ("sales_clicks", "Клики: отдел продаж", "number", "traffic"),
    ("avg_duration", "Средняя сессия, сек.", "seconds", "traffic"),
    ("bounce_rate", "Отказы", "percent", "traffic"),
    ("consent_rate", "Согласие на cookies", "percent", "landing"),
    ("avg_scroll", "Средняя глубина просмотра", "percent", "landing"),
]


def instant(value):
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, (int, float)):
        result = datetime.fromtimestamp(value / 1000 if value > 1e11 else value, UTC)
    else:
        result = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    return (
        result.replace(tzinfo=UTC) if result.tzinfo is None else result.astimezone(UTC)
    )


def iso(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime

    def contains(self, value):
        return self.start <= value < self.end


@dataclass(frozen=True)
class Filters:
    current: Window
    previous: Window
    zone: ZoneInfo
    group: str
    source: str = ""
    campaign: str = ""

    @classmethod
    def parse(cls, data, now=None):
        if not isinstance(data, dict):
            raise ValueError("Ожидался объект фильтров.")
        try:
            zone = ZoneInfo(str(data.get("timezone", "Asia/Tashkent")))
            start, end = instant(data["start"]), instant(data["end"])
        except (ValueError, KeyError, ZoneInfoNotFoundError, TypeError):
            raise ValueError("Проверьте даты и часовой пояс.") from None
        group = data.get("group", "day")
        if group not in {"hour", "day", "week", "month"}:
            raise ValueError("Шаг должен быть: час, день, неделя или месяц.")
        if data.get("comparison", "previous") == "custom":
            try:
                previous = Window(
                    instant(data["compare_start"]), instant(data["compare_end"])
                )
            except (KeyError, ValueError, TypeError):
                raise ValueError("Укажите обе даты периода сравнения.") from None
        elif data.get("comparison", "previous") == "previous":
            previous = Window(start - (end - start), start)
        else:
            raise ValueError("Неизвестный режим сравнения.")
        current = Window(start, end)
        now = now or datetime.now(UTC)
        for window in (current, previous):
            if window.end <= window.start or window.end - window.start > timedelta(
                days=366
            ):
                raise ValueError(
                    "Каждый период должен быть от одного часа до 366 дней."
                )
            if window.end > now + timedelta(seconds=60):
                raise ValueError(
                    "Сравнение доступно только для фактических периодов, без будущих дат."
                )
            local_start, local_end = (
                window.start.astimezone(zone),
                window.end.astimezone(zone),
            )
            if (
                local_start.minute
                or local_start.second
                or local_start.microsecond
                or local_end.minute
                or local_end.second
                or local_end.microsecond
            ):
                raise ValueError("Выберите границы по целым часам.")
        source, campaign = (
            str(data.get("utm_source", "")).strip(),
            str(data.get("utm_campaign", "")).strip(),
        )
        if max(len(source), len(campaign)) > 128:
            raise ValueError("Фильтр UTM слишком длинный.")
        return cls(current, previous, zone, group, source, campaign)

    def metadata(self):
        return {
            "start": iso(self.current.start),
            "end": iso(self.current.end),
            "compare_start": iso(self.previous.start),
            "compare_end": iso(self.previous.end),
            "timezone": self.zone.key,
            "group": self.group,
            "utm_source": self.source,
            "utm_campaign": self.campaign,
            "boundary": "start inclusive; end exclusive",
            "equal_duration": self.current.end - self.current.start
            == self.previous.end - self.previous.start,
        }


def buckets(window, filters):
    local = window.start.astimezone(filters.zone)
    point = local.replace(minute=0, second=0, microsecond=0)
    if filters.group != "hour":
        point = point.replace(hour=0)
    if filters.group == "week":
        point -= timedelta(days=point.weekday())
    if filters.group == "month":
        point = point.replace(day=1)
    result = []
    while point.astimezone(UTC) < window.end:
        if filters.group == "hour":
            following = (point.astimezone(UTC) + timedelta(hours=1)).astimezone(
                filters.zone
            )
        elif filters.group == "month":
            following = point.replace(
                year=point.year + (point.month == 12), month=point.month % 12 + 1, day=1
            )
        else:
            following = point + timedelta(days=7 if filters.group == "week" else 1)
        result.append(
            {
                "start": iso(max(point.astimezone(UTC), window.start)),
                "end": iso(min(following.astimezone(UTC), window.end)),
                "label": point.isoformat(),
                "values": {},
            }
        )
        point = following
        if len(result) > 10000:
            raise ValueError("Слишком много точек. Выберите более крупный шаг.")
    return result


def blank_period(window, filters):
    return {
        "start": iso(window.start),
        "end": iso(window.end),
        "totals": {},
        "buckets": buckets(window, filters),
        "unavailable": {},
        "breakdowns": {},
    }


def delta(current, previous, unit="number"):
    if current is None or previous is None:
        return {"absolute": None, "percent": None, "state": "unavailable"}
    absolute = round(current - previous, 6)
    percent = (
        round(absolute / abs(previous) * 100, 2)
        if previous
        else (0 if current == 0 else None)
    )
    return {
        "absolute": absolute,
        "percent": percent,
        "state": "new" if previous == 0 and current != 0 else "compared",
        "unit": "percentage_points" if unit == "percent" else unit,
    }


def assemble(filters, current, previous, source, notes=None):
    metrics = [
        {
            "key": key,
            "label": label,
            "unit": unit,
            "source": owner,
            "current": current["totals"].get(key),
            "previous": previous["totals"].get(key),
            "change": delta(
                current["totals"].get(key), previous["totals"].get(key), unit
            ),
            "reason": current["unavailable"].get(key)
            or previous["unavailable"].get(key),
        }
        for key, label, unit, owner in METRICS
    ]
    return {
        "filters": filters.metadata(),
        "current": current,
        "previous": previous,
        "metrics": metrics,
        "source": source,
        "notes": notes or [],
        "generated_at": iso(datetime.now(UTC)),
    }


def match_attribution(row, filters):
    return (
        not filters.source
        or str(row.get("utm_source") or "").casefold() == filters.source.casefold()
    ) and (
        not filters.campaign
        or str(row.get("utm_campaign") or "").casefold() == filters.campaign.casefold()
    )


def attributed(rows, filters):
    for row in rows:
        if match_attribution(row, filters):
            yield row


def timed_rows(rows, window):
    for row in rows:
        try:
            when = instant(
                row.get("timestamp") or row.get("create_date") or row.get("create_time")
            )
        except (TypeError, ValueError, OverflowError):
            continue
        if window.contains(when):
            yield row, when


def _safe_number(value):
    try:
        number = float(value or 0)
        return number if isfinite(number) else 0
    except (ValueError, TypeError):
        return 0


def traffic_period(window, filters, visitors, leads):
    period = blank_period(window, filters)
    starts = [instant(bucket["start"]) for bucket in period["buckets"]]
    selected = list(timed_rows(attributed(visitors, filters), window))
    if len(selected) > MAX_RECORDS:
        raise ValueError("Более 250 000 записей. Сократите период.")
    grouped = [[] for _ in starts]
    for row, when in selected:
        grouped[bisect_right(starts, when) - 1].append(row)

    def summarize(rows):
        identities = {
            str(row.get("visitor_id") or row.get("ip") or ("row:" + str(row["id"])))
            for row in rows
        }
        count = len(rows)
        accepted = sum(row.get("cookie_consent") == "accepted" for row in rows)
        return {
            "visitors": len(identities),
            "visits": count,
            "unique_ips": len({row["ip"] for row in rows if row.get("ip")}),
            "avg_duration": round(
                sum(_safe_number(row.get("session_duration")) for row in rows) / count,
                2,
            )
            if count
            else 0,
            "avg_scroll": round(
                sum(_safe_number(row.get("scroll_depth")) for row in rows) / count, 2
            )
            if count
            else 0,
            "consent_rate": round(accepted / count * 100, 2) if count else 0,
        }

    period["totals"].update(summarize([row for row, _ in selected]))
    for bucket, rows in zip(period["buckets"], grouped):
        bucket["values"].update(summarize(rows))
    if filters.source or filters.campaign:
        period["unavailable"]["leads"] = (
            "У старых заявок нет UTM-атрибуции. Снимите фильтр источника/кампании."
        )
        period["unavailable"]["lead_rate"] = period["unavailable"]["leads"]
    else:
        lead_rows = list(
            timed_rows(
                (row for row in leads if str(row.get("status", "1")) != "0"), window
            )
        )
        period["totals"]["leads"] = len(lead_rows)
        for bucket in period["buckets"]:
            bucket["values"]["leads"] = 0
        for _, when in lead_rows:
            period["buckets"][bisect_right(starts, when) - 1]["values"]["leads"] += 1
        for values in [
            period["totals"],
            *[bucket["values"] for bucket in period["buckets"]],
        ]:
            values["lead_rate"] = (
                round(values["leads"] / values["visits"] * 100, 2)
                if values["visits"]
                else None
            )
    for metric in (
        "views",
        "bounce_rate",
        "goals",
        "goal_rate",
        "demo_clicks",
        "sales_clicks",
    ):
        period["unavailable"][metric] = (
            "Журнал лендинга не измеряет этот показатель. Выберите GA4 или Яндекс.Метрику."
        )
    for key, field in [
        ("channels", "utm_source"),
        ("devices", "device_type"),
        ("languages", "language"),
        ("pages", "page_url"),
        ("campaigns", "utm_campaign"),
    ]:
        counts = Counter(str(row.get(field) or "Не указано") for row, _ in selected)
        period["breakdowns"][key] = [
            {"name": name, "value": count} for name, count in counts.most_common(30)
        ]
    campaigns = {}
    for row, _ in selected:
        if not any(
            row.get(key) for key in ("utm_source", "utm_medium", "utm_campaign")
        ):
            continue
        key = tuple(
            str(row.get(field) or "Не указано")
            for field in ("utm_source", "utm_medium", "utm_campaign")
        )
        group = campaigns.setdefault(
            key, {"source": key[0], "medium": key[1], "campaign": key[2], "rows": []}
        )
        group["rows"].append(row)
    period["campaigns"] = [
        {
            **{key: value for key, value in group.items() if key != "rows"},
            **summarize(group["rows"]),
        }
        for group in sorted(
            campaigns.values(), key=lambda item: len(item["rows"]), reverse=True
        )
    ]
    return period


def platform_period(window, filters, users, payments):
    period = blank_period(window, filters)
    starts = [instant(bucket["start"]) for bucket in period["buckets"]]
    user_rows = list(timed_rows(attributed(users, filters), window))
    payment_rows = list(timed_rows(attributed(payments, filters), window))
    groups = [{"users": [], "payments": []} for _ in starts]
    for rows, name in [(user_rows, "users"), (payment_rows, "payments")]:
        for row, when in rows:
            groups[bisect_right(starts, when) - 1][name].append(row)

    def summarize(user_group, payment_group):
        paid = [
            row for row in payment_group if str(row.get("status", "")).upper() == "PAID"
        ]
        total = (
            None
            if any(row.get("amount_uzs") is None for row in paid)
            else sum(int(row["amount_uzs"]) for row in paid)
        )
        return {
            "new_users": len(user_group),
            "checkouts": len(payment_group),
            "paid_payments": len(paid),
            "paying_users": len({row["user_id"] for row in paid}),
            "revenue_uzs": total,
            "payment_rate": round(len(paid) / len(payment_group) * 100, 2)
            if payment_group
            else None,
            "avg_payment_uzs": round(total / len(paid), 2)
            if paid and total is not None
            else None,
        }

    period["totals"].update(
        summarize([row for row, _ in user_rows], [row for row, _ in payment_rows])
    )
    for bucket, group in zip(period["buckets"], groups):
        bucket["values"].update(summarize(group["users"], group["payments"]))
    if period["totals"]["revenue_uzs"] is None:
        for key in ("revenue_uzs", "avg_payment_uzs"):
            period["unavailable"][key] = (
                "У части успешных платежей отсутствует сумма в UZS. Итог не подменён нулём."
            )
    return period


def merge_period(target, incoming):
    if target["start"] != incoming["start"] or target["end"] != incoming["end"]:
        raise ValueError("Источники вернули разные интервалы.")
    target["totals"].update(incoming["totals"])
    target["unavailable"].update(incoming.get("unavailable", {}))
    indexed = {bucket["start"]: bucket for bucket in target["buckets"]}
    for bucket in incoming["buckets"]:
        if bucket["start"] not in indexed:
            raise ValueError("Источники вернули разные временные группы.")
        indexed[bucket["start"]]["values"].update(bucket["values"])


def csv_bytes(rows):
    output = StringIO(newline="")
    writer = csv.writer(output)
    for row in rows:
        safe = []
        for cell in row:
            text = "" if cell is None else str(cell)
            if not isinstance(cell, (int, float)) and text.lstrip().startswith(
                ("=", "+", "-", "@")
            ):
                text = "'" + text
            safe.append(text)
        writer.writerow(safe)
    return b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")


def xlsx_bytes(sheets):
    """Minimal OOXML workbook: literal strings never become formulas. No parser dependency."""
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package = "http://schemas.openxmlformats.org/package/2006/relationships"
    content = "http://schemas.openxmlformats.org/package/2006/content-types"
    ET.register_namespace("", main)
    ET.register_namespace("r", rel)

    def xml(element):
        return ET.tostring(element, encoding="utf-8", xml_declaration=True)

    def node(parent, tag, **attrs):
        return ET.SubElement(parent, "{" + main + "}" + tag, attrs)

    def column(number):
        result = ""
        while number:
            number, digit = divmod(number - 1, 26)
            result = chr(65 + digit) + result
        return result

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        types = ET.Element("Types", xmlns=content)
        ET.SubElement(
            types,
            "Default",
            Extension="rels",
            ContentType="application/vnd.openxmlformats-package.relationships+xml",
        )
        ET.SubElement(types, "Default", Extension="xml", ContentType="application/xml")
        ET.SubElement(
            types,
            "Override",
            PartName="/xl/workbook.xml",
            ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
        )
        root_rel = ET.Element("Relationships", xmlns=package)
        ET.SubElement(
            root_rel,
            "Relationship",
            Id="rId1",
            Type=rel + "/officeDocument",
            Target="xl/workbook.xml",
        )
        workbook = ET.Element("{" + main + "}workbook")
        definitions = node(workbook, "sheets")
        sheet_rels = ET.Element("Relationships", xmlns=package)
        for index, (name, rows) in enumerate(sheets, 1):
            if not rows:
                rows = [["Нет данных"]]
            ET.SubElement(
                types,
                "Override",
                PartName=f"/xl/worksheets/sheet{index}.xml",
                ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
            )
            node(
                definitions,
                "sheet",
                name=name[:31],
                sheetId=str(index),
                **{"{" + rel + "}id": f"rId{index}"},
            )
            ET.SubElement(
                sheet_rels,
                "Relationship",
                Id=f"rId{index}",
                Type=rel + "/worksheet",
                Target=f"worksheets/sheet{index}.xml",
            )
            sheet = ET.Element("{" + main + "}worksheet")
            views = node(sheet, "sheetViews")
            view = node(views, "sheetView", workbookViewId="0")
            node(
                view,
                "pane",
                ySplit="1",
                topLeftCell="A2",
                activePane="bottomLeft",
                state="frozen",
            )
            data = node(sheet, "sheetData")
            for row_number, values in enumerate(rows, 1):
                row = node(data, "row", r=str(row_number))
                for col, value in enumerate(values, 1):
                    cell = node(row, "c", r=f"{column(col)}{row_number}")
                    if value is None:
                        continue
                    if isinstance(value, bool):
                        cell.set("t", "b")
                        node(cell, "v").text = "1" if value else "0"
                    elif isinstance(value, (int, float)) and isfinite(value):
                        node(cell, "v").text = str(value)
                    else:
                        cell.set("t", "inlineStr")
                        text = node(node(cell, "is"), "t")
                        text.set(
                            "{http://www.w3.org/XML/1998/namespace}space", "preserve"
                        )
                        text.text = re.sub(
                            r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value)
                        )[:32767]
            node(
                sheet, "autoFilter", ref=f"A1:{column(max(map(len, rows)))}{len(rows)}"
            )
            archive.writestr(f"xl/worksheets/sheet{index}.xml", xml(sheet))
        archive.writestr("[Content_Types].xml", xml(types))
        archive.writestr("_rels/.rels", xml(root_rel))
        archive.writestr("xl/workbook.xml", xml(workbook))
        archive.writestr("xl/_rels/workbook.xml.rels", xml(sheet_rels))
    return output.getvalue()


def report_sheets(report):
    metadata = [
        ["Параметр", "Значение"],
        *[[key, value] for key, value in report["filters"].items()],
        ["source", report["source"]],
        ["generated_at", report["generated_at"]],
        [
            "note",
            "Границы: начало включено, конец исключён. Проценты конверсии не суммируются.",
        ],
        *[["note", note] for note in report.get("notes", [])],
    ]
    summary = [
        [
            "Метрика",
            "Текущий период",
            "Период сравнения",
            "Разница",
            "Изменение, %",
            "Единица",
            "Примечание",
        ]
    ]
    for metric in report["metrics"]:
        summary.append(
            [
                metric["label"],
                metric["current"],
                metric["previous"],
                metric["change"]["absolute"],
                metric["change"]["percent"],
                metric["change"].get("unit", metric["unit"]),
                metric.get("reason"),
            ]
        )
    sheets = [("Параметры", metadata), ("Сравнение", summary)]
    for title, key in [("Текущий период", "current"), ("Период сравнения", "previous")]:
        rows = [
            [
                "Начало, UTC",
                "Конец, UTC",
                "Метка в часовом поясе",
                *[label for _, label, _, _ in METRICS],
            ]
        ]
        for bucket in report[key]["buckets"]:
            rows.append(
                [
                    bucket["start"],
                    bucket["end"],
                    bucket["label"],
                    *[bucket["values"].get(metric) for metric, _, _, _ in METRICS],
                ]
            )
        sheets.append((title, rows))
    return sheets


def payment_records(ledger, orders, linked_aliases=()):
    """Normalize ledger/order mirrors consistently across both database readers."""
    known = set(linked_aliases) | {
        str(row[field])
        for row in ledger
        for field in ("id", "transaction_id")
        if row.get(field)
    }
    payments = []
    for row in ledger:
        if str(row.get("plan_type", "")).lower() in {
            "ads_deposit",
            "advertiser_deposit",
        }:
            continue
        payments.append({**row, "amount_uzs": row.get("paid_amount_uzs")})
    for row in sorted(
        orders,
        key=lambda item: (
            str(item.get("status", "")).upper() != "PAID",
            -int(item.get("create_time") or 0),
        ),
    ):
        if row["purpose"] == "advertiser_deposit" or any(
            str(row.get(field)) in known
            for field in ("id", "external_transaction_id")
            if row.get(field)
        ):
            continue
        metadata = row.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (ValueError, TypeError):
                metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        payments.append(
            {
                **row,
                "utm_source": metadata.get("utm_source", ""),
                "utm_campaign": metadata.get("utm_campaign", ""),
            }
        )
        known.update(
            str(row[field])
            for field in ("id", "external_transaction_id")
            if row.get(field)
        )
    return payments
