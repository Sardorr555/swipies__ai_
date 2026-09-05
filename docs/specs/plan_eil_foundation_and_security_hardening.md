# Technical Implementation Plan: Enterprise Intelligence Layer (EIL) — Foundation & Security Hardening (Phase 1)

**Specification Reference:** [`docs/specs/spec_eil_foundation_and_security_hardening.md`](file:///D:/ragflow/swipies_25/ragflow/docs/specs/spec_eil_foundation_and_security_hardening.md)  
**Document Status:** Ready for Review  
**Version:** 1.0.0  
**Target Branch:** `test`  
**Plan Key:** `plan_eil_foundation_and_security_hardening`  

---

## 1. Architecture & Vertical Slice Graph

```mermaid
graph TD
    subgraph Phase 1: Database Model Restoration & Schema Init
        M1[1.1 Define Peewee Models: KnowledgeEntity, EntityAlias, KnowledgeRelation,<br/>ConversationMetadata, ExpertiseProfile, SummaryRegistry, EILAuditLog<br/>api/db/db_models.py]
        M2[1.2 Register All 7 Models in init_database_tables<br/>api/db/db_models.py]
        M3[1.3 Validate Service Imports & Table Creation<br/>api/db/services/intelligence_service.py]
        M1 --> M2
        M2 --> M3
    end

    subgraph Phase 2: Access Control & IDOR Hardening
        A1[2.1 Implement resolve_scoped_tenant_id helper<br/>api/apps/restful_apis/intelligence_api.py]
        A2[2.2 Enforce is_superuser on /export/excel<br/>api/apps/restful_apis/intelligence_api.py]
        A3[2.3 Apply Tenant Resolution to All 10 Remaining Endpoints<br/>api/apps/restful_apis/intelligence_api.py]
        M3 --> A1
        A1 --> A2
        A1 --> A3
    end

    subgraph Phase 3: Privacy Sanitization & EIL Worker Hardening
        P1[3.1 Extend process_conversation_event with sensitive_rules<br/>rag/intelligence/pipeline/worker.py]
        P2[3.2 Step 1 Ingestion: anonymize_text + PIIAnonymizer.sanitize<br/>rag/intelligence/pipeline/worker.py]
        P3[3.3 Step 4 Pre-DB Write Field Sanitizer across All Tables<br/>rag/intelligence/pipeline/worker.py]
        A3 --> P1
        P1 --> P2
        P2 --> P3
    end

    subgraph Phase 4: Non-Blocking Chat Pipeline Integration
        C1[4.1 Implement dispatch_eil_conversation_event helper<br/>api/db/services/dialog_service.py]
        C2[4.2 Hook into async_chat_solo upon turn completion<br/>api/db/services/dialog_service.py]
        C3[4.3 Hook into streaming chat upon [DONE] completion<br/>api/db/services/dialog_service.py]
        C4[4.4 Fire-and-forget asyncio.create_task with Exception Shield<br/>api/db/services/dialog_service.py]
        P3 --> C1
        C1 --> C2
        C1 --> C3
        C2 & C3 --> C4
    end

    subgraph Phase 5: Automated Security & Regression Test Suite
        T1[5.1 Zero-Plaintext Direct SQL Assertion Test AC-6.1<br/>test/test_intelligence_layer.py]
        T2[5.2 IDOR & RBAC Regression Test AC-6.2<br/>test/test_intelligence_layer.py]
        T3[5.3 Multi-Tenant Boundary Isolation Test AC-6.3<br/>test/test_intelligence_layer.py]
        T4[5.4 Superuser Cross-Tenant Aggregation Test AC-6.4<br/>test/test_intelligence_layer.py]
        T5[5.5 Service Resilience & Empty DB Test AC-6.5<br/>test/test_intelligence_layer.py]
        T6[5.6 Non-blocking Exception Resilience Test AC-6.6<br/>test/test_intelligence_layer.py]
        C4 --> T1
        C4 --> T2
        C4 --> T3
        C4 --> T4
        C4 --> T5
        C4 --> T6
    end

    subgraph Phase 6: System Verification & Parity
        V1[6.1 Execute Full Test Suite: pytest test/test_intelligence_layer.py]
        V2[6.2 Execute Sensitive Data Suite: pytest test/test_sensitive_data_replacement.py]
        V3[6.3 Clean Git Working Tree Audit]
        T1 & T2 & T3 & T4 & T5 & T6 --> V1
        V1 --> V2
        V2 --> V3
    end
```

---

## 2. Detailed Implementation Phases

### Phase 1: Database Model Restoration & Schema Init (`api/db/db_models.py`)

- **Objective:** Re-create all 7 missing Peewee ORM models in `api/db/db_models.py` and register them in `init_database_tables()` so that table creation and service queries operate without runtime exceptions.
- **Files Modified:**
  - [`api/db/db_models.py`](file:///D:/ragflow/swipies_25/ragflow/api/db/db_models.py)
  - [`api/db/services/intelligence_service.py`](file:///D:/ragflow/swipies_25/ragflow/api/db/services/intelligence_service.py)
- **Step-by-Step Actions:**
  1. Add `KnowledgeEntity` class definition:
     ```python
     class KnowledgeEntity(DataBaseModel):
         id = CharField(max_length=32, primary_key=True)
         tenant_id = CharField(max_length=32, null=False, index=True)
         name = CharField(max_length=255, null=False, index=True)
         entity_type = CharField(max_length=64, null=False, index=True, help_text="Person|Project|Tech|Doc|Org|Customer|Decision")
         description = TextField(null=True)
         canonical_id = CharField(max_length=32, null=True, index=True)
         attributes = JSONField(null=True, default=dict)
         confidence_score = FloatField(default=1.0)
         class Meta:
             db_table = "knowledge_entity"
     ```
  2. Add `EntityAlias` class definition:
     ```python
     class EntityAlias(DataBaseModel):
         id = CharField(max_length=32, primary_key=True)
         tenant_id = CharField(max_length=32, null=False, index=True)
         alias_name = CharField(max_length=255, null=False, index=True)
         entity_id = CharField(max_length=32, null=False, index=True)
         source_type = CharField(max_length=64, null=True)
         class Meta:
             db_table = "entity_alias"
     ```
  3. Add `KnowledgeRelation` class definition:
     ```python
     class KnowledgeRelation(DataBaseModel):
         id = CharField(max_length=32, primary_key=True)
         tenant_id = CharField(max_length=32, null=False, index=True)
         src_entity_id = CharField(max_length=32, null=False, index=True)
         predicate = CharField(max_length=64, null=False, index=True, help_text="OWNS|USES|CREATED|DISCUSSED|FIXES|EXPERT_IN")
         dst_entity_id = CharField(max_length=32, null=False, index=True)
         weight = FloatField(default=1.0)
         confidence_score = FloatField(default=1.0)
         conversation_id = CharField(max_length=32, null=True, index=True)
         document_id = CharField(max_length=32, null=True, index=True)
         source_snippet = TextField(null=True)
         class Meta:
             db_table = "knowledge_relation"
     ```
  4. Add `ConversationMetadata` class definition:
     ```python
     class ConversationMetadata(DataBaseModel):
         id = CharField(max_length=32, primary_key=True)
         conversation_id = CharField(max_length=32, null=False, unique=True, index=True)
         tenant_id = CharField(max_length=32, null=False, index=True)
         user_id = CharField(max_length=32, null=False, index=True)
         department = CharField(max_length=128, null=True)
         project_id = CharField(max_length=32, null=True, index=True)
         topics = JSONField(null=True, default=list)
         tags = JSONField(null=True, default=list)
         summary = TextField(null=True)
         decisions_json = JSONField(null=True, default=list)
         action_items_json = JSONField(null=True, default=list)
         unresolved_questions = JSONField(null=True, default=list)
         referenced_doc_ids = JSONField(null=True, default=list)
         models_used = JSONField(null=True, default=list)
         agents_involved = JSONField(null=True, default=list)
         language = CharField(max_length=16, null=True, default="en")
         duration_seconds = IntegerField(default=0)
         class Meta:
             db_table = "conversation_metadata"
     ```
  5. Add `ExpertiseProfile` class definition:
     ```python
     class ExpertiseProfile(DataBaseModel):
         id = CharField(max_length=32, primary_key=True)
         tenant_id = CharField(max_length=32, null=False, index=True)
         user_id = CharField(max_length=32, null=False, index=True)
         domain_topic = CharField(max_length=128, null=False, index=True)
         confidence_score = FloatField(default=0.0)
         depth_level = CharField(max_length=32, default="Intermediate")
         contribution_count = IntegerField(default=1)
         evidence_summary = TextField(null=True)
         last_active_at = BigIntegerField(null=False)
         class Meta:
             db_table = "expertise_profile"
     ```
  6. Add `SummaryRegistry` class definition:
     ```python
     class SummaryRegistry(DataBaseModel):
         id = CharField(max_length=32, primary_key=True)
         tenant_id = CharField(max_length=32, null=False, index=True)
         summary_type = CharField(max_length=32, null=False, index=True, help_text="Daily|Weekly|Monthly|Project|Customer|Department")
         target_id = CharField(max_length=64, null=False, index=True)
         title = CharField(max_length=255, null=False)
         content = TextField(null=False)
         key_decisions = JSONField(null=True, default=list)
         key_risks = JSONField(null=True, default=list)
         trending_topics = JSONField(null=True, default=list)
         period_start = BigIntegerField(null=False)
         period_end = BigIntegerField(null=False)
         class Meta:
             db_table = "summary_registry"
     ```
  7. Add `EILAuditLog` class definition:
     ```python
     class EILAuditLog(DataBaseModel):
         id = CharField(max_length=32, primary_key=True)
         tenant_id = CharField(max_length=32, null=False, index=True)
         operator_id = CharField(max_length=32, null=False, index=True)
         action = CharField(max_length=64, null=False, index=True)
         resource_type = CharField(max_length=64, null=False)
         resource_id = CharField(max_length=64, null=True)
         details = JSONField(null=True, default=dict)
         ip_address = CharField(max_length=45, null=True)
         class Meta:
             db_table = "eil_audit_log"
     ```
  8. Register all 7 models in `init_database_tables()` in `api/db/db_models.py`.

---

### Phase 2: Access Control & IDOR Hardening (`api/apps/restful_apis/intelligence_api.py`)

- **Objective:** Eliminate IDOR and multi-tenant data leaks across all 11 endpoints. Enforce `is_superuser` validation on cross-tenant exports and queries.
- **Files Modified:**
  - [`api/apps/restful_apis/intelligence_api.py`](file:///D:/ragflow/swipies_25/ragflow/api/apps/restful_apis/intelligence_api.py)
- **Step-by-Step Actions:**
  1. Define `resolve_scoped_tenant_id` at the top of `intelligence_api.py`:
     ```python
     def resolve_scoped_tenant_id(user, requested_global: bool) -> str | None:
         """
         Enforces tenant isolation:
         - Superusers can query globally if requested_global is True.
         - Regular users are strictly bound to their tenant_id regardless of requested_global.
         """
         if requested_global and getattr(user, "is_superuser", False):
             return None
         return getattr(user, "tenant_id", None) or getattr(user, "id", "")
     ```
  2. Protect `/intelligence/export/excel`:
     ```python
     @manager.route("/intelligence/export/excel", methods=["GET"])
     @login_required
     async def export_excel():
         if not getattr(current_user, "is_superuser", False):
             return get_json_result(
                 data=False,
                 retmsg="Permission denied: Superuser privileges required for global export.",
                 retcode=RetCode.AUTHENTICATION_ERROR
             )
         is_global = request.args.get("global", "false").lower() == "true"
         tenant_id = resolve_scoped_tenant_id(current_user, is_global)
         csv_data = ProactiveIntelligenceService.export_excel_onboarding(tenant_id)
         return Response(
             csv_data,
             mimetype="text/csv",
             headers={"Content-disposition": "attachment; filename=onboarding_surveys_export.csv"}
         )
     ```
  3. Refactor the remaining 10 endpoints to call `resolve_scoped_tenant_id(current_user, is_global)`:
     - `get_full_graph()`
     - `query_knowledge_graph()`
     - `search_enterprise()`
     - `get_executive_dashboard()`
     - `get_sentiment_analytics()`
     - `get_roi_analytics()`
     - `get_decision_timeline()`
     - `generate_faq_article()`
     - `build_project_wiki()`
     - `simulate_what_if()`
     - `get_dashboard_stats()`

---

### Phase 3: Privacy Sanitization & EIL Worker Hardening (`rag/intelligence/pipeline/worker.py`)

- **Objective:** Guarantee that all sensitive terms ($A \to B$) configured for a dialog are sanitized before extractors run and before any write occurs to any EIL database table.
- **Files Modified:**
  - [`rag/intelligence/pipeline/worker.py`](file:///D:/ragflow/swipies_25/ragflow/rag/intelligence/pipeline/worker.py)
  - [`rag/intelligence/security/anonymizer.py`](file:///D:/ragflow/swipies_25/ragflow/rag/intelligence/security/anonymizer.py)
- **Step-by-Step Actions:**
  1. Import `anonymize_text` from `api.utils.sensitive_data_utils`.
  2. Update `EILBackgroundWorker.process_conversation_event`:
     ```python
     def process_conversation_event(
         self,
         tenant_id: str,
         conversation_id: str,
         user_id: str,
         text_transcript: str,
         sensitive_rules: list = None,
         llm_client: Any = None
     ) -> bool:
     ```
  3. Execute Step 1 (Tenant rules substitution $A \to B$) and Step 2 (General PII sanitization):
     ```python
     if sensitive_rules:
         text_transcript = anonymize_text(text_transcript, sensitive_rules)
     clean_text, pii_meta = PIIAnonymizer.sanitize(text_transcript)
     ```
  4. Implement recursive field-level pre-DB write sanitizer `_sanitize(val)`:
     ```python
     def _sanitize(val):
         if isinstance(val, str):
             return anonymize_text(val, sensitive_rules) if sensitive_rules else val
         if isinstance(val, list):
             return [_sanitize(x) for x in val]
         if isinstance(val, dict):
             return {k: _sanitize(v) for k, v in val.items()}
         return val
     ```
  5. Apply `_sanitize` to `KnowledgeEntity.create()`, `EntityAlias.create()`, `KnowledgeRelation.create()`, `ConversationMetadata.create()`, `ExpertiseProfile.create()`, and `SummaryRegistry.create()`.

---

### Phase 4: Non-Blocking Chat Pipeline Integration (`api/db/services/dialog_service.py`)

- **Objective:** Hook the EIL background worker into `dialog_service.py` non-blockingly upon completion of every conversation turn.
- **Files Modified:**
  - [`api/db/services/dialog_service.py`](file:///D:/ragflow/swipies_25/ragflow/api/db/services/dialog_service.py)
- **Step-by-Step Actions:**
  1. Add helper `_dispatch_eil_event(dialog, conv_id, user_id, transcript)`:
     ```python
     def _dispatch_eil_event(dialog, conv_id, user_id, transcript):
         try:
             sensitive_rules = (dialog.prompt_config or {}).get("sensitive_data_replacement", {}).get("rules", [])
             tenant_id = getattr(dialog, "tenant_id", "") or getattr(dialog, "user_id", "")
             from rag.intelligence.pipeline.worker import EILBackgroundWorker
             worker = EILBackgroundWorker()
             
             import threading
             def _run():
                 try:
                     worker.process_conversation_event(
                         tenant_id=tenant_id,
                         conversation_id=conv_id,
                         user_id=user_id,
                         text_transcript=transcript,
                         sensitive_rules=sensitive_rules
                     )
                 except Exception as err:
                     logger.warning(f"[EIL] Background processing failed for conv {conv_id}: {err}")
                     
             t = threading.Thread(target=_run, daemon=True)
             t.start()
         except Exception as e:
             logger.warning(f"[EIL] Failed to dispatch background intelligence event: {e}")
     ```
  2. Invoke `_dispatch_eil_event` in `async_chat_solo` after history is updated.
  3. Invoke `_dispatch_eil_event` in streaming `chat` (KB mode) when stream finishes.

---

### Phase 5: Automated Security & Regression Test Suite (`test/test_intelligence_layer.py`)

- **Objective:** Implement full automated test suite verifying all 6 acceptance criteria.
- **Files Modified:**
  - [`test/test_intelligence_layer.py`](file:///D:/ragflow/swipies_25/ragflow/test/test_intelligence_layer.py)
- **Test Matrix:**
  1. `test_zero_plaintext_sensitive_data_in_all_eil_tables`: Verifies 0 occurrences of Word A across all EIL tables.
  2. `test_idor_and_rbac_export_excel`: Verifies regular user receives HTTP 403 on `/export/excel`.
  3. `test_idor_global_flag_forced_tenant_scoping`: Verifies regular user `?global=true` is forced to `current_user.tenant_id`.
  4. `test_multi_tenant_boundary_isolation`: Verifies Tenant A cannot see Tenant B's data.
  5. `test_superuser_global_access`: Verifies superuser can query cross-tenant aggregates.
  6. `test_empty_db_and_service_resilience`: Verifies all services handle empty DB gracefully without 500.
  7. `test_non_blocking_worker_resilience`: Verifies chat completes normally even if worker fails.

---

### Phase 6: System Verification & Parity

- **Objective:** Run complete verification across entire platform before commit.
- **Commands:**
  1. `pytest test/test_intelligence_layer.py`
  2. `pytest test/test_sensitive_data_replacement.py`
  3. `git status --short` verification.
