# Technology Stack

**Project:** xvpn.remnawave (Ansible collection: Remnawave Panel + Node on EL10, rootless Podman + Quadlet, SELinux enforcing, Traefik)
**Researched:** 2026-11-23
**Overall confidence:** MEDIUM-HIGH (versions verified live against GitHub/PyPI/Galaxy/Docker Hub/Rocky mirrors on 2026-11-23; CI-for-rootless-systemd and SELinux booleans are MEDIUM/LOW, see flags)

> Headline surprise: **Rocky 10.3 ships Podman 6.1.4**, not 5.x. Podman 6 removed slirp4netns, CNI, iptables, BoltDB and cgroups v1, and changed the `podman quadlet` on-disk layout. Older EL10 minors (10.0-10.2) carry Podman 5.x. The collection must work on both lines. `containers.podman` >= 1.21.0 is the first release with Podman 6 support.

## Recommended Stack

### Control node (where `ansible-playbook` runs)

| Technology | Version (verified) | Purpose | Why | Confidence |
|------------|--------------------|---------|-----|------------|
| ansible-core | **2.21.x primary, 2.22 (GA Nov 2026, latest tag v2.22.0) also tested** | Engine | Molecule supports only N/N-1 Ansible = 2.22/2.21. 2.21 runs on Python 3.12-3.14 (works on an EL10 control node, Python 3.12). 2.22 needs controller Python >= 3.13. Target-side Python 3.12 on EL10 is supported by both. | HIGH |
| `requires_ansible` in galaxy/meta | `>=2.20.0` | Collection floor | 2.20 is in security-only support until 2 Nov 2026 and EOL May 2027. Do not claim older cores; do not test them. | MEDIUM |
| Python (controller) | 3.12 (2.21) / 3.13 (2.22) | | Constraint above | HIGH |

### Target host packages (EL10, installed by roles via dnf)

| Package | Version on Rocky 10.3 (verified from mirror) | Purpose | Notes |
|---------|-----------------------------------------------|---------|-------|
| podman | 6.1.4 (10.3); 5.x on 10.0-10.2 | Runtime + Quadlet generator | Declare min supported `podman >= 5.4`; assert via `podman --version` pre-task. |
| netavark / aardvark-dns | 2.1.0 | Container networking + name resolution | Only supported backend (CNI gone in Podman 6 and unsupported in RHEL 10). |
| passt (+ passt-selinux) | 0^20260728 | **pasta** rootless networking | Only rootless net stack on EL10/Podman 6. Preserves client source IP (unlike slirp4netns). |
| container-selinux | 2.250.0 | SELinux policy for `container_t` | Required; do not touch policy modules unless an AVC proves it necessary. |
| crun | 1.30.1 | OCI runtime | Default; cgroups v2 only. |
| firewalld | 2.4.3 | Host firewall | nftables backend (Podman 6 dropped iptables, EL10 is nftables-native). |
| python3-libselinux, python3-policycoreutils | 3.11 | Required by `ansible.posix.seboolean`/`selinux`/`sefcontext` on the target | Python 3.12 on target; install before using those modules. |
| fail2ban (EPEL 10) | 1.1.0 | Hardening | Needs `epel-release`; use `fail2ban-firewalld` + `fail2ban-selinux`. |
| dnf-automatic (BaseOS) | 4.20 | Automatic security updates | Configure `upgrade_type = security`; no extra repo. |

### Container images (pin exact tags; every tag is a role variable)

