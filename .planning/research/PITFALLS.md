# Domain Pitfalls

**Domain:** Ansible collection deploying Remnawave Panel/Node (Xray VLESS Reality self-steal, LAN egress group) on Rocky/Alma 10, rootless Podman + Quadlet, SELinux enforcing, firewalld, Traefik
**Researched:** 2026-11-23
**Method note:** Written from training knowledge of Podman/Quadlet/SELinux/Traefik/Xray/Remnawave, without live doc fetches in this run. Each pitfall carries a confidence tag. Items tagged MEDIUM or LOW are explicitly "verify in a spike before you build on it". Nothing here should be treated as verified against the current Remnawave release.

**Phase names used for mapping** (suggested; the roadmap may rename them):
- **P0 Foundation/Spike**: rootless runtime plumbing (user, linger, subuid, sysctl, Quadlet helper, become_user), test harness, a throwaway end-to-end spike
- **P1 Panel**: Panel stack and Traefik on the Panel host
- **P2 Node + self-steal**: remnanode, Traefik decoy, Reality
- **P3 API registration**: bootstrap admin, tokens, config profile, nodes, hosts
- **P4 LAN access**: LAN inbound, routing, DNS
- **P5 Backups/Upgrades**
- **P6 Hardening**: SSH, fail2ban, firewalld, auto-updates
- **P7 CI/Docs/Release**

---

## Critical Pitfalls

Mistakes that cause rewrites, silent security failure, or a non-working install.

### Pitfall 1: Client source IP is lost, so Traefik IP allowlists silently fail (rootless networking mode)
**What goes wrong:** In rootless Podman, a container on a user-defined bridge (netavark) network gets published ports through `rootlessport`, which commonly shows the connection as coming from the bridge gateway (e.g. `10.89.0.1`) instead of the real client. Traefik `ipAllowList`, access logs, and fail2ban all then see the wrong address. With slirp4netns the same thing happens. Only `Network=host` and `Network=pasta` (not bridge+pasta) reliably preserve the source address.
**Why it happens:** Rootless has no real host netns to DNAT in; a userspace proxy re-originates the connection.
**Consequences:** Either the Panel admin allowlist blocks everyone (operator "fixes" it by allowing the gateway, which now allows the whole internet), or it is wide open. Security control that passes a smoke test from the LAN and fails in production.
**Prevention:**
- Decide the Panel-host topology in P0: either Traefik with `Network=host` and backend published on `127.0.0.1:3000`, or a single Quadlet `.pod` using `Network=pasta` containing Traefik + backend + Postgres + Valkey (shared localhost, source IP preserved, coupled restarts). Do NOT default to "Traefik on a bridge network with published 80/443".
- Add a Molecule/verify task that connects from a second source address and asserts the Traefik access log records that address (not a gateway).
- MEDIUM confidence on exact behaviour in the Podman 5.x shipped by EL10; test empirically.
**Detection:** Traefik access log shows the same `10.x.0.1` for every request; allowlist 403 from a permitted IP.
**Phase:** P0 (decision + spike), P1 (implement + test).

### Pitfall 2: Reality `dest` target (Traefik) gives the game away: default cert, default 404, exposed port
**What goes wrong:** Xray Reality forwards any unauthenticated connection to `dest`, including probes with a wrong or absent SNI. Traefik answers with its self-signed `TRAEFIK DEFAULT CERT` and the plain-text `404 page not found`. Both are instant fingerprints that distinguish "Reality node" from "normal HTTPS site". Also: the real site on the internal entrypoint may be bound to `0.0.0.0:8443` (reachable directly), the self-steal cert may not exist yet when Xray starts, and the masking site may be identical across every install of this public collection.
**Why it happens:** Traefik defaults are tuned for routing, not for looking like a single boring website.
**Consequences:** Self-steal gives no stealth, defeating the project's core value.
**Prevention:**
- Set the Traefik TLS store `default` certificate to the node-domain LE cert, so unknown SNI still gets a valid cert for the real domain.
- Add a catch-all router (lowest priority, `HostRegexp(`.+`)`/`PathPrefix(`/`)`) serving the decoy site for any Host, so no Traefik 404 ever appears. Remove `Server`/version-leaking headers and the dashboard/API (`api.insecure=false`, no ping on the public entrypoint).
- Internal entrypoint binds `127.0.0.1:8443` only. Use the literal `127.0.0.1` in Reality `dest` (not `localhost`, which can resolve to `::1`).
- Order tasks: Traefik up on :80, cert obtained and verified, THEN enable the Reality inbound pointing at it. Gate with an `openssl s_client` check.
- Post-deploy verify (automated): `openssl s_client -connect NODE:443 -servername DOMAIN`, again with a random SNI, and again with no SNI. All three must present the same valid LE certificate chain and the same HTTP response.
- Do not ship one fixed decoy site as the only option; ship a minimal neutral template plus a variable to point at the user's own static directory, and document that identical default content is itself a fingerprint at scale.
**Detection:** `curl -k https://IP/` shows Traefik 404 or default cert CN.
**Phase:** P2.

