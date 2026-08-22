# Swipies AI (RAGFlow) Constitution

## Core Principles

### I. Dynamic API Model Discovery & Zero Hardcoding (NON-NEGOTIABLE)
- **Live Provider Introspection**: Model catalogs must never rely on static/hardcoded lists for remote AI providers. All available models (Chat, Embedding, Rerank, Vision, ASR, TTS) must be queried dynamically via live provider endpoints using the configured API credentials.
- **Resilience & Fault Tolerance**: Single-capability failures (e.g. 403 on experimental embedding endpoints) must never fail the entire provider connection if core model discovery or chat generation is operational.
- **Zero Phantom Models**: Only verified, active models returned by live provider APIs with valid credentials may be exposed to tenants and users.

### II. Admin-Governed Centralized AI Defaults
- **Platform-Wide Sovereignty**: The System Administrator controls all default model assignments (Default Chat, Default Embedding, Default Rerank, Default Vision, and Tier-specific models) via the Admin Panel.
- **Instant Tenant Synchronization**: Changes made to global default models must automatically propagate to tenant defaults (`Tenant.llm_id`, `Tenant.embd_id`, `Tenant.rerank_id`, `Tenant.img2txt_id`, `Tenant.asr_id`) and in-memory runtime settings.

### III. Reproducible & Fail-Safe Containerized Deployments
- **Clean State Guarantees**: Docker and Compose deploy pipelines must enforce robust pre-launch cleanup (`set +e` cleanup routines for containers, networks, and volumes) to eliminate name conflict aborts.
- **Zero Secrets in Git**: All API keys, tokens, and instance credentials belong strictly to the database/environment variables and must always be masked before reaching frontend clients or logs.

### IV. Type-Safe Fullstack Architecture & Contracts
- **Clean Separation of Concerns**: React 19 / TypeScript / Vite frontend decoupled from Flask / Peewee / Python 3.11+ backend services through explicit DTO interfaces and REST/SSE contracts.
- **Defensive API Validation**: Every API endpoint must validate schemas, handle database transaction lifecycles cleanly, and return standard JSON error responses (`code`, `message`, `data`).

### V. FinOps, Token Quotas & Observability
- **Strict Subscription Boundaries**: Model usage must honor subscription tiers (FREE, PLUS, PRO) with token limits, requests-per-minute limits, and per-model quotas.
- **Structured Logging & Auditing**: Every model invocation and administrative modification must be traceable with timestamps, user context, and token usage accounting.

## Development & Spec Workflow

### SDD Phase Protocol
1. **Specify (`/speckit-specify`)**: Establish clear, unambiguous requirements and scope boundaries before writing code.
2. **Plan (`/speckit-plan`)**: Break features into phased architectural plans with verified data structures.
3. **Tasks (`/speckit-tasks`)**: Generate discrete, testable checklist tasks.
4. **Implement (`/speckit-implement`)**: Execute changes in accordance with TDD and regression testing.
5. **Converge (`/speckit-converge`)**: Review codebase diffs, remove stale dead code, and verify end-to-end functionality.

## Governance

- **Supremacy**: This Constitution governs all technical architecture, pull requests, and automated refactoring tasks across the Swipies AI codebase.
- **Amendments**: Amendments require explicit justification, documented rationale, and verification across backend and frontend services.

**Version**: 1.0.0 | **Ratified**: 2026-08-20 | **Last Amended**: 2026-08-20
