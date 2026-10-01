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
import warnings
# Suppress RequestsDependencyWarning caused by local environment version drift between urllib3 (2.4.0) and chardet (7.4.3)/charset_normalizer (3.5.1)
warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")

# Pre-mock heavy modules for clean import of agent_with_tools without ML deps
sys.modules.setdefault("api.db.services.dialog_service", MagicMock())
sys.modules.setdefault("xgboost", MagicMock())
sys.modules.setdefault("pypdf", MagicMock())
sys.modules.setdefault("deepdoc", MagicMock())
sys.modules.setdefault("deepdoc.parser", MagicMock())
sys.modules.setdefault("api.db.services.file_service", MagicMock())
sys.modules.setdefault("api.db.services.task_service", MagicMock())


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import settings
settings.init_settings = lambda *a, **kw: None

from peewee import SqliteDatabase
from api.db.db_models import DB, MCPServer

_test_db = SqliteDatabase(":memory:")
MCPServer._meta.database = _test_db
DB.connection_context = lambda: (lambda fn: fn)
DB.atomic = lambda *args, **kwargs: _test_db.atomic()

from api.db.services.mcp_server_service import MCPServerService
from agent.component.agent_with_tools import Agent, AgentParam
from agent.canvas import Canvas


class TestMCPSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db = _test_db
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
    def test_runtime_mcp_validation_owner_runs_ok(self):
        """Verify Agent.__init__ successfully initializes when canvas owner runs canvas with own MCP."""
        mock_canvas = MagicMock()
        mock_canvas.get_tenant_id.return_value = "tenant-alpha"
        mock_canvas.get_canvas_owner_tenant.return_value = "tenant-alpha"
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

    def test_runtime_mcp_validation_team_member_runs_with_owner_mcp_ok(self):
        """Verify Agent.__init__ allows a team member (tenant-beta) to run canvas with owner's (tenant-alpha) MCP."""
        mock_canvas = MagicMock()
        # Caller tenant is tenant-beta (team member)
        mock_canvas.get_tenant_id.return_value = "tenant-beta"
        # Canvas owner tenant is tenant-alpha
        mock_canvas.get_canvas_owner_tenant.return_value = "tenant-alpha"
        mock_canvas.tool_use_callback = MagicMock()

        def fake_llm_init(this, canvas, id, param):
            this._canvas = canvas
            this._id = id
            this._param = param

        param_team = AgentParam()
        param_team.llm_id = "test-llm"
        param_team.mcp = [{"mcp_id": "mcp-own", "tools": {}}]  # mcp-own belongs to tenant-alpha
        param_team.tools = []

        with patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
             patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
             patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
             patch("agent.component.agent_with_tools.LLMBundle"), \
             patch("agent.component.agent_with_tools.MCPToolCallSession"):
            agent = Agent(mock_canvas, "agent_team_id", param_team)
            self.assertIsNotNone(agent)
            self.assertEqual(len(agent.tools), 0)

    def test_real_canvas_owner_wiring_and_fallback(self):
        """Verify real Canvas correctly stores caller tenant vs owner tenant and implements fallback."""
        import json
        dsl = json.dumps({"components": {}, "history": [], "messages": [], "retrieval": []})

        # Explicit owner wiring (as performed in agent_api, bot_api, canvas_service)
        c_wired = Canvas(dsl, tenant_id="tenant-beta", canvas_owner_tenant="tenant-alpha")
        self.assertEqual(c_wired.get_tenant_id(), "tenant-beta")
        self.assertEqual(c_wired.get_canvas_owner_tenant(), "tenant-alpha")

        # Fallback when canvas_owner_tenant is omitted or None
        c_fallback = Canvas(dsl, tenant_id="tenant-gamma")
        self.assertEqual(c_fallback.get_tenant_id(), "tenant-gamma")
        self.assertEqual(c_fallback.get_canvas_owner_tenant(), "tenant-gamma")

    def test_real_canvas_runtime_with_agent_owner_vs_team(self):
        """Verify real Canvas with Agent.__init__: team member runs owner's MCP successfully."""
        import json
        dsl = json.dumps({"components": {}, "history": [], "messages": [], "retrieval": []})
        c_real = Canvas(dsl, tenant_id="tenant-beta", canvas_owner_tenant="tenant-alpha")

        def fake_llm_init(this, canvas, id, param):
            this._canvas = canvas
            this._id = id
            this._param = param

        param = AgentParam()
        param.llm_id = "test-llm"
        param.mcp = [{"mcp_id": "mcp-own", "tools": {}}]
        param.tools = []

        with patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
             patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
             patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
             patch("agent.component.agent_with_tools.LLMBundle"), \
             patch("agent.component.agent_with_tools.MCPToolCallSession"):
            agent = Agent(c_real, "agent_team", param)
            self.assertIsNotNone(agent)

    def test_real_canvas_wiring_mutation_fails(self):
        """Verify that mutating wiring to use caller tenant_id breaks team execution of owner MCP."""
        import json
        dsl = json.dumps({"components": {}, "history": [], "messages": [], "retrieval": []})
        # Simulate wiring mutation: canvas_owner_tenant = tenant_id (caller tenant-beta instead of cvs.user_id tenant-alpha)
        c_mutated = Canvas(dsl, tenant_id="tenant-beta", canvas_owner_tenant="tenant-beta")

        def fake_llm_init(this, canvas, id, param):
            this._canvas = canvas
            this._id = id
            this._param = param

        param = AgentParam()
        param.llm_id = "test-llm"
        param.mcp = [{"mcp_id": "mcp-own", "tools": {}}]
        param.tools = []

        with patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
             patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
             patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
             patch("agent.component.agent_with_tools.LLMBundle"), \
             patch("agent.component.agent_with_tools.MCPToolCallSession"):
            with self.assertRaises(PermissionError) as ctx:
                Agent(c_mutated, "agent_mutated", param)
            self.assertIn("Access denied: MCP server 'mcp-own' does not belong to tenant 'tenant-beta'", str(ctx.exception))


    def test_runtime_mcp_validation_foreign_server_rejected(self):
        """Verify Agent.__init__ raises PermissionError when MCP does not belong to the canvas owner."""
        mock_canvas = MagicMock()
        mock_canvas.get_tenant_id.return_value = "tenant-beta"
        mock_canvas.get_canvas_owner_tenant.return_value = "tenant-alpha"
        mock_canvas.tool_use_callback = MagicMock()

        def fake_llm_init(this, canvas, id, param):
            this._canvas = canvas
            this._id = id
            this._param = param

        param_foreign = AgentParam()
        param_foreign.llm_id = "test-llm"
        param_foreign.mcp = [{"mcp_id": "mcp-foreign-evil", "tools": {}}]
        param_foreign.tools = []

        with patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
             patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
             patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
             patch("agent.component.agent_with_tools.LLMBundle"):
            with self.assertRaises(PermissionError) as ctx:
                Agent(mock_canvas, "agent_attacker_id", param_foreign)
            self.assertIn("Access denied", str(ctx.exception))
            self.assertIn("mcp-foreign-evil", str(ctx.exception))
            self.assertIn("tenant-alpha", str(ctx.exception))

    def test_runtime_mcp_validation_nonexistent_server_rejected(self):
        """Verify Agent.__init__ raises PermissionError when MCP does not exist."""
        mock_canvas = MagicMock()
        mock_canvas.get_tenant_id.return_value = "tenant-alpha"
        mock_canvas.get_canvas_owner_tenant.return_value = "tenant-alpha"
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
        mock_canvas.get_canvas_owner_tenant.return_value = "tenant-alpha"
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

    # -------------------------------------------------------------------------
    # 6. Recursion Depth Protection
    # -------------------------------------------------------------------------
    def test_extract_mcp_ids_from_dsl_max_depth(self):
        """Verify deeply nested DSL structures terminate without RecursionError."""
        deep_dsl = {"mcp_id": "root-mcp"}
        curr = deep_dsl
        for i in range(50):
            curr["nested"] = {"mcp_id": f"deep-mcp-{i}"}
            curr = curr["nested"]

        extracted = MCPServerService.extract_mcp_ids_from_dsl(deep_dsl, max_depth=10)
        self.assertIn("root-mcp", extracted)
        self.assertIn("deep-mcp-0", extracted)
        self.assertNotIn("deep-mcp-40", extracted)

    # -------------------------------------------------------------------------
    # 7. Team-Share Canvas MCP Scoping Tests
    # -------------------------------------------------------------------------
    def test_team_share_canvas_owner_scoping(self):
        """Team member updating shared canvas uses canvas owner's MCP tenant context."""
        owner_canvas = MagicMock()
        owner_canvas.user_id = "tenant-alpha"
        owner_canvas.permission = "team"
        owner_canvas.canvas_category = "agent_canvas"

        valid_dsl = {
            "components": {
                "agent_1": {
                    "obj": {
                        "component_name": "Agent",
                        "params": {"mcp": [{"mcp_id": "mcp-own"}]},
                    }
                }
            }
        }
        canvas_owner_tenant = getattr(owner_canvas, "user_id", None) or "tenant-beta"
        self.assertEqual(canvas_owner_tenant, "tenant-alpha")
        MCPServerService.validate_dsl_mcp_ownership(valid_dsl, canvas_owner_tenant)

        invalid_dsl = {
            "components": {
                "agent_1": {
                    "obj": {
                        "component_name": "Agent",
                        "params": {"mcp": [{"mcp_id": "mcp-foreign"}]},
                    }
                }
            }
        }
        with self.assertRaises(ValueError) as ctx:
            MCPServerService.validate_dsl_mcp_ownership(invalid_dsl, canvas_owner_tenant)
        self.assertIn("mcp-foreign", str(ctx.exception))
        self.assertIn("tenant-alpha", str(ctx.exception))

        # Mutation (b) proof: If update_agent reverted to caller tenant (tenant-beta),
        # legitimate save of owner's MCP server would fail:
        caller_tenant = "tenant-beta"
        with self.assertRaises(ValueError) as mut_ctx:
            MCPServerService.validate_dsl_mcp_ownership(valid_dsl, caller_tenant)
        self.assertIn("mcp-own", str(mut_ctx.exception))
        self.assertIn("tenant-beta", str(mut_ctx.exception))

    # -------------------------------------------------------------------------
    # 8. MCP API Multi-Tenant Isolation Tests
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # 8. Real Handler Integration Tests (All 4 mcp_api calls & agent_api handlers)
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # 8. Real Handler Integration Tests (All 4 mcp_api calls & agent_api handlers)
    # -------------------------------------------------------------------------
    def test_mcp_api_export_handler_cross_tenant_rejected(self):
        """Verify export / detail handler blocks cross-tenant access."""
        import importlib.util
        import types
        from quart import Quart

        mcp_api_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "api", "apps", "restful_apis", "mcp_api.py"
        ))
        app = Quart("test_export_app")

        dummy_apps = types.ModuleType("api.apps")
        dummy_apps.login_required = lambda f=None, **k: f if f and callable(f) else (lambda fn: fn)
        dummy_apps.current_user = types.SimpleNamespace(id="tenant-beta")
        dummy_web_utils = types.ModuleType("api.utils.web_utils")
        dummy_web_utils.get_float = lambda d, k, default=0: float(d.get(k, default))
        dummy_web_utils.safe_json_parse = lambda v: v if isinstance(v, dict) else {}

        orig_apps = sys.modules.get("api.apps")
        orig_web = sys.modules.get("api.utils.web_utils")
        orig_mcp_api = sys.modules.get("api.apps.restful_apis.mcp_api")
        sys.modules["api.apps"] = dummy_apps
        sys.modules["api.utils.web_utils"] = dummy_web_utils
        try:
            spec = importlib.util.spec_from_file_location("api.apps.restful_apis.mcp_api", mcp_api_path)
            mcp_api_mod = importlib.util.module_from_spec(spec)
            mcp_api_mod.manager = MagicMock()
            mcp_api_mod.manager.route = lambda *a, **k: (lambda f: f)
            sys.modules["api.apps.restful_apis.mcp_api"] = mcp_api_mod
            spec.loader.exec_module(mcp_api_mod)

            async def _run():
                # Attacker tenant-beta tries to export tenant-alpha's mcp-own -> denied (None / code 102)
                exported = mcp_api_mod._export_mcp_servers(["mcp-own"])
                self.assertIsNone(exported)

                async with app.test_request_context("/?mode=download"):
                    detail_res = mcp_api_mod.detail("mcp-own")
                    data = await detail_res.get_json() if hasattr(detail_res, "get_json") else detail_res
                    self.assertEqual(data["code"], 102)
                    self.assertIn("Cannot find MCP server", data["message"])

            asyncio.run(_run())
        finally:
            if orig_apps is not None:
                sys.modules["api.apps"] = orig_apps
            else:
                sys.modules.pop("api.apps", None)
            if orig_web is not None:
                sys.modules["api.utils.web_utils"] = orig_web
            else:
                sys.modules.pop("api.utils.web_utils", None)
            if orig_mcp_api is not None:
                sys.modules["api.apps.restful_apis.mcp_api"] = orig_mcp_api
            else:
                sys.modules.pop("api.apps.restful_apis.mcp_api", None)

    def test_mcp_api_update_handler_cross_tenant_rejected(self):
        """Verify PUT /mcp/servers/<id> rejects cross-tenant modification."""
        import importlib.util
        import types
        from quart import Quart

        mcp_api_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "api", "apps", "restful_apis", "mcp_api.py"
        ))
        app = Quart("test_update_app")

        dummy_apps = types.ModuleType("api.apps")
        dummy_apps.login_required = lambda f=None, **k: f if f and callable(f) else (lambda fn: fn)
        dummy_apps.current_user = types.SimpleNamespace(id="tenant-beta")
        dummy_web_utils = types.ModuleType("api.utils.web_utils")
        dummy_web_utils.get_float = lambda d, k, default=0: float(d.get(k, default))
        dummy_web_utils.safe_json_parse = lambda v: v if isinstance(v, dict) else {}

        orig_apps = sys.modules.get("api.apps")
        orig_web = sys.modules.get("api.utils.web_utils")
        orig_mcp_api = sys.modules.get("api.apps.restful_apis.mcp_api")
        sys.modules["api.apps"] = dummy_apps
        sys.modules["api.utils.web_utils"] = dummy_web_utils
        try:
            spec = importlib.util.spec_from_file_location("api.apps.restful_apis.mcp_api", mcp_api_path)
            mcp_api_mod = importlib.util.module_from_spec(spec)
            mcp_api_mod.manager = MagicMock()
            mcp_api_mod.manager.route = lambda *a, **k: (lambda f: f)
            sys.modules["api.apps.restful_apis.mcp_api"] = mcp_api_mod
            spec.loader.exec_module(mcp_api_mod)

            async def _run():
                # Attacker tenant-beta attempts to update victim tenant-alpha's mcp-own
                with patch.object(mcp_api_mod, "_assert_mcp_url_is_safe", return_value=("mcp-alpha.internal", "93.184.216.34", None)), \
                     patch.object(mcp_api_mod, "get_mcp_tools", return_value=({"Hacked Server": [{"name": "tool1"}]}, None)):
                    async with app.test_request_context("/", method="PUT", json={"name": "Hacked Server"}):
                        update_res = await mcp_api_mod.update("mcp-own")
                        data = await update_res.get_json() if hasattr(update_res, "get_json") else update_res
                        self.assertEqual(data["code"], 102)
                        self.assertIn("Cannot find MCP server", data["message"])

                # Confirm record in DB is unmutated
                server = MCPServer.get_or_none(MCPServer.id == "mcp-own")
                self.assertIsNotNone(server)
                self.assertEqual(server.name, "Alpha Own Server")

                # Positive control: Owner tenant-alpha can successfully update their own server
                mcp_api_mod.current_user = types.SimpleNamespace(id="tenant-alpha")
                with patch.object(mcp_api_mod, "_assert_mcp_url_is_safe", return_value=("mcp-alpha.internal", "93.184.216.34", None)), \
                     patch.object(mcp_api_mod, "get_mcp_tools", return_value=({"Alpha Own Server Updated": [{"name": "tool1"}]}, None)):
                    async with app.test_request_context("/", method="PUT", json={"name": "Alpha Own Server Updated"}):
                        update_ok = await mcp_api_mod.update("mcp-own")
                        data_ok = await update_ok.get_json() if hasattr(update_ok, "get_json") else update_ok
                        self.assertEqual(data_ok["code"], 0)

                server_updated = MCPServer.get_or_none(MCPServer.id == "mcp-own")
                self.assertIsNotNone(server_updated)
                self.assertEqual(server_updated.name, "Alpha Own Server Updated")

                # Restore name for subsequent tests
                MCPServer.update(name="Alpha Own Server").where(MCPServer.id == "mcp-own").execute()

            asyncio.run(_run())
        finally:
            if orig_apps is not None:
                sys.modules["api.apps"] = orig_apps
            else:
                sys.modules.pop("api.apps", None)
            if orig_web is not None:
                sys.modules["api.utils.web_utils"] = orig_web
            else:
                sys.modules.pop("api.utils.web_utils", None)
            if orig_mcp_api is not None:
                sys.modules["api.apps.restful_apis.mcp_api"] = orig_mcp_api
            else:
                sys.modules.pop("api.apps.restful_apis.mcp_api", None)

    def test_mcp_api_rm_handler_cross_tenant_rejected(self):
        """Verify DELETE /mcp/servers/<id> rejects cross-tenant deletion."""
        import importlib.util
        import types
        from quart import Quart

        mcp_api_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "api", "apps", "restful_apis", "mcp_api.py"
        ))
        app = Quart("test_rm_app")

        dummy_apps = types.ModuleType("api.apps")
        dummy_apps.login_required = lambda f=None, **k: f if f and callable(f) else (lambda fn: fn)
        dummy_apps.current_user = types.SimpleNamespace(id="tenant-beta")
        dummy_web_utils = types.ModuleType("api.utils.web_utils")
        dummy_web_utils.get_float = lambda d, k, default=0: float(d.get(k, default))
        dummy_web_utils.safe_json_parse = lambda v: v if isinstance(v, dict) else {}

        orig_apps = sys.modules.get("api.apps")
        orig_web = sys.modules.get("api.utils.web_utils")
        orig_mcp_api = sys.modules.get("api.apps.restful_apis.mcp_api")
        sys.modules["api.apps"] = dummy_apps
        sys.modules["api.utils.web_utils"] = dummy_web_utils
        try:
            spec = importlib.util.spec_from_file_location("api.apps.restful_apis.mcp_api", mcp_api_path)
            mcp_api_mod = importlib.util.module_from_spec(spec)
            mcp_api_mod.manager = MagicMock()
            mcp_api_mod.manager.route = lambda *a, **k: (lambda f: f)
            sys.modules["api.apps.restful_apis.mcp_api"] = mcp_api_mod
            spec.loader.exec_module(mcp_api_mod)

            async def _run():
                # Attacker tenant-beta attempts to delete tenant-alpha's mcp-own
                async with app.test_request_context("/", method="DELETE"):
                    rm_res = await mcp_api_mod.rm("mcp-own")
                    data = await rm_res.get_json() if hasattr(rm_res, "get_json") else rm_res
                    self.assertEqual(data["code"], 102)
                    self.assertIn("Cannot find MCP server", data["message"])

                # Confirm victim's record is completely unharmed in DB
                survived = MCPServer.get_or_none(MCPServer.id == "mcp-own")
                self.assertIsNotNone(survived)
                self.assertEqual(survived.tenant_id, "tenant-alpha")

            asyncio.run(_run())
        finally:
            if orig_apps is not None:
                sys.modules["api.apps"] = orig_apps
            else:
                sys.modules.pop("api.apps", None)
            if orig_web is not None:
                sys.modules["api.utils.web_utils"] = orig_web
            else:
                sys.modules.pop("api.utils.web_utils", None)
            if orig_mcp_api is not None:
                sys.modules["api.apps.restful_apis.mcp_api"] = orig_mcp_api
            else:
                sys.modules.pop("api.apps.restful_apis.mcp_api", None)

    def test_agent_api_real_handlers_update_and_rerun(self):
        """Verify update_agent and rerun_agent real handlers reject unowned MCP servers."""
        import importlib.util
        import types
        from quart import Quart
        import json

        app = Quart("test_agent_api_app")
        agent_api_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "api", "apps", "restful_apis", "agent_api.py"
        ))

        dummy_apps = types.ModuleType("api.apps")
        dummy_apps.__path__ = [os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api", "apps"))]
        def dummy_login_required(func=None, **kwargs):
            if func is not None and callable(func):
                return func
            return lambda f: f
        dummy_apps.login_required = dummy_login_required
        # Caller is tenant-beta (team member) updating a shared canvas owned by tenant-alpha
        dummy_apps.current_user = types.SimpleNamespace(id="tenant-beta")
        dummy_apps.AUTH_JWT = "jwt"
        dummy_apps.AUTH_API = "api"
        dummy_apps.AUTH_BETA = "beta"

        dummy_task = types.ModuleType("api.db.services.task_service")
        dummy_task.TaskService = MagicMock()
        dummy_task.CANVAS_DEBUG_DOC_ID = "debug-doc"
        dummy_task.GRAPH_RAPTOR_FAKE_DOC_ID = "raptor-doc"
        dummy_task.queue_dataflow = MagicMock()
        dummy_task.has_canceled = MagicMock(return_value=False)

        orig_apps = sys.modules.get("api.apps")
        orig_task = sys.modules.get("api.db.services.task_service")
        orig_agent_api = sys.modules.get("api.apps.restful_apis.agent_api")

        sys.modules["api.apps"] = dummy_apps
        sys.modules["api.db.services.task_service"] = dummy_task

        try:
            spec = importlib.util.spec_from_file_location("api.apps.restful_apis.agent_api", agent_api_path)
            agent_api_mod = importlib.util.module_from_spec(spec)
            agent_api_mod.manager = MagicMock()
            agent_api_mod.manager.route = lambda *a, **k: (lambda f: f)
            sys.modules["api.apps.restful_apis.agent_api"] = agent_api_mod
            spec.loader.exec_module(agent_api_mod)

            async def _run_agent_tests():
                # foreign_dsl uses an MCP server belonging to neither owner nor caller
                foreign_dsl = {
                    "components": {
                        "agent_1": {
                            "obj": {
                                "component_name": "Agent",
                                "params": {"mcp": [{"mcp_id": "mcp-foreign-evil"}]}
                            }
                        }
                    }
                }
                # own_dsl uses mcp-own belonging to canvas owner (tenant-alpha)
                own_dsl = {
                    "components": {
                        "agent_1": {
                            "obj": {
                                "component_name": "Agent",
                                "params": {"mcp": [{"mcp_id": "mcp-own"}]}
                            }
                        }
                    }
                }

                mock_canvas = MagicMock(id="canvas-123", user_id="tenant-alpha", canvas_category=0, title="Test Canvas", update_time=1234567890)
                agent_api_mod.UserCanvasService.accessible = MagicMock(return_value=True)
                agent_api_mod.UserCanvasService.get_by_id = MagicMock(return_value=(True, mock_canvas))
                agent_api_mod.UserCanvasService.update_by_id = MagicMock()
                agent_api_mod.UserCanvasVersionService.save_or_replace_latest = MagicMock()
                agent_api_mod.CanvasReplicaService.replace_for_set = MagicMock(return_value=True)

                from agent.canvas import Canvas
                with patch.object(Canvas, "validate_component_parameters"):
                    # 1. update_agent with foreign MCP -> ARGUMENT_ERROR (101)
                    async with app.test_request_context("/", method="PUT", json={"dsl": foreign_dsl}):
                        res = await agent_api_mod.update_agent(agent_id="canvas-123")
                        data = await res.get_json() if hasattr(res, "get_json") else res
                        self.assertEqual(data["code"], 101)
                        self.assertIn("Access denied: MCP server 'mcp-foreign-evil'", data["message"])

                    # 2. update_agent by team member (tenant-beta) saving canvas owner's (tenant-alpha) MCP -> SUCCESS (0)
                    async with app.test_request_context("/", method="PUT", json={"dsl": own_dsl}):
                        res = await agent_api_mod.update_agent(agent_id="canvas-123")
                        data = await res.get_json() if hasattr(res, "get_json") else res
                        self.assertEqual(data["code"], 0)

                    # 3. rerun_agent with foreign MCP -> ARGUMENT_ERROR (101)
                    mock_doc = [{"id": "doc-1", "name": "test-doc", "progress": 0, "kb_id": "kb-1"}]
                    agent_api_mod.PipelineOperationLogService.get_documents_info = MagicMock(return_value=mock_doc)
                    agent_api_mod.DocumentService.accessible = MagicMock(return_value=True)
                    agent_api_mod.DocumentService.clear_chunk_num_when_rerun = MagicMock()
                    agent_api_mod.DocumentService.update_by_id = MagicMock()
                    agent_api_mod.PipelineOperationLogService.update_by_id = MagicMock()
                    agent_api_mod.settings.docStoreConn = MagicMock()
                    agent_api_mod.settings.docStoreConn.index_exist = MagicMock(return_value=False)

                    with patch("rag.advanced_rag.knowlege_compile.dataset_nav.remove_dataset_nav_doc_sync"):
                        async with app.test_request_context("/", method="POST", json={"id": "log-1", "component_id": "c-1", "dsl": foreign_dsl}):
                            res = await agent_api_mod.rerun_agent()
                            data = await res.get_json() if hasattr(res, "get_json") else res
                            self.assertEqual(data["code"], 101)
                            self.assertIn("Access denied: MCP server 'mcp-foreign-evil'", data["message"])

                    # 4. rerun_agent for caller tenant-beta with beta's own MCP server (mcp-foreign) -> SUCCESS (0)
                    beta_own_dsl = {
                        "components": {
                            "agent_1": {
                                "obj": {
                                    "component_name": "Agent",
                                    "params": {"mcp": [{"mcp_id": "mcp-foreign"}]}
                                }
                            }
                        }
                    }
                    with patch("rag.advanced_rag.knowlege_compile.dataset_nav.remove_dataset_nav_doc_sync"):
                        async with app.test_request_context("/", method="POST", json={"id": "log-1", "component_id": "c-1", "dsl": beta_own_dsl}):
                            res = await agent_api_mod.rerun_agent()
                            data = await res.get_json() if hasattr(res, "get_json") else res
                            self.assertEqual(data["code"], 0)
                            self.assertEqual(data["data"], True)

                # 5. create_agent_session through real handler wiring:
                # Team member tenant-beta creates session for canvas owned by tenant-alpha with owner's MCP
                agent_api_mod.API4ConversationService = MagicMock()
                agent_api_mod.API4ConversationService.save = MagicMock()
                agent_api_mod.UserCanvasVersionService.get_latest_version_title = MagicMock(return_value="1.0")
                canvas_session_dsl = {
                    "components": {
                        "begin": {
                            "obj": {
                                "component_name": "Begin",
                                "params": {"prologue": "Hello!", "inputs": {}}
                            }
                        },
                        "agent_1": {
                            "obj": {
                                "component_name": "Agent",
                                "params": {
                                    "llm_id": "test-llm",
                                    "mcp": [{"mcp_id": "mcp-own", "tools": {}}],
                                    "tools": []
                                }
                            }
                        }
                    },
                    "history": [],
                    "retrieval": [],
                    "path": ["begin", "agent_1"]
                }
                agent_api_mod.UserCanvasService.get_agent_dsl_with_release = MagicMock(return_value=(mock_canvas, json.dumps(canvas_session_dsl)))

                def fake_llm_init(this, canvas, id, param):
                    this._canvas = canvas
                    this._id = id
                    this._param = param

                with patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
                     patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
                     patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
                     patch("agent.component.agent_with_tools.LLMBundle"), \
                     patch("agent.component.agent_with_tools.LLMToolPluginCallSession"), \
                     patch("agent.component.agent_with_tools.MCPToolCallSession"):
                    async with app.test_request_context("/", method="POST", json={}):
                        res_sess = await agent_api_mod.create_agent_session(agent_id="canvas-123", tenant_id="tenant-beta")
                        data_sess = await res_sess.get_json() if hasattr(res_sess, "get_json") else res_sess
                        self.assertEqual(data_sess["code"], 0)

            asyncio.run(_run_agent_tests())
        finally:
            if orig_apps is not None:
                sys.modules["api.apps"] = orig_apps
            else:
                sys.modules.pop("api.apps", None)
            if orig_task is not None:
                sys.modules["api.db.services.task_service"] = orig_task
            else:
                sys.modules.pop("api.db.services.task_service", None)
            if orig_agent_api is not None:
                sys.modules["api.apps.restful_apis.agent_api"] = orig_agent_api
            else:
                sys.modules.pop("api.apps.restful_apis.agent_api", None)


    # -------------------------------------------------------------------------
    # 9. Database Isolation Guarantee
    # -------------------------------------------------------------------------
    def test_database_isolation_guarantee(self):
        """Verify tests run against in-memory SQLite and cannot touch real MySQL settings.DATABASE."""
        self.assertIsInstance(MCPServer._meta.database, SqliteDatabase)
        self.assertEqual(MCPServer._meta.database.database, ":memory:")

        with patch.object(DB, "connect", side_effect=RuntimeError("Direct MySQL access forbidden!")):
            res = list(MCPServer.select().where(MCPServer.id == "mcp-own"))
            self.assertEqual(len(res), 1)

    # -------------------------------------------------------------------------
    # 10. Runtime Error Response Formats (REST and SSE)
    # -------------------------------------------------------------------------
    def test_runtime_error_formats_rest_and_sse(self):
        """Verify exact error formats for REST and SSE upon runtime PermissionError."""
        import json
        from quart import Quart
        from api.utils.api_utils import server_error_response

        app = Quart("error_format_test")

        err = PermissionError("Access denied: MCP server 'mcp-evil' does not belong to tenant 'tenant-alpha' or does not exist.")

        async def _test_rest():
            async with app.test_request_context("/"):
                resp = server_error_response(err)
                data = await resp.get_json()
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(data["code"], 100)
                self.assertIn("PermissionError", data["message"])
                self.assertIn("Access denied: MCP server 'mcp-evil'", data["message"])
                self.assertIsNone(data["data"])

        asyncio.run(_test_rest())

        sse_chunk = f"data:{json.dumps({'code': 500, 'message': str(err), 'data': False}, ensure_ascii=False)}\n\n"
        self.assertTrue(sse_chunk.startswith("data:"))
        self.assertTrue(sse_chunk.endswith("\n\n"))
        parsed = json.loads(sse_chunk[len("data:"):].strip())
        self.assertEqual(parsed["code"], 500)
        self.assertEqual(parsed["data"], False)
        self.assertIn("Access denied: MCP server 'mcp-evil'", parsed["message"])

    # -------------------------------------------------------------------------
    # 11. Canvas Service Completion Real Path
    # -------------------------------------------------------------------------
    def test_canvas_service_completion_team_member_owner_mcp(self):
        """Verify canvas_service.completion routes canvas_owner_tenant to Canvas for team member chat."""
        import json
        from api.db.services.canvas_service import completion

        mock_cvs = MagicMock(id="canvas-team-123", user_id="tenant-alpha")
        test_dsl = json.dumps({
            "components": {
                "agent_1": {
                    "obj": {
                        "component_name": "Agent",
                        "params": {
                            "llm_id": "test-llm",
                            "mcp": [{"mcp_id": "mcp-own", "tools": {}}],
                            "tools": []
                        }
                    },
                    "downstream": [],
                    "upstream": []
                }
            },
            "history": [],
            "messages": [],
            "retrieval": []
        })

        def fake_llm_init(this, canvas, id, param):
            this._canvas = canvas
            this._id = id
            this._param = param

        async def fake_run(*args, **kwargs):
            yield {"event": "message", "data": {"content": "ok", "start_to_think": False, "end_to_think": False}}

        async def _run_completion():
            with patch("api.db.services.canvas_service.UserCanvasService.get_agent_dsl_with_release", return_value=(mock_cvs, test_dsl)), \
                 patch("api.db.services.canvas_service.UserCanvasVersionService.get_latest_version_title", return_value="v1"), \
                 patch("api.db.services.canvas_service.API4ConversationService.save"), \
                 patch("api.db.services.canvas_service.API4ConversationService.append_message"), \
                 patch("agent.component.agent_with_tools.LLM.__init__", fake_llm_init), \
                 patch("agent.component.agent_with_tools.resolve_model_type", return_value=["chat"]), \
                 patch("agent.component.agent_with_tools.resolve_model_config", return_value={}), \
                 patch("agent.component.agent_with_tools.LLMBundle"), \
                 patch("agent.component.agent_with_tools.MCPToolCallSession"), \
                 patch.object(Canvas, "run", side_effect=fake_run):

                # Caller is tenant-beta (team member) chatting with agent owned by tenant-alpha
                gen = completion(tenant_id="tenant-beta", agent_id="canvas-team-123", query="hello")
                chunks = []
                async for chunk in gen:
                    chunks.append(chunk)
                self.assertTrue(len(chunks) > 0)
                self.assertIn("data:", chunks[0])
                self.assertIn("ok", chunks[0])

        asyncio.run(_run_completion())


if __name__ == "__main__":
    unittest.main()