### Pitfall 3: PROXY protocol (`xver`) mismatch between Xray and Traefik
**What goes wrong:** With `xver: 1`, Xray prepends a PROXY header to the connection to `dest`. If Traefik's internal entrypoint has no `proxyProtocol` config, or `trustedIPs` doesn't include the address Traefik actually sees as the source (it may be a gateway/pasta address, not `127.0.0.1`), TLS handshakes fail on garbage bytes. Probes then get a broken site; legitimate clients are unaffected, so it looks fine in testing.
**Prevention:** Default to `xver: 0`. The decoy does not need real client IPs. If real IPs are wanted, give Traefik `Network=host`, entrypoint `127.0.0.1:8443` with `proxyProtocol.trustedIPs=[127.0.0.1/32]`, and test with a probe client. Never enable `xver` without a verify step that fetches the decoy through port 443 with the real SNI.
**Detection:** `openssl s_client` through :443 with the correct SNI hangs or reports handshake failure; Traefik logs "proxy protocol not trusted" style errors.
**Phase:** P2.

### Pitfall 4: Rootless `Network=host` + ports below 1024 + `ip_unprivileged_port_start`
**What goes wrong:** An unprivileged process cannot bind 80/443 unless `net.ipv4.ip_unprivileged_port_start <= 80`. Setting it fixes the bind, but the sysctl is host-global: every local unprivileged process can then bind 80..1023 (port-hijack risk if a service is down). Also it must be persisted (`/etc/sysctl.d/`) AND applied live, before the first container start; otherwise first run fails and a later run "heals" it (non-idempotent first run). Rootless `--cap-add=NET_ADMIN` applies inside the user namespace only and does not grant host-netns capabilities even in `Network=host`.
**Prevention:** Set the sysctl to 80 (smallest that covers 80 and 443), via `ansible.posix.sysctl` with `reload: true`, ordered before any container task. Document the tradeoff in README (single-purpose VPN host, no other local users). Do not set it to 0. Assert effective value with `sysctl -n` in verify. Confirm remnanode actually works without real NET_ADMIN (it is requested in the official compose; check what the feature is for, e.g. optional features) before relying on it.
**Detection:** "bind: permission denied" in Traefik/Xray logs on first run.
**Phase:** P0.

### Pitfall 5: `systemctl --user` from Ansible fails ("Failed to connect to bus") or is non-idempotent
**What goes wrong:** Several independent failure modes:
1. No `XDG_RUNTIME_DIR` / `DBUS_SESSION_BUS_ADDRESS` in the `become_user` environment, so `systemctl --user` fails with "No medium found" / "Failed to connect to bus".
2. No lingering, so `/run/user/UID` and the user manager do not exist (and everything stops when the SSH session ends / at boot).
3. Right after `loginctl enable-linger`, `/run/user/UID/bus` is not there yet (race); the next task fails.
4. `become_user` from root to an unprivileged user without `acl` installed (or without pipelining) fails with "Failed to set permissions on the temporary files".
5. `ansible.builtin.systemd` with `enabled: true` on a Quadlet-generated unit errors ("generated/transient") or reports `changed` every run.
**Prevention:**
- A single shared helper (include_tasks or module wrapper) used by both roles: `loginctl enable-linger USER` (guard with `creates: /var/lib/systemd/linger/USER`), then `wait_for path=/run/user/UID/bus`, and every user-scope task gets `environment: {XDG_RUNTIME_DIR: "/run/user/{{ uid }}", DBUS_SESSION_BUS_ADDRESS: "unix:path=/run/user/{{ uid }}/bus"}`.
- Install `acl`; enable pipelining in the documented ansible.cfg; never use `allow_world_readable_tmpfiles`.
- Write files as root with `owner:`/`group:` where possible; use `become_user` only for `systemctl --user` and `podman` invocations.
- Put `[Install] WantedBy=default.target` in each Quadlet file, and use `state: started` only (never `enabled:`) for generated units.
- Use a regular (uid >= 1000, `/home/NAME`) user, not `--system`: system users get no subuid/subgid range and no default SELinux home labelling. Verify `/etc/subuid` and `/etc/subgid` entries exist; if added after Podman first ran, run `podman system migrate` as that user.
**Detection:** First run passes on a dev box with an open SSH session, fails in CI/after reboot. Second run shows `changed` on the enable task.
**Phase:** P0 (build once, reuse everywhere). HIGH confidence on all items.

