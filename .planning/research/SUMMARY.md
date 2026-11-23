# Project Research Summary

**Project:** xvpn.remnawave (Ansible collection deploying Remnawave Panel and Node on EL10)
**Domain:** Infrastructure-as-code for a VLESS/Reality VPN control plane: rootless Podman + Quadlet, SELinux enforcing, Traefik, firewalld
**Researched:** 2026-11-23
**Overall confidence:** MEDIUM

## Executive Summary

This is an Ansible collection that deploys two kinds of hosts: one Remnawave **Panel** host (backend, Postgres, Valkey, subscription page, Traefik edge) and N **Node** hosts (remnanode/Xray, a Traefik-fronted decoy site for Reality self-steal). Every container runs as a rootless Podman service under a dedicated lingering user, managed by Quadlet unit files rendered from Jinja2 templates. The collection then drives the Panel REST API to create config profiles, nodes, hosts and internal squads idempotently. No existing public project combines rootless Podman/Quadlet, SELinux enforcing, declarative Panel-API resource management and Molecule CI; that combination is the differentiator. Experts building this today would pin every image tag, keep the Panel on loopback behind a single TLS edge, and treat the Panel API as the source of truth for generated Reality keys and tokens.

The recommended approach is opinionated: target EL10 only (Rocky/Alma 10); pin Remnawave backend 3.4.11, node 3.4.6, subscription-page 8.0.1, Postgres 18.4, Valkey 9, Traefik v3.7.19 and nginx-unprivileged 1.31; render Quadlet files with `ansible.builtin.template` rather than `containers.podman.podman_container`; use `ansible.builtin.uri` for the Panel API only until idempotency is proven, then promote to custom modules; put Traefik and remnanode on `Network=host`; use Traefik's file provider only (no Podman socket); and keep `xver: 0` for the Reality dest. Build order follows the dependency chain: rootless plumbing, then Traefik and Panel, then the self-steal node, then API registration, then LAN routing, then backups, hardening and CI polish.

The key risks are (1) the self-steal path (Reality `dest` to a Traefik TLS entrypoint on loopback), which the whole project hinges on and which has no verified precedent with Traefik; (2) SELinux and rootless-runtime behaviour, which cannot be validated in container-based CI and needs a VM-based test tier; and (3) Remnawave API and environment drift between versions, which must be checked against the pinned backend before any API task is written. Mitigations are a Phase 0/2 spike with hand-written configs, a VM Molecule tier (AlmaLinux/Rocky 10 with SELinux enforcing), generate-once secret handling, and version-pinned API adapters.

## Key Findings

### Recommended Stack

The stack is an Ansible-core 2.21 (2.22 also tested) controller with `containers.podman >= 1.21.2`, `ansible.posix >= 2.2.2` and `community.general >= 14.0.1`. The target EL10 host gets Podman (6.1.4 on Rocky 10.3; 5.x on 10.0 to 10.2, so the floor is `podman >= 5.4`), netavark, passt/pasta, container-selinux, crun, firewalld and the python SELinux bindings. Rootless networking is pasta, because slirp4netns is gone in Podman 6. Remnawave-side versions are pinned in role variables, never floating tags.

**Core technologies:**
- **Podman 5.4+/6.x with Quadlet**: rootless runtime and systemd integration; the only supported container path on EL10.
- **Remnawave backend 3.4.11 / node 3.4.6 (kept on the same minor) / subscription-page 8.0.1**: the Panel and Xray node; backend and node are released in lockstep.
- **Postgres 18.4 and Valkey 9-alpine**: Panel DB and cache. Postgres 18 mounts data at `/var/lib/postgresql`, not `/data`. Valkey is upstream's Redis replacement and is wired over a unix socket on a shared named volume.
- **Traefik v3.7.19**: Panel TLS edge (ACME HTTP-01, file provider, IP allowlist) and node-side TLS terminator for the decoy on `127.0.0.1:8443`. Do not use v3.8 RCs or v2.
- **nginx-unprivileged 1.31-alpine**: static decoy site behind Traefik (Traefik cannot serve static files itself).
- **Molecule 26.11.0 + molecule-plugins + ansible-lint 26.11.0**: lint, plus a container tier (not a gate) and a VM tier (the real gate).

### Expected Features

