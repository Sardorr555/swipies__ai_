# Telegram bot analytics

Implementation prepared and push authorized by the owner on 2026-11-26; deployment remains deferred. This module reports
the connected bot's observed audience and confirmed bot purchases. It never reads
Swipies subscriptions, Ads payments, uploaded receipts or messages claiming payment.

## Sources and counting

The existing Telegram polling application captures incoming content, callbacks,
successful outgoing replies, `successful_payment` and `refunded_payment`. No second
poller is started. An additive SQL event ledger is the durable outbox. The worker
in the existing channel runtime claims and projects events transactionally; event,
charge and refund identifiers prevent duplicate processing after restart. Pending
Telegram updates are retained. During a SQL outage, an encrypted, sanitized Redis
spool retains observations and acknowledges them only after SQL insertion. Redis
must have persistence enabled, sufficient capacity and monitoring. Simultaneous
SQL and Redis failure is logged and cannot guarantee recovery of that observation.

Unique users use a per-bot random encrypted secret and HMAC pseudonyms. Private
chat labels are safe pseudonyms. The ledger stores no message text, attachments,
raw Telegram user IDs, user names or bot token. Group titles identify group chats.
The encrypted recovery spool may temporarily contain routing IDs, never text.
Agent/dialog rebindings retain bot identity; replacing the bot creates a separate
identity. Existing shares remain revocable after replacement.

All timestamps are UTC. IANA date boundaries support DST. Periods before collection
show unavailable data; overlapping periods show a partial-coverage notice. There
is no fabricated historical import. Lifetime users are all observed users, active
users are distinct actors in the selected period, new users use first observation.
Group membership/subscriber totals are unavailable. Conversion uses payers among
the same period's active cohort, divided by those active users; incomplete periods
show no conversion percentage.

Payments use integer minor units and official Telegram currency exponents. USD,
UZS and Stars (XTR) remain separate, with no FX conversion. Gross revenue and
confirmed refunds remain separate. Unique payers differ from transaction count.
Native refunds with purchases predating collection are still factual refunds.
External payment coverage begins at source verification. Unconfigured or earlier
payment history is unavailable, rather than a fabricated zero.

## External payment bridge

Native Telegram success/refund events work without a bridge. External gateways
require a provider-side adapter that verifies the gateway's own callback and then
sends the signed protocol below. The existing Atmos integration sells platform
subscriptions and is deliberately not treated as this bot-purchase source.

An owner or organization admin creates a source through
`POST /api/v1/chat-channels/{channel}/analytics/payment-sources` with `name` and a
32–200 character `secret`; storage uses existing `enc:v2` encryption. No secret
is returned by listing. Configure the same secret in the trusted provider adapter.
The returned notification path accepts a signed `{"type":"verification"}` to
activate the source. Revoking the source stops future notifications.

Every notification sends `X-Swipies-Timestamp` (integer Unix seconds) and
`X-Swipies-Signature` (HMAC-SHA256 of timestamp + `.` + exact raw request body,
using the source secret). The timestamp tolerance is five minutes. Keep the same
event and transaction identifiers on retries. Request bodies are limited to 64 KiB.
Do not put secrets or callbacks into logs.

Create a server attribution order using
`POST /api/v1/chat-channels/{channel}/analytics/orders`: `source_id`,
`telegram_user_id`, optional `telegram_chat_id`, `currency`, `amount_minor`.
The user must already have been observed by that bot. The returned order ID goes
into the real gateway checkout metadata. Creating the order records no payment.
The trusted adapter subsequently sends `type=payment_succeeded`, `event_id`,
`transaction_id`, `order_id`, `currency`, `amount_minor`. Refunds use
`type=refund_succeeded`, a unique event ID and the original transaction/order ID.
Currency and amount must match the server order; cumulative refunds cannot exceed
the confirmed charge. External transactions use callback receipt time. Enabling
an actual gateway is a release/integration step, not a claim that staging made a
real purchase.

## Access, widgets and exports

The private route is `/user-setting/chat-channel/{id}/analytics`; the Telegram
channel card exposes Analytics after successful runtime registration. Only the
owner and active tenant owner/admin roles can read, export or manage sharing.
Normal members and strangers are denied. Tables support search/sort/pagination.

The share panel selects metrics, revenue visibility, period/timezone, title and
expiry (including unlimited), creates a living link, copies it, downloads a PNG
and offers the platform's system share menu when available. PNG dimensions are
1080×1920 or 1080×1080. A created link can be included as text in the card; create
the link before exporting if that option is needed. Bundled Noto Sans includes its
OFL license. No social account credentials or automatic Instagram posting exist.

Public URL: `/shared/telegram-analytics#<capability>`. The 256-bit random capability
is returned once and only its hash is stored. It is sent by POST body, never as a
query parameter or API URL, with credentials omitted. Public responses use an
explicit projection of selected aggregates; no users, chats, internal IDs, texts,
source credentials or unselected financial chart fields are exposed. Redis rate
limits fail closed. Responses and the HTML shell are no-store/noindex/no-referrer.
Telemetry skips the public route and private share controls. The optional iframe
uses this same read-only capability. The outer reverse proxy must preserve these
headers and permit framing for this route without caching it.

Revocation/expiry denies subsequent reads, and the public page removes displayed
data on the next refresh (15 seconds, or focus/manual refresh). A previously
downloaded PNG or copied aggregate cannot be remotely erased.

## Release procedure (requires owner's release instruction)

1. Review the combined patch against the current checkout, preserving unrelated
   changes. It includes the separately documented CodeExec release.
2. Back up the database and encrypted keyring. Run
   `python -m api.scripts.migrate_telegram_analytics` first: dry-run is default.
   Only during the authorized release run with `--apply` to create ten additive
   analytics tables. Existing tables are not rewritten; repeating is safe.
3. Build the frontend and ship its Nginx template. Confirm public HTML/API cache,
   referrer, robots and iframe headers through the actual HTTPS proxy.
4. Restart the existing channel runtime, without adding another Telegram poller.
   Verify the correct bot identity, first collection timestamp and worker backlog.
5. Verify an inbound message and successful reply, same-user deduplication,
   sharing/export/revocation, and a gateway sandbox event if a bridge is configured.
   Real financial testing requires a separate agreed transaction.

The current verification uses an isolated MySQL schema, source copy and loopback
frontend/API. It does not migrate production; the later owner instruction authorizes a Git push only. See the release
handoff and saved verification report for exact checks and remaining release work.

Primary references: https://core.telegram.org/bots/api#successfulpayment,
https://core.telegram.org/bots/api#refundedpayment,
https://core.telegram.org/bots/payments/currencies.json.