### Pitfall 6: Quadlet generator fails silently; service "not found"
**What goes wrong:** A syntax error, unknown key, or a key from a newer Podman than EL10 ships makes the generator skip the file; `systemctl --user start foo.service` then says "Unit not found" with no obvious reason. Other quirks: generated unit names (`foo.container` -> `foo.service`, `foo.network` -> `foo-network.service`, `foo.volume` -> `foo-volume.service`, `foo.pod` -> `foo-pod.service`) must be used in `Requires=`/`After=`; Quadlet files are only re-read on `daemon-reload`; changes to an `EnvironmentFile` need a restart (not reload); short image names fail because EL runs `short-name-mode=enforcing` (use fully-qualified `docker.io/remnawave/...` or `ghcr.io/...`); the first image pull can exceed the default start timeout (set `TimeoutStartSec=900` or pre-pull); `PublishPort` is meaningless with `Network=host`; `Restart=always` hides a crash-looping config error (Remnawave validates env at boot and exits).
**Prevention:** Run `/usr/libexec/podman/quadlet -dryrun -user` (as the target user, with the XDG env) as a post-template verification step and fail the play on non-empty errors. Use handlers: template -> daemon-reload -> restart. Assert a minimum Podman version in a preflight (EL10 ships Podman 5.x; features like `.pod`, `Notify=healthy` depend on minor version). Use `containers.podman.podman_image` as the user for pre-pull. Require health-gated ordering with `HealthCmd` + `Notify=healthy` on Postgres.
**Detection:** `systemctl --user list-unit-files | grep NAME` empty; `journalctl --user` shows generator warnings.
**Phase:** P0 (helper + dryrun check), reused in P1/P2.

### Pitfall 7: User units cannot order against system `network-online.target`; boot-time start races
**What goes wrong:** User-manager units cannot depend on system targets. After a reboot, with linger, containers (especially Traefik requesting ACME, or Xray/pasta needing the interface/IP) may start before the network is up and flap or fail permanently if `Restart=` is absent.
**Prevention:** Set `Restart=always` + `RestartSec=` on every Quadlet; add a system drop-in `user@UID.service.d/` with `After=network-online.target` (and `Wants=`). Include a reboot test in the VM-based Molecule scenario (see Pitfall 20). MEDIUM confidence on the cleanest drop-in; verify.
**Detection:** Works after deploy, broken after the first reboot.
**Phase:** P0/P2, verified in P7.

### Pitfall 8: Remnawave panel rejects traffic that does not look like HTTPS-behind-proxy
**What goes wrong:** The backend refuses (drops/empty reply or error) requests lacking proxy headers (`X-Forwarded-Proto: https`, `X-Forwarded-For`), i.e. direct `http://localhost:3000` calls. This breaks: container healthchecks (`curl localhost:3000`), Ansible API calls made directly against the loopback port, the subscription page calling the panel through the internal URL, and operators testing without TLS. Traefik adds the headers by default, so everything looks fine through Traefik only.
**Prevention:** Healthcheck and API-bootstrap requests must send `-H 'X-Forwarded-Proto: https' -H 'X-Forwarded-For: 127.0.0.1'` (confirm exact requirement against the installed version; MEDIUM). Run Ansible API calls on the Panel host against `127.0.0.1:3000` with those headers (bypasses the admin gating layer, no TLS/cookie issues) via `delegate_to`. Never expose 3000 or the metrics port 3001 beyond loopback/internal network.
**Detection:** Health probe flaps while the UI works through the domain.
**Phase:** P1/P3.

