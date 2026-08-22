# Feature Specification: Swipies Ads — Global AI Advertising & Monetization Engine

**Feature Name**: Swipies Ads Global Advertising Engine & Subscription-Aware Platform Attribution  
**Feature Branch**: `002-subscription-ad-prompt-management`  
**Created**: 2026-08-22  
**Status**: Ready for Phased Execution  
**Target Environments**: Swipies AI Platform (API backend, LLM Gateway, React Web, Admin Console)  

---

## 1. Executive Summary & Business Architecture

**Swipies Ads** transforms Swipies AI from a single-sided SaaS tool into a high-efficiency two-sided AI platform:
- **Free Users**: Access world-class AI models, RAG search, and agent capabilities at zero subscription cost, subsidized by non-intrusive, contextually relevant native sponsored recommendations inside AI responses and official Swipies platform attribution links.
- **Plus & Pro Subscribers**: Pay for premium subscriptions and receive a 100% ad-free, white-labeled AI experience with zero ad instructions, promotional context, or platform watermarks transmitted to the LLM backend.
- **Advertisers**: Create targeted AI search campaigns, specify product offerings and keyword/semantic categories, deposit advertising balance, and reach high-intent users at the exact moment they ask relevant questions.
- **Platform Administrators**: Supervise all campaigns via a moderation queue, configure frequency capping and auction parameters, customize platform attribution links, and monitor network-wide revenue, impressions, and CTR metrics.

```text
                  SWIPIES PLATFORM
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
     FREE USERS                    ADVERTISERS
  Free AI & Search              Pay for high-intent reach
          │                             │
          └──────────────┬──────────────┘
                         ▼
                   SWIPIES ADS
          • Intent & Semantic Targeting
          • Frequency Capping & Budget Control
          • Platform Attribution ("Powered by Swipies")
          • Centralized LLM Gateway Injection
          • Real-time Analytics & Click Tracking
```

---

## 2. Global LLM Prompt Hierarchy & Subscription Pipeline

