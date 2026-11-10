# Support solution landing

Published 2026-11-09 by explicit owner request. Public URLs:
https://support.swipies.app/uz/, /ru/ and /en/; root preserves Russian default.

## Experience and branding
Separate AI support marketing page with a centered offer, interactive support
console (delivery/login/specialist cases), example source documents, capabilities,
channels, setup guide and FAQ. All copy, metadata, demo answers and controls are
translated into Uzbek Latin, Russian and English. Examples explicitly use fictional
documents and are not a live AI agent. No fake response-time statistics, tickets,
prices or customer testimonials are presented.

Reuses the original SwipiesAI wordmark, original favicon and locally served
Inter/JetBrains Mono fonts. Telegram and Instagram use canonical brand SVG geometry;
generic UI icons use canonical Lucide nodes. Licenses are bundled. No new brand
mark or Unicode pseudo-icons. Source: new site for swipies/solutions/support.

## Shared platform and administrator
All five platform CTAs use the existing shared acquisition-link.js with
data-landing=support. Language links retain UTM and sw_campaign. The existing
central redirect records Support transitions and forwards the existing visitor ID
and UTM mechanism into platform registration. The exact existing registry row
support / https://support.swipies.app/ is active=1. Other registry rows, including
Sales and Realty, were unchanged. No platform or administrator code was edited.

Marketing describes knowledge-grounded replies and preparation for escalation.
Order checks, actual helpdesk ticket creation and automatic handoff require their
own configured tools/integrations; the page does not claim those are enabled.

## Deployment isolation
Static root /var/www/swipies-support. Dedicated Nginx file and symlink
/etc/nginx/sites-available/swipies-support and sites-enabled/swipies-support.
Separate certificate swipies-support issued through the existing ACME account;
renewal uses /var/www/swipies-support-acme and a lineage-guarded reload hook.
The main swipies.app files, shared Nginx configuration and main certificate were
not changed. Sales files, virtual host and certificate hashes were also protected.
Release staging: support-20261109-26d8ff97. Scoped backups and baseline metadata
remain on the server under /home/ubuntu/swipies-admin-releases/.

## Verification
Local Chrome: three locales, nine example cases, 15 viewport combinations,
keyboard tabs, mobile menu, FAQ, UTM-preserving CTAs and language switches passed.
Live Chrome: actual HTTPS pages, real tracking script, support handoff URLs,
all demo cases and mobile navigation passed without clicking platform CTAs.
Public pages and assets return 200. Support active=1 and Sales active=1 were read
from the registry; original favicon hash matches the main site's favicon.
No synthetic transition, ticket, lead or user account was created in production.