| Image | Pinned default (2026-11-23) | Purpose | Notes |
|-------|------------------------------|---------|-------|
| `docker.io/remnawave/backend` | **3.4.11** (also `ghcr.io/remnawave/backend`) | Panel API + UI | Floating `:3` and `:latest` exist; never default to them. API contract changes between 3.x minors are possible, so pin and CI-test the pinned version. |
| `docker.io/remnawave/node` | **3.4.6** (`ghcr.io/remnawave/node`) | Xray-core node (`remnanode`) | Official compose uses `:latest`; pin instead. Backend and node versions are released in lockstep (3.4.x); keep them within the same minor. |
| `docker.io/remnawave/subscription-page` | **8.0.1** (Docker Hub tags: `8.0.1`, `8.0.0`, `7.2.6`, `latest`, `dev`) | Subscription page | Separate major line from backend. Needs an API token to talk to the Panel. |
| `docker.io/library/postgres` | **18.4** (what upstream `docker-compose-prod.yml` uses) | Panel DB | PG18 image keeps data under `/var/lib/postgresql` (mount the volume there, NOT `/var/lib/postgresql/data`). `TZ=UTC` mandatory (upstream warns), `shm_size 512mb` equivalent via `ShmSize=`. Do not move to 17/16 without a reason: PG major upgrades are not in-place. |
| `docker.io/valkey/valkey` | **9-alpine** (Valkey 9.2.0 current) | Redis-compatible cache/queue | Upstream already moved from Redis to Valkey. Run with `--save "" --appendonly no --maxmemory-policy noeviction`. Upstream wires it to the backend over a **unix socket on a shared volume** (`REDIS_SOCKET=/var/run/valkey/valkey.sock`, `--unixsocketperm 777`, `--port 0`); replicate with a named Quadlet `.volume` shared by two containers (SELinux: named volumes are auto-labelled; do NOT use host bind mounts for the socket). |
| `docker.io/library/traefik` | **v3.7.19** (v3.8.0-rc.3 exists; do not use RC) | Reverse proxy / TLS terminator | See Traefik section. |
| `docker.io/nginxinc/nginx-unprivileged` | **1.31-alpine** (tag family `1.31.x-alpine`) | Static decoy website behind Traefik | Traefik cannot serve static files itself; needs a tiny backend. Unprivileged variant listens on 8080, fits rootless. Alternative of equal merit: `static-web-server`. |

### Remnawave runtime contract (verified from upstream `main`: `.env.sample`, `docker-compose-prod.yml`, `libs/contract`)

**Backend (`remnawave/backend`)** - ports: `APP_PORT=3000` (API+UI), `METRICS_PORT=3001` (`/health`, `/metrics`, basic-auth `METRICS_USER`/`METRICS_PASS`). Bind published ports to `127.0.0.1` only. Required env: `DATABASE_URL=postgresql://user:pass@remnawave-db:5432/db`, `REDIS_SOCKET` (socket path), `APP_SECRET` (replaces older JWT secrets in v3.4; verify per-version in a phase research), `PANEL_DOMAIN`, `FRONT_END_DOMAIN`, `SUB_PUBLIC_DOMAIN` (e.g. `panel.domain.com/api/sub`, must match the public subscription URL), `POSTGRES_USER/PASSWORD/DB`, `API_INSTANCES=1`. Upstream compose sets `nofile 1048576` (use `Ulimit=nofile=1048576:1048576`). Healthcheck: `curl -f http://localhost:3001/health`. Optional: Telegram/webhook vars (expose as free-form `remnawave_panel_extra_env` dict, do not model each one). Swagger/Scalar live at `/backend-tools/swagger` and `/backend-tools/scalar`.
**Secrets handling:** backend reads plain env, so use Podman secrets (`podman_secret` + Quadlet `Secret=name,type=env,target=VAR`) for `APP_SECRET`, `DATABASE_URL` (as one secret since it embeds the password), `POSTGRES_PASSWORD`, `METRICS_PASS`.

**Node (`remnawave/node`)** - official compose: `network_mode: host`, `cap_add: NET_ADMIN`, `nofile 1048576`, env `NODE_PORT=2222` (Panel-to-node control port; firewall to Panel IP only) and `SECRET_KEY` (obtained from Panel, below). Xray inbound ports (e.g. 443) are defined in the Panel's config profile, not on the node.

