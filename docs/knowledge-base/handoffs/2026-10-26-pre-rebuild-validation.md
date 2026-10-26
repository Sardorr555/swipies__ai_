# Pre-rebuild validation — 2026-10-26

Branch: `swipies_26`. Application source remains the implementation published in `4180bd41d`; this validation changes documentation only. The owner requested a fresh verification and push before their manual rebuild.

## Results

Public HTTPS audit: **94 successful assertions, zero failures**, including repeated reconnect and cleanup checks. Existing two protected test identities were reused. Verified MCP stdio and direct HTTP via the official SDK; discovery of 272 operations; dataset/chatbot/agent CRUD; repeated multipart uploads and download; actual configured-model reply; parsing to DONE with a chunk; embedding retrieval; a correct document-grounded answer with reference; Free attribution and persistence in agent history; tenant isolation including download/retrieval; authorization/Origin/traversal/privilege-injection rejection. Test session, agent, chatbot, dataset and documents were deleted and became inaccessible.

Local regression checks: **236 tests passed, none skipped**, in these selected suites:

| Suite | Tests | Result |
|---|---:|---|
| API/MCP/model runtime/channel/access | 86 | PASS |
| test_connector_security | 21 | PASS |
| test_swipies_ads_watermark_and_crawler_keywords | 15 | PASS |
| test_crm_foundations | 16 | PASS |
| test_crm_amocrm | 11 | PASS |
| test_crm_bitrix24 | 10 | PASS |
| test_crm_1c | 27 | PASS |
| test_crm_tool_and_outbox | 44 | PASS |
| test_user_activity_telemetry | 6 | PASS |

Deployment script Bash syntax and Git diff checks passed. Docker Compose validation and a fresh image build were not run because Docker CLI is unavailable on this Windows host. No server deployment or production migration was performed in this validation. The owner will rebuild.

## Limits

These are selected regression suites and the main external-agent workflow, not the entire upstream repository test suite or all frontend paths. CRM/telemetry tests are local and isolated; real third-party CRM/database/OAuth connections were not made. Live Free attribution passed; active paid Plus/Pro runtime attribution was not exercised. The corrected client identifier works with Cloudflare; the old Python-urllib identifier remains blocked by its policy. The exact deployed server Git SHA was not read over SSH.

No new defect was observed in the tested paths; no additional application code fix was needed.
