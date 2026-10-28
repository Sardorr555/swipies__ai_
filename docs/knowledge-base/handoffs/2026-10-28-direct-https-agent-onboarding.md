# Direct HTTPS agent onboarding — 2026-10-28

Branch: swipies_26. Static public documentation/landing change; runtime API and
the existing Python bridge are unchanged. No OAuth prerequisite was added.

The preferred path now starts with existing authorized HTTPS/code tools:
manifest -> private identity persistence -> bootstrap/reconnect -> authenticated
JSON-RPC -> discover/describe/execute. Manual host MCP configuration is optional.
Existing accounts retain their own credentials/tenant; new Free accounts are
separate. Host permissions and the documented catalog exclusions remain explicit.

Updated llms.txt/full, agents.html (automatic section before the optional setup
generator), discovery JSON, OpenAPI description and homepage EN/RU/UZ copy plus
structured data. No visual redesign or local prototype assets were included.

Validation: 24 static/JS/translation/schema/client checks, 18 setup-generator
combinations and 8 invalid inputs passed. Targeted onboarding checks validate
section order, handshake JSON and agreement on bootstrap and transport.

A clean direct-HTTPS Python agent used the official published bridge, with no
preconfigured key or installed MCP connection. All 17 live flow assertions
passed: new Free bootstrap, persisted identity/reconnect, 272-operation catalog,
dataset creation/upload/parsing, agent execution, chatbot RAG with source
references and Free attribution. A second Bridge instance reconnected to the
same account without a manually supplied key. All synthetic dataset/chat/agent
resources were deleted; the empty Free identity remains in private Windows
DPAPI storage outside the repository. A cleanup harness initially selected the
wrong bulk agent-delete route; using the discovered per-agent delete completed
cleanup. This was a verifier correction, not a runtime failure.

This tests the direct Python/HTTPS environment, not installation inside actual
ChatGPT, Claude Code or Cursor products. Do not infer universal client support.
Previous broader verification claims are dated separately in discovery JSON.

Publication: copy only the existing public landing asset whitelist to
/var/www/html, after matching current baseline revisions and making a private
backup; atomically install docs before index and restore on verification failure.
The static-only Git commit uses [skip ci]; the main app workflow does not publish
this web root. Record final public HTTPS/browser results after publication.