**Subscription page (`remnawave/subscription-page`)** - `APP_PORT=3010`, `REMNAWAVE_PANEL_URL` (Panel base URL, internal `http://remnawave:3000` or public https), `REMNAWAVE_API_TOKEN`, `CUSTOM_SUB_PREFIX`, `TRUST_PROXY=1` (Express hop count; keep 1 behind Traefik). If the Panel sits behind an auth gate, `CADDY_AUTH_API_TOKEN` sends `X-Api-Key`; not needed with an IP allowlist.

### Quadlet / Podman features to use

| Feature | Use | Notes |
|---------|-----|-------|
| `.container`, `.network`, `.volume` | Core | One user-defined `.network` for Panel stack gives aardvark-dns name resolution (`remnawave-db`, `remnawave-redis`). Podman 6: network isolation is on by default; fine for this design. |
| `.pod` | Not needed for Panel | A pod forces `PublishPort` onto the pod and conflicts with `Network=host`. Use network + named containers; simpler health/restart semantics per service. |
| `.kube` / `podman kube play` | **Do not use** | Adds a YAML layer and loses per-container Quadlet keys (Secret=, Notify=healthy, HealthCmd). |
| `.image`, `AutoUpdate=` | `.image` optional; `AutoUpdate=` **off** | Version bumps happen by changing role variables (requirement), not by registry drift. |
| `Notify=healthy` + `HealthCmd=` | Yes, for Postgres/Valkey/backend | Gives real systemd ordering (`After=`/`Requires=` on `*.service`) equivalent to compose `depends_on: service_healthy`. |
| `Secret=` | Yes | See above. |
| `Network=host` (node) | Yes | Rootless host networking egresses from the host netns, so LAN routing/source address and Xray's direct outbounds work. Xray binding 443 needs `net.ipv4.ip_unprivileged_port_start <= 443` (host netns sysctl). |
| `Network=pasta` | For Traefik (Panel host) | Rootless default on EL10. Preserves real client IP for Traefik access logs/allowlists. |
| `Pull`/image timeout | Set `TimeoutStartSec=900` in `[Service]` | First start pulls images; default 90 s start timeout kills it (documented pitfall). |
| Search path | `~/.config/containers/systemd/` of the service user (`containers.podman` `quadlet_dir`) | Podman 6 additionally allows `/usr/share/containers/systemd/users/`; not needed. |
| `[Install] WantedBy=default.target` | Yes + `loginctl enable-linger <user>` | Without linger, rootless services die at logout and do not start at boot. |

### Ansible collections

| Collection | Version (Galaxy, verified) | Purpose | Use for |
|------------|---------------------------|---------|---------|
| `containers.podman` | **>=1.21.2** (1.21.0 added Podman 6 support; 1.21.1/.2 are idempotency fixes) | Quadlet + secrets + volumes/networks | `podman_container` with `state: quadlet` (`quadlet_dir`, `quadlet_filename`, `quadlet_file_mode`, `quadlet_options` for raw `[Unit]`/`[Service]`/`[Install]` lines), `podman_network`/`podman_volume` (quadlet mode), `podman_secret`, `podman_quadlet`, `podman_image`. |
| `ansible.posix` | **2.2.2** (`requires_ansible >=2.16`) | `firewalld`, `seboolean`, `sysctl`, `selinux` (assert only), `mount` | Port/rich rules, sysctl.d drop-in for unprivileged ports, SELinux booleans. |
| `community.general` | **14.0.1** | `sefcontext`, `ini_file`, `systemd_creds*`, misc | Only for what `ansible.builtin` lacks. `sefcontext` for custom file contexts if any are ever needed. |
| `ansible.builtin` | core | `template`, `uri`, `systemd_service` (`scope: user`), `dnf`, `user`, `command` | Bulk of the work. |
| `community.postgresql` | **Do not depend on it** (5.1.2 exists) | | Postgres lives in a container with no exposed port; needs psycopg2 on target. Remnawave runs its own migrations. Backups use `podman exec ... pg_dump` from a systemd timer. |
| `community.crypto` | optional | Generating secrets on controller | Prefer `ansible.builtin.password` lookup / `community.general.random_string` only if needed. |

