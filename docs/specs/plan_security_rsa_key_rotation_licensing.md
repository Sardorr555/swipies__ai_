# Technical Implementation Plan: RSA Key Rotation & Licensing Security Incident Remediation

**Plan Key:** `plan_security_rsa_key_rotation_licensing`  
**Parent Specification:** [`spec_security_rsa_key_rotation_licensing`](file:///D:/ragflow/swipies_25/ragflow/docs/specs/spec_security_rsa_key_rotation_licensing.md)  
**Target Branch:** `licence_v`  
**Security Incident ID:** `SEC-INC-2026-0828-01`  
**Document Status:** Ready for Review  
**Version:** 1.0.0  
**Date:** 2026-08-28  

---

## 1. Architectural Overview & Strict Gated Execution Graph

To guarantee that private cryptographic materials and access tokens are never exposed again, the implementation is governed by **strict, non-skippable gate conditions**.

```mermaid
flowchart TD
    subgraph Immediate [⚡ PHASE 0: IMMEDIATE ACTION - SEC-PAT]
        P0["AC-4: Revoke Leaked GitHub PAT & Sanitize install.sh"]
    end

    subgraph Phase1 [📦 PHASE 1: PHYSICAL BUILD SEPARATION - AC-1]
        P1A["Remove COPY generate_license.py from Dockerfile"]
        P1B["Add generate_license.py to .dockerignore & .gitignore"]
        P1C["Remove generate_license.py from licence_v working tree"]
        P1D["Build & inspect client Docker image layers"]
    end

    GATE1{{"🔒 GATE 1: Build Layer Verification\n(Zero trace of generator in any image layer)"}}

    subgraph Phase2 [🔑 PHASE 2: KEY ROTATION & SERVER ISOLATION - AC-2 & AC-5]
        P2A["Generate new RSA-2048 pair (N_new, E_new, D_new)"]
        P2B["Place D_new & generator STRICTLY on swipies.app server"]
        P2C["Implement POST /v1/licenses/verify authoritative API"]
    end

    GATE2{{"🔒 GATE 2: Closed Server Confirmation\n(D_new safely stored only on swipies.app, not in git/client)"}}

    subgraph Phase3 [🛡️ PHASE 3: CLIENT VERIFIER UPDATE - AC-2.4 & AC-2.5]
        P3A["Update license_verifier.py with N_new / E_new (ver=2)"]
        P3B["Remove SWIPIES-ACT- bypass branch"]
        P3C["Verify automatic rejection of old D_old signatures"]
    end

    GATE3{{"🔒 GATE 3: Rejection & Verification Test\n(Old keys fail with Invalid signature; v2 keys pass)"}}

    subgraph Phase4 [🚚 PHASE 4: CLIENT REISSUE & NOTIFICATION - AC-3]
        P4A["Run batch migration script for active paid licenses"]
        P4B["Update customer license portal on swipies.app"]
        P4C["Trigger transactional notification emails"]
    end

    subgraph Phase5 [🧪 PHASE 5: FINAL SYSTEM AUDIT & CI/CD HARDENING]
        P5A["Full end-to-end regression & security verification"]
        P5B["CI/CD secret scanner configuration"]
    end

    Immediate --> Phase1
    Phase1 --> P1A --> P1B --> P1C --> P1D --> GATE1
    GATE1 --> Phase2
    Phase2 --> P2A --> P2B --> P2C --> GATE2
    GATE2 --> Phase3
    Phase3 --> P3A --> P3B --> P3C --> GATE3
    GATE3 --> Phase4
    Phase4 --> P4A --> P4B --> P4C --> Phase5
```

---

## 2. Phase Breakdown with Gated Criteria

### Phase 0: Immediate Emergency Action (AC-4: Token Revocation)
> **Rationale:** The GitHub Personal Access Token (`ghp_7W6rLcA...`) is live right now in [`install.sh`](file:///D:/ragflow/swipies_25/ragflow/install.sh#L226). This phase has zero dependencies and must be executed immediately before touching build configurations.

1. **Task 0.1:** Revoke PAT `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` in GitHub account security settings.
2. **Task 0.2:** Sanitize [`install.sh`](file:///D:/ragflow/swipies_25/ragflow/install.sh):
   - Replace authenticated `git clone` URL with unauthenticated public image pull workflow (`docker compose pull`).
   - If fallback clone is retained, use public HTTPS repository URL without embedded tokens.
3. **Task 0.3:** Grep codebase for any residual occurrences of `ghp_`, `gho_`, or raw private keys.

---

### Phase 1: Physical Build Separation & Containment (AC-1)
> **Goal:** Ensure the client distribution artifact (`ghcr.io/.../swipies-backend:licence_v`) cannot contain `generate_license.py` or private key materials in any layer.

1. **Task 1.1:** Edit [`Dockerfile`](file:///D:/ragflow/swipies_25/ragflow/Dockerfile#L270):
   - Remove line 270: `COPY generate_license.py ./`.
2. **Task 1.2:** Update [`.dockerignore`](file:///D:/ragflow/swipies_25/ragflow/.dockerignore) and `.gitignore`:
   - Add entries: `generate_license.py`, `internal/licensing/`, `*private*.pem`, `*.key`.
3. **Task 1.3:** Remove `generate_license.py` from the `licence_v` tracking tree (`git rm --cached generate_license.py` or removal).
4. **Task 1.4:** Perform local multi-stage Docker build:
   - Execute `docker build -t test-backend-clean .`
   - Inspect build history with `docker history test-backend-clean` and inspect container filesystem (`docker run --rm test-backend-clean ls -la /ragflow/generate_license.py` $\to$ must return file not found).

> [!IMPORTANT]
> ### 🔒 GATE 1: Build Layer Verification
> **PASS CONDITION:** The file `generate_license.py` is absent from all intermediate and final Docker layers, and `docker history` confirms no `COPY` directive touching licensing generators. Proceed to Phase 2 only when Gate 1 is 100% verified.

---

### Phase 2: Key Pair Generation, Server Placement & Online Verify API (AC-2 & AC-5)
> **Goal:** Mint a fresh RSA-2048 cryptographic key pair and establish authoritative online verification.

1. **Task 2.1 (Offline Generation):**
   - Generate independent RSA-2048 key pair using standard OpenSSL / Cryptography library:
     - $N_{new}$ (2048-bit modulus)
     - $E_{new} = 65537$
     - $D_{new}$ (2048-bit private exponent)
2. **Task 2.2 (Server-Side Isolation):**
   - Package `generate_license.py` (configured with $D_{new}$) exclusively for the closed `swipies.app` server environment.
   - Configure issuance endpoints in `system_api.py` and `license_api.py` to read $D_{new}$ from secure environment variables (`SWIPIES_LICENSE_PRIVATE_KEY`) if running in SaaS mode, without requiring raw script files in repository.
3. **Task 2.3 (Authoritative Online Verify API - AC-5):**
   - Implement `POST /v1/licenses/verify` in `api/apps/restful_apis/system_api.py`:
     - Input: `{"license_key": "<key>"}`
     - Validate signature and query `LicenseKeyService.query(license_key=key)`.
     - Check `is_paid == True`, `status == "active"`, and `expiry_date > NOW()`.
     - Return structured verification result (`{"code": 0, "data": {"valid": True, ...}}`).

> [!IMPORTANT]
> ### 🔒 GATE 2: Closed Server Confirmation
> **PASS CONDITION:** $D_{new}$ is safely deployed only to the closed `swipies.app` environment. Confirmed that zero commits or staged files contain $D_{new}$. Proceed to Phase 3.

---

### Phase 3: Client Verifier Update & Legacy Rejection (AC-2.4, AC-2.5)
> **Goal:** Update the client-side verifier to trust only $N_{new}$ and reject old pirated keys.

1. **Task 3.1:** Update [`api/utils/license_verifier.py`](file:///D:/ragflow/swipies_25/ragflow/api/utils/license_verifier.py):
   - Replace `RSA_N` with $N_{new}$.
   - Set `RSA_E = 65537`.
   - Update `decode_license` to validate payload version (`ver == 2` or legacy graceful rejection).
2. **Task 3.2 (Bypass Removal):**
   - Delete lines 15–19 in [`license_verifier.py`](file:///D:/ragflow/swipies_25/ragflow/api/utils/license_verifier.py#L15-L19) (`if cleaned_key.startswith("SWIPIES-ACT-"): ...`).
   - Delete line 42 in `verify_license_online` (`if license_key.strip().startswith("SWIPIES-ACT-"): return True`).
3. **Task 3.3 (Unit & Security Verification):**
   - Update [`test/unit_test/api/utils/test_license_verifier.py`](file:///D:/ragflow/swipies_25/ragflow/test/unit_test/api/utils/test_license_verifier.py):
     - Test 1: v2 key signed with $D_{new}$ passes offline verification.
     - Test 2: Old key signed with $D_{old}$ is rejected (`recovered_hash != hash_int`).
     - Test 3: `SWIPIES-ACT-` token is rejected.
     - Test 4: Online verification against mock `POST /v1/licenses/verify` returns active status.

> [!IMPORTANT]
> ### 🔒 GATE 3: Rejection & Verification Test
> **PASS CONDITION:** All unit tests pass; mathematical incompatibility confirms 100% of keys generated with $D_{old}$ fail verification on the client. Proceed to Phase 4.

---

### Phase 4: Batch Reissue Workflow for Legitimate Clients (AC-3)
> **Goal:** Automatically generate and deliver new v2 keys to all paying customers without interruption.

1. **Task 4.1 (Audit & Selection Script):**
   - Write migration script `bin/reissue_paid_licenses.py`:
     - Select from `license_key` table where `is_paid = 1` AND `status = 'active'` AND `expiry_date > NOW()`.
2. **Task 4.2 (v2 Key Generation):**
   - For each legitimate customer, generate a v2 key with $D_{new}$ preserving their exact paid `expiry_date` and `duration_months`.
   - Update the database record with the new `license_key`.
3. **Task 4.3 (Customer Delivery & Notification):**
   - Update user portal on `swipies.app` so the user settings page displays the new v2 key.
   - Prepare transactional email notification template explaining the security upgrade with copy-paste instructions for their Self-Hosted server.

---

### Phase 5: Final Security Audit & CI/CD Hardening
1. **Task 5.1:** Run comprehensive test suites across `test_license_verifier.py` and `test_sensitive_data_replacement.py`.
2. **Task 5.2:** Add secret scanning step in `.github/workflows/publish_docker_images.yml` to prevent future token or key commits.

---

## 3. Risk Mitigation & Rollback Strategy

| Scenario | Rollback / Mitigation Plan |
| :--- | :--- |
| **A paying customer is offline and running old code** | Client instances running old image continue running until updated; upon updating, their portal key has already been converted to v2. |
| **Central licensing server times out** | `license_verifier.py` retains local RSA-2048 offline fallback check to ensure 0% disruption to air-gapped systems. |
| **Installer fails due to revoked token** | `install.sh` pulls directly from public GHCR images (`ghcr.io/sardorr555/swipies-backend:licence_v`), requiring no credentials. |

---

## 4. Acceptance Criteria Verification Matrix

| Acceptance Criterion | Verification Method | Pass Condition |
| :--- | :--- | :--- |
| **AC-1: Physical Isolation** | `docker history` & `docker run` inspection | `generate_license.py` not found in image or layers |
| **AC-2: Key Rotation** | Unit test `test_old_key_rejected` | Keys signed with $D_{old}$ fail signature validation |
| **AC-3: Client Reissue** | Database audit & query | 100% of active paid licenses have valid v2 keys |
| **AC-4: Token Revocation** | `curl` with leaked token & repo inspection | GitHub returns 401 Bad Credentials for old PAT |
| **AC-5: Online Verify API** | HTTP test `POST /v1/licenses/verify` | Returns `valid: true` for DB-active keys, `valid: false` for revoked |
