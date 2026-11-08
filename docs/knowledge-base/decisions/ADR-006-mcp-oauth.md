# ADR-006: OAuth authorization for the existing tenant MCP gateway

- **Status:** Accepted for local implementation; production enablement pending.
- **Date:** 2026-10-29
- **Branch:** swipies_26
- **Modules:** `api/agent_oauth.py`, `api/db/services/agent_oauth_service.py`,
  `api/agent_access.py`, consent template and Nginx discovery routing.

## Context

API-key/stdio clients can bootstrap a Free account and manage tenant resources.
A webpage-reading ChatGPT session cannot acquire HTTP write tools from visiting
the landing page, and ChatGPT's custom remote MCP path needs supported OAuth
authorization to access private tenant resources without copying API keys.

## Alternatives

1. Public unauthenticated MCP: rejected because private tenant writes require
   account isolation and revocable authorization.
2. API keys only: retained for existing clients but insufficient for ChatGPT's
   OAuth connection flow.
3. External OAuth identity provider: a valid future option, but no configured
   provider currently represents Swipies' existing owner/anonymous Free identity.
4. OAuthLib authorization code/PKCE adapter over existing identity services:
   selected. OAuthLib handles the protocol; the platform resolves only its own
   logged-in owner or existing constrained Free bootstrap service.

## Decision

Add feature-gated standard resource/server discovery, CIMD and bounded dynamic
client registration, S256 PKCE, explicit consent and opaque resource-bound tokens.
Pin ChatGPT metadata/callback locations; arbitrary remote client documents and
redirects are not accepted. This initial OAuth adapter supports ChatGPT, while
other clients keep using API-key/stdio access until reviewed OAuth callbacks are
added.

Reuse the existing APIToken and tenant authorization model. A connection receives
its own delegate key, stored only inside encrypted Redis grant records. External
OAuth clients receive short-lived opaque credentials. Read/write/offline scopes
are enforced by the gateway before existing route dispatch. Existing route
permissions, quotas, subscription rules and Plus/Pro branding remain authoritative.

Reuse AES-GCM/master-secret fail-closed policy without changing ciphertext format
or adding custom cryptographic protocol. Use shared Redis TTL records and atomic
Lua consumption for one-use codes/refresh rotation. Replay revokes the grant and
delegate. Do not alter DB schema, Go/CRM/Ads modules or old API-key behavior.

## Consequences and verification

A new OAuth-capable client can connect with one consent; users can create a Free
workspace or keep their existing owner workspace and subscription. No universal
automatic connector installation is claimed. Client host permissions still apply.

Redis loss and absolute grant expiry require reconnect. Anonymous Free claiming/
recovery and automatic cleanup of abandoned delegate-key rows remain outside this
change. OAuth callbacks are provider-specific and deliberately limited.

See [OAuth operations and release guide](../oauth-access.md) for configuration,
token lifetimes, revoke/rollback, tests and pending live ChatGPT verification.
