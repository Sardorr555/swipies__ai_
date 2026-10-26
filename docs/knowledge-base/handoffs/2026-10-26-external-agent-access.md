# Handoff: external agent access on swipies_26

- Date: 2026-10-26
- Working directory: D:\ragflow\swipies_25\ragflow
- Branch: swipies_26
- Base commit: 697aa5aee; changes remain uncommitted.

## Implemented

Python MCP facade over authenticated tenant REST routes; atomic headless Free service-account bootstrap; stdio client with persistent identity/Windows DPAPI; persisted Plus/Pro-only branding entitlement and Message-only canvas attribution. No platform-side LLM, migration or Go change. See ../agent-access.md and ../decisions/ADR-005-external-agent-access.md.

## Validation

56 tests in test/test_agent_access.py passed, including official MCP SDK, bounded ASGI, binary downloads, SQLite rollback, credential revocation and client registration. Connector security: 21 passed. Watermark/crawler regression: 15 passed. Agent channel/access-control regression: 9 passed. Syntax and diff checks passed. Old test/testcases/test_web_api/test_user_app/test_user_app_unit.py requires ZHIPU_AI_API_KEY in shared conftest; isolated with --confcutdir, its 9 tests fail because its stubs omit Lead. The same failure was reproduced against the unchanged user_api.py from HEAD in a scratch baseline tree, so this is pre-existing. Those tests are not counted as passed.

## Pending release and limitations

No push/deploy/production migration was authorized or executed. Validate the full Python API with real DB/Redis and the public reverse proxy before releasing. Configure source IP limits/trusted proxies and allowed browser origins for the deployment. Go-only deployments are not covered. Account claiming/email recovery is not implemented; existing customers use their own API keys. The catalog intentionally excludes admin/payment/authentication/token-management operations. External AI hosts still need MCP configuration and retain their own approval policies.

## Repository rules

Do not push, deploy or apply production migrations without explicit owner instruction. Never print credentials or registration secrets. Preserve existing changes. If committing, use the repository owner's author identity specified by AGENTS.md.