### Pitfall 9: Open first-admin registration on a fresh Panel
**What goes wrong:** On first start Remnawave has no admin and exposes a registration endpoint that the first caller wins. If the route is public (or the allowlist/secret gating is wired after the proxy goes live), anyone can claim the Panel between "container up" and "Ansible creates admin".
**Prevention:** Order: start Panel on loopback only -> create admin over loopback via API -> only then enable the public Traefik router. Never publish the router before the admin exists; make the "admin exists" check part of the role's gating condition. Generate the admin password on the target host/vault, `no_log`.
**Detection:** Unknown admin account in the UI.
**Phase:** P1/P3.

### Pitfall 10: Secrets regenerated on every run, or env changed after the volume exists
**What goes wrong:** `lookup('community.general.random_string')`/`password` evaluated each run rotates `JWT_AUTH_SECRET`, `JWT_API_TOKENS_SECRET`, the metrics password and the DB password. Rotating JWT secrets invalidates all sessions and API tokens (breaking the subscription page and any stored token). Changing `POSTGRES_PASSWORD` after the volume is initialised does NOT change the DB password, so the backend cannot connect. Passwords with special characters break `DATABASE_URL`. `.env.sample`-style defaults (e.g. `METRICS_USER/PASS=admin`) get shipped by accident.
**Prevention:** "Generate once, persist on the target" pattern: stat the secret file (root-owned, 0600) -> create only if missing -> read back. Use alphanumeric generators only. Make DB credentials immutable after first init (or provide an explicit, documented rotation procedure with `ALTER USER`). Support operator-provided secrets via Vault vars as override. Assert no default/`change_me` values reach the container. Back up secrets with the DB (Pitfall 17).
**Detection:** Subscription page 401 after a re-run; backend "password authentication failed".
**Phase:** P1.

### Pitfall 11: Non-idempotent API registration: duplicate nodes, rotated keys, restart storms
**What goes wrong:**
- `POST /api/nodes` on every run creates duplicates or 409s; matching by UUID the operator does not have.
- Always-`changed` `uri` tasks defeat the `changed=0` requirement.
- Config-profile `PUT` with semantically equal JSON (key order differs) triggers a Xray restart on every node using it: brief connection drops each run.
- Regenerating the Reality x25519 keypair or shortIds on each run, or after recreating the profile, drops all clients; recreating a profile/inbound changes UUIDs that Hosts/squads reference.
- The API token is shown only once; recreating "to be safe" accumulates tokens.
- Remnawave's API changed shape across majors (v1 inbounds-on-node -> v2 config profiles + internal squads + hosts). A collection that pins neither panel nor API version breaks on the next release.
**Prevention:** Idempotency contract: GET list -> match by stable natural key (node name) -> diff normalised JSON (sorted keys) -> write only on difference, `changed_when` derived from the diff. Generate Reality keys only when the profile does not already contain them, and read them back from the Panel (source of truth is the Panel DB, not inventory). Persist the API token on the Panel host (0600), reuse it. Ship a small custom module/plugin (or a well-tested filter set) rather than ad-hoc `uri` chains. Pin Panel and Node as a tested pair (exact tags, no floating `2`/`latest`); preflight asserts Panel version against a supported range from the collection's compatibility table. Keep an `api_version`-keyed adapter layer so one breaking release is a one-file change. MEDIUM confidence on the exact current endpoint shapes; confirm against the OpenAPI at the target version.
**Detection:** Second run `changed>0`; node list doubled; clients disconnect on each deploy.
**Phase:** P3, with idempotence test in P7.

### Pitfall 12: Node/secret registration ordering and cross-host dependencies
**What goes wrong:** The Panel connects TO the node (port `NODE_PORT`, default 2222, mTLS + JWT); the node does not call the Panel. The node's `SECRET_KEY` comes from the Panel. In the versions known to the researcher the key looks panel-wide (from the keygen endpoint) rather than per-node, so "rotate secret" or re-keying the panel breaks every node at once (MEDIUM; verify). Playbook ordering: Panel play must complete (and be reachable via `hostvars`/`delegate_to`) before the node role runs; `--limit node1` runs fail because panel facts are absent. Port 2222 open to the world exposes the node control plane. Clock skew breaks JWT validation.
**Prevention:** Node role fetches what it needs via `delegate_to: panel_host` with a clear failure message if the panel group is not in the play. Document `ansible-playbook` invocation with both groups, or provide an explicit variable fallback for the secret. firewalld rich rule: allow `NODE_PORT` only from the Panel IP. Enforce chrony/time sync. Never log the secret (`no_log`).
**Detection:** Node shows offline in Panel; "invalid token"/TLS errors on node logs.
**Phase:** P3 (with P2 for firewall).

