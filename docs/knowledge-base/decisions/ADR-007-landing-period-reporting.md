# ADR-007: Shared factual periods for the landing administrator

Date: 2026-10-31. Status: implemented locally on `swipies_26`, release pending.

## Context

The separate landing admin used static growth labels, day-only provider charts,
browser-local user records and exports of the last loaded traffic rows. Its
SQLite journal and the platform billing/user database have different owners.
The requested behavior is factual comparison, without forecasts, plus date- and
filter-aware Excel/CSV downloads.

## Decision

Use the pure stdlib [reporting core](../../../api/analytics_reporting.py) for
UTC boundaries, timezone calendar groups, comparison values and file generation
in both applications. The landing service reads its own SQLite file read-only;
platform users and payments are obtained from narrow authenticated superuser
routes via a fixed origin. Do not expose cross-database credentials, create
schema migrations, or import Ads/CRM business services.

Query each provider's period total and native time groups separately. Do not sum
distinct-user buckets or manufacture missing metrics. Use current PAID status
and creation date for payments, explicitly documenting the absence of paid-at
history. Deduplicate mirrored order/ledger records, exclude advertiser deposits
and avoid guessed currency conversion. With an unsupported UTM lead filter,
return an explanation rather than silently broadening the data.

Keep existing navigation/theme. Add one global filter model for overview,
tables and exports; cap reads and fail clearly on oversized reports. Use normal
platform login/OTP plus a fresh superuser profile check. A browser-local login
flag never authorizes a report. XLSX uses literal strings rather than formulas;
CSV protects text that could be interpreted as a formula.

## Consequences

Release must update both Python services and static assets together. The shared
core is copied next to the standalone API. There is no additional XLSX runtime
dependency. Queries remain bounded; oversized historical analytics should later
move to indexed aggregate/event storage. Live GA4/Metrika credentials and source
totals still require release verification. Existing public legacy telemetry/lead
routes are outside this feature's access guarantees. Details and tests are in
[landing-admin-analytics.md](../landing-admin-analytics.md).
