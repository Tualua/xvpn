# Architecture Patterns

**Domain:** Ansible collection deploying Remnawave Panel + Node (Xray VLESS Reality self-steal, LAN egress group) on EL10, rootless Podman + Quadlet, SELinux enforcing, Traefik
**Researched:** 2026-11-23
**Overall confidence:** MEDIUM. Node compose facts (host network, `NODE_PORT=2222`, `SECRET_KEY` copied from Panel, firewall node port to Panel IP only) were confirmed on docs.rw. Panel REST endpoint names/shapes, Traefik PROXY-protocol behaviour, and rootless/SELinux details come from training knowledge and could not be re-verified (docs.rw API spec/self-steal pages were not fetchable). Items tagged **[VERIFY]** need a spike in the relevant phase.

## Recommended Architecture

Two host types, never co-located (per PROJECT.md): one **Panel host**, N **Node hosts**. Each host has a small number of dedicated rootless users (one per trust domain), each with lingering systemd user manager and Quadlet units in `~/.config/containers/systemd/`.

```
                    Internet / LAN clients
                       |80,443            |80,443 (+LAN-inbound port)
                       v                  v
  PANEL HOST                         NODE HOST
  +-----------------------------+    +-------------------------------------------+
  | user rw-edge                |    | user rw-edge                              |
  |  traefik (Network=host)     |    |  traefik (Network=host)                   |
  |   :80  ACME HTTP-01         |    |   :80 ACME HTTP-01 + redirect             |
  |   :443 TLS, admin gate      |    |   127.0.0.1:9443 TLS + PROXY proto (dest) |
  |   file provider (dynamic/)  |    |  decoy (static site) 127.0.0.1:8080       |
  |        | loopback           |    |        ^ dest 127.0.0.1:9443 (xver=1)     |
  | user rw-panel               |    | user rw-node                              |
  |  [remnawave.network]        |    |  remnanode (Network=host)                 |
  |  backend  127.0.0.1:3000    |    |   Xray :443  public Reality inbound       |
  |  sub-page 127.0.0.1:3010    |    |   Xray :LAN  LAN Reality inbound          |
  |  postgres (net only)        |    |   API  :2222 mTLS+JWT  <-- Panel IP only  |
  |  valkey   (net only)        |    +-------------------------------------------+
  |  backup timer (pg_dump)     |
  +-----------------------------+
        |  Panel ---- HTTPS/mTLS to node:2222 (Panel initiates) ---->  Node
        |  Controller (Ansible) ---- SSH ---> Panel host ---- 127.0.0.1:3000 REST ----> backend
```

Key decisions (opinionated):

1. **Traefik always runs `Network=host`, in its own user (`rw-edge`), with the file provider only (no Podman socket).** Gives real client IP (needed for admin IP allowlist and logs) without rootless port-forwarder quirks, binds 80/443 directly, and is the same role on Panel and Node. Backends are reached on `127.0.0.1:<port>` published by their own rootless user.
2. **Panel data plane (backend, postgres, valkey, subscription page) on one Quadlet `.network` under `rw-panel`.** Postgres/Valkey publish nothing. Backend and sub-page publish only `127.0.0.1`. No `.pod` (independent restarts, health ordering through `After=`/`Requires=`).
3. **remnanode `Network=host`** (matches upstream compose). Best throughput, true client IP, and LAN/egress use the host stack. Trade-off: Xray can reach host loopback/own IPs, so routing must block them (see section 6). pasta/pod variant is a documented alternative, not v1 default **[VERIFY]**.
4. **Env files (0600, templated) instead of Podman secrets** for v1. Same-UID trust makes Podman secrets marginal, and they cannot be updated in place (breaks idempotence).
5. **Ansible talks to the Panel API via SSH delegation to the Panel host and `127.0.0.1:3000`**, not through the public/gated URL. Send `X-Forwarded-Proto: https` and `X-Forwarded-For: 127.0.0.1` headers (the backend refuses plain-HTTP requests lacking them) **[VERIFY]**. The admin gate therefore never blocks automation.

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `common` (hardening) | SSH, fail2ban, dnf-automatic, base firewalld zone, SELinux-enforcing assertion, chrony, sysctl | Host only |
| `podman_rootless` | Install podman/quadlet deps, create service users, subuid/subgid, linger, `net.ipv4.ip_unprivileged_port_start`, user-systemd helper tasks (`deploy_quadlet`, generator dry-run validation, daemon-reload, restart handlers) | Used by every container role via `include_role tasks_from` |
| `traefik` | Static config, ACME HTTP-01 resolver, file-provider `dynamic/` dir, entrypoints, firewalld ports; exposes `add_route` task interface | Backends on loopback; Let's Encrypt |
| `panel` | postgres + valkey + backend Quadlets, `.network`, env/secret generation, admin bootstrap, API token creation, Traefik route + admin-gate middleware | `traefik` (route files), DB/cache, API token file |
| `subscription_page` | sub-page container, route on separate domain, uses API token | backend (via localhost), `traefik` |
| `backup` | systemd user timer + `pg_dump` via `podman exec`, rotation, optional offsite hook, restore doc/task | postgres container |
| `node` | remnanode Quadlet, env (`NODE_PORT`, `SECRET_KEY`), firewalld rich rule for panel IP, sysctl | Panel (inbound only), `traefik`, `selfsteal` |
| `selfsteal` (could live in `node`) | Decoy site container, Traefik node entrypoint `reality` + cert for node domain, readiness wait for cert | `traefik`, Xray dest |
| `node_registration` | Idempotent API sequence: config profile, node, hosts, internal squads; returns `SECRET_KEY`, waits until node connected | Panel API (delegated), `node` role |
| `plugins/modules` + `module_utils` | `remnawave_config_profile`, `_node`, `_host`, `_internal_squad`, `_api_token` (check_mode, diff, no_log) | Panel API |
| `plugins/filter` | `xray_config` builder: inbounds, Reality, routing rules from structured vars | `node_registration` |

