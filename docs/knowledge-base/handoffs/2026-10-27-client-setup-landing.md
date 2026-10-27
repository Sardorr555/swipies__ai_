# Client-specific MCP setup — 2026-10-27

Branch: swipies_26. Static landing-only release, following 5ce40b0f3.

Added a shared generator to /#swipies-setup and /agents.html#swipies-setup.
It supports Codex CLI, Claude Code user-scoped stdio and Cursor mcp.json;
Windows PowerShell and POSIX shell; Python interpreter selection; an absolute
local client path; translated EN/RU/UZ steps and copy feedback. The homepage
inherits its language; the guide has a separate language selector. Download is
the existing source served as .py.txt with save-as instructions.

Generated output is local-only, held in memory and rendered as text. Invalid
paths/control characters disable copying. No credential is collected, request
made, client configuration written, permission bypassed or connection status
invented. Existing-account/Plus/Pro users are directed to set SWIPIES_API_KEY in
the MCP process securely before first use. Cursor instructions preserve other
servers. Full AI instructions and discovery JSON now link the setup guide.

Command syntax verified against local codex mcp add --help and official Claude
Code/Cursor documentation. Checks passed: 18 client/terminal/interpreter
combinations, 8 invalid inputs, translation completeness, JSON round trips,
6 PowerShell AST parses and 6 POSIX shlex parses of paths containing spaces,
apostrophes and shell metacharacters (no generated commands executed).
25 static HTML/JS/JSON/Schema/sitemap/client checks also passed. Browser checks
covered all 3 clients in all 3 languages, homepage language inheritance,
copy-success feedback, invalid-path disabling, POSIX interpreter switching and
390px Uzbek layout without horizontal overflow. Browser clipboard readback is
not independently available. This release does not test installing the
connection into actual Claude Code/Cursor applications on customer machines.

Ten public assets returned HTTP 200 and expected MIME types after publication.
Private server backup: /home/ubuntu/swipies-deployments/landing-20261027T012156Z.
Every existing asset's original revision was checked before replacement; new
asset paths were required absent. Docs/assets were installed before index.html,
and rollback remains automatic on failed HTTPS checks. No backend containers,
Nginx configuration or database changes. Use [skip ci] for this static-only
commit; main platform CI does not publish the public web root.
