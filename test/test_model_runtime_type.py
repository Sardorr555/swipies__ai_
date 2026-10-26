"""Provider capability bitmasks must select the requested runtime factory.

Execute the actual resolver/factory methods with isolated provider records,
without importing deployment settings, accessing a DB or calling an LLM.
"""
import ast
import enum
import json
import logging
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest
from common.constants import ActiveStatusEnum, LLMType

ROOT = Path(__file__).resolve().parents[1]


def load_function(relative, name, namespace, class_name=None):
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    if class_name:
        tree = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    node.decorator_list = []
    future = ast.parse("from __future__ import annotations").body
    exec(compile(ast.fix_missing_locations(ast.Module(body=future + [node], type_ignores=[])), str(ROOT / relative), "exec"), namespace)
    return namespace[name]


@pytest.mark.parametrize("stored_type,requested", [(1, "chat"), (2, "embedding"), (9, "chat"), (9, "vision"), ("chat", "chat"), ("embedding", "embedding")])
def test_provider_config_selects_requested_factory(monkeypatch, stored_type, requested):
    provider = SimpleNamespace(id="provider-test", provider_name="TestFactory")
    instance = SimpleNamespace(id="instance-test", api_key="synthetic-test-credential", extra='{"base_url":"https://provider.invalid"}')
    model = SimpleNamespace(model_name="test-model", model_type=stored_type, status=ActiveStatusEnum.ACTIVE.value, extra="{}")
    def query_model(provider_id, instance_id, capability, name):
        assert (provider_id, instance_id, capability, name) == (provider.id, instance.id, requested, "test-model")
        return model
    namespace = {
        "os": os, "enum": enum, "json": json, "LLMType": LLMType, "ActiveStatusEnum": ActiveStatusEnum,
        "logger": logging.getLogger(__name__),
        "split_model_name": lambda name: ("test-model", "default", "TestFactory"),
        "TenantModelProviderService": SimpleNamespace(get_by_tenant_id_and_provider_name=lambda *args: provider),
        "TenantModelService": SimpleNamespace(get_by_provider_id_and_instance_id_and_model_type_and_model_name=query_model),
        "_resolve_instance_for_model": lambda *args: instance,
        "_decode_api_key_config": lambda value: (value, False, None),
        "_lookup_factory_llm_info": lambda *args: {"max_tokens": 4096},
    }
    resolve = load_function("api/db/joint_services/tenant_model_service.py", "get_model_config_from_provider_instance", namespace)
    config = resolve("new-service-tenant", requested, "test-model@default@TestFactory")
    runtime = ModuleType("rag.llm")
    def factory(kind):
        return lambda *args, **kwargs: SimpleNamespace(kind=kind, args=args, kwargs=kwargs)
    for registry, kind in (("ChatModel", "chat"), ("EmbeddingModel", "embedding"), ("CvModel", "vision"), ("OcrModel", "ocr"), ("RerankModel", "rerank"), ("Seq2txtModel", "asr"), ("TTSModel", "tts")):
        setattr(runtime, registry, {"TestFactory": factory(kind)})
    monkeypatch.setitem(sys.modules, "rag.llm", runtime)
    build = load_function("api/db/services/tenant_llm_service.py", "model_instance", {"LLMType": LLMType, "logging": logging}, class_name="TenantLLMService")
    bound = build(None, config)
    assert bound is not None, "Runtime factory received a DB capability bitmask"
    assert bound.kind == requested
    assert bound.kwargs["base_url"] == "https://provider.invalid"
    assert bound.args[0] == "synthetic-test-credential"
    assert config["max_tokens"] == 4096