**Quadlet authoring decision (opinionated): render `.container` / `.network` / `.volume` files from your own Jinja2 templates with `ansible.builtin.template`**, then `daemon-reload` and start. Reasons: (1) templates are reviewable diffs for community users and `ansible-lint`/`yamllint` stay out of the way; (2) full access to every Quadlet key (`Notify=healthy`, `Secret=`, `Ulimit=`, `Sysctl=`, `AddCapability=`) without waiting on module option parity; (3) deterministic idempotence (`changed` only when file content changes) and no dependency on the container module's `podman inspect`-based comparison that has had recurring idempotency fixes (1.21.1, 1.21.2 are both such fixes); (4) works identically on Podman 5.x and 6.x. Use `containers.podman.podman_secret` (not quadlet-generating) for secrets, since secrets are not Quadlet units. Keep `podman_container state: quadlet` as a documented alternative only. Confidence: MEDIUM-HIGH (design judgment backed by changelog evidence).

**User-scope systemd from Ansible:** use `ansible.builtin.systemd_service` with `scope: user` and `become_user: <svc_user>`, passing `environment: {XDG_RUNTIME_DIR: /run/user/<uid>}` (and `DBUS_SESSION_BUS_ADDRESS`). Enable linger first (`loginctl enable-linger`, guarded with `creates: /var/lib/systemd/linger/<user>`). Check `systemd --user` is reachable before `daemon-reload`. After writing Quadlet files, validate with `/usr/lib/systemd/system-generators/podman-system-generator --user --dryrun` as a `check_mode`-safe pre-flight task.

### Traefik v3.7 fit assessment (answers the PROJECT.md "verify" question)

**Verdict: YES for both roles, with one structural caveat (loopback TCP, not unix socket).** Confidence: MEDIUM-HIGH for ACME/entrypoint behavior (core documented Traefik features); MEDIUM for the Xray-fallback integration (assembled from Xray Reality docs + Traefik semantics, must be proven in the first Node phase).

