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

## Maintenance and release

Update the visible section, translations, guide and machine documents together.
Derive contracts from api/agent_access.py and the live runtime manifest; never
hardcode operation IDs or advertise Ads/admin/payment support in MCP.
Whenever tools/swipies_agent_client.py changes, refresh and byte-compare the
public text copy. Never embed an account credential in any public asset.

The main platform deployment workflow does not publish this static web root.
Publish only the eight files listed above (including sitemap.xml and index.html)
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