**Must have (table stakes):**
- Panel stack as Quadlet units (backend, Postgres, Valkey) on a private network, with healthchecks, `Notify=healthy` ordering and linger
- Traefik fronting the Panel with Let's Encrypt HTTP-01 and a persistent `acme.json` (0600)
- Generate-once secrets (APP_SECRET, DB password, metrics credentials) that survive reruns
- First-admin bootstrap (register only while no admin exists, else login) and a long-lived API token
- Subscription page on its own domain, using the API token
- Panel protection: at minimum an IP allowlist; subscription and node-to-panel paths must stay reachable
- Node role: remnanode as a Quadlet unit with `SECRET_KEY` and `NODE_PORT=2222`, firewalld restricting 2222 to the Panel IP
- Node registration via the Panel API: config profile (VLESS Reality, xtls-rprx-vision), node, hosts, internal squads
- Self-steal: Reality `dest` to local Traefik with a real cert and a stub site
- firewalld and SELinux contexts managed by the role; host hardening (SSH, fail2ban, dnf-automatic) as opt-in toggles
- Postgres backup on a systemd timer with rotation, plus a tested restore procedure
- Pinned-tag upgrades via role variables; idempotence (second run `changed=0`) enforced by Molecule
- Examples, `no_log` on token/key tasks, vault layout, README

**Should have (differentiators):**
- Declarative Panel API resources as custom modules with `check_mode`, `--diff` and real `changed`
- LAN-access squad: dedicated `vless-lan` inbound on a separate port, its own squad, routing rules that allow declared subnets and block private, loopback and node-own addresses for everyone else
- Default-deny private-IP routing for all public inbounds (`geoip:private`, loopback, link-local)
- Inventory-driven topology (one `remnawave_nodes` list creating everything end to end)
- Node decommission (`state: absent`, behind an explicit flag)
- Pre-upgrade backup with rollback to the previous tag
- Stub-site templates selectable by variable; cert-expiry monitoring; Cloudflare-proxy DNS sanity check

**Defer (v2+ / v1.x):**
- Offsite/encrypted backups (S3, age), Reality key rotation, metrics exposure
- Marzban/3x-ui migration helper
- Cookie/secret-path gate on the Panel (LOW confidence; ship IP allowlist first)
- DNS-01 cert flows, EL8/9 or Debian support, Panel and Node on the same host, bundling a bot or billing

### Architecture Approach

Two host types, never co-located. Each host runs a small set of dedicated rootless users (`rw-edge`, `rw-panel`, `rw-node`), each with lingering systemd user units under `~/.config/containers/systemd/`. Traefik runs `Network=host` in `rw-edge` on both hosts, using the file provider only. On the Panel, backend and subscription page publish only on `127.0.0.1`; Postgres and Valkey publish nothing. On the Node, remnanode runs `Network=host` (matches upstream), and Xray's `dest` points at Traefik's loopback TLS entrypoint. Ansible reaches the Panel API by SSH-delegating to the Panel host and calling `127.0.0.1:3000`, so the admin gate never blocks automation. The Panel connects to the node on 2222; the node never calls the Panel.

**Major components:**
1. **`common` / `podman_rootless`**: users, linger, subuid/subgid, sysctl `ip_unprivileged_port_start=80`, firewalld baseline, SELinux-enforcing assertion, and one shared helper for user-scope systemd and Quadlet dry-run validation
2. **`traefik`**: static and dynamic config, ACME resolver, entrypoints, and an `add_route` task interface consumed by other roles via `include_role tasks_from`
3. **`panel`**: `.network`, Postgres, Valkey, backend Quadlets; env files (0600); bootstrap admin; token creation
4. **`subscription_page`**: sub-page container and route, using the token
5. **`selfsteal` / `node`**: decoy static container, Traefik `reality` entrypoint, remnanode Quadlet, firewall rules, cert-readiness wait
6. **`node_registration` + `plugins/modules` + `plugins/filter`**: idempotent get/diff/patch of config profile, node, hosts and squads; Xray config builder filter with stable key order
7. **`backup`**: user timer, `podman exec pg_dump` with pipefail and temp-file-then-move, rotation

### Critical Pitfalls