- **Panel host:** Traefik `:80` entrypoint (`web`) + `:443` (`websecure`); `certificatesResolvers.le.acme.httpChallenge.entryPoint=web`; `storage` JSON `0600` on a persistent volume. File provider (dynamic config rendered by Ansible) for routers: `panel.<domain>` -> `http://host:3000`, `sub.<domain>` -> `:3010`. **Do not mount the Podman socket or use the Docker/Podman provider** (rootless socket mount under SELinux is a privilege and labelling problem for no benefit). Panel protection via Traefik `ipAllowList` middleware (primary, LAN/admin CIDRs) and/or a secret-path/cookie rule (`HeaderRegexp` on Cookie or `ForwardAuth`). Backend needs forwarded headers (`X-Forwarded-Proto: https`, `X-Forwarded-For`); Traefik sets these by default.
- **Node host (self-steal):** Xray owns `:443` (Network=host). Traefik on the same host listens on **`:80` for HTTP-01** and on a **loopback-only TLS entrypoint, e.g. `127.0.0.1:8443`**, holding the real Let's Encrypt cert for the node's domain, routing to the nginx-unprivileged decoy. Reality `target` (alias `dest`; Xray renamed it, both accepted) = `127.0.0.1:8443`, `serverNames` = [node domain]. Traefik supports TLS 1.3 + h2 by default, which Reality requires of the target. Optional `xver: 1` plus `entryPoints.<name>.proxyPolicy`/`proxyProtocol.trustedIPs=127.0.0.1/32` to pass real client IPs; default to `xver: 0` (fewer moving parts), expose as variable.
- **Caveat:** Traefik entrypoints are TCP/UDP listeners. Popular self-steal guides use nginx/Caddy on a **unix socket** (`/dev/shm/nginx.sock`, `xver:1`); I found no evidence Traefik can do that (LOW confidence it cannot; treat as unsupported). The loopback port approach is functionally equivalent for this threat model; the port must be bound to `127.0.0.1` only (Traefik entrypoint address `127.0.0.1:8443`) and not opened in firewalld. Mark TLS-entrypoint-on-loopback + Xray fallback as the primary spike of the Node phase.
- **Cert bootstrap ordering on Node:** port 80 must reach Traefik with the node domain's A record pointing at the host before Xray is configured; ACME HTTP-01 does not need 443. Xray can start before the cert exists (fallback just fails until issued), but verify issuance in a task (`wait_for` on `acme.json` content / HTTPS probe through 127.0.0.1:8443 with SNI) before registering the inbound as healthy.
- **Rootless ports 80/443:** `ansible.posix.sysctl: net.ipv4.ip_unprivileged_port_start=80` written to `/etc/sysctl.d/` (`reload: true`). This is a host-wide relaxation; document it. Alternative (firewalld redirect 80->8080) is worse for HTTP-01 debugging and breaks `Network=host` Xray on 443, so use the sysctl.
- **Do not use** Traefik v2 (2.11 is the maintenance branch), v3.8 RCs, or the Traefik Hub/Enterprise features. Pin `v3.7.19` (rootless-friendly, official image runs as root inside the userns, which is fine rootless: maps to the unprivileged service user).

### SELinux and firewall (enforcing, no permissive)

| Concern | Approach | Confidence |
|---------|----------|------------|
| Bind mounts of config/ACME storage | `Volume=host:ctr:Z` (private label) for single-container paths, `:z` when shared | HIGH |
| Named volumes (PG data, valkey socket) | Quadlet `.volume`; auto-labelled by Podman; no manual `semanage fcontext` | HIGH |
| Containers connecting to non-standard ports (backend -> node `:2222`, Xray outbound to arbitrary LAN ports) | Likely requires `ansible.posix.seboolean: container_connect_any=on persistent=true` for the node and panel service hosts | MEDIUM: must be proven by AVC (`ausearch -m avc`) in an enforcing VM; this is the single most likely SELinux blocker |
| Xray binding 443 as `container_t` | Possibly allowed (http_port_t); if denied, prefer boolean over custom module | LOW, flag for phase research |
| `SecurityLabelDisable=true`, `--privileged`, `setenforce 0` | **Forbidden** (project constraint) | HIGH |
| firewalld | `ansible.posix.firewalld` with `permanent: true, immediate: true, state: enabled`; Panel host: 80/443 public, SSH; Node host: 80/tcp, 443/tcp+udp as needed, **2222/tcp via rich rule limited to Panel IP**; never open 3000/3001/3010/8443 | HIGH |
| SSH | `sshd_config.d` drop-in, `ansible.builtin.template` + `validate: sshd -t -f %s` | HIGH |

### Panel API from Ansible (verified against `remnawave/backend` `libs/contract`)

Use **`ansible.builtin.uri`** only; no third-party Remnawave collection exists/needed. Base path `/api`. Auth is two-stage:

