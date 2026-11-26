# Telegram analytics — prepared release, publication deferred

Owner asked to finish the earlier CodeExec work and add Telegram analytics before
a later push. The owner explicitly authorized pushing on 2026-11-26. Production deployment and migration remain deferred.

Canonical prepared source is the local `work/project` copy, based on deployed
commit `c0294a8cd`, with the previous CodeExec patch merged first. The original
server checkout, its unrelated changes and production schema remain untouched.
The combined release archive contains both features, additive migration, tests,
font/license and operational documentation. No runtime credentials are included.

Analytics tests use only `swipies_tg_analytics_stage_20261126`, a dedicated MySQL
schema. Browser fixtures are synthetic; no real user/payment history is copied
and no Telegram poller or checkout is started by the QA runner. The copied QA API
and frontend are accessed through a loopback SSH tunnel and are stopped afterward.
The QA-only sign-in helper is not part of the product archive.

Implemented: channel-card entry, private dashboard with periods/timezones, daily
charts and chat pagination, distinct audience/payment counts, native refunds,
verified external bridge, scope-selected public links, expiry/revocation, PNG
exports and optional iframe. Tests verify owner/admin boundaries, persistence,
duplicates, timezones/DST, unavailable history, currencies, confirmed external
orders, privacy, PNG dimensions, and cache/revocation HTTP behavior.

Next release work: follow [analytics procedure](../telegram-bot-analytics.md) and
[CodeExec handoff](2026-11-23-codeexec-night-release.md), including the existing
BotFather credential rotation requirement. Actual external gateway adapters must
be configured for bot purchases; platform-owner Atmos subscriptions are excluded.
Do not claim production deployment or historical backfill from staging results.

Push destination: `codex/codeexec-telegram-analytics`. The existing `swipies_26` push workflow automatically deploys production, so publication uses a separate feature branch. Merge/deployment requires the owner's release instruction.
