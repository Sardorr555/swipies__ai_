# Provider model catalog and subscription access

Updated: 2026-11-27. Branch: `swipies_26`.

The public Telegram analytics page owns a viewport-height scrolling region. It can scroll inside the application root, which deliberately hides overflow. This covers mobile browsers and long shared dashboards without changing the authenticated application layout.

In `/admin/ai-management`, **Обновить каталог из API** reads all returned models from configured global providers. Discovery uses the saved credential only on the server. It populates the platform catalog without requiring a TenantModel installation and preserves existing model prices, kill switches, plan grants, and user overrides. Gemini and Anthropic discovery follows pagination. Provider errors do not return credential-bearing exception strings.

The subscription model matrix supports separate Free, Plus and Pro rules and model/provider search. Newly discovered models have no automatic plan grant; the administrator enables each desired plan. Existing plan assignments are retained. Repeated policy edits update all legacy rows matching the plan and model rather than creating conflicting primary-key variants. Editing a token cap alone does not enable the model.

The model picker and default-model settings honor the same access rules as runtime execution. A quota-exhausted model remains visible, while inference still enforces its quota. A disabled policy overrides a plan default. A registered global model without a grant is denied unless it is the plan default or has an explicit user allowance. Runtime rejects denied IDs and composite names before provider credential fallback. The model list includes published platform models and the tenant's own models; it does not inherit unpublished administrator installations.

Discovery stores capability labels for embeddings, transcription, TTS, realtime and image generation, avoiding their inclusion in text-chat selectors. The admin catalog includes disabled entries so they can be managed again. No new schema, branch, or runtime container is required.

Regression suite: `test/test_platform_model_catalog.py`, `test/test_model_provider_security.py`, and `test/test_telegram_analytics.py`, run against the existing dedicated QA schema. The browser verification checks that the shared dashboard scrolls from its header to its footer at mobile width.
