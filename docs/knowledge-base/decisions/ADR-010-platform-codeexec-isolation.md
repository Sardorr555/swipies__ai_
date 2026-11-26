# ADR-010: Platform CodeExec with disposable gVisor runtimes

Date: 2026-11-23. Status: implemented and tested on a separate staging copy;
production publication is deferred by the owner.

The local process provider runs inside the application container and cannot be
the security boundary for arbitrary code from platform users. Separate working
directories do not isolate server files, service credentials or network access.

Use a platform-managed HTTP provider and a fresh nonroot gVisor container for
every Python execution. Never fall back to local processes for account code.
The controller holds Docker authority and only its own service credential; it
has no application source, database credentials or tenant storage mounts.
Do not expose its HTTP port publicly or mount its Docker socket into runners.

Each run receives a private internal network and a disposable CONNECT gateway.
Only api.telegram.org:443 is accepted. The trusted platform resolves this fixed
hostname, validates public IPv4 addresses, and pins the gateway's connection.
TLS certificate validation stays in the Python HTTPS client. Other destinations,
redirects to other hosts, metadata and application service networks are denied.
An INPUT rule blocks the allocated 10.240.0.0/16 range from the Docker host.

Integration delivery executes outside user code. The owner selects an encrypted
channel credential and a recipient in static scenario parameters. Python returns
an attachment or a reference to its input argument, filename and caption. The
trusted delivery service resolves the owner-bound credential and uploads multipart
to the fixed Telegram HTTPS origin. Neither tokens nor credential objects enter
Python, model prompts, scenario code or execution results.

CodeExec requires an active account and applies plan request/token ceilings and
user overrides. Redis atomically reserves CodeExec daily, monthly and minute
request counters, combined with existing AI usage checks. Resource ceilings apply
even to administrator-owned workflows. An unavailable limiter denies execution.

Tradeoffs: only Python is enabled by this isolated provider. The controller remains
a privileged infrastructure component because it controls Docker. gVisor reduces
host kernel exposure but is not a guarantee against every runtime vulnerability.
The trusted Telegram sender can time out after Telegram accepted a request;
such a timeout returns delivery status unknown and never confirms delivery.
