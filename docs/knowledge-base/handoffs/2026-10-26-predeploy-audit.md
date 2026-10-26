# Pre-deployment bug audit

- Date: 2026-10-26
- Branch: swipies_26
- Repository: D:\ragflow\swipies_25\ragflow
- Base commit remains 697aa5aee; code is uncommitted. No push, deployment or production DB change.

## Reproduced and fixed

1. Repeated multipart file fields were rejected. Preserve their order and field names.
2. A path converter could select an uncatalogued static endpoint. Match and compare the resolved rule/endpoint before dispatch.
3. Missing Content-Length bypassed request limits. Bound streamed bytes before JSON decoding.
4. Concurrent clients could read an empty credential file. Atomically publish a fully written/fsynced file without replacing another identity.
5. Existing user profile responses exposed internal access_token to MCP. Mask secret fields and reflected bearer credentials in tool results, preserving web-login compatibility.
6. PowerShell module availability broke Windows credential encryption. Use native DPAPI via ctypes; real Windows roundtrip is tested.
7. Inherited Windows encodings broke Cyrillic MCP output. Explicit UTF-8 stdio is tested in a real subprocess over verified local HTTPS.

Also test cancellation cleanup, safe bootstrap retries and absence of retries for authenticated writes. Do not describe these tests as a full production deployment: DB/Redis/external providers and the deployed reverse proxy have not been exercised together.

## Final commands/results

`python -m pytest test/test_agent_access.py test/test_agent_access_model_integration.py test/unit_test/api/channels/test_agent_channel_bridge.py test/unit_test/api/apps/restful_apis/test_agentbots_access_control.py -q -p no:cacheprovider --basetemp=<local-temp>`: **80 passed in 6.53s**.

`python -m unittest test.test_connector_security`: **21 tests, OK, 37.945s**.

`python -m unittest test.test_swipies_ads_watermark_and_crawler_keywords`: **15 tests, OK, 4.065s**.

Total: 116 passed checks in the named suites. The old user API unit suite still has the pre-existing missing Lead stub and is not counted. Syntax compilation and diff checks are required before handoff.

## Next

After explicit deployment authorization, prepare a release commit and rollback reference using the repository owner's identity. Deploy to a test environment with real MySQL/Redis, check the public manifest and registration/MCP, then exercise resource creation, document parsing, tenant isolation and branding. Only then perform the production release. Observe AGENTS.md restrictions on push, deployment and production migrations.
