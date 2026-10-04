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
"""Step 3 Test Suite: CRM Chat Text-to-SQL Field Map & Agent Canvas Template."""

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")
warnings.filterwarnings("ignore", category=ResourceWarning)

import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest

# Ensure Peewee does not attempt real DB connections
from api.db.db_models import DB
DB.connect = lambda *a, **kw: True
DB.connection_context = lambda: (lambda fn: fn)

from common.constants import FileSource
from api.crm.schema import (
    CRM_SOURCE_FIELD_MAPS,
    is_crm_source,
    get_crm_field_map,
    auto_populate_crm_field_map,
)
from api.db.template_utils import normalize_canvas_template_categories
from common.file_utils import get_project_base_directory


class TestCRMSchemaAndFieldMap:
    """Tests for CRM schema definitions and automated field mapping."""

    @pytest.mark.parametrize(
        "src,expected_source",
        [
            (FileSource.BITRIX24, True),
            (FileSource.AMOCRM, True),
            (FileSource.KOMMO, True),
            (FileSource.HUBSPOT, True),
            (FileSource.ONE_C, True),
            ("bitrix24", True),
            ("amocrm", True),
            ("kommo", True),
            ("hubspot", True),
            ("1c_odata", True),
            ("one_c", True),
            ("1c", True),
            ("mysql", False),
            ("s3", False),
            ("jira", False),
            (None, False),
        ],
    )
    def test_is_crm_source(self, src, expected_source):
        assert is_crm_source(src) == expected_source

    def test_crm_source_field_maps_completeness(self):
        for src in [
            FileSource.BITRIX24,
            FileSource.AMOCRM,
            FileSource.KOMMO,
            FileSource.HUBSPOT,
            FileSource.ONE_C,
        ]:
            fm = get_crm_field_map(src)
            assert isinstance(fm, dict)
            assert len(fm) >= 5, f"Source {src} should define at least 5 standard fields"
            # Verify field map values are descriptive strings for LLM Text-to-SQL prompts
            for k, v in fm.items():
                assert isinstance(k, str) and k.strip(), f"Empty key for {src}"
                assert isinstance(v, str) and v.strip(), f"Empty description for {src}.{k}"

    def test_auto_populate_crm_field_map_success(self):
        fake_kb = SimpleNamespace(
            id="kb_test_123",
            parser_config={},
        )

        with patch("api.db.services.knowledgebase_service.KnowledgebaseService.get_by_id", return_value=(True, fake_kb)), \
             patch("api.db.services.knowledgebase_service.KnowledgebaseService.update_parser_config") as mock_update:
            
            res = auto_populate_crm_field_map("kb_test_123", FileSource.BITRIX24)
            assert res is True
            mock_update.assert_called_once()
            called_kb_id, called_cfg = mock_update.call_args[0]
            assert called_kb_id == "kb_test_123"
            assert "field_map" in called_cfg
            assert "table_column_names" in called_cfg
            assert "opportunity" in called_cfg["field_map"]
            assert "title" in called_cfg["field_map"]

    def test_auto_populate_crm_field_map_preserves_custom_fields(self):
        fake_kb = SimpleNamespace(
            id="kb_test_custom",
            parser_config={
                "field_map": {"custom_vip_score": "VIP Score (1-100)"},
                "table_column_names": ["custom_vip_score"],
            },
        )

        with patch("api.db.services.knowledgebase_service.KnowledgebaseService.get_by_id", return_value=(True, fake_kb)), \
             patch("api.db.services.knowledgebase_service.KnowledgebaseService.update_parser_config") as mock_update:
            
            res = auto_populate_crm_field_map("kb_test_custom", FileSource.HUBSPOT)
            assert res is True
            called_kb_id, called_cfg = mock_update.call_args[0]
            fm = called_cfg["field_map"]
            # Preserved existing custom field
            assert fm["custom_vip_score"] == "VIP Score (1-100)"
            # Added CRM fields
            assert "dealname" in fm
            assert "amount" in fm
            assert "custom_vip_score" in called_cfg["table_column_names"]

    def test_auto_populate_crm_field_map_non_crm_ignored(self):
        with patch("api.db.services.knowledgebase_service.KnowledgebaseService.get_by_id") as mock_get:
            res = auto_populate_crm_field_map("kb_test_123", "s3")
            assert res is False
            mock_get.assert_not_called()

    def test_auto_populate_crm_field_map_kb_not_found(self):
        with patch("api.db.services.knowledgebase_service.KnowledgebaseService.get_by_id", return_value=(False, None)):
            res = auto_populate_crm_field_map("non_existent_kb", FileSource.AMOCRM)
            assert res is False