### Pitfall 13: LAN access leaks (the "other users reach private IPs" problem)
**What goes wrong:** Xray's `freedom` outbound will connect to anything the host can reach: 10.0.0.0/8, 192.168.0.0/16, `127.0.0.1` (node's own SSH, Traefik, any local service, since the container uses host networking), link-local/metadata `169.254.0.0/16`. Specific traps:
- Xray routing by `ip`/`geoip:private` only matches when the target is an IP. A domain that resolves to a private IP (`internal.corp`, `localtest.me`, DNS rebinding) bypasses it unless domain resolution is applied (`domainStrategy: IPIfNonMatch`/`IPOnDemand` in routing, `UseIP` on freedom). Newer Xray releases may have post-resolution blocking on the outbound; check the version shipped in the node image (LOW).
- LAN inbound and regular inbound share one routing table; ordering matters: LAN-allow by `inboundTag` + declared CIDRs first, then block all private/loopback/link-local for everyone, then default direct.
- Several Reality inbounds cannot share port 443; the LAN group therefore needs a separate inbound on another port (or per-user routing, which does not scale). Firewall and Hosts must be consistent.
- DNS: the host's resolver (LAN DNS) is used for everyone, so regular users can resolve and enumerate internal names; LAN users may need the internal resolver for internal zones (Xray `dns` section with domain-scoped servers) while regular users use public DNS only. DNS queries also leak through the client if the client does local resolution.
- Defence in depth: nftables/firewalld rules on the node cannot distinguish LAN users from others (same process), so do not rely on host firewall for per-group isolation.
**Prevention:** Generate the routing block from variables (`lan_subnets`, `lan_inbound_tag`) in a single template; always include loopback/link-local/metadata block rules; always set a domain strategy that resolves; write a verify that, from a non-LAN test user, attempts `10.x`, a name resolving to `127.0.0.1`, and the host's own SSH, and expects failure; and from a LAN user expects only declared subnets. Treat as a security feature with tests, not config.
**Detection:** Non-LAN test user can hit `127.0.0.1:22` or an internal host.
**Phase:** P4 (design questions raise in P2 so inbound/port layout is right).

---

## Moderate Pitfalls

### Pitfall 14: SELinux labels on volumes and files
**What goes wrong:** Bind mounts without `:Z`/`:z` fail with permission denied under enforcing. Specifics:
- `:Z` (private, relabels) for dirs used by one container; `:z` (shared) only when several containers share a dir. Never `:Z` a broad directory (home, `/etc`): it relabels the world.
- Single-file bind mounts (config files rendered by Ansible `template`): Ansible replaces the inode and the new file inherits the directory default type, not `container_file_t`, until the next container start relabels. Mount directories, not files, or restart on change (handler already does).
- Service user with a non-standard home (`/srv/x`, `/opt/x`) gets wrong default contexts (`var_t`) and breaks the user manager/Podman; use `/home/NAME`, or add `semanage fcontext -a -e /home /opt/x`.
- Prefer named Podman volumes (Postgres data) to dodge label and subuid ownership issues.
- `container_manage_cgroup` is for containers running systemd as init; none of the Remnawave images need it. Do NOT toggle it to "fix" denials; use `ausearch -m avc` / `audit2why` to find the real cause.
- Ansible SELinux modules (`seboolean`, `sefcontext`, `seport`) need `python3-libselinux` and `python3-policycoreutils` on the target for the interpreter Ansible uses, else "Aborting, target uses selinux but python bindings aren't installed".
- Binding 8443/other ports from `container_t`: verify with AVC logs rather than guessing; use `semanage port` only if an AVC proves it.
**Prevention:** Verify stage runs `getenforce == Enforcing` and `ausearch -m avc -ts boot` (expect zero lines); fail CI on any AVC. Never ship `permissive` as a troubleshooting variable default.
**Phase:** P0 (helper conventions), P1/P2 (apply), P7 (AVC-zero test).

