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
import time
from datetime import datetime, timedelta
from peewee import fn

from api.db.db_models import DB, User
from api.db.telemetry_models import UserActivityEvent
from common.misc_utils import get_uuid


MODULE_LABELS = {
    "chat": "AI Chat & Assistent",
    "datasets": "Bilimlar Bazasi & Datasetlar",
    "agent_canvas": "Agent Canvas & Workflow",
    "crm": "CRM & ERP Integratsiyalari",
    "search": "Hujjatlar Qidiruvi (Search)",
    "files_skills": "Fayllar & Ko'nikmalar",
    "settings": "Sozlamalar & Hisob",
    "ads": "Swipies Reklama Tizimi",
    "admin": "Admin Boshqaruv Paneli",
    "other": "Boshqa Bo'limlar",
}

# Redaction blocklist to guarantee no tokens or sensitive text leak into telemetry
SENSITIVE_KEYWORDS = {
    "password", "secret", "token", "authorization", "bearer",
    "api_key", "credential", "private", "credit_card", "cvv"
}


class TelemetryService:
    """Enterprise-grade service for user activity telemetry, behavior analytics and click-stream aggregation."""

    @classmethod
    def sanitize_metadata(cls, meta: dict) -> dict:
        """Strip any sensitive keys or potential tokens from event metadata."""
        if not isinstance(meta, dict):
            return {}
        cleaned = {}
        for k, v in meta.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in SENSITIVE_KEYWORDS):
                continue
            if isinstance(v, str) and len(v) > 500:
                cleaned[k] = v[:500] + "...[TRUNCATED]"
            elif isinstance(v, (int, float, bool, str, list, dict)):
                cleaned[k] = v
        return cleaned

    @classmethod
    @DB.connection_context()
    def record_batch_events(
        cls,
        events: list[dict],
        user_id: str | None = None,
        tenant_id: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> int:
        """Validate, sanitize and bulk-insert user activity events."""
        if not events or not isinstance(events, list):
            return 0

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        hour_of_day = now.hour
        now_ts = int(time.time() * 1000)

        rows = []
        for raw in events[:100]:  # Limit max 100 events per batch
            if not isinstance(raw, dict):
                continue

            session_id = str(raw.get("session_id") or "sess_anon").strip()[:64]
            event_type = str(raw.get("event_type") or "click").strip()[:32]
            module = str(raw.get("module") or "other").strip()[:64]
            page_route = str(raw.get("page_route") or "/").strip()[:255]
            action_category = str(raw.get("action_category") or "interaction").strip()[:64]
            action_name = str(raw.get("action_name") or "unknown_action").strip()[:128]
            
            element_tag = str(raw.get("element_tag") or "").strip()[:32] or None
            element_id = str(raw.get("element_id") or "").strip()[:128] or None
            
            # Clean element label (button title/text)
            raw_label = str(raw.get("element_label") or "").strip()
            element_label = raw_label[:255] if raw_label else None

            duration = 0.0
            try:
                duration = max(0.0, float(raw.get("duration_seconds", 0.0)))
                if duration > 86400:  # Cap crazy runaway timer at 24 hours
                    duration = 86400.0
            except (ValueError, TypeError):
                duration = 0.0

            clean_meta = cls.sanitize_metadata(raw.get("metadata") or {})

            rows.append({
                "id": get_uuid(),
                "user_id": user_id or raw.get("user_id") or None,
                "tenant_id": tenant_id or raw.get("tenant_id") or None,
                "session_id": session_id,
                "event_type": event_type,
                "module": module,
                "page_route": page_route,
                "action_category": action_category,
                "action_name": action_name,
                "element_tag": element_tag,
                "element_id": element_id,
                "element_label": element_label,
                "duration_seconds": duration,
                "metadata": clean_meta,
                "ip": (ip or "").strip()[:64] or None,
                "user_agent": (user_agent or "").strip()[:255] or None,
                "date_str": date_str,
                "hour_of_day": hour_of_day,
                "timestamp": now_ts,
            })

        if rows:
            with DB.atomic():
                UserActivityEvent.insert_many(rows).execute()
        return len(rows)

    @classmethod
    @DB.connection_context()
    def get_overview(cls, days: int = 7) -> dict:
        """High-level summary of active users, time spent, click activity, and top modules."""
        now = datetime.now()
        start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        today_str = now.strftime("%Y-%m-%d")

        query = UserActivityEvent.select().where(UserActivityEvent.date_str >= start_date)

        # 1. Active Users (DAU & Period Active)
        dau = (
            UserActivityEvent.select(fn.COUNT(fn.DISTINCT(UserActivityEvent.user_id)))
            .where((UserActivityEvent.date_str == today_str) & (UserActivityEvent.user_id.is_null(False)))
            .scalar() or 0
        )
        
        active_users_period = (
            UserActivityEvent.select(fn.COUNT(fn.DISTINCT(UserActivityEvent.user_id)))
            .where((UserActivityEvent.date_str >= start_date) & (UserActivityEvent.user_id.is_null(False)))
            .scalar() or 0
        )

        # 2. Total actions and clicks
        total_actions = query.count()
        total_clicks = query.where(UserActivityEvent.event_type == "click").count()
        total_page_views = query.where(UserActivityEvent.event_type == "page_view").count()

        # 3. Total Time spent
        total_seconds = (
            UserActivityEvent.select(fn.SUM(UserActivityEvent.duration_seconds))
            .where(UserActivityEvent.date_str >= start_date)
            .scalar() or 0.0
        )

        avg_time_per_user = (
            round(total_seconds / active_users_period, 1)
            if active_users_period > 0
            else 0.0
        )

        # 4. Top Module
        top_module_row = (
            UserActivityEvent.select(
                UserActivityEvent.module,
                fn.COUNT(UserActivityEvent.id).alias("event_count"),
                fn.SUM(UserActivityEvent.duration_seconds).alias("total_time"),
            )
            .where(UserActivityEvent.date_str >= start_date)
            .group_by(UserActivityEvent.module)
            .order_by(fn.SUM(UserActivityEvent.duration_seconds).desc(), fn.COUNT(UserActivityEvent.id).desc())
            .first()
        )

        top_module = top_module_row.module if top_module_row else "chat"
        top_module_name = MODULE_LABELS.get(top_module, top_module)

        return {
            "period_days": days,
            "dau": dau,
            "active_users_period": active_users_period,
            "total_actions": total_actions,
            "total_clicks": total_clicks,
            "total_page_views": total_page_views,
            "total_time_spent_seconds": round(total_seconds, 1),
            "total_time_spent_hours": round(total_seconds / 3600.0, 2),
            "avg_time_per_user_seconds": avg_time_per_user,
            "avg_time_per_user_minutes": round(avg_time_per_user / 60.0, 1),
            "top_module": top_module,
            "top_module_name": top_module_name,
        }

    @classmethod
    @DB.connection_context()
    def get_module_breakdown(cls, days: int = 7) -> list[dict]:
        """Calculates breakdown of visits, dwell time, and interactions per platform module."""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        stats = (
            UserActivityEvent.select(
                UserActivityEvent.module,
                fn.COUNT(UserActivityEvent.id).alias("total_events"),
                fn.SUM(UserActivityEvent.duration_seconds).alias("total_time"),
                fn.COUNT(fn.DISTINCT(UserActivityEvent.user_id)).alias("unique_users"),
                fn.COUNT(fn.DISTINCT(UserActivityEvent.session_id)).alias("unique_sessions"),
            )
            .where(UserActivityEvent.date_str >= start_date)
            .group_by(UserActivityEvent.module)
            .order_by(fn.SUM(UserActivityEvent.duration_seconds).desc())
        )

        total_platform_time = sum((s.total_time or 0.0) for s in stats) or 1.0

        res = []
        for row in stats:
            mod_code = row.module
            time_sec = float(row.total_time or 0.0)
            events_count = int(row.total_events or 0)
            share = round((time_sec / total_platform_time) * 100.0, 1)

            # count page views vs clicks for this module
            clicks = (
                UserActivityEvent.select()
                .where(
                    (UserActivityEvent.date_str >= start_date)
                    & (UserActivityEvent.module == mod_code)
                    & (UserActivityEvent.event_type == "click")
                )
                .count()
            )
            page_views = (
                UserActivityEvent.select()
                .where(
                    (UserActivityEvent.date_str >= start_date)
                    & (UserActivityEvent.module == mod_code)
                    & (UserActivityEvent.event_type == "page_view")
                )
                .count()
            )

            avg_dwell = round(time_sec / max(1, page_views), 1)

            res.append({
                "module": mod_code,
                "module_name": MODULE_LABELS.get(mod_code, mod_code),
                "total_events": events_count,
                "page_views": page_views,
                "clicks": clicks,
                "total_time_seconds": round(time_sec, 1),
                "total_time_minutes": round(time_sec / 60.0, 1),
                "avg_dwell_seconds": avg_dwell,
                "unique_users": int(row.unique_users or 0),
                "unique_sessions": int(row.unique_sessions or 0),
                "share_percentage": share,
            })
        return res

    @classmethod
    @DB.connection_context()
    def get_top_clicks(cls, days: int = 7, limit: int = 25) -> list[dict]:
        """Rank user clicks on buttons, navigation items, and UI controls."""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        clicks = (
            UserActivityEvent.select(
                UserActivityEvent.element_label,
                UserActivityEvent.element_id,
                UserActivityEvent.element_tag,
                UserActivityEvent.module,
                UserActivityEvent.action_name,
                UserActivityEvent.page_route,
                fn.COUNT(UserActivityEvent.id).alias("click_count"),
                fn.COUNT(fn.DISTINCT(UserActivityEvent.user_id)).alias("unique_users"),
            )
            .where(
                (UserActivityEvent.date_str >= start_date)
                & (UserActivityEvent.event_type == "click")
                & (
                    (UserActivityEvent.element_label.is_null(False))
                    | (UserActivityEvent.element_id.is_null(False))
                )
            )
            .group_by(
                UserActivityEvent.element_label,
                UserActivityEvent.element_id,
                UserActivityEvent.element_tag,
                UserActivityEvent.module,
                UserActivityEvent.action_name,
                UserActivityEvent.page_route,
            )
            .order_by(fn.COUNT(UserActivityEvent.id).desc())
            .limit(limit)
        )

        res = []
        for r in clicks:
            label = r.element_label or r.element_id or r.action_name or "Tugma"
            res.append({
                "label": label,
                "element_id": r.element_id,
                "element_tag": r.element_tag or "button",
                "module": r.module,
                "module_name": MODULE_LABELS.get(r.module, r.module),
                "action_name": r.action_name,
                "page_route": r.page_route,
                "click_count": int(r.click_count or 0),
                "unique_users": int(r.unique_users or 0),
            })
        return res

    @classmethod
    @DB.connection_context()
    def get_user_leaderboard(cls, days: int = 7, search: str = "", page: int = 1, page_size: int = 20) -> dict:
        """User engagement leaderboard showing total time, actions, clicks, and preferred module."""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        query = (
            UserActivityEvent.select(
                UserActivityEvent.user_id,
                fn.COUNT(UserActivityEvent.id).alias("total_actions"),
                fn.SUM(UserActivityEvent.duration_seconds).alias("total_time"),
                fn.MAX(UserActivityEvent.timestamp).alias("last_active_ts"),
            )
            .where(
                (UserActivityEvent.date_str >= start_date)
                & (UserActivityEvent.user_id.is_null(False))
            )
            .group_by(UserActivityEvent.user_id)
        )

        total_users = query.count()
        paginated_rows = (
            query.order_by(fn.SUM(UserActivityEvent.duration_seconds).desc(), fn.COUNT(UserActivityEvent.id).desc())
            .paginate(page, page_size)
        )

        user_ids = [r.user_id for r in paginated_rows if r.user_id]
        user_info_map = {}
        if user_ids:
            users = User.select(User.id, User.email, User.nickname, User.avatar, User.last_login_time).where(User.id.in_(user_ids))
            for u in users:
                user_info_map[u.id] = {
                    "email": u.email,
                    "nickname": u.nickname or u.email.split("@")[0],
                    "avatar": u.avatar,
                    "last_login_time": str(u.last_login_time) if u.last_login_time else None,
                }

        items = []
        for r in paginated_rows:
            uid = r.user_id
            u_info = user_info_map.get(uid, {
                "email": f"user_{uid[:8]}",
                "nickname": f"User {uid[:6]}",
                "avatar": None,
                "last_login_time": None,
            })

            if search and search.lower() not in u_info["email"].lower() and search.lower() not in u_info["nickname"].lower():
                continue

            # Find user's favorite module
            fav_mod_row = (
                UserActivityEvent.select(
                    UserActivityEvent.module,
                    fn.SUM(UserActivityEvent.duration_seconds).alias("mod_time"),
                )
                .where(
                    (UserActivityEvent.date_str >= start_date)
                    & (UserActivityEvent.user_id == uid)
                )
                .group_by(UserActivityEvent.module)
                .order_by(fn.SUM(UserActivityEvent.duration_seconds).desc())
                .first()
            )
            fav_module = fav_mod_row.module if fav_mod_row else "chat"

            # Clicks count
            clicks_count = (
                UserActivityEvent.select()
                .where(
                    (UserActivityEvent.date_str >= start_date)
                    & (UserActivityEvent.user_id == uid)
                    & (UserActivityEvent.event_type == "click")
                )
                .count()
            )

            tot_sec = float(r.total_time or 0.0)
            items.append({
                "user_id": uid,
                "email": u_info["email"],
                "nickname": u_info["nickname"],
                "avatar": u_info["avatar"],
                "total_actions": int(r.total_actions or 0),
                "total_clicks": clicks_count,
                "total_time_seconds": round(tot_sec, 1),
                "total_time_minutes": round(tot_sec / 60.0, 1),
                "favorite_module": fav_module,
                "favorite_module_name": MODULE_LABELS.get(fav_module, fav_module),
                "last_active_timestamp": r.last_active_ts,
            })

        return {
            "total": total_users,
            "page": page,
            "page_size": page_size,
            "items": items,
        }

    @classmethod
    @DB.connection_context()
    def get_hourly_activity_timeline(cls, days: int = 7) -> list[dict]:
        """Activity volume by hour of the day across the specified period."""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        stats = (
            UserActivityEvent.select(
                UserActivityEvent.hour_of_day,
                fn.COUNT(UserActivityEvent.id).alias("actions"),
                fn.SUM(UserActivityEvent.duration_seconds).alias("time_seconds"),
                fn.COUNT(fn.DISTINCT(UserActivityEvent.user_id)).alias("users"),
            )
            .where(UserActivityEvent.date_str >= start_date)
            .group_by(UserActivityEvent.hour_of_day)
            .order_by(UserActivityEvent.hour_of_day.asc())
        )

        hours_map = {h: {"hour": f"{h:02d}:00", "actions": 0, "users": 0, "time_minutes": 0} for h in range(24)}
        for r in stats:
            h = int(r.hour_of_day)
            if h in hours_map:
                hours_map[h]["actions"] = int(r.actions or 0)
                hours_map[h]["users"] = int(r.users or 0)
                hours_map[h]["time_minutes"] = round(float(r.time_seconds or 0.0) / 60.0, 1)

        return list(hours_map.values())

    @classmethod
    @DB.connection_context()
    def get_raw_events(
        cls,
        page: int = 1,
        page_size: int = 50,
        user_id: str | None = None,
        module: str | None = None,
        event_type: str | None = None,
    ) -> dict:
        """Paginated list of raw activity events for audit and drill-down."""
        query = UserActivityEvent.select()
        if user_id:
            query = query.where(UserActivityEvent.user_id == user_id)
        if module and module != "all":
            query = query.where(UserActivityEvent.module == module)
        if event_type and event_type != "all":
            query = query.where(UserActivityEvent.event_type == event_type)

        total = query.count()
        events = query.order_by(UserActivityEvent.timestamp.desc()).paginate(page, page_size)

        items = []
        for e in events:
            items.append({
                "id": e.id,
                "user_id": e.user_id,
                "session_id": e.session_id,
                "event_type": e.event_type,
                "module": e.module,
                "module_name": MODULE_LABELS.get(e.module, e.module),
                "page_route": e.page_route,
                "action_category": e.action_category,
                "action_name": e.action_name,
                "element_tag": e.element_tag,
                "element_id": e.element_id,
                "element_label": e.element_label,
                "duration_seconds": e.duration_seconds,
                "date_str": e.date_str,
                "hour_of_day": e.hour_of_day,
                "timestamp": e.timestamp,
            })

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }

    @classmethod
    @DB.connection_context()
    def get_features_usage_matrix(cls, days: int = 7) -> list[dict]:
        """Calculates adoption, invocation counts and user reach for each platform feature."""
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        stats = (
            UserActivityEvent.select(
                UserActivityEvent.action_name,
                UserActivityEvent.module,
                UserActivityEvent.element_id,
                fn.COUNT(UserActivityEvent.id).alias("invocations"),
                fn.COUNT(fn.DISTINCT(UserActivityEvent.user_id)).alias("unique_users"),
                fn.MAX(UserActivityEvent.timestamp).alias("last_used"),
            )
            .where(
                (UserActivityEvent.date_str >= start_date)
                & (UserActivityEvent.action_category == "feature_usage")
            )
            .group_by(UserActivityEvent.action_name, UserActivityEvent.module, UserActivityEvent.element_id)
            .order_by(fn.COUNT(UserActivityEvent.id).desc())
        )

        res = []
        for r in stats:
            res.append({
                "feature_name": r.action_name or "Noma'lum Funksiya",
                "module": r.module,
                "module_name": MODULE_LABELS.get(r.module, r.module),
                "endpoint": r.element_id,
                "invocations": int(r.invocations or 0),
                "unique_users": int(r.unique_users or 0),
                "last_used": r.last_used,
            })
        return res

