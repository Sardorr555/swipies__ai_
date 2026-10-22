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
import time
from datetime import datetime
from peewee import (
    BigIntegerField,
    CharField,
    FloatField,
    IntegerField,
    TextField,
)
from playhouse.postgres_ext import JSONField

from api.db.db_models import DataBaseModel, DB
from common.misc_utils import get_uuid


class UserActivityEvent(DataBaseModel):
    """
    Fine-grained platform telemetry and user behavior event model.
    Captures user route visits, dwell time, element clicks, and platform feature usage.
    """
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=32, null=True, index=True, help_text="Authenticated user ID or null for anonymous")
    tenant_id = CharField(max_length=32, null=True, index=True, help_text="Tenant ID associated with the user")
    session_id = CharField(max_length=64, null=False, index=True, help_text="Client session identifier")
    
    # Event classification
    event_type = CharField(max_length=32, null=False, index=True, help_text="page_view | click | action | heartbeat")
    module = CharField(max_length=64, null=False, index=True, help_text="Platform module: chat, datasets, agent_canvas, crm, search, files_skills, settings, ads, admin")
    page_route = CharField(max_length=255, null=False, index=True, help_text="Relative URI path e.g. /chats, /dataset/files")
    
    # Detailed action properties
    action_category = CharField(max_length=64, null=True, index=True, help_text="navigation | interaction | chat | upload | search | crm | config")
    action_name = CharField(max_length=128, null=True, index=True, help_text="Semantic action name e.g. send_message, create_agent, click_nav")
    
    # UI Element details
    element_tag = CharField(max_length=32, null=True, help_text="button | a | input | tab | switch")
    element_id = CharField(max_length=128, null=True, help_text="DOM ID or component test ID")
    element_label = CharField(max_length=255, null=True, help_text="Button text, title, or aria-label")
    
    # Timing & Metrics
    duration_seconds = FloatField(default=0.0, help_text="Time spent on page or duration of active interaction")
    
    # Context & Environment
    metadata = JSONField(null=True, default=dict, help_text="Sanitized non-sensitive contextual metadata")
    ip = CharField(max_length=64, null=True, help_text="Client IP (sanitized)")
    user_agent = CharField(max_length=255, null=True, help_text="Browser user agent string")
    
    # High performance partitioning / group by indices
    date_str = CharField(max_length=10, null=False, index=True, help_text="YYYY-MM-DD for fast date aggregation")
    hour_of_day = IntegerField(default=0, index=True, help_text="Hour of day (0-23)")
    timestamp = BigIntegerField(null=False, index=True, help_text="Unix timestamp in milliseconds")

    class Meta:
        db_table = "user_activity_event"
        indexes = (
            (("module", "date_str"), False),
            (("user_id", "date_str"), False),
            (("event_type", "date_str"), False),
        )

    @classmethod
    def create_event(cls, **kwargs):
        if not kwargs.get("id"):
            kwargs["id"] = get_uuid()
        now = datetime.now()
        if not kwargs.get("date_str"):
            kwargs["date_str"] = now.strftime("%Y-%m-%d")
        if "hour_of_day" not in kwargs or kwargs.get("hour_of_day") is None:
            kwargs["hour_of_day"] = now.hour
        if not kwargs.get("timestamp"):
            kwargs["timestamp"] = int(time.time() * 1000)
        return cls.create(**kwargs)
