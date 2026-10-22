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

from api.apps import current_user
from api.db.services.telemetry_service import TelemetryService
from api.utils.api_utils import get_data_error_result, get_json_result, get_request_json
from common.constants import RetCode

logger = logging.getLogger(__name__)

# Mounts at /v1/telemetry
page_name = "telemetry"
manager = Blueprint("telemetry", __name__)


@manager.route("/ping", methods=["GET"])
async def telemetry_ping():
    return get_json_result(data={"status": "active", "service": "telemetry_collector"})


@manager.route("/events", methods=["POST"])
async def ingest_telemetry_events():
    """
    Ingest user telemetry events in batch from web client.
    Permits both authenticated users and anonymous visitors (with session_id).
    """
    try:
        req = await get_request_json()
        if not req or not isinstance(req, dict):
            return get_data_error_result(message="Invalid payload, JSON object expected.")

        events = req.get("events")
        if not events or not isinstance(events, list):
            return get_data_error_result(message="Events list is required.")

        user_id = None
        tenant_id = None
        try:
            if hasattr(current_user, "is_authenticated") and current_user.is_authenticated:
                user_id = getattr(current_user, "id", None)
                tenant_id = getattr(current_user, "tenant_id", None) or user_id
        except Exception:
            pass

        # Extract IP and User-Agent
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()
        user_agent = request.headers.get("User-Agent", "")

        inserted = TelemetryService.record_batch_events(
            events=events,
            user_id=user_id,
            tenant_id=tenant_id,
            ip=ip,
            user_agent=user_agent,
        )

        return get_json_result(data={"saved": inserted, "status": "ok"})
    except Exception as e:
        logger.exception(f"Error ingesting telemetry events: {e}")
        return get_json_result(
            data={"saved": 0},
            message=f"Telemetry error: {str(e)}",
            code=RetCode.SERVER_ERROR,
        )