### Pitfall 15: firewalld interplay with rootless
**What goes wrong:** Rootless published/host ports bypass nothing: traffic arrives through the normal host INPUT path, so firewalld must explicitly allow 80/443/NODE_PORT/panel ports (opposite of rootful Docker, where DNAT bypasses zones; do not "learn" from rootful guides). Others: `ansible.posix.firewalld` needs `python3-firewall`; `permanent: true` without `immediate: true` leaves runtime rules missing until reload; reloads can drop rules added at runtime; zone changes over SSH can lock you out; rich-rule source restrictions (NODE_PORT from Panel IP only) must be verified from both a permitted and a non-permitted source; LE HTTP-01 needs port 80 open to the whole internet on the Panel host even if 443 is allowlisted.
**Prevention:** Idempotent `firewalld` tasks with `permanent` + `immediate`; ensure SSH service is in the zone before applying; test allow and deny paths.
**Phase:** P6 (with port-opening in P1/P2).

### Pitfall 16: Traefik specifics for this project
**What goes wrong:**
- Traefik has no native "secret path/cookie" gate for the Panel. Options: `ipAllowList` (needs the real source IP, Pitfall 1), `forwardAuth` to a tiny service, a plugin (downloaded at runtime: supply-chain/availability risk), or router rule tricks (`HeaderRegexp` on `Cookie` + a setter router adding `Set-Cookie`) (LOW/MEDIUM; spike). Hiding the Panel under a path prefix breaks the SPA's absolute asset paths. Non-matching requests must fall through to a decoy, not a Traefik 404.
- Allowlist/gating applied at the router will also block the subscription page's server-side calls if it uses the public Panel URL; use the internal URL with required forwarded headers, or an exempt route.
- Don't mount the Podman socket into Traefik (Docker provider): it hands container-escape-grade access to the proxy and needs SELinux label disablement. Use the file provider with templated dynamic config.
- ACME: `acme.json` must be `0600` and persisted across container recreation (volume), or every redeploy re-requests certificates and hits Let's Encrypt limits (5 duplicate certs/week, failed-validation limits). Use the LE staging CA in all tests. HTTP-01 requires port 80 reachable; do not apply a catch-all redirect that breaks the challenge route (Traefik handles it first, but verify). Before the cert exists Traefik serves its default cert: cover in Pitfall 2 ordering.
- Pin the Traefik major (v2 -> v3 changed rule syntax and defaults).
- On the node, Traefik is behind Xray: "TLS passthrough vs termination" is moot there; Traefik terminates on the internal entrypoint. On the Panel host Traefik terminates normally on 443.
**Phase:** P1 (Panel), P2 (node).

### Pitfall 17: Postgres backups from a rootless container
**What goes wrong:**
- Postgres UID 999 maps to a subuid on the host; host-level file copies of the volume are unreadable/inconsistent. Backup must go through `podman exec ... pg_dump`.
- `pg_dump | gzip` without `set -o pipefail` writes a valid-looking empty archive on failure; write to a temp name and `mv` on success; verify size and `pg_restore --list`.
- cron under a lingering rootless user is awkward; use a user systemd timer (needs linger and the XDG env) with `Persistent=true`; no `-t`/TTY allocation in `podman exec`.
- Rotation must not delete the only good backup if backups are failing (keep last N successful, alert on staleness).
- Backing up only the DB: the `.env` secrets are also needed for a faithful restore; include them (encrypted) or document them as vault-managed.
- Backups on the same disk are not backups; provide an off-host sync hook (rsync/restic/S3 variable) even if off by default.
- A restore that was never tested: ship a documented, tested restore playbook/Molecule step.
- Postgres 18+ official image changed the data mount layout (`/var/lib/postgresql` instead of `/var/lib/postgresql/data`) (MEDIUM): check the tag you pin before reusing old Quadlet volume lines.
**Phase:** P5.

### Pitfall 18: Image tag upgrades and DB migrations
**What goes wrong:** The backend runs schema migrations on start; there is no downgrade. A tag bump restarts the container and starts the migration with the old container's data in place; a failed or slow migration + `Restart=always` loops. Major Postgres bumps need dump/restore, not a tag bump. Floating tags (`:2`, `:latest`) upgrade you on an unrelated redeploy or on image re-pull. Panel/Node version skew can break the Xray config shape.
**Prevention:** Exact tags in role defaults, bumped deliberately with the compatibility table; a pre-upgrade `pg_dump` task that runs automatically when the Panel tag changes (compare running image vs desired); generous `TimeoutStartSec`; upgrade order documented (Panel first, then nodes) with API/version preflight; separate variable and guard for Postgres major upgrades (refuse to proceed). Do not use `podman-auto-update` (breaks the pin contract).
**Phase:** P5.