1. **Client source IP lost under bridge networking, so the Traefik IP allowlist fails silently.** Put Traefik on `Network=host` (or a pasta pod sharing localhost); add a Molecule check that the access log records a real source address.
2. **Reality dest exposes Traefik's default cert and 404.** Set the TLS store default cert to the node-domain LE cert, add a catch-all decoy router, bind the internal entrypoint to `127.0.0.1` only, and gate Reality enablement on an `openssl s_client` check with the real SNI, a random SNI and no SNI.
3. **PROXY-protocol (`xver`) mismatch between Xray and Traefik.** Default to `xver: 0`; enable only with `proxyProtocol.trustedIPs=127.0.0.1/32` and a probe-based verify.
4. **Rootless ports below 1024 and the host-global sysctl.** Set `ip_unprivileged_port_start=80` persistently and live before the first container start; document the tradeoff; assert it in verify.
5. **`systemctl --user` from Ansible (bus, XDG, linger race, ACL).** Use one shared helper that enables linger, waits for `/run/user/UID/bus`, and sets `XDG_RUNTIME_DIR`/`DBUS_SESSION_BUS_ADDRESS`; use `state: started`, never `enabled:`, on generated units; install `acl`.
6. **Silent Quadlet generator failures and boot-ordering races.** Dry-run the generator as the target user and fail the play on errors; `Restart=always` with `RestartSec`; a `user@UID.service` drop-in ordered after `network-online.target`; a reboot test in the VM tier.
7. **Secrets rotated on every run, and API non-idempotency (duplicate nodes, rotated Reality keys, Xray restarts).** Generate once and read back; diff normalised JSON before any PATCH; never regenerate x25519 keys or shortIds; persist the API token 0600 on the Panel host.
8. **Admin registration race and missing proxy headers.** Start the Panel on loopback, create the admin there, and only then publish the Traefik router; send `X-Forwarded-Proto: https` and `X-Forwarded-For` on loopback API calls and healthchecks.
9. **LAN leaks: private IPs, domain-to-private-IP bypass, shared DNS.** Use a generated routing block with `domainStrategy: IPIfNonMatch`; loopback/link-local/node-own blocks; negative tests from a non-LAN user (`127.0.0.1:22`, internal names).
10. **Container-based CI cannot prove SELinux, rootless systemd or reboot behaviour.** Use a VM tier (libvirt, AlmaLinux 10 and Rocky 10, SELinux enforcing, zero AVC lines) as the real gate; containers only for fast checks.

## Implications for Roadmap

Based on the dependency chain (`common/podman_rootless` before everything; Traefik before Panel and Node; Panel before API registration; node before registration; registration before LAN), the suggested phase structure is eight phases. Phase numbers are suggestions for the roadmapper.

### Phase 0: Rootless foundation and harness spike
**Rationale:** Every later role depends on the user/linger/XDG helper, the sysctl for ports 80/443, Quadlet validation, and a working VM test tier. Deciding these first avoids rewrites.
**Delivers:** `common` and `podman_rootless` roles; a hello-world Quadlet on enforcing EL10; `galaxy.yml` skeleton, ansible-lint and yamllint config; VM Molecule scenario (AlmaLinux 10 / Rocky 10 via libvirt) with a reboot check; `getenforce` and zero-AVC assertions; decision recorded on Podman 5.x vs 6.x minimum.
**Addresses:** firewalld and SELinux baseline; idempotence foundation; preflight checks
**Avoids:** Pitfalls 4, 5, 6, 7, 14, 20, 24

### Phase 1: Traefik edge and Panel stack
**Rationale:** The Panel is the control plane for everything after it. Traefik on `Network=host` settles the source-IP question before any allowlist is written.
**Delivers:** Traefik role (static config, ACME HTTP-01 against LE staging first, file provider, `add_route`); Panel `.network`, Postgres 18.4, Valkey 9, backend 3.4.11 Quadlets; generate-once env files; loopback-only backend publish; ipAllowList admin gate; loopback-first admin bootstrap; subscription page route (container only).
**Uses:** Traefik v3.7.19, Postgres 18.4, Valkey 9, backend 3.4.11, subscription-page 8.0.1; `ansible.builtin.template` for Quadlet files
**Implements:** `traefik`, `panel`, `subscription_page` (container part) components
**Avoids:** Pitfalls 1, 8, 9, 10, 16, 19

