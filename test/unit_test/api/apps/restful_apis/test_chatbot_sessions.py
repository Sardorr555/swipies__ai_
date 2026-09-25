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
"""Unit tests for chatbot session listing and visitor isolation in bot_api.py."""

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


class _PassthroughManager:
    def route(self, *_args, **_kwargs):
        return lambda func: func


def _stub(monkeypatch, name, **attrs):
    mod = ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


async def _passthrough_thread_pool_exec(fn, *args, **kwargs):
    return fn(*args, **kwargs)


def _load_bot_api_for_sessions(monkeypatch, *, dialog_exists=True, dialog_tenant="tenant-1", request_headers=None, request_args=None):
    request_headers = request_headers or {}
    request_args = request_args or {}

    calls = {}

    dialog_service = SimpleNamespace(
        get_by_id=lambda d_id: (dialog_exists, SimpleNamespace(
            id=d_id,
            tenant_id=dialog_tenant,
            status="1",
            name="Test Dialog",
            icon="avatar.png",
            prompt_config={"prologue": "Hi"}
        )) if dialog_exists else (False, None),
    )

    def _get_list(dialog_id, tenant_id, page_number, items_per_page, orderby, desc, id=None, user_id=None, **kwargs):
        calls["get_list"] = {
            "dialog_id": dialog_id,
            "tenant_id": tenant_id,
            "page_number": page_number,
            "items_per_page": items_per_page,
            "user_id": user_id,
        }
        # Simulate returned sessions
        return 1, [
            {
                "id": "sess-123",
                "dialog_id": dialog_id,
                "name": "Hello world",
                "user_id": user_id,
                "create_time": 1000,
                "update_time": 1050,
                "message": [
                    {"role": "user", "content": "Hello", "id": "m1"},
                    {"role": "assistant", "content": "Hi there", "id": "m2"}
                ]
            }
        ]

    api4_service = SimpleNamespace(
        get_list=_get_list,
        get_by_id=lambda s_id: (True, SimpleNamespace(id=s_id, dialog_id="diag-1", user_id="user-1")),
        save=lambda **kwargs: calls.__setitem__("save", kwargs),
    )

    req_obj = SimpleNamespace(
        headers=request_headers,
        args=request_args,
    )

    class _MockResponse:
        def __init__(self, *a, **k):
            self.mimetype = k.get("mimetype", "text/plain")
            self.headers = SimpleNamespace(add_header=lambda *args, **kwargs: None)

    _stub(monkeypatch, "quart", Response=_MockResponse, request=req_obj)
    _stub(monkeypatch, "api.apps", AUTH_BETA="beta", login_required=lambda *_a, **_k: (lambda func: func))
    _stub(monkeypatch, "agent.canvas", Canvas=lambda *a, **k: SimpleNamespace(get_component_input_form=lambda _n: {}, get_prologue=lambda: "", get_mode=lambda: "agent"))
    _stub(monkeypatch, "api.db.db_models", APIToken=SimpleNamespace(query=lambda **_k: []))
    _stub(monkeypatch, "api.db.services.api_service", API4ConversationService=api4_service)
    _stub(monkeypatch, "api.db.services.canvas_service", UserCanvasService=SimpleNamespace(accessible=lambda *_a, **_k: True), completion=lambda *_a, **_k: None)
    _stub(monkeypatch, "api.db.services.user_canvas_version", UserCanvasVersionService=SimpleNamespace())
    _stub(monkeypatch, "api.db.services.conversation_service", async_iframe_completion=lambda *_a, **_k: None)
    _stub(monkeypatch, "api.db.services.dialog_service", DialogService=dialog_service, async_ask=lambda *_a, **_k: None, gen_mindmap=lambda *_a, **_k: None)
    _stub(monkeypatch, "api.db.services.doc_metadata_service", DocMetadataService=SimpleNamespace())
    _stub(monkeypatch, "api.db.services.knowledgebase_service", KnowledgebaseService=SimpleNamespace())
    _stub(monkeypatch, "api.db.services.llm_service", LLMBundle=SimpleNamespace(), resolve_llm_setting=lambda *_a, **_k: {})
    _stub(monkeypatch, "common.metadata_utils", apply_meta_data_filter=lambda *_a, **_k: None)
    _stub(monkeypatch, "api.db.services.search_service", SearchService=SimpleNamespace())
    _stub(monkeypatch, "api.db.services.user_service", TenantService=SimpleNamespace(), UserTenantService=SimpleNamespace())
    _stub(monkeypatch, "api.db.joint_services.tenant_model_service", get_tenant_default_model_by_type=lambda *_a, **_k: None, get_model_config_from_provider_instance=lambda *_a, **_k: None, resolve_model_config=lambda *_a, **_k: None)
    _stub(monkeypatch, "common.misc_utils", get_uuid=lambda: "uuid", thread_pool_exec=_passthrough_thread_pool_exec)
    _stub(
        monkeypatch,
        "api.utils.api_utils",
        add_tenant_id_to_kwargs=lambda func: func,
        check_duplicate_ids=lambda *_a, **_k: None,
        get_error_data_result=lambda message="Sorry", code=102, **_k: {"code": code, "message": message, "data": None},
        get_json_result=lambda code=0, message="success", data=None: {"code": code, "message": message, "data": data},
        get_result=lambda **kwargs: {"code": 0, "data": kwargs.get("data")},
        get_request_json=lambda: {"stream": False},
        server_error_response=lambda exc: {"code": 500, "message": str(exc)},
        validate_request=lambda *_a, **_k: lambda func: func,
    )
    _stub(monkeypatch, "api.utils.pagination_utils", DEFAULT_PAGE=1, DEFAULT_PAGE_SIZE=30, validate_rest_api_page=lambda p: max(p, 1), validate_rest_api_page_size=lambda size: min(max(size, 1), 100))
    _stub(monkeypatch, "rag.app.tag", label_question=lambda *_a, **_k: None)
    _stub(monkeypatch, "rag.prompts.template", load_prompt=lambda *_a, **_k: "")
    _stub(monkeypatch, "rag.prompts.generator", cross_languages=lambda *_a, **_k: None, keyword_extraction=lambda *_a, **_k: None)
    _stub(monkeypatch, "common.constants", RetCode=SimpleNamespace(ARGUMENT_ERROR=101, AUTHENTICATION_ERROR=108, SUCCESS=0), LLMType=SimpleNamespace(), StatusEnum=SimpleNamespace(VALID=SimpleNamespace(value="1")))
    _stub(monkeypatch, "common", settings=SimpleNamespace())
    _stub(monkeypatch, "common.settings", retriever=SimpleNamespace(), kg_retriever=SimpleNamespace())
    _stub(monkeypatch, "api.utils.reference_metadata_utils", enrich_chunks_with_document_metadata=lambda *_a, **_k: None, resolve_reference_metadata_preferences=lambda *_a, **_k: None)
    _stub(monkeypatch, "rag.utils.web_search_conn", has_web_search_provider=lambda *_a, **_k: False)

    repo_root = Path(__file__).resolve().parents[5]
    module_path = repo_root / "api" / "apps" / "restful_apis" / "bot_api.py"
    spec = importlib.util.spec_from_file_location("test_chatbot_sessions_bot_api", module_path)
    module = importlib.util.module_from_spec(spec)
    module.manager = _PassthroughManager()
    monkeypatch.setitem(sys.modules, "test_chatbot_sessions_bot_api", module)
    spec.loader.exec_module(module)
    return module, calls


