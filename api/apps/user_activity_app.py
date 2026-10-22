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
from quart import Blueprint, request

from api.apps import current_user, login_required
from api.db.services.telemetry_service import TelemetryService
from api.utils.api_utils import get_data_error_result, get_json_result
from common.constants import RetCode

logger = logging.getLogger(__name__)

# Mounts at /v1/admin/user-activity
page_name = "admin/user-activity"
manager = Blueprint("user_activity_admin", __name__)


def require_superuser():
    if not getattr(current_user, "is_superuser", False):
        return get_json_result(
            data=False,
            message="Superuser authorization required for platform telemetry analytics.",
            code=RetCode.AUTHENTICATION_ERROR,
        )
    return None


@manager.route("/overview", methods=["GET"])
@login_required
async def get_activity_overview():
    """Retrieve high-level user activity and engagement KPI summary."""
    guard = require_superuser()
    if guard:
        return guard

    try:
        days = int(request.args.get("days", 7))
        days = max(1, min(365, days))
        overview = TelemetryService.get_overview(days=days)
        return get_json_result(data=overview)
    except Exception as e:
        logger.exception(f"Error in get_activity_overview: {e}")
        return get_json_result(data=False, message=str(e), code=RetCode.SERVER_ERROR)


@manager.route("/modules", methods=["GET"])
@login_required
async def get_modules_breakdown():
    """Retrieve time spent, visits, and click metrics grouped by platform module."""
    guard = require_superuser()
    if guard:
        return guard

    try:
        days = int(request.args.get("days", 7))
        days = max(1, min(365, days))
        breakdown = TelemetryService.get_module_breakdown(days=days)
        return get_json_result(data=breakdown)
    except Exception as e:
        logger.exception(f"Error in get_modules_breakdown: {e}")
        return get_json_result(data=False, message=str(e), code=RetCode.SERVER_ERROR)


@manager.route("/clicks", methods=["GET"])
@login_required
async def get_top_clicks():
    """Retrieve top clicked buttons, links, and UI interactive controls."""
    guard = require_superuser()
    if guard:
        return guard

    try:
        days = int(request.args.get("days", 7))
        days = max(1, min(365, days))
        limit = int(request.args.get("limit", 25))
        limit = max(5, min(100, limit))
        top_clicks = TelemetryService.get_top_clicks(days=days, limit=limit)
        return get_json_result(data=top_clicks)
    except Exception as e:
        logger.exception(f"Error in get_top_clicks: {e}")
        return get_json_result(data=False, message=str(e), code=RetCode.SERVER_ERROR)


@manager.route("/users", methods=["GET"])
@login_required
async def get_users_leaderboard():
    """Retrieve user engagement leaderboard with total time, clicks, and favored module."""
    guard = require_superuser()
    if guard:
        return guard

    try:
        days = int(request.args.get("days", 7))
        days = max(1, min(365, days))
        page = max(1, int(request.args.get("page", 1)))
        page_size = max(1, min(100, int(request.args.get("page_size", 20))))
        search = str(request.args.get("search", "")).strip()

        leaderboard = TelemetryService.get_user_leaderboard(
            days=days, search=search, page=page, page_size=page_size
        )
        return get_json_result(data=leaderboard)
    except Exception as e:
        logger.exception(f"Error in get_users_leaderboard: {e}")
        return get_json_result(data=False, message=str(e), code=RetCode.SERVER_ERROR)


@manager.route("/timeline", methods=["GET"])
@login_required
async def get_activity_timeline():
    """Retrieve 24-hour activity distribution across the specified period."""
    guard = require_superuser()
    if guard:
        return guard

    try:
        days = int(request.args.get("days", 7))
        days = max(1, min(365, days))
        timeline = TelemetryService.get_hourly_activity_timeline(days=days)
        return get_json_result(data=timeline)
    except Exception as e:
        logger.exception(f"Error in get_activity_timeline: {e}")
        return get_json_result(data=False, message=str(e), code=RetCode.SERVER_ERROR)


@manager.route("/events", methods=["GET"])
@login_required
async def get_raw_events():
    """Retrieve paginated stream of raw user activity events for drill-down and auditing."""
    guard = require_superuser()
    if guard:
        return guard

    try:
        page = max(1, int(request.args.get("page", 1)))
        page_size = max(1, min(100, int(request.args.get("page_size", 50))))
        user_id = request.args.get("user_id")
        module = request.args.get("module")
        event_type = request.args.get("event_type")

        data = TelemetryService.get_raw_events(
            page=page,
            page_size=page_size,
            user_id=user_id,
            module=module,
            event_type=event_type,
        )
        return get_json_result(data=data)
    except Exception as e:
        logger.exception(f"Error in get_raw_events: {e}")
        return get_json_result(data=False, message=str(e), code=RetCode.SERVER_ERROR)


@manager.route("/features", methods=["GET"])
@login_required
async def get_features_matrix():
    """Retrieve adoption and usage stats for all platform features and functions."""
    guard = require_superuser()
    if guard:
        return guard

    try:
        days = int(request.args.get("days", 7))
        days = max(1, min(365, days))
        data = TelemetryService.get_features_usage_matrix(days=days)
        return get_json_result(data=data)
    except Exception as e:
        logger.exception(f"Error in get_features_matrix: {e}")
        return get_json_result(data=False, message=str(e), code=RetCode.SERVER_ERROR)


@manager.route("/utm-conversions", methods=["GET"])
@login_required
async def get_utm_conversions():
    """Retrieve marketing campaign registration attribution and conversion performance."""
    guard = require_superuser()
    if guard:
        return guard

    try:
        from api.db.db_models import User
        days = int(request.args.get("days", 30))
        days = max(1, min(365, days))

        # Query users that have UTM source or campaign
        users = list(User.select().where(
            (User.utm_source.is_null(False) & (User.utm_source != "")) |
            (User.utm_campaign.is_null(False) & (User.utm_campaign != ""))
        ).dicts())

        campaigns = {}
        total_registered = 0
        for u in users:
            src = (u.get("utm_source") or "direct").strip()
            med = (u.get("utm_medium") or "none").strip()
            cmp = (u.get("utm_campaign") or "unnamed").strip()
            key = f"{src.lower()}::{med.lower()}::{cmp.lower()}"

            if key not in campaigns:
                campaigns[key] = {
                    "source": src,
                    "medium": med,
                    "campaign": cmp,
                    "registrations": 0,
                    "active_users": 0,
                    "last_signup": u.get("create_time"),
                    "users": []
                }
            c = campaigns[key]
            c["registrations"] += 1
            total_registered += 1
            if str(u.get("is_active")) == "1":
                c["active_users"] += 1
            c["users"].append({
                "id": u.get("id"),
                "email": u.get("email"),
                "nickname": u.get("nickname"),
                "created_at": u.get("create_time"),
                "is_active": str(u.get("is_active")) == "1"
            })

        campaign_list = list(campaigns.values())
        campaign_list.sort(key=lambda x: x["registrations"], reverse=True)

        return get_json_result(data={
            "total_utm_registrations": total_registered,
            "campaigns_count": len(campaign_list),
            "campaigns": campaign_list
        })
    except Exception as e:
        logger.exception(f"Error in get_utm_conversions: {e}")
        return get_json_result(data=False, message=str(e), code=RetCode.SERVER_ERROR)