### Phase 2: Self-steal spike and remnanode (node host)
**Rationale:** This is the highest-risk integration in the project. Hand-written configs should prove Reality-to-Traefik on loopback before the role is built. If the spike fails, revisit the Traefik decision (PROJECT.md allows this).
**Delivers:** Spike result documented; Traefik `reality` entrypoint on `127.0.0.1:8443`; nginx-unprivileged decoy with at least two stub templates; node-domain cert in the TLS default store; remnanode `Network=host` Quadlet started with a manually supplied `SECRET_KEY`; firewalld rich rule (2222 from Panel IP only); `s_client` verification with correct, random and absent SNI.
**Uses:** remnanode 3.4.6, nginx-unprivileged, Traefik
**Implements:** `selfsteal` and `node` components
**Avoids:** Pitfalls 2, 3, 21, 25

### Phase 3: Panel API layer and node registration
**Rationale:** Registration depends on a running Panel (Phase 1) and a node (Phase 2). Idempotency rules must be enforced at this layer.
**Delivers:** Token bootstrap (mint via `/api/tokens` with JWT, persist 0600 on Panel host); `keygen` secret handoff with `no_log`; config-profile builder filter (stable key order); idempotent get/diff/patch for config profile, node, hosts and internal squads; wait-for-connected with bounded retries; subscription page wired to the token; version adapter keyed to the pinned backend.
**Uses:** `ansible.builtin.uri` first, then `plugins/modules` once tests pass
**Implements:** `node_registration`, `plugins/modules`, `plugins/filter`
**Avoids:** Pitfalls 11, 12

### Phase 4: LAN access squad
**Rationale:** Depends on a working node with the public inbound and the registration flow. It is the headline differentiator, but it is a security feature that needs negative tests.
**Delivers:** `vless-lan` inbound on a separate port with its own Reality keys; `squad-lan` and `squad-public`; ordered routing rules (node-own-IP block above the LAN allow rule, loopback/link-local/`geoip:private` blocks, bittorrent block, default direct); `domainStrategy: IPIfNonMatch`; e2e tests from public and LAN test users.
**Avoids:** Pitfall 13

### Phase 5: Backups, restore and upgrades
**Rationale:** Needs a running DB (Phase 1) and a pinned-tag mechanism. Standard patterns, but a backup that has never been restored is not a feature.
**Delivers:** user timer running `podman exec pg_dump` with pipefail and temp-then-move; rotation that keeps the last N good backups; env/secret backup handling; separate restore playbook tested in the VM tier; pre-upgrade dump when the desired tag differs from the running image; Postgres major-upgrade guard.
**Avoids:** Pitfalls 17, 18

### Phase 6: Host hardening
**Rationale:** Last among the functional phases because lockout risk is highest here and it should not block the Panel and Node work.
**Delivers:** sshd drop-in with `validate: sshd -t`; fail2ban (EPEL, systemd backend, firewalld action); dnf-automatic security-only; full firewalld allow/deny tests.
**Avoids:** Pitfalls 15, 23

### Phase 7: CI hardening, examples and docs
**Rationale:** Docs and examples are written alongside each phase, but final CI matrix and release polish come last.
**Delivers:** ansible-core 2.21/2.22 matrix; Pebble for ACME in CI; idempotence and AVC-zero gates in the VM tier; examples (Panel plus two nodes, vault example); README and variable reference from `argument_specs`; decision on collection namespace.
**Avoids:** Pitfalls 20, 22, 24

### Phase Ordering Rationale

- Phase 0 first because every role uses the same rootless helper and the test harness decision gates everything.
- Traefik and Panel (Phase 1) before the node, because node registration requires a reachable Panel and the subscription page requires the token.
- The self-steal spike (Phase 2) runs as early as possible because it is the riskiest integration; it can run in parallel with Phase 1 as a hand-written-config spike.
- API registration (Phase 3) sits after both the Panel and a node exist, which mirrors the required data flow (keygen, profile, node, hosts, squads).
- LAN (Phase 4) is deliberately late: it needs the public inbound and registration working, and it is a security feature that must not be rushed.
- Backups (Phase 5) and hardening (Phase 6) are independent of each other and can be reordered if needed.

### Research Flags

