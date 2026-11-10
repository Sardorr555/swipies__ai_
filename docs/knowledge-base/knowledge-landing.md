# Knowledge solution landing

Published 2026-11-09 by explicit owner request: https://knowledge.swipies.app/uz/,
/ru/ and /en/. Root preserves Russian default. Shared acquisition registry
knowledge / https://knowledge.swipies.app/ is active=1.

## Design skills and direction
Applied downloaded design-it skill and its editorial-design reference:
C:/Users/KTS/.agents/skills/design-it/SKILL.md and
C:/Users/KTS/.agents/skills/design-it/editorial-design/SKILL.md.
Chose its Yacht Club palette: #F9F6F0 paper, #1B2A49 ink, #C85A32 accent,
#E2D8C9 secondary base. Original Swipies logo amber is preserved as a brand
exception. The page is a new editorial composition, not a recoloured Support
template: asymmetrical headline/document hero, fine rules, numbered content rows,
split answer/source reader and a final typographic callout.

Locally served Playfair Display (upright and real italic) and Source Sans 3 are
paired for editorial headings and readable body copy. Fonts come from the official
Google Fonts repository and are converted to WOFF2 with fontTools; OFL licenses
are bundled. Original SwipiesAI wordmark, original JetBrains Mono logo font and
identical favicon are reused. Telegram uses canonical brand SVG geometry and
generic icons use Lucide, with bundled licenses. No Unicode pseudo-icons or new logo.

## Content and interaction
AI document assistant offer, formats, capabilities, use cases, integrations,
setup instructions and FAQ are fully translated. Three sample questions per
language have two source references each. Selecting a reference opens the
appropriate excerpt and page/section alongside the answer. Examples explicitly
use fictional documents and prewritten answers, not a live AI service.
Source attribution in actual agents depends on retrieval and display configuration;
the page states this instead of promising a source for every answer.

Responsive layouts fall back to one column on phones. Native FAQ, keyboard tabs,
visible focus and reduced-motion behaviour are implemented. Motion is limited to
opacity/transform reveals and a short source selection transition.

## Shared administrator and isolated deployment
All five platform CTAs use the unchanged shared acquisition-link.js with
data-landing=knowledge. Language links preserve UTM and sw_campaign. The existing
central redirect records Knowledge transitions and uses the existing visitor ID
and registration mechanism. No platform or administrator code was changed.

Static root /var/www/swipies-knowledge; dedicated Nginx config and symlink
swipies-knowledge; independent certificate swipies-knowledge and dedicated ACME
webroot. The renewal reload hook is guarded by this certificate lineage.
Main swipies.app, Sales and Support content/config/certificate hashes were
protected during launch. All other registry rows were preserved.
Staging release: knowledge-20261109-23c0874d.

## Verification
Local Chrome: UZ/RU/EN, nine question selections, 18 reference states, 15 viewport
combinations, keyboard navigation, mobile menu, FAQ and reduced motion passed.
No Cyrillic remained in rendered Uzbek/English pages. Live Chrome verified HTTPS,
actual fonts, real tracking script, source interactions and campaign-preserving
language links. Public pages/assets return 200. Original favicon hash matches
the primary site's favicon. No synthetic CTA transition, lead or account was
created in production. Main site, Sales and Support remain unchanged.
