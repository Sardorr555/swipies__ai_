# Requirement Checklist: Swipies Ads Security & Admin Password Bugfix

## Acceptance Criteria Checklist

- [x] **AC1 (SEC-01): Elimination of `/v1/ads/billing/deposit` Backdoor**
  - [x] Delete `deposit_advertiser_balance` endpoint in `api/apps/ad_app.py`
  - [x] Verify `POST /v1/ads/billing/deposit` returns HTTP 404
  - [x] Verify balance crediting only works through Atmos webhook callback

- [x] **AC2 (SEC-02): Elimination of Currency Arbitrage**
  - [x] When `amount_uzs > 0`, ignore client-supplied `amount_usd` in `payment_service.py`
  - [x] Calculate `amount_usd = round(float(amount_uzs) / rate, 2)` server-side
  - [x] Automated test: request with `amount_uzs: 100` and `amount_usd: 10000` is computed as ~0.01 USD

- [x] **AC3 (SEC-03): Protection of Subscription Renewal Worker**
  - [x] Add `require_superuser()` to `POST /v1/ads/admin/process-renewals` in `ad_app.py`
  - [x] Automated test: non-superuser receives 403 Forbidden
  - [x] Automated test: superuser is allowed

- [x] **AC4 (SEC-04, SEC-05, SEC-06): Multi-Tenant Isolation & IDOR Elimination**
  - [x] SEC-04: Campaign insights verifies `AdCampaign.advertiser_id == adv.id`
  - [x] SEC-05: Audience members verifies `AdAudienceSegment.advertiser_id == adv.id`
  - [x] SEC-06: Feeds management verifies `AdFeed.advertiser_id == adv.id`
  - [x] Automated test: accessing other tenant's resources returns 404 / 403

- [x] **AC5 (ARCH-03): Removal of Fast-Path DDL Mutations**
  - [x] Remove all `ALTER TABLE` DDL queries from `ad_engine_service.py`
  - [x] Ensure `AdAdvertiser` / `AdTrackingPixel` have static columns in `db_models.py`

- [x] **AC6 (SEC-07): Developer Email Removal & Hardcode Cleansing**
  - [x] Remove `albakiev.sardorbek@gmail.com` from `api/db/db_models.py` (line 3645)
  - [x] Remove `albakiev.sardorbek@gmail.com` from `admin/server/auth.py` (line 339)
  - [x] Parameterize SQL queries with `DEFAULT_SUPERUSER_EMAIL`

- [x] **AC7 & AC8 (BUG-08, BUG-09): Atomic Balance Mutex & Deprecation Cleanup**
  - [x] Balance updates use `with DB.atomic():` and `for_update()`
  - [x] Remove peewee `reload()` calls

- [x] **AC9 (BUG-10): Admin User Password Management & Authentication Bugfix**
  - [x] Frontend: connect submit button directly to form submit
  - [x] Frontend: suppress browser autofill on password fields (`autoComplete="new-password"`)
  - [x] Frontend: explicitly reset form fields upon modal open
  - [x] Frontend: add `encodeURIComponent(username)` in `api.ts`
  - [x] Frontend: add toast messages (`message.success`, `message.error`)
  - [x] Backend: case-insensitive and whitespace-stripped lookup in `admin/server/services.py`
  - [x] Backend: normalize emails in user authentication routines
  - [x] Verification: changing user password in admin panel succeeds and login succeeds
