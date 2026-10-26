# Repeat live Agent Access audit — 2026-10-26

Branch `swipies_26`, local implementation `4180bd41d`. The public server's exact Git SHA was not read over SSH; the fixed model behavior was verified directly. No source code changed in this audit.

## Confirmed on public HTTPS

The audit logged **94 successful assertions, zero failed assertions**, including repeated account reconnect and cleanup assertions. Existing two isolated test identities were reused; no additional service accounts were registered in this run.

- Public manifest; authenticated discovery of 272 operations; anonymous/invalid key and hostile Origin rejection; invalid registration and paid-plan injection rejection.
- Official MCP SDK over both a real stdio subprocess and direct Streamable HTTP, including authenticated calls.
- Dataset create/read/update; two same-field multipart file uploads; download with the original synthetic Unicode content; chatbot create/read/update; Message-agent creation, session and execution.
- Actual configured model completion now succeeds, including Free attribution.
- Parsing reaches `DONE`, progress 1.0, one chunk. The earlier model-type assertion failures no longer reproduce.
- Retrieval uses the parsed document and embedding model and returns the synthetic fact. The chatbot is attached to this dataset and answers the document question correctly with a document reference and Free attribution.
- Agent history persists attribution. Model/connector/tenant discovery succeeds.
- Other test identity cannot read/update the dataset, read the chatbot/agent, execute the agent, download the document or retrieve its contents.
- Unknown MCP operations and path traversal rejected; profile credential masked; MCP GET returns 405.
- Session, agent, chatbot, dataset and documents deleted by exact test IDs. Follow-up GETs confirm resource inaccessibility. Existing customer resources were not changed; the previous authorized account remains accessible.

## Local regression checks

API/MCP/model/channel/access suite: 86 tests. Connector security: 21 tests. Branding/crawler suite: 15 tests. All **122 passed**. The test runner suppresses raw credential-related logs and records only summaries.

## Limits

The default Python-urllib identifier still receives Cloudflare error 1010 by deployment policy; the updated bridge identifies itself as `SwipiesAgent/1.0` and passed. Use the updated external client copy.

Free attribution is verified live. Plus/Pro-only omission and expiry handling are covered by local regression tests; no active paid test account was available for a live paid-plan scenario. Real third-party database and OAuth connections require their actual authorization and were not exercised. This audit covers the implemented headless workflow, not every unrelated RAGFlow feature, UI path, provider or channel. The existing SSH/GitHub deployment key was not inspected or repaired in this audit.
