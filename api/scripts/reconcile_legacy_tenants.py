#!/usr/bin/env python3
#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
Historical Tenant Payment Reconciliation & Backfill CLI.

Audits all active non-free tenants against:
1. Team Whitelist (internal accounts)
2. Atmos Settlement CSV (gateway-verified real payments)
3. Unverified accounts (flagged as REQUIRES_AUDIT in PaymentTransaction ledger)

Usage:
  python api/scripts/reconcile_legacy_tenants.py --dry-run
  python api/scripts/reconcile_legacy_tenants.py --csv-path=/path/to/settlement.csv --team-emails=admin@swipies.app,dev@swipies.app --execute
  python api/scripts/reconcile_legacy_tenants.py --execute --downgrade-unverified
"""

import os
import sys
import csv
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ReconcileLegacyTenants")


def load_atmos_csv(csv_path: str):
    """
    Parses Atmos settlement CSV file.
    Expected headers (or flexible match): transaction_id, account/email, amount/amount_uzs, status/result
    """
    if not csv_path or not os.path.exists(csv_path):
        return {}

    transactions = {}
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys
            norm_row = {k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items() if k}
            tx_id = norm_row.get("transaction_id") or norm_row.get("id") or norm_row.get("tx_id")
            email = norm_row.get("email") or norm_row.get("account") or norm_row.get("user")
            status = str(norm_row.get("status") or norm_row.get("result") or "").upper()
            raw_amount = norm_row.get("amount") or norm_row.get("amount_uzs") or "0"
            try:
                amount_num = float(raw_amount.replace(",", "").replace(" ", ""))
                # If amount > 10,000,000 it's likely tiyins
                amount_uzs = int(amount_num // 100) if amount_num > 10000000 else int(amount_num)
            except ValueError:
                amount_uzs = 0

            if tx_id:
                record = {
                    "transaction_id": tx_id,
                    "email": email.lower() if email else "",
                    "status": status,
                    "amount_uzs": amount_uzs,
                    "raw": norm_row,
                }
                transactions[tx_id] = record
                if email:
                    transactions[email.lower()] = record
    logger.info(f"Loaded {len(transactions)} transaction records from {csv_path}")
    return transactions


def run_reconciliation(
    csv_path: str = None,
    team_emails_str: str = "",
    dry_run: bool = True
):
    from api.db.db_models import User, Tenant, PaymentTransaction, DB
    from api.db.services.payment_transaction_service import PaymentTransactionService

    team_emails = set(
        e.strip().lower() for e in team_emails_str.split(",") if e.strip()
    ) if team_emails_str else set()

    # Default internal team whitelist if none provided
    if not team_emails:
        team_emails = {"admin@swipies.app", "developer@swipies.app"}

    csv_data = load_atmos_csv(csv_path) if csv_path else {}

    print("\n" + "=" * 70)
    print(f"  SWIPIES PAYMENT RECONCILIATION AUDIT ({'DRY-RUN' if dry_run else 'LIVE EXECUTION'})")
    print("=" * 70)
    print(f"Team Whitelist ({len(team_emails)}): {', '.join(team_emails)}")
    if csv_path:
        print(f"Atmos CSV: {csv_path}")
    print("Gate Policy: Non-destructive audit logging only (Resolution via Admin UI)")
    print("-" * 70)

    # 1. Fetch non-free tenants
    with DB.connection_context():
        non_free_tenants = list(Tenant.select().where(Tenant.plan_type != "free"))

    print(f"Found {len(non_free_tenants)} non-free tenant(s) in database.\n")

    stats = {
        "total": len(non_free_tenants),
        "team_whitelisted": 0,
        "csv_matched_paid": 0,
        "already_recorded": 0,
        "unverified_flagged": 0,
    }

    report_rows = []

    for tenant in non_free_tenants:
        with DB.connection_context():
            user = User.get_or_none(User.id == tenant.id)
        email = user.email.lower() if user and user.email else f"unknown-{tenant.id}@unknown.com"
        plan = tenant.plan_type
        expected_uzs = PaymentTransactionService.calculate_expected_amount_uzs(plan, 1)

        # Check if already recorded in payment_transaction
        existing_tx = PaymentTransactionService.get_by_tx_id(f"legacy-{tenant.id}")
        if not existing_tx:
            # Check by user_id
            existing_user_txs = list(PaymentTransaction.select().where(
                (PaymentTransaction.user_id == tenant.id) &
                (PaymentTransaction.status == "PAID")
            ))
            if existing_user_txs:
                existing_tx = existing_user_txs[0]

        decision = ""
        action_note = ""

        # Case 1: Team whitelist
        if email in team_emails:
            decision = "TEAM_WHITELIST"
            action_note = "Marked as internal team member (0 UZS)"
            stats["team_whitelisted"] += 1
            if not dry_run:
                PaymentTransactionService.create_pending(
                    transaction_id=f"legacy-team-{tenant.id}",
                    user_id=tenant.id,
                    tenant_id=tenant.id,
                    account_email=email,
                    plan_type=plan,
                    duration_months=12,
                    expected_amount_uzs=0,
                    payment_method="manual_admin",
                )
                PaymentTransactionService.mark_paid(
                    transaction_id=f"legacy-team-{tenant.id}",
                    paid_amount_uzs=0,
                    audit_note="Team internal account whitelist backfill",
                )

        # Case 2: Already recorded as PAID in ledger
        elif existing_tx and existing_tx.status == "PAID":
            decision = "ALREADY_VERIFIED"
            action_note = f"Ledger TX #{existing_tx.transaction_id} already marked PAID ({existing_tx.paid_amount_uzs} UZS)"
            stats["already_recorded"] += 1

        # Case 3: Matched in Atmos CSV
        elif email in csv_data or str(tenant.id) in csv_data:
            csv_rec = csv_data.get(email) or csv_data.get(str(tenant.id))
            csv_status = csv_rec.get("status", "")
            csv_amount = csv_rec.get("amount_uzs", 0)
            csv_tx_id = csv_rec.get("transaction_id", f"legacy-csv-{tenant.id}")

            if csv_status in ("PAID", "SUCCESS", "CONFIRMED", "OK") and csv_amount >= expected_uzs * 0.9:
                decision = "CSV_MATCHED_PAID"
                action_note = f"Verified via Atmos CSV #{csv_tx_id} ({csv_amount} UZS)"
                stats["csv_matched_paid"] += 1
                if not dry_run:
                    PaymentTransactionService.create_pending(
                        transaction_id=csv_tx_id,
                        user_id=tenant.id,
                        tenant_id=tenant.id,
                        account_email=email,
                        plan_type=plan,
                        duration_months=1,
                        expected_amount_uzs=expected_uzs,
                        payment_method="legacy_backfill",
                    )
                    PaymentTransactionService.mark_paid(
                        transaction_id=csv_tx_id,
                        paid_amount_uzs=csv_amount,
                        gateway_response=csv_rec.get("raw"),
                        audit_note=f"Reconciled via Atmos CSV settlement match {csv_tx_id}",
                    )
            else:
                decision = "CSV_UNDERPAID_OR_FAILED"
                action_note = f"CSV record found but invalid: status={csv_status}, amount={csv_amount} UZS"
                stats["unverified_flagged"] += 1
                if not dry_run:
                    tx, _ = PaymentTransactionService.create_pending(
                        transaction_id=f"legacy-audit-{tenant.id}",
                        user_id=tenant.id,
                        tenant_id=tenant.id,
                        account_email=email,
                        plan_type=plan,
                        duration_months=1,
                        expected_amount_uzs=expected_uzs,
                        payment_method="legacy_backfill",
                    )
                    PaymentTransaction.update(
                        status="REQUIRES_AUDIT",
                        audit_note=f"Atmos CSV mismatch: {action_note}"
                    ).where(PaymentTransaction.id == tx.id).execute()

        # Case 4: No payment found & not in team
        else:
            decision = "UNVERIFIED_SUSPECT"
            action_note = f"No Atmos record found for plan '{plan}' (expected {expected_uzs:,} UZS)"
            stats["unverified_flagged"] += 1
            if not dry_run:
                tx, _ = PaymentTransactionService.create_pending(
                    transaction_id=f"legacy-unverified-{tenant.id}",
                    user_id=tenant.id,
                    tenant_id=tenant.id,
                    account_email=email,
                    plan_type=plan,
                    duration_months=1,
                    expected_amount_uzs=expected_uzs,
                    payment_method="legacy_backfill",
                )
                PaymentTransaction.update(
                    status="REQUIRES_AUDIT",
                    audit_note="Unverified legacy subscription without payment evidence"
                ).where(PaymentTransaction.id == tx.id).execute()

        report_rows.append((email, plan, decision, action_note))

    # Print summary table
    print(f"{'EMAIL':<32} | {'PLAN':<8} | {'DECISION':<20} | {'NOTE'}")
    print("-" * 100)
    for email, plan, decision, note in report_rows:
        print(f"{email:<32} | {plan:<8} | {decision:<20} | {note}")

    print("\n" + "=" * 70)
    print("  RECONCILIATION SUMMARY")
    print("=" * 70)
    print(f"Total Non-Free Tenants : {stats['total']}")
    print(f"Team Whitelisted       : {stats['team_whitelisted']}")
    print(f"CSV Matched & Paid     : {stats['csv_matched_paid']}")
    print(f"Already Verified       : {stats['already_recorded']}")
    print(f"Requires Audit         : {stats['unverified_flagged']}")
    print("=" * 70)
    if dry_run:
        print("\n[NOTE]: This was a DRY-RUN. No changes were made to the database.")
        print("To apply classification changes to the ledger, run with: --execute")
        print("NOTE: Unverified accounts are marked REQUIRES_AUDIT in the ledger and can be resolved individually via Admin UI / POST /admin/payments/reconcile.\n")


def main():
    parser = argparse.ArgumentParser(description="Reconcile legacy non-free tenants against payment records.")
    parser.add_argument("--csv-path", type=str, default="", help="Path to Atmos settlement CSV file")
    parser.add_argument("--team-emails", type=str, default="", help="Comma-separated internal team emails to whitelist")
    parser.add_argument("--execute", action="store_true", help="Execute real database ledger changes (default is dry-run)")

    args = parser.parse_args()
    dry_run = not args.execute

    run_reconciliation(
        csv_path=args.csv_path,
        team_emails_str=args.team_emails,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()
