# ADR-005: External agents use tenant APIs through MCP

- Status: Accepted for implementation; not deployed
- Date: 2026-10-26
- Branch: swipies_26
- Modules: api/agent_access.py, api/db/services/agent_access_service.py, tools/swipies_agent_client.py

## Context

External agents must operate Swipies without browser automation or an LLM running inside Swipies. Customers need separate identities. Reusing one platform owner's key for all agents would merge tenant data and bypass subscription isolation. Existing MCP integrations and the Go retrieval server do not provide full Python tenant API management.

## Alternatives

1. Browser automation: requires an interactive login and duplicates frontend behavior.
2. A second set of MCP CRUD services: duplicates authorization, quotas and business logic.
3. A stateless authenticated MCP facade over registered tenant APIs, with a local automatic-bootstrap client: selected.

## Decision

Mark common login_required wrappers with accepted authentication types. Build the operation catalog only from selected user-facing API families accepting API tokens. Dispatch operation ids in-process through ASGI with the caller's bearer token and bounded response collection. Never accept arbitrary URLs, privilege contexts, cookies or redirect targets.

Anonymous service-account bootstrap is separate from human sign-in. A client-generated random identity makes retries idempotent; new users are forced to Free. Shared registration record preparation preserves the existing model defaults, while direct model writes provide one transaction (service decorators close DB connections and cannot be nested in the transaction). Redis applies atomic per-source and global creation limits. Disabled credentials are not restored. Existing customers can use existing API keys.

Branding is an independent entitlement: only active persisted Plus/Pro plans grant omission. Advertising configuration and inferred superuser Pro capabilities are not branding entitlements.

## Consequences and verification

No schema migration, extra privileged key, Go business module or platform-side LLM is needed. Supported operations follow the authenticated Python REST surface. External hosts still require their own MCP setup and authorization; account claiming and recovery are not implemented. See ../agent-access.md for release conditions, size/time limits and tests. Integration tests use the official MCP SDK and SQLite transactions without production services.
