# Sales solution landing

Date: 2026-11-08. New isolated hostname: https://sales.swipies.app/.
The main public swipies.app landing, its assets and certificate are unchanged.

## Experience
Russian sales page: clear offer, furniture conversation illustration, benefits,
interactive canned examples for products/services/courses, supported integration
boundaries, setup guide, FAQ and platform calls to action. Demonstrations are
explicitly labeled examples; no live LLM or fabricated customer testimonials.
No invented prices, conversion figures, automatic CRM write claims or paid orders.
Inter is served locally with its original OFL license; no third-party tracking SDK.

## Shared administrator connection
Every platform CTA has data-swipies-platform. The existing acquisition-link.js
is loaded with data-landing=sales. It forwards sw_campaign and standard UTM tags
to the existing central /api/acquisition/go/sales redirect. That service records
the landing and tags and passes a random vid to the unchanged platform login.
Registrations can be matched by the existing shared admin, subject to its documented
identity limits. Sales already exists in the admin registry at the correct URL;
leave active=0 until DNS, independent TLS and HTTPS are verified.

## Isolated deployment
Source: new site for swipies/solutions/sales. Server root: /var/www/swipies-sales.
Dedicated Nginx config: /etc/nginx/sites-available/swipies-sales, with a separate
sites-enabled symlink. ACME webroot: /var/www/swipies-sales-acme. The shared main
Nginx file is not replaced or edited. Separate TLS certificate name: swipies-sales;
do not expand or replace the main swipies.app certificate.

Current stage: production HTTPS published 2026-11-09 after owner confirmed DNS.
Sales is active in the shared administrator registry. Its dedicated Let's Encrypt
certificate covers only sales.swipies.app. Existing main configuration and
certificate were not edited. Realty and every other registry row were preserved.

## Validation
Chrome checks passed at 1440, 1024, 768, 390 and 320px: no horizontal overflow,
demo choices, keyboard-accessible tabs, FAQ, mobile menu and reduced motion.
All five platform CTA URLs carry the expected sales landing and UTM values.
No test transitions or demo accounts were inserted into production analytics.
Main public index hashes match the baseline after isolated server staging.

## Production verification — 2026-11-09
Public HTTPS and all static assets return 200. Chrome verified the real attribution
script, all five Sales CTA URLs with UTM preservation, interactive demo tabs and
mobile navigation. No production CTA was opened for testing and no synthetic
transition or account was created. Sales is active=1; Realty remains active=0.
Protected main public/private index.html, shared Nginx file and main certificate
hashes matched the pre-launch baseline. A separate renewal configuration and
Sales-only guarded Nginx reload hook were installed for the new certificate.
Cloudflare briefly returned 526 during the initial reload; the Sales config was
rolled back, then successfully activated after direct SNI and public HTTPS checks.
No TLS verification or Cloudflare security setting was disabled.

## Multichannel positioning, languages and brand — 2026-11-09

Release: sales-content-20261109-0c031850. Public /uz/, /ru/, /en/ pages include translated
copy, metadata and all interactive examples. Root keeps the existing Russian default.
Language links preserve the current query and campaign identifiers; all locales
still use acquisition landing=sales. No admin or platform code change was needed.

Positioning emphasizes an AI seller connected to Telegram, Instagram Direct, a
website and other channels. Non-standard integrations depend on platform capabilities
and account access and are offered individually; no unrestricted third-party access
or new working connectors are implied by the marketing copy.

Header/footer reuse the original public SwipiesAI wordmark, its original JetBrains
Mono font, amber accent and the identical primary favicon. The invented symbol
was removed. Local font licenses are bundled. The primary site itself was not edited.

Validation: 27 localized demo answers, 15 viewport combinations, accessible tabs,
mobile menus, FAQ and campaign-preserving language links passed. No Cyrillic remains
in the rendered Uzbek/English pages. Live browser checks verify the real shared
tracking script without creating production CTA events. Server-side backup and
protected primary file/config/certificate hashes were checked during publication.

## Brand and interface SVG icons — 2026-11-09

Release sales-content-20261109-f7f4bb7e. Replaced pseudo-icons in all three locales with
canonical Telegram/Instagram brand glyphs from installed Simple Icons (CC0),
and canonical Lucide interface icons (ISC). Original glyph path geometry is
preserved. Licenses and attribution are bundled locally. Reworked channel icon
tiles and spacing; the shared SwipiesAI wordmark is unchanged.
All 27 demo answers, 15 responsive combinations, language switching and UTM
checks passed locally. Public language pages show the updated SVGs without
creating test CTA transitions. Primary website and shared admin were unchanged.