### Data Flow

- **Client data path:** Client -> node :443 -> Xray Reality. Authenticated (valid shortId/key) -> VLESS -> routing -> outbound (direct). Unauthenticated or probe -> Xray forwards the raw TLS to `dest` 127.0.0.1:9443 -> Traefik presents the real LE cert for node domain -> decoy site. Probes see a legitimate site.
- **Control path:** Panel -> node:2222 (mTLS + JWT signed by Panel key). Node never calls Panel. Panel pushes Xray config, pulls stats.
- **Provisioning path:** Controller -> SSH -> Panel host -> `127.0.0.1:3000` REST with API token. Token produced once by `panel` role bootstrap, stored 0600 on Panel host (never on the controller).
- **Cert path:** Traefik :80 HTTP-01 -> LE. State in `acme.json` (0600) in `rw-edge` home; persisted volume, so reruns do not re-issue.

### Collection layout

```
xvpn/remnawave/
  galaxy.yml  README.md  meta/runtime.yml (requires_ansible)
  docs/  examples/inventory/{hosts.yml,group_vars/}
  playbooks/  site.yml  panel.yml  node.yml  update.yml  backup_restore.yml
  roles/
    common/            meta/argument_specs.yml
    podman_rootless/   tasks/{main,user,deploy_quadlet,validate}.yml
    traefik/           tasks/{main,add_route}.yml  templates/{traefik.yml,dynamic/*.j2}
    panel/             tasks/{main,db,valkey,backend,bootstrap}.yml
    subscription_page/
    backup/
    node/
    selfsteal/
    node_registration/
  plugins/{modules,module_utils,filter}/
  extensions/molecule/<scenario>/    # collection-level molecule layout
  tests/ (sanity/unit for modules)   .github/workflows/ci.yml
```

Conventions: every role has `meta/argument_specs.yml` (validates inputs, doubles as docs). Variable prefixes `xvpn_<role>_*` (e.g. `xvpn_panel_domain`). No `meta` role dependencies; ordering lives in playbooks (explicit, testable). Image tags are plain vars (`xvpn_panel_backend_image: remnawave/backend:2.x`), optional digest pin. Roles do not know each other: `traefik` exposes `add_route` (params: name, rule, service URL, middlewares), consumed via `include_role ... tasks_from: add_route`.

Molecule: tier 1 (fast, every PR) ansible-lint + yamllint + module unit tests + Molecule with podman/systemd containers for templating, idempotence (`changed=0` second run), and Quadlet validation via `/usr/lib/systemd/system-generators/podman-system-generator --user --dryrun`. Tier 2 (VM-based, EL10 cloud image under KVM) for what containers cannot prove: SELinux enforcing, rootless user systemd, sysctl, firewalld, real 80/443. Use Pebble (ACME test server) in tier 2 with Traefik `caServer` override. **[VERIFY]** runner KVM availability; this is the largest CI risk.

