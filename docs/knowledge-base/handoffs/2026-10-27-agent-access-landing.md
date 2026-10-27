# Public AI access landing release — 2026-10-27

Branch: swipies_26. Scope: static public cloud landing and AI integration docs.

Published EN/RU/UZ external AI control section with navigation, hero/footer
links, an example workflow, copyable prompt and FAQ. Added a standalone guide,
llms.txt, full plaintext instructions, custom discovery JSON, OpenAPI 3.1 and a
downloadable stdio client. Homepage metadata and sitemap expose the new guide.
The runtime operation catalog is authoritative. Client setup, tenant boundaries,
external credentials and Plus/Pro-only branding removal are explicitly covered.
No claim that every AI automatically installs tools by reading a URL is made.

The current production cloud index was used as the editing baseline because the
checked-in root was an older enterprise page. Server routing, enterprise site,
payment forms, platform backend and database were not changed.

Validation: 24 static checks passed (HTML IDs/anchors, inline JS, structured
data, EN/RU/UZ completeness, OpenAPI refs/JSON Schemas, sitemap, client byte
equality). Codex CLI's local help confirms the documented `mcp add` syntax.
Desktop Russian and 390px Uzbek layouts had no horizontal overflow; translation
and copy-success UI worked. Browser clipboard readback was unavailable in the
test harness, so exact clipboard contents were not independently verified.
The live public API manifest matches the documented protocol and branding;
the operation catalog rejects anonymous access.

All eight published URLs returned HTTP 200 with correct MIME types. JSON,
plaintext, XML and downloaded client matched staging exactly; origin files
matched byte-for-byte, and CDN HTML passed semantic checks. Two earlier attempts
rolled back automatically: CDN changes HTML and Nginx denies .py downloads.
The final source is served as .py.txt, with explicit save-as instructions, leaving
the existing deny policy intact. Successful private backup:
`/home/ubuntu/swipies-deployments/landing-20261027T001637Z`.

Static publication is separate from the platform deployment workflow. The
commit uses [skip ci] to avoid an unrelated application restart. Future static
changes follow README-agent-access.md in the landing directory. No additional
platform, CRM or paid Ads live verification was implied by this static release.
