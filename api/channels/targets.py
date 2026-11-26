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

from __future__ import annotations

from typing import Any


def validate_agent_target(agent_id: str, tenant_id: str, *, service: Any = None) -> str | None:
    """Validate that a channel tenant may run the selected Agent."""
    if service is None:
        from api.db.services.canvas_service import UserCanvasService

        service = UserCanvasService

    found, agent = service.get_by_id(agent_id)
    if not found or getattr(agent, "canvas_category", "") != "agent_canvas":
        return "not_found"
    if not service.accessible(agent_id, tenant_id):
        return "forbidden"
    return None


def mask_secret(secret_str: str) -> str:
    if not secret_str or not isinstance(secret_str, str):
        return ""
    if ":" in secret_str:
        prefix, rest = secret_str.split(":", 1)
        suffix = rest[-4:] if len(rest) >= 4 else "***"
        return f"{prefix}:***{suffix}"
    if len(secret_str) <= 8:
        return "***"
    return f"{secret_str[:3]}***{secret_str[-4:]}"


def sanitize_channel_config(config: dict, channel: str = "") -> dict:
    if not isinstance(config, dict):
        return {}
    res = {}
    for k, v in config.items():
        if k == "credential" and isinstance(v, dict):
            cred = dict(v)
            has_token = bool(cred.get("token") or cred.get("bot_token") or cred.get("secret"))
            masked_cred = {}
            for cred_k, cred_v in cred.items():
                if cred_k in ("token", "bot_token", "secret", "password", "api_key", "client_secret"):
                    masked_cred[cred_k] = mask_secret(cred_v)
                else:
                    masked_cred[cred_k] = cred_v
            masked_cred["credential_configured"] = has_token
            res["credential"] = masked_cred
            res["credential_configured"] = has_token
        else:
            res[k] = v
    if "credential_configured" not in res:
        res["credential_configured"] = bool((config.get("credential") or {}).get("token"))
    return res


def channel_to_safe_dict(channel_dict: dict) -> dict:
    if not isinstance(channel_dict, dict):
        return {}
    d = dict(channel_dict)
    ch_type = d.get("channel", "")
    cfg = d.get("config") or {}
    d["config"] = sanitize_channel_config(cfg, ch_type)
    d["credential_configured"] = d["config"].get("credential_configured", False)
    return d
