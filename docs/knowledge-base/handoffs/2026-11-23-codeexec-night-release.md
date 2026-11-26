# CodeExec — staged implementation, publication deferred

Owner instruction: do not push now; release will be done at night. A later
request to continue preparation did not revoke that instruction. Do not infer
publication authorization merely from the clock.

Baseline server commit: `c0294a8cd`. Existing unrelated server changes were
preserved. Application source and sandbox settings in the production checkout
were not overwritten. Prepared source is under
`/home/ubuntu/codeexec-release-20261122`; the staging application source copy is
`/ragflow/work-codeexec-stage` inside `swipies-cpu`.

Verified: 30 authenticated API/isolation checks, 6 actual Canvas branching checks
using synthetic Agent output, 13 new regression tests and 21 existing connector
security tests. Run the legacy connector suite in a separate process because its
module stubs conflict with an already loaded real Quart application.

The extra Canvas check preserves the pending-receipt stage when the user writes
an intermediate text message before attaching the receipt. A full isolated
frontend production build was also prepared; see the saved build result.

Real Telegram deliveries: synthetic image and text document with profile captions
to `5095856147`, message IDs 32 and 33. Real rejection did not claim delivery.
No money was transferred. Temporary accounts were deleted and the staging
controller/control network stopped and removed after tests. No ephemeral runner
containers remained. The staging copy's runtime credential file was removed.

Infrastructure prepared: SHA512-verified gVisor release-20261116.0, Docker runtime
registration and test image `swipies-codeexec:2026-11-22`. The dedicated
10.240.0.0/16 INPUT drop rule remains; install the included systemd unit for reboot
persistence during the authorized release. The original service credential is
kept only in the protected server `.manager.env`, excluded from the source bundle.

The owner still needs to rotate the old Telegram token through BotFather before
publication, since previous work embedded it in source/history. Save the new token
in the encrypted channel credential store. Migration is dry-run by default and
has not been applied: 17 related scenario snapshots and 4 channels were found.

Next: review the patch against the server's current dirty checkout, complete the
agreed release, apply the encrypted credential/canvas migration, restart workers,
and verify public HTTPS/MCP plus a real inbound Telegram photo/document without
a caption. Do not claim production readiness from staging checks alone.

See [runtime and release procedure](../codeexec-platform.md) and
[ADR-010](../decisions/ADR-010-platform-codeexec-isolation.md).


Update 2026-11-26: the owner explicitly authorized a Git push of the combined CodeExec and Telegram analytics changes. Deployment, credential rotation and production migration remain separate release steps.
