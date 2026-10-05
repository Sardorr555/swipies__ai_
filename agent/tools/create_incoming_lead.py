#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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
import os
import re
from abc import ABC
from typing import Any, Dict

from agent.tools.base import ToolParamBase, ToolBase, ToolMeta
from common.connection_utils import timeout
from api.db.crm_models import CRMConnection, CRMOutbox
from api.db.services.crm_service import CRMConnectionService, CRMOutboxService, compute_lead_business_key
from api.crm.clients.bitrix24 import normalize_phone_to_e164

logger = logging.getLogger("CreateIncomingLead")


class CreateIncomingLeadParam(ToolParamBase):
    """Configuration parameters for CreateIncomingLead tool component."""

    def __init__(self):
        self.meta: ToolMeta = {
            "name": "create_incoming_lead",
            "description": "Registers an incoming sales lead from chat into connected CRM systems (amoCRM, Bitrix24). Invoke this tool when contact details (phone, name, requirements, budget) are provided.",
            "parameters": {
                "phone": {
                    "type": "string",
                    "description": "Customer phone number (international format preferred, e.g. +14155552671).",
                    "default": "{sys.query}",
                    "required": True,
                },
                "name": {
                    "type": "string",
                    "description": "Customer full name or company name.",
                    "default": "",
                    "required": False,
                },
                "note": {
                    "type": "string",
                    "description": "Customer inquiry summary, requirements, or conversation notes.",
                    "default": "",
                    "required": False,
                },
                "price": {
                    "type": "number",
                    "description": "Estimated deal value or budget.",
                    "default": 0,
                    "required": False,
                },
                "title": {
                    "type": "string",
                    "description": "Title or subject of the incoming lead/deal.",
                    "default": "",
                    "required": False,
                },
            },
        }
        super().__init__()
        self.connection_id = ""
        self.allow_anonymous = False
        self.default_phone_region = "US"

    def check(self):
        pass

    def get_input_form(self) -> dict[str, dict]:
        return {
            "phone": {"name": "Phone", "type": "line"},
            "name": {"name": "Customer Name", "type": "line", "optional": True},
            "note": {"name": "Notes / Summary", "type": "paragraph", "optional": True},
            "price": {"name": "Price / Budget", "type": "line", "optional": True},
            "title": {"name": "Lead Title", "type": "line", "optional": True},
        }


