# Public cloud landing and AI discovery

The public root at https://swipies.app/ is a static Nginx site. The current
cloud HTML was synchronized from production on 2026-10-27 before adding the
external AI control section; the previous checked-in root was an older
enterprise design. Existing enterprise pages, pricing, forms and assets were
not replaced by this release. Root index.html contains its styles, JavaScript
and EN/RU/UZ translations; legacy separate scripts are not its source of truth.

## Public entry points

- `/#agent-access`: localized explanation, example workflow and copyable prompt.
- `/agents.html`: human connection guide, no JavaScript required.
- `/llms.txt` and `/llms-full.txt`: readable AI discovery and integration instructions.
- `/agent-access.json`: custom capability/discovery document, not a universal installer.
- `/agent-access.openapi.json`: OpenAPI 3.1 gateway contract; tenant operations are discovered at runtime.
- `/downloads/swipies_agent_client.py.txt`: exact source of `tools/swipies_agent_client.py`.
  Save it as `swipies_agent_client.py`. Nginx deliberately denies .py URLs;
  keep the text download rather than weakening the deny rule.

- `/agent-setup.js` and `/agent-setup.css`: shared localized setup generator on
  the homepage and guide. Client names, terminal, Python command and a local
  absolute path produce Codex/Claude Code commands or Cursor JSON. The path
  remains in memory; no keys are collected and no connection is installed.

## Maintenance and release

Update the visible section, translations, guide and machine documents together.
Derive contracts from api/agent_access.py and the live runtime manifest; never
hardcode operation IDs or advertise Ads/admin/payment support in MCP.
Whenever tools/swipies_agent_client.py changes, refresh and byte-compare the
public text copy. Never embed an account credential in any public asset.

The main platform deployment workflow does not publish this static web root.
Publish only the ten files listed above (including sitemap.xml and index.html)
to /var/www/html after owner authorization. Preserve private backups outside the
web root, check that the original root has not changed, write documentation
before index.html atomically, and verify public HTTPS statuses/content types.
Cloudflare may transform HTML, so compare origin files byte-for-byte and check
the public HTML semantically. JSON, plaintext and the client must match exactly.
Restore the previous whitelisted files if verification fails. No container
restart, Nginx configuration change or database migration is required.

Validation: parse HTML/JSON/JSON-LD/XML, check inline JavaScript syntax, local
anchors, unique IDs, all three translations and OpenAPI references/schemas;
inspect desktop/mobile and compare public API discovery to the specification.


## Client setup maintenance

Keep the setup markup on index.html and agents.html in sync. Homepage setup
inherits EN/RU/UZ from the page language; the standalone guide has its own
language selector. Change both JS/CSS cache version queries when updating assets.
Use textContent for generated commands; never insert paths using innerHTML.
Commands use PowerShell literal quoting on Windows and POSIX shell quoting on
macOS/Linux. Cursor JSON uses JSON.stringify. Copy stays disabled until the
path is absolute, ends in .py and contains no control characters. The page
cannot verify that the file or Python interpreter exists.

Run `node tools/check_swipies_setup.cjs` from the repository root. The check
covers 18 client/terminal/interpreter combinations, invalid inputs, complete
EN/RU/UZ strings and the absence of network/storage APIs in the generator.
Inspect desktop/mobile and copied output in the browser. Before publishing,
verify official client command/configuration documentation and local Codex CLI
help. Current references: https://developers.openai.com/codex/mcp/,
https://code.claude.com/docs/en/mcp and
https://cursor.com/help/customization/mcp.

Existing account keys belong in the actual MCP process environment before first
use. A local path field never accepts or configures a paid account credential.
The generator does not claim a successful connection or enable host tools.


## Automatic HTTPS onboarding (2026-10-28)

The default documentation entry is direct HTTPS bootstrap, before optional
host MCP installation. Keep the same sequence in llms.txt/full, the automatic
section of agents.html, discovery JSON and visible EN/RU/UZ homepage copy.
An HTTP-capable assistant needs no manual MCP installation to send JSON-RPC.
Do not imply that webpage-only sessions acquire tools, that a new Free account
inherits paid resources, or that Ads/admin/payment operations are exposed.
New-account verification must persist its identity privately, use only synthetic
test data, inspect operation docs and remove only its own disposable resources.