class TestChatbotSessions:
    """Test suite for GET /api/v1/chatbots/<dialog_id>/sessions."""

    def test_missing_visitor_id_fails_hard(self, monkeypatch):
        module, calls = _load_bot_api_for_sessions(monkeypatch, request_headers={})
        result = asyncio.run(module.chatbot_sessions(dialog_id="diag-1", tenant_id="tenant-1"))

        assert result["code"] == 101  # ARGUMENT_ERROR
        assert "X-Visitor-Id" in result["message"]
        assert "get_list" not in calls

    def test_invalid_visitor_id_format_fails_hard(self, monkeypatch):
        # Sequential or malicious non-UUIDv4 strings must fail immediately
        module, calls = _load_bot_api_for_sessions(monkeypatch, request_headers={"X-Visitor-Id": "not-a-valid-uuid"})
        result = asyncio.run(module.chatbot_sessions(dialog_id="diag-1", tenant_id="tenant-1"))

        assert result["code"] == 101
        assert "X-Visitor-Id" in result["message"]
        assert "get_list" not in calls

    def test_valid_visitor_id_returns_sessions(self, monkeypatch):
        valid_uuid = "c3b53f60-9884-486a-9fa5-f93ea8c772cb"
        module, calls = _load_bot_api_for_sessions(
            monkeypatch,
            request_headers={"X-Visitor-Id": valid_uuid},
            request_args={"page": "1", "page_size": "10"}
        )
        result = asyncio.run(module.chatbot_sessions(dialog_id="diag-1", tenant_id="tenant-1"))

        assert result["code"] == 0
        assert "get_list" in calls
        assert calls["get_list"]["user_id"] == valid_uuid
        assert calls["get_list"]["dialog_id"] == "diag-1"
        assert len(result["data"]) == 1
        assert result["data"][0]["id"] == "sess-123"

    def test_inaccessible_dialog_denied(self, monkeypatch):
        valid_uuid = "c3b53f60-9884-486a-9fa5-f93ea8c772cb"
        module, calls = _load_bot_api_for_sessions(
            monkeypatch,
            dialog_exists=False,
            request_headers={"X-Visitor-Id": valid_uuid}
        )
        result = asyncio.run(module.chatbot_sessions(dialog_id="diag-wrong", tenant_id="tenant-1"))

        assert result["code"] == 102
        assert "get_list" not in calls

    def test_completions_rejects_session_of_different_visitor(self, monkeypatch):
        visitor_a = "c3b53f60-9884-486a-9fa5-f93ea8c772cb"
        visitor_b = "11111111-2222-4333-8444-555555555555"

        # Session belongs to visitor_b
        session_id = "sess-owned-by-b"
        api4_stub = SimpleNamespace(
            get_by_id=lambda s_id: (True, SimpleNamespace(id=s_id, dialog_id="diag-1", user_id=visitor_b))
        )
        module, _ = _load_bot_api_for_sessions(
            monkeypatch,
            request_headers={"X-Visitor-Id": visitor_a}
        )
        monkeypatch.setattr(module, "API4ConversationService", api4_stub)

        async def _mock_req():
            return {"session_id": session_id, "stream": False, "question": "hi"}

        monkeypatch.setattr(module, "get_request_json", _mock_req)

        result = asyncio.run(module.chatbot_completions(dialog_id="diag-1", tenant_id="tenant-1"))
        assert result["code"] == 102
        assert "Authentication error" in result["message"]

    def test_completions_accepts_session_of_same_visitor(self, monkeypatch):
        visitor_a = "c3b53f60-9884-486a-9fa5-f93ea8c772cb"
        session_id = "sess-owned-by-a"
        api4_stub = SimpleNamespace(
            get_by_id=lambda s_id: (True, SimpleNamespace(id=s_id, dialog_id="diag-1", user_id=visitor_a))
        )

        async def _mock_iframe_completion(*a, **k):
            yield {"answer": "pong"}

        module, _ = _load_bot_api_for_sessions(
            monkeypatch,
            request_headers={"X-Visitor-Id": visitor_a}
        )
        monkeypatch.setattr(module, "API4ConversationService", api4_stub)
        monkeypatch.setattr(module, "iframe_completion", _mock_iframe_completion)

        async def _mock_req():
            return {"session_id": session_id, "stream": False, "question": "ping"}

        monkeypatch.setattr(module, "get_request_json", _mock_req)

        result = asyncio.run(module.chatbot_completions(dialog_id="diag-1", tenant_id="tenant-1"))
        assert result["code"] == 0
        assert result["data"]["answer"] == "pong"

    def test_completions_rejects_legacy_session_without_user_id(self, monkeypatch):
        visitor_id = "c3b53f60-9884-486a-9fa5-f93ea8c772cb"
        session_id = "sess-legacy-null-user-id"

        # Legacy session created before migration where conv.user_id is None / null
        legacy_session = SimpleNamespace(id=session_id, dialog_id="diag-1", user_id=None)
        api4_stub = SimpleNamespace(
            get_by_id=lambda s_id: (True, legacy_session)
        )

        headers = {"X-Visitor-Id": visitor_id}
        payload = {"session_id": session_id, "stream": False, "question": "Access legacy history"}

        module, _ = _load_bot_api_for_sessions(
            monkeypatch,
            request_headers=headers
        )
        monkeypatch.setattr(module, "API4ConversationService", api4_stub)

        async def _mock_req():
            return payload

        monkeypatch.setattr(module, "get_request_json", _mock_req)

        # Step-by-step tracing
        print(f"\n[TRACE] Step 1 - Visitor: visitor_id={visitor_id}")
        print(f"[TRACE] Step 2 - Target Session: session_id={session_id}, conv.user_id={legacy_session.user_id}")
        print(f"[TRACE] Step 3 - Request: headers={headers}, payload={payload}")

        result = asyncio.run(module.chatbot_completions(dialog_id="diag-1", tenant_id="tenant-1"))

        print(f"[TRACE] Step 4 - Response: {result}")

        # Verify Deny-by-Default: conv.user_id != visitor_id (None != valid UUID)
        assert result["code"] == 102
        assert "Authentication error" in result["message"]

    def test_chatbot_sessions_strict_isolation_between_visitors(self, monkeypatch):
        visitor_a = "c3b53f60-9884-486a-9fa5-f93ea8c772cb"
        visitor_b = "11111111-2222-4333-8444-555555555555"

        mock_db_conversations = [
            {"id": "sess-a1", "dialog_id": "diag-1", "user_id": visitor_a, "name": "Conv A1", "message": []},
            {"id": "sess-a2", "dialog_id": "diag-1", "user_id": visitor_a, "name": "Conv A2", "message": []},
            {"id": "sess-b1", "dialog_id": "diag-1", "user_id": visitor_b, "name": "Conv B1", "message": []},
            {"id": "sess-b2", "dialog_id": "diag-1", "user_id": visitor_b, "name": "Conv B2", "message": []},
            {"id": "sess-legacy-null", "dialog_id": "diag-1", "user_id": None, "name": "Legacy Session", "message": []},
        ]

        print(f"\n[TRACE] === Setup Mock DB Records ===")
        print(f"[TRACE] Visitor A: {visitor_a}")
        print(f"[TRACE] Visitor B: {visitor_b}")
        print(f"[TRACE] Total conversations in DB: {len(mock_db_conversations)}")
        for item in mock_db_conversations:
            print(f"[TRACE]   DB Record: id={item['id']} user_id={item['user_id']} name={item['name']}")

        def _isolated_get_list(dialog_id, tenant_id, page_number, items_per_page, orderby, desc, id=None, user_id=None, **kwargs):
            # Mirror Peewee SQL query logic: where(cls.model.dialog_id == dialog_id).where(cls.model.user_id == user_id)
            filtered = [
                s for s in mock_db_conversations
                if s["dialog_id"] == dialog_id and s["user_id"] == user_id and user_id is not None
            ]
            return len(filtered), filtered

        # -------------------------------------------------------------
        # 1. Visitor A calls chatbot_sessions
        # -------------------------------------------------------------
        headers_a = {"X-Visitor-Id": visitor_a}
        args_a = {"page": "1", "page_size": "20"}
        module_a, _ = _load_bot_api_for_sessions(
            monkeypatch,
            request_headers=headers_a,
            request_args=args_a
        )
        monkeypatch.setattr(module_a.API4ConversationService, "get_list", _isolated_get_list)

        print(f"\n[TRACE] === Request 1: Visitor A ===")
        print(f"[TRACE] Target: GET /api/v1/chatbots/diag-1/sessions")
        print(f"[TRACE] Headers: {headers_a}")
        print(f"[TRACE] Args: {args_a}")

        result_a = asyncio.run(module_a.chatbot_sessions(dialog_id="diag-1", tenant_id="tenant-1"))
        returned_ids_a = [s["id"] for s in result_a.get("data", [])]

        print(f"[TRACE] Response 1: code={result_a.get('code')}, count={len(returned_ids_a)}, session_ids={returned_ids_a}")
        print(f"[TRACE] Full Response 1 Body: {result_a}")

        assert result_a["code"] == 0
        assert returned_ids_a == ["sess-a1", "sess-a2"]
        assert "sess-b1" not in returned_ids_a
        assert "sess-b2" not in returned_ids_a
        assert "sess-legacy-null" not in returned_ids_a

        # -------------------------------------------------------------
        # 2. Visitor B calls chatbot_sessions
        # -------------------------------------------------------------
        headers_b = {"X-Visitor-Id": visitor_b}
        args_b = {"page": "1", "page_size": "20"}
        module_b, _ = _load_bot_api_for_sessions(
            monkeypatch,
            request_headers=headers_b,
            request_args=args_b
        )
        monkeypatch.setattr(module_b.API4ConversationService, "get_list", _isolated_get_list)

        print(f"\n[TRACE] === Request 2: Visitor B ===")
        print(f"[TRACE] Target: GET /api/v1/chatbots/diag-1/sessions")
        print(f"[TRACE] Headers: {headers_b}")
        print(f"[TRACE] Args: {args_b}")

        result_b = asyncio.run(module_b.chatbot_sessions(dialog_id="diag-1", tenant_id="tenant-1"))
        returned_ids_b = [s["id"] for s in result_b.get("data", [])]

        print(f"[TRACE] Response 2: code={result_b.get('code')}, count={len(returned_ids_b)}, session_ids={returned_ids_b}")
        print(f"[TRACE] Full Response 2 Body: {result_b}")

        assert result_b["code"] == 0
        assert returned_ids_b == ["sess-b1", "sess-b2"]
        assert "sess-a1" not in returned_ids_b
        assert "sess-a2" not in returned_ids_b
        assert "sess-legacy-null" not in returned_ids_b

        # -------------------------------------------------------------
        # 3. Request without X-Visitor-Id (Unauthenticated / Legacy access attempt)
        # -------------------------------------------------------------
        headers_c = {}
        module_c, calls_c = _load_bot_api_for_sessions(
            monkeypatch,
            request_headers=headers_c,
            request_args={"page": "1", "page_size": "20"}
        )
        monkeypatch.setattr(module_c.API4ConversationService, "get_list", _isolated_get_list)

        print(f"\n[TRACE] === Request 3: Missing X-Visitor-Id (Legacy/Null Protection) ===")
        print(f"[TRACE] Target: GET /api/v1/chatbots/diag-1/sessions")
        print(f"[TRACE] Headers: {headers_c} (no visitor ID provided)")

        result_c = asyncio.run(module_c.chatbot_sessions(dialog_id="diag-1", tenant_id="tenant-1"))

        print(f"[TRACE] Response 3: code={result_c.get('code')}, message={result_c.get('message')}, data={result_c.get('data')}")
        print(f"[TRACE] Full Response 3 Body: {result_c}")
        print(f"[TRACE] DB Query executed: {'get_list' in calls_c}")

        # Strict validation asserts
        assert result_c["code"] == 101  # RetCode.ARGUMENT_ERROR
        assert "Valid 'X-Visitor-Id' header is required." in result_c["message"]
        assert "get_list" not in calls_c  # Hard stop before DB query: zero records leaked!
        print(f"[TRACE] === Strict Isolation Verified: Zero Leakage Across A, B, and Legacy Records ===\n")

    def test_completions_without_visitor_id_backward_compatibility(self, monkeypatch):
        """Verify AC4: Existing embed snippets without X-Visitor-Id continue working seamlessly.
        POST /completions without X-Visitor-Id does NOT fail or return 400/101 error.
        Hard validation is strictly isolated to the new /sessions endpoint.
        """
        async def _mock_iframe_completion(*a, **k):
            yield {"answer": "Backward compatibility confirmed: legacy embed client responds successfully."}

        # 1. Non-streaming completions without X-Visitor-Id header
        module, _ = _load_bot_api_for_sessions(
            monkeypatch,
            request_headers={}  # No X-Visitor-Id header sent by legacy client
        )
        monkeypatch.setattr(module, "iframe_completion", _mock_iframe_completion)

        async def _mock_req_json():
            return {
                "stream": False,
                "question": "Question from existing production client without visitor identity"
            }

        monkeypatch.setattr(module, "get_request_json", _mock_req_json)

        print("\n[TRACE] === AC4 Regression: Legacy Client Calling POST /completions without X-Visitor-Id ===")
        print("[TRACE] Request Headers: {} (no X-Visitor-Id)")
        print("[TRACE] Request Payload: {'stream': False, 'question': '...'}")

        result = asyncio.run(module.chatbot_completions(dialog_id="diag-1", tenant_id="tenant-1"))
        print(f"[TRACE] Response: code={result.get('code')}, data={result.get('data')}")

        assert result["code"] == 0, f"Expected 0 (success) but got {result.get('code')}: {result.get('message')}"
        assert "Backward compatibility confirmed" in result["data"]["answer"]

        # 2. SSE Streaming completions without X-Visitor-Id header
        async def _mock_req_stream():
            return {
                "stream": True,
                "question": "Streaming question from existing production client"
            }

        monkeypatch.setattr(module, "get_request_json", _mock_req_stream)
        stream_resp = asyncio.run(module.chatbot_completions(dialog_id="diag-1", tenant_id="tenant-1"))

        print(f"[TRACE] Streaming Response Mimetype: {getattr(stream_resp, 'mimetype', None)}")
        assert stream_resp is not None
        assert stream_resp.mimetype == "text/event-stream"
        print("[TRACE] === AC4 Verified: 100% Backward Compatibility Preserved for Legacy Embed Clients ===\n")




