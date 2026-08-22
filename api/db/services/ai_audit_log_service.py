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
import json
import logging
import uuid
from common.time_utils import current_timestamp
from api.db.db_models import DB, AIAuditLog, User
from api.db.services.common_service import CommonService
from api.utils.key_crypto import sanitize_sensitive_dict

logger = logging.getLogger(__name__)


class AIAuditLogService(CommonService):
    model = AIAuditLog

    @classmethod
    @DB.connection_context()
    def log_action(
        cls,
        user_id: str,
        action: str,
        target_type: str,
        target_id: str = None,
        old_val: dict | None = None,
        new_val: dict | None = None,
        details: dict | None = None,
    ) -> AIAuditLog | None:
        """
        Log an administrative AI infrastructure action.
        Guarantees that no raw API keys or passwords are written to the audit log.
        """
        try:
            log_id = uuid.uuid4().hex
            payload = details or {}
            if old_val is not None:
                payload["old_val"] = sanitize_sensitive_dict(old_val)
            if new_val is not None:
                payload["new_val"] = sanitize_sensitive_dict(new_val)
            
            sanitized_payload = sanitize_sensitive_dict(payload)
            details_json = json.dumps(sanitized_payload)

            log_entry = cls.model.create(
                id=log_id,
                user_id=user_id or "system",
                action=action,
                target_type=target_type,
                target_id=target_id or "",
                details=details_json,
                create_time=current_timestamp(),
            )
            return log_entry
        except Exception as e:
            logger.warning("Failed to write AI audit log: %s", e)
            return None

    @classmethod
    @DB.connection_context()
    def get_logs(
        cls,
        limit: int = 50,
        offset: int = 0,
        action: str | None = None,
        target_type: str | None = None,
        user_id: str | None = None,
    ) -> tuple[list[dict], int]:
        """
        Retrieve paginated AI audit logs with user email/nickname joined.
        """
        query = cls.model.select()
        if action:
            query = query.where(cls.model.action == action)
        if target_type:
            query = query.where(cls.model.target_type == target_type)
        if user_id:
            query = query.where(cls.model.user_id == user_id)

        total = query.count()
        logs = list(query.order_by(cls.model.create_time.desc()).offset(offset).limit(limit))

        # Join user info
        user_ids = {l.user_id for l in logs if l.user_id}
        users_map = {}
        if user_ids:
            for u in User.select(User.id, User.email, User.nickname).where(User.id.in_(list(user_ids))):
                users_map[u.id] = {"email": u.email, "nickname": u.nickname}

        result = []
        for l in logs:
            ld = l.to_dict()
            u_info = users_map.get(l.user_id, {"email": l.user_id, "nickname": l.user_id})
            ld["user_email"] = u_info["email"]
            ld["user_nickname"] = u_info["nickname"]
            try:
                ld["details_parsed"] = json.loads(l.details) if l.details else {}
            except Exception:
                ld["details_parsed"] = {}
            result.append(ld)

        return result, total