## Panel host details (2)

- Units (`rw-panel`): `remnawave.network`, `remnawave-db.container` (postgres, volume `:Z`, healthcheck), `remnawave-valkey.container`, `remnawave-backend.container` (`After/Requires` db+valkey, `PublishPort=127.0.0.1:3000:3000`, `EnvironmentFile=`), `remnawave-sub.container` (`PublishPort=127.0.0.1:3010:3010`, env `REMNAWAVE_PANEL_URL`, `REMNAWAVE_API_TOKEN`). Valkey vs Redis: follow current upstream compose.
- Generated secrets (JWT secrets, DB password): created once on first run, persisted in the 0600 env file; template uses lookup of existing value so reruns are `changed=0`.
- Traefik routes (file provider): `panel_domain` -> `127.0.0.1:3000`, `sub_domain` -> `127.0.0.1:3010`, both HTTPS with `certResolver`.
- **Admin login protection, ranked:** (a) `ipAllowList` middleware on panel router (default when LAN/VPN reachable); (b) secret-cookie gate using only core Traefik: router A matches `Host && Query(key=X)` with a headers middleware setting `Set-Cookie` plus redirect to `/`; router B (panel) matches `Host && HeaderRegexp(Cookie, ...)`; catch-all returns 404/decoy **[VERIFY: Set-Cookie survives the redirect middleware chain]**; (c) hidden path is NOT recommended (the panel SPA does not support a sub-path). Avoid Traefik plugins (they download from the plugin catalog at start, a supply-chain and offline risk). Never gate the subscription domain (clients fetch it) and never gate API through the Ansible path (loopback).
- Backend `IS_DOCS_ENABLED=false` and metrics bound to loopback.

## Node host details (3)

### Self-steal with Traefik (feasibility: YES, MEDIUM confidence)

Xray inbound (public), schematic:

```json
{ "tag": "vless-public", "port": 443, "protocol": "vless",
  "settings": {"clients": [], "decryption": "none"},
  "streamSettings": {"network": "tcp", "security": "reality",
    "realitySettings": {
      "dest": "127.0.0.1:9443", "xver": 1,
      "serverNames": ["node1.example.com"],
      "privateKey": "...", "shortIds": ["..."] } } }
```

- Traefik node static config: `web` entrypoint `:80` (ACME HTTP-01 + redirect to https), `reality` entrypoint `127.0.0.1:9443` with `proxyProtocol.trustedIPs=["127.0.0.1/32"]`, default TLS options `minVersion: VersionTLS12` (TLS 1.3 and h2 are available by default, which Reality requires of a dest), `certificatesResolvers.le.acme.httpChallenge.entryPoint=web`. Router `Host(node domain)` on `reality` entrypoint -> decoy service `127.0.0.1:8080`. Traefik cannot serve static files itself, so a tiny static container (e.g. nginx-unprivileged or caddy file_server) is the decoy.
- **Why TCP loopback, not unix socket:** upstream Remnawave docs show nginx on a unix socket; Traefik entrypoints cannot listen on unix sockets, so use `127.0.0.1:9443` (not reachable externally, so no firewall hole).
- **xver / proxy protocol:** `xver: 1` makes Xray prepend a PROXY header (v1) on the connection to `dest` so the TLS terminator sees the real client IP (decoy access logs, optional rate limiting). It is optional for masking. If enabled, Traefik MUST have `proxyProtocol` on that entrypoint and trust only 127.0.0.1; if not, TLS handshake fails and the self-steal breaks (loud smoke test: `openssl s_client -connect node:443 -servername node-domain` must return the LE cert). Whether Traefik rejects header-less connections on that entrypoint must be confirmed **[VERIFY]**. Fallback: `xver: 0` and no proxyProtocol (lose client IP in decoy logs only).
- **Cert issuance with 443 owned by Xray:** HTTP-01 uses :80 only, which Xray does not own, so it works. DNS A record for node domain must point to the node. Role waits (bounded retry) for the domain in `acme.json` before declaring Traefik ready; node can start before the cert exists (cert needed only when probes arrive), but the verification task must assert it. LE rate limits: use staging resolver flag in tests.
- **Panel does not push Traefik config.** Traefik/decoy are managed by Ansible only; Panel only controls Xray.

### Rootless networking (80/443, client IP, LAN)

