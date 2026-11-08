# PostHog landing analytics

Date: 2026-11-08. Branch: `swipies_26`. Implementation and automated checks are local; production enablement and live PostHog query verification are not implied by these tests.

## Boundaries

The isolated Flask extension is [landing_posthog.py](../../new%20site%20for%20swipies/landing_posthog.py). Its page is `/admin/posthog`, opened through one new navigation item. Existing login, administrator sessions, old reporting routes, exports and landing content remain in place. Existing administrator authorization protects every new reporting method. The HTML route validates the same session through a five-minute HttpOnly/Secure/SameSite=Strict cookie restricted to this page. The session token remains the existing principal; there is no second login or new administrator account. Revoking the original session immediately revokes reporting access.

The public collection config exposes only the public capture token and approved origins; the read API key is server-only. The new Nginx locations must be installed for cross-subdomain consent CORS and the authenticated page. `/posthog.html` is explicitly denied; do not publish private Python, `.env`, JSON settings, databases or environment examples under the static web root.

## Configuration

Use the landing service's existing **private `.env`**, not browser variables, tracked files, the static web root, or `admin_reporting_private.json` (its existing allowlist is unchanged). See [posthog.env.example](../../new%20site%20for%20swipies/posthog.env.example); it contains no credentials and defaults to disabled.

| Variable | Purpose |
| --- | --- |
| `POSTHOG_ENABLED` | `0` until a separately authorized release; `1` enables configured production collection |
| `POSTHOG_ENVIRONMENT` | Only `production` captures; other environments are disabled |
| `POSTHOG_PROJECT_ID` | Existing US project: `718705` |
| `POSTHOG_PROJECT_TOKEN` | Public project capture token, separate from the read key |
| `POSTHOG_READ_API_KEY` | Private API credential with only `query:read`, restricted to this project where supported |
| `POSTHOG_API_HOST` | US `https://us.posthog.com`; EU `https://eu.posthog.com` |
| `POSTHOG_INGEST_HOST` | US `https://us.i.posthog.com`; EU `https://eu.i.posthog.com` |
| `POSTHOG_ASSET_HOST` | US `https://us-assets.i.posthog.com`; EU `https://eu-assets.i.posthog.com` |
| `POSTHOG_INTERNAL_CIDRS` | Comma-separated trusted internal network ranges; configure the actual ranges before enabling |
| `POSTHOG_INTERNAL_VISITOR_IDS` | Comma-separated known internal anonymous browser IDs; never account secrets |
| `POSTHOG_STATE_DB` | Optional private absolute path; default `posthog-state.sqlite` beside the private landing database |
| `POSTHOG_CACHE_SECONDS` | Report TTL, default 60, clamped to 15–300 seconds |

Self-hosted installations may set all three hosts to their own HTTPS origins. Paths, credentials, queries and fragments are rejected. Their SDK asset must be served at `/static/array.js`, and their installation must support the documented Query and Capture APIs. Do not introduce broad API scopes to work around configuration errors.

The authenticated setup page lists missing configuration names and instructions without echoing either key. No key was invented and no demo data is used in operational reports. Local smoke tests use isolated synthetic fixtures only.

## Browser events and consent

[posthog-tracker.js](../../new%20site%20for%20swipies/posthog-tracker.js), identically copied into `web/public/`, loads the official SDK only after the existing `swipies_cookie_consent=accepted` decision and a successful anonymous consent receipt. A Secure root-domain consent/identity cookie carries the decision to `api.swipies.app`; an explicit local refusal takes precedence. No unrelated legacy analytics behavior is changed.

- `$pageview`: once per public pathname in this document; hash-only navigation and reevaluation do not duplicate it.
- `cta_click`: predefined CTA IDs only; one actual click is an event, not a unique person.
- `pricing_viewed`: pricing section intersects the viewport, once per document.
- `plan_selected`: a plan CTA, distinct from checkout creation or payment success.
- `registration_started`: actual `useRegister` mutation begins; dispatches a content-free DOM event once per document.
- `payment_started`: actual checkout/payment record exists in the database, emitted by the server collector.
- `registration_completed`, `payment_completed`: server facts only; these events are rejected by the browser privacy hook.

