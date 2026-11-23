## Язык общения

Всё общение с пользователем в этом проекте (вопросы, статусы, отчёты, пояснения) — на русском языке. Код, пути, технические термины и промпты субагентов остаются на английском. Для GSD это закреплено как `response_language: "ru"` в `.planning/config.json`.

<!-- GSD:project-start source:PROJECT.md -->

## Project

**xvpn.remnawave — Ansible-коллекция для Remnawave**

Публичная Ansible-коллекция `xvpn.remnawave` с ролями для развёртывания Remnawave Panel и Remnawave Node на Rocky/Alma Linux 10 (SELinux enforcing, rootless Podman + Quadlet). Ноды используют VLESS Reality в режиме self-steal: Reality указывает на собственный домен ноды, за ним стоит правдоподобный сайт-заглушка. Отдельная группа клиентов может через ноду выходить во внутреннюю сеть (LAN), в которой стоит нода. Коллекция предназначена для сообщества (open source) и для любого, кто поднимает Remnawave на RHEL-совместимых хостах.

**Core Value:** Из inventory одной командой получается рабочая, защищённая и идемпотентная инсталляция Remnawave: Panel за прокси с защищённым входом, ноды автоматически зарегистрированы через API, Reality self-steal без внешних «чужих» доменов, и всё это работает на RHEL 10 с SELinux enforcing без ослабления безопасности.

### Constraints

- **Платформа**: Rocky Linux 10 / AlmaLinux 10 — единственная целевая ОС v1
- **Безопасность**: SELinux enforcing обязателен, permissive не допускается
- **Рантайм**: rootless Podman + Quadlet (systemd user units), без Docker
- **Прокси**: Traefik, если технически подходит для self-steal и Panel; иначе решение пересматривается с обоснованием
- **TLS**: Let's Encrypt через HTTP-01 на порту 80
- **Топология**: Panel на отдельном хосте, ноды на других хостах
- **Качество**: идемпотентность, Molecule + CI, ansible-lint
- **Публичность**: коллекция open source и должна быть понятна внешним пользователям (README, примеры inventory)

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

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

### Traefik v3.7 fit assessment (answers the PROJECT.md "verify" question)

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

### Development / test tooling

| Tool | Version (PyPI, verified) | Purpose | Notes |
|------|---------------------------|---------|-------|
| molecule | **26.11.0** (calver; requires Python >= 3.11) | Scenario runner | Latest Ansible N/N-1 only. |
| molecule-plugins | **26.11.0** with extras `[podman]` and `[vagrant]` | Drivers | Drivers live in `molecule-plugins`; install extras per driver. Do not also install old standalone `molecule-podman` (duplicate entry points break Molecule). |
| ansible-lint | **26.11.0** | Lint | Profile `production`; Same calver stream as Molecule. |
| yamllint | 1.38.0 | YAML lint | |
| pytest-testinfra | 10.2.2 | Optional verifiers | Prefer `ansible.builtin.assert` + `uri`/`command` verifiers (fewer deps); testinfra optional. |
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

# Controller (Python 3.12+, ideally a venv / pipx)

# Collection dependencies (galaxy.yml `dependencies` + requirements.yml)

# CI VM tier only (ubuntu-24.04 runner)

## Open Items for Phase-Level Research

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

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
