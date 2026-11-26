"""Explicit, individually exposed MCP tools for Swipies (directory-compliant).

Each tool maps to exactly one existing tenant API route and is dispatched through
agent_access.execute(), so tenant checks, quotas and licensing still apply.
The generic discover/execute tools and payment tools are hidden unless
SWIPIES_AGENT_LEGACY_TOOLS=1.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
LEGACY_NAMES = frozenset({
    "swipies_list_operations", "swipies_describe_operation", "swipies_execute",
    "swipies_create_subscription_quote", "swipies_create_payment_session", "swipies_check_payment_status",
    "swipies_list_plans",
})
BILLING_TITLES = {
    "swipies_get_account_limits": "Get account limits",
    "swipies_estimate_dataset_plan": "Estimate plan for a dataset",
}
API_DOCS = " API reference: https://help.swipies.app/docs/dev/"

READ = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False, "idempotentHint": True}
WRITE = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}
DELETE = {"readOnlyHint": False, "destructiveHint": True, "openWorldHint": False}


def legacy_enabled():
    return os.getenv("SWIPIES_AGENT_LEGACY_TOOLS", "0") == "1"


def _id(name, desc):
    return {"type": "string", "description": desc, "pattern": ID_RE.pattern}


def _ids(desc):
    return {"type": "array", "items": {"type": "string", "pattern": ID_RE.pattern}, "minItems": 1, "maxItems": 100, "description": desc}


PAGE = {"type": "integer", "minimum": 1, "description": "Page number, starting at 1."}
PAGE_SIZE = {"type": "integer", "minimum": 1, "maximum": 100, "description": "Items per page (1-100, default 30)."}

# name: (title, description, method, path, annotations, write, schema)
CURATED = {
    "swipies_list_datasets": (
        "List knowledge bases",
        "List the user's Swipies knowledge bases (datasets) with their document and chunk counts. Optionally filter by exact name.",
        "GET", "/api/v1/datasets", READ, False,
        {"page": PAGE, "page_size": PAGE_SIZE, "name": {"type": "string", "description": "Exact knowledge base name to filter by."}}, []),
    "swipies_get_dataset": (
        "Get knowledge base details",
        "Get settings and statistics of one Swipies knowledge base by its ID.",
        "GET", "/api/v1/datasets/<dataset_id>", READ, False,
        {"dataset_id": _id("dataset_id", "Knowledge base ID from swipies_list_datasets.")}, ["dataset_id"]),
    "swipies_list_documents": (
        "List documents in a knowledge base",
        "List documents in one Swipies knowledge base with parsing status and progress. Optionally filter by keyword in the file name.",
        "GET", "/api/v1/datasets/<dataset_id>/documents", READ, False,
        {"dataset_id": _id("dataset_id", "Knowledge base ID."), "keywords": {"type": "string", "description": "Keyword to match in document names."}, "page": PAGE, "page_size": PAGE_SIZE}, ["dataset_id"]),
    "swipies_list_document_chunks": (
        "List chunks of a document",
        "List the indexed text chunks of one parsed document, optionally filtered by keyword.",
        "GET", "/api/v1/datasets/<dataset_id>/documents/<document_id>/chunks", READ, False,
        {"dataset_id": _id("dataset_id", "Knowledge base ID."), "document_id": _id("document_id", "Document ID from swipies_list_documents."), "keywords": {"type": "string", "description": "Keyword to match in chunk text."}, "page": PAGE, "page_size": PAGE_SIZE}, ["dataset_id", "document_id"]),
    "swipies_search_knowledge_base": (
        "Search knowledge bases",
        "Semantic and keyword search across one or more Swipies knowledge bases. Returns the most relevant text chunks with document names and similarity scores. Use this to answer questions from the user's own documents.",
        "POST", "/api/v1/retrieval", READ, False,
        {"question": {"type": "string", "minLength": 1, "maxLength": 4000, "description": "What to search for."}, "dataset_ids": _ids("Knowledge base IDs to search."), "document_ids": {**_ids("Optional: limit the search to these document IDs."), "minItems": 0}, "page_size": {"type": "integer", "minimum": 1, "maximum": 50, "description": "Number of chunks to return (default 10)."}, "similarity_threshold": {"type": "number", "minimum": 0, "maximum": 1, "description": "Minimum similarity 0-1 (default 0.2)."}}, ["question", "dataset_ids"]),
    "swipies_list_chat_assistants": (
        "List chat assistants",
        "List the user's Swipies chat assistants (bots) and the knowledge bases each one uses.",
        "GET", "/api/v1/chats", READ, False,
        {"page": PAGE, "page_size": PAGE_SIZE, "name": {"type": "string", "description": "Exact assistant name to filter by."}}, []),
    "swipies_list_chat_sessions": (
        "List conversations of an assistant",
        "List conversation sessions of one Swipies chat assistant, newest first.",
        "GET", "/api/v1/chats/<chat_id>/sessions", READ, False,
        {"chat_id": _id("chat_id", "Chat assistant ID from swipies_list_chat_assistants."), "page": PAGE, "page_size": PAGE_SIZE}, ["chat_id"]),
    "swipies_create_dataset": (
        "Create knowledge base",
        "Create a new empty Swipies knowledge base in the user's account.",
        "POST", "/api/v1/datasets", WRITE, True,
        {"name": {"type": "string", "minLength": 1, "maxLength": 128, "description": "Knowledge base name."}, "description": {"type": "string", "maxLength": 2000, "description": "Optional description."}}, ["name"]),
    "swipies_update_dataset": (
        "Rename or describe knowledge base",
        "Overwrite the name and/or description of an existing Swipies knowledge base. The previous values are replaced; confirm with the user first.",
        "PUT", "/api/v1/datasets/<dataset_id>", DELETE, True,
        {"dataset_id": _id("dataset_id", "Knowledge base ID."), "name": {"type": "string", "minLength": 1, "maxLength": 128, "description": "New name."}, "description": {"type": "string", "maxLength": 2000, "description": "New description."}}, ["dataset_id"]),
    "swipies_upload_document": (
        "Upload document",
        "Upload one file (up to 16 MB, base64-encoded) into a Swipies knowledge base. After uploading, call swipies_parse_documents to index it.",
        "POST", "/api/v1/datasets/<dataset_id>/documents", WRITE, True,
        {"dataset_id": _id("dataset_id", "Knowledge base ID."), "filename": {"type": "string", "minLength": 1, "maxLength": 255, "description": "File name with extension, e.g. policy.pdf."}, "content_base64": {"type": "string", "minLength": 1, "description": "File content, base64-encoded."}, "content_type": {"type": "string", "description": "MIME type, e.g. application/pdf."}}, ["dataset_id", "filename", "content_base64"]),
    "swipies_parse_documents": (
        "Index documents",
        "Start parsing and indexing uploaded documents so they become searchable. Check progress with swipies_list_documents.",
        "POST", "/api/v1/datasets/<dataset_id>/documents/parse", WRITE, True,
        {"dataset_id": _id("dataset_id", "Knowledge base ID."), "document_ids": _ids("Document IDs to index.")}, ["dataset_id", "document_ids"]),
    "swipies_create_chat_assistant": (
        "Create chat assistant",
        "Create a Swipies chat assistant that answers questions from the given knowledge bases.",
        "POST", "/api/v1/chats", WRITE, True,
        {"name": {"type": "string", "minLength": 1, "maxLength": 128, "description": "Assistant name."}, "dataset_ids": _ids("Knowledge base IDs the assistant should use."), "description": {"type": "string", "maxLength": 2000, "description": "Optional description."}}, ["name", "dataset_ids"]),
    "swipies_ask_chat_assistant": (
        "Ask chat assistant",
        "Send a question to a Swipies chat assistant and get its answer with source references. Pass session_id to continue an existing conversation.",
        "POST", "/api/v1/chat/completions", WRITE, True,
        {"chat_id": _id("chat_id", "Chat assistant ID."), "question": {"type": "string", "minLength": 1, "maxLength": 8000, "description": "The user's question."}, "session_id": _id("session_id", "Optional session ID to continue a conversation.")}, ["chat_id", "question"]),
    "swipies_delete_datasets": (
        "Delete knowledge bases",
        "Permanently delete Swipies knowledge bases and all their documents. This cannot be undone; confirm with the user first.",
        "DELETE", "/api/v1/datasets", DELETE, True,
        {"ids": _ids("Knowledge base IDs to delete.")}, ["ids"]),
    "swipies_delete_documents": (
        "Delete documents",
        "Permanently delete documents from a Swipies knowledge base. This cannot be undone; confirm with the user first.",
        "DELETE", "/api/v1/datasets/<dataset_id>/documents", DELETE, True,
        {"dataset_id": _id("dataset_id", "Knowledge base ID."), "ids": _ids("Document IDs to delete.")}, ["dataset_id", "ids"]),
}


def _schema(props, required):
    return {"type": "object", "properties": props, "required": list(required), "additionalProperties": False}


def tool_list(legacy):
    out = []
    for name, (title, desc, _m, _p, ann, _w, props, req) in CURATED.items():
        out.append({"name": name, "title": title, "description": desc, "inputSchema": _schema(props, req), "annotations": {"title": title, **ann}})
    for tool in legacy:
        name = tool["name"]
        if name in BILLING_TITLES:
            title = BILLING_TITLES[name]
            out.append({**tool, "title": title, "annotations": {"title": title, **READ}})
        elif name in LEGACY_NAMES and legacy_enabled():
            ann = dict(tool.get("annotations", {}))
            ann.setdefault("readOnlyHint", False)
            ann.setdefault("destructiveHint", not ann["readOnlyHint"])
            ann.setdefault("openWorldHint", False)
            out.append({**tool, "title": name, "annotations": {"title": name, **ann}})
    return out


def _check_id(value, field):
    if not isinstance(value, str) or not ID_RE.match(value):
        raise ValueError(f"{field} must be a valid ID")
    return value


def _check_ids(value, field):
    if not isinstance(value, list) or not 1 <= len(value) <= 100:
        raise ValueError(f"{field} must be a non-empty array of IDs")
    return [_check_id(v, field) for v in value]


def _page(args, query):
    for key in ("page", "page_size"):
        if key in args:
            if not isinstance(args[key], int) or isinstance(args[key], bool) or args[key] < 1 or args[key] > (100 if key == "page_size" else 100000):
                raise ValueError(f"{key} is out of range")
            query[key] = args[key]


def build(name, args):
    _t, _d, method, path, _a, _w, props, required = CURATED[name]
    unknown = set(args) - set(props)
    if unknown:
        raise ValueError("Unknown argument(s): " + ", ".join(sorted(unknown)))
    for key in required:
        if key not in args or args[key] in ("", None, []):
            raise ValueError(f"{key} is required")
    pp = {k: _check_id(args[k], k) for k in re.findall(r"<([^>]+)>", path)}
    query, body, files = {}, None, None
    if name in ("swipies_list_datasets", "swipies_list_chat_assistants"):
        _page(args, query)
        if "name" in args:
            query["name"] = str(args["name"])[:128]
    elif name in ("swipies_list_documents", "swipies_list_document_chunks"):
        _page(args, query)
        if "keywords" in args:
            query["keywords"] = str(args["keywords"])[:200]
    elif name == "swipies_list_chat_sessions":
        _page(args, query)
    elif name == "swipies_search_knowledge_base":
        body = {"question": str(args["question"])[:4000], "dataset_ids": _check_ids(args["dataset_ids"], "dataset_ids")}
        if args.get("document_ids"):
            body["document_ids"] = _check_ids(args["document_ids"], "document_ids")
        size = args.get("page_size", 10)
        if not isinstance(size, int) or isinstance(size, bool) or not 1 <= size <= 50:
            raise ValueError("page_size must be 1-50")
        body["page_size"] = size
        if "similarity_threshold" in args:
            th = args["similarity_threshold"]
            if not isinstance(th, (int, float)) or isinstance(th, bool) or not 0 <= th <= 1:
                raise ValueError("similarity_threshold must be between 0 and 1")
            body["similarity_threshold"] = th
    elif name in ("swipies_create_dataset", "swipies_update_dataset"):
        body = {k: str(args[k]) for k in ("name", "description") if k in args}
        if name == "swipies_update_dataset" and not body:
            raise ValueError("Provide name and/or description to change")
    elif name == "swipies_upload_document":
        files = [{"field": "file", "filename": str(args["filename"])[:255], "base64": str(args["content_base64"]), "content_type": str(args.get("content_type") or "application/octet-stream")}]
    elif name == "swipies_parse_documents":
        body = {"document_ids": _check_ids(args["document_ids"], "document_ids")}
    elif name == "swipies_create_chat_assistant":
        body = {"name": str(args["name"])[:128], "dataset_ids": _check_ids(args["dataset_ids"], "dataset_ids")}
        if "description" in args:
            body["description"] = str(args["description"])[:2000]
    elif name == "swipies_ask_chat_assistant":
        body = {"chat_id": _check_id(args["chat_id"], "chat_id"), "messages": [{"role": "user", "content": str(args["question"])[:8000]}], "stream": False}
        if args.get("session_id"):
            body["session_id"] = _check_id(args["session_id"], "session_id")
    elif name in ("swipies_delete_datasets", "swipies_delete_documents"):
        body = {"ids": _check_ids(args["ids"], "ids")}
    call = {"operation_id": method.lower() + "_" + hashlib.sha256(path.encode()).hexdigest()[:16], "path_parameters": pp, "query": query}
    if files is not None:
        call["files"] = files
    elif body is not None:
        call["body"] = body
    return call


def _trim(result):
    """Drop the internal prompt/debug text from assistant answers."""
    try:
        payload = json.loads(result["content"][0]["text"])
        inner = payload.get("data", {}).get("data")
        if isinstance(inner, dict):
            inner.pop("prompt", None)
            inner.pop("audio_binary", None)
        result["content"][0]["text"] = json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        pass
    return result


async def call(app, principal, name, args, execute):
    if CURATED[name][5] and "swipies:write" not in principal.get("scopes", []):
        raise PermissionError("Write permission required")
    result = await execute(app, principal["authorization"], build(name, args))
    return _trim(result) if name == "swipies_ask_chat_assistant" else result
