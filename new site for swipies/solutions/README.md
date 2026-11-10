# Solution landing requirements

Owner requirements, 2026-11-09:
- Every new solution landing must have Uzbek (Latin), Russian and English versions.
- Translate the complete page, interactive demos, navigation and metadata.
- Preserve UTM and sw_campaign when visitors switch languages.
- Reuse the exact SwipiesAI wordmark and favicon from swipies.app. Do not invent
  separate solution logos. The primary wordmark uses JetBrains Mono 700 and amber AI.
- Never modify the primary swipies.app landing when editing solution pages.
- Connect solution platform CTAs to the existing shared acquisition admin.

Sales is the first implementation: /uz/, /ru/, /en/ (root preserves Russian default).
All pages share the same sales landing identifier and the same platform account.

Use actual brand SVG glyphs for named platforms (Telegram, Instagram, etc.).
Use one consistent vector interface icon set for generic website/CRM/UI functions.
Do not substitute Unicode symbols or invented marks for platform brand icons.
