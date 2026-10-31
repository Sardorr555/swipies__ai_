# Landing administrator: factual period comparisons

Date: 2026-10-31. Branch: `swipies_26`. Implemented; deployment and live-provider verification remain pending.

## Behavior

[admin.html](../../new%20site%20for%20swipies/admin.html) loads
[admin-analytics.js](../../new%20site%20for%20swipies/admin-analytics.js) and
[admin-analytics.css](../../new%20site%20for%20swipies/admin-analytics.css).
The existing dark/amber navigation and settings remain. The overview compares
current and reference values, absolute differences and percentage changes.
Conversion-rate differences use percentage points. A zero baseline is labeled
as a new value, without an infinite growth percentage. Missing data uses a dash.

The global controls select two factual periods, IANA timezone, hour/day/week/month
grouping, traffic provider, UTM source and UTM campaign. Default reference is the
adjacent interval of equal elapsed duration; custom reference dates are allowed.
All boundaries are whole local hours: start inclusive, end exclusive. Presets
exclude the unfinished current hour. No future estimates are generated. Periods are capped at 366 days each.
Weeks start Monday and months follow the selected timezone's calendar. Partial
edge groups are clipped. The chart pairs groups by ordinal position, and unequal
duration is explicitly explained; values are never normalized or projected.

Traffic, users, UTM journal and lead tables share the applied date/UTM filters.
Tables have 100-row pagination and search. Excel/CSV export includes all matching
records up to an explicit 50,000-row cap, rather than only the visible page or
the old 500-row traffic limit. Over-limit requests fail with a reduce-range
message; report input is bounded to 250,000 records. Unapplied draft filters are
labeled, and export first applies them. An unsuccessful refresh keeps the last
successful report with an explicit warning.

## Sources and definitions

- [analytics_reporting.py](../../api/analytics_reporting.py) owns interval parsing,
  local calendar groups, distinct counts, comparisons, CSV and stdlib OOXML XLSX.
- The separate Flask landing API uses
  [landing_admin_api.py](../../new%20site%20for%20swipies/landing_admin_api.py)
  to read `visitors` and `leads` from its existing SQLite journal in read-only
  mode. No schema migration or production-data backfill is performed.
- Local visitor identities use visitor ID, then IP, then record ID. Unique
  visitors are counted per period, not summed across buckets. Journal rows are
  sessions; they are not claimed as true pageview events. Journal-only data does
  not invent bounce rates, goals or CTA counts. UTM aggregates are calculated
  across the full selected period; their detail display is labeled as top 100.
- Old leads have no UTM fields. With UTM filters, lead metrics are unavailable
  and filtered lead-table/export requests explain why, rather than returning
  unfiltered leads. Visitor device/country/language counts use stored telemetry.
- Read-only, `login_required` plus `is_superuser` platform routes:
  `GET /api/v1/admin/analytics/periods` and
  `GET /api/v1/admin/analytics/users` in
  [system_api.py](../../api/apps/restful_apis/system_api.py).
  [landing_analytics_service.py](../../api/db/services/landing_analytics_service.py)
  reads safe user fields, payment ledger and orders. Registrations and payments
  are assigned by **record creation time**, with **current payment status**.
  A confirmed paid-at timestamp is not available; this is not a settlement or
  accounting-period report. Do not label it as cash received at payment time.
- Revenue counts only PAID payments in UZS. Mirrored orders are deduplicated
  against ledger IDs/transaction IDs, including matches outside the date range;
  repeated order transaction IDs are also suppressed. Advertiser deposits are
  excluded. Missing paid amounts leave revenue/average unavailable. No estimated
  USD exchange rate or Ads/CRM service import is introduced.
- [landing_analytics_providers.py](../../new%20site%20for%20swipies/landing_analytics_providers.py)
  requests native GA4 or Metrika totals and time series; unique-user period totals
  are queried separately. GA4 timezone must match the property, and repeated DST
  hours require daily grouping. Metrika uses a fixed UTC offset; DST-changing
  intervals require UTC. If `time_intervals` is absent, its bytime axis is rebuilt
  from requested native calendar dates only when all metric-array lengths match.
  Provider sampling/threshold notices are shown. Live-provider credential/access
  verification remains pending; automated tests mock provider responses.

