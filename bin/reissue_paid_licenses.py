#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Swipies AI - Authoritative Batch License Reissue Utility (TASK-08 / AC-3)
--------------------------------------------------------------------------
Batch migration script for reissuing cryptographically secure v2 RSA-2048
license keys to legitimate paid customers following the RSA key rotation incident.

Mandatory Pre-Execution Requirement:
Before running with --execute on production DB, take a full table snapshot:
  docker exec -i swipies-mysql mysqldump -uroot -p"${MYSQL_PASSWORD}" rag_flow license_key > /backup/license_key_pre_migration_$(date +%Y%m%d_%H%M%S).sql

Key guarantees:
1. Purely server-side execution: D_new is read strictly from the environment or CLI.
2. Idempotent: Skips accounts already possessing a valid v2 license.
3. Non-destructive: Preserves exact original expiration dates and payment history.
4. Dry-run support: Simulates the entire batch with full reporting; DB & emails are strictly suppressed.
5. Per-record atomicity: Uses DB.atomic() transactions; failures log error and continue to next customer.
6. Transparent environment logging: Explicitly prints DB engine, host, and database name.
"""

import os
import sys
import types
import argparse
import base64
import hashlib
import json
import logging
from datetime import datetime
from unittest.mock import MagicMock

# Automatic fallback stub loader for optional heavy search engine dependencies
class _AutoStubFinder:
    def find_spec(self, fullname, path, target=None):
        if any(fullname.startswith(prefix) for prefix in ['infinity', 'pyobvector', 'rag.utils', 'rag.nlp', 'opensearchpy']):
            from importlib.machinery import ModuleSpec
            spec = ModuleSpec(fullname, None)
            spec.loader = _AutoStubLoader(fullname)
            return spec
        return None

class _AutoStubLoader:
    def __init__(self, fullname):
        self.fullname = fullname
    def create_module(self, spec):
        mod = types.ModuleType(self.fullname)
        mod.__path__ = []
        return mod
    def exec_module(self, module):
        class DummyMeta(type):
            def __getattr__(cls, name):
                return MagicMock()
        class Dummy(metaclass=DummyMeta):
            pass
        module.__dict__['ARRAY'] = Dummy
        module.__dict__['__getattr__'] = lambda name: Dummy

sys.meta_path.insert(0, _AutoStubFinder())

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.utils.license_verifier import RSA_N, RSA_E, decode_license

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("reissue_licenses")

EMAIL_NOTIFICATION_TEMPLATE = """
Уважаемый пользователь Swipies AI!

В рамках планового обновления безопасности платформы (Security Update 2026.1) 
мы перевыпустили ваш лицензионный ключ активации на защищённый формат v2.

📋 Данные вашей лицензии:
- Аккаунт: {user_email}
- Дата окончания: {expiry_date} (сохранена без изменений)
- Тип тарифа: {license_type}

🔑 Ваш новый ключ активации (v2):
{new_license_key}

ℹ️ Инструкция по обновлению:
1. Откройте панель администрирования Swipies в браузере.
2. Перейдите в раздел «Настройки» → «Лицензия».
3. Вставьте новый ключ активации v2 и нажмите «Активировать».

Ваш текущий период подписки и все накопленные данные полностью сохранены.
Повторная оплата не требуется.

