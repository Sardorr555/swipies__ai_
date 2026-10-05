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
"""CRM Schema definitions, field mappings, and automated Knowledge Base configuration for Text-to-SQL."""

from __future__ import annotations

import logging
from typing import Any

from common.constants import FileSource

logger = logging.getLogger("api.crm.schema")

# Canonical field mappings for each supported CRM platform.
# Maps entity fields to human-readable descriptions used by LLM Text-to-SQL prompts.
CRM_SOURCE_FIELD_MAPS: dict[str, dict[str, str]] = {
    FileSource.BITRIX24: {
        "id": "Record ID",
        "title": "Deal / Lead Title",
        "name": "Contact / Company Name",
        "opportunity": "Deal Opportunity / Value",
        "price": "Deal Price / Value",
        "currency_id": "Currency Code",
        "stage_id": "Deal Stage ID",
        "status_id": "Lead Status ID",
        "contact_id": "Associated Contact ID",
        "company_id": "Associated Company ID",
        "phone": "Phone Number",
        "email": "Email Address",
        "entity_type": "Bitrix24 Entity Type",
        "date_create": "Creation Date",
        "date_modify": "Modification Date",
    },
    FileSource.AMOCRM: {
        "id": "Lead / Contact ID",
        "name": "Lead / Contact Name",
        "price": "Deal Budget / Price",
        "status_id": "Stage / Status ID",
        "pipeline_id": "Pipeline ID",
        "phone": "Phone Number",
        "email": "Email Address",
        "entity_type": "amoCRM Entity Type",
        "created_at": "Creation Timestamp",
        "updated_at": "Update Timestamp",
    },
    FileSource.KOMMO: {
        "id": "Lead / Contact ID",
        "name": "Lead / Contact Name",
        "price": "Deal Budget / Price",
        "status_id": "Stage / Status ID",
        "pipeline_id": "Pipeline ID",
        "phone": "Phone Number",
        "email": "Email Address",
        "entity_type": "Kommo Entity Type",
        "created_at": "Creation Timestamp",
        "updated_at": "Update Timestamp",
    },
    FileSource.HUBSPOT: {
        "id": "Object ID",
        "dealname": "Deal Name",
        "amount": "Deal Amount",
        "dealstage": "Deal Stage ID",
        "pipeline": "Pipeline ID",
        "firstname": "First Name",
        "lastname": "Last Name",
        "email": "Email Address",
        "phone": "Phone Number",
        "company": "Company Name",
        "entity_type": "HubSpot Object Type",
        "createdate": "Creation Date",
        "hs_lastmodifieddate": "Last Modified Date",
    },
    FileSource.ONE_C: {
        "ref_key": "1C Object UUID",
        "code": "Item / Document Code",
        "description": "Item Description / Title",
        "price": "Unit Price",
        "quantity": "Warehouse Stock Balance",
        "unit": "Unit of Measurement",
        "catalog": "1C Catalog or Document",
        "date": "Document Date",
        "posted": "Document Posted Status",
    },
    FileSource.SALESFORCE: {
        "id": "Salesforce Object ID",
        "name": "Record Name",
        "amount": "Opportunity Amount",
        "stage_name": "Opportunity Stage Name",
        "close_date": "Expected Close Date",
        "email": "Contact Email",
        "phone": "Phone Number",
        "account_id": "Associated Account ID",
        "entity_type": "Salesforce Object Type",
    },
}

CRM_SOURCES: frozenset[str] = frozenset(CRM_SOURCE_FIELD_MAPS.keys())

_CRM_SOURCE_ALIASES: dict[str, str] = {
    "bitrix24": FileSource.BITRIX24,
    "amocrm": FileSource.AMOCRM,
    "kommo": FileSource.KOMMO,
    "hubspot": FileSource.HUBSPOT,
    "1c_odata": FileSource.ONE_C,
    "onec": FileSource.ONE_C,
    "one_c": FileSource.ONE_C,
    "1c": FileSource.ONE_C,
    "salesforce": FileSource.SALESFORCE,
}


def is_crm_source(source_name: str | None) -> bool:
    """Return True if source_name is a known CRM connector source."""
    if not source_name:
        return False
    norm = str(source_name).strip().lower()
    return norm in CRM_SOURCES or norm in _CRM_SOURCE_ALIASES


def get_crm_field_map(source_name: str | None) -> dict[str, str]:
    """Retrieve the standard schema field map for a given CRM source."""
    if not source_name:
        return {}
    norm = str(source_name).strip().lower()
    resolved = _CRM_SOURCE_ALIASES.get(norm, norm)
    return dict(CRM_SOURCE_FIELD_MAPS.get(resolved, {}))


def auto_populate_crm_field_map(kb_id: str, source_name: str) -> bool:
    """Auto-populate Knowledge Base parser_config['field_map'] for CRM datasets.

    Enables out-of-the-box Text-to-SQL querying in standard Chat dialogs
    without requiring manual field mapping configuration by the user.
    """
    if not kb_id or not is_crm_source(source_name):
        return False
    crm_fm = get_crm_field_map(source_name)
    if not crm_fm:
        return False

    try:
        from api.db.services.knowledgebase_service import KnowledgebaseService

        e, kb = KnowledgebaseService.get_by_id(kb_id)
        if not e or not kb:
            return False

        parser_config = dict(kb.parser_config or {})
        existing_fm = parser_config.get("field_map") or {}

        # Merge CRM fields with existing (preserve any user customized field definitions)
        merged_fm = dict(crm_fm)
        merged_fm.update(existing_fm)

        if merged_fm != existing_fm:
            parser_config["field_map"] = merged_fm
            existing_cols = parser_config.get("table_column_names") or []
            new_cols = list(dict.fromkeys(existing_cols + list(merged_fm.keys())))
            parser_config["table_column_names"] = new_cols
            KnowledgebaseService.update_parser_config(kb_id, parser_config)
            logger.info(
                "Auto-populated CRM field_map for kb_id=%s source=%s (%d fields)",
                kb_id,
                source_name,
                len(merged_fm),
            )
            return True
        return False
    except Exception as exc:
        logger.warning(
            "auto_populate_crm_field_map failed for kb_id=%s source=%s: %s",
            kb_id,
            source_name,
            exc,
        )
        return False