Localhost/other domains, webdriver, DNT, known administrator sessions and explicit test/debug/preview/e2e/ph_test URLs do not capture. Server-configured internal CIDRs and visitor IDs also exclude traffic. Internal ranges are not guessed.

`before_send` uses an allowlist: public page-path classes, referrer **origin only**, limited UTM tags, device class, anonymous IDs, known CTA/plan IDs and schema/environment metadata. Raw URLs, query strings, form values, person properties, passwords, email, tokens and conversations are omitted. Sensitive-looking UTM tags are dropped. Session Replay, automatic capture, field recording, heatmaps, performance capture, surveys, feature flags and external dependency loading are explicitly disabled. Config/consent/SDK requests use no-referrer where controlled by this integration.

Consent receipt writes only the anonymous identity and decision to the integration's private state. It accepts exact approved Swipies origins, bounded JSON and rate limits; it cannot submit a conversion. Async grant/withdraw/regrant requests are serialized, and a generation guard prevents SDK initialization after withdrawal. A request already in flight cannot be recalled. Consent must remain granted at conversion delivery; pre-consent events are not backfilled. Anonymous consent is a preference record, not proof of the visitor's real identity or an authentication mechanism.

## Confirmed conversions

[landing_posthog_collector.py](../../new%20site%20for%20swipies/landing_posthog_collector.py) uses the existing `landing_platform_reports.connection()` read-only transaction and MYSQL settings. It never writes to platform or legacy analytics tables. Registration requires a persisted user, tenant, owner membership and root folder. Payment success requires an actual `PAID` order/ledger record. Public legacy `/api/platform/events` is deliberately not trusted for success.

Only eligible anonymous visitor IDs with consent are delivered. Superusers, configured internal IDs and advertising deposits are excluded. A separate private SQLite outbox stores consent, stable UUIDs, order/gateway alias mappings and pending delivery state. The payload contains no raw user/order/gateway identifiers or payment details. Mirrored order/ledger records sharing an ID or transaction are deduplicated. Retry uses the same PostHog event UUID and `$insert_id`; remote capture uses the public token, never the private query key.

The daemon polls every 30 seconds. Timeouts, bounded retry/backoff, leases and failure isolation keep registration, payments and the old admin working if PostHog fails. Delivery failures are visible in the new status panel. Each source is bounded to 10,000 facts since first activation; exceeding that fails visibly rather than silently truncating conversions. Before exceeding this volume, add tested incremental paging and retention/alias-preserving compaction. Current state has no automatic deletion policy: keep it private, back it up and plan retention. Do not delete deduplication aliases casually or historical facts can be sent again. Multiple application workers must share the same private state path.

For ledger rows `provisioned_at` supplies the confirmation time. If an order has no reliable confirmation timestamp, the event time is explicitly **first observed PAID**, not an invented historical timestamp. Events before integration start and failed/partial provisioning are not imported. Unlinked duplicate records cannot be inferred without a common payment identity. Reconcile these source-schema assumptions against the actual server during the separately authorized release.

## Reports and definitions

The server makes fixed HogQL queries through the official `/api/projects/{id}/query/` endpoint. No user SQL is accepted. Periods/timezones use the existing validated reporting core. Today/7/30-day presets end at the last **complete hour**; a custom range is half-open `[start,end)`, to whole hours. The UI displays the timezone and last successful update. Current and previous periods use the same duration and rules; overlapping explicitly requested comparison periods remain independent.

- Visitors: distinct anonymous browser IDs with a landing pageview; not accounts or physical people.
- Sessions: distinct SDK `$session_id` among landing views; missing IDs are excluded.
- Views: actual landing `$pageview` events.
- Created accounts / paid transactions: unique confirmed server event UUIDs. They are separate from funnel browser counts.
- Funnel: one browser ID follows landing → landing CTA → registration → payment in chronological order, within the chosen period and at most seven days from the first landing view. Conversion denominators are landing-stage browser IDs. Repeated clicks or several accounts are not several visitors.
- Acquisition: safe UTM source/campaign and referrer origin; groups can overlap for returning browsers and are not first-touch attribution.
- Devices: explicit desktop/mobile/tablet classifier; a returning browser can occur in more than one group.
- Timeline: hourly for short periods, daily otherwise; complete empty aggregate groups mean zero events, while API errors and unavailable data never become zeros. UTC bucket identities preserve repeated DST hours.

