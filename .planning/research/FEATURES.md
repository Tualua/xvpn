# Feature Landscape

**Domain:** Ansible collection deploying Remnawave Panel/Node (VLESS Reality self-steal, LAN egress) on EL10, rootless Podman + Quadlet, SELinux enforcing, Traefik
**Researched:** 2026-11-23
**Overall confidence:** MEDIUM (landscape from web search snippets plus domain knowledge; Remnawave API endpoint names should be verified against the live OpenAPI/Swagger of the pinned Panel version in phase research)

## Competitive Landscape (what exists)

| Project | Type | What it covers | Gaps vs this project |
|---------|------|----------------|----------------------|
| [ryabkov82/vff-remnawave-auto](https://github.com/ryabkov82/vff-remnawave-auto) | Ansible | Panel, nodes, subscription page, Marzban migration, node registration by fetching key from Panel API (Makefile target), node disable/delete roles | Docker based, Debian/Ubuntu oriented, RU docs, not a packaged collection |
| [iphizic/remna-playbook](https://github.com/iphizic/remna-playbook) | Ansible | Simple install playbook, venv + Galaxy requirements, prep playbook builds inventory | Basic, install only |
| [eGamesAPI/remnawave-reverse-proxy](https://github.com/eGamesAPI/remnawave-reverse-proxy) | Bash installer | Panel + Node + NGINX/Xray, selfsteal node creation and panel integration, cookie-secret panel protection (URL param sets cookie; else 404/blank), Cloudflare cert auto-renew, UFW, BBR, warns on proxied selfsteal domain | Not idempotent, imperative, not infrastructure-as-code, project self-describes as educational |
| [DigneZzZ/remnawave-scripts](https://github.com/DigneZzZ/remnawave-scripts) | Bash | One-command Panel/Node install, scheduled backup (Telegram/S3, retention, age encryption), selective restore (restore marked beta) | Imperative |
| Official docs (docs.rw) | Docs | docker compose for Panel/Node, reverse proxy guides (nginx, angie), tinyauth for nginx, recommendation to firewall node port to Panel IP only | No automation |
| Marzban / 3x-ui Ansible roles | Ansible | Install + config templating, mostly Docker/systemd, no API-driven registration | Different product |

Key observation: no existing project combines (a) rootless Podman/Quadlet, (b) SELinux enforcing, (c) declarative, idempotent Panel-API-driven resource management (config profiles, nodes, hosts, squads), (d) Molecule/CI. This is the white space.

## Table Stakes

Features users expect. Missing means the collection feels incomplete versus existing scripts/roles.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Panel role: backend + Postgres + Redis (Valkey) as Quadlet units on a private Podman network | Core purpose; every competitor does it | Med | Pin image tags via vars; `.container`/`.network`/`.volume` files; healthchecks and `After=`/`Requires=` ordering; `loginctl enable-linger` for the service user |
| Secrets generation on first run (JWT secrets, Postgres password, metrics creds) persisted so re-runs do not rotate them | Idempotency plus security | Med | Use `lookup('password')` to a controller-side file or require vault vars; never regenerate on re-run |
| Traefik fronting Panel with Let's Encrypt HTTP-01 | Stated requirement; scripts use nginx/caddy | Med | Traefik file provider, static config templated; acme.json persistent with 0600 and SELinux label |
| Subscription page container on separate domain behind Traefik | Official component; competitors deploy it | Low-Med | Needs Panel URL + API token (`REMNAWAVE_API_TOKEN`) so depends on token bootstrap |
| Panel login protection: at least IP allowlist and secret-path/cookie gate | Panel admin exposed to internet is the #1 community concern; eGames and docs (tinyauth) emphasise it | Med | Implement via Traefik middlewares (ipAllowList; cookie/header check via forward-auth or plugin-free router rule). Subscription and node-to-panel API paths must stay reachable |
| First admin bootstrap | Otherwise the "one command" claim fails | Med | `POST /api/auth/register` works only while no admin exists; make task tolerate "already registered" (HTTP error) so re-runs are changed=0. Login to obtain JWT |
| API token creation for automation | Subscription page and node registration need a token | Med | Tokens are created via authenticated API (`/api/tokens`); store token as controller-side fact or vault file; list-then-create for idempotency by name |
| Node role: remnanode (Xray) as Quadlet unit with SECRET_KEY, NODE_PORT | Core purpose | Med | Host networking or pasta decision drives client IP and LAN access; cap NET_ADMIN only if needed; log volume |
| Node auto-registration via Panel API | Stated core value; vff-remnawave-auto proves demand | High | Get Panel public key (`/api/keygen`), create node (name, address, port, config profile + active inbounds), node picks up SECRET_KEY. Look up by name first for idempotency |
| Config profile + inbounds management (VLESS Reality TCP, xtls-rprx-vision) | Node unusable without it | High | Template Xray JSON; generate x25519 private key/shortIds once and persist; create or update profile by name; compare normalised JSON to avoid false changes |
| Hosts creation (user-facing connection entries: address, port, SNI, fingerprint) | Without hosts, subscriptions are empty | Med | Reference config profile UUID and inbound UUID resolved by tag |
| Internal squads (assign inbounds to user groups) | Needed for default squad and LAN squad | Med | Create or update squad by name with set of inbound UUIDs |
| Self-steal: Reality `dest` to local Traefik with real cert for node domain plus stub site | Stated core; competitors do via nginx | High | Traefik on node listens on localhost/unix socket TLS port; cert via HTTP-01 on :80 (443 owned by Xray). Verify Traefik can serve cert-bearing TLS on non-443 port while resolving via HTTP-01 on 80; verify `serverNames` match cert |
| Stub site templates (at least 2-3 static sites) with selection var | eGames/others ship several masking templates | Low | Static HTML served by Traefik via small static server container or file provider; allow user-supplied directory |
| firewalld rules and SELinux contexts managed by role | Stated; EL10 specific | Med | Open 80/443/node port; restrict node API port to Panel IP via rich rule; `container_file_t` on volumes (`:Z`), `ip_unprivileged_port_start` sysctl for rootless 80/443 |
| Host hardening: SSH, fail2ban, unattended security updates (dnf-automatic) | Stated; every script has UFW at minimum | Med | Opt-in toggle per sub-feature; protect against locking out (keep current SSH port until verified) |
| Postgres backup on schedule with rotation (systemd timer) | Stated; DigneZzZ scripts set expectation | Med | `pg_dump` via `podman exec` to a dated file, retention N, systemd timer user unit |
| Restore playbook/task | A backup without tested restore is not a feature | Med | Separate explicit playbook (not in normal run); document the procedure; test in Molecule |
| Version upgrades through image tag vars | Stated | Low-Med | Pin tags, pull, restart on change; pre-upgrade backup hook; no `latest` default |
| Idempotency (second run changed=0) | Stated; Molecule `idempotence` step enforces it | High (cross-cutting) | Quadlet files via template, `daemon-reload` only on change via handler; API tasks must be GET-compare-then-write |
| Example inventories and playbooks | Public collection must be usable | Low | `examples/` with Panel + 2 nodes, group_vars skeleton, vault example |
| Secrets via ansible-vault, `no_log` on API tasks | Public collection hygiene | Low | Document vault layout; never print tokens; ship `.example` vault file only |
| README + docs (quickstart, variables reference, architecture, troubleshooting) | Public/community collection | Med | English README (project docs are Russian; decide language policy); role `argument_specs` for auto-validated variable docs |
| Molecule scenarios + CI (ansible-lint, yamllint, molecule) | Stated | High | Quadlet needs systemd in test container: use systemd-enabled EL10 image or VM-based driver (podman-in-podman rootless is tricky); Panel API tests can use a real Panel container |
| Preflight validation (OS, SELinux enforcing, DNS resolves to host, ports free) | Prevents most failed first runs and LE rate-limit burn | Low-Med | `assert` tasks with clear messages; use LE staging toggle |

## Differentiators

Features that set this collection apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Rootless Podman + Quadlet + SELinux enforcing, fully working | No competitor does it; RHEL-family users have no option | High | The central differentiator; document pitfalls solved |
| Declarative Panel API resources as Ansible modules/plugins (e.g. `remnawave_node`, `remnawave_config_profile`, `remnawave_host`, `remnawave_squad`) with `check_mode` and real `changed` reporting | True idempotency, reusable outside the roles, `--check` diff support | High | Python modules using `ansible.module_utils.urls`; or start with `uri` + `set_fact` and promote to modules later. Modules are the strongest quality signal for a "collection" |
| LAN access squad: dedicated inbound + internal squad routed to declared private subnets; all other users blocked from private IPs | Stated unique feature; extremely hard to do right by hand | High | See "LAN routing design" below |
| Default-deny private-IP routing rule for all public inbounds (`geoip:private` to block outbound) | Prevents SSRF/LAN pivot by ordinary users, a real hardening gain | Med | Part of generated Xray config; ordering of routing rules matters |
| Declarative inventory-driven topology: one `remnawave_nodes` list creating node, profile, host, squads end to end | "One command from inventory" core value | High | Resources keyed by name; optional `state: absent` and prune mode |
| Node decommission (`state: absent`: delete node/host, stop units) | vff-remnawave-auto has it; completes lifecycle | Low-Med | Guard behind explicit flag |
| Cert expiry/renewal monitoring and Traefik healthcheck | Self-steal breaks silently if cert expires | Low-Med | Alert via simple systemd `OnFailure=` or documented metric |
| Cloudflare-proxy / DNS sanity check for selfsteal domain (eGames added this) | Prevents mis-deploy where domain is proxied (breaks Reality) | Low | Compare resolved A record with host public IP in preflight |
| Pre-upgrade automatic backup + rollback by previous tag | Safer upgrades | Med | Keep previous tag var; rollback playbook |
| Backup offsite (S3/rsync/SFTP) and optional age encryption | DigneZzZ has it; sensitive DB (user keys) | Med | Optional; keep local rotation as table stakes |
| Panel hidden-path / cookie-auth as Traefik-native feature with documented bypass-safe design | Competes with eGames cookie scheme without nginx | Med | Cookie set via entry URL param needs forward-auth or small middleware; see anti-features re: extra services |
| Node metrics/log rotation and basic Prometheus-friendly exposure | Operations polish | Low-Med | Optional; Panel exposes metrics endpoint with basic auth |
| Reality key/shortId rotation task | Security hygiene | Med | Update profile, bump hosts |
| Marzban/3x-ui migration helper | vff-remnawave-auto has Marzban migration | High | Defer; out of core value |
| Support for multiple stub-site "personalities" per node and per-node domain | Reduces fingerprinting across nodes | Low | Variable per host |

## LAN routing design (feature spec notes)

Goal: one group of users reaches the node's private subnets; everyone else cannot.

- Dedicated inbound with its own **tag** (for example `lan-in`) on a separate port in the same config profile; separate internal squad that contains only that inbound; the LAN users are assigned only to that squad. A host entry points to that inbound.
- Xray routing rules, in order: (1) `inboundTag: [lan-in]` + `ip: [<declared CIDRs>]` -> `direct`; (2) `ip: [geoip:private]` -> `block` for all remaining traffic; (3) default `direct`. Per-inbound tags are the reliable discriminator; per-user (`user` email) routing is an alternative but depends on how Remnawave sets client email, so verify before relying on it (LOW confidence).
- Network dependency: the node container must actually reach the LAN. With rootless Podman, `network_mode: host` is simplest for reachability and real client IPs; pasta/slirp bridged networking adds NAT/source issues. Decision is a STACK/ARCHITECTURE item, but this feature fixes the requirement: host networking for remnanode.
- Must also protect the host itself: block `lan-in` clients from reaching the node's own admin ports/Podman sockets unless intended (the declared CIDRs should exclude the node host, or add a block rule for the node's own address).
- Declared subnets come from an inventory variable (`remnawave_lan_subnets`), rendered into the Xray profile; empty list means the LAN feature is off and only the block rule is emitted.

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Docker/rootful compose support | Contradicts rootless Podman decision; doubles test matrix | Quadlet only; point Docker users to existing roles |
| Ubuntu/Debian, EL8/EL9 support in v1 | Dilutes focus, Quadlet features differ by Podman version | EL10 only; assert on OS in preflight |
| Panel and Node on the same host | Out of scope; port 80/443 and Traefik conflicts | Document that topology is unsupported |
| DNS-01 / Cloudflare-token cert flows | Out of scope for v1; secrets burden | HTTP-01 only; document upgrade path |
| WireGuard/tunnel to LAN | Node sits inside the LAN | n/a |
| Disabling or setting SELinux permissive as a "fix" | Violates core constraint | Ship proper contexts/booleans; document `ausearch` troubleshooting |
| Auto-registering/creating end users and subscriptions | Business data belongs to the operator/billing bot; not infrastructure | Provide only infra resources (nodes, profiles, hosts, squads); users via UI/API/bot |
| Bundling a Telegram bot, billing, or Marzban migration in v1 | Scope creep; separate ecosystem | Link to Awesome Remnawave |
| Interactive menus / bash wizard UX | Anti-declarative; this is the competitors' domain | Inventory-driven only |
| Shipping real secrets, default passwords, or `latest` tags | Public repo safety and reproducibility | Require vault vars; assert if placeholder values remain |
| Extra auth stack (tinyauth, Authelia) installed by default | More moving parts for a login gate | Traefik middlewares only; document tinyauth as optional external |
| Mandatory Galaxy publication gate in v1 | Out of scope per PROJECT.md | Keep metadata Galaxy-ready (galaxy.yml, namespace placeholder) |
| Custom Xray routing GUI/arbitrary routing DSL | Complex surface | Expose Xray config profile JSON override plus the LAN/private-block knobs |

## Feature Dependencies

```
Preflight checks -> everything
Host hardening/firewalld/SELinux baseline -> Podman rootless user + linger + sysctl (ports <1024)
Podman rootless user -> Panel Quadlet units (backend, postgres, valkey) -> Traefik (Panel) with LE HTTP-01
Panel reachable (Traefik) -> Admin bootstrap (register/login) -> API token
API token -> Subscription page (needs token + Panel URL)
API token -> Panel API resource modules (config profile, squad, host, node)
Panel public key (keygen) + node created in Panel -> Node SECRET_KEY -> remnanode Quadlet start
Node domain DNS + port 80 open -> Node Traefik cert (HTTP-01) -> Self-steal (Reality dest) -> Config profile with Reality serverNames/dest
Config profile (inbounds with tags) -> Internal squads -> Hosts -> Subscription output
LAN inbound + LAN squad + routing rules -> requires host network on node + declared subnets
Backup timer -> Restore playbook -> Upgrade (pre-upgrade backup hook)
Panel login protection (Traefik middlewares) -> must exempt subscription domain and node->panel API traffic
Molecule/CI -> all roles (idempotence verifies API modules' GET-compare logic)
```

Ordering hazard: Panel node registration requires Panel up, so the playbook is two plays (Panel first, nodes after), and node plays delegate API calls to the controller (or to the Panel host) via the Panel URL.

## MVP Recommendation

Prioritize (v1 is the stated core value, so table stakes nearly all land in v1):

1. Panel role (Quadlet, Traefik, TLS, secrets, backups) plus preflight and hardening baseline
2. Admin bootstrap, API token, Panel API resources (config profile, squad, host, node) with true idempotency
3. Node role with self-steal, stub site, firewalld/SELinux
4. LAN squad/inbound with private-IP default block (the headline differentiator; Medium-High complexity, build after basic node works)
5. Molecule + CI, examples, docs written alongside each phase, not at the end

Suggested internal ordering: infra roles (Panel, then Node) -> API resource layer -> self-steal -> LAN routing -> restore/upgrade polish -> docs/CI hardening.

Defer:
- Offsite/encrypted backups (S3/age): nice-to-have after local backups and restore are proven
- Reality key rotation, cert monitoring, metrics: v1.x
- Marzban/3x-ui migration: separate project or later milestone
- Promotion of `uri`-based tasks to full Python modules: acceptable to start with `uri` in v1 if idempotency tests pass, but modules are the preferred direction (flag for architecture phase)

## Complexity and Risk Flags for Phase Research

- Self-steal with Traefik (TLS termination on non-443 port reached from Xray `dest`, with HTTP-01 on 80): needs validation spike (HIGH risk)
- Panel API shape for the pinned Panel version (config profiles/inbounds/squads/hosts schema changed across 2.x): verify against OpenAPI before coding (MEDIUM risk)
- Rootless host networking + privileged ports + LAN reachability + real client IP: spike needed (HIGH risk)
- Molecule for Quadlet/systemd-user/SELinux: driver choice affects feasibility (HIGH risk)
- Cookie-auth gate via Traefik without plugins: may require forward-auth helper; IP allowlist and secret-path-only variants are the safe baseline (MEDIUM risk)

## Sources

- [vff-remnawave-auto (Ansible, nodes/panel/subscription/Marzban migration)](https://github.com/ryabkov82/vff-remnawave-auto) - MEDIUM (web search summary)
- [iphizic/remna-playbook](https://github.com/iphizic/remna-playbook) - MEDIUM
- [eGamesAPI/remnawave-reverse-proxy](https://github.com/eGamesAPI/remnawave-reverse-proxy) and [release notes v1.6.1](https://newreleases.io/project/github/eGamesAPI/remnawave-reverse-proxy/release/v1.6.1) - MEDIUM (mirror/secondary source; cookie scheme and selfsteal features)
- [DigneZzZ/remnawave-scripts](https://github.com/DigneZzZ/remnawave-scripts) - MEDIUM (backup/restore feature set)
- [Remnawave official docs: Panel install](https://docs.rw/docs/install/remnawave-panel/), [Node install](https://docs.rw/docs/install/remnawave-node), [tinyauth for nginx](https://docs.rw/docs/security/tinyauth-for-nginx), [Awesome Remnawave](https://docs.rw/docs/awesome-remnawave) - HIGH for existence of components; API endpoint names recalled from domain knowledge, LOW-MEDIUM until checked against Swagger
- Xray routing semantics (inboundTag, geoip:private, rule order) - domain knowledge, MEDIUM; verify in Xray docs during phase research