1. **Bootstrap (first run only):** `GET /api/auth/status`; if no admin, `POST /api/auth/register` `{username, password}` (password >= 24 chars with upper/lower/digit) -> `response.accessToken` (JWT). Else `POST /api/auth/login`.
2. **Mint a long-lived API token:** `POST /api/tokens` `{name, expiresInDays, scopes}` (default scope `["*"]`). This endpoint is **forbidden with an API key; JWT only**. Response `response.token`. Store it on the controller (vault/lookup) and reuse as `Authorization: Bearer <token>`. Tokens have expiry, so the role should detect 401 and re-mint. Same token feeds the subscription-page `REMNAWAVE_API_TOKEN`.
3. **Node registration flow:** `GET /api/keygen` -> `response.secretKey` (this is the node `SECRET_KEY`; Panel-wide, one value for all nodes); `POST /api/config-profiles` (Xray JSON + name) -> get UUID, `GET /api/config-profiles/{uuid}/inbounds` -> inbound UUIDs; `POST /api/nodes` `{name, address, port: 2222, configProfile:{activeConfigProfileUuid, activeInbounds:[uuid]}, countryCode, ...}`; `POST /api/internal-squads` for the LAN squad (squad <-> inbounds mapping; users are added via `/api/internal-squads/{uuid}/bulk-actions/add-users`); `POST /api/hosts` for client-facing host entries.
4. **Idempotency pattern:** `GET` list -> match by `name` (`selectattr`/`json_query`-free `selectattr`) -> `POST` if absent, `PATCH` if differing (compare only owned fields), `changed_when` explicitly; `status_code: [200, 201]`; `no_log: true` on anything carrying tokens/keys; `validate_certs` default true. Wrap in an `include_tasks` per resource.
5. **Reachability:** if the Panel is IP-allowlisted or on a hidden path, run API tasks `delegate_to` the Panel host against `http://127.0.0.1:3000` (add `X-Forwarded-Proto: https` and `X-Forwarded-For: 127.0.0.1` headers: Remnawave expects to be behind an HTTPS reverse proxy; verify exact behavior per version, MEDIUM) rather than punching the allowlist for the controller.
6. **Contract drift:** the API surface is versioned with the backend (3.4.x). Pin the backend tag and keep an API smoke test (Molecule verify) per pinned version. `@remnawave/backend-contract` (npm) and `/backend-tools/swagger` are the schema sources of truth.

### Development / test tooling

| Tool | Version (PyPI, verified) | Purpose | Notes |
|------|---------------------------|---------|-------|
| molecule | **26.11.0** (calver; requires Python >= 3.11) | Scenario runner | Latest Ansible N/N-1 only. |
| molecule-plugins | **26.11.0** with extras `[podman]` and `[vagrant]` | Drivers | Drivers live in `molecule-plugins`; install extras per driver. Do not also install old standalone `molecule-podman` (duplicate entry points break Molecule). |
| ansible-lint | **26.11.0** | Lint | Profile `production`; Same calver stream as Molecule. |
| yamllint | 1.38.0 | YAML lint | |
| pytest-testinfra | 10.2.2 | Optional verifiers | Prefer `ansible.builtin.assert` + `uri`/`command` verifiers (fewer deps); testinfra optional. |

**Test strategy (two tiers; opinionated):**