Phases likely needing deeper research during planning (`/gsd:plan-phase --research-phase <N>`):
- **Phase 0:** Podman 5.x vs 6.x differences visible to Quadlet on EL10.0 to 10.3; whether GitHub-hosted runners expose KVM reliably for the libvirt tier; `user@.service` drop-in details for boot ordering.
- **Phase 2:** HIGH priority. Reality-to-Traefik handshake on loopback (TLS 1.3/h2, ALPN, `xver` behaviour); whether remnanode needs `NET_ADMIN` in rootless mode; SELinux `container_connect_any` and port-443 binding for `container_t`; default-cert behaviour under unknown SNI.
- **Phase 1:** Admin gate. The ipAllowList baseline is standard; any cookie or secret-path gate is LOW confidence and needs a spike before it becomes a requirement. Also verify backend forwarded-header requirements and exact env set at 3.4.11 (`APP_SECRET` vs the older JWT secrets).
- **Phase 3:** Exact REST contract (keygen, config-profiles, nodes, hosts, internal-squads, x25519 generation, token scopes) must be read from the OpenAPI/Swagger of backend 3.4.11 before any task is written. Endpoint names in FEATURES and ARCHITECTURE are recalled from memory.
- **Phase 4:** Xray routing semantics at the node image's Xray version, `geoip:private` coverage (link-local, ULA), and DNS behaviour for LAN names.

Phases with standard patterns (skip research-phase):
- **Phase 5:** Backup and restore via `pg_dump` in a container; well-understood.
- **Phase 6:** sshd, fail2ban, firewalld and dnf-automatic are documented EL patterns; only the EPEL and firewalld-action details need a quick check.
- **Phase 7:** Matrix, lint and docs are standard tooling.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Versions and package sets verified live against GitHub, PyPI, Galaxy, Docker Hub and Rocky mirrors on 2026-11-23. Remnawave env/API details verified against upstream `main`, not the pinned tag. SELinux booleans and nested-Podman CI are LOW/MEDIUM. |
| Features | MEDIUM | Competitor landscape from web search summaries and domain knowledge. Remnawave API endpoint names are unverified (LOW-MEDIUM) until checked against the pinned Swagger. |
| Architecture | MEDIUM | Node compose facts confirmed on docs.rw. Traefik PROXY-protocol behaviour, rootless/SELinux details and REST shapes are from training knowledge and marked [VERIFY]. |
| Pitfalls | MEDIUM | Written from training knowledge without live doc fetches. HIGH on mechanism (systemd, Quadlet, Ansible) but MEDIUM on Remnawave- and Traefik-specific behaviour. |

**Overall confidence:** MEDIUM. Stack choices are well-grounded. The architecture is coherent, but its load-bearing integration (Reality to Traefik on loopback, rootless networking under SELinux) and the Remnawave API contract are not yet verified.

### Source conflicts to resolve during planning

- **Podman version on EL10:** STACK (verified from Rocky 10.3 mirror) says 6.1.4 ships on 10.3 and 5.x on 10.0 to 10.2. PITFALLS says "EL10 ships Podman 5.x". Treat STACK as authoritative; support both (`podman >= 5.4`).
- **Traefik networking:** STACK proposes pasta; ARCHITECTURE and PITFALLS propose `Network=host`. Use `Network=host` for Traefik on both hosts.
- **Secrets delivery:** STACK recommends Podman secrets (`Secret=`); ARCHITECTURE recommends 0600 env files for v1 because secrets cannot be updated in place without breaking idempotence. Use env files for v1.
- **Remnawave secret variables:** STACK says `APP_SECRET` replaces the older JWT secrets in v3.4; PITFALLS names `JWT_AUTH_SECRET` and `JWT_API_TOKENS_SECRET`. Verify against backend 3.4.11 before writing the env template.
- **Reality `dest` port:** ARCHITECTURE uses `127.0.0.1:9443`; STACK and PITFALLS use `127.0.0.1:8443`. Use `127.0.0.1:8443` and make it a variable.
- **`xver`:** STACK and PITFALLS default to `xver: 0`; ARCHITECTURE's example shows `xver: 1`. Default to `xver: 0`.
- **LAN routing order:** FEATURES places the LAN allow rule first; ARCHITECTURE places the node-own-IP block above it when the node address falls inside an allowed subnet. Use the ARCHITECTURE ordering.
- **Quadlet authoring:** STACK recommends templates over `containers.podman.podman_container state: quadlet`; the other files are consistent with templates. Record the decision.

