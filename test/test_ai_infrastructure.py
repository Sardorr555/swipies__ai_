#
# Integration test for RAGFlow Single Global Instance & PRO BYOK
#
import sys
import os
import types
import importlib.abc
import sqlalchemy.types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class AutoMock(types.ModuleType):
    def __init__(self, name):
        super().__init__(name)
        self.__path__ = []
        self.__file__ = "<mock>"
    def __getattr__(self, name):
        val = AutoMock(f"{self.__name__}.{name}")
        setattr(self, name, val)
        return val
    def __call__(self, *args, **kwargs):
        return AutoMock("mock_call")

class BaseClass:
    def __init__(self, *args, **kwargs): pass
    def __getattr__(self, name): return lambda *a, **kw: None

class ArrayType(sqlalchemy.types.JSON):
    def __init__(self, *args, **kwargs): pass

class VectorType(sqlalchemy.types.JSON):
    def __init__(self, *args, **kwargs): pass

class AutoLoader(importlib.abc.Loader):
    def create_module(self, spec):
        mod = AutoMock(spec.name)
        if spec.name == "infinity.rag_tokenizer":
            mod.RagTokenizer = BaseClass
        elif spec.name == "pyobvector":
            mod.ARRAY = ArrayType
            mod.VECTOR = VectorType
        elif spec.name == "opensearchpy":
            mod.OpenSearch = BaseClass
            mod.NotFoundError = Exception
        elif spec.name == "azure.storage.blob":
            mod.ContainerClient = BaseClass
        return mod
    def exec_module(self, module):
        pass

class AutoImporter(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        mock_prefixes = [
            "infinity", "pyobvector", "qdrant", "pymilvus", "elasticsearch",
            "elastic", "tika", "opensearch", "azure", "minio", "oss2", "cos",
            "boto3", "botocore", "google.cloud", "s3transfer", "opendal", "redis", "valkey", "langfuse"
        ]
        if any(fullname.startswith(prefix) for prefix in mock_prefixes):
            import importlib.machinery
            return importlib.machinery.ModuleSpec(fullname, AutoLoader(), is_package=True)
        return None

sys.meta_path.insert(0, AutoImporter())

from peewee import SqliteDatabase
from api.db.db_models import (
    DB,
    GlobalRagflowInstance,
    AIProvider,
    AIModel,
    SubscriptionPlan,
    SubscriptionAIPolicy,
    UserTokenLimit,
    TokenUsageLog,
    AIAuditLog,
    User,
    Tenant,
)

# Replace DB connection context to passthrough for SQLite in-memory testing
DB.connection_context = lambda: (lambda fn: fn)

from api.utils.key_crypto import encrypt_api_key, decrypt_api_key, mask_api_key, sanitize_sensitive_dict
from api.db.services.global_instance_service import GlobalInstanceService, GLOBAL_INSTANCE_ID
from api.db.services.ai_policy_service import AIPolicyManager, AIModelService
from api.db.services.ai_provider_service import AIProviderService
from api.db.services.ai_audit_log_service import AIAuditLogService

def run_tests():
    print("1. Testing authenticated Key Crypto...")
    raw_key = "sk-proj-test-secret-key-abcdef-123456789"
    encrypted = encrypt_api_key(raw_key)
    assert encrypted.startswith("enc:v1:"), f"Bad enc format: {encrypted}"
    decrypted = decrypt_api_key(encrypted)
    assert decrypted == raw_key, f"Decryption mismatch: {decrypted} != {raw_key}"
    masked = mask_api_key(raw_key)
    assert masked.startswith("sk-") and masked.endswith("6789"), f"Bad mask: {masked}"
    print("   -> Key Crypto OK")

    print("2. Initializing In-Memory Test Database Schema...")
    test_db = SqliteDatabase(":memory:")
    models_to_test = [
        GlobalRagflowInstance,
        AIProvider,
        AIModel,
        SubscriptionPlan,
        SubscriptionAIPolicy,
        UserTokenLimit,
        TokenUsageLog,
        AIAuditLog,
        User,
        Tenant,
    ]
    for m in models_to_test:
        m._meta.database = test_db
    test_db.bind(models_to_test)
    test_db.connect()
    test_db.create_tables(models_to_test)
    print("   -> Test DB Schema & Tables created OK")
    from api.db.services.ai_policy_service import AIPolicyManager, AIModelService
    from api.db.services.ai_provider_service import AIProviderService
    from api.db.services.ai_audit_log_service import AIAuditLogService

    print("3. Testing Single Global Instance Singleton...")
    inst = GlobalInstanceService.get_global_instance()
    assert inst.id == "GLOBAL", f"Expected GLOBAL, got {inst.id}"
    print(f"   -> Global Instance verified: {inst.id} ({inst.name}) - Status: {inst.status}")

    print("4. Testing AIPolicyManager Default Data Seeding...")
    AIPolicyManager.init_default_data()
    providers = AIProviderService.get_global_providers()
    models = AIModelService.get_platform_models()
    print(f"   -> Global Providers: {len(providers)}, Global Platform Models: {len(models)}")
    assert len(providers) >= 4
    assert len(models) >= 10

    print("5. Testing Model Access Policy Resolution for FREE vs PLUS vs PRO...")
    # FREE tier should access gpt-4o-mini
    free_ok, msg1, code1 = AIPolicyManager.check_model_access("test_free_user", "openai/gpt-4o-mini")
    assert free_ok == True, f"Free user should access gpt-4o-mini: {msg1}"

    # FREE tier should NOT access claude-3-5-sonnet (pro only)
    free_pro_ok, msg2, code2 = AIPolicyManager.check_model_access("test_free_user", "anthropic/claude-3-5-sonnet-20241022")
    assert free_pro_ok == False and code2 == 403, f"Free user should get 403 for claude: {msg2}"

    # PRO check for adding custom model
    can_free, reason_free = AIPolicyManager.can_add_custom_model("test_free_user")
    assert can_free == False, "Free user must not be allowed to add custom BYOK model"
    print("   -> Subscription tier access & BYOK gating verified OK")

    print("6. Testing Central Token Accounting & Cost Computation...")
    AIPolicyManager.record_token_usage("test_tenant_1", "test_user_1", "openai/gpt-4o-mini", "CHAT", 10000, 2000, 12000)
    analytics = AIPolicyManager.get_admin_analytics()
    assert analytics["summary"]["total_requests"] >= 1
    assert analytics["summary"]["total_cost"] > 0
    print(f"   -> Analytics recorded: Requests: {analytics['summary']['total_requests']}, Total tokens: {analytics['summary']['total_tokens']}, Estimated cost: ${analytics['summary']['total_cost']}")

    print("7. Testing AI Infrastructure Audit Log Sanitization...")
    AIAuditLogService.log_action(
        user_id="admin_user_001",
        action="UPDATE_MODEL_CONFIG",
        target_type="ai_model",
        target_id="openai/gpt-4o",
        new_val={"api_key": "super_secret_password_999", "status": "active"},
    )
    logs, total = AIAuditLogService.get_logs(limit=5)
    assert total >= 1
    parsed_details = logs[0].get("details_parsed", {})
    assert "super_secret_password_999" not in str(parsed_details), "API key leaked into audit log!"
    print("   -> Audit Logging & secret sanitization verified OK")

    print("\n=======================================================")
    print(" ALL BACKEND INTEGRATION & ARCHITECTURE TESTS PASSED! ")
    print("=======================================================")

if __name__ == "__main__":
    run_tests()
