# Security Incident Response Specification: RSA Licensing Key Rotation & Physical Build Isolation

**Feature Key:** `spec_security_rsa_key_rotation_licensing`  
**Security Incident ID:** `SEC-INC-2026-0828-01`  
**Severity:** Critical (CVSS 9.8 - Key Compromise & Token Leakage)  
**Target Modules:** `Dockerfile`, `.dockerignore`, `install.sh`, `api/utils/license_verifier.py`, `api/apps/restful_apis/system_api.py`, `api/apps/restful_apis/license_api.py`, `admin/server/services.py`, `internal/licensing/`  
**Target Branch:** `licence_v`  
**Document Status:** Ready for Review  
**Version:** 1.0.0  
**Specification Owner:** Core Security & Architecture Team  
**Date:** 2026-08-28  

---

## 1. Executive Summary & Incident Statement

### 1.1 Problem Statement
During a technical security audit of the `licence_v` branch, two critical vulnerabilities were identified in the production licensing and installation workflows:

1. **Private RSA Key Compromise (`RSA_D`):**
   - The file `generate_license.py` containing the raw private RSA key `RSA_D` is physically tracked in the git repository across all branches (`licence_v`, `test`, `swipies_26`) and explicitly copied into the public container image via [`Dockerfile:270`](file:///D:/ragflow/swipies_25/ragflow/Dockerfile#L270) (`COPY generate_license.py ./`).
   - Any user deploying the Self-Hosted platform or inspecting the Docker image layers can execute `generate_license.py` to mint arbitrary, perpetual, fully functional offline enterprise licenses without paying.
   - The private key is recorded in git commit history (`883c6c0e3`, `cda3f04e8`), making simple deletion insufficient without a full key rotation.

2. **Plaintext GitHub Personal Access Token (PAT) Leakage:**
   - In [`install.sh:226`](file:///D:/ragflow/swipies_25/ragflow/install.sh#L226), a plaintext GitHub Personal Access Token (`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`) is hardcoded in the public curl installer script, exposing read/clone access to the entire private repository.

3. **Insecure Activation Bypass (`SWIPIES-ACT-`):**
   - [`api/utils/license_verifier.py`](file:///D:/ragflow/swipies_25/ragflow/api/utils/license_verifier.py#L15-L19) contains a plaintext prefix bypass allowing unverified Base64 tokens without mathematical cryptographic signatures.

4. **Missing Authoritative Online Verification Endpoint:**
   - Client instances attempt to verify licenses against `https://api.swipies.io/v1/licenses/verify` ([`license_verifier.py:50`](file:///D:/ragflow/swipies_25/ragflow/api/utils/license_verifier.py#L50)), but this endpoint does not exist on the backend. This causes 100% of online checks to fail open and fall back to the compromised offline RSA signature.

```mermaid
flowchart TD
    subgraph Incident [🚨 Critical Security Vulnerabilities]
        V1["Private RSA_D Key exposed in generate_license.py"]
        V2["generate_license.py baked into public Docker Image"]
        V3["GitHub PAT (ghp_...) hardcoded in install.sh"]
        V4["SWIPIES-ACT- unauthenticated signature bypass"]
        V5["Online endpoint /v1/licenses/verify non-existent"]
    end

    subgraph Remediation [🛡️ Security Remediation Plan]
        R1["AC-1: Physical Build Separation (Clean Dockerfile & .dockerignore)"]
        R2["AC-2: Key Rotation (New RSA-2048, D_new on Server Only, ver=2)"]
        R3["AC-3: Batch Reissue for Legitimate Paid Clients"]
        R4["AC-4: Token Revocation & install.sh Sanitization"]
        R5["AC-5: Authoritative Online Verification API (POST /v1/licenses/verify)"]
    end

    Incident --> Remediation
```

---

## 2. Scope & Architectural Boundaries

```mermaid
flowchart LR
    subgraph InScope [✅ IN SCOPE - Security Incident Response]
        S1["Remove COPY generate_license.py from Dockerfile"]
        S2["Add generate_license.py to .dockerignore & .gitignore"]
        S3["Generate independent RSA-2048 key pair (N_new, E_new, D_new)"]
        S4["Update license_verifier.py to N_new / E_new and ver=2 schema"]
        S5["Remove SWIPIES-ACT- bypass in license_verifier.py"]
        S6["Revoke leaked GitHub PAT and clean install.sh fallback"]
        S7["Implement POST /v1/licenses/verify endpoint in backend"]
        S8["Batch reissue migration script for active paid licenses"]
    end

    subgraph OutOfScope [❌ OUT OF SCOPE - Tracked Separately]
        O1["Fixing limit_license() 402 trial gate in api/apps/__init__.py"]
        O2["Performance caching for check_license()"]
        O3["Atmos payment gateway enhancements"]
        O4["Sensitive Data Replacement (already completed)"]
    end
```

---

## 3. Detailed Technical Requirements & Acceptance Criteria

### 3.1 AC-1: Physical Build Isolation (Containment)
- **AC-1.1:** The directive `COPY generate_license.py ./` is completely removed from [`Dockerfile`](file:///D:/ragflow/swipies_25/ragflow/Dockerfile).
- **AC-1.2:** `generate_license.py` and `internal/licensing/` are explicitly added to [`.dockerignore`](file:///D:/ragflow/swipies_25/ragflow/.dockerignore) and `.gitignore` in `licence_v`.
- **AC-1.3:** Multi-stage build inspection: The final published container image (`ghcr.io/sardorr555/swipies-backend:licence_v`) must contain zero occurrences of `generate_license.py` or private key materials across **all intermediate and final layers**.
- **AC-1.4:** The client-side [`api/utils/license_verifier.py`](file:///D:/ragflow/swipies_25/ragflow/api/utils/license_verifier.py) continues to operate autonomously using only the public modulus $N_{new}$ and exponent $E_{new}$.
- **AC-1.5:** The internal SaaS deployment (`swipies.app`) maintains access to the generator via server-side configuration/environment, ensuring issuance via Atmos payment callbacks remains local and fast.

### 3.2 AC-2: Cryptographic RSA-2048 Key Pair Rotation & Schema Versioning
- **AC-2.1:** An independent, cryptographically secure 2048-bit RSA key pair is generated ($N_{new}, E_{new} = 65537, D_{new}$).
- **AC-2.2:** The private key $D_{new}$ is stored **strictly** on the secure licensing server (`swipies.app`) and is **never** committed to any public or client-facing repository.
- **AC-2.3 (License Payload v2 Schema):** The payload format is updated to include an explicit version tag:
  ```json
  {
    "ver": 2,
    "owner": "client@company.com",
    "expiry": "YYYY-MM-DD",
    "type": "yearly"
  }
  ```
- **AC-2.4 (Rejection of Old Compromised Keys):** 
  - Client-side [`license_verifier.py`](file:///D:/ragflow/swipies_25/ragflow/api/utils/license_verifier.py) is updated with $N_{new}$.
  - Any license signed with the old compromised private key $D_{old}$ mathematically fails verification ($\text{sig}^{E_{new}} \not\equiv \text{hash} \pmod{N_{new}}$) and is rejected with `"Invalid license signature."`.
- **AC-2.5 (Bypass Elimination):** The `SWIPIES-ACT-` unauthenticated bypass branch in `decode_license()` and `verify_license_online()` is removed.

### 3.3 AC-3: Batch Reissue Workflow for Legitimate Paid Clients
- **AC-3.1:** An automated migration script queries the central `license_key` database for all records satisfying:
  $$\text{is\_paid} = \text{True} \quad \land \quad \text{status} = \text{"active"} \quad \land \quad \text{expiry\_date} > \text{NOW}()$$
- **AC-3.2:** For every legitimate record, a new v2 license key is generated using $D_{new}$, preserving the exact original expiration date and duration months without requiring re-payment.
- **AC-3.3:** The central database record is updated with `license_key = key_v2`.
- **AC-3.4:** The user profile API (`/v1/license`) and user portal on `swipies.app` immediately present the reissued v2 key to the customer.

### 3.4 AC-4: Repository Sanitization & Token Revocation
- **AC-4.1:** The leaked token `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` is immediately revoked in GitHub Developer Settings.
- **AC-4.2:** [`install.sh`](file:///D:/ragflow/swipies_25/ragflow/install.sh) is sanitized:
  - Remove all embedded GitHub PAT credentials.
  - Standardize on `docker compose pull` of public images; if fallback repository cloning is used, ensure it clones public/non-authenticated URLs without embedded secrets.
- **AC-4.3:** Thorough grep/trufflehog audit confirming zero remaining plain secrets in `install.sh`, `docker-compose.yml`, and `Dockerfile`.

### 3.5 AC-5: Authoritative Online Verification API
- **AC-5.1:** Implement a public-facing authoritative verification endpoint on `swipies.app`:
  - **Route:** `POST /v1/licenses/verify`
  - **Request Body:** `{"license_key": "<key_string>"}`
  - **Verification Logic:**
    1. Decode license payload (`decode_license`).
    2. Lookup `license_key` in database `license_key` table.
    3. Verify `is_paid == True`, `status == "active"`, and `expiry_date > NOW()`.
    4. Return `{"code": 0, "valid": true, "expiry": "YYYY-MM-DD", "type": "yearly"}` if valid (zero PII/owner exposed), or `{"code": 102, "valid": false, "reason": "license_invalid"}` if refunded, invalid, or expired.
- **AC-5.2 (Instant Revocation Support):** Provides instant revocation capability for refunds/chargebacks without waiting for offline cryptographic token expiry.
- **AC-5.3 (Offline Fallback Continuity):** If a client instance is completely air-gapped or network connectivity to `api.swipies.io` fails, the client seamlessly falls back to local RSA-2048 offline signature verification.

---

## 4. Architecture & Data Flow

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Self-Hosted Admin
    participant ClientInstance as Client RAGFlow Instance
    participant Verifier as license_verifier.py (Client)
    participant CentralAuth as swipies.app (/v1/licenses/verify)
    participant BillingDB as Central License DB

    Note over Customer,ClientInstance: License Key Activation (v2)
    Customer->>ClientInstance: Input License Key (v2)
    ClientInstance->>Verifier: check_license(key)
    
    Verifier->>Verifier: 1. Decode & Verify RSA-2048 with N_new
    alt Invalid RSA Signature (e.g. minted with old D_old)
        Verifier-->>ClientInstance: Return (False, "Invalid license signature.")
    else Valid RSA-2048 Signature
        Verifier->>CentralAuth: 2. POST /v1/licenses/verify {"license_key": key}
        alt Online Check Successful (200 OK)
            CentralAuth->>BillingDB: Query status & is_paid
            BillingDB-->>CentralAuth: status="active", is_paid=True
            CentralAuth-->>Verifier: {"valid": true}
            Verifier-->>ClientInstance: Return (True, "License active.")
        else Central Server Unreachable / Timeout (3s)
            Verifier-->>ClientInstance: Return (True, "License active (Offline RSA verified).")
        else License Revoked in DB (Refund / Chargeback)
            CentralAuth-->>Verifier: {"valid": false, "reason": "revoked"}
            Verifier-->>ClientInstance: Return (False, "License revoked by server.")
        end
    end
```

---

## 5. Security & Risk Analysis

| Risk ID | Risk Description | Severity | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **SEC-R1** | Old pirated licenses continue working after patch | Critical | Mathematical key rotation ($N_{new} \neq N_{old}$); old signatures will not verify under $N_{new}$. |
| **SEC-R2** | Private key leaked again in future builds | High | Remove from Dockerfile, enforce `.dockerignore`, and store $D_{new}$ strictly as server environment variable. |
| **SEC-R3** | Legitimate paying customers locked out upon update | High | AC-3 automated batch reissue preserving original expiration dates and notifying customers via email/portal. |
| **SEC-R4** | Revoked leaked GitHub token breaks client installer | Medium | Sanitize `install.sh` fallback to avoid relying on private token clone; pull public GHCR images directly. |
| **SEC-R5** | Air-gapped enterprise client fails online check | Low | Graceful fallback in `license_verifier.py` to local RSA signature if central server times out. |

---

## 6. Verification & Gated Acceptance Checklist

- [ ] **G-1 (Build Hygiene):** `Dockerfile` does not contain `COPY generate_license.py ./`.
- [ ] **G-2 (Ignore Verification):** `generate_license.py` is present in `.dockerignore` and `.gitignore`.
- [ ] **G-3 (Image Layer Audit):** `docker history` and `dive` on the built client image confirm zero trace of `generate_license.py`.
- [ ] **G-4 (Key Pair Verification):** New $N_{new}, E_{new}$ embedded in `license_verifier.py`; $D_{new}$ kept outside client repository.
- [ ] **G-5 (Old Key Rejection Test):** Unit test verifies that any license key generated with old $D_{old}$ returns `is_valid = False` with `"Invalid license signature."`.
- [ ] **G-6 (v2 Key Acceptance Test):** Unit test verifies that a v2 key generated with $D_{new}$ passes offline verification cleanly.
- [ ] **G-7 (Bypass Removal Test):** Unit test verifies that `"SWIPIES-ACT-..."` string fails signature check.
- [ ] **G-8 (Online Verify Endpoint Test):** `POST /v1/licenses/verify` returns `{"valid": true}` for active paid keys and `{"valid": false}` for revoked keys.
- [ ] **G-9 (Leaked Token Revocation):** Leaked GitHub PAT `ghp_...` is revoked; `install.sh` contains zero secrets.
- [ ] **G-10 (Batch Reissue Script):** Migration script executes cleanly against database, updating active paid licenses to v2 keys.