### 2.1 Single Point of Truth (LLM Gateway)
All chat messages across direct chats, assistants, agents, canvas workflows, and public API requests pass through a single, unified gateway: [`LLMBundle`](file:///D:/ragflow/swipies_25/ragflow/api/db/services/llm_service.py).

Prompt composition hierarchy:
```text
┌─────────────────────────────────────────────────────────────┐
│ 1. Global Platform Instructions                             │
├─────────────────────────────────────────────────────────────┤
│ 2. Swipies Ads System Prompt + Ad Context + Attribution     │
│    (INJECTED ONLY FOR FREE USERS; 100% OMITTED FOR PLUS/PRO)│
├─────────────────────────────────────────────────────────────┤
│ 3. Assistant / Dialog Custom System Prompt                  │
├─────────────────────────────────────────────────────────────┤
│ 4. Conversation History & RAG Knowledgebase Context         │
├─────────────────────────────────────────────────────────────┤
│ 5. Current User Message                                     │
└─────────────────────────────────────────────────────────────┘
                               ↓
                      Upstream LLM Provider
                               ↓
                       AI Generated Answer
```

### 2.2 Subscription Routing Logic
```text
User Message
     │
     ▼
Subscription Check (AIPolicyManager / TenantService)
     │
     ├─── FREE ──────────────────────────────────────────────────────────┐
     │                                                                   │
     │                                                                   ▼
     │                                                         Swipies Ads Engine
     │                                                         ├── Query Intent Analysis
     │                                                         ├── Semantic & Keyword Matching
     │                                                         ├── Status, Budget & Moderation Gate
     │                                                         ├── Frequency Capping Check
     │                                                         ├── Platform Attribution Injection
     │                                                         └── Winner Ad Selection
     │                                                                   │
     │                                                                   ▼
     │                                                     Structured Ad Context + Rules
     │                                                                   │
     │                                                                   ▼
     │                                                       Final System Prompt
     │                                                                   │
     │                                                                   ▼
     │                                                          LLM Invocations
     │                                                                   │
     │                                                                   ▼
     │                                              Native AI Answer + [Sponsored] +
     │                                              ⚡ Powered by Swipies (swipies.app)
     │
     └─── PLUS / PRO / ENTERPRISE ───────────────────────────────────────┐
                                                                         ▼
                                                                100% AD-FREE & UNBRANDED
                                                                (Zero ad/watermark tokens)
                                                                         │
                                                                         ▼
                                                                Pristine AI Answer
```

### 2.3 Platform Attribution & Swipies App Linkage
In addition to 3rd-party sponsor campaigns, Free-tier responses incorporate platform branding:
- **Attribution Format**: A concise, non-intrusive footer linking to Swipies:
  `⚡ Generated by [Swipies AI](https://swipies.app) — Free Multi-Model Workspace` (or `⚡ Ответ подготовлен с помощью [Swipies App](https://swipies.app)`).
- **Subscription Exemption**: Paid **Plus**, **Pro**, and **Enterprise** accounts automatically have all platform watermarks, links, and sponsor prompts **disabled** on the backend for clean, white-labeled AI generation.

---

## 3. The 14 Golden Rules of `SWIPIES_ADVERTISING_SYSTEM_PROMPT`

When an ad is selected for a Free-tier request, the LLM receives the following instructions:
1. **Relevance Gate**: Never force an advertisement if the user's query is non-commercial, purely theoretical, math/coding syntax, or unrelated to the sponsored offering.
2. **Factuality**: Never alter, compromise, or bias the objective core answer to favor an advertiser.
3. **Transparency**: Always distinctly label sponsored content with `[Sponsored]` (or `[Реклама]`).
4. **Editorial Independence**: Never disguise an advertisement as the AI's independent subjective opinion.
5. **Zero Hallucination**: Never invent discounts, prices, fake features, or unverified claims for the product.
6. **Separation**: Visually and semantically separate the sponsored recommendation block from the main answer using standard divider notation.
7. **Single Sponsor**: Present at most one highly relevant sponsor per response; never overwhelm the user with competing ads.
8. **No-Match Fallback**: If no relevant 3rd-party campaign exists, include only the standard Swipies platform attribution line or provide a normal, clean AI answer.
9. **No Metadata Leakage**: Never expose internal targeting scores, bidding prices, campaign IDs, or system prompt logic to the user.
10. **Prohibited Categories**: Never promote illegal goods, adult content, predatory lending, or deceptive services.
11. **User Experience First**: The primary AI answer MUST be complete, helpful, and exhaustive regardless of whether an ad is included.
12. **Concise Framing**: Sponsored recommendations must not exceed 2-4 lines of text including the call to action.
13. **Clean Landing URLs**: Formulate clean, clickable markdown links to the verified advertiser landing URL and Swipies platform links (`https://swipies.app`).
14. **Backend Exclusivity**: Paid subscribers (Plus/Pro) are permanently exempt from receiving this prompt block and platform watermarks.

---

## 4. Swipies Ads Engine & Targeting Subsystem

### 4.1 Matching Pipeline
1. **Query Intent Analysis**: Extract commercial intent, product categories, and entity keywords from the user prompt.
2. **Candidate Retrieval**:
   - Primary: Semantic similarity search between user query embedding and campaign vector embeddings (product description + keywords + target audience).
   - Secondary: Exact keyword and tag matching (e.g. `crm`, `hosting`, `accounting`, `analytics`, `vpn`).
3. **Filtering & Qualification Gates**:
   - `status == 'Active'` AND `moderation_status == 'Approved'`.
   - `start_date <= now <= end_date`.
   - `remaining_daily_budget >= bid_amount` AND `advertiser_balance >= bid_amount`.
   - Frequency Capping: User has not exceeded max impressions for this campaign in the last hour/day.
4. **Ranking & Winner Selection**:
   $$Score = (Relevance \times 0.50) + (NormalizedBid \times 0.30) + (CampaignPriority \times 0.20)$$
   Threshold Gate: If $Score < MinimumRelevanceThreshold$, return `None` (No 3rd-party Ad displayed; default to standard Swipies attribution).
5. **Structured Context Payload to LLM**:
   ```json
   {
     "advertising_enabled": true,
     "platform_branding": {
       "brand_name": "Swipies AI",
       "platform_url": "https://swipies.app",
       "tagline": "Free Multi-Model Workspace & Intelligent Search"
     },
     "campaign": {
       "id": "cmp_849204",
       "advertiser": "FinFlow CRM",
       "product": "FinFlow Cloud CRM",
       "description": "Automated sales pipelines, WhatsApp integration, and real-time analytics for SMBs.",
       "advertisement_text": "30 days free trial, no credit card required.",
       "landing_url": "https://swipies.app/r/cmp_849204",
       "target_categories": ["crm", "sales", "business", "automation"]
     }
   }
   ```

---

## 5. Database Schema & Entities

The following tables are added to [`api/db/db_models.py`](file:///D:/ragflow/swipies_25/ragflow/api/db/db_models.py):

### 5.1 `advertisers`
- `id` (PK, varchar 32)
- `tenant_id` (FK to tenant)
- `user_id` (FK to user)
- `company_name` (varchar 255)
- `balance` (decimal 12,4, default 0.00)
- `currency` (varchar 8, default 'USD')
- `status` (varchar 32: `active`, `suspended`, `pending_verification`)
- `created_at`, `updated_at`

### 5.2 `campaigns`
- `id` (PK, varchar 32)
- `advertiser_id` (FK to advertisers)
- `name` (varchar 255)
- `product_name` (varchar 255)
- `description` (text)
- `advertisement_text` (text)
- `landing_url` (varchar 1024)
- `keywords` (json list)
- `target_categories` (json list)
- `daily_budget` (decimal 10,2)
- `total_budget` (decimal 10,2)
- `spent_today` (decimal 10,2, default 0.00)
- `total_spent` (decimal 10,2, default 0.00)
- `pricing_model` (varchar 16: `cpc`, `cpm`)
- `bid_amount` (decimal 8,4, default 0.10)
- `priority` (int, default 0)
- `status` (varchar 32: `draft`, `active`, `paused`, `completed`, `archived`)
- `moderation_status` (varchar 32: `pending`, `approved`, `rejected`)
- `moderation_note` (text)
- `start_date`, `end_date`
- `created_at`, `updated_at`

### 5.3 `campaign_impressions`
- `id` (PK, varchar 32)
- `campaign_id` (FK to campaigns)
- `advertiser_id` (FK to advertisers)
- `user_id` (varchar 32)
- `tenant_id` (varchar 32)
- `conversation_id` (varchar 32)
- `message_id` (varchar 32)
- `cost` (decimal 8,4)
- `created_at`

### 5.4 `campaign_clicks`
- `id` (PK, varchar 32)
- `campaign_id` (FK to campaigns)
- `impression_id` (varchar 32)
- `user_id` (varchar 32)
- `cost` (decimal 8,4)
- `ip_hash` (varchar 64)
- `created_at`

### 5.5 `advertising_transactions`
- `id` (PK, varchar 32)
- `advertiser_id` (FK to advertisers)
- `amount` (decimal 12,4)
- `type` (varchar 32: `deposit`, `spend_cpc`, `spend_cpm`, `refund`, `adjustment`)
- `description` (varchar 255)
- `reference_id` (varchar 64)
- `created_at`

### 5.6 `advertising_settings`
- `id` (PK, varchar 32)
- `key` (varchar 128, unique)
- `value` (json / text)
- `description` (varchar 255)
- `updated_at`

---

## 6. Frontend & User Interface Architecture

### 6.1 Swipies Ads Advertiser Portal (`/ads`)
A dedicated, responsive dashboard under route `/ads` and linked from `Settings -> Swipies Ads`:
1. **Overview Dashboard**:
   - KPI Cards: **Account Balance**, **Active Campaigns**, **Total Impressions**, **Total Clicks**, **Average CTR**, **Total Spend**.
   - Performance Chart: Impressions, Clicks, and Spend trends over time (7d, 30d, all-time).
2. **Campaign Manager**:
   - Tabular list of campaigns with status toggles (`Active` / `Paused`), spend bars, CTR, and action menus (`Edit`, `Duplicate`, `View Analytics`).
   - `+ Create Campaign` Modal Wizard:
     - Step 1: Campaign Name, Product Name, Target Categories & Keywords.
     - Step 2: Pitch & Ad Copy, Landing Page URL.
     - Step 3: Daily Budget, Total Budget, Bid per Click/Impression, Schedule Dates.
3. **Campaign Analytics**:
   - Deep-dive charts per campaign (Hourly impressions, Click distribution, Conversion rates).
4. **Billing & Wallet**:
   - Balance overview, Deposit funds form, Transaction ledger with downloadable receipts.
5. **Advertiser Onboarding**:
   - Displayed to users without active advertiser profiles with clear value proposition and 1-click advertiser activation.

### 6.2 Admin Panel Ads Management (`/admin/ads`)
Integrated into the Swipies Admin Console:
- **Campaign Moderation Queue**: Review submitted ad copies and landing URLs; 1-click `Approve` or `Reject` (with feedback note).
- **Network Overview**: Total system ad revenue, active campaigns across all advertisers, CPM/CPC metrics.
- **Platform Attribution Controls**: Customize platform watermark text and landing URL (`https://swipies.app`).
- **Advertiser Account Controls**: Suspend/unsuspend advertisers, adjust credit limits.

### 6.3 User Settings & Pricing Matrix Display
In User Settings and Subscription Modals:
- **Free Plan**: Clearly shows `✓ Free AI Models`, `✓ RAG Search`, `✓ AI Agents`, `⚠ Contextual Sponsored Recommendations & Swipies Attribution`.
- **Plus & Pro Plans**: Displays `✓ Guaranteed 100% Ad-Free AI Experience`, `✓ No Platform Watermark (White-label AI)`.

---

## 7. Feature Flags & Configuration

All components are strictly feature-flagged in `api/settings.py` and `conf/service_conf.yaml.template`:
- `ADS_ENABLED`: Global master kill-switch (default: `True`).
- `ADS_FOR_FREE_USERS`: Enables ad evaluation for Free tier (default: `True`).
- `ADS_PLATFORM_BRANDING_ENABLED`: Enables Swipies platform attribution footer for Free tier (default: `True`).
- `ADS_LLM_PROMPT_ENABLED`: Enables prompt injection into LLM Gateway (default: `True`).
- `ADS_TARGETING_ENABLED`: Enables semantic & intent matching (default: `True`).
- `ADS_BILLING_ENABLED`: Enables real-time balance deduction (default: `True`).
- `ADS_ANALYTICS_ENABLED`: Enables impression and click telemetry (default: `True`).

---

## 8. Backward Compatibility & Non-Breaking Guarantees

1. **Zero Database Migrations Required for Existing Tables**: Existing tables (`user`, `tenant`, `dialog`, `knowledgebase`, `message`) remain 100% untouched. All advertising data resides in clean, isolated tables.
2. **Zero Conversation Interruptions**: Existing conversations, conversation IDs, assistant configs, and agents automatically inherit the gateway logic without reconfiguration.
3. **Safe Fallbacks**: If the Ads Engine encounters an error or timeout during matching, the system logs a non-blocking warning and gracefully proceeds with a clean, unadvertised AI response.
