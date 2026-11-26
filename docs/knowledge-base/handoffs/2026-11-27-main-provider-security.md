# Main branch: provider credential isolation and chat model selection

Owner explicitly requested these urgent fixes, a push to the existing primary
branch `swipies_26`, and rebuilding the existing application services. Do not
create another branch or additional application/QA containers.

Provider management now performs tenant-owned lookups with admin fallback
disabled for reading, creating, modifying and deleting instances/models. Platform
credentials are no longer reachable through the normal Model Providers API.
Instance detail responses are write-only for ordinary users; only authenticated
superusers may reveal their own managed credentials. Blank updates preserve the
existing key. Runtime model resolution remains separate from management scope.
The provider compatibility fallback cannot materialize a global key under an
ordinary account when no administrator account exists.

Chat model validation accepts exact enabled global AIModel IDs and legacy admin
TenantModel IDs only when tied to a published, enabled platform model. Capability,
account policy and available credentials are checked before returning an internal
runtime configuration. Arbitrary foreign/private tenant models remain denied.
Composite names and equivalent legacy/global IDs are normalized consistently;
default model metadata includes the actual model ID.

The header upgrade label uses a real localized `header.upgrade` entry for EN/RU/UZ
with a readable fallback for other languages. Rebuilding replaces the stale
frontend that displayed the raw translation key in the sidebar.

Verification uses the existing application container and the pre-existing
dedicated MySQL QA schema, with synthetic provider credentials. The regression
suite is `test/test_model_provider_security.py`; it must never target production.
No customer keys, database contents or credentials belong in verification output.
The exposed provider credential must be revoked/replaced by the account owner at
the provider, because preventing subsequent disclosure cannot revoke an already
copied key. No key value is recorded here.

Only reviewed paths are staged. Existing unrelated server changes, settings and
data are preserved. Private rollback copies are outside Git. Production release
checks and the final commit are recorded in the external verification report.
