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
from peewee import CharField, IntegerField, BigIntegerField
from api.db.db_models import DataBaseModel, JSONField


class CRMConnection(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=128, null=False)
    crm_type = CharField(max_length=32, null=False, default="amocrm")  # amocrm, bitrix24, bitrix24_onprem, 1c_odata
    auth_type = CharField(max_length=32, null=False, default="oauth2")  # oauth2, inbound_webhook, basic_auth
    status = CharField(max_length=32, null=False, default="active")    # active, reauth_required, disabled
    token_version = IntegerField(default=1, null=False)                # monotonic fencing counter
    config = JSONField(null=False, default={})                         # encrypted credentials (enc:v2:)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "crm_connection"
        indexes = (
            (("tenant_id", "status"), False),
        )


class CRMOutbox(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)
    connection_id = CharField(max_length=32, null=False, index=True)
    business_key = CharField(max_length=64, null=True, index=True)     # HMAC-SHA256 for 24h dedup, nulled after 30d
    status = CharField(max_length=32, null=False, default="PENDING")   # PENDING, PROCESSING, SENT, FAILED, DEAD_LETTER
    retry_count = IntegerField(default=0, null=False)
    max_retries = IntegerField(default=5, null=False)
    next_retry_at = BigIntegerField(null=True, index=True)
    lease_owner = CharField(max_length=64, null=True)
    lease_expires_at = BigIntegerField(null=True)
    lead_data = JSONField(null=False, default={})                      # payload (name, phone, query, context), scrubbed after 30d
    error_log = JSONField(null=True, default={})                       # error messages with secrets sanitized

    def __str__(self):
        return f"{self.id}:{self.status}"

    class Meta:
        db_table = "crm_outbox"
        indexes = (
            (("status", "next_retry_at"), False),
            (("tenant_id", "business_key"), False),
            (("lease_owner", "lease_expires_at"), False),
        )