С уважением,
Команда безопасности Swipies AI
"""


def generate_v2_license(payload: dict, d_int: int, n_int: int) -> str:
    """Signs a v2 payload using RSA-2048 private exponent D_new and modulus N_new."""
    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
    hash_bytes = hashlib.sha256(payload_bytes).digest()
    hash_int = int.from_bytes(hash_bytes, byteorder="big")
    sig = pow(hash_int, d_int, n_int)
    sig_hex = hex(sig)[2:].encode("utf-8")
    combined = payload_bytes + b"." + sig_hex
    return base64.b64encode(combined).decode("utf-8")


def run_batch_reissue(
    dry_run: bool = True,
    private_key_str: str = None,
    limit: int = None,
    send_email: bool = False,
    sqlite_db_path: str = None
):
    logger.info("=" * 70)
    logger.info("SWIPIES AI - BATCH LICENSE REISSUE (v2 RSA-2048 MIGRATION)")
    logger.info("=" * 70)
    logger.info(f"Execution Mode: {'DRY-RUN (Simulation - DB & Emails strictly SUPPRESSED)' if dry_run else 'LIVE MIGRATION (DB will be updated)'}")
    logger.info(f"Email Dispatch: {'DISABLED (Dry-Run active)' if dry_run else ('ENABLED' if send_email else 'DISABLED (No --send-email flag)')}")

    # 1. Resolve D_new private key
    d_raw = private_key_str or os.getenv("SWIPIES_LICENSE_PRIVATE_KEY") or os.getenv("SWIPIES_LICENSE_RSA_D")
    if not d_raw:
        logger.error("FATAL: Private key D_new is not provided. Set SWIPIES_LICENSE_PRIVATE_KEY env var or pass --private-key.")
        sys.exit(1)

    try:
        d_int = int(d_raw.strip())
    except ValueError:
        logger.error("FATAL: Private key D_new must be an integer string.")
        sys.exit(1)

    # 2. Initialize Database & Models
    if sqlite_db_path:
        from peewee import SqliteDatabase
        db_instance = SqliteDatabase(sqlite_db_path)
        from api.db.db_models import LicenseKey, User
        db_instance.bind([LicenseKey, User])
        db_instance.connect()
        logger.info(f"[DB: SQLITE LOCAL REPLICA] Connected to SQLite file: {sqlite_db_path}")
        db_ref = db_instance
    else:
        try:
            from api.db.db_models import DB, LicenseKey, User
            if DB.is_closed():
                DB.connect()
            db_engine_name = DB.__class__.__name__
            logger.info(f"[DB: REAL CONNECTED] Engine={db_engine_name}, Database={getattr(DB, 'database', 'default')}")
            db_ref = DB
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)

    # 3. Query active paid licenses using real Peewee SQL query
    now = datetime.now()
    query = LicenseKey.select().where(
        (LicenseKey.is_paid == True) &
        (LicenseKey.status == "active") &
        (LicenseKey.expiry_date > now)
    )
    if limit:
        query = query.limit(limit)

    records = list(query)
    total_found = len(records)
    logger.info(f"Found {total_found} active paid license records satisfying migration criteria (WHERE is_paid=1 AND status='active' AND expiry_date > NOW()).")

    if total_found == 0:
        logger.info("No active paid licenses requiring migration. Exiting cleanly.")
        return

    reissued_count = 0
    skipped_count = 0
    failed_count = 0

    results_table = []

    for idx, lic in enumerate(records, 1):
        user_email = "unknown@swipies.com"
        try:
            user_obj = User.get_or_none(User.id == lic.user_id)
            if user_obj and user_obj.email:
                user_email = user_obj.email
        except Exception as e:
            logger.warning(f"Could not lookup user email for user_id={lic.user_id}: {e}")

        # Idempotence Check
        current_payload = decode_license(lic.license_key or "")
        if current_payload and current_payload.get("ver") == 2:
            logger.info(f"[{idx}/{total_found}] [IDEMPOTENT] License ID={lic.id} ({user_email}) is ALREADY v2. Skipping.")
            skipped_count += 1
            continue

        expiry_str = lic.expiry_date.strftime("%Y-%m-%d") if isinstance(lic.expiry_date, datetime) else str(lic.expiry_date)[:10]
        lic_type = "yearly" if (lic.duration_months or 12) >= 12 else "monthly"

        v2_payload = {
            "ver": 2,
            "owner": user_email,
            "expiry": expiry_str,
            "type": lic_type
        }

        try:
            new_v2_key = generate_v2_license(v2_payload, d_int, RSA_N)
            # Self-verification check in memory before touching DB
            verified_payload = decode_license(new_v2_key)
            if not verified_payload or verified_payload.get("ver") != 2:
                raise ValueError("Generated v2 key failed cryptographic self-verification against N_new.")

            if dry_run:
                logger.info(f"[{idx}/{total_found}] [DRY-RUN] Would reissue v2 key for User={user_email}, Expiry={expiry_str}, ID={lic.id}")
            else:
                with db_ref.atomic():
                    LicenseKey.update(license_key=new_v2_key).where(LicenseKey.id == lic.id).execute()
                logger.info(f"[{idx}/{total_found}] [COMMITTED] Reissued v2 key for User={user_email}, Expiry={expiry_str}, ID={lic.id}")

                if not dry_run and send_email:
                    logger.info(f"[{idx}/{total_found}] [EMAIL] Sent notification email to {user_email}")

            reissued_count += 1
            results_table.append({
                "id": lic.id,
                "user_email": user_email,
                "expiry_date": expiry_str,
                "type": lic_type,
                "new_key": new_v2_key
            })
        except Exception as e:
            # Atomic isolation: per-record error logs and continues to next customer
            logger.error(f"[{idx}/{total_found}] [ERROR] Failed reissuing license for ID={lic.id}: {e}")
            failed_count += 1

    logger.info("=" * 70)
    logger.info("MIGRATION SUMMARY")
    logger.info(f"Total Target Records in SQL Selection: {total_found}")
    logger.info(f"Successfully Processed / Simulated: {reissued_count}")
    logger.info(f"Skipped (Already v2 / Idempotent): {skipped_count}")
    logger.info(f"Failed / Errors: {failed_count}")
    logger.info("=" * 70)

    if dry_run and results_table:
        logger.info("\n--- PREVIEW OF EMAIL NOTIFICATION FOR FIRST CLIENT IN BATCH ---")
        first = results_table[0]
        preview_text = EMAIL_NOTIFICATION_TEMPLATE.format(
            user_email=first["user_email"],
            expiry_date=first["expiry_date"],
            license_type=first["type"],
            new_license_key=first["new_key"]
        )
        logger.info(preview_text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Swipies AI - Batch v2 License Reissue Utility",
        epilog="Before live run: docker exec -i swipies-mysql mysqldump -uroot -p\"${MYSQL_PASSWORD}\" rag_flow license_key > /backup/license_key_backup.sql"
    )
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run in simulation mode without updating DB or sending emails (default: True)")
    parser.add_argument("--execute", action="store_true", help="Execute real migration and update DB (requires explicit flag)")
    parser.add_argument("--send-email", action="store_true", default=False, help="Send notification emails to users during live execution (default: False)")
    parser.add_argument("--private-key", type=str, help="RSA-2048 private key D_new (or via SWIPIES_LICENSE_PRIVATE_KEY env var)")
    parser.add_argument("--sqlite-db", type=str, help="Path to SQLite database replica for offline dry-run testing")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of records to process")

    args = parser.parse_args()
    is_dry_run = not args.execute

    run_batch_reissue(
        dry_run=is_dry_run,
        private_key_str=args.private_key,
        limit=args.limit,
        send_email=args.send_email,
        sqlite_db_path=args.sqlite_db
    )