### Pitfall 19: Remnawave environment pitfalls
**What goes wrong:** Env is validated at boot (fail-fast crash loop if wrong). Known sharp edges: `SUB_PUBLIC_DOMAIN` is a bare domain without `https://`; `FRONT_END_DOMAIN` must match the Panel domain (CORS/cookies), mismatch gives a UI that loads but cannot log in; `IS_DOCS_ENABLED=true` publishes Swagger/Scalar (leaks the full API surface to the internet, default to false); `METRICS_USER/PASS` and port 3001 stay on loopback/internal; renamed/removed variables between versions; optional Telegram/webhook variables have format requirements. The subscription page needs a Panel API token (chicken-and-egg ordering: Panel -> admin -> token -> subscription page) and its own domain/cert.
**Prevention:** Template the env from a documented, version-keyed variable map; run a preflight comparing required keys per supported version; assert formats (no scheme in `SUB_PUBLIC_DOMAIN`); defaults safe (docs off, metrics loopback). Check the exact variable list at the pinned version (MEDIUM).
**Phase:** P1.

### Pitfall 20: Testing rootless Podman + systemd + SELinux in CI
**What goes wrong:** GitHub-hosted runners run Ubuntu (AppArmor). A Molecule "docker/podman driver" container on top of them shares the host kernel's LSM, so SELinux enforcing is not testable there at all; systemd-in-container needs privileged, cgroup tweaks; nested rootless Podman (uid maps, `/dev/fuse`, `/dev/net/tun` for pasta) is fragile; `loginctl enable-linger` and `user@.service` behave differently without a real login manager; reboot behaviour is untestable. A green container-based CI therefore proves little about the actual risks of this project.
**Prevention:** Three tiers:
1. Fast tier (every PR): yamllint, ansible-lint (production profile), `ansible-test sanity`, template rendering, Quadlet `-dryrun` validation. Containers acceptable here.
2. Real tier (PR/nightly): Molecule with VM-backed instances of Rocky 10 and Alma 10 cloud images (QEMU/KVM via a delegated/vagrant/libvirt scenario; KVM is generally available on current GitHub Linux runners, verify for your plan; self-hosted fallback). Asserts: `getenforce`, zero AVC, linger, reboot survival, idempotence (second run `changed=0`), firewalld allow/deny paths.
3. Integration tier (nightly): real Panel + Node images, a Pebble ACME server (or LE staging) for HTTP-01, an Xray client verifying Reality end to end, and the LAN isolation negative tests. Mirror/cache images (Docker Hub pull limits).
**Detection:** Tests pass in CI, fail on first real RHEL host.
**Phase:** P0 (harness decision, since everything else depends on it), P7 (complete).

---

## Minor Pitfalls

### Pitfall 21: `LimitNOFILE`/ulimit in rootless
**What goes wrong:** Official node compose sets very high `nofile` ulimits; rootless containers cannot exceed the user manager's hard limit, so the container fails to start ("operation not permitted") or silently has a low limit that throttles Xray under load.
**Prevention:** Raise `LimitNOFILE` for `user@UID.service` via a drop-in, set Quadlet `Ulimit=` within it. Tune kernel sysctls (somaxconn, BBR, conntrack) on the host, not in the container.
**Phase:** P2.

### Pitfall 22: Docker Hub and registry reliance
**What goes wrong:** Anonymous Docker Hub pull limits break reruns and CI; fully-qualified names required (short-name enforcing).
**Prevention:** Registry variable with `ghcr.io`/Docker Hub choices; optional registry login via `podman_secret`/auth file; mirror in CI.
**Phase:** P0/P7.

### Pitfall 23: SSH / fail2ban / auto-updates on EL10
**What goes wrong:** Editing sshd cipher lists manually conflicts with system crypto-policies (use `update-crypto-policies`); lockout from bad `sshd_config` (use `validate: sshd -t`, keep session open, test a second connection before disconnecting); fail2ban comes from EPEL 10 and needs `backend = systemd` (no rsyslog on minimal installs) and the firewalld action; fail2ban cannot see real client IPs for container logs under rootless bridging (Pitfall 1); `dnf-automatic` security-only mode needs a reboot for kernel updates (document, optional `needs-restarting`), and unattended `podman`/`pasta`/`netavark` upgrades can change behaviour under running containers.
**Phase:** P6.