| Concern | `Network=host` (v1 default) | pasta/pod alternative |
|---------|------------------------------|-----------------------|
| Bind 80/443 | Needs `net.ipv4.ip_unprivileged_port_start=80` (sysctl.d, set by `podman_rootless`); alternative nft redirect 80/443 to high ports, preserves source IP but more moving parts | Same sysctl needed for published ports if pod binds <1024 |
| Client IP | Preserved natively | pasta preserves source IP for forwarded ports **[VERIFY]**; slirp4netns/rootlessport on bridge networks historically hid it |
| LAN reachability | Direct, host stack and routes | Outbound via pasta using host addressing; reachable but host-own addresses need `--map-gw` |
| Host loopback exposure | Xray can dial 127.0.0.1 and own IPs: MUST block in routing | Naturally isolated |
| `NET_ADMIN` | Capability is namespaced to the user namespace and does not apply to the host netns, so features needing it (torrent-blocker nftables) will not work **[VERIFY]**; Xray proxying does not need it | Same |
| SELinux | `container_t` binding 443/http_port_t **[VERIFY]**, fall back to documented `semanage port` | Published by Podman, not the container |

SELinux rules of thumb: all bind mounts `:Z` (private) or `:z` (shared across users never needed), no `SecurityLabelDisable`, no `container_use_devices`/boolean loosening in v1; any needed `semanage` change is an explicit, idempotent task (`community.general.seport`, `ansible.posix.seboolean`), never `setenforce 0`. The `common` role asserts `getenforce == Enforcing`.

Firewalld (node): `80/tcp`, `443/tcp`, LAN-inbound port public; `2222/tcp` via rich rule/source zone for Panel IP only. Nothing else; loopback ports need no rules.

## Panel <-> Node communication (4)

- Direction: Panel connects to `node:NODE_PORT` (default 2222). Node API is mTLS with certs generated by Panel and a JWT verified against Panel's public key, all packed in `SECRET_KEY` which the node needs at startup (docs.rw: copied from Panel "Add node", HIGH).
- `SECRET_KEY` retrieval for automation: Panel key endpoint (believed `GET /api/keygen`, returns the key material to embed) **[VERIFY exact shape in v2]**. Treat value as a secret (`no_log`), write only to node env file 0600.
- Firewall: node `2222` restricted to Panel public/LAN IP (docs.rw, HIGH). Panel needs no inbound from nodes.
- Panel -> node address is the node's IP or domain (domain preferred; avoids breakage if IP changes).

## Automated registration data flow (5)

Order matters (each step yields UUIDs consumed by the next):

```
[panel role]   bootstrap admin (register if none, else login) -> POST /api/tokens -> token file (0600)
[registration] 1 x25519 keypair  : read from existing profile if present, else generate (panel tool endpoint
                                   or `xray x25519`) -> never regenerate on rerun
               2 config profile  : POST/PATCH /api/config-profiles {name, config(JSON from filter)}
                                   -> uuid + inbounds[{uuid, tag, port}]
               3 node            : POST/PATCH /api/nodes {name, address, port, configProfile:
                                   {activeConfigProfileUuid, activeInboundsUuids}} -> uuid
               4 SECRET_KEY      : keygen endpoint -> to node role env
               5 hosts           : POST/PATCH /api/hosts (one per inbound: address=node domain,
                                   port, sni=node domain, remark) linking inbound uuid
               6 internal squads : POST/PATCH /api/internal-squads {name, inbounds:[uuids]}
[node role]    render env with SECRET_KEY, start remnanode
[registration] poll GET /api/nodes/{uuid} until connected (bounded retry) -> fail with diagnostics
```
(Endpoint paths and field names are MEDIUM confidence, from training memory of the v2 API; confirm against `/api` OpenAPI of the pinned version. Pin Panel version and test per supported minor.)

**Idempotence pattern (get-or-create-or-patch) implemented in custom modules, not raw `uri`:**
1. Natural keys: profile `name`, node `name`, host `remark`, squad `name`, token `name`. Lookup via list endpoint.
2. Absent -> create (`changed=true`). Present -> compute desired vs actual on a **normalized** subset (sorted keys, ignore server-owned fields, uuids, timestamps, and secrets like generated privateKey that are preserved) -> PATCH only on diff.
3. Generated-once values (Reality private key, shortIds, API token) are read back from the system of record (Panel profile / token file) and never regenerated; the token value is shown once at creation, hence persisted on the Panel host.
4. `check_mode` + `--diff` supported; all secrets `no_log`; HTTP retries on 5xx while backend starts (`until/retries`); wait for `/api/auth/status`-style health before the first call.
5. Do not delete unmanaged objects by default (`state: absent` explicit only). Users are out of scope for the collection (Panel manages users); only squads are.
6. Config JSON built by a filter from structured vars so a rerun produces byte-identical output (stable key order).

