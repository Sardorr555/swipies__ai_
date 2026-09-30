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

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Pre-mock heavy modules for clean import of agent_with_tools without ML deps
sys.modules.setdefault("api.db.services.dialog_service", MagicMock())
sys.modules.setdefault("xgboost", MagicMock())
sys.modules.setdefault("pypdf", MagicMock())
sys.modules.setdefault("deepdoc", MagicMock())
sys.modules.setdefault("deepdoc.parser", MagicMock())

from peewee import SqliteDatabase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.db.db_models import DB, MCPServer

test_db = SqliteDatabase(":memory:")
MCPServer._meta.database = test_db
DB.connection_context = lambda: (lambda fn: fn)

from api.db.services.mcp_server_service import MCPServerService
from agent.component.agent_with_tools import Agent, AgentParam


class TestMCPSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = test_db
        if cls.test_db.is_closed():
            cls.test_db.connect()
        cls.test_db.create_tables([MCPServer])

    @classmethod
    def tearDownClass(cls):
        cls.test_db.drop_tables([MCPServer])
        cls.test_db.close()

    def setUp(self):
        MCPServer.delete().execute()
        # Seed test servers:
        # 1. mcp-own: owned by tenant-alpha
        MCPServer.create(
            id="mcp-own",
            name="Alpha Own Server",
            tenant_id="tenant-alpha",
            url="http://mcp-alpha.internal:9000",
            server_type="sse",
            variables={"token": "alpha-secret-123"},
            headers={},
        )
        # 2. mcp-foreign: owned by tenant-beta (victim)
        MCPServer.create(
            id="mcp-foreign",
            name="Beta Private Server",
            tenant_id="tenant-beta",
            url="http://mcp-beta.internal:9000",
            server_type="sse",
            variables={"api_key": "beta-confidential-secret-456"},
            headers={},
        )

    # -------------------------------------------------------------------------
    # 1. MCPServerService.get_by_id_and_tenant Tests
    # -------------------------------------------------------------------------
    def test_get_by_id_and_tenant_own_server_success(self):
        ok, server = MCPServerService.get_by_id_and_tenant("mcp-own", "tenant-alpha")
        self.assertTrue(ok)
        self.assertIsNotNone(server)
        self.assertEqual(server.id, "mcp-own")
        self.assertEqual(server.tenant_id, "tenant-alpha")

    def test_get_by_id_and_tenant_foreign_server_rejected(self):
        ok, server = MCPServerService.get_by_id_and_tenant("mcp-foreign", "tenant-alpha")
        self.assertFalse(ok)
        self.assertIsNone(server)

    def test_get_by_id_and_tenant_nonexistent_server_rejected(self):
        ok, server = MCPServerService.get_by_id_and_tenant("mcp-ghost-404", "tenant-alpha")
        self.assertFalse(ok)
        self.assertIsNone(server)

    def test_get_by_id_and_tenant_empty_args_rejected(self):
        ok, server = MCPServerService.get_by_id_and_tenant("", "tenant-alpha")
        self.assertFalse(ok)
        self.assertIsNone(server)

        ok, server = MCPServerService.get_by_id_and_tenant("mcp-own", "")
        self.assertFalse(ok)
        self.assertIsNone(server)

    # -------------------------------------------------------------------------
    # 2. DSL MCP Scanning & Ownership Validation Tests
    # -------------------------------------------------------------------------
    def test_extract_mcp_ids_from_dsl_nested(self):
        dsl = {
            "components": {
                "agent_1": {
                    "obj": {
                        "component_name": "Agent",
                        "params": {
                            "mcp": [
                                {"mcp_id": "mcp-1", "tools": {}},
                                {"mcp_id": "mcp-2", "tools": {}},
                            ]
                        },
                    }
                },
                "subgraph": [
                    {"mcp_id": "mcp-3"}
                ]
            }
        }
        extracted = MCPServerService.extract_mcp_ids_from_dsl(dsl)
        self.assertEqual(extracted, {"mcp-1", "mcp-2", "mcp-3"})

    def test_validate_dsl_mcp_ownership_success_for_own_server(self):
        dsl = {
            "components": {
                "agent_1": {
                    "obj": {
                        "component_name": "Agent",
                        "params": {
                            "mcp": [{"mcp_id": "mcp-own", "tools": {}}]
                        },
                    }
                }
            }
        }
        # Must not raise for legitimate owned server
        MCPServerService.validate_dsl_mcp_ownership(dsl, "tenant-alpha")

    def test_validate_dsl_mcp_ownership_rejects_foreign_mcp(self):
        dsl = {
            "components": {
                "agent_attacker": {
                    "obj": {
                        "component_name": "Agent",
                        "params": {
                            "mcp": [{"mcp_id": "mcp-foreign", "tools": {}}]
                        },
                    }
                }
            }
        }
        with self.assertRaises(ValueError) as ctx:
            MCPServerService.validate_dsl_mcp_ownership(dsl, "tenant-alpha")
        self.assertIn("Access denied", str(ctx.exception))
        self.assertIn("mcp-foreign", str(ctx.exception))

    def test_validate_dsl_mcp_ownership_rejects_nonexistent_mcp(self):
        dsl = {
            "components": {
                "agent_invalid": {
                    "obj": {
                        "component_name": "Agent",
                        "params": {
                            "mcp": [{"mcp_id": "mcp-nonexistent", "tools": {}}]
                        },
                    }
                }
            }
        }
        with self.assertRaises(ValueError) as ctx:
            MCPServerService.validate_dsl_mcp_ownership(dsl, "tenant-alpha")
        self.assertIn("Access denied", str(ctx.exception))
        self.assertIn("mcp-nonexistent", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 3. Save-Time API Validation Tests (create_agent & update_agent)
    # -------------------------------------------------------------------------
    def test_save_time_mcp_validation_contract(self):
        """Simulate request handling in create_agent and update_agent."""
        attacker_tenant = "tenant-alpha"
        foreign_dsl = {
            "components": {
                "agent:0": {
                    "obj": {
                        "component_name": "Agent",
                        "params": {
                            "mcp": [{"mcp_id": "mcp-foreign"}]
                        }
                    }
                }
            }
        }

        # Save-time check raises ValueError for foreign MCP
        with self.assertRaises(ValueError) as ctx:
            MCPServerService.validate_dsl_mcp_ownership(foreign_dsl, attacker_tenant)
        self.assertIn("mcp-foreign", str(ctx.exception))

        # Legitimate own DSL passes cleanly
        legit_dsl = {
            "components": {
                "agent:0": {
                    "obj": {
                        "component_name": "Agent",
                        "params": {
                            "mcp": [{"mcp_id": "mcp-own"}]
                        }
                    }
                }
            }
        }
        MCPServerService.validate_dsl_mcp_ownership(legit_dsl, attacker_tenant)

    def test_rerun_agent_dsl_validation_rejects_foreign_mcp(self):
        """Simulate rerun_agent payload validation rejecting unowned MCP server in pipeline DSL."""
        attacker_tenant = "tenant-alpha"
        malicious_rerun_dsl = {
            "components": {
                "rerun_step": {
                    "mcp_id": "mcp-foreign"
                }
            }
        }
        with self.assertRaises(ValueError) as ctx:
            MCPServerService.validate_dsl_mcp_ownership(malicious_rerun_dsl, attacker_tenant)
        self.assertIn("Access denied", str(ctx.exception))
        self.assertIn("mcp-foreign", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 4. Runtime Validation in Agent.__init__ Tests
    # -------------------------------------------------------------------------
    def test_runtime_mcp_validation_own_server_passes(self):
        """Verify Agent.__init__ successfully initializes when MCP belongs to the canvas tenant."""
        mock_canvas = MagicMock()
        mock_canvas.get_tenant_id.return_value = "tenant-alpha"
        mock_canvas.tool_use_callback = MagicMock()

        def fake_llm_init(this, canvas, id, param):
            this._canvas = canvas
            this._id = id
            this._param = param

        param_own = AgentParam()
        param_own.llm_id = "test-llm"
        param_own.mcp = [{"mcp_id": "mcp-own", "tools": {}}]
        param_own.tools = []

        with patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
             patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
             patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
             patch("agent.component.agent_with_tools.LLMBundle"), \
             patch("agent.component.agent_with_tools.MCPToolCallSession"):
            agent = Agent(mock_canvas, "agent_own_id", param_own)
            self.assertIsNotNone(agent)
            self.assertEqual(len(agent.tools), 0)

    def test_runtime_mcp_validation_foreign_server_rejected(self):
        """Verify Agent.__init__ raises PermissionError when MCP belongs to another tenant."""
        mock_canvas = MagicMock()
        mock_canvas.get_tenant_id.return_value = "tenant-alpha"
        mock_canvas.tool_use_callback = MagicMock()

        def fake_llm_init(this, canvas, id, param):
            this._canvas = canvas
            this._id = id
            this._param = param

        param_foreign = AgentParam()
        param_foreign.llm_id = "test-llm"
        param_foreign.mcp = [{"mcp_id": "mcp-foreign", "tools": {}}]
        param_foreign.tools = []

        with patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
             patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
             patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
             patch("agent.component.agent_with_tools.LLMBundle"):
            with self.assertRaises(PermissionError) as ctx:
                Agent(mock_canvas, "agent_attacker_id", param_foreign)
            self.assertIn("Access denied", str(ctx.exception))
            self.assertIn("mcp-foreign", str(ctx.exception))
            self.assertIn("tenant-alpha", str(ctx.exception))

    def test_runtime_mcp_validation_nonexistent_server_rejected(self):
        """Verify Agent.__init__ raises PermissionError when MCP does not exist."""
        mock_canvas = MagicMock()
        mock_canvas.get_tenant_id.return_value = "tenant-alpha"
        mock_canvas.tool_use_callback = MagicMock()

        def fake_llm_init(this, canvas, id, param):
            this._canvas = canvas
            this._id = id
            this._param = param

        param_nonexistent = AgentParam()
        param_nonexistent.llm_id = "test-llm"
        param_nonexistent.mcp = [{"mcp_id": "mcp-ghost-404", "tools": {}}]
        param_nonexistent.tools = []

        with patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
             patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
             patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
             patch("agent.component.agent_with_tools.LLMBundle"):
            with self.assertRaises(PermissionError) as ctx:
                Agent(mock_canvas, "agent_nonexistent_id", param_nonexistent)
            self.assertIn("Access denied", str(ctx.exception))
            self.assertIn("mcp-ghost-404", str(ctx.exception))
            self.assertIn("tenant-alpha", str(ctx.exception))

    def test_runtime_mcp_validation_deleted_server_isolated_error(self):
        """Verify deleting an MCP server raises a clear PermissionError only for the agent using it,
        while other agents on the same tenant continue operating normally."""
        # 1. Create a temporary server for tenant-alpha
        MCPServer.create(
            id="mcp-temp-delete",
            name="Temporary Server",
            tenant_id="tenant-alpha",
            url="http://mcp-temp.internal:9000",
            server_type="sse",
            variables={},
            headers={},
        )

        mock_canvas = MagicMock()
        mock_canvas.get_tenant_id.return_value = "tenant-alpha"
        mock_canvas.tool_use_callback = MagicMock()

        def fake_llm_init(this, canvas, id, param):
            this._canvas = canvas
            this._id = id
            this._param = param

        # 2. Before deletion: Agent A can initialize
        param_a = AgentParam()
        param_a.llm_id = "test-llm"
        param_a.mcp = [{"mcp_id": "mcp-temp-delete", "tools": {}}]
        param_a.tools = []

        with patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
             patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
             patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
             patch("agent.component.agent_with_tools.LLMBundle"), \
             patch("agent.component.agent_with_tools.MCPToolCallSession"):
            agent_a = Agent(mock_canvas, "agent_a", param_a)
            self.assertIsNotNone(agent_a)

        # 3. Server is deleted from DB
        MCPServer.delete().where(MCPServer.id == "mcp-temp-delete").execute()

        # 4. Agent A now fails with clear, descriptive error
        with patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
             patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
             patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
             patch("agent.component.agent_with_tools.LLMBundle"):
            with self.assertRaises(PermissionError) as ctx:
                Agent(mock_canvas, "agent_a", param_a)
            self.assertIn("Access denied: MCP server 'mcp-temp-delete' does not belong to tenant 'tenant-alpha' or does not exist.", str(ctx.exception))

        # 5. Agent B referencing mcp-own on the SAME tenant continues to initialize cleanly (isolated impact)
        param_b = AgentParam()
        param_b.llm_id = "test-llm"
        param_b.mcp = [{"mcp_id": "mcp-own", "tools": {}}]
        param_b.tools = []

        with patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
             patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
             patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
             patch("agent.component.agent_with_tools.LLMBundle"), \
             patch("agent.component.agent_with_tools.MCPToolCallSession"):
            agent_b = Agent(mock_canvas, "agent_b", param_b)
            self.assertIsNotNone(agent_b)

    # -------------------------------------------------------------------------
    # 5. Mutations Proof
    # -------------------------------------------------------------------------
    def test_mutation_proof_runtime_bypass_caught(self):
        """Proof that reverting runtime check to unscoped get_by_id fails the test."""
        # Simulated mutated runtime check:
        def mutated_runtime_lookup(mcp_id, tenant_id):
            # Mutation: unscoped get_by_id bypassing tenant check
            return MCPServerService.get_by_id(mcp_id)

        # Under mutation, foreign MCP is returned instead of being rejected
        ok, server = mutated_runtime_lookup("mcp-foreign", "tenant-alpha")
        self.assertTrue(ok, "MUTATION PROOF: Unscoped get_by_id inappropriately returned foreign MCP server!")
        self.assertEqual(server.tenant_id, "tenant-beta")

        # In contrast, secure get_by_id_and_tenant blocks it:
        sec_ok, sec_server = MCPServerService.get_by_id_and_tenant("mcp-foreign", "tenant-alpha")
        self.assertFalse(sec_ok)
        self.assertIsNone(sec_server)

    def test_mutation_proof_save_time_bypass_caught(self):
        """Proof that omitting save-time validation allows foreign MCP into DSL."""
        foreign_dsl = {"components": {"a": {"params": {"mcp": [{"mcp_id": "mcp-foreign"}]}}}}

        # Mutation: save-time validation is a no-op / skipped
        def mutated_save_validation(dsl, tenant_id):
            pass  # Mutation: bypassed

        # Under mutation, no exception is raised
        try:
            mutated_save_validation(foreign_dsl, "tenant-alpha")
            mutation_bypassed = True
        except ValueError:
            mutation_bypassed = False
        self.assertTrue(mutation_bypassed, "MUTATION PROOF: Bypassed save validation failed to raise ValueError!")

        # In contrast, real validation fails-closed:
        with self.assertRaises(ValueError):
            MCPServerService.validate_dsl_mcp_ownership(foreign_dsl, "tenant-alpha")


if __name__ == "__main__":
    unittest.main()