### Pitfall 24: Ansible-core version and collection hygiene
**What goes wrong:** ansible-core 2.19 changed templating (conditionals must be real booleans, stricter undefined handling) and breaks older-style roles; EL10 targets use Python 3.12 (check supported matrix in `meta/runtime.yml`); ansible-lint production profile enforces FQCN, `changed_when` on commands, `no-handler` etc.; renaming the temporary `xvpn.remnawave` namespace later touches every FQCN, docs and test; empty `galaxy.yml` metadata surfaces when publishing.
**Prevention:** Test against two ansible-core versions in CI (matrix), set `requires_ansible`, centralise namespace in one test variable, decide the real name before the README/examples are written.
**Phase:** P0/P7.

### Pitfall 25: Reality dependencies on the domain side
**What goes wrong:** SNI mismatches between the Reality `serverNames`, the Host entry's SNI, the cert's SAN and the DNS name give "connected but no traffic" clients. A/AAAA records mismatch (AAAA points elsewhere or missing while the host listens on IPv6). `dest`/`target` field naming changed across Xray versions. Host `fingerprint`, `flow` (`xtls-rprx-vision`) and port must match the inbound.
**Prevention:** Single source of truth variable `node_domain` rendered into Traefik host rule, ACME domain, Reality `serverNames`, Host `sni`/`address`; preflight DNS check (A/AAAA resolves to node public IP) before ACME and before enabling Reality; assert `serverNames` equals the cert's SAN in verify.
**Phase:** P2/P3.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| P0 rootless plumbing | linger/XDG/DBUS (5), sysctl (4), Quadlet silent errors (6), boot ordering (7) | One tested helper; dryrun verification; VM reboot test |
| P0 network decision | Source IP loss (1) | Spike: host vs pasta pod; verify source IP preserved |
| P0 test harness | Containers cannot test SELinux/rootless (20) | VM-backed Molecule from day one |
| P1 Panel | Proxy headers (8), admin registration race (9), secrets (10), env (19), Traefik gate (16) | Loopback-first bootstrap, generate-once secrets, env map per version |
| P2 Node/self-steal | Default cert/404 (2), xver (3), ulimit (21), DNS (25) | Default cert = node cert, catch-all decoy, xver=0, s_client verify |
| P3 API registration | Idempotency/key rotation (11), ordering/secret (12) | Diff-before-write, persist keys in Panel, version adapter |
| P4 LAN | Private IP leak, domain bypass, DNS (13) | Generated routing block, domain strategy, negative tests |
| P5 Backups/Upgrades | Backup validity (17), migrations (18) | pg_dump via exec, pipefail+mv, auto pre-upgrade dump, pinned tags |
| P6 Hardening | firewalld (15), SSH lockout (23) | validate sshd, test allow/deny |
| P7 CI/Release | Test realism (20), ansible-core (24) | Tiered CI, version matrix |

## Research Flags (which phases need deeper research before planning)

- **P0:** needs a hands-on spike (source-IP preservation per networking mode; NET_ADMIN need for remnanode; user@ drop-ins).
- **P2:** needs a spike with a real Xray client (Reality to Traefik, default-cert behaviour, xver).
- **P3:** needs fresh read of the Remnawave OpenAPI at the pinned version (endpoint shapes, SECRET_KEY scope, admin bootstrap).
- **P4:** needs Xray routing/DNS verification at the node image's Xray version (post-resolution blocking features).
- **P1 gating:** Traefik cookie/secret gating approach is unproven (LOW); spike before committing the requirement.
- P5, P6, P7: standard patterns, lower research need.

## Sources

- Training knowledge of Podman/Quadlet (`podman-systemd.unit(5)`), systemd user manager/linger, SELinux container policy, Traefik (entrypoints, proxyProtocol, ACME HTTP-01, TLS store), Xray-core Reality docs, Remnawave docs/compose; Ansible module docs (`ansible.posix.firewalld`, `ansible.builtin.systemd`). Confidence MEDIUM overall; not re-verified against live documentation in this run.
- Items marked MEDIUM/LOW in text must be validated in the stated spike phase.