### Gaps to Address

- **Reality over Traefik loopback TLS:** not verified end to end. Address with the Phase 2 spike (hand-written configs first). Fallback: revisit Traefik.
- **Remnawave REST contract at 3.4.11:** endpoint names, payload shapes, token scopes (`GET /api/tokens/scopes`), keygen semantics (panel-wide vs per-node), and whether the backend requires forwarded headers from loopback. Read the pinned OpenAPI at the start of Phase 3.
- **Remnawave env set at 3.4.11:** `APP_SECRET` vs the older JWT secret variables; the exact required list. Preflight should compare the env template against the pinned image's documented variables.
- **Node `NET_ADMIN` requirement:** unknown whether remnanode features need it in rootless mode. Test in Phase 2 by running the node without it and checking logs.
- **SELinux for `container_t`:** whether binding 443 and connecting to arbitrary LAN ports need `container_connect_any` or `semanage port`. Make changes only where AVC logs prove them necessary (Phase 0 VM tier and Phase 2).
- **Cookie or secret-path Panel gate:** no verified Traefik-native approach without plugins. Ship the ipAllowList baseline; treat the cookie gate as a Phase 1 spike that may be deferred.
- **CI feasibility:** whether GitHub-hosted runners provide reliable KVM for the libvirt tier, and whether Molecule vagrant wiring works for a two-VM scenario. Address in Phase 0 and Phase 7.
- **Xray version in the node image:** `geoip:private` coverage and post-resolution blocking depend on the image's Xray build. Address in Phase 4.
- **Reboot survival with linger and `user@.service` ordering:** drop-in approach is MEDIUM confidence. Address with a reboot test in the Phase 0 VM tier.

## Sources

### Primary (HIGH confidence)
- GitHub releases/tags API (queried 2026-11-23): remnawave/backend 3.4.11, remnawave/node 3.4.6, remnawave/subscription-page 8.0.1, traefik v3.7.19, ansible-core v2.22.0, molecule and ansible-lint v26.11.0, valkey 9.2.0, podman v6.2.0 / 5.8.10
- Upstream Remnawave files on `main`: `backend/.env.sample`, `backend/docker-compose-prod.yml`, `node/docker-compose-prod.yml`, `subscription-page/docker-compose-prod.yml` and `.env.sample`, `backend/libs/contract/**`
- Podman v6.0.0 release notes; Podman Quadlet man page (v6.0.2)
- Rocky Linux 10 mirror package listings; EPEL 10 (fail2ban 1.1.0)
- containers.podman CHANGELOG and `podman_container` module docs
- Galaxy API: containers.podman 1.21.2, ansible.posix 2.2.2, community.general 14.0.1, community.postgresql 5.1.2
- Ansible release and maintenance table
- Node compose facts (host network, port 2222, SECRET_KEY origin, firewall advice): https://docs.rw/docs/install/remnawave-node (fetched)
- Docker Hub tag listings; Vagrant Cloud box API (almalinux/10 libvirt 10.2.20260914)

### Secondary (MEDIUM confidence)
- Xray Reality docs and community self-steal guides (unix-socket and `xver` patterns)
- Competitor projects: vff-remnawave-auto, iphizic/remna-playbook, eGamesAPI/remnawave-reverse-proxy, DigneZzZ/remnawave-scripts
- Remnawave official docs (Panel install, Node install, tinyauth for nginx)
- Ansible module docs (`ansible.posix.firewalld`, `ansible.builtin.systemd`)
- Traefik documented behaviour (entrypoints, `proxyProtocol`, ACME HTTP-01, TLS store default certificate)

### Tertiary (LOW confidence, needs validation)
- Remnawave REST endpoint names and payloads beyond what `libs/contract` confirms (verify against the pinned OpenAPI)
- Traefik unix-socket entrypoint absence (no evidence found; treated as unsupported; verify in Phase 2 spike)
- SELinux booleans `container_connect_any` and `container_t` port binding (not verified)
- Traefik cookie/secret-path gate via core middlewares (unproven)
- Xray `geoip:private` coverage and routing semantics (verify at the node image's Xray version)
- Podman 5.x vs 6.x Quadlet key differences across EL10.0 to 10.3 (not fully verified)

---
*Research completed: 2026-11-23*
*Ready for roadmap: yes*