class TestCRMAgentCanvasTemplate:
    """Tests for the pre-built CRM Sales & Intelligence Agent canvas template."""

    @pytest.fixture
    def template_data(self):
        base_dir = get_project_base_directory()
        tmpl_path = os.path.join(base_dir, "agent", "templates", "crm_sales_intelligence_agent.json")
        assert os.path.exists(tmpl_path), f"Template file missing: {tmpl_path}"
        with open(tmpl_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_template_json_valid_and_normalized(self, template_data):
        norm = normalize_canvas_template_categories(template_data)
        assert norm["id"] == 42
        assert norm["canvas_type"] in ("Recommended", "Customer Support")
        assert "Recommended" in norm["canvas_types"]
        assert norm["canvas_category"] == "agent_canvas"
        assert isinstance(norm["title"], dict)
        assert "en" in norm["title"] and "ru" in norm["title"]
        assert isinstance(norm["description"], dict)
        assert "en" in norm["description"] and "ru" in norm["description"]

    def test_template_dsl_components_and_wiring(self, template_data):
        dsl = template_data["dsl"]
        components = dsl["components"]
        assert "begin" in components
        assert "Agent:CrmSalesAgent" in components
        assert "Message:CrmSalesMessage" in components

        # Begin wires to Agent
        assert "Agent:CrmSalesAgent" in components["begin"]["downstream"]
        # Agent wires to Message
        assert "Message:CrmSalesMessage" in components["Agent:CrmSalesAgent"]["downstream"]
        assert "begin" in components["Agent:CrmSalesAgent"]["upstream"]

        # Check Agent tools
        agent_params = components["Agent:CrmSalesAgent"]["obj"]["params"]
        tools = agent_params["tools"]
        tool_names = [t["component_name"] for t in tools]
        assert "QueryCRMRecords" in tool_names
        assert "CreateIncomingLead" in tool_names
        assert "CheckStock" in tool_names
        assert "Retrieval" in tool_names

    def test_template_graph_nodes_and_edges(self, template_data):
        graph = template_data["dsl"]["graph"]
        nodes = graph["nodes"]
        edges = graph["edges"]

        node_ids = {n["id"] for n in nodes}
        assert "begin" in node_ids
        assert "Agent:CrmSalesAgent" in node_ids
        assert "Message:CrmSalesMessage" in node_ids
        assert "Tool:QueryCrmRecordsToolNode" in node_ids
        assert "Tool:CreateIncomingLeadToolNode" in node_ids
        assert "Tool:CheckStockToolNode" in node_ids
        assert "Tool:RetrievalToolNode" in node_ids

        edge_targets = {e["target"] for e in edges}
        assert "Agent:CrmSalesAgent" in edge_targets
        assert "Message:CrmSalesMessage" in edge_targets
        assert "Tool:QueryCrmRecordsToolNode" in edge_targets
        assert "Tool:CreateIncomingLeadToolNode" in edge_targets
        assert "Tool:CheckStockToolNode" in edge_targets
        assert "Tool:RetrievalToolNode" in edge_targets

    def test_tool_components_resolve_via_component_class(self):
        # Stub out dependencies to avoid heavy imports
        sys.modules.setdefault("api.db.services.dialog_service", MagicMock())
        sys.modules.setdefault("xgboost", MagicMock())
        sys.modules.setdefault("pypdf", MagicMock())
        sys.modules.setdefault("api.db.services.file_service", MagicMock())
        sys.modules.setdefault("api.db.services.task_service", MagicMock())

        from agent.component import component_class
        # Verify QueryCRMRecords and its Param can be loaded dynamically by the canvas engine
        cls_query = component_class("QueryCRMRecords")
        param_query = component_class("QueryCRMRecordsParam")
        assert cls_query is not None
        assert param_query is not None

        cls_lead = component_class("CreateIncomingLead")
        param_lead = component_class("CreateIncomingLeadParam")
        assert cls_lead is not None
        assert param_lead is not None

        cls_stock = component_class("CheckStock")
        param_stock = component_class("CheckStockParam")
        assert cls_stock is not None
        assert param_stock is not None


class TestCRMConnectorLinkAndSyncTrigger:
    """Tests that linking a CRM connector to a Knowledge Base triggers auto-population."""

    def test_link_connectors_triggers_auto_population(self):
        from api.db.services.connector_service import Connector2KbService

        mock_conn = SimpleNamespace(
            id="conn_crm_1",
            source=FileSource.BITRIX24,
            config={},
        )

        with patch("api.db.services.connector_service.Connector2KbService.query", return_value=[]), \
             patch("api.db.services.connector_service.Connector2KbService.save"), \
             patch("api.db.services.connector_service.SyncLogsService.schedule"), \
             patch("api.db.services.connector_service.ConnectorService.get_by_id", return_value=(True, mock_conn)), \
             patch("api.db.services.connector_service.auto_populate_crm_field_map") as mock_auto_pop:

            Connector2KbService.link_connectors(
                kb_id="kb_b24_abc",
                connectors=[{"id": "conn_crm_1", "auto_parse": "1"}],
                tenant_id="tenant_123",
            )

            mock_auto_pop.assert_called_once_with("kb_b24_abc", FileSource.BITRIX24)
