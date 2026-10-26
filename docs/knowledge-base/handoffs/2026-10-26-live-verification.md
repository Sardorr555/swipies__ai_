# Live Agent Access verification — 2026-10-26

Branch: `swipies_26`. The owner reported a manual deployment after release `b172b0f5c`; public behavior confirms the Agent Access endpoints exist. The exact server commit was not established over SSH.

## Verified against public HTTPS

- Manifest/version/protocol and Plus/Pro branding metadata.
- Two isolated Free service accounts, DPAPI identity persistence, repeat bootstrap resolving the same account, no-store on bootstrap.
- Official MCP SDK through a real stdio subprocess against production; initialize, three tools, authenticated execution and discovery of 272 operations.
- Dataset create/read/update; two same-field multipart uploads; chatbot create/read/update; agent create/read, session creation and Message-only echo execution.
- Actual Free Message-agent output contains the Swipies attribution.
- Second account cannot read/change the first account's dataset, read its chatbot/agent, or execute the agent.
- Anonymous and invalid credentials denied, hostile Origin denied, path traversal and unknown operations rejected; bootstrap cannot request a paid plan; profile credentials redacted.
- Test agent/session/chatbot/dataset/documents deleted by exact saved IDs; subsequent resource reads denied. Two empty named service-account identities remain for future verification, with secrets stored only in local Windows DPAPI files. Existing customer resources were not modified.

The test log has 65 successful assertions (including repeated reconnect checks) and three failed assertions. This is not a full-platform or all-provider certification. Paid-plan runtime attribution and real third-party database/OAuth connections were not exercised.

## Reproduced defects and corrections

1. Cloudflare returns HTTP 403/error 1010 for the default Python-urllib identifier. `SwipiesAgent/1.0` succeeds. Added this actual product identifier to both bridge request types. The updated local bridge passed live official-SDK checks.
2. Chatbot completion returns business code 100, `Can't find model .../1/deepseek-v4-pro`. Document parsing fails at binding embeddings with `.../2/text-embedding-3-small`. Provider-instance resolution returned `TenantModel.model_type`, a capability bitmask, while runtime factory selection requires the requested string capability. Change that return value to `model_type_val`, consistent with the existing ID-based resolver. Provider/model selection, authorization and encryption are unchanged.

The second defect is reproduced using the real resolver and factory methods: before correction, four numeric/supported-multi-capability cases fail while two legacy string cases pass; after correction all six pass. Combined API/MCP/channel/access/model tests: **86 passed in 4.76 seconds**.

## Outstanding

Publish the correction, deploy the new server resolver and restart the Python API plus document/task workers, and update external client script copies. No schema migration is required. Repeat real chatbot inference and document parsing, then retrieval and attribution, using disposable resources. A unit test pass is not evidence those production operations now succeed.

GitHub's last known main deployment run still failed with an invalid SSH key; no new server deployment was performed in this audit. The owner currently deploys manually. Do not claim the fix is active until retested.