class CreateIncomingLead(ToolBase, ABC):
    """Canvas tool to validate, rate-limit, deduplicate, and enqueue incoming CRM leads."""

    component_name = "CreateIncomingLead"

    def _check_hourly_rate_limit(self, tenant_id: str, limit: int, is_anonymous: bool) -> bool:
        """Enforce tenant hourly rate limit via Redis with fail-open for auth, fail-closed for anon."""
        key = f"crm:ratelimit:lead:{tenant_id}"
        try:
            from rag.utils.redis_conn import REDIS_CONN
            if REDIS_CONN and REDIS_CONN.is_alive() and REDIS_CONN.REDIS:
                r = REDIS_CONN.REDIS
                cnt = r.incr(key)
                if cnt == 1:
                    r.expire(key, 3600)
                if cnt > limit:
                    logger.warning("Tenant '%s' exceeded hourly lead limit (%d/%d)", tenant_id, cnt, limit)
                    return False
                return True
            else:
                # Redis outage: fail-open for authenticated sales sessions, fail-closed for anonymous
                if is_anonymous:
                    logger.warning("Redis unreachable: rejecting anonymous lead creation (fail-closed)")
                    return False
                logger.warning("Redis unreachable: permitting authenticated lead creation (fail-open)")
                return True
        except Exception as e:
            logger.warning("Error checking Redis lead rate limit: %s", e)
            if is_anonymous:
                return False
            return True

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 30)))
    def _invoke(self, **kwargs) -> Dict[str, Any]:
        try:
            return self._do_invoke(**kwargs)
        finally:
            try:
                db = getattr(CRMConnection._meta, "database", None)
                if db and not db.is_closed():
                    db.close()
            except Exception:
                pass
            try:
                db_outbox = getattr(CRMOutbox._meta, "database", None)
                if db_outbox and not db_outbox.is_closed() and db_outbox != db:
                    db_outbox.close()
            except Exception:
                pass

    def _do_invoke(self, **kwargs) -> Dict[str, Any]:
        if self.check_if_canceled("CreateIncomingLead processing"):
            return {"status": "canceled"}

        # 1. Turn-level rate limit (T5.2): strictly 1 lead per turn
        turn_count = getattr(self._canvas, "_turn_lead_count", 0)
        if turn_count >= 1:
            raise ValueError("Rate limit exceeded: only 1 lead creation is permitted per conversational turn.")

        # 2. Server-side channel determination based strictly on authentication method (Point 1)
        # Client request body (custom_header.channel) is UNTRUSTED and NEVER used for authorization.
        server_channel = getattr(self._canvas, "get_channel", lambda: None)()
        if not server_channel:
            server_channel = getattr(self._canvas, "_channel", None)

        server_auth = getattr(self._canvas, "auth_type", None)
        if not server_channel and server_auth:
            auth_str = str(server_auth).strip().upper()
            if auth_str in ("AUTH_API", "API"):
                server_channel = "api"
            elif auth_str in ("AUTH_JWT", "JWT"):
                server_channel = "chat"
            elif auth_str in ("AUTH_BETA", "BETA", "EMBED"):
                server_channel = "embed"

        is_embed = (
            getattr(self._canvas, "is_embed", False)
            or getattr(self._canvas, "_is_public", False)
            or str(server_auth).strip().upper() in ("AUTH_BETA", "BETA", "EMBED")
        )

        norm_channel = str(server_channel).strip().lower() if server_channel is not None else ""
        if is_embed and norm_channel in ("api", "internal", "admin", "chat", "web", "authenticated"):
            norm_channel = "embed"

        authenticated_channels = frozenset({"internal", "web", "chat", "authenticated", "api", "admin"})
        is_authenticated = bool(norm_channel and norm_channel in authenticated_channels)
        is_anon = not is_authenticated
        if is_anon and not getattr(self._param, "allow_anonymous", False):
            raise PermissionError(
                f"Access denied: Lead creation from anonymous/public channels is forbidden unless 'allow_anonymous' is enabled in tool configuration (channel='{norm_channel}')."
            )

        # 3. Parameter validation & sanitization (T5.4)
        raw_phone = kwargs.get("phone") or ""
        if not raw_phone:
            raise ValueError("Missing required parameter 'phone'.")

        raw_name = kwargs.get("name") or "Incoming Lead"
        name = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(raw_name).strip())[:128]

        raw_note = kwargs.get("note") or kwargs.get("text") or ""
        note = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(raw_note).strip())[:2000]

        price = 0
        if "price" in kwargs and kwargs["price"] is not None:
            try:
                price = float(kwargs["price"])
            except Exception:
                price = 0

        title = str(kwargs.get("title") or f"Lead from Chat: {name}").strip()[:128]

        # 4. Tenant hourly rate limit (T5.2): 100 leads/hour
        tenant_id = getattr(self._canvas, "get_canvas_owner_tenant", lambda: None)() or getattr(self._canvas, "get_tenant_id", lambda: None)()
        if not tenant_id:
            raise ValueError("Canvas context missing valid tenant ID.")
        hourly_limit = int(os.environ.get("RAGFLOW_CRM_HOURLY_LIMIT", 100))
        if not self._check_hourly_rate_limit(tenant_id, hourly_limit, is_anon):
            raise ValueError(f"Rate limit exceeded: Tenant has reached the maximum of {hourly_limit} leads per hour.")

        # 5. Resolve active CRMConnection & configured region (Point 6)
        conn_id = getattr(self._param, "connection_id", "") or ""
        ok, conn = CRMConnectionService.resolve_active_connection(tenant_id, conn_id if conn_id else None)
        if not ok or not conn:
            if conn_id:
                raise ValueError(f"Configured CRM connection '{conn_id}' was not found for tenant '{tenant_id}'.")
            raise ValueError(f"No active CRM connection found for tenant '{tenant_id}'. Please configure a CRM connection first.")
        conn_id = conn.id

        # Enforce CRM management/write permission check
        if not CRMConnectionService.is_management_enabled(conn):
            raise PermissionError(
                f"CRM management is disabled for provider '{conn.name or conn.crm_type}'. "
                f"Data extraction and search remain active, but write actions (creating/updating leads) are disabled."
            )

        conn_cfg = CRMConnectionService.get_decrypted_config(conn)
        region = conn_cfg.get("default_phone_region") or conn_cfg.get("phone_region") or getattr(self._param, "default_phone_region", None)
        phone_e164 = normalize_phone_to_e164(str(raw_phone), default_region=region)

        # Strict E.164 regex: +[1-9][0-9]{1,14} with minimum subscriber length (total length >= 7)
        if not re.fullmatch(r"^\+[1-9]\d{1,14}$", phone_e164) or len(phone_e164) < 7:
            raise ValueError(
                f"Invalid phone number format: '{raw_phone}'. Must be a valid international phone number in E.164 format (e.g. +14155552671)."
            )

        # 6. Deduplication & Outbox enqueue (T5.5)
        b_key = compute_lead_business_key(tenant_id, conn_id, phone_e164)
        lead_payload = {
            "name": name,
            "phone": phone_e164,
            "note": note,
            "price": price,
            "title": title,
        }

        outbox_record, was_created = CRMOutboxService.enqueue(
            tenant_id=tenant_id,
            connection_id=conn_id,
            lead_data=lead_payload,
            business_key=b_key,
        )

        # Increment turn counter
        self._canvas._turn_lead_count = turn_count + 1

        msg = (
            f"Lead successfully queued for CRM dispatch (Outbox ID: {outbox_record.id})."
            if was_created
            else f"Duplicate lead identified within 24-hour window. Existing record reused (Outbox ID: {outbox_record.id})."
        )
        logger.info("CreateIncomingLead completed: tenant=%s connection=%s outbox_id=%s created=%s", tenant_id, conn_id, outbox_record.id, was_created)

        return {
            "status": "success",
            "outbox_id": str(outbox_record.id),
            "is_duplicate": not was_created,
            "message": msg,
        }
