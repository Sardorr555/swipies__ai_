"""Durable, consent-gated conversion outbox; platform/journal are read-only.

Only this integration's separate private SQLite file is written. A failure here
never propagates into registration, billing, the landing or existing reports.
"""

import json
import os
import re
import sqlite3
import threading
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from landing_admin_api import load_core

ID = re.compile(r"(?:v_[a-z0-9]{6,20}_[0-9]{13}|[a-f0-9-]{36})\Z")


def safe_tag(value):
    text = str(value or "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]{0,63}", text) or re.search(
        r"[a-f0-9]{32,}|(?:phc_|phx_|eyJ)", text, re.IGNORECASE
    ):
        return ""
    return text


class State:
    def __init__(self, path, clock=time.time):
        self.path = Path(path).resolve()
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if Path(path).is_symlink():
            raise ValueError("State file cannot be a symlink")
        with closing(self.db()) as db, db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS meta (name TEXT PRIMARY KEY,value REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS consent (visitor TEXT PRIMARY KEY,granted INTEGER NOT NULL,since REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS aliases (event TEXT,alias TEXT,uuid TEXT NOT NULL,PRIMARY KEY(event,alias));
            CREATE TABLE IF NOT EXISTS outbox (uuid TEXT PRIMARY KEY,visitor TEXT NOT NULL,at REAL NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,next_attempt REAL NOT NULL DEFAULT 0,lease REAL NOT NULL DEFAULT 0);
            """)
            db.execute(
                "INSERT OR IGNORE INTO meta VALUES ('started',?)", [self.clock()]
            )
        os.chmod(self.path, 0o600)

    def db(self):
        return sqlite3.connect(self.path, timeout=5)

    @property
    def started(self):
        with closing(self.db()) as db:
            return db.execute("SELECT value FROM meta WHERE name='started'").fetchone()[
                0
            ]

    def consent(self, visitor, granted):
        if not ID.fullmatch(visitor):
            raise ValueError("Invalid anonymous visitor id")
        with closing(self.db()) as db, db:
            db.execute(
                "INSERT INTO consent VALUES (?,?,?) ON CONFLICT(visitor) DO UPDATE SET granted=excluded.granted,since=excluded.since WHERE granted!=excluded.granted",
                [visitor, int(granted), self.clock()],
            )
            if not granted:
                db.execute(
                    "UPDATE outbox SET status='cancelled' WHERE visitor=? AND status='pending'",
                    [visitor],
                )

    def allowed(self, visitor, at):
        with closing(self.db()) as db:
            row = db.execute(
                "SELECT granted,since FROM consent WHERE visitor=?", [visitor]
            ).fetchone()
        return bool(row and row[0] and at >= row[1])

    def enqueue(self, event, aliases, visitor, at, properties):
        if not self.allowed(visitor, at):
            return False
        with closing(self.db()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            known = []
            for alias in aliases:
                row = db.execute(
                    "SELECT uuid FROM aliases WHERE event=? AND alias=?", [event, alias]
                ).fetchone()
                if row:
                    known.append(row[0])
            ident = (
                min(known)
                if known
                else str(
                    uuid5(
                        NAMESPACE_URL,
                        "swipies/posthog/" + event + "/" + min(aliases),
                    )
                )
            )
            for alias in aliases:
                db.execute(
                    "INSERT OR IGNORE INTO aliases VALUES (?,?,?)",
                    [event, alias, ident],
                )
            payload = {
                "uuid": ident,
                "event": event,
                "distinct_id": visitor,
                "timestamp": datetime.fromtimestamp(at, UTC).isoformat(),
                "properties": {
                    **properties,
                    "$insert_id": ident,
                    "$process_person_profile": False,
                    "$geoip_disable": True,
                    "$ip": None,
                    "swipies_origin": "server",
                    "swipies_schema": "1",
                    "swipies_environment": "production",
                    "swipies_internal": False,
                },
            }
            db.execute(
                "INSERT OR IGNORE INTO outbox(uuid,visitor,at,payload) VALUES (?,?,?,?)",
                [ident, visitor, at, json.dumps(payload, separators=(",", ":"))],
            )
        return True

    def claim(self):
        now = self.clock()
        with closing(self.db()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT uuid,visitor,at,payload,attempts FROM outbox WHERE status='pending' AND next_attempt<=? AND lease<=? ORDER BY rowid LIMIT 1",
                [now, now],
            ).fetchone()
            if row:
                db.execute("UPDATE outbox SET lease=? WHERE uuid=?", [now + 60, row[0]])
        return row

    def finish(self, ident, success, attempts, retry_after=0):
        with closing(self.db()) as db, db:
            db.execute(
                "UPDATE outbox SET status=?,attempts=?,next_attempt=?,lease=0 WHERE uuid=? AND status='pending'",
                [
                    "sent" if success else "pending",
                    attempts + 1,
                    self.clock()
                    + max(retry_after, min(3600, 2 ** min(attempts + 1, 11))),
                    ident,
                ],
            )

    def status(self):
        with closing(self.db()) as db:
            counts = dict(
                db.execute("SELECT status,COUNT(*) FROM outbox GROUP BY status")
            )
            last = db.execute(
                "SELECT MAX(at) FROM outbox WHERE status='sent'"
            ).fetchone()[0]
        return {
            "pending": counts.get("pending", 0),
            "sent": counts.get("sent", 0),
            "cancelled": counts.get("cancelled", 0),
            "last_event_at": last,
            "tracking_started_at": self.started,
        }


def read_facts(since):
    from landing_platform_reports import connection

    stamp = int(since * 1000)
    with connection() as conn:

        def read(query):
            with conn.cursor() as cursor:
                cursor.execute(query, [stamp, 10001])
                rows = list(cursor.fetchall())
            if len(rows) > 10000:
                raise ValueError(
                    "Conversion source exceeds safe scan limit; retention/paging configuration required"
                )
            return rows

        users = read(
            "SELECT u.id,u.visitor_id,u.create_time,u.is_superuser FROM user u WHERE u.create_time >= %s AND EXISTS (SELECT 1 FROM tenant t WHERE t.id=u.id) AND EXISTS (SELECT 1 FROM user_tenant ut WHERE ut.user_id=u.id AND ut.tenant_id=u.id AND ut.role='owner') AND EXISTS (SELECT 1 FROM file f WHERE f.tenant_id=u.id AND f.type='folder') ORDER BY u.create_time LIMIT %s"
        )
        ledger = read(
            "SELECT p.id,p.transaction_id,p.user_id,p.status,p.plan_type,p.create_time,p.provisioned_at,u.visitor_id,u.is_superuser FROM payment_transaction p JOIN user u ON u.id=p.user_id WHERE p.create_time >= %s ORDER BY p.create_time LIMIT %s"
        )
        orders = read(
            "SELECT p.id,p.external_transaction_id,p.user_id,p.status,p.purpose,p.plan_id,p.create_time,u.visitor_id,u.is_superuser FROM payment_orders p JOIN user u ON u.id=p.user_id WHERE p.create_time >= %s ORDER BY p.create_time LIMIT %s"
        )
    return {"users": users, "ledger": ledger, "orders": orders}


class Collector:
    def __init__(
        self,
        config,
        database,
        *,
        state=None,
        facts=read_facts,
        transport=None,
        clock=time.time,
    ):
        self.config = config
        self.clock = clock
        self.facts = facts
        self.stop = threading.Event()
        self.state = state or State(
            config.state_db
            or Path(database).resolve().with_name("posthog-state.sqlite"),
            clock,
        )
        self.transport = transport
        self.error = None

    def tick(self):
        if not self.config.capture_ready:
            return
        core = load_core()
        snapshot = self.facts(self.state.started)

        def eligible(row):
            visitor = str(row.get("visitor_id") or "")
            return bool(
                ID.fullmatch(visitor)
                and visitor not in self.config.internal_visitors
                and row.get("is_superuser") not in (True, 1, "1")
            )

        for row in snapshot["users"]:
            if eligible(row):
                self.state.enqueue(
                    "registration_completed",
                    ["user:" + str(row["id"])],
                    row["visitor_id"],
                    core.instant(row["create_time"]).timestamp(),
                    {"site_area": "platform"},
                )
        # Orders first preserves the stable checkout identity when a gateway ID
        # is assigned later and the same payment is mirrored into the ledger.
        for row in [*snapshot["orders"], *snapshot["ledger"]]:
            if not eligible(row) or str(
                row.get("purpose") or row.get("plan_type", "")
            ).lower() in {"advertiser_deposit", "ads_deposit"}:
                continue
            aliases = ["id:" + str(row["id"])]
            transaction = row.get("external_transaction_id") or row.get(
                "transaction_id"
            )
            if transaction:
                aliases.append("tx:" + str(transaction))
            at = core.instant(row["create_time"]).timestamp()
            props = {
                "site_area": "platform",
                "plan": safe_tag(row.get("plan_id") or row.get("plan_type")),
            }
            self.state.enqueue("payment_started", aliases, row["visitor_id"], at, props)
            if str(row.get("status", "")).upper() == "PAID":
                confirmed = (
                    core.instant(row["provisioned_at"]).timestamp()
                    if row.get("provisioned_at")
                    else self.clock()
                )
                self.state.enqueue(
                    "payment_completed",
                    aliases,
                    row["visitor_id"],
                    confirmed,
                    {
                        **props,
                        "payment_time_basis": "provisioned_at"
                        if row.get("provisioned_at")
                        else "first_observed_paid",
                    },
                )
        delivery_error = None
        for _ in range(20):
            row = self.state.claim()
            if not row:
                break
            ident, visitor, at, payload, attempts = row
            if not self.state.allowed(visitor, at):
                self.state.consent(visitor, False)
                continue
            try:
                if self.transport is None:
                    import requests

                    self.transport = requests
                response = self.transport.post(
                    self.config.ingest_host + "/i/v0/e/",
                    json={"api_key": self.config.project_token, **json.loads(payload)},
                    timeout=(3, 8),
                    allow_redirects=False,
                )
                success = response.status_code in (200, 201)
                retry = (
                    str(response.headers.get("Retry-After", "60"))
                    if response.status_code == 429
                    else "0"
                )
                self.state.finish(
                    ident,
                    success,
                    attempts,
                    max(0, min(3600, int(retry))) if retry.isdigit() else 60,
                )
                if not success:
                    delivery_error = "Доставка в PostHog отложена; события сохранены для повторной попытки."
                    break
            except Exception:  # noqa: BLE001 -- optional delivery must retain retry state.
                self.state.finish(ident, False, attempts)
                delivery_error = (
                    "PostHog недоступен; события сохранены для повторной попытки."
                )
                break
        self.error = delivery_error

    def run(self):
        while not self.stop.is_set():
            try:
                self.tick()
            except Exception:  # noqa: BLE001 -- isolate the optional background worker.
                self.error = (
                    "Сборщик событий временно недоступен; источник данных не изменён."
                )
            self.stop.wait(30)
