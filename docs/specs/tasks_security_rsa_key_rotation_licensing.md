# Tasks: RSA Key Rotation & Licensing Security Incident Remediation

**Tasks Key:** `tasks_security_rsa_key_rotation_licensing`  
**Parent Plan:** [`plan_security_rsa_key_rotation_licensing`](file:///D:/ragflow/swipies_25/ragflow/docs/specs/plan_security_rsa_key_rotation_licensing.md)  
**Parent Spec:** [`spec_security_rsa_key_rotation_licensing`](file:///D:/ragflow/swipies_25/ragflow/docs/specs/spec_security_rsa_key_rotation_licensing.md)  
**Target Branch:** `licence_v`  
**Security Incident ID:** `SEC-INC-2026-0828-01`  
**Document Status:** Ready for Implementation  
**Version:** 1.0.0  
**Date:** 2026-08-28  

---

## Task Dependency & Gated Execution Checklist

```mermaid
flowchart TD
    T01["TASK-01: Revoke Leaked PAT & Sanitize install.sh (Phase 0)"] --> T02["TASK-02: Clean Dockerfile & Update Ignore Rules (Phase 1)"]
    T02 --> T03["TASK-03: Remove Generator from Tree & Verify Layers (Phase 1)"]
    T03 --> G1{{"🔒 GATE 1: Build Layer Verification"}}
    G1 --> T04["TASK-04: Generate RSA-2048 Key Pair (Phase 2)"]
    T04 --> T05["TASK-05: Implement POST /v1/licenses/verify API (Phase 2)"]
    T05 --> G2{{"🔒 GATE 2: Closed Server Confirmation"}}
    G2 --> T06["TASK-06: Update license_verifier.py to N_new & Remove SWIPIES-ACT- (Phase 3)"]
    T06 --> T07["TASK-07: Implement Security Test Suite & Rejection Verification (Phase 3)"]
    T07 --> G3{{"🔒 GATE 3: Rejection & Verification Test"}}
    G3 --> T08["TASK-08: Batch License Reissue Script for Paid Clients (Phase 4)"]
    T08 --> T09["TASK-09: Final Full Audit, CI/CD Hardening & Verification (Phase 5)"]
```

---

## Detailed Task Breakdown

### ⚡ Phase 0: Immediate Emergency Action (AC-4)

- [x] **TASK-01 (Emergency PAT Sanitization & `install.sh` Hardening):**
  - **Files:** [`install.sh`](file:///D:/ragflow/swipies_25/ragflow/install.sh), [`new site for swipies/install.sh`](file:///D:/ragflow/swipies_25/ragflow/new%20site%20for%20swipies/install.sh), [`copy_secrets.py`](file:///D:/ragflow/swipies_25/ragflow/copy_secrets.py), [`.github/workflows/deploy_main.yml`](file:///D:/ragflow/swipies_25/ragflow/.github/workflows/deploy_main.yml), [`.github/workflows/deploy_new_server.yml`](file:///D:/ragflow/swipies_25/ragflow/.github/workflows/deploy_new_server.yml)
  - **Objective:** Remove plaintext token `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` from all deployment workflows and helper scripts.
  - **Actions:**
    1. Sanitize fallback clone in `install.sh` and `new site for swipies/install.sh` to use pure `docker compose pull`.
    2. Sanitize `copy_secrets.py` to read `GITHUB_TOKEN` from environment instead of hardcoded plaintext string.
    3. Sanitize `.github/workflows/deploy_new_server.yml` and `.github/workflows/deploy_main.yml` to use `${{ secrets.GITHUB_TOKEN }}`.
    4. Grep entire repository for any residual occurrences of `ghp_`, `gho_`, or raw private keys.
    5. Document manual action requirement for owner to click "Revoke" in GitHub Developer Settings.

---

### 📦 Phase 1: Physical Build Separation & Containment (AC-1)

- [x] **TASK-02 (Dockerfile & `.dockerignore` Cleaning):**
  - **Files:** [`Dockerfile`](file:///D:/ragflow/swipies_25/ragflow/Dockerfile), [`.dockerignore`](file:///D:/ragflow/swipies_25/ragflow/.dockerignore), `.gitignore`
  - **Objective:** Prevent `generate_license.py` from ever entering any Docker build context.
  - **Actions:**
    1. Remove line 270 (`COPY generate_license.py ./`) from [`Dockerfile`](file:///D:/ragflow/swipies_25/ragflow/Dockerfile).
    2. Add `generate_license.py`, `internal/licensing/`, `*private*.pem`, and `*.key` to [`.dockerignore`](file:///D:/ragflow/swipies_25/ragflow/.dockerignore) and `.gitignore`.

- [x] **TASK-03 (Repository Tree Sanitization & Gate 1 Verification):**
  - **Files:** `generate_license.py`, `Dockerfile`
  - **Objective:** Remove `generate_license.py` from client repository tree and verify image layer hygiene.
  - **Actions:**
    1. Remove `generate_license.py` from the `licence_v` tracking tree.
    2. Verify that `git status` shows no generator files tracked for client distribution.
    3. **GATE 1 CHECKPOINT:** Verify build instructions confirm zero trace of generator in client artifacts.

---

### 🔑 Phase 2: Key Pair Generation, Server Placement & Online Verify API (AC-2 & AC-5)

- [x] **TASK-04 (RSA-2048 Key Pair Generation & Server Script Packaging):**
  - **Files:** `server_generate_license.py` (for closed server use only)
  - **Objective:** Generate an independent, cryptographically secure RSA-2048 key pair ($N_{new}, E_{new} = 65537, D_{new}$) and prepare isolated server issuance script.
  - **Actions:**
    1. Generate RSA-2048 key pair using OpenSSL / standard Cryptography module.
    2. Format $D_{new}$ for storage strictly on `swipies.app` server environment (`SWIPIES_LICENSE_PRIVATE_KEY`).
    3. Ensure $D_{new}$ is NEVER committed to git or stored in client workspace.

- [x] **TASK-05 (Authoritative Online Verification API):**
  - **Files:** [`api/apps/restful_apis/system_api.py`](file:///D:/ragflow/swipies_25/ragflow/api/apps/restful_apis/system_api.py), [`api/apps/backward_compat.py`](file:///D:/ragflow/swipies_25/ragflow/api/apps/backward_compat.py), [`api/apps/__init__.py`](file:///D:/ragflow/swipies_25/ragflow/api/apps/__init__.py), [`docker/nginx/proxy.conf`](file:///D:/ragflow/swipies_25/ragflow/docker/nginx/proxy.conf)
  - **Objective:** Implement `POST /v1/licenses/verify` on the backend to verify active licenses against the database.
  - **Actions:**
    1. Add route `@manager.route("/licenses/verify", methods=["POST"])` with rate limiting and timing equalization.
    2. Add route to `allowed_prefixes` in `api/apps/__init__.py` to prevent 402 block.
    3. Add backward compatibility route alias in `api/apps/backward_compat.py`.
    4. Parse `license_key`, decode payload, query `LicenseKeyService.query(license_key=key)`.
    5. Check `is_paid == True`, `status == "active"`, and `expiry_date > NOW()`.
    6. Return `{"code": 0, "valid": true, "expiry": ...}` or `{"code": 102, "valid": false, "reason": "license_invalid"}`.
    7. **GATE 2 CHECKPOINT:** Confirm $D_{new}$ is securely stored only on the server.
       - *Known limitation & mitigation:* Reverse proxy client IP resolution prioritizes `X-Real-IP` and rightmost `X-Forwarded-For`. Production edge ingress must overwrite `X-Real-IP` with `$remote_addr` to prevent spoofing.

---

### 🛡️ Phase 3: Client Verifier Update & Legacy Rejection (AC-2.4 & AC-2.5)

- [x] **TASK-06 (Client `license_verifier.py` Update & Bypass Removal):**
  - **Files:** [`api/utils/license_verifier.py`](file:///D:/ragflow/swipies_25/ragflow/api/utils/license_verifier.py)
  - **Objective:** Embed $N_{new}$ in the client verifier and eliminate unauthenticated bypasses.
  - **Actions:**
    1. Update `RSA_N` to $N_{new}$ and `RSA_E = 65537`.
    2. Add payload version check (`ver == 2`).
    3. Remove `SWIPIES-ACT-` bypass branches from `decode_license` and `verify_license_online`.

- [x] **TASK-07 (Security Unit Testing & Legacy Key Rejection Test):**
  - **Files:** [`test/unit_test/api/utils/test_license_verifier.py`](file:///D:/ragflow/swipies_25/ragflow/test/unit_test/api/utils/test_license_verifier.py)
  - **Objective:** Verify mathematically and programmatically that old keys fail and v2 keys pass.
  - **Actions:**
    1. Write test: Key generated with old $D_{old}$ fails verification with `"Invalid license signature."`.
    2. Write test: v2 Key generated with $D_{new}$ passes offline verification.
    3. Write test: `SWIPIES-ACT-` token is rejected.
    4. Write test: Online verify endpoint returns expected valid/revoked payloads.
    5. **GATE 3 CHECKPOINT:** 100% test pass rate (5/5 passed) confirming mathematical rejection of pirated keys.

---

### 🚚 Phase 4: Batch Reissue Workflow for Legitimate Clients (AC-3)

- [x] **TASK-08 (Batch License Reissue Migration Script):**
  - **Files:** [`bin/reissue_paid_licenses.py`](file:///D:/ragflow/swipies_25/ragflow/bin/reissue_paid_licenses.py)
  - **Objective:** Reissue v2 license keys to all verified paying customers preserving their original expiration dates.
  - **Actions:**
    1. Query `license_key` table for `is_paid = 1` AND `status = 'active'` AND `expiry_date > NOW()`.
    2. Generate v2 keys with $D_{new}$ for each customer.
    3. Update database records with the new `license_key` within `DB.atomic()` transactions.
    4. Prepare email notification template and portal display confirmation.
    5. Tested with `--dry-run` and idempotence protection.
    6. **Mandatory Production Backup Step:** Take MySQL table backup before `--execute`:
       `docker exec -i swipies-mysql mysqldump -uroot -p"${MYSQL_PASSWORD}" rag_flow license_key > /backup/license_key_pre_migration_$(date +%Y%m%d_%H%M%S).sql`

---

### 🧪 Phase 5: Final Security Audit & Verification (AC-4.3)

- [x] **TASK-09 (Full System Verification & CI/CD Hardening):**
  - **Files:** [`.github/workflows/publish_docker_images.yml`](file:///D:/ragflow/swipies_25/ragflow/.github/workflows/publish_docker_images.yml), documentation
  - **Objective:** Ensure end-to-end green tests, zero secrets in working tree, and record production operational considerations.
  - **Actions:**
    1. Run `python test/test_sensitive_data_replacement.py` (12/12 passed) and `pytest test/unit_test/api/utils/test_license_verifier.py` (6/6 passed).
    2. Verify `git status --short` and `git diff --stat`.
    3. Document final status in `docs/specs/`.
    4. **Operational Follow-up Note 1 (Multi-worker Rate Limiting):** In-memory fallback rate limit (`_IN_MEMORY_RATE_LIMITS`) is process-isolated; during Redis outage, effective limit scales to $N_{\text{workers}} \times \text{limit}$. Redis high-availability sentinel/cluster is recommended for strict centralized quota.
    5. **Operational Follow-up Note 2 (Air-gapped Continuity vs Revocation):** Fail-open при недоступности licensing-сервера обеспечивает непрерывность работы air-gapped клиентов до жесткой даты `expiry` в RSA-токене. Для принудительного отзыва умышленно заблокировавших сеть клиентов рекомендуется в будущем внедрить grace period (например, требование успешного phone-home не реже 1 раза в 14 дней).
