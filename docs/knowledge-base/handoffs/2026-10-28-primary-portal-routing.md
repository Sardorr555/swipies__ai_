# Primary portal routing correction

Date: 2026-10-28 (Asia/Tashkent). Branch: `swipies_26`.

## Result

The shared authentication resolver previously selected a retired portal for most
Swipies subdomains, including the API portal. Login/registration-related 401
redirects now keep `api.swipies.app` on that origin. Existing `app.swipies.app`
deployments retain their own origin. Ads and other official subdomains use the
API portal; localhost/IP/custom installations keep local routing.

`getMainAppUrl` in `web/src/utils/authorization-util.ts` is also reused by the Ads
return link. Both payment checkout URL constructors return to
`https://api.swipies.app/ads`, preserving the payment result ID. Explicit retired
hostname references have been removed from all tracked text files and the
production frontend bundle.

Docker Python/hybrid/Go/HTTPS Nginx templates and the frontend Nginx template no
longer list the retired hostname. The landing Nginx generator retains Ads only
in its auxiliary block. The licensed-server workflow now calls the Ads-only
`docker/setup_ads_nginx.sh` helper. The old combined helper was replaced.

## Validation

- Jest: 45 tests passed across auth cross-subdomain/session synchronization and
  floating widget bugfix suites. Added coverage for API and Ads routing,
  registration return parameters, existing app origin, custom origins and
  misleading domain suffixes.
- Existing mocked Atmos payment suite: 7 tests passed using temporary local
  SQLite. Added checks for the initial and reloaded checkout return URLs and
  matching payment result IDs. No real payment or production DB was used.
- Vite production build: success, 14,393 modules transformed, 1m 52s.
- Python source and Nginx generator: parsed without execution. Updated workflow
  YAML parsed without executing any deployment steps.
- Git whitespace check: clean. Source and generated frontend hostname scans:
  no matches for the retired portal.

The payment harness emitted SQLite compatibility warnings already outside this
URL-only change; the suite completed successfully. Vite emitted dependency/chunk
size warnings. No local Linux distribution or Nginx binary is installed, so
`bash -n`/`nginx -t` could not be run locally. Validate those on a Linux staging
host before executing the changed host setup helper.

## Release boundary

The owner authorized publishing this correction to `swipies_26`. Its push
triggers the existing main deployment workflow; completion must be checked
separately before calling the live site fixed. No DNS or Cloudflare changes,
or manual host Nginx reload, are included. Removing a hostname from
source does not remove old DNS records or installed host Nginx site files; review
those separately during an authorized release. Do not run the host setup helper
blindly on a server that still has an older combined Ads site configuration.