- **Tier 1: lint + Molecule `podman` driver, on GitHub-hosted `ubuntu-24.04` runners.** Platform image `docker.io/rockylinux/rockylinux:10-ubi-init` (or `geerlingguy/docker-rockylinux10-ansible:latest`, rebuilt 2026-11-22), `systemd: true`/`privileged` for systemd-as-PID1. Use this for: templates render, package/sysctl/firewalld-offline logic, Quadlet files pass `podman-system-generator --dryrun`, idempotence (`changed=0` on second converge), variable validation. **Limits:** the container shares the runner's kernel with SELinux not enforcing on Ubuntu, so SELinux and real nested rootless Podman with `systemd --user` cannot be asserted here. Nested rootless Podman in a privileged container is possible but fragile (needs `/dev/fuse`, subuid/subgid, linger). LOW confidence that it is stable; do not make it the gate.
- **Tier 2: real VM with SELinux enforcing, Molecule `vagrant` driver (libvirt) using box `almalinux/10`** (Vagrant Cloud libvirt box current at 10.2.20260914; `rockylinux/10` box is stale at 2025-06, so use AlmaLinux for the VM tier and run the same role on Rocky via a nightly cloud-image job). GitHub-hosted Linux runners expose `/dev/kvm`, so libvirt works; slower (~10+ min), run on PR to main/nightly, not every push. This tier is the only one that validates the actual requirements: SELinux enforcing, rootless Podman 6 + `systemd --user` + linger, pasta, ports 80/443 sysctl, firewalld. Multi-host scenario (Panel VM + Node VM) enables the full API registration flow end-to-end. MEDIUM confidence (components exist; end-to-end integration unverified); phase research flag.
- Mock Let's Encrypt in CI with **Pebble** (HTTP-01 capable) via Traefik `caServer` override so CI never hits production ACME rate limits. MEDIUM.
- Matrix: ansible-core {2.21, 2.22}; Rocky/Alma {10 current}. Add Podman 5.x only if an older EL10 minor image is retained.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Quadlet authoring | `template` rendering `.container` files | `containers.podman.podman_container state: quadlet` | Option-parity lag, repeated idempotency bugfixes, harder to express `Notify=healthy`/`Secret=`; keep as documented alternative. |
| Orchestration | Individual `.container` + `.network` | `.pod` / `.kube` / podman-compose | Pod forbids PublishPort with host net; kube/compose lose Quadlet-native systemd semantics. |
| Reverse proxy | Traefik v3.7 (project constraint) | Caddy / nginx (what upstream Remnawave docs and most self-steal guides use) | Both have simpler unix-socket + auto-HTTPS stories. Traefik stays because the user mandated it and it works via loopback TCP; reopen the decision only if the Node-phase spike fails. |
| Self-steal target | `127.0.0.1:8443` TCP | unix socket | Traefik lacks unix-socket entrypoints (LOW-confidence claim). |
| Redis | Valkey 9 | Redis 7/8 | Upstream moved to Valkey; licence-clean on EL10. |
| Postgres access | `podman exec pg_dump` | `community.postgresql` | Needs published port + psycopg2; unnecessary. |
| Rootless net | pasta (default) | slirp4netns | Removed in Podman 6; deprecated on RHEL 10. |
| Node network | `Network=host` | pasta + published ports | Xray's dynamic inbounds are defined in the Panel, so published ports would have to track config; host net also gives straightforward LAN egress. Trade-off: NET_ADMIN is only scoped to the userns in rootless; verify what node features need it (see PITFALLS). |
| Test driver | podman + vagrant-libvirt tiers | docker driver, delegated-only | Docker is out of scope; delegated gives no managed lifecycle. |
| Image updates | Variable pin, `AutoUpdate=` off | `podman-auto-update` timer | Requirement: controlled version bumps. |
| Ansible target | EL10 only | EL9 / Debian | Out of scope. |

## Installation

```bash
# Controller (Python 3.12+, ideally a venv / pipx)
python3 -m venv .venv && . .venv/bin/activate
pip install "ansible-core>=2.21,<2.23" \
            "molecule==26.11.0" "molecule-plugins[podman,vagrant]==26.11.0" \
            "ansible-lint==26.11.0" yamllint

# Collection dependencies (galaxy.yml `dependencies` + requirements.yml)
ansible-galaxy collection install \
  "containers.podman:>=1.21.2" \
  "ansible.posix:>=2.2.2" \
  "community.general:>=14.0.1"

# CI VM tier only (ubuntu-24.04 runner)
sudo apt-get install -y qemu-kvm libvirt-daemon-system libvirt-dev vagrant
vagrant plugin install vagrant-libvirt
```

Target hosts (done by the roles, not by hand):

```bash
dnf install -y podman passt passt-selinux container-selinux firewalld \
   python3-libselinux python3-policycoreutils dnf-automatic
dnf install -y epel-release && dnf install -y fail2ban fail2ban-firewalld fail2ban-selinux
```

## Open Items for Phase-Level Research