CTA/source/device top lists are intentionally bounded and labeled; absent rare rows are not asserted to be zero. The cache retains up to 16 reports; API 429 honors a bounded Retry-After cooldown. On failure, a previously successful report up to 15 minutes old is shown only with its original timestamp and an explicit stale warning; without a cached success, an error is shown.

“PostHog и данные системы” calls the existing read-only platform report once with identical time boundaries and timezone. Registration comparison shows both facts and their difference. Existing payment reports date current PAID rows by **creation date**, so their window is not guaranteed comparable with confirmation/first-observed timestamps. The page explicitly marks that comparison unavailable instead of presenting a false difference. Blockers, consent, delivery delay, new-integration history, anonymous identity and different counting rules are explained. Existing reports and exports are not changed.

## Files

New landing files: `landing_posthog.py`, `landing_posthog_collector.py`, `posthog-tracker.js`, `posthog-nav.js`, `posthog.html`, `posthog.css`, `posthog-admin.js`, `posthog-nginx.conf`, `posthog.env.example`.

Minimal edits: landing `api.py` (optional registration), `index.html` (one deferred script), `admin.html` (one deferred nav script), `setup_nginx.py` (isolated locations), `.gitignore` (private runtime files). Platform edits: `web/index.html` (one deferred script), `web/src/hooks/use-login-request.ts` (content-free start event), `web/public/posthog-tracker.js` (same tracker). No package/dependency changes are required by PostHog.

Tests: `test/test_landing_posthog.py`, `test/landing_posthog_browser.cjs`. Architecture: [ADR-008](decisions/ADR-008-isolated-posthog-analytics.md). Unrelated changes made concurrently in this checkout are not part of this task.

## Validation and release limits

Run the PostHog Python tests with `test/test_landing_admin_reporting.py` and `test/test_landing_native_compat.py`. The native auth checks compile the actual existing authorization functions against a test-owned SQLite DB. Browser tests use the existing JSDOM dependency and no live network. Optionally set `POSTHOG_SDK_FILE` to a locally downloaded official `array.js` to exercise the real SDK privacy hook in the isolated harness; no SDK binary is committed.

Before a separately approved production release: provide real capture/read credentials in the private service environment, verify `query:read` in project 718705, internal exclusions, actual source schema, read-only DB access, the new Nginx locations, private state permissions and applicable CSP domains. Publish only JS/CSS as public assets; keep the HTML behind its authenticated route and keep the state/config private. Reload only the required service/config after checking Nginx. Verify a consented non-internal visit, one real registration and a confirmed test payment through the application's authorized payment test mechanism. Do not turn on Replay as part of this integration. Unit/browser tests alone do not prove live ingestion or a live payment. The separate connected-account verification below records the actual SQL and diagnostic ingestion checks; the real customer conversion journey remains pending production release; application read-key verification is recorded below.

