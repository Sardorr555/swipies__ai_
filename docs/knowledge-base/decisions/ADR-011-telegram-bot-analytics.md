# ADR-011: Bot-scoped Telegram analytics and revocable aggregate sharing

Status: implemented in the prepared release, not deployed.

Use the existing Telegram application as the sole ingress and persist a dedicated
SQL event ledger, projected asynchronously with idempotent keys. An encrypted
Redis spool handles temporary SQL failures. Use per-bot encrypted HMAC identity
secrets; retain no conversation text or plaintext user identifiers in analytics.
Pin the bot identity independently of agent/dialog bindings.

Treat native Telegram confirmed events and signed, server-order-bound provider
notifications as the only payment facts. Never infer payments from receipts,
button clicks or platform subscriptions. Keep currencies and Stars separate and
make collection gaps explicit.

Authorize owner/tenant admin at every private endpoint. Public viewers use hashed,
unguessable, revocable fragment capabilities and explicit aggregate projections;
never reuse the owner session. Share scope also controls chart fields and PNGs.
No-cache/noindex headers, telemetry exclusion and bounded/rate-limited requests
are part of the API contract.

This adds ten tables and a bundled OFL font, with no new poller or npm dependency.
Public HTML proxy headers and Redis persistence are release requirements.
See [implementation and operations](../telegram-bot-analytics.md).
