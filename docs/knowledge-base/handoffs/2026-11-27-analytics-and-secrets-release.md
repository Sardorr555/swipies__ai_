# Handoff: Telegram analytics in platform + provider secrets release (2026-11-27)

## Branch / commits
- Branch: `swipies_26`
- `chore(server): capture live production hotfixes into git` — records hand-applied server changes so the CI deploy guard passes (docker/.env stays server-local).
- `feat: Telegram bot analytics in Chat channels + write-only provider keys` — this release.

## What changed
- **Provider keys (write-only).** `show_provider_instance` returns `api_key: ""` plus `has_api_key` for every role, admin included. A blank key on update keeps the stored server key. Platform (admin) keys keep working for users on the server side only. Tests: `test/test_model_provider_security.py`.
- **Telegram analytics** taken from `codex/codeexec-telegram-analytics` (commit 90b3e45) *without* the CodeExec isolation parts (sandbox runtime, codeexec API/service, admin sandbox page), which stay on that branch.
  - Button «Аналитика» is shown for every Telegram bot row in Chat channels; the page shows an empty state until data arrives.
  - Routes: `/user-setting/chat-channel/:channelId/analytics`, public share `/shared/telegram-analytics`.
  - `drop_pending_updates` kept `True` (unchanged behaviour); analytics bot registration added on channel start.
  - Channel configs are now encrypted on save (`encrypt_connector_config`); reads use `decrypt_connector_config`, which passes legacy plaintext through.
- Removed a hardcoded GitHub token fallback from `.github/workflows/deploy_new_server.yml`. The token must be revoked by the owner.

## Deployment notes
- Server tree had uncommitted changes, so CI deploy refused to run since 2026-11-10. After this release the server must be clean (`git status` empty except untracked scratch files) for `deploy_main.yml` to work on every push.
- `docker/.env` is tracked in git but holds production secrets: on the server it is marked `git update-index --skip-worktree docker/.env`. Do not commit server `.env` values.
- Analytics tables: additive migration `python api/scripts/migrate_telegram_analytics.py --apply` (owner-approved for this release), then restart `ragflow-cpu` so bots register.

## Not verified here
- Full frontend `tsc`/vite build could not run in the agent sandbox (lockfile registry blocked); syntax of changed TS files was checked. The server build in `deploy_main.sh` is the real gate and rolls back on failure.
- Python tests require the full app environment; run inside the container.
