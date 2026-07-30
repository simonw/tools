# Fly.io Platform Changelog

A detailed changelog of new features and changes to the Fly.io platform, reconstructed entirely from the git history of the [superfly/docs](https://github.com/superfly/docs) repository (the source for [fly.io/docs](https://fly.io/docs)).

## Methodology

All 3,541 commits in the repository — from the initial public commit on **2021-05-30** through **2026-07-29** — were reviewed. Commit subjects, diffs, and file additions were used to identify platform changes: new products and features, changes to existing features, deprecations and removals, pricing changes, and region/hardware changes. Pure documentation housekeeping (typo fixes, formatting, link fixes, docs-site tooling) was excluded.

**A caveat on dates**: each date is the date the change landed in the *documentation*, which usually tracks the feature's launch closely but can lag (or occasionally precede) the actual platform change. Entries describing something as "documented" may reflect a capability that existed earlier and was only written up at that point.

Entries are ordered newest-first by year; within each year they run chronologically by month.

## The big arcs

A few multi-year storylines stand out across the history:

- **Nomad ("Apps V1") → Fly Machines ("Apps V2")**: Machines commands first appear in September 2021, the Machines API soft-launches in May 2022, Apps V2 ships in March 2023, becomes the default in May 2023, automated migration arrives June 2023, and the last V1/Nomad docs are deleted in November 2023.
- **Postgres**: from the original Stolon-based Fly Postgres (2021), to `postgres-flex` on Machines (2022–2023), to the Supabase partnership (2024, wound down in 2025), to the fully managed **Managed Postgres (MPG)** product launched in early 2025 and made the recommended option that October.
- **SQLite/LiteFS**: LiteFS launches in beta September 2022, LiteFS Cloud launches June 2023 and is sunset by October 2024.
- **GPUs**: launched in waitlist beta October 2023 (A100s, then L40S and A10), price cuts through 2024–2025, then deprecated in February 2026 with shutdown slated for August 2026.
- **Pricing**: from free tier with allowances (2021–2023), to the $5 Hobby plan (November 2023), to Pay As You Go (June 2024), to fully usage-based billing with all legacy plans sunset (October 2024) and a 7-day free trial (October 2025).
- **Object storage**: Tigris launches in beta January 2024, GA a month later, with steadily deeper platform integration (statics serving, custom domains, object ACLs) — and its free data transfer ending in 2025–2026.
- **Routing**: the `fly-replay` header (2022) grows into a full dynamic request routing system — replay caching, instance pinning, region preference lists, cross-network and cross-organization replays (2025–2026).

---

## 2026

### January 2026
- **2026-01-05** — **App-scoped egress IPs exit beta; machine-scoped egress IPs deprecated**: flyctl docs dropped the "(Beta)" label from `fly ips allocate-egress` (app-scoped static egress IPs), while the `fly machine egress-ip` commands were marked "(Deprecated)" — the start of the transition from machine-scoped to app-scoped static egress IPs.
- **2026-01-08** — **New `fly mpg detach` command**: Managed Postgres (MPG) gained a `detach` command to remove the attachment record linking an app to a managed Postgres cluster (secrets must still be removed separately with `fly secrets unset`).
- **2026-01-20** — **Fly Kubernetes moves to closed beta**: All FKS (Fly Kubernetes) doc pages were updated to state the service is in *closed* beta (previously just "beta"), still not recommended for critical production use.
- **2026-01-20** — **TLS handler supports custom ALPN protocols**: Docs updated to highlight that the Fly Proxy `tls` handler can terminate TLS for arbitrary non-HTTP protocols via custom ALPN values (example changed to MQTT), alongside revised recommendations for gRPC service handlers.
- **2026-01-27** — **`fly secrets list` shows per-machine deployment status**: The command now reports each secret's deployment status across Machines — Deployed, Staged (not deployed to any machine, marked `*`), Partial (marked `!`), or Unknown — instead of just the time the secret was last set.

### February 2026
- **2026-02-09** — **New Machine root-filesystem and swap flags**: `fly machine create/run/update` gained `--rootfs-persist` (persist root filesystem across restarts: never/always/restart) and `--rootfs-size` (grow the root filesystem via overlayfs), followed by `--swap-size` (Feb 10) and `--rootfs-fs-size` (Feb 11) for sizing the filesystem independent of the rootfs volume.
- **2026-02-09** — **Arcjet extension adds Python support**: The Arcjet security extension docs added Python SDK support with a FastAPI integration example, alongside the existing JavaScript support.
- **2026-02-11** — **GPU Machines deprecated with price cuts**: GPU-enabled Fly Machines were officially deprecated, with docs warning "GPUs are deprecated and will be unavailable after August 1." On-demand prices were roughly halved for the wind-down: A10 $1.50→$0.75/hr, L40S $1.25→$0.70/hr, A100 40G PCIe $2.50→$1.25/hr, A100 80G SXM $3.50→$1.50/hr. GPU mentions were subsequently scrubbed from other docs (Mar 18) and the Flycast blueprint was rewritten to drop its GPU/Ollama example (May 19).
- **2026-02-11** — **Upstash Redis fixed plans, Auto Upgrade, and Prod Pack**: `fly redis create` gained `--plan`, `--enable-auto-upgrade`, and `--enable-prodpack` flags. Docs (Feb 17) replaced the old Starter/Standard/Pro plans with new fixed-size plans (Fixed 250MB $10/mo through Fixed 50GB $400/mo, plus per-read-region fees), an Auto Upgrade add-on that bumps you to the next plan when hitting limits, and a $200/mo Prod Pack add-on with enterprise monitoring/compliance/availability features, manageable via `fly redis update`.
- **2026-02-12** — **Custom TLS certificate import (`fly certs import`)**: You can now upload your own TLS certificate and private key (PEM format) instead of relying only on Fly-managed Let's Encrypt certs. A major certificate docs overhaul (Feb 17) also documented the new `fly certs setup` flow, a `_fly-ownership` TXT record method for domain ownership verification (useful behind CDNs or when importing custom certs), the HTTP-01 challenge, and added a full Certificates resource reference (~700 lines) to the Machines API docs.

### March 2026
- **2026-03-02** — **`fly platform regions` drops capacity info**: The command no longer shows the 'Capacity' column indicating how many performance-1x VMs could be launched per region.
- **2026-03-09** — **New `fly machine wait` command**: Waits for a Machine to reach a given state (`--state`, default "settled") with a configurable `--wait-timeout` (default 5m).
- **2026-03-18** — **Machine restart policy renamed `on-fail` → `on-failure`**: The `--restart` flag option on `fly machine create/run/update` was renamed; `on-failure` remains the default for Machines created by `fly deploy` and scheduled Machines, `always` for `fly m run`.
- **2026-03-20** — **fly-replay gains `timeout` and `fallback`**: Dynamic request routing via the `fly-replay` header now supports a `timeout` field (how long the proxy tries the replay target) and a `fallback` field (`force_self` or `prefer_self`) that routes the request back to the originating Machine on failure, with a new `fly-replay-failed` request header carrying metadata about the failed replay attempt.

### April 2026
- **2026-04-06** — **Tigris public buckets served from dedicated content domains**: Public bucket objects are now served without authentication from dedicated domains (`https://<bucket>.t3.tigrisfiles.io/<key>`, plus `t3.tigrisbucket.io` and `t3.tigrisblob.io`), with custom domains configurable via `flyctl storage update <bucket> --custom-domain` and a CNAME record.
- **2026-04-08** — **New `--cachedrive-size` Machine flag**: `fly machine create/run/update` gained `--cachedrive-size` for attaching a cache drive (sized in MB), replacing the short-lived `--rootfs-fs-size` flag.
- **2026-04-15** — **Create a Machine with a volume from a snapshot in one command**: Docs added `fly scale count --with-new-volumes --from-snapshot <snapshot id> 1` for creating a Machine and a new volume populated from a volume snapshot in a single step.
- **2026-04-17** — **Docker Compose support for Fly Machines**: With flyctl v0.3.152+, an existing Docker Compose setup can be deployed directly via a new `[build.compose]` section in `fly.toml`; Fly builds and runs Compose services as containers within a single Machine, auto-detecting standard compose file names.
- **2026-04-20** — **Machine-scoped egress IPs formally deprecated with a migration path**: The egress IPs docs were rewritten around the deprecation, adding a new `fly machine egress-ip promote <machine-id>` command to "promote" existing machine-scoped egress IPs to app-scoped ones (keeping external allowlists unchanged, with possible brief downtime; promoted IPs retain the original machine's region). Allocation instructions and the proxy-pattern workaround were removed. Docs on Jun 9 further steered all users to app-scoped static egress IPs.
- **2026-04-28** — **Managed Postgres plan lineup renamed**: `fly mpg create --plan` now takes Basic, Starter, Launch, Scale, or Performance (previously "development, production, etc"), and `fly postgres create` gained a `--generate-name` flag.
- **2026-04-29** — **Tigris object-level ACLs, `t3.storage.dev` endpoint, and Tigris CLI**: Individual objects can now have their own ACLs (public objects in private buckets and vice versa). The Tigris docs were substantially reworked to document the `t3.storage.dev` endpoint, management via the Tigris CLI (`tigris login`) and the Tigris web console at `console.storage.dev`, access-key handling, and zero-downtime migration guidance (replacing the old shadow-buckets framing).
- **2026-04-30** — **`fly tokens create readonly` gains `--org` flag**: Read-only tokens can now target a specific Fly.io organization.

### May 2026
- **2026-05-01** — **Cross-network replays**: New `fly orgs cross-network-replays` command group (`status`, `enable`, `disable`) and a dashboard toggle let org admins allow `fly-replay` with `app=` to route requests across different private networks within the same organization (previously restricted to the same network).
- **2026-05-07** — **`fly mpg create --v2` flag**: Managed Postgres briefly gained a `--v2` flag to create clusters on the "V2 platform"; the flag was removed again on Jul 22.
- **2026-05-08** — **Autostop scale limit documented**: Docs now state that Fly Proxy's autostop loop runs every few minutes and stops at most one Machine per region per pass, making autostop/autostart unsuitable for apps with thousands of Machines (e.g. per-user dev environments) — the recommended pattern at scale is one app per user with dynamic routing, or self-shutdown when idle.
- **2026-05-29** — **Log search migrated from Quickwit to VictoriaLogs**: Fly's searchable-logs backend moved to a Fly-run VictoriaLogs instance (queried with LogsQL via Grafana); log retention dropped from ~30/15 days to 7 days. The app logs REST API docs were corrected to describe the JSON:API response format with `meta.next_token` cursor pagination (replacing the previously documented `start_time` param); log search remains free during beta.

### June 2026
- **2026-06-11** — **Tigris data transfer is now billed**: Extensions pricing docs removed "Bandwidth to Tigris Object Storage" from the free-data-transfer list; transfer to Tigris is billed under standard data transfer pricing.
- **2026-06-17** — **Metrics retention, cost, limits, and alerting documented**: Managed Prometheus retains metric data ~15 days and remains free (with advance notice promised before any pricing change); Fly.io has no built-in metrics alerting, so users must alert against the Prometheus endpoint themselves. A follow-up (Jun 22) corrected the per-Machine metrics scrape limit from 16 KiB to 16 MB.
- **2026-06-19** — **Billing preauthorization terms changed**: Card pre-authorization holds after signup are now "usually less than US $10" (previously $5) and may be visible for up to 10 business days (previously 7 days).
- **2026-06-25** — **`fly wireguard token` commands removed**: The entire `fly wireguard token` command group (create/delete/list/start/update) was removed from flyctl, replaced by a new `fly tokens create wireguard` command under the unified tokens system.

### July 2026
- **2026-07-06** — **New `--build-context-warn-size` build flag**: `fly deploy`, `fly launch`, and `fly console` gained a flag (also settable via `FLY_BUILD_CONTEXT_WARN_SIZE`) to warn when the Docker build context exceeds a given size.
- **2026-07-13** — **MySQL and Supabase extensions removed from flyctl**: The `fly mysql` command group, `fly extensions mysql`, and all `fly extensions supabase` commands (dashboard/destroy/list/status) were deleted from the CLI — removal of the managed MySQL extension and the Supabase Postgres extension tooling.
- **2026-07-14** — **`fly apps list` shows network names**: Apps on a non-default private network now display the network name in listings.
- **2026-07-22** — **`fly logs` machine filtering improvements**: The `--machine` filter gained a `-m` shorthand and a new `-s`/`--select` flag to pick a Machine from an interactive list; docs updated from instance-based to machine-based filtering language.
- **2026-07-23** — **`fly machine run --shell` app lifecycle change**: Interactive shells no longer create and destroy a temporary app per Machine; instead an app for interactive shells is created once and reused — the Machine is destroyed when the shell exits, but the app is retained for future shells.

## 2025

### January 2025
- **2025-01-08** — **Support access changes and scope-of-support policy**: Docs updated to state that ticket-based support (email + new self-service Support Portal in the dashboard) is available to organizations with a Standard, Premium, or Enterprise Support package or legacy Launch/Scale plans; billing/account email support remains open to everyone. A follow-up on 2025-01-09 added an explicit "Scope of Support" matrix listing which products Fly.io actively supports, with notes added to the LiteFS, monitoring, and (unmanaged) Postgres pages.
- **2025-01-08** — **Supabase Postgres integration wind-down begins**: Supabase was removed as a "fully managed provider" option in the Postgres docs, and remaining Supabase docs content was stripped out on 2025-01-31, foreshadowing the extension's deprecation.
- **2025-01-16** — **`min_machines_running` behavior clarified**: A warning was added to the autostop/autostart docs stating that `min_machines_running` only maintains minimum running Machines in the app's *primary region* and has no effect in other regions (use `fly scale count` per-region instead).
- **2025-01-20** — **New Prisma and Shopify guides**: New doc pages for running Prisma ORM apps on Fly.io (with Postgres and SQLite variants) and for hosting Shopify apps on Fly.io.

### February 2025
- **2025-02-05** — **GPU region availability reduced**: The `a100-80gb` GPU availability list changed from `ams`, `iad`, `mia`, `sjc`, `syd` to `iad`, `sjc`, `syd` (Amsterdam and Miami dropped).
- **2025-02-07** — **Supabase Managed Postgres extension deprecated**: A deprecation notice was added to the Supabase extension docs pointing users at the Supabase-side deprecation of Fly Postgres.
- **2025-02-19** — **`fly managed-postgres` commands appear in flyctl**: The flyctl docs sync added the new `fly managed-postgres` command group with `connect` and `proxy` subcommands — the first CLI surface for the upcoming Managed Postgres product.
- **2025-02-25** — **Managed Postgres (MPG) docs launched**: A new `/mpg` docs section (index + overview) was added for Fly.io Managed Postgres, the fully managed Postgres product, including a flyctl usage section — marking MPG's initial (preview) availability.

### March 2025
- **2025-03-18** — **Wafris flyctl extension docs removed**: The `fly extensions wafris` command docs (create/dashboard/destroy) were removed from the flyctl extensions documentation.

### April 2025
- **2025-04-02** — **Per-user dev environments (sandboxes) blueprint**: New blueprint "Per-User Dev Environments with Fly Machines" documenting how to build per-user sandboxes/dev environments on Fly Machines.
- **2025-04-03** — **Comprehensive health checks reference**: A completed Health Checks doc covering top-level checks, service-level checks, and machine checks, and clarifying that failing checks stop request routing but do not auto-restart Machines.
- **2025-04-07** — **Tigris data transfer no longer free**: Docs removed the statement that data transfer to Tigris Object Storage is free.
- **2025-04-13** — **`fly mcp` command group launched**: flyctl gained a new `fly mcp` command family (`mcp proxy`, `mcp server`, `mcp wrap`) for running and proxying Model Context Protocol servers, alongside a new "Deploying Remote MCP Servers" blueprint (2025-04-11).
- **2025-04-16** — **Managed Postgres soft launch (Technical Preview)**: MPG docs updated for soft launch: labeled "Technical Preview, suitable for production workloads," with automatic backups/recovery, HA with automatic failover, monitoring, encryption at rest/in transit, the `pgvector` extension, three plans (Launch: 2 vCPU/4GB, Performance: 4 vCPU/8GB, Enterprise: 8 vCPU/16GB), and up to 500GB storage at creation. On 2025-04-29 the "tech preview" copy was removed and plans corrected, and `fly managed-postgres create` (plus `list`/`status` on 2025-04-24 and `attach` on 2025-04-07) landed in flyctl.
- **2025-04-22** — **`fly-replay-cache` for Fly Proxy dynamic request routing**: New docs for the `fly-replay-cache` response field, which lets apps cache replay decisions in Fly Proxy so subsequent matching requests are routed without an extra replay hop. Also added: a "one app per user" explainer blueprint on the platform's app-per-tenant isolation model.

### May 2025
- **2025-05-01** — **Machine states/lifecycle documentation rewritten**: The Machine states page was rewritten with the full Machine lifecycle state diagram and versioning details.
- **2025-05-07** — **Regions overhaul: more WireGuard gateways, edge-only regions removed**: `arn` (Stockholm), `bom` (Mumbai), `ewr` (Secaucus), `gdl` (Guadalajara), and `qro` (Querétaro) were marked as gateway regions, and the separate "Edge-only regions" concept/table was removed from the regions reference.
- **2025-05-09** — **Model Context Protocol (MCP) docs section**: A new MCP documentation section was built out through May–June covering deploying remote MCP servers on Fly Machines, transports (SSE/HTTP streaming), access control (HTTP authorization, Flycast, reverse proxy), and the flyctl MCP server. In parallel, flyctl gained `fly mcp launch`, `add`, `remove` (2025-05-15), `destroy`, `inspect` (2025-05-17), `list` (2025-05-21), and `logs` (2025-05-24).
- **2025-05-14** — **Base images blueprint**: New blueprint "Using base images for faster deployments" on prebuilding base Docker images to speed up deploys. A "Setting Hard and Soft Concurrency Limits" blueprint followed on 2025-05-15.
- **2025-05-15** — **A100-80GB GPUs back in Amsterdam**: The `ams` region was re-added to the `a100-80gb` GPU availability list.
- **2025-05-22** — **Network Policies for Fly Machines**: New guide documenting network policies to restrict Machine traffic (e.g., limiting egress to HTTP/HTTPS) with selectors, rules, and an API summary.
- **2025-05-23** — **"Connecting to User Machines" blueprint and `fly-replay` auth guidance**: New blueprint for connecting public and management services to user apps (multi-tenant platforms), including using `fly-replay` and replay-source authentication; redundant fly-replay content was consolidated.
- **2025-05-26** — **Observability for User Apps**: New guide for platform builders covering the Fly Telemetry Forwarder, streaming Fly app logs to end users, and building a central log-router service.
- **2025-05-27** — **Fly.io private Docker registry guide**: New guide for using `registry.fly.io` directly to build, tag, push, and deploy images across apps. (On 2025-07-14 docs noted that `fly auth docker` registry tokens expire after 5 minutes.)
- **2025-05-28** — **`fly machine place` command**: New flyctl command that simulates a batch of Machine placements across multiple regions to preview where Machines would land.

### June 2025
- **2025-06-02** — **Volume and root-filesystem I/O limits documented**: New "Volume limits" section giving max IOPS/bandwidth per Machine type (e.g., shared-cpu-1x/2x: 4000 IOPS / 16MiB/s; shared-cpu-4x: 8000 IOPS / 32MiB/s), and documenting that ephemeral root filesystems are capped at 2000 IOPS and 8MiB/s regardless of Machine type.
- **2025-06-10** — **AWS-to-Fly.io migration guide**: New overview guide for migrating apps from AWS, walking through architectural differences and deployment-model adjustments.
- **2025-06-13** — **Multi-container Machines**: New doc for running multiple containers in a single Fly Machine, covering sidecar use cases, container definitions, dependencies, health checks, and example configuration.
- **2025-06-18** — **8GB image size limit documented**: Docs added the deployment failure explanation for the 8GB uncompressed rootfs limit on non-GPU Machines (GPU Machines get 50GB), with workarounds via volumes or object storage.
- **2025-06-18** — **Fly Proxy content encoding**: New reference doc "Content Encoding with the Fly Proxy" describing how the proxy handles HTTP response compression.
- **2025-06-20** — **Machine placement and regional capacity guidance**: New doc explaining all-or-nothing scaling behavior when a region lacks capacity, checking available CPU cores with `fly platform regions`, and giving the scheduler prioritized region lists or geographic groups for `fly machine clone`/create.
- **2025-06-23** — **Upstash Kafka removed**: All mentions of the Upstash Kafka extension were removed from the docs (product discontinued).
- **2025-06-24** — **`fly-replay-cache` works without a domain**: Replay-cache path patterns no longer require an explicit domain; the cached replay is scoped to the request domain by default.
- **2025-06-26** — **Seamless deployments guide**: New guide "Seamless Deployments on Fly.io" on achieving zero-downtime deploys via health checks and deploy strategies.

### July 2025
- **2025-07-03** — **App handover guide**: New guide for agencies/consultants on transferring apps between Fly.io organizations, covering both develop-in-their-org and build-then-move workflows.
- **2025-07-09** — **`[[statics]]` behavior clarified**: Statics docs rewritten to explain the two modes of serving static assets — from a static file server inside the running Machine (Machine must be running; autostart applies) or from Tigris object storage — replacing the old description of proxy/worker-host delivery.
- **2025-07-11** — **Managed Postgres docs expansion**: New MPG pages for creating and connecting to clusters (dashboard and flyctl), supported Postgres extensions, and importing existing databases; WireGuard connection instructions followed on 2025-07-22.
- **2025-07-14** — **`fly certs setup` command**: New flyctl command that shows DNS setup instructions for a hostname's certificate; custom-domain certificate docs were refreshed alongside.
- **2025-07-16** — **Understanding Cloudflare guide**: New guide on running Fly.io apps behind Cloudflare, plus a callout (2025-07-17) about the Cloudflare Universal SSL "ghost records" issue breaking ACME validation.
- **2025-07-17** — **Work queue and task scheduling guides**: New guide on deferring long-running tasks to a distributed work queue (Celery, on-demand Fly Machines workers, Redis/Valkey), and a task scheduling guide (2025-07-18) covering Cron Manager, Supercronic, scheduled Machines, and in-app scheduling.
- **2025-07-22** — **LiteFS Cloud fully deprecated in docs**: LiteFS Cloud was removed from navigation with wording confirming the product was retired on October 15, 2024 (open-source LiteFS unaffected).
- **2025-07-23** — **MPG connection pool mode configuration**: New docs for configuring PgBouncer `pool_mode` (session vs. transaction) on Managed Postgres clusters from the dashboard.
- **2025-07-24** — **Static egress IPs repriced/repackaged**: The "Static Machine IP" pricing section became "Static Egress IPs for Machines": $0.005/hour (~$3.60/month) now buys a dedicated outbound IPv4 + IPv6 pair per Machine.
- **2025-07-25** — **`fly-replay-delete-header` documented**: New Fly Proxy capability letting a replaying app instruct the proxy to delete request headers before replaying, with notes on interaction with replay caching.
- **2025-07-29** — **Free allowances limited to legacy plans**: Billing docs reworked to clarify that free resource allowances apply only to legacy (pre-October 2024) plan users, with clarified language around the deprecated $5 Hobby plan and one-time free trial credit.
- **2025-07-31** — **MPG regions roadmap**: Docs listed `ams`, `nrt`, `sin`, and `sjc` as "coming soon" Managed Postgres regions.

### August 2025
- **2025-08-01** — **JSON body syntax for `fly-replay`**: Dynamic request routing docs updated to describe `fly-replay` as a response (header or JSON body format), not just a header — the start of a series of replay-routing feature docs.
- **2025-08-04** — **Organization roles and permissions doc**: New security doc detailing what Members and Admins can each do in a Fly.io organization.
- **2025-08-05** — **Machines API: `volume_count` on app list**: The `apps_list` endpoint now returns a `volume_count` field per app. Also added: a guide to building infrastructure automation without Terraform (flyctl + GitHub Actions vs. the Machines API).
- **2025-08-06** — **`fly ips allocate` command**: New flyctl command that allocates the recommended set of IP addresses for an app in one step.
- **2025-08-11** — **Managed Postgres pricing chart**: The Postgres overview gained an MPG pricing chart alongside plan details.
- **2025-08-15** — **Machine Suspend/Resume reference**: New reference doc for Machine suspend — pausing a running Machine with full state (including memory) saved to persistent storage, resuming in hundreds of milliseconds instead of a full boot. A follow-up (2025-09-04) documented that a Machine can suspend *itself* token-free via the `/.fly/api` Unix socket.
- **2025-08-19** — **Preferred-instance routing**: New docs for routing to specific Machines: `prefer_instance` in `fly-replay`, client-set `fly-prefer-instance-id` and `fly-force-instance-id` request headers, and the `fly-preferred-instance-unavailable` fallback header.
- **2025-08-19** — **MPG cluster configuration doc**: New "Cluster configuration options" page covering connection pooling modes, changing MPG plans, and users/roles (Schema Admin vs. Writer permissions).
- **2025-08-22** — **Rollback guide and `--max-unavailable` change**: New rollback guide (how to roll back deploys, image retention). Separately, `fly deploy --max-unavailable` is now expressed as a float (e.g., `0.5`) instead of a percentage.
- **2025-08-29** — **Secrets mountable as files**: Secrets docs overhauled with a new section on mounting secrets as files on the Machine filesystem at startup via the `[[files]]` section in `fly.toml` (base64-encoded values). Also added: a "Getting Started with N-Tier Architecture" guide.

### September 2025
- **2025-09-05** — **MPG monitoring and metrics dashboard**: New "Monitoring and Metrics" doc for the Managed Postgres performance-monitoring dashboard.
- **2025-09-09** — **`fly-replay` region syntax expanded**: Replay routing now accepts comma-separated region preference lists, geographic groups (e.g., `apac`), and an `any` fallback (e.g., `fly-replay: region="sjc,any"`), combinable with `app=`. Same day, flyctl gained `fly sftp put` / `fly ssh sftp put` for uploading files to a Machine.
- **2025-09-10** — **MPG region expansion live**: `ams`, `nrt`, `sin`, and `sjc` moved from "coming soon" to available Managed Postgres regions (joining `fra`, `gru`, `iad`, `lax`, `ord`, `syd`).
- **2025-09-11** — **Replay cache bypass controls**: New docs for `fly-replay-cache-control` and `fly-replay-cache-status` headers plus the `allow_bypass` field, letting clients skip a cached replay without invalidating it.
- **2025-09-12** — **Resiliency and volumes updates**: The "Resiliency for your apps" guide was overhauled with multi-region guidance; a new guide covered using Fly Volume forks to preload data for faster startups; and rate-limit docs noted app deletions are capped at 100/minute.
- **2025-09-16** — **Machine shutdown sequence documented**: Runtime config reference updated with the full controlled-shutdown sequence (`kill_signal` then `kill_timeout` then forced shutdown) for `fly deploy`, `fly machine stop`, and autostop, with a warning that `kill_timeout` is best-effort. A Phoenix-with-MPG guide also landed the same day.
- **2025-09-24** — **`persist_rootfs` Machine option**: New Machine config option to persist the root filesystem across restarts and updates, with values `never` (default), `restart`, and `always`, documented in both the Machines API config and `fly.toml` references.
- **2025-09-29** — **`fly secrets sync` command**: New flyctl command to sync local flyctl state with the latest versions of app secrets set elsewhere.

### October 2025
- **2025-10-01** — **Configurable automatic volume snapshots**: New `auto_backup_enabled` volume flag in the Machines API and `scheduled_snapshots` option in `fly.toml` `[mounts]` (2025-10-02) to enable/disable automatic daily snapshots, alongside the existing `snapshot_retention` (1–60 days, default 5).
- **2025-10-01** — **Instance exit metrics**: New `fly_instance_exit_*` metrics documented for understanding and alerting on why Machines terminate.
- **2025-10-01** — **Logs API doc and Enveloop removal**: New "Logs API options" doc for programmatic log access (including the unofficial NATS log proxy); the deprecated Enveloop extension docs were removed (deprecation warning added 2025-09-02).
- **2025-10-02** — **Egress IPs networking doc**: New networking page consolidating egress IP behavior, machine-scoped static egress IPs, and the NAT/proxy pattern.
- **2025-10-07** — **MPG becomes the recommended Postgres**: Unmanaged Fly Postgres (UPG) pages were updated to recommend Managed Postgres instead.
- **2025-10-09** — **7-day free trial introduced**: New "Fly.io 7-day Free Trial" page describing trial resource limits, trial-status tracking in the dashboard, and apps stopping when the trial is exhausted until a payment method is added. Updated messaging on 2025-10-28: the trial is 2 total VM hours or 7 days (whichever comes first), and trial Machines auto-stop after 5 minutes of runtime.
- **2025-10-14** — **New Managed Postgres plans**: MPG plan lineup expanded, now spanning from a Starter plan (2 shared vCPUs, 2GB RAM) up to Performance-8x (8 performance vCPUs, 64GB RAM, $1,922/month).
- **2025-10-16** — **Volume snapshot storage pricing announced**: Starting January 1, 2026, volume snapshot storage will be billed (pro-rated hourly, free allowance subtracted); snapshots are stored incrementally so only changed data is charged. The pricing page was also cleaned up the same day.
- **2025-10-16** — **Deprecated regions removed**: The regions reference dropped a large set of retired regions including `atl`, `bog`, `bos`, `den`, `eze`, `gdl`, `gig`, `hkg`, `mad`, `mia`, `otp`, `phx`, `qro`, and `scl`; remaining references across the docs were cleaned up on 2025-10-17.
- **2025-10-20** — **MPG backup and restore commands**: flyctl gained `fly mpg backup create`, `fly mpg backup list`, and `fly mpg restore` for Managed Postgres.
- **2025-10-23** — **Cost management guide**: New "Cost Management on Fly.io" doc on predicting bills and avoiding surprise charges.
- **2025-10-24** — **Session-based replay caching (sticky sessions) documented**: New docs comparing client-side `fly-force-instance-id` and server-side `fly-replay` approaches for routing session-affine requests to specific Machines.
- **2025-10-28** — **Internal DNS: `all.` prefix and stopped-Machine behavior**: Docs added the `all.`-prefixed `.internal` DNS names and split the internal DNS table, clarifying that AAAA queries for `.internal` domains return only started (running) Machines — stopped/autostopped Machines are excluded.

### November 2025
- **2025-11-10** — **MPG database and user management via flyctl**: New `fly mpg databases` (create/list) commands, followed by `fly mpg users` (create/delete/list/set-role) on 2025-11-11, with an accompanying guide (2025-11-26) on creating databases via dashboard and flyctl and managing users via flyctl.
- **2025-11-25** — **`fly-force-region` header**: New replay routing header that routes strictly to the listed region(s) with no nearest-region fallback (unlike `fly-prefer-region`), supporting ordered multi-region lists.
- **2025-11-28** — **Egress IP allocation commands**: flyctl gained `fly ips allocate-egress` and `fly ips release-egress` (the CLI surface for December's app-scoped egress IP launch).

### December 2025
- **2025-12-02** — **App transfer via dashboard UI**: Moving an app between organizations can now be done from the App Settings page in the dashboard, in addition to the CLI; the app handover guide was updated accordingly.
- **2025-12-04** — **MPG inter-region bandwidth charges announced**: Starting February 2026, Managed Postgres inter-region private network usage will be charged at the same data-transfer rate as Machines (same free quota; same-region transfer stays free).
- **2025-12-05** — **Custom deploy workflows guide**: New guide on taking control of deployment flow — staggered/selective deploys, avoiding Machine restarts, and handling partial rollout failures. A "Working with Docker on Fly.io" guide followed on 2025-12-12.
- **2025-12-12** — **First 10 single-hostname certificates free**: Certificate pricing updated so every organization's first 10 non-wildcard (single hostname) TLS certificates are free.
- **2025-12-15** — **MPG regions: London and Toronto**: `lhr` (London) and `yyz` (Toronto) added to the available Managed Postgres regions.
- **2025-12-18** — **App-scoped static egress IPs**: New feature: allocate static egress IPv4+IPv6 pairs per app per region with `fly ips allocate-egress`, shared across all of an app's Machines in that region and persistent across Machine recreation. Priced at $3.60/month per IPv4 (IPv6 free), with a 1,024 concurrent connections per destination IP limit per Machine; legacy machine-scoped static egress IPs remain but are no longer recommended.
- **2025-12-19** — **Cross-organization `fly-replay` routing**: `fly-replay` with `app=` can now route to apps in *other* organizations via a per-org allowlist of replay sources, managed with the new `fly orgs replay-sources` commands (`add`/`list`/`remove`, added 2025-12-18).

## 2024

### January 2024
- **2024-01-05** — **Switch from dedicated to shared IPv4**: Docs added instructions for switching an app from a dedicated IPv4 back to a free shared IPv4 address (allocate with `fly ips allocate-v4 --shared`, then release the dedicated IP), reflecting new flexibility in Anycast IP management.
- **2024-01-09** — **Smoke checks on deploy**: `fly deploy` now runs "smoke checks" against newly deployed Machines — if a Machine crashes right after deployment, the deploy fails and the error surfaces in troubleshooting output.
- **2024-01-10** — **Wildcard certificates no longer require a dedicated IP**: Docs removed the requirement to purchase a dedicated IPv4/IPv6 address to use wildcard TLS certificates (reaffirmed again on 2024-04-23).
- **2024-01-10** — **Mixing Fly Launch–managed and unmanaged Machines supported**: Docs added a note (and on 2024-01-17 removed the old warning) confirming an app can now contain both `fly deploy`-managed Machines and unmanaged Machines created via `fly machine run`/Machines API.
- **2024-01-11** — **Fly Kubernetes (FKS) quickstart**: First quickstart docs for Fly Kubernetes Service, Fly.io's managed Kubernetes running on Fly Machines (closed beta, cluster creation via `fly ext k8s create`).
- **2024-01-15** — **On-demand volume snapshots**: flyctl gained `fly volumes snapshots create` (v0.1.142) and docs for creating volume snapshots on demand, in addition to the automatic daily snapshots; restoring from snapshots documented alongside.
- **2024-01-15** — **flyctl command deprecations**: `fly history` documented as deprecated, and doc pages for the removed `fly regions`, `fly monitor`, and `fly vm` commands were deleted (2024-01-16), completing the Nomad-era command cleanup.
- **2024-01-18** — **Supabase Postgres on Fly.io (private beta)**: Docs for the new Supabase managed Postgres extension, provisioned via flyctl with low-latency access from Fly.io regions; one free resource-limited database per user, then pay-as-you-go on the Supabase Pro plan.
- **2024-01-19** — **Tigris object storage (beta)**: New `reference/tigris` doc page for Tigris, the S3-compatible global object storage extension, added to navigation (provisioned via `fly storage create`).
- **2024-01-23** — **Postgres snapshot retention change**: Daily Postgres volume snapshots retention documented as 5 days (previously stated as 7 days).
- **2024-01-24** — **Rootfs pricing for stopped Machines**: Pricing and billing pages documented the new charge for stopped Machines' root file systems: $0.15 per GB of rootfs per 30 days stopped.
- **2024-01-28** — **Paid Hobby plan for new accounts**: Pricing page reworked to reflect that new accounts start on the $5/month paid Hobby plan (with a one-time $5 free trial credit), replacing the old free Hobby plan for new sign-ups.

### February 2024
- **2024-02-02** — **Tigris shadow buckets and AWS API compatibility**: Docs added for Tigris "shadow buckets" (transparently migrate/pull objects from an existing S3 bucket) and detailed AWS S3 API compatibility; flyctl gained `fly storage update`/`fly storage status` (2024-02-06).
- **2024-02-08** — **Upstash Redis moves to pay-as-you-go pricing**: All new Upstash Redis databases run on PAYG pricing ($0.02 per 100K commands) instead of fixed plans.
- **2024-02-12** — **GPUs no longer require a paid plan**: Pricing page updated to remove the paid-plan requirement for creating GPU Machines.
- **2024-02-14** — **Tigris goes GA**: Beta warnings removed from Tigris object storage docs ("Take Tigris to production").
- **2024-02-14** — **Multi-GPU Machines**: New `gpus = N` setting documented in the fly.toml `[[vm]]` section for attaching multiple GPUs to a single Machine.
- **2024-02-19** — **Machine sizing via fly.toml `[[vm]]` section**: Scaling docs updated to cover setting Machine CPU/memory (`size`, `memory`, `cpus`, etc.) declaratively in fly.toml instead of only via `fly scale` commands.
- **2024-02-29** — **Machines API metadata filter**: The list-Machines endpoint now supports filtering by metadata (`metadata.{key}` query parameter).

### March 2024
- **2024-03-01** — **FKS beta expansion**: Fly Kubernetes docs grew substantially: new cluster-management page (`kubernetes/clusters`), persistent volumes support via PVCs, FKS pricing added to the pricing page, and a new Kubernetes docs section; follow-ups documented supported/unsupported features (2024-03-06), Services of type LoadBalancer (2024-03-08), service concurrency configuration (2024-03-11), cluster connection docs (2024-04-11), and GPU support in FKS via the `gpu.fly.io/<type>` resource (2024-04-15).
- **2024-03-05** — **SOC 2 Type 2**: Security and healthcare pages updated from SOC 2 Type 1 to Type 2 attestation.
- **2024-03-11** — **Kafka on Fly.io (private beta)**: New docs for managed Kafka clusters (`reference/kafka`), with `fly extensions kafka create/list/status/update/destroy/dashboard` commands landing in flyctl (synced 2024-03-09).
- **2024-03-11** — **Upstash Redis discount deprecations**: Docs removed mention of the Sidekiq and empty-response command discounts, which Upstash is deprecating.
- **2024-03-20** — **Per-second GPU billing**: Billing docs updated: GPUs are billed per second the attached Machine is running (in `started` state), separately from the Machine itself.
- **2024-03-27** — **`autostop`/`autostart` naming**: Machine API/CLI settings renamed from `auto_stop`/`auto_start` to `autostop`/`autostart` in Machine config docs.

### April 2024
- **2024-04-03** — **Review apps guide**: New guide for spinning up per-PR review apps on Fly.io using GitHub Actions.
- **2024-04-15** — **`swap_size_mb` replaces manual swapfiles**: Docs replaced hand-rolled swapfile instructions with the fly.toml `swap_size_mb` option for enabling swap on Machines.
- **2024-04-15** — **New scoped deploy tokens**: flyctl docs synced `fly tokens create ssh` (SSH-only tokens), followed by `fly tokens create machine-exec` (Machine command-execution tokens) on 2024-04-23.
- **2024-04-16** — **`http_options.response.pristine` flag**: New fly.toml service option that stops Fly Proxy from adding/modifying HTTP response headers, leaving responses untouched.
- **2024-04-17** — **Fly Proxy error codes reference**: New `reference/error-codes` page documenting all proxy-generated error codes returned via the `fly-request-id` header, for debugging failed requests.
- **2024-04-19** — **Supabase Postgres public beta**: Supabase managed Postgres moved from private to public beta.
- **2024-04-20** — **Default volume size reduced**: Default Fly Volume size changed from 3 GB to 1 GB.
- **2024-04-22** — **Cross-region volume forks**: `fly volumes fork` can now copy a volume into a different region using the `--region` flag.
- **2024-04-26** — **Kafka public beta**: Managed Kafka clusters moved from private to public beta.
- **2024-04-26** — **`vm.kernel_args` option**: New fly.toml `[vm]` setting to pass custom kernel arguments to a Machine's guest kernel.
- **2024-04-29** — **OpenID Connect (OIDC) tokens for Machines**: New docs for workload identity: Machines can fetch signed OIDC identity tokens (e.g., to authenticate to AWS via role assumption without static credentials).
- **2024-04-29** — **Upstash Redis fixed-price plans**: Alongside PAYG, new fixed-price plans documented (Starter $10/mo, Standard $50/mo per region, Pro 2K $280/mo), selectable via `fly redis update`, recommended for high-polling workloads like Sidekiq/BullMQ.
- **2024-04-30** — **Nvidia A10 GPUs**: A10 cards added to GPU docs, quickstart, FKS GPU docs, and pricing.

### May 2024
- **2024-05-03** — **Volume snapshot retention control**: New `snapshot_retention` setting in fly.toml `[mounts]` and a new "update volume" Machines API endpoint documented; the snapshots API gained a `retention_days` field (2024-05-09).
- **2024-05-06** — **Upstash Vector**: New docs for the Upstash Vector extension (managed vector database for AI/embeddings workloads), with `fly extensions vector` commands synced to flyctl on 2024-05-01.
- **2024-05-08** — **HIPAA compliance offering**: New "Going to Production with HIPAA Apps" doc and a reworked healthcare page describing running HIPAA-compliant apps on Fly.io (BAAs, hard tenant isolation).
- **2024-05-28** — **`machine_checks` in fly.toml**: New deploy-time check type that spawns a test Machine and verifies it (running a command against the new image) before continuing the deployment — especially useful for canary deploys.
- **2024-05-31** — **Free allowances restricted**: Free resource allowances are no longer given to free-trial organizations, only to organizations on a paid plan.

### June 2024
- **2024-06-05** — **`fly incidents` commands**: flyctl gained `fly incidents list` (and `fly incidents hosts list` on 2024-06-10) for viewing platform/host incidents affecting your apps.
- **2024-06-11** — **Machine restart policy in fly.toml**: New `[restart]` section documented (`policy = "always" | "never" | "on-failure"`, `retries`) for configuring Machine restart behavior declaratively.
- **2024-06-17** — **Pay As You Go plan launched**: New organizations now start on the Pay As You Go plan (pure usage-based, no monthly subscription) instead of the $5/month Hobby plan; Hobby became legacy. Billing page updated for PAYG on 2024-06-21.
- **2024-06-19** — **Machine migration documented**: New reference page describing how Fly.io automatically migrates Machines between hosts (for maintenance/deprecation/overcrowding), including volume forking to the destination host and Machine ID preservation.
- **2024-06-19** — **Arcjet extension**: New docs for the Arcjet application-security extension (rate limiting, bot detection, email validation, attack protection), with `fly extensions arcjet` commands synced 2024-06-10.
- **2024-06-20** — **fly-autoscaler (metrics-based autoscaling)**: New docs for the fly-autoscaler tool that polls metrics (e.g., Prometheus queries) and automatically creates/starts Machines to match demand, plus a reference autoscaling page distinguishing pre-allocated (Fly Proxy autostart/autostop) vs metrics-based autoscaling.
- **2024-06-20** — **No more default `hard_limit`**: Service concurrency defaults changed — `soft_limit` defaults to 20 and `hard_limit` is now unlimited when unset (previously a hard limit default applied).
- **2024-06-27** — **`fly-force-instance-id` header**: New dynamic request routing header documented for forcing Fly Proxy to route a request to a specific Machine (basis for sticky sessions).
- **2024-06-28** — **Per-region Machines pricing**: Machines compute pricing became per-region, with a phased rollout starting July 1 (prices ramping 25% per month toward listed regional prices through November); pricing page gained per-region price tables.

### July 2024
- **2024-07-01** — **Machines API rate limits published**: Documented limits of 1 req/s per action per Machine (burst 3 req/s), with Get Machine allowed 5 req/s (burst 10 req/s).
- **2024-07-02** — **Hobby plans discontinued**: The paid $5/month Hobby plan and Legacy Hobby plan closed to new sign-ups; new organizations go on Pay As You Go.
- **2024-07-03** — **Enveloop extension**: New docs for the Enveloop managed email/messaging extension (`fly extensions enveloop` commands synced 2024-05-04).
- **2024-07-15** — **Regions page overhaul**: Regions doc updated to 38 regions with per-region gateway (WireGuard) indicators and plan-restricted regions (e.g., `bom` and `fra` requiring Launch plan or higher).
- **2024-07-16** — **`fly apps move`**: New docs for moving an entire app (with its resources) between organizations via `fly apps move <app> --org <target>`.
- **2024-07-17** — **New bandwidth/egress pricing**: Granular data transfer pricing introduced for organizations created after July 18, 2024: per-region-group internet egress rates ($0.02/GB NA-EU up to $0.12/GB Africa/India), cheaper private-network cross-region rates ($0.006–$0.05/GB), free same-region transfer, and free transfer to Tigris. Pre-existing orgs could opt in starting 2024-08-01.
- **2024-07-17** — **LiteFS Cloud sunset**: Sunsetting banner added across LiteFS docs — LiteFS Cloud (managed backups/restore for LiteFS) deprecated, with Litestream-based alternatives documented on 2024-07-29.
- **2024-07-18** — **Serve statics from Tigris**: fly.toml `[[statics]]` gained `tigris_bucket` and `index_document` options, letting Fly Proxy serve static assets directly from a Tigris object storage bucket, including index-document support.
- **2024-07-22** — **Machine reservation blocks**: New 40% discount for prepaying annual blocks of compute in a region ($36–$3,600/yr for shared, $144–$14,400/yr for performance Machines), granted as monthly credits.
- **2024-07-26** — **Machine suspension (suspend/resume)**: New `suspended` Machine capability documented: suspend Machines API endpoint, `fly machine suspend` (CLI synced 2024-06-17), and `autostop = "suspend"` so Fly Proxy suspends instead of stops idle Machines for much faster snapshot-based resume. Suspended Machines billed the same as stopped ones (clarified 2024-08-19).

### August 2024
- **2024-08-02** — **New flyctl extension and Postgres commands**: Docs sync added `fly mysql` / `fly extensions mysql` (managed MySQL extension), `fly extensions wafris` (Wafris web application firewall), `fly extensions kubernetes` (FKS cluster management incl. `save-kubeconfig`), `fly postgres backup` (config/create/restore — new barman-based Postgres backups), and `fly synthetics` (synthetic monitoring agent) command sets.
- **2024-08-12** — **`idle_timeout` HTTP option**: New `http_options.idle_timeout` setting documented for `[http_service]` and `[services.ports]` to configure the idle timeout for connections to your app.
- **2024-08-15** — **Unified Billing**: New billing feature allowing multiple organizations to consolidate under one Billing Organization with a single invoice and shared credits; Linked Organizations capped at 100 per Billing Org, with docs for converting existing orgs added 2024-08-29.
- **2024-08-15** — **L40S GPU price cut**: L40S price reduced to $1.25/hr on the pricing page.
- **2024-08-16** — **Custom private networks**: New `networking/custom-private-networks` doc covering isolating apps on custom 6PN networks (via `--network` flag / network config) instead of the default org network.
- **2024-08-27** — **Volume auto-extend clarified**: Documented that `auto_extend_size_limit` must be set (along with threshold/increment) for automatic volume extension to work.

### September 2024
- **2024-09-24** — **Static egress IPs for Machines**: New feature documented with pricing: attach a static egress (outgoing) IPv4/IPv6 to a Machine via `fly machine egress-ip allocate` for IP-allowlisted external services; $0.005/hr, survives Machine migration (CLI commands `allocate`/`list` synced same day; `release` added 2024-10-03).

### October 2024
- **2024-10-07** — **Plans sunset — usage-based billing for everyone**: Legacy plans (Hobby, Launch, Scale, Enterprise) deprecated as of October 7, 2024; existing plan customers grandfathered, all new customers/organizations billed purely on resource usage. Pricing/billing pages restructured and the regions page dropped plan-gating details.
- **2024-10-14** — **CPU performance and quotas documented**: New `machines/cpu-performance` page detailing shared vs performance vCPU scheduling: 80ms periods, shared vCPUs at a 5ms (1/16th) baseline quota, performance at 50ms (10/16th), burst balances (up to 500s/5000s), cgroup-based throttling, and new throttle/steal metrics in Managed Grafana.
- **2024-10-22** — **Performance vCPUs get 100% quota**: Behavior change — `performance` vCPUs now get 100% CPU quota (80ms/80ms, effectively no throttling), up from the previous 10/16 baseline; shared vCPUs stay at 6.25%.

### November 2024
- **2024-11-27** — **`[deploy.release_command_vm]`**: New fly.toml section to explicitly size the temporary Machine that runs your release command (e.g., `size = "performance-1x"`, `memory = "8gb"`).

### December 2024
- **2024-12-17** — **Canary deploys restricted with volumes**: Deploy strategy docs updated to state the `canary` strategy cannot be used for Machines with attached volumes (matching the existing `bluegreen` restriction).

## 2023

### January 2023
- **2023-01-09** — **`fly-prefer-region` request header and regional routing revamp**: The fly-replay docs were rewritten as "Regional Request Routing" and now document the new `fly-prefer-region` request header, which lets clients ask Fly Proxy to send a request directly to a desired region (useful for large uploads where `fly-replay` can't buffer/replay). A 1MB request size limit for `fly-replay` was also documented (2023-01-11).
- **2023-01-10** — **External port ranges for services**: `fly.toml` `[[services.ports]]` gained `start_port`/`end_port`, letting a single service definition listen on a whole range of external ports instead of one port per block.
- **2023-01-20** — **Machines/Apps V2 config additions documented**: New docs for the `[metrics]` section, the `[http_service]` section (a simplified HTTP service config for Machines-based apps), health `checks` in the Machines API create/update requests, and an experimental `exec` option for overriding the container entrypoint.

### February 2023
- **2023-02-10** — **Paid-plan-only regions**: The regions table now marks higher-demand regions (Frankfurt `fra` and Chennai `maa`) as requiring a paid plan to scale up VMs — a new platform restriction on free usage in constrained regions.
- **2023-02-16** — **Machines API HTTP check options**: Machine health checks gained `protocol` (http/https), `tls_skip_verify`, and custom `headers` options in the Machines API.
- **2023-02-22** — **`starting` Machine status**: The Machines API added a documented `starting` state to the Machine lifecycle statuses.
- **2023-02-28** — **Postgres "flex" implementation**: TimescaleDB docs were updated for the new flex implementation of Fly Postgres — the newer repmgr-based `postgres-flex` cluster architecture replacing the original Stolon-based images.

### March 2023
- **2023-03-03** — **Flycast DNS names**: New `appname.flycast` domains that resolve only to an app's Flycast (private load-balanced) addresses, added mainly to help PostgreSQL clients that can't handle raw IPv6 addresses in connection strings.
- **2023-03-13** — **60-second proxy timeout documented**: Docs added stating Fly Proxy enforces a 60-second idle timeout on connections (this limit was later removed in September).
- **2023-03-25** — **Apps V2 release**: Major docs launch for Apps V2, the new Machines-based application platform replacing Nomad orchestration. A whole new `apps/` docs section landed covering `fly launch`, `fly deploy`, `fly scale count`, `fly scale machine`, process groups, volume storage, app restart/delete, plus a migrate-to-v2 stub and transition banners across the docs. Manual V2 migration steps were added 2023-03-30.
- **2023-03-27** — **Deploy tokens**: New `fly tokens create deploy` command producing app-scoped tokens that can only manage a single app and its resources — designed for CI (GitHub Actions) instead of full-account personal access tokens.
- **2023-03-29** — **Regions list expanded**: Updated regions list adding new locations including Stockholm (arn), Bogotá (bog), Boston (bos), Denver (den), Guadalajara (gdl), Rio de Janeiro (gig), and others.

### April 2023
- **2023-04-03** — **Shared IPv4 addresses**: Pricing/services docs now distinguish free shared IPv4 addresses (assigned to apps by default) from dedicated IPv4 addresses at $2/month.
- **2023-04-04** — **`fly scale vm` and `fly scale memory` for Apps V2**: Vertical scaling commands documented for Machines-based V2 apps; `fly scale count` horizontal scaling docs were reworked 2023-04-22.
- **2023-04-09** — **Pricing changes: no free "tier", credit card required**: Pricing page updated for Apps V2 to clarify there is no free tier as such (just free allowances on plans) and that all plans require a credit card (2023-04-10).
- **2023-04-14** — **Scale to zero**: Docs for scaling apps to zero Machines with `fly scale count 0`, complementing the new stop/start Machine model.
- **2023-04-16** — **LiteFS v0.4.0**: Consolidated docs for LiteFS v0.4.0: the new built-in LiteFS proxy (primary-forwarding HTTP proxy), halt lock and write forwarding, `litefs export`, the `litefs run` command with new arguments, and candidate autopromotion.
- **2023-04-17** — **Volume max size documented**: Fly Volumes maximum size explicitly documented as 500GB (default 3GB).
- **2023-04-20** — **Automatic Machine start/stop**: New `auto_stop_machines` and `auto_start_machines` settings (default `true`) with a dedicated "Automatically Stop and Start Machines" docs page — Fly Proxy stops Machines when there's excess capacity and starts them on incoming requests.
- **2023-04-21** — **`fly consul attach`/`detach` commands**: New flyctl commands for attaching/detaching a Consul cluster to an app (used for LiteFS lease management).
- **2023-04-25** — **33 regions**: Regions list, count, and map updated to 33 regions, including newly added Atlanta (atl).
- **2023-04-27** — **Public Machines API endpoint `api.machines.dev`**: Docs now recommend the new public `api.machines.dev` HTTPS endpoint for the Machines API over WireGuard tunnels or `flyctl proxy`.

### May 2023
- **2023-05-02** — **Fly.io Extensions Program**: New page announcing the Extensions program for deeply integrated third-party services (managed databases, error tracking, log aggregation). Over May–August the full Extensions API was documented: provisioning, SSO/OAuth flows, request signing, billing, and provider webhooks.
- **2023-05-02** — **`_instances.internal` DNS name**: New internal DNS entry returning all addresses, apps, regions, and instances in the organization's 6PN network.
- **2023-05-06** — **New region: Ezeiza, Argentina (eze)**: Buenos Aires-area region added, bringing the total to 34 regions.
- **2023-05-10** — **Apps V2 default for all new orgs**: All new organizations now get Apps V2 (Machines-based) apps by default; `--force-nomad`/`--force-machines` flags were removed from `fly apps create`, `fly deploy`, and `fly launch` (2023-05-16).
- **2023-05-15** — **Fly Postgres: 3-node HA and scale-to-zero**: Production Postgres option is now a three-node high-availability cluster (was two-node), and single-node Development clusters can be configured to scale to zero after one hour without connections.
- **2023-05-17** — **`min_machines_running` setting**: New option for the auto start/stop feature to keep a minimum number of Machines always running in the primary region.
- **2023-05-23** — **Process-group DNS names**: New `<group>.process.<appname>.internal` private DNS entries for addressing Machines by process group.
- **2023-05-26** — **Canary deploy strategy re-introduced for Apps V2**: The `canary` deployment strategy, previously Nomad-only, documented as available again for Machines-based apps.

### June 2023
- **2023-06-01** — **`fly migrate-to-v2` automated migration**: Docs updated with instructions for the automated `fly migrate-to-v2` command that migrates Nomad (V1) apps to Apps V2.
- **2023-06-07** — **Machine `metrics` config**: Machines API config gained a `metrics` object (port + path) defining a Prometheus scrape endpoint per Machine.
- **2023-06-09** — **LiteFS Cloud launch**: New managed service providing streaming backups and point-in-time restore (up to 30 days) for LiteFS SQLite databases, whether running on Fly.io or elsewhere. Docs added for cloud backups, restore, and management via flyctl and the dashboard; disaster recovery docs followed 2023-07-11.
- **2023-06-22** — **Bluegreen deploy strategy for V2 apps**: The `bluegreen` deployment strategy documented as supported for Apps V2 (initially not usable with volumes).
- **2023-06-27** — **LiteFS 0.5**: Docs updated to LiteFS version 0.5, with a new Docker getting-started guide and a LiteFS speedrun.
- **2023-06-28** — **`http_service` checks + region change**: New docs for health checks under `[[http_service.checks]]` in fly.toml. Separately, the Chennai (MAA) region was removed in favor of Mumbai (BOM).

### July 2023
- **2023-07-04** — **Remote builders by default**: Getting-started docs updated to reflect that `fly launch`/`fly deploy` now use remote builders by default.
- **2023-07-10** — **Dynamic Machine metadata DNS routing**: New `<value>.<key>.kv._metadata.<appname>.internal` DNS names that resolve to the IPv6 addresses of Machines with matching metadata.
- **2023-07-17** — **Machines API OpenAPI/Swagger spec**: A Swagger 2.0 specification for the Machines API published at machines-api-spec.fly.dev for autogenerating clients. Also new region: Phoenix, Arizona (phx).
- **2023-07-19** — **Restartless volume extend**: Extending a Fly Volume (`fly vol extend`) no longer requires restarting the attached Machine.
- **2023-07-24** — **`tls_server_name` for checks**: New option for HTTPS health checks to verify the certificate hostname, in both fly.toml services and the Machines API.
- **2023-07-27** — **Machine files**: New ability to write files into Machines at boot via the Machines API and fly.toml `[[files]]` — from an image path, a `raw_value`, or a `secret_name`.

### August 2023
- **2023-08-02** — **`swap_size_mb` config option**: New top-level fly.toml directive to provision swap space in Machines.
- **2023-08-20** — **Sentry error-tracking extension**: New docs for the Sentry partnership: every Fly.io organization gets a year of Sentry Team Plan credits (50k errors, 100k performance transactions, 500 session replays, 1GB attachments/month), provisioned via `fly ext sentry`. Publicly linked in the docs nav 2023-09-12.
- **2023-08-28** — **`kill_timeout` maximum changed**: Docs updated so the maximum `kill_timeout` is now 300 seconds (previously documented as up to 86,400s/24h for dedicated VMs).
- **2023-08-31** — **Experimental `exec` option**: fly.toml `[experimental]` section documents `exec` for overriding the Machine's command at deploy.

### September 2023
- **2023-09-05** — **60-second proxy idle timeout removed**: Fly Proxy no longer enforces the 60-second idle timeout on connections; the documented limit was deleted. Also new `fly secrets deploy` command documented — deploys staged secrets without rebuilding the image.
- **2023-09-06** — **LiteFS event stream**: New LiteFS docs for the events API endpoint (init, tx, primaryChange events) for observability and coordination.
- **2023-09-15** — **Per-process-group custom metrics**: The `[[metrics]]` config in fly.toml now supports a `processes` field so different process groups can expose different Prometheus metrics endpoints.
- **2023-09-21** — **Machine restart policy docs**: New dedicated page for Machine restart policies (`no`, `always`, `on-failure`) and how flyctl and the Machines API set them.

### October 2023
- **2023-10-05** — **LiteFS Cloud pricing**: LiteFS Cloud pricing published: $5/month for up to 10GB of database storage, $0.50/GB/month beyond that.
- **2023-10-12** — **Custom (segmented) app networks**: Machines docs expanded on passing a `network` argument at app creation to isolate an app in its own private network, unable to reach other apps in the organization over 6PN.
- **2023-10-17** — **Fly GPUs (waitlist beta)**: New GPU quickstart guide for running GPU workloads (A100s, `a100-40gb` in ord) on GPU-enabled accounts via a waitlist, using Machines with CUDA images and volumes for model storage. Same day: new `deploy.max_unavailable` fly.toml option controlling how many Machines can be down during rolling deploys.
- **2023-10-19** — **Volume forking**: New `fly volumes fork` docs for copying a volume's data to a new volume, plus a dedicated guide for forking Fly Postgres volumes to clone clusters.
- **2023-10-24** — **Redis renamed "Upstash for Redis"**: Product renamed per Redis trademark requirements.
- **2023-10-27** — **Configurable deploy timeouts**: New `release_command_timeout` and `wait_timeout` settings in fly.toml `[deploy]` (and matching `fly deploy` flags); the default release command timeout is 5 minutes.
- **2023-10-30** — **Web launchers hidden**: The /launch web launchers were hidden, with redirects to the `fly launch` docs (formally retired with a redirect page on 2023-12-12).

### November 2023
- **2023-11-02** — **Upstash Redis pay-as-you-go pricing**: New pricing model: one free resource-limited database per organization, then per-request pay-as-you-go billing (empty responses from polling not billed); `fly redis dashboard` documented for usage details.
- **2023-11-07** — **Terraform docs removed**: The Terraform-with-Machines guides were deleted, reflecting the provider's best-effort/deprecated status.
- **2023-11-08** — **`h2_backend` option + new billing page**: New `http_service.http_options.h2_backend` setting enabling HTTP/2 cleartext (H2C) backends, allowing gRPC/HTTP/2-only services behind the `http` handler. A new consolidated Billing docs page also landed.
- **2023-11-10** — **GPU pricing published**: On-demand GPU pricing added: A100 40G PCIe at $2.50/hr and A100 80G SXM at $3.50/hr, requiring a Launch, Scale, or Enterprise plan; reserved/dedicated discounts available. Pricing page also reframed around the $5/month Hobby plan.
- **2023-11-15** — **`mounts.initial_size` and `[[vm]]` config sections**: fly.toml gained `mounts.initial_size` for setting the size of volumes created on first deploy, and a new `[[vm]]` section for declaring Machine compute requirements (size, memory, cpus, cpu-kind, gpu-kind) per process group.
- **2023-11-17** — **Apps V1 (Nomad) docs removed**: All V1/Nomad-era content deleted — legacy scaling page, migrate-to-v2 page, V1 transition banners — marking the effective end of the Nomad-to-Machines migration in the docs.
- **2023-11-20** — **Volume auto-extend**: New automatic volume extension options documented for fly.toml (`auto_extend_size_threshold`, `auto_extend_size_increment`, `auto_extend_size_limit`) and the Machines API (`extend_threshold_percent`, `add_size_gb`, `size_gb_limit`).
- **2023-11-23** — **Fly Launch UI**: Docs updated across launch, deploy, Dockerfile, and CI guides for the new web-based Launch UI flow, where `fly launch` opens a browser page to tweak app settings before first deploy.
- **2023-11-30** — **Supabase Postgres docs (pre-launch)**: Initial docs for fully managed Supabase Postgres hosted on Fly.io infrastructure (one free database per org, then pay-as-you-go under Supabase Pro), created via `fly ext supabase`.

### December 2023
- **2023-12-06** — **Expanded Fly GPUs docs**: New GPU docs section with an index, "Getting started with Fly GPUs," and a Python/GPU example app, noting L40S cards incoming alongside A100s.
- **2023-12-07** — **Nvidia L40S GPUs**: The `l40s` GPU kind added to Machine configuration and GPU docs (merged 2023-12-20); L40S pricing of $2.50/hr per GPU added to the pricing page on 2023-12-21.
- **2023-12-15** — **Supabase Postgres extension launched**: Supabase docs added to the public sidebar. Same day, region restrictions were updated: paid-plan-only regions now specifically require the Launch, Scale, or Enterprise plan (Hobby excluded), with the region count at 35.
- **2023-12-28** — **Extensions API machine event webhooks**: Extensions API docs expanded with Machine event webhooks so extension providers can react to customer Machine lifecycle events.

## 2022

### January 2022
- **2022-01-12** — **Static site launcher**: `fly launch` now detects static sites automatically ("Detected a Static app") and configures deployment; the docs replaced a long manual goStatic walkthrough with the new launcher-based flow.
- **2022-01-24** — **Free volume storage added to free tier**: Pricing page updated to include 3GB of provisioned persistent volume capacity per organization in the free allowances.

### February 2022
- **2022-02-02** — **`flyctl turboku` region option**: The Heroku-app launcher command `flyctl turboku` gained a `--region` option for choosing where the app deploys.
- **2022-02-21** — **`fly postgres connect` and `fly proxy`**: New flyctl workflows for reaching Fly Postgres documented — `flyctl postgres connect` opens a psql shell and `flyctl proxy 5432` forwards the server port locally, both using flyctl's user-mode WireGuard so no manual VPN tunnel is needed.
- **2022-02-22** — **`fly image update` for Fly Postgres**: Postgres reference now documents upgrading a Postgres cluster to the latest postgres-ha release with `flyctl image update`.

### March 2022
- **2022-03-05** — **New region: Miami (mia)**: Miami, Florida added to the region list.
- **2022-03-07** — **`private_network` fly.toml entry deprecated**: References to the deprecated `private_network` option were removed from the fly.toml configuration docs; supported TLS versions and ciphers at the edge were also documented.
- **2022-03-08** — **Redis image configuration options**: The Fly Redis image now supports configuration via secrets/env vars (e.g. `MAXMEMORY_POLICY`), with defaults of `maxmemory` at 90% of VM memory and `allkeys-lru` eviction. On 2022-03-24 the docs also noted the Redis image no longer ships a Prometheus exporter (metrics removed).
- **2022-03-22** — **`force_https` option**: New `force_https` setting in `[[services.ports]]` automatically redirects HTTP to HTTPS with a 301; only valid on HTTP handlers (deploys fail if set elsewhere). Merged to docs 2022-04-04.
- **2022-03-29** — **flyctl via Homebrew**: flyctl can now be installed with plain `brew install flyctl`.

### April 2022
- **2022-04-01** — **New setup-style flyctl GitHub Action**: GitHub Actions continuous-deployment docs updated to use the new setup-style `flyctl-actions/setup-flyctl` action instead of the old wrapper action.
- **2022-04-05** — **"Anchor scaling" removed**: The volume-based anchor scaling section was deleted from the scaling docs — apps with volumes now place instances strictly according to where volumes exist, rather than volumes acting as optional "anchors" alongside `fly scale count`.
- **2022-04-08** — **`restart_limit` in health checks**: Documented the `restart_limit` option for `services.tcp_checks`/`http_checks`, including `restart_limit = 0` (default, never restart on failed checks).
- **2022-04-10** — **Region removed: Atlanta (atl)**: atl was dropped from the regions list (remaining references cleaned up 2022-08-19).
- **2022-04-28** — **Full metrics catalog documented**: All Fly-exposed Prometheus metrics (instance, proxy/HTTP, and later disk/network detail) were added to the metrics reference.

### May 2022
- **2022-05-03** — **`fly ssh establish` deprecated**: Troubleshooting docs now recommend `fly ssh console -s` instead of the removed `fly ssh establish` step.
- **2022-05-08** — **Default volume size cut from 10GB to 3GB**: `fly volumes create` now defaults to a 3GB volume instead of 10GB.
- **2022-05-11** — **Fly Machines soft launch**: New Machines reference documents the Machines REST API ("Flaps") — create/launch, list, get, start, stop, wait, update, and delete machines and machine-hosting apps, plus the machine state model. Follow-up commits through May added networking docs, secrets support (secrets set at the app level, applied on machine update), wake-on-request clarifications, and a "Functions as a Service (FaaS) on Machines" app guide.
- **2022-05-24** — **PlanetScale integration guide**: New app guide for using PlanetScale serverless MySQL (including regional read replicas) with Fly apps; references the PlanetScale Team plan.
- **2022-05-26** — **Laravel getting-started guide**: First Laravel deployment guide added (Dockerfile-based at this point).

### June 2022
- **2022-06-10** — **Laravel launcher in flyctl**: `fly launch` now detects and configures Laravel apps automatically; the Laravel guide was rewritten around the new launcher and Laravel was added to the speedrun.
- **2022-06-24** — **New region: Montreal (yul)**: yul added to the regions list, along with an explanation of gateway-only regions (regions that host WireGuard gateways).
- **2022-06-27** — **`fly-replay` header reference**: New reference page for the `fly-replay` response header, letting an app instance ask the Fly proxy to replay a request to another region, a specific instance, or another app in the same organization (fields: `region`, `instance`, `app`, `state`, `elsewhere`), plus the `fly-replay-src` header.
- **2022-06-28** — **Machines API volume mounts**: The Machines API now documents attaching persistent volumes via a `mounts` config (volume ID + mount path), currently one volume per machine.

### July 2022
- **2022-07-15** — **`[processes]` section (preview)**: Documented the fly.toml `[processes]` block for multi-process apps — run the same app image with different commands (web, worker, etc.) and match specific processes to `services`, `mounts`, or `statics` sections. Flagged as a preview feature.
- **2022-07-18** — **Terraform provider for Fly + Machines tutorial**: New guide for deploying Fly Machines with the Fly.io Terraform provider (infrastructure-as-code for machines, IPs, and apps).
- **2022-07-23** — **`flyctl init` retired from docs**: Removed from the flyctl sidebar in favor of `fly launch`.
- **2022-07-29** — **Fly Postgres: restore from snapshot**: Postgres reference now documents creating a new Postgres app from a volume snapshot (`fly postgres create --snapshot-id ...`), including restoring multi-region clusters. A "Run a MySQL app on Fly" guide (MySQL container with a volume) was added the same day.

### August 2022
- **2022-08-02** — **Build secrets documentation**: New "Build Secrets" reference showing how to expose secret values at Docker build time using BuildKit secret mounts plus `fly deploy --build-secret`; secrets nav split into Build Secrets and Runtime Secrets.
- **2022-08-03** — **Free tier without a credit card**: Pricing docs now describe free allowances available before adding a payment method (2 apps with one shared-cpu-1x VM each, ~2,340 shared-CPU hours/month, 1GB volume), with larger allowances (3 VMs, 3GB volumes, 160GB transfer) after adding a card.
- **2022-08-03** — **`fly volumes extend` and create-from-snapshot**: Volumes docs now cover extending a volume's size (`fly volumes extend`, grow-only) and creating a new volume from a snapshot; volume snapshots are taken daily and retained 5 days.
- **2022-08-15** — **Redis by Upstash (public beta) and Flycast first documented**: New docs for fully-managed, Redis-compatible Upstash databases provisioned inside your Fly organization (with global read replicas), replacing the "Run Redis on Fly" guide. The same commit added the first "Private Load Balancing (aka Flycast)" section to private networking — a private IPv6 address that routes through the Fly proxy with geo load balancing.
- **2022-08-18** — **MetricsQL support**: Managed Prometheus metrics docs note support for the extended MetricsQL query language (VictoriaMetrics backend).
- **2022-08-22** — **Healthcare/compliance page**: New page targeting healthcare apps on Fly.io, with links to HIPAA-relevant material and SOC2 information.
- **2022-08-24** — **`services.concurrency.type`**: Documented the concurrency `type` option — load-balance and scale by `connections` (default) or `requests` (recommended for web services) — along with clarified `soft_limit`/`hard_limit` semantics.
- **2022-08-26** — **Heroku migration guide**: New "Migrate from Heroku" docs including a Heroku→Fly command cheat sheet and pricing/database comparisons.
- **2022-08-30** — **Redis by Upstash plan changes**: Free plan daily bandwidth limit dropped from 10GB to 100MB; daily command-count limits removed on all plans.

### September 2022
- **2022-09-01** — **Machines config gains `concurrency`; new filesystem metrics**: Machine `services` config now supports concurrency settings (`type` connections/requests, `soft_limit`, `hard_limit`); `fly_instance_filesystem_*` metrics were added to the exposed instance metrics.
- **2022-09-06** — **LiteFS launched (beta)**: New LiteFS docs section — "Getting Started with LiteFS", a config (`litefs.yml`) reference, and "How LiteFS Works" — introducing Fly's FUSE-based distributed SQLite replication layer with Consul-based primary election. A Rails LiteFS guide followed 2022-09-26 (moved from alpha to beta 2022-09-27).
- **2022-09-15** — **Paid support plans**: Support page updated to list more support options and link to paid plans.
- **2022-09-26** — **New regions: Denver (den) and Johannesburg (jnb)**: Both added to the regions list.
- **2022-09-27** — **Fly Postgres on Machines (Apps V2) preview**: Large new "Postgres on Machines" reference documenting the V2 Fly Postgres — clusters running on Fly Machines — alongside the original Nomad-based (V1) Postgres, with a new Postgres landing page distinguishing the two.
- **2022-09-29** — **Apps V1 vs Apps V2 reference**: New apps reference page explaining Apps V1 (Nomad-orchestrated) versus Apps V2 (Machines-based) platform generations.

### October 2022
- **2022-10-12** — **Machines Postgres docs become the default**: The Postgres-on-Machines docs replaced the legacy Nomad Postgres docs as the primary Fly Postgres documentation.
- **2022-10-20** — **Machines API leases**: Documented machine leases (`POST /machines/{id}/lease` etc.) for coordinating exclusive machine ownership during updates.
- **2022-10-21** — **Fly Postgres manual failover on Machines**: Documented the failover procedure for Machines-based Postgres clusters.
- **2022-10-27** — **`tls_options` config; LiteFS special files**: New `services.ports.tls_options` fly.toml setting to control ALPN protocols and allowed TLS versions at the edge (including TLS-only pass-through). Separately, LiteFS's `.primary` and `-pos` special files were documented.
- **2022-10-28** — **Autoscaling overhaul**: Autoscaling docs rewritten — the old Standard/Balanced region-pool modes are gone, replaced by a single horizontal autoscaler that scales out when load exceeds `soft_limit × instance count` and scales in over a 10-minute window, between min/max counts. New data-storage guides (volumes, MinIO object storage) were added the same day.
- **2022-10-29** — **Node launcher drops buildpacks**: `fly launch` no longer uses Cloud Native Buildpacks by default for Node.js apps (Dockerfile-based instead).

### November 2022
- **2022-11-10** — **Scheduled Machines**: Documented the `schedule` field of machine config — run a machine at `hourly`, `daily`, `weekly`, or `monthly` intervals (machines are started from their last stop time).
- **2022-11-13** — **Fly Postgres major-version upgrade restriction**: `fly image update` now only updates a Postgres cluster if no major Postgres version change is required; major upgrades require provisioning a new cluster and restoring the database.
- **2022-11-16** — **Scaling docs for Machines Postgres**: Documented scaling V2 (Machines) Postgres VMs with `fly machine update --memory/--cpus`, HA-cluster scaling guidance, and Postgres resource parameter tuning.
- **2022-11-21** — **Django framework docs**: New Django deployment docs section added.
- **2022-11-22** — **New regions: Warsaw (waw) and Bucharest (otp)**: Both added to the regions list.

### December 2022
- **2022-12-02** — **External TLS connections to Fly Postgres**: Documented `pg_tls` configuration and the full procedure for exposing a Fly Postgres app to connections from outside its private network (public IP, TLS, publicly resolvable hostname).
- **2022-12-05** — **`fly dns-records` and `fly domains` removed from docs**: The DNS records and domains management commands were dropped from the flyctl command nav (alongside `resume`), reflecting their deprecation; `fly image` commands were added.
- **2022-12-08** — **Machines pricing published**: Machines pricing (which also covers Fly Postgres on Machines) added to the pricing page as a separate section from regular Apps VM pricing, plus a new machine VM sizing guide (`fly machine update --size/--memory/--cpus`), updated again 2022-12-14.
- **2022-12-12** — **`fly ping` command**: New flyctl command for ICMP-pinging apps/hosts over the WireGuard mesh, added to the flyctl docs nav.
- **2022-12-13** — **Flycast cross-organization networking**: Flycast (private load balancing) docs expanded to cover the new option of exposing services across organization networks, with geo-aware load balancing, TLS termination, and port restriction on private traffic.
- **2022-12-14** — **Shared anycast IPv4 addresses**: New apps with services on port 80 (HTTP) or 443 (TLS/HTTP) now automatically get a free *shared* anycast IPv4 address on first deploy (dedicated IPv4 remains a paid option); dedicated IPv6 remains free and automatic.
- **2022-12-15** — **Redis by Upstash out of beta**: Redis docs updated for launch — renamed "Redis by Upstash", public-beta disclaimer removed.
- **2022-12-16** — **Credit card requirement & preauthorization policy**: New billing doc explaining that a valid credit card is required for most accounts, how small (<$5) preauthorization holds work, and that charges occur monthly for usage beyond the free allowance.
- **2022-12-20** — **Run a Machines app with flyctl**: New guide for running apps directly on Fly Machines using `fly machine run` and fly.toml (positioning Machines as the building blocks of the V2 app platform), updated to use shared IPv4.
- **2022-12-26** — **LiteFS v0.3.0**: LiteFS docs updated for v0.3.0 — reworked configuration reference plus new `litefs mount` and `litefs import` commands; a rewritten Getting Started guide followed on 2022-12-29.
- **2022-12-31** — **`fly sftp` in flyctl docs**: New nav entry for `fly sftp` (move files to and from a VM over SSH/SFTP).

## 2021

### May 2021
- **2021-05-30** — **Fly.io documentation open-sourced (baseline snapshot)**: The docs repository was opened to the public, capturing the platform as of mid-2021: Firecracker VM-based apps deployed from Docker containers via `flyctl`, Anycast networking, managed SSL certificates, persistent volumes, autoscaling, `fly scale`, Fly Postgres clusters, multi-region PostgreSQL, metrics, and app guides (Minio, NATS, Redis, nginx, etc.).
- **2021-05-31** — **Monorepo and multi-environment deployments documented**: New `reference/monorepo.html.md` page describing how to deploy multiple apps from one repository — `flyctl deploy <path>` to set the working directory/build context and the `--config` flag to point at alternate `fly.toml` files for multiple deploy targets.

### June 2021
- **2021-06-04** — **Private networking (6PN) becomes default, WireGuard access documented**: The private networking reference was rewritten: every app instance now gets an organization-scoped "6PN" IPv6 address and DNS at `fdaa::3` configured automatically — the previous `[experimental] private_network=true` opt-in in `fly.toml` is no longer needed. Also documents connecting external machines (e.g. a dev laptop) to the 6PN network via `flyctl`-generated WireGuard configs, including the per-organization WireGuard DNS address pattern (`<org-prefix>::3`).
- **2021-06-11** — **flyctl command set churn: `fly config env` and `fly curl` added, `fly builds` removed**: CLI docs added new commands `fly config env` (display app environment) and `fly curl` (timed HTTP requests against an app), removed the `fly builds`/`fly builds logs` commands, and dropped unimplemented Postgres user/database management sections (creating/dropping users and databases) from the Postgres reference. The `fly curl` docs were removed again on 2021-06-22, indicating the command was pulled back.
- **2021-06-30** — **PostgreSQL cluster pricing published**: The pricing page gained a "PostgreSQL Clusters" section explaining that `fly pg create` provisions a 2-node cluster billed as ordinary VM + volume resources, with example totals from ~$6.88/mo (2x shared-cpu-1x, 256MB RAM, 10GB volumes) up to ~$1,266/mo (2x dedicated-cpu-8x, 64GB RAM, 500GB volumes).

### July 2021
- **2021-07-01** — **Docker projects page and multiple-processes guide**: New `docker-projects` page pitching running any Docker container on Fly.io in minutes via `flyctl launch`, highlighting the IPv6/WireGuard network fabric and userland-WireGuard `flyctl ssh console`. A new "Running Multiple Processes Inside A Fly.io App" guide documented patterns for running several programs in one VM (since Fly runs containers as microVMs with their own kernel, not under Docker).
- **2021-07-09** — **Fly Redis (built-in cache) starts disappearing from docs**: The `FLY_REDIS_CACHE_URL` environment variable was removed from the runtime environment reference — the first step in deprecating the built-in regional Redis cache service (fully deprecated in December).
- **2021-07-19** — **Public Grafana dashboard for built-in metrics**: The metrics reference added instructions for importing Fly's pre-built Grafana dashboard (ID 14741) against the per-organization Prometheus metrics endpoint, with a public `superfly/dashboards` repo for contributions.

### September 2021
- **2021-09-08** — **Restore Postgres from volume snapshots**: New docs explain that Fly.io takes daily automatic storage snapshots of every provisioned volume, listable with `fly volumes snapshots list <volume-id>`, and that a Postgres cluster can be restored into a new app with `fly postgres create --snapshot-id <snapshot-id>`.
- **2021-09-09** — **Exposing Postgres to external connections documented**: New docs cover allocating public IPs (`fly ips allocate-v4` / `fly ips allocate-v6`) and adding a `[[services]]` section mapping external ports (e.g. 443 with TLS handler, or a raw port) to Postgres's internal port 5432, since Postgres apps expose no external ports by default.
- **2021-09-15** — **Experimental `cmd` and `entrypoint` overrides in fly.toml**: The configuration reference documented new `[experimental]` settings `cmd` (2021-09-15) and `entrypoint` (2021-09-21) that override the Docker image's `CMD` and `ENTRYPOINT`, specified as arrays of strings.
- **2021-09-21** — **`fly init` deprecated in favor of `fly launch`**: Docs began removing references to the deprecated `fly init` command, delinking stale guides built around it; follow-up commits on 2021-09-22 scrubbed remaining references in the Deno and Python guides.
- **2021-09-22** — **New region: Chennai (maa)**: The `maa` (Chennai, India) region was added to the regions list. The same day, the Deno getting-started guide was rewritten to match a new native Deno launcher in `fly launch`.
- **2021-09-27** — **Fly Machines commands first documented**: A flyctl docs refresh added the entire `fly machine` command family — `fly machine run <image>`, `list`, `start`, `stop`, `kill`, `remove` — the first public documentation of the Machines (direct Firecracker VM control) capability. The same update added `fly volumes snapshots` / `fly volumes snapshots list` commands and restored the `fly builds` / `fly builds list` / `fly builds logs` docs.

### October 2021
- **2021-10-04** — **`fly init` removed from flyctl**: The `flyctl init` command page was deleted, completing the deprecation in favor of `fly launch`. The same release added `--generate-name` to `fly apps create` and `--build-only` to `fly machine run`.
- **2021-10-15** — **`fly proxy` command documented**: New docs for `flyctl proxy <local:remote>`, which proxies local connections to an app over the WireGuard tunnel, with a `--select` flag to pick a specific instance.

### November 2021
- **2021-11-26** — **`fly launch` gains new flags**: A flyctl docs refresh documented new `fly launch` options: `--dockerfile` (path to a custom Dockerfile), `--generate-name`, and `--no-deploy` (skip the deployment prompt).

### December 2021
- **2021-12-05** — **Anycast inbound TCP port filter documented**: New "The Dreaded Port Filter" guide publicly listed which inbound TCP ports Fly's Anycast network accepts (25, 53, 80, 443, 853, 5000, 8080, 8443, 100xx, 25565), noting UDP has no filter, private 6PN traffic is unrestricted, new ports can be added on request, and that Fly is working to remove the restriction entirely.
- **2021-12-07** — **UDP (and mixed UDP/TCP) services guide**: New "Running Fly.io Apps On UDP and TCP" guide documenting `protocol = "udp"` in `[[services]]` and the gotchas — UDP listeners must bind the special `fly-global-services` address while TCP binds `0.0.0.0` — with a full echo-server walkthrough.
- **2021-12-07** — **Fly Redis officially deprecated**: The Redis reference was rewritten with a callout that the built-in regional Redis cache ("Fly Redis") is deprecated; the recommended approach is now running Redis yourself as a Fly app using the `flyio/redis:6.2.6` image with a persistent volume mounted at `/data`. Also this week, the Fly Postgres reference was linked from the main docs sidebar.
- **2021-12-10** — **New flyctl commands: `fly dig`, `fly image`, `fly postgres connect`, `fly turboku`**: A flyctl docs refresh added `fly dig` (make DNS requests against Fly's internal DNS), `fly image show`/`fly image update` (manage an app's Docker image), `fly postgres connect`, `fly turboku` (deploy a Heroku app to Fly), and a `fly create` alias. The same day, the Elixir getting-started guide was rewritten for the new native Elixir/Phoenix launcher in `fly launch`, including automatic Postgres provisioning/attachment during launch.
- **2021-12-13** — **Remix support**: A new getting-started guide for Remix apps was added, reflecting `fly launch` support for deploying Remix projects.
- **2021-12-14** — **More internal DNS names documented**: The private networking reference added previously undocumented `.internal` DNS entries: `top<number>.nearest.of.<appname>.internal` (N closest instances), `<alloc_id>.vm.<appname>.internal` (a specific instance), and `global.<appname>.internal` (instances in all regions).
- **2021-12-22** — **fly.toml `[deploy]` section documented**: New configuration docs for `release_command` (run a one-off VM command such as DB migrations before each release, aborting the deploy on non-zero exit) and `strategy`, with four deployment strategies: `canary` (default without volumes), `rolling` (default with volumes), `bluegreen`, and `immediate`.

