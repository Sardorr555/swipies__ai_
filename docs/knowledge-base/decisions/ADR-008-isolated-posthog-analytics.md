# ADR-008: Isolated PostHog analytics for the landing

Date: 2026-11-08. Status: implemented locally; production enablement pending owner instruction. Branch: `swipies_26`.

## Context

The owner requires PostHog alongside the existing landing administrator analytics, without changing public presentation, authentication, business transactions or existing reports. Public telemetry cannot prove an actual registration or payment. Capture credentials and private report credentials have different exposure and permissions.

## Decision

Register one optional Flask extension and authenticated `/admin/posthog` route, with one additional navigation item. Reuse the current administrator token validation and the existing read-only platform data adapter. Collect explicit browser events through the official SDK after the existing analytics consent. A content-free React registration-start event is the only extra behavior in the registration hook.

Emit confirmed conversion events from read-only database facts through a separate private, consent-gated durable outbox. Do not trust legacy public event submissions and do not add PostHog calls to registration or payment transaction paths. Use stable event UUIDs and linked order/gateway aliases for retry and mirror deduplication. No platform schema migration is needed.

Use server-side official Query API with a project-restricted `query:read` credential; only the separate public capture token reaches browsers. Hosts are explicit HTTPS configuration, supporting US/EU/self-hosted PostHog. Disable Replay/autocapture and allowlist outgoing event properties. Reports have bounded cache/stale fallback, rate-limit handling and explicit setup/error states.

Compare only compatible facts for identical periods/timezones. Existing PAID reports use creation date, so show payment comparison as unavailable where confirmation time is not guaranteed. Never replace unavailable data with a fabricated zero.

## Alternatives

Embedding a PostHog dashboard in the old page would couple authentication and report behavior. Trusting client success clicks would fabricate conversions. Posting synchronously inside billing/signup would introduce a new availability dependency. Replacing the old reporting provider would violate the requested coexistence. These approaches are not used.

## Consequences

An optional third-party outage does not stop existing site behavior. The separate state file needs private storage, shared worker access, backup and eventual retention/paging work. Confirmation timestamps, consent loss, ingestion delays and identity resets legitimately differ from old system counts. There is no historical backfill before activation, and no live-provider guarantee until credentials and actual server behavior are verified. Source scans are bounded at 10,000 facts and fail explicitly rather than silently truncating.

See [configuration, privacy, event definitions, changed files and release checks](../posthog.md). No production publication is authorized by this ADR.
