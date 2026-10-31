"""Read-only platform facts for the landing administrator's period comparison."""

import json

from api.analytics_reporting import Filters, MAX_RECORDS, assemble, platform_period


def _bounded(query):
    result = list(query.limit(MAX_RECORDS + 1).dicts())
    if len(result) > MAX_RECORDS:
        raise ValueError("Более 250 000 записей. Сократите период.")
    return result


def report(parameters):
    from api.db.db_models import DB, User, PaymentTransaction, PaymentOrder

    filters = Filters.parse(parameters)

    def in_windows(field):
        return (
            (field >= int(filters.current.start.timestamp() * 1000))
            & (field < int(filters.current.end.timestamp() * 1000))
        ) | (
            (field >= int(filters.previous.start.timestamp() * 1000))
            & (field < int(filters.previous.end.timestamp() * 1000))
        )

    with DB.connection_context():
        users = _bounded(
            User.select(
                User.id,
                User.create_time,
                User.visitor_id,
                User.utm_source,
                User.utm_campaign,
            ).where(in_windows(User.create_time))
        )
        fields = [
            PaymentTransaction.id,
            PaymentTransaction.transaction_id,
            PaymentTransaction.user_id,
            PaymentTransaction.status,
            PaymentTransaction.paid_amount_uzs,
            PaymentTransaction.plan_type,
            PaymentTransaction.create_time,
            PaymentTransaction.utm_source,
            PaymentTransaction.utm_campaign,
        ]
        ledger = _bounded(
            PaymentTransaction.select(*fields).where(
                in_windows(PaymentTransaction.create_time)
            )
        )
        orders = _bounded(
            PaymentOrder.select(
                PaymentOrder.id,
                PaymentOrder.external_transaction_id,
                PaymentOrder.user_id,
                PaymentOrder.status,
                PaymentOrder.purpose,
                PaymentOrder.amount_uzs,
                PaymentOrder.create_time,
                PaymentOrder.metadata,
            ).where(in_windows(PaymentOrder.create_time))
        )
        # A mirrored order can have a different creation date from the ledger.
        # Check its aliases outside the requested dates before counting it.
        aliases = list(
            {
                str(row.get(field))
                for row in orders
                for field in ("id", "external_transaction_id")
                if row.get(field)
            }
        )
        known = {
            str(row[field])
            for row in ledger
            for field in ("id", "transaction_id")
            if row.get(field)
        }
        for offset in range(0, len(aliases), 200):
            batch = aliases[offset : offset + 200]
            linked = (
                PaymentTransaction.select(
                    PaymentTransaction.id, PaymentTransaction.transaction_id
                )
                .where(
                    (PaymentTransaction.id.in_(batch))
                    | (PaymentTransaction.transaction_id.in_(batch))
                )
                .dicts()
            )
            for row in linked:
                known.update(
                    str(row[field])
                    for field in ("id", "transaction_id")
                    if row.get(field)
                )
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
    return assemble(
        filters,
        platform_period(filters.current, filters, users, payments),
        platform_period(filters.previous, filters, users, payments),
        "platform",
        [
            "Регистрации и платежи относятся к дате создания записи. Статусы оплаты актуальны на момент отчёта.",
            "В выручку входят только PAID-платежи, без рекламных депозитов. Валюта — UZS; расчётный курс USD не используется.",
        ],
    )


def users_report(parameters):
    from api.db.db_models import DB, User

    filters = Filters.parse(parameters)
    page = int(parameters.get("page", 1))
    search = str(parameters.get("search", "")).strip()
    if not 1 <= page <= MAX_RECORDS // 100 or len(search) > 200:
        raise ValueError("Некорректный номер страницы или поиск.")
    with DB.connection_context():
        query = User.select(
            User.id,
            User.email,
            User.nickname,
            User.create_time,
            User.create_date,
            User.status,
            User.referred_by_id,
            User.utm_source,
            User.utm_campaign,
        ).where(
            User.create_time >= int(filters.current.start.timestamp() * 1000),
            User.create_time < int(filters.current.end.timestamp() * 1000),
        )
        records = _bounded(query.order_by(User.create_time.desc(), User.id.desc()))
    from api.analytics_reporting import instant, iso, match_attribution

    records = [
        row
        for row in records
        if match_attribution(row, filters)
        and (
            not search
            or search.casefold() in str(row.get("email") or "").casefold()
            or search.casefold() in str(row.get("nickname") or "").casefold()
        )
    ]
    total = len(records)
    records = records[(page - 1) * 100 : page * 100]
    for row in records:
        row["create_date"] = iso(instant(row["create_time"]))
    return {"data": records, "total": total, "page": page, "page_size": 100}
