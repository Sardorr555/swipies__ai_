"""Read-only platform facts for the existing authenticated landing service.

Uses its existing private MYSQL_* configuration. Never creates identities,
sessions or credentials, and never writes to either database.
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from landing_admin_api import load_core


def load_private_settings():
    """Keep deployed credentials outside tracked/static sources."""
    path = Path(__file__).resolve().with_name("admin_reporting_private.json")
    if not path.exists():
        return
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise RuntimeError("Private landing configuration must have mode 0600")
    settings = json.loads(path.read_text(encoding="utf-8"))
    allowed = {
        "MYSQL_HOST",
        "MYSQL_PORT",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DBNAME",
        "TELEGRAM_BOT_TOKEN",
        "GA_SERVICE_ACCOUNT_KEY",
        "YM_OAUTH_TOKEN",
        "GA_PROPERTY_ID",
        "YM_COUNTER_ID",
    }
    if not isinstance(settings, dict) or any(
        key not in allowed or not isinstance(value, str)
        for key, value in settings.items()
    ):
        raise RuntimeError("Invalid private landing configuration")
    for key, value in settings.items():
        if not os.environ.get(key):
            os.environ[key] = value


@contextmanager
def connection():
    import pymysql

    identity = os.environ.get("MYSQL_PASSWORD")
    if not identity:
        raise ValueError(
            "Не настроено защищённое подключение аналитики к базе платформы."
        )
    conn = pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "5455")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=identity,
        database=os.environ.get("MYSQL_DBNAME", "rag_flow"),
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4",
        connect_timeout=3,
        read_timeout=20,
        write_timeout=10,
        autocommit=False,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
        conn.begin()
        yield conn
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()


def platform_report(path, connect=connection):
    core = load_core()
    url = urlsplit(path)
    if url.path not in {
        "/api/v1/admin/analytics/periods",
        "/api/v1/admin/analytics/users",
    }:
        raise ValueError("Неизвестный отчёт платформы.")
    parameters = {key: value[0] for key, value in parse_qs(url.query).items()}
    filters = core.Filters.parse(parameters)
    windows = (filters.current, filters.previous)

    def bounds(selected):
        return [
            int(value.timestamp() * 1000)
            for window in selected
            for value in (window.start, window.end)
        ]

    def predicate(selected):
        return (
            "("
            + " OR ".join("(create_time >= %s AND create_time < %s)" for _ in selected)
            + ")"
        )

    with connect() as conn:

        def read(sql, values):
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
                rows = list(cursor.fetchall())
            if len(rows) > core.MAX_RECORDS:
                raise ValueError("Более 250 000 записей. Сократите период.")
            return rows

        if url.path.endswith("/users"):
            page = int(parameters.get("page", 1))
            search = parameters.get("search", "").strip()
            if not 1 <= page <= core.MAX_RECORDS // 100 or len(search) > 200:
                raise ValueError("Некорректный номер страницы или поиск.")
            users = read(
                "SELECT id,email,nickname,create_time,status,is_active,last_login_time,referred_by_id,utm_source,utm_campaign, (SELECT COUNT(*) FROM knowledgebase k WHERE k.created_by=user.id AND k.status='1') AS kb_count, (SELECT COUNT(*) FROM dialog d WHERE d.tenant_id=user.id AND d.status='1') AS dialog_count FROM user WHERE "
                + predicate([filters.current])
                + " ORDER BY create_time DESC,id DESC LIMIT %s",
                [*bounds([filters.current]), core.MAX_RECORDS + 1],
            )
            selected = [
                row
                for row in users
                if core.match_attribution(row, filters)
                and (
                    not search
                    or search.casefold() in str(row.get("email") or "").casefold()
                    or search.casefold() in str(row.get("nickname") or "").casefold()
                )
            ]
            total = len(selected)
            selected = selected[(page - 1) * 100 : page * 100]
            for row in selected:
                row["create_date"] = core.iso(core.instant(row.pop("create_time")))
            return {"data": selected, "total": total, "page": page, "page_size": 100}

        users = read(
            "SELECT id,create_time,visitor_id,utm_source,utm_campaign FROM user WHERE "
            + predicate(windows)
            + " LIMIT %s",
            [*bounds(windows), core.MAX_RECORDS + 1],
        )
        ledger = read(
            "SELECT id,transaction_id,user_id,status,paid_amount_uzs,plan_type,create_time,utm_source,utm_campaign FROM payment_transaction WHERE "
            + predicate(windows)
            + " LIMIT %s",
            [*bounds(windows), core.MAX_RECORDS + 1],
        )
        orders = read(
            "SELECT id,external_transaction_id,user_id,status,purpose,amount_uzs,create_time,metadata FROM payment_orders WHERE "
            + predicate(windows)
            + " LIMIT %s",
            [*bounds(windows), core.MAX_RECORDS + 1],
        )
        aliases = list(
            {
                str(row[field])
                for row in orders
                for field in ("id", "external_transaction_id")
                if row.get(field)
            }
        )
        known = set()
        for offset in range(0, len(aliases), 200):
            batch = aliases[offset : offset + 200]
            placeholders = ",".join(["%s"] * len(batch))
            linked = read(
                "SELECT id,transaction_id FROM payment_transaction WHERE id IN ("
                + placeholders
                + ") OR transaction_id IN ("
                + placeholders
                + ")",
                [*batch, *batch],
            )
            known.update(
                str(row[field])
                for row in linked
                for field in ("id", "transaction_id")
                if row.get(field)
            )
        payments = core.payment_records(ledger, orders, known)
    return core.assemble(
        filters,
        core.platform_period(filters.current, filters, users, payments),
        core.platform_period(filters.previous, filters, users, payments),
        "platform",
        [
            "Регистрации и платежи относятся к дате создания записи. Статусы оплаты актуальны на момент отчёта.",
            "В выручку входят только PAID-платежи в UZS, без рекламных депозитов и двойного учёта заказов.",
            "База платформы читается в транзакции READ ONLY через существующее защищённое подключение админки лендинга.",
        ],
    )