Cross-host variable handoff (Node play needs data from Panel play): `node_registration` runs with `delegate_to: <panel host>` and registers `remnawave_node_secret` via `set_fact` on the node host (`delegate_facts` not needed), keeping a single `playbooks/node.yml` per node that works with `--limit`.

## LAN-access design (6)

- **Two inbounds in one config profile** (a Reality inbound cannot share port 443 with another inbound, and per-user routing by email is unreliable): `vless-public` tag, port 443; `vless-lan` tag, separate port (e.g. 8444; still TLS-looking), its own Reality keypair/shortIds, `dest` = same Traefik `127.0.0.1:9443` with the same node domain in `serverNames` (so probes on the LAN port also see the decoy).
- **Internal squads:** `squad-public` -> `[vless-public]`; `squad-lan` -> `[vless-lan]` (optionally also public). Users only receive credentials/links for inbounds in their squads, so non-LAN users cannot even connect to the LAN inbound. A host entry per inbound makes subscription links.
- **Routing rules, ordered (first match wins), `domainStrategy: IPIfNonMatch`** (so a public hostname resolving to a private IP, i.e. DNS rebinding, still hits IP rules):

```json
"rules": [
  {"type":"field","inboundTag":["vless-lan"],"ip":["192.168.10.0/24","10.20.0.0/16"],"outboundTag":"DIRECT"},
  {"type":"field","ip":["127.0.0.0/8","<node-own-IP>/32"],"outboundTag":"BLOCK"},
  {"type":"field","ip":["geoip:private"],"outboundTag":"BLOCK"},
  {"type":"field","protocol":["bittorrent"],"outboundTag":"BLOCK"}
]
```
  The allow-list is the operator's `xvpn_node_lan_subnets` variable; node-own-IP block comes before nothing broader needed because allow rule is first, so place the node-own-IP block **above** the LAN allow rule if the node's address lies inside an allowed subnet (LAN users should not reach the node host's own services). The catch-all default is DIRECT to the Internet. `geoip:private` is built into Xray (no geoip.dat dependency) **[VERIFY list includes link-local/ULA]**.
- Also deny IPv6 private ranges and decide DNS: LAN users may need internal names, resolved via node resolver (freedom outbound) and matched by IP rules afterwards; optional Xray `dns` block with internal server for LAN inbound is a v1.x enhancement.
- Verification tests (e2e): public-squad user fails to reach LAN host and `127.0.0.1:2222`; LAN-squad user reaches allowed subnet only, not other RFC1918 ranges and not node loopback.

## Patterns to Follow

### Pattern 1: Per-trust-domain rootless user + lingering
Users `rw-edge`, `rw-panel`, `rw-node`; `loginctl enable-linger`; tasks run with `become_user` and `XDG_RUNTIME_DIR=/run/user/<uid>`; `ansible.builtin.systemd scope=user`. Quadlet files written to `~/.config/containers/systemd/`; handler does `daemon-reload` then restart only changed units; a validate step runs the Quadlet generator dry-run so syntax errors fail the play instead of silently producing no unit.

### Pattern 2: Dynamic route drop-ins
Roles drop `dynamic/<role>-<name>.yml`; Traefik file provider hot-reloads, so no Traefik restarts on route changes.

### Pattern 3: Versions as variables, update = rerun
Pinned tags in vars, `Pull=missing`, Quadlet file change triggers restart; `playbooks/update.yml` bumps and verifies health. Backup before backend major bump.

### Pattern 4: Health-gated readiness
`wait_for` / `uri` checks after each tier (DB healthy -> backend 200 via loopback -> route 200 via HTTPS -> node connected) so failures point to the layer.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Raw `uri` task chains with `changed_when: true`
Breaks idempotence and leaks secrets. Use purpose-built modules with normalized diffing.

### Anti-Pattern 2: Mounting Podman socket into Traefik / Docker provider
Rootless socket exposure and SELinux fights. Use file provider.

### Anti-Pattern 3: Weakening SELinux to make containers work
Diagnose with `ausearch -m avc`, use `:Z`, targeted `semanage`. Never permissive, never blanket booleans.

### Anti-Pattern 4: Exposing Panel API through the admin gate to automation
Couples provisioning to allowlists/cookies. Use SSH + loopback.

### Anti-Pattern 5: Using the same Reality inbound for LAN and public with email-based routing
Fragile and unauditable. Separate inbound tag + squad.

### Anti-Pattern 6: Role-to-role `meta` dependencies
Hidden ordering, hard Molecule isolation. Orchestrate in playbooks.

## Scalability Considerations

| Concern | 1 node | 10 nodes | 100 nodes |
|---------|--------|----------|-----------|
| Registration | Sequential API calls | `--limit`/serial per node, API calls serialized through Panel host | Batch/`throttle: 1` on registration tasks; consider fewer profile objects (shared profile, per-node reality keys optional) |
| Config profile | One per node | Shared profile per node group, per-node domain via host entries | Same, with group_vars templates |
| Certs | One LE cert/node | LE rate limits fine (distinct domains) | Watch 50 certs/week/registered domain limit; stagger |
| Panel DB | Trivial | Trivial | Backups sized; stats retention tuning |

## Suggested Build Order

1. **Scaffolding + CI skeleton**: `galaxy.yml`, ansible-lint config, Molecule tier-1, argument_specs pattern, tier-2 VM harness decision (EL10 + SELinux enforcing). Foundation for "changed=0" gate on everything.
2. **`common` + `podman_rootless`**: users, linger, sysctl, firewalld base, SELinux assertion, `deploy_quadlet` helper with generator validation. Prove a hello-world Quadlet on enforcing EL10.
3. **`traefik`** (host network, file provider, ACME HTTP-01 against Pebble/staging, `add_route`). **Parallel risk spike:** Xray Reality `dest` -> Traefik `:9443` with `xver`/proxyProtocol on EL10 (hand-written config), because the whole project hinges on it. If it fails, revisit the Traefik decision (PROJECT.md allows this).
4. **`panel`**: network, db, valkey, backend, env secrets, route + admin gate, bootstrap admin + API token.
5. **API modules + `subscription_page`**: client library, `remnawave_api_token` etc.; sub-page needs the token.
6. **`backup`**: timer, rotation, restore test (needs running DB).
7. **`node` + `selfsteal`**: remnanode host-network Quadlet, firewall rule, decoy, Traefik node entrypoint; first with manually supplied `SECRET_KEY`.
8. **`node_registration`**: config profile, node, hosts, squads, secret handoff, connected-wait; xray config filter; idempotence tests.
9. **LAN access**: second inbound, squads, routing rules, negative/positive reachability e2e.
10. **Hardening completion, update playbook, docs/examples, full e2e VM matrix (Rocky + Alma 10).**

Dependencies: 2 -> everything; 3 -> 4 and 7; 4 -> 5, 6, 8; 7 + 5 -> 8; 8 -> 9.

## Research Flags

| Phase | Flag |
|-------|------|
| Spike in 3 | Traefik PROXY protocol behaviour with Xray `xver`; Reality + Traefik TLS handshake compat (HIGH priority) |
| 2/7 | Rootless host-network: 443 bind under SELinux, `NET_ADMIN` effect, client IP |
| 4 | Admin cookie-gate with core Traefik middlewares; backend forwarded-header requirement; Postgres/Valkey versions per pinned Panel |
| 5/8 | Exact v2 REST contract (keygen, config-profiles, nodes, hosts, internal-squads, x25519) from OpenAPI of pinned version |
| 1 | CI feasibility of SELinux-enforcing rootless tests (KVM runners) |
| 9 | Xray `geoip:private` coverage, node-own-IP blocking, DNS behaviour for LAN names |

## Sources

- https://docs.rw/docs/install/remnawave-node (fetched; HIGH for node compose, port 2222, SECRET_KEY origin, firewall advice)
- https://docs.rw/docs/install/reverse-proxies/nginx (fetched; MEDIUM, nginx reverse-proxy shape only)
- Remnawave backend OpenAPI / docs.rw `/api` (NOT retrievable this session; endpoint names are from training knowledge, LOW-MEDIUM until verified)
- Xray-core Reality/routing docs, Traefik v3 entrypoint proxyProtocol/ACME docs, Podman Quadlet/pasta docs (training knowledge, MEDIUM; verify during phase research)
