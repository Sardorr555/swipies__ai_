# Official landing support chatbot — 2026-10-28

The owner requested a real Swipies chatbot on the public landing page using the
platform's native widget. Resources are permanent; do not treat them as disposable
audit data. Workspace: the previously authorized Pro service account.

- Chat: `211a043cd2eb11f1b59c0571c62b03a7` (Swipies AI — Website Assistant).
- Dataset: `196a1d76d2eb11f1b59c0571c62b03a7` (Swipies — Website Knowledge Base).
- Five indexed, curated public product/onboarding/integration/agent-access/plan
  documents, verified against official public pages on 2026-10-28.
- System instruction: [landing-support-system-prompt.md](landing-support-system-prompt.md).
- The assistant explains the product in Russian, English and Uzbek. It has no
  management tools, does not claim account actions, invent prices or request keys.
  Human contact is Telegram/email; there is no automatic operator handoff.
- Six live native-chat checks cover onboarding, agent access, Uzbek branding,
  unsupported account actions, human contact and invented pricing/prompt injection.
  All returned grounded answers. Exact pricing is intentionally referred to checkout
  because public landing and license configurations contain differing amounts.

The landing only adds support-chat.js, which hosts /chats/widget in master/window
mode and validates postMessage origin/source. The public native embed credential
is delivered in /support-chat-config.json, provisioned separately on the server;
never commit management keys or the generated config. Public embed access is
confirmed unable to manage datasets. Existing fonts, layout and amber section stay.

Shared-chat authorization is now read from the embed URL without updating the
owner's cookie/localStorage, borrowing an owner session or logging the owner out
when public auth expires. 30 auth tests and 70 existing widget tests pass; the
production frontend build passes. Shared-view cleanup/redirect operations preserve
the account session. This is required before publishing a widget on the same root
domain as the platform.

Release uses [skip ci], a frontend-only build/restart with rollback, and a separate
three-file static landing publication with baseline checks/private backup. Do not
restart backend/storage containers, migrate databases, or change Nginx. Confirm
live browser open/send/close/history behavior before declaring publication complete.