Official references checked 2026-11-08: [JavaScript configuration](https://posthog.com/docs/libraries/js/config), [privacy](https://posthog.com/docs/privacy/data-collection), [Query API](https://posthog.com/docs/api/query), [API scopes](https://posthog.com/docs/api/scopes), [private API keys](https://posthog.com/docs/api/personal-api-keys), [Capture API](https://posthog.com/docs/api/capture).


## Connected-account verification (2026-11-08)

The owner connected the official PostHog plugin. `projects-get` and `project-get` confirm access to US project **718705**, named **Default project**, with project timezone **UTC**. `api_host` confirms the US ingestion region. Session recording opt-in is **false**. At initial inspection, before diagnostic delivery, project metadata reported no ingested events and schema discovery found no recently observed Swipies events. This did not mean that the landing had no visitors.

All seven SQL statements generated by the current application were executed successfully through the real PostHog connection: period totals, hourly timeline, CTA, UTM/referrer, devices and both ordered funnel periods. The real `events` column schema was checked first. These are read-only parser/execution smoke tests against an empty project, not a successful real conversion or ingestion test. At this stage no event had been sent. Subsequently, two explicitly test/internal diagnostics verified ingestion and the privacy settings below. No fake pageview, registration or payment was emitted, and no landing deployment or production collection was activated.

The project's actual public capture token and US host configuration were retrieved without printing their values and merged into the existing ignored **local** landing `.env`, preserving unrelated settings and keeping `POSTHOG_ENABLED=0`. The owner subsequently supplied the separate secret `POSTHOG_READ_API_KEY`; it is stored only in the ignored local `.env` and was not included in tracked files or command output. The chat plugin's delegated credentials are not extracted or reused by the application. Its exposed tools do not create a scoped personal reporting API key, so a separate owner-created `query:read` credential is used in [Personal API keys](https://us.posthog.com/settings/user-api-keys). Restrict project access to 718705 where the UI supports it. Do not enable broad read/write scopes.

A workspace-only `work/set-posthog-read-key.ps1` helper provides hidden local input, validates the personal-key format, writes only the ignored local environment setting and does not enable capture or deploy. It does not print the key. This is a local setup aid, not a published web asset. The user can alternatively set the same variable through their private environment-management process. The application's own Query API transport and administrator report endpoint were subsequently validated with that key. A separate explicit production-release instruction is still required. Real landing → registration → paid checkout verification remains pending that release and an authorized payment test.

Official plugin skills consulted: `posthog:querying-posthog-data` and `posthog:instrument-product-analytics`. User restrictions take precedence over their generic recommendations: no form-content identification, no error payload capture and no broad instrumentation beyond this task were added.


### Diagnostic delivery and privacy controls

Two events named `swipies_integration_check` were sent via the official Capture API, with independent check IDs, `swipies_environment=test` and `swipies_internal=true`. Read-only queries confirmed each was received once and neither matched the production report predicate. They are diagnostics, not pageviews or successful registrations/payments. The first diagnostic exposed automatic GeoIP enrichment through property metadata (no IP/location values were queried). That prompted a privacy fix before any release.

In the actual project, `anonymize_ips=true`, `capture_console_log_opt_in=false` and `session_recording_opt_in=false` are now confirmed. The browser allowlist and conversion collector explicitly set `$geoip_disable=true` and `$ip=null`; these cannot be overridden by incoming properties. The second live diagnostic confirmed **one received event, zero matches in working reports and zero events with GeoIP enrichment**. Earlier diagnostics are retained as labeled test data; no deletion was attempted. The landing remains undeployed and local collection remains disabled.

Rate-limit handling now respects an API budget `Retry-After` of up to one hour, including a regression test that prevents early retry at 3,599 seconds. Current validation: **73 Python tests passed, 10 browser tests passed (including the actual official SDK), Ruff passed**. The private application read-key is verified below; the actual production conversion journey remains pending.


### Application transport verification with the supplied read key

The owner supplied a reporting credential, which was saved in the existing ignored local `.env`; a temporary transfer file was removed immediately. No credential values were printed or added to tracked code/documentation. `POSTHOG_ENABLED=0` was preserved.

The workspace-only `work/verify_posthog_read_key.py` used the real current `landing_posthog` code and actual Query API transport against project 718705. It registered an isolated Flask test application with the current native administrator authorization functions and a temporary, test-owned session database. It did not start an HTTP server or the conversion daemon, and it did not change production, the existing administrator database, or the stored collection flag.

Result: the administrator report returned HTTP 200 / `state=ready`; all **seven queries** succeeded using the supplied credential. Unauthenticated status/report requests returned 401 and the private page redirected to the existing login. The public capture token and secret read key were absent from the report response. No capture events were sent by this check. Platform comparison was deliberately unavailable in this isolated transport test; it does not prove access to the actual production MySQL facts.

The local Python environment emitted an existing Requests dependency-version warning, but the live request completed successfully; no dependencies were changed. Production package/runtime compatibility, the real Nginx route and the full registration/payment journey must still be checked during a separately authorized release. Current automated validation remains **73 Python tests + 10 browser tests**, alongside the actual-provider checks above.
