---
sidebar_position: 8
slug: /license_activation
title: Self-Hosted & Enterprise License
---

# Self-Hosted & Enterprise License Guide

Swipies AI provides an **Enterprise Self-Hosted (On-Premise)** deployment option designed for organizations that require complete data sovereignty, air-gapped security, and dedicated infrastructure. 

This guide walks you through acquiring, downloading, deploying, and activating your Swipies AI commercial license.

---

## 1. Cloud SaaS vs. Self-Hosted Enterprise

| Feature | Cloud SaaS (`swipies.app`) | Self-Hosted Enterprise |
| :--- | :--- | :--- |
| **Hosting Environment** | Managed Swipies Cloud Infrastructure | Your Private Server / Cloud (AWS, Azure, Bare-metal) |
| **Data Privacy** | Encrypted multi-tenant Cloud | 100% Isolated inside your corporate network |
| **Offline Air-Gap Support** | No (Requires Internet) | **Yes (Full Air-Gap mode supported)** |
| **Document Capacity** | Tier-based monthly limits | **Unlimited documents and chunk storage** |
| **Local LLM / SLM Support** | Cloud APIs only | **Ollama, vLLM, Local HuggingFace, Custom APIs** |
| **Support & SLA** | Community / Ticket Support | **Dedicated Priority SLA & Direct Engineering Channel** |

---

## 2. Acquiring Your Commercial License Key

You can obtain a cryptographically signed license key directly through the Swipies AI customer portal:

1. Log in to [https://swipies.app](https://swipies.app).
2. Click your user avatar in the bottom-left corner and select **User Settings**.
3. In the navigation sidebar, select **License** (or navigate directly to `/user-setting/license`).
4. Choose your desired licensing period:
   - **Pilot / 6 Months**: Ideal for evaluation, pilot projects, and single-server deployments.
   - **Annual / 12 Months (Best Value)**: Includes 2 bonus months free, priority SLA, and guaranteed forward upgrade compatibility.
5. Complete payment using Visa, MasterCard, or corporate billing.
6. Once processed, your license key is generated immediately:
   - Click **Copy Key** to copy the full cryptographic string to your clipboard.
   - Click **Download (.key)** to save the license certificate file locally.
   - (Optional) Use the **Rename** action to tag the key with your destination server name (e.g. `prod-server-us-east`).

---

## 3. Server Requirements & Prerequisites

Before deploying the self-hosted instance, ensure your host server meets the following requirements:

### Hardware Specifications
* **CPU**: Minimum 8 vCPUs (16+ vCPUs recommended for production with local reranker/embedding models).
* **RAM**: Minimum 16 GB (32 GB+ recommended).
* **Storage**: Minimum 100 GB SSD NVMe available disk space.
* **OS**: Ubuntu 22.04 LTS or 24.04 LTS (x86_64 or ARM64).
* **Network**: Ports `80`, `443`, and `9380` open in firewall/security groups.

### Software Dependencies
Ensure Docker Engine and Docker Compose are installed:

```bash
# Verify Docker installation
docker --version
docker compose version
```

If Docker is not yet installed:
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

---

## 4. Downloading and Deploying Swipies AI to Your Server

### Step 4.1: Clone the Official Repository

Clone the Swipies AI repository to your server's application directory:

```bash
# Clone the repository
git clone https://github.com/Sardorr555/swipies__ai_.git /opt/swipies
cd /opt/swipies
```

### Step 4.2: Configure Environment Variables

Navigate to the `docker` directory and configure the environment:

```bash
cd /opt/swipies/docker

# Copy example environment configuration
cp .env.example .env
```

Edit `.env` using your preferred text editor (e.g., `nano .env`):
* Set your domain or public server IP.
* Configure database and Redis passwords if customizing default credentials.
* (Optional) Specify `SWPIES_LICENSE_KEY` for zero-touch automatic activation (see Section 5 below).

### Step 4.3: Launch the Services

Start all core microservices (RAG backend, Web UI, MySQL, Elasticsearch/Infinity, Redis, MinIO) in detached mode:

```bash
# Start containers
docker compose up -d

# Verify all services are running healthy
docker compose ps
```

To monitor real-time startup logs:
```bash
docker compose logs -f swipies
```

Once the containers are up, access the Web UI at:
```
http://<YOUR_SERVER_IP_OR_DOMAIN>
```

---

## 5. Activating Your License on the Server

Swipies AI provides three flexible methods to activate your license:

### Method A: Interactive Web UI (Recommended)

1. Open your browser and navigate to `http://<YOUR_SERVER_IP>`.
2. Log in with administrator credentials (default or initial created superuser).
3. Open **User Settings** (click your profile icon) and navigate to the **License** section.
4. If a license prompt modal appears (or click **Activate License**), paste your full cryptographic license key into the text area.
5. Click **Activate License**.
6. The system validates the digital signature. Upon success:
   - A confirmation banner displays **"License Activated Successfully!"**.
   - Your license tier, owner name, and exact expiration date are shown.
   - The UI automatically reloads with all Enterprise capabilities enabled.

### Method B: Automated REST API (CI/CD & Headless)

For programmatic provisioning or automation scripts, activate the license via the internal REST API:

```bash
curl -X POST "http://127.0.0.1:9380/v1/system/license" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ADMIN_ACCESS_TOKEN>" \
  -d '{
    "license_key": "YOUR_FULL_CRYPTOGRAPHIC_LICENSE_KEY_STRING"
  }'
```

**Expected Response (`200 OK`):**
```json
{
  "code": 0,
  "data": {
    "is_valid": true,
    "message": "License activated successfully. 365 days remaining until 2027-09-15.",
    "payload": {
      "owner": "Acme Corporation",
      "type": "yearly",
      "expiry": "2027-09-15"
    }
  }
}
```

### Method C: Zero-Touch Pre-Activation via Environment Variable

If deploying via automated infrastructure (Terraform, Ansible, Cloud-Init, or Kubernetes Helm):
1. Add the license key to `docker/.env`:
   ```env
   SWPIES_LICENSE_KEY=YOUR_FULL_CRYPTOGRAPHIC_LICENSE_KEY_STRING
   ```
2. On initial startup, the Swipies AI engine automatically decodes and provisions the license key into system configuration without requiring manual UI interaction.

---

## 6. Monitoring and Renewing Licenses

### Checking Expiration and Status
* In **User Settings -> License**, view the live status indicator:
  - **Active**: License is valid and in effect.
  - **Days Left Counter**: Real-time expiration bar showing elapsed vs. remaining subscription time.
  - **Transaction Reference**: Associated order or payment ID for accounting records.

### License Key Renewal
* To renew an expiring license, generate a new key on [https://swipies.app](https://swipies.app).
* Paste the new key into the license settings modal. The system updates the expiration date dynamically without interrupting running tasks, ongoing user chats, or requiring container restarts.

---

## 7. Frequently Asked Questions (FAQ)

#### Q: Can Swipies AI run without an internet connection (Air-Gapped)?
**Yes.** The cryptographic validation engine uses local asymmetric key verification. Once activated, the self-hosted instance requires zero external internet connectivity to operate.

#### Q: What happens when the license expires?
When a license reaches its expiration date, administrative access remains available so you can input a renewed key. Read-only query operations continue, while new document batch parsing is paused until renewal.

#### Q: Where is the license stored on the host?
The license key is securely saved in the system configuration database (`system_settings` table under key `license.key`). Your license persists across container updates, reboots, and upgrades.
