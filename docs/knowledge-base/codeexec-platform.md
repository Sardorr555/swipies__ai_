# Platform CodeExec release and verification

Date: 2026-11-23. Production push and application release are deferred by owner
instruction. The production application files, sandbox settings and bot binding
have not been changed by this implementation.

## Implementation

- `agent/sandbox/providers/isolated.py`: authenticated platform runtime, current
  settings on every dispatch, safe provider errors, Python-only execution.
- `agent/sandbox/isolated_runtime/`: disposable gVisor runner and private egress
  proxy, readonly root, uid 65534, no capabilities, no host/application mounts.
- `api/db/services/codeexec_service.py`: active-account policy, existing plan and
  token ceilings, request reservations, file bounds and owner-bound integration.
- `api/db/services/telegram_delivery_service.py`: encrypted channel credential
  resolution and multipart upload, success only after Telegram `ok=true` plus
  `message_id`; payment always pending manual review.
- `api/apps/restful_apis/codeexec_api.py`: authenticated status and execution;
  JSON data URI and multipart file inputs. These two operations are discovered
  through the existing MCP operation catalog. No admin operation is exposed.
- Channel service encrypts new/updated secrets using the existing AES-GCM vault
  format. Trusted channel bootstrap decrypts credentials immediately before use.
- Telegram channel carries images/documents even when their caption is empty.
- CodeExec no longer accepts a nonzero exit status as success because of partial
  stdout; stale business output is cleared before each run.

## Runtime limits

30 seconds maximum per execution, 512 MiB RAM, one CPU, 64 processes, 64 file
descriptors, 10 MiB per file and total returned artifacts, 20 returned files,
64 MiB workspace, 16 MiB temporary directory, 2 MiB combined stdout/stderr,
256 KiB source, 14 MiB arguments, 16 MiB HTTP body, 2 concurrent runs/account and
3 concurrent runs/platform. Egress proxy is limited to 64 MiB and 16 MiB traffic.
Per-run resources are removed in `finally`; surviving resources are reclaimed
when the sole controller restarts. Proxy and runner also have finite lifetimes.

## API examples

`GET /api/v1/codeexec/status` with the current account Authorization header returns
`ready` and public limits, without global credentials or provider endpoints.

`POST /api/v1/codeexec/execute`, JSON body:

```json
{"code":"def main(value): return value * 2","arguments":{"value":21},"timeout":10}
```

For multipart, provide `code`, JSON text `arguments`, optional `timeout`, and one
or more `file` parts. Python receives `attachments` with filename, MIME and data URI.
Return a JSON-serializable value from `main(**arguments)`.

Optional owner-controlled `telegram_delivery` has `channel_id` and `recipient_id`.
The Python result must contain `attachment` (data URI), or `attachment_argument`
(name of an original argument), plus `filename`, `caption` and `kind`. Never put
a Telegram token into code or arguments. Confirm delivery only if result.ok is
the Boolean true. The migrated scenario explicitly rejects the string false.

MCP: discover using `swipies_list_operations(keyword="codeexec")`, inspect each
operation, then invoke through `swipies_execute`. Normal authentication, scopes
and account limits apply. Admin configuration is kept outside this catalog.

## Nighttime release procedure (not executed)

1. Review the source bundle and server diff; preserve existing unrelated changes.
   No Git push or production publication has been performed.
2. gVisor `runsc` release-20261116.0 was installed with verified upstream SHA512
   and Docker configuration reloaded. A real nonroot Python smoke test passed.
3. Install/enable `codeexec-firewall.service`; verify the INPUT drop rule before
   starting the controller. The dedicated subnet must not overlap deployment
   routes. The test rule is currently installed for this isolated range.
4. In `agent/sandbox/isolated_runtime`, create `.manager.env` with a random
   `CODEEXEC_MANAGER_TOKEN`, permissions 0600. Never commit this file. Build and
   start `compose.yaml`. The controller has no published ports. Attach only the
   trusted API/worker containers to `swipies-codeexec-control`.
5. Install the reviewed Python changes and admin UI asset through the normal
   release process. A complete `web/Dockerfile` builder-target production build
   passed on the isolated server copy; no frontend asset was published.
6. `prepare_release.py` defaults to dry-run. It verifies channel/canvas ownership,
   prepares encrypted rollback material, migrates channel credentials and removes
   the legacy bot token from this canvas and its saved scenario snapshots.
   Apply only during the agreed release. It selects the isolated provider and
   connects channel `10fc1030e67911f1ab8bbd075d96b9fd` to canvas
   `aa35ab5ce67a11f1ab8bbd075d96b9fd`. Recipient remains `5095856147`.
7. Restart application/worker processes, then repeat authenticated public HTTPS
   status, two ordinary accounts plus a new account, multipart and Telegram tests.
   Also test a real inbound Telegram photo/document without a caption.

Dry-run found 17 related scenario snapshots and 4 channel records to migrate.
The fake bank card in the old scenario is removed; no real payment details are
invented. The bot asks for 100000 UZS only after profile confirmation. A person
reviews payment; a receipt image is never treated as proof of payment.

## Remaining release boundaries

The existing bot token was already stored in plaintext source/history by prior
work. Rotate it through BotFather and save the replacement in the encrypted
channel credential store during release. This implementation cannot revoke
copies in old logs, previous agents' scratch files or external history.

Staging uses a separate application source copy and the existing trusted database
for disposable accounts. Sandbox settings are overridden only inside the staging
test process. Real Telegram test messages were sent by explicit task authorization,
using synthetic attachments without any financial transaction.

The production LLM conversation and public MCP endpoint remain on the old code
until release. Branching tests cover the real Canvas components with synthetic
Agent output; they do not claim a live, end-user Telegram conversation passed.
See the accompanying verification report for exact successful assertions.