Primary API contracts:
[GA4 schema](https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema),
[GA4 reports](https://developers.google.com/analytics/devguides/reporting/data/v1/basics),
[Metrika bytime](https://yandex.ru/dev/metrika/en/stat/openapi/bytime),
[Metrika date/time filters](https://yandex.ru/dev/metrika/ru/stat/attributes/visitsbehavior_date_time_/date_time_precision).

## Authentication and export

New reports, records and export endpoints require Bearer authorization and verify
the current platform profile's `is_superuser` on every request. The old local
password is not accepted. Login proxies the standard `/api/v1/auth/login`; when
the platform requests email verification, `/api/v1/auth/activate` completes it.
The legacy admin-login route is not used to bypass the normal verification.
No localhost-preview identity exists in production code. Responses are no-store.
Upstream platform origin is fixed, redirects are disabled, timeouts/body/row
limits are explicit. JSON error messages do not expose upstream credentials.

XLSX report sheets: parameters, metric comparison, current buckets and reference
buckets. Record exports include parameter/search metadata and all matched rows.
CSV repeats dates/timezone/UTM/search/type columns so the filters travel with the
file. Text is escaped as literal XLSX strings and formula-like CSV text receives
a prefix. Numbers stay numeric; unavailable values stay blank. Credentials are
never included in exports. Visitor/lead text is escaped before HTML rendering.

Previously embedded analytics credential literals were removed from current
`admin.html`/`api.py` sources. Previously exposed credentials must be rotated
before production release; deleting literals does not revoke deployed or historic
copies. Provider settings are administrator supplied. Legacy public telemetry/
lead endpoints remain outside this change and require a separate access review;
these new routes do not make them private retroactively.

## Verification and release

Validation on 2026-10-31: 167 pytest cases passed across landing reporting,
agent-access, OAuth and real-model integration; 27 unittest cases passed for
connector security and Ads settings/localization. Ruff E9/F, JavaScript syntax
and Git whitespace checks passed. Provider tests use mocked transport.

[test_landing_admin_reporting.py](../../test/test_landing_admin_reporting.py)
tests calendar/DST boundaries, zero/null deltas, more than 500 visits, attribution,
pagination/search, normal login/OTP and superuser checks, read-only SQLite,
full XLSX/CSV exports through openpyxl, safe text and absent credentials,
mocked native GA4/Metrika reports and real Peewee model financial deduplication.

The loopback preview lives outside the repository, in the Codex work directory,
on `http://127.0.0.1:8785/admin.html`. Its banner explicitly labels all data as
synthetic. It must never be deployed. Browser verification covered login,
weekly grouping, custom unequal reference dates, UTM filtering/pagination and
successful Excel generation. Waiting for the browser download event hung in the
automation helper; the button's completion message and API export were verified.

For a future authorized release:

1. Deploy platform Python core/service/routes together. Restart platform API
   workers through the existing release mechanism. No Vite rebuild is needed for
   this admin feature and no DB migration is required.
2. In the standalone landing service directory, deploy `api.py`,
   `landing_admin_api.py`, `landing_analytics_providers.py` and a copy of
   `api/analytics_reporting.py` named `analytics_reporting.py` next to `api.py`.
   The checkout fallback path is not sufficient in `/home/ubuntu/landing_swipies`.
   Preserve its actual SQLite database and environment. Restart its Python service.
3. Publish `admin.html`, `admin-analytics.js` and `admin-analytics.css` together.
   Ensure `/api/admin/analytics/*` reaches the landing Flask API, while the new
   `/api/v1/admin/analytics/*` routes stay on the platform API.
4. Verify superuser login/OTP, non-admin denial, an actual filtered comparison,
   provider timezone/access, and downloaded totals against source records before
   claiming production success. Keep unrequested pending OAuth changes separate.

See [ADR-007](decisions/ADR-007-landing-period-reporting.md).


## Production compatibility discovered during deployment (2026-10-31)

The running landing had newer secure admin sessions, private provider settings,
platform sync and event ingestion than the tracked baseline. Its code was
preserved while integrating the reporting assets. The browser retains the normal
`/api/auth/login` and `/api/auth/verify` session flow. Every new report request
validates the existing landing-admin session; expired/revoked sessions are denied.
Platform superuser JWT login remains supported for installations without native
landing auth. Neither flow treats a localStorage flag as authorization.

[landing_platform_reports.py](../../new%20site%20for%20swipies/landing_platform_reports.py)
uses the landing service's existing MYSQL_* configuration in a MySQL READ ONLY
transaction to query bounded user/payment facts for its own verified admins.
It never impersonates a platform user or creates a service account. Both the
Peewee reader and direct SQL reader share payment normalization/deduplication.
The existing main API routes remain protected by platform superuser auth.

Already configured secrets are preserved in a private 0600 server-side
`admin_reporting_private.json` outside the web root and Git, or existing service
environment. Credential fallbacks are removed from source/HTML. New reporting
can use server-configured GA4/Metrika credentials without returning them to the
browser or spreadsheets. Rotation of previously exposed values is still needed.
The native auth/events/sync features are retained, rather than replaced with the
older tracked standalone API. Four additional compatibility tests verify native
session revocation, READ ONLY transaction cleanup, SQL/model parity and private
provider-credential handling. No schema change is introduced by this feature.