1. Rootless Xray (`container_t`) binding 443 and connecting to arbitrary LAN ports on SELinux enforcing: required booleans (`container_connect_any`), AVC proof (Node phase).
2. What the node actually needs `NET_ADMIN` for (rootless caps are userns-scoped; Xray core does not need it for plain VLESS+Reality; likely torrent-blocker/nft features) and whether dropping it is safe.
3. Traefik loopback TLS entrypoint as Reality `target`: confirm handshake behavior, ALPN/h2, optional PROXY protocol, and ACME HTTP-01 with Xray holding 443 (Node phase spike).
4. Backend 3.4.x exact env set (`APP_SECRET`, TCP vs socket Redis fallback), reverse-proxy header requirements, API-token scope names (`GET /api/tokens/scopes`).
5. Podman 5.x vs 6.x differences visible to Quadlet files across EL10.0-10.3 (min supported version decision).
6. Vagrant-libvirt on GitHub runners + Molecule vagrant driver two-VM scenario wiring; Pebble integration.

## Sources

- GitHub releases/tags API (queried 2026-11-23): remnawave/backend 3.4.11, remnawave/node 3.4.6, remnawave/subscription-page 8.0.1, traefik/traefik v3.7.19 (v3.8.0-rc.3 pre-release), ansible/ansible v2.22.0, ansible/molecule v26.11.0, ansible/ansible-lint v26.11.0, valkey-io/valkey 9.2.0, podman v6.2.0 / 5.8.10 (repo moved to `podman-container-tools/podman`) - HIGH
- Upstream Remnawave files (raw GitHub `main`): `backend/.env.sample`, `backend/docker-compose-prod.yml`, `node/docker-compose-prod.yml`, `subscription-page/docker-compose-prod.yml` + `.env.sample`, `backend/libs/contract/**` (auth, api-tokens, keygen, nodes, config-profiles, internal-squads, hosts routes and schemas) - HIGH
- Podman v6.0.0 release notes (breaking changes list): https://github.com/podman-container-tools/podman/releases/tag/v6.0.0 - HIGH
- Rocky Linux 10 mirror package listings (podman 6.1.4, passt, netavark 2.1.0, crun 1.30.1, container-selinux 2.250.0, firewalld 2.4.3, dnf-automatic, python 3.12.16) and EPEL 10 (fail2ban 1.1.0): dl.rockylinux.org, dl.fedoraproject.org - HIGH
- containers.podman CHANGELOG + `podman_container` module docs (Quadlet options): https://github.com/containers/ansible-podman-collections - HIGH
- Galaxy API: containers.podman 1.21.2, ansible.posix 2.2.2, community.general 14.0.1, community.postgresql 5.1.2 - HIGH
- Ansible release/maintenance table (core 2.20/2.21/2.22 support windows and Python ranges): https://docs.ansible.com/ansible/devel/reference_appendices/release_and_maintenance.html - HIGH
- Podman Quadlet man page (v6.0.2): https://docs.podman.io/en/v6.0.2/markdown/podman-systemd.unit.5.html - HIGH
- PyPI (molecule, molecule-plugins, ansible-lint, yamllint, pytest-testinfra versions) - HIGH
- Docker Hub tag listings (traefik, valkey, nginx-unprivileged, rockylinux, geerlingguy image) and Vagrant Cloud box API (almalinux/10 libvirt 10.2.20260914; rockylinux/10 stale) - HIGH
- Xray Reality docs https://xtls.github.io/en/config/transports/reality.html and community self-steal guides (unix-socket + xver pattern) - MEDIUM
- Traefik loopback-TLS/ACME/unix-socket-entrypoint conclusions: from documented Traefik behavior and absence of evidence of unix-socket entrypoints - MEDIUM/LOW; verify in spike
- SELinux boolean (`container_connect_any`) and nested rootless-Podman-in-Molecule feasibility: practitioner knowledge, not verified in this session - LOW/MEDIUM
