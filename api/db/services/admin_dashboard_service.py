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
import logging
from datetime import datetime, timedelta, timezone
from peewee import fn

from api.db.db_models import DB, User, Tenant, PaymentTransaction, PaymentOrder
from api.db.services.common_service import CommonService
from common.time_utils import datetime_format


class AdminDashboardService(CommonService):
    """Unified Analytics & Performance Metrics Engine for Admin Dashboard."""

    EXCHANGE_RATE_UZS_PER_USD = 12800.0

    @classmethod
    @DB.connection_context()
    def get_dashboard_overview(cls) -> dict:
        """Calculate complete user, activity, revenue and subscription analytics."""
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)

        # ---------------------------------------------------------------------
        # 1. USER METRICS
        # ---------------------------------------------------------------------
        all_users = list(User.select())
        total_users = len(all_users)

        active_users_count = sum(1 for u in all_users if str(getattr(u, "is_active", "1")) == "1" and str(getattr(u, "status", "1")) == "1")
        inactive_users_count = total_users - active_users_count
        superuser_count = sum(1 for u in all_users if getattr(u, "is_superuser", False))

        new_today = 0
        new_this_week = 0
        new_this_month = 0

        # Login channel distribution & Activity
        login_channels = {}
        active_today_count = 0
        active_7d_count = 0
        active_30d_count = 0

        # 30-Day Registration Trend map
        date_reg_map = { (now - timedelta(days=i)).strftime("%Y-%m-%d"): 0 for i in range(29, -1, -1) }

        # User map for fast tenant plan lookup
        user_tenant_plans = {}
        try:
            for t in list(Tenant.select(Tenant.id, Tenant.plan_type)):
                user_tenant_plans[str(t.id)] = (t.plan_type or "free").lower()
        except Exception as e:
            logging.warning(f"Error reading Tenant plans: {e}")

        for u in all_users:
            c_date = getattr(u, "create_date", None)
            if c_date:
                if isinstance(c_date, datetime):
                    dt = c_date
                else:
                    try:
                        dt = datetime.strptime(str(c_date)[:19], "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        dt = None

                if dt:
                    if dt >= today_start:
                        new_today += 1
                    if dt >= seven_days_ago:
                        new_this_week += 1
                    if dt >= thirty_days_ago:
                        new_this_month += 1

                    day_str = dt.strftime("%Y-%m-%d")
                    if day_str in date_reg_map:
                        date_reg_map[day_str] += 1

            # Activity & Login time
            l_time = getattr(u, "last_login_time", None)
            if l_time:
                if isinstance(l_time, datetime):
                    ldt = l_time
                else:
                    try:
                        ldt = datetime.strptime(str(l_time)[:19], "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        ldt = None

                if ldt:
                    if ldt >= today_start:
                        active_today_count += 1
                    if ldt >= seven_days_ago:
                        active_7d_count += 1
                    if ldt >= thirty_days_ago:
                        active_30d_count += 1

            # Login channel
            ch = (getattr(u, "login_channel", None) or "email").lower().strip()
            if not ch:
                ch = "email"
            login_channels[ch] = login_channels.get(ch, 0) + 1

        daily_registration_trend = [{"date": k, "count": v} for k, v in date_reg_map.items()]

        # ---------------------------------------------------------------------
        # 2. REVENUE & PAYMENT METRICS
        # ---------------------------------------------------------------------
        paid_records = list(
            PaymentTransaction.select(
                PaymentTransaction.id,
                PaymentTransaction.user_id,
                PaymentTransaction.paid_amount_uzs,
                PaymentTransaction.plan_type,
                PaymentTransaction.status,
                PaymentTransaction.create_date,
                PaymentTransaction.transaction_id,
            )
        )

        existing_tx_ids = set()
        for r in paid_records:
            if r.id: existing_tx_ids.add(str(r.id))
            if r.transaction_id: existing_tx_ids.add(str(r.transaction_id))

        all_orders = []
        try:
            all_orders = list(PaymentOrder.select())
        except Exception as ex:
            logging.warning(f"Error fetching PaymentOrder table: {ex}")

        # Revenue aggregators
        total_revenue_uzs = 0
        rev_today_uzs = 0
        rev_7d_uzs = 0
        rev_30d_uzs = 0

        paying_users = set()
        paid_transactions_count = 0

        # Status distribution
        status_counts = {}

        # Plan breakdown
        plan_breakdown = {}

        # 30-Day Revenue Trend map
        date_rev_map = { (now - timedelta(days=i)).strftime("%Y-%m-%d"): {"revenue_uzs": 0, "count": 0} for i in range(29, -1, -1) }

        # Process PaymentTransaction rows
        for r in paid_records:
            st = (r.status or "PENDING").upper()
            status_counts[st] = status_counts.get(st, 0) + 1

            pt = (r.plan_type or "other").lower()
            if pt not in plan_breakdown:
                plan_breakdown[pt] = {"count": 0, "revenue_uzs": 0, "paid_count": 0}
            plan_breakdown[pt]["count"] += 1

            if st == "PAID":
                amt = int(r.paid_amount_uzs or 0)
                total_revenue_uzs += amt
                paid_transactions_count += 1
                if r.user_id: paying_users.add(str(r.user_id))

                plan_breakdown[pt]["paid_count"] += 1
                plan_breakdown[pt]["revenue_uzs"] += amt

                c_date = r.create_date
                if isinstance(c_date, datetime):
                    dt = c_date
                elif c_date:
                    try:
                        dt = datetime.strptime(str(c_date)[:19], "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        dt = None
                else:
                    dt = None

                if dt:
                    if dt >= today_start:
                        rev_today_uzs += amt
                    if dt >= seven_days_ago:
                        rev_7d_uzs += amt
                    if dt >= thirty_days_ago:
                        rev_30d_uzs += amt

                    day_str = dt.strftime("%Y-%m-%d")
                    if day_str in date_rev_map:
                        date_rev_map[day_str]["revenue_uzs"] += amt
                        date_rev_map[day_str]["count"] += 1

        # Process PaymentOrder rows (excluding deduplicated IDs)
        for o in all_orders:
            oid_str = str(o.id)
            if oid_str in existing_tx_ids or str(getattr(o, "external_transaction_id", "") or "") in existing_tx_ids:
                continue

            st = (o.status or "PENDING").upper()
            if st in ["INIT", "CREATED", "PROCESSING"]:
                st = "PENDING"
            status_counts[st] = status_counts.get(st, 0) + 1

            pt = (o.plan_id or o.purpose or "deposit").lower()
            if getattr(o, "purpose", "") == "advertiser_deposit":
                pt = "ads_deposit"

            if pt not in plan_breakdown:
                plan_breakdown[pt] = {"count": 0, "revenue_uzs": 0, "paid_count": 0}
            plan_breakdown[pt]["count"] += 1

            if st == "PAID":
                amt = int(o.amount_uzs or 0)
                total_revenue_uzs += amt
                paid_transactions_count += 1
                if o.user_id: paying_users.add(str(o.user_id))

                plan_breakdown[pt]["paid_count"] += 1
                plan_breakdown[pt]["revenue_uzs"] += amt

                c_time = getattr(o, "create_time", None)
                dt = None
                if isinstance(c_time, datetime):
                    dt = c_time
                elif isinstance(c_time, (int, float)):
                    try:
                        dt = datetime.fromtimestamp(c_time / 1000.0 if c_time > 1e11 else c_time)
                    except Exception:
                        dt = None

                if dt:
                    if dt >= today_start:
                        rev_today_uzs += amt
                    if dt >= seven_days_ago:
                        rev_7d_uzs += amt
                    if dt >= thirty_days_ago:
                        rev_30d_uzs += amt

                    day_str = dt.strftime("%Y-%m-%d")
                    if day_str in date_rev_map:
                        date_rev_map[day_str]["revenue_uzs"] += amt
                        date_rev_map[day_str]["count"] += 1

        daily_revenue_trend = [
            {"date": k, "revenue_uzs": v["revenue_uzs"], "revenue_usd": round(v["revenue_uzs"] / cls.EXCHANGE_RATE_UZS_PER_USD, 2), "count": v["count"]}
            for k, v in date_rev_map.items()
        ]

        # Weekly trend (last 8 weeks)
        weekly_revenue_trend = []
        for w in range(7, -1, -1):
            w_start = now - timedelta(days=(w + 1) * 7)
            w_end = now - timedelta(days=w * 7)
            w_rev = sum(
                r.paid_amount_uzs or 0 for r in paid_records
                if (r.status or "").upper() == "PAID" and r.create_date and w_start <= (r.create_date if isinstance(r.create_date, datetime) else datetime.fromisoformat(str(r.create_date)[:19])) < w_end
            )
            weekly_revenue_trend.append({
                "week": f"{w_start.strftime('%d.%m')} - {w_end.strftime('%d.%m')}",
                "revenue_uzs": w_rev,
                "revenue_usd": round(w_rev / cls.EXCHANGE_RATE_UZS_PER_USD, 2),
            })

        # Monthly trend (last 6 months)
        monthly_revenue_trend = []
        for m in range(5, -1, -1):
            m_dt = now - timedelta(days=m * 30)
            m_label = m_dt.strftime("%b %Y")
            m_start = datetime(m_dt.year, m_dt.month, 1)
            # End of month
            if m_dt.month == 12:
                m_end = datetime(m_dt.year + 1, 1, 1)
            else:
                m_end = datetime(m_dt.year, m_dt.month + 1, 1)

            m_rev = sum(
                r.paid_amount_uzs or 0 for r in paid_records
                if (r.status or "").upper() == "PAID" and r.create_date and m_start <= (r.create_date if isinstance(r.create_date, datetime) else datetime.fromisoformat(str(r.create_date)[:19])) < m_end
            )
            monthly_revenue_trend.append({
                "month": m_label,
                "revenue_uzs": m_rev,
                "revenue_usd": round(m_rev / cls.EXCHANGE_RATE_UZS_PER_USD, 2),
            })

        paying_users_count = len(paying_users)
        arppu_uzs = round(total_revenue_uzs / paying_users_count, 0) if paying_users_count > 0 else 0
        conversion_rate_pct = round((paying_users_count / total_users * 100.0), 2) if total_users > 0 else 0.0

        # ---------------------------------------------------------------------
        # 3. RECENT ACTIVITY LISTS
        # ---------------------------------------------------------------------
        recent_users_list = []
        sorted_users = sorted(all_users, key=lambda x: str(getattr(x, "create_date", "") or ""), reverse=True)[:10]
        for u in sorted_users:
            recent_users_list.append({
                "id": u.id,
                "nickname": u.nickname or "User",
                "email": u.email,
                "create_date": str(u.create_date or "")[:19],
                "is_active": str(getattr(u, "is_active", "1")) == "1",
                "is_superuser": getattr(u, "is_superuser", False),
                "plan_type": user_tenant_plans.get(str(u.id), "free"),
                "last_login_time": str(u.last_login_time or "")[:19],
            })

        recent_payments_list = []
        # Sort transactions
        all_tx_combined = []
        for r in paid_records:
            all_tx_combined.append({
                "id": str(r.id),
                "user_id": str(r.user_id or ""),
                "amount_uzs": int(r.paid_amount_uzs or 0),
                "plan_type": r.plan_type or "standard",
                "status": (r.status or "PENDING").upper(),
                "create_date": str(r.create_date or "")[:19],
                "gateway": "atmos",
            })
        for o in all_orders:
            if str(o.id) not in existing_tx_ids:
                all_tx_combined.append({
                    "id": str(o.id),
                    "user_id": str(o.user_id or ""),
                    "amount_uzs": int(o.amount_uzs or 0),
                    "plan_type": o.plan_id or o.purpose or "deposit",
                    "status": (o.status or "PENDING").upper(),
                    "create_date": str(getattr(o, "create_date", "") or "")[:19],
                    "gateway": getattr(o, "gateway", "atmos") or "atmos",
                })

        all_tx_combined.sort(key=lambda x: x["create_date"], reverse=True)
        recent_payments_list = all_tx_combined[:10]

        # Attach email to recent payments
        user_email_map = {str(u.id): u.email for u in all_users}
        for tx in recent_payments_list:
            tx["user_email"] = user_email_map.get(tx["user_id"], tx["user_id"])

        return {
            # User statistics
            "user_stats": {
                "total_users": total_users,
                "active_users": active_users_count,
                "inactive_users": inactive_users_count,
                "superuser_count": superuser_count,
                "new_users_today": new_today,
                "new_users_this_week": new_this_week,
                "new_users_this_month": new_this_month,
                "active_today": active_today_count,
                "active_7d": active_7d_count,
                "active_30d": active_30d_count,
                "login_channels": login_channels,
                "daily_registration_trend": daily_registration_trend,
            },
            # Revenue & Financial statistics
            "revenue_stats": {
                "total_revenue_uzs": total_revenue_uzs,
                "total_revenue_usd": round(total_revenue_uzs / cls.EXCHANGE_RATE_UZS_PER_USD, 2),
                "revenue_today_uzs": rev_today_uzs,
                "revenue_today_usd": round(rev_today_uzs / cls.EXCHANGE_RATE_UZS_PER_USD, 2),
                "revenue_this_week_uzs": rev_7d_uzs,
                "revenue_this_week_usd": round(rev_7d_uzs / cls.EXCHANGE_RATE_UZS_PER_USD, 2),
                "revenue_this_month_uzs": rev_30d_uzs,
                "revenue_this_month_usd": round(rev_30d_uzs / cls.EXCHANGE_RATE_UZS_PER_USD, 2),
                "paying_users_count": paying_users_count,
                "paid_transactions_count": paid_transactions_count,
                "arppu_uzs": arppu_uzs,
                "conversion_rate_pct": conversion_rate_pct,
                "daily_revenue_trend": daily_revenue_trend,
                "weekly_revenue_trend": weekly_revenue_trend,
                "monthly_revenue_trend": monthly_revenue_trend,
            },
            # Subscriptions & Distribution
            "subscription_stats": {
                "plan_breakdown": plan_breakdown,
                "status_distribution": status_counts,
            },
            # Feeds
            "recent_users": recent_users_list,
            "recent_payments": recent_payments_list,
        }
