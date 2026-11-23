# Walking Skeleton — xvpn.remnawave

**Phase:** 1
**Generated:** 2026-11-23

## Capability Proven End-to-End

An operator runs `ansible-playbook -i inventory xvpn.remnawave.foundation` against a clean Rocky/AlmaLinux 10 host; a read-only preflight play gates the host, then the rootless user `rw-edge` (linger, subuid/subgid, home under `/var/lib/xvpn`) gets a generator-validated Quadlet unit through `fedora.linux_system_roles.podman`, and that unit serves HTTP on host port 80 as non-root, surviving a reboot under SELinux enforcing with zero AVCs — proven by Molecule (container tier on every push, VM tier on PR/nightly) and linted in CI.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Distribution unit | Ansible collection `xvpn.remnawave` (galaxy.yml, `requires_ansible >=2.20.0`) | Public Galaxy-ready artifact (FND-06); FQCN roles and playbooks |
| Operator entry point | Collection playbook `playbooks/foundation.yml` (`xvpn.remnawave.foundation`): play 1 preflight (`any_errors_fatal`), play 2 common + podman_rootless | Separate read-only first play guarantees "nothing changed" on any failure (D-06) |
| Role boundaries | `preflight` (read-only), `common` (packages, SELinux gate, add-only firewalld), `podman_rootless` (users, home, SELinux equivalence, sysctl, linger, user manager, Quadlet deploy); no `meta` dependencies | D-09; later roles call `include_role ... tasks_from` |
| Container runtime | Rootless Podman + Quadlet user units, one service user per trust domain: `rw-edge`, `rw-panel`, `rw-node` | D-07; project constraint (no Docker, no rootful) |
| Quadlet deployment interface | `include_role: xvpn.remnawave.podman_rootless`, `tasks_from: quadlet`, vars `xvpn_podman_rootless_quadlet_user`, `xvpn_podman_rootless_quadlet_specs` (`template_src` absolute paths), `xvpn_podman_rootless_quadlet_activate`; generator `--dryrun` validation, then LSR `podman` with `podman_pull_image: false` | D-10 resolved in RESEARCH in favour of LSR (prefer maintained Galaxy roles); one interface for Phases 2-4 |
| Service user home | `/var/lib/xvpn/<user>` with SELinux equivalence `/var/lib/xvpn` = `/home` | D-08; proven by the zero-AVC VM tier, escalation to the user if it fails |
| Privileged ports | Host sysctl `net.ipv4.ip_unprivileged_port_start=80` in `/etc/sysctl.d/99-xvpn-unprivileged-ports.conf` | FND-03; documented host-wide trade-off |
| Firewall | `ansible.posix.firewalld`, add-only in the zone of the public interface, SSH guard | D-13, D-14 |
| Variables | `xvpn_<role>_*`, shared `xvpn_public_interface` / `xvpn_public_ip`; `meta/argument_specs.yml` in every role; lint skip `var-naming[no-role-prefix]` | ARCHITECTURE.md, D-04 |
| Quality gate | `scripts/check.sh` (ansible-lint production, yamllint, argument_specs presence, syntax-check, build) locally and in CI | QA-01 |
| Test tiers | Molecule collection mode `extensions/molecule/`: `container` + `preflight` (podman driver, every push), `vm` (vagrant+libvirt, AlmaLinux 10 + Rocky 10, SELinux enforcing, reboot, zero AVC; PR/nightly/on demand; delegated GenericCloud fallback) | D-15..D-18 |
| CI | GitHub Actions: `lint.yml`, `molecule-container.yml`, `molecule-vm.yml`; actions pinned by SHA, `contents: read` | D-17 |

## Stack Touched in Phase 1

- [x] Project scaffold (galaxy.yml, runtime, changelog, lint configs, `scripts/check.sh`) — Plan 01
- [x] Routing equivalent — operator playbook `xvpn.remnawave.foundation` with preflight + foundation plays — Plans 01-03
- [x] State write — service user, SELinux file-context equivalence, sysctl, linger, Quadlet unit on the target host — Plan 01
- [x] State read — read-only preflight (OS, SELinux, Podman, ports, DNS) — Plans 01-02
- [x] User-visible behaviour — fixture HTTP service on host :80 as a rootless user, surviving reboot — Plans 01 + 05
- [x] Deployment — CI runs on GitHub Actions; local one-command `molecule test -s vm` — Plans 04-05

## Out of Scope (Deferred to Later Slices)

- Traefik, ACME/Pebble, Panel stack, secrets handling — Phase 2
- Remnawave node, Reality self-steal, Panel API modules — Phase 3
- `xvpn_lan_interface`, LAN firewalld zone — Phase 4
- SSH hardening (sshd drop-in, fail2ban), dnf-automatic, backups, CI ansible-core matrix 2.21/2.22, full docs — Phase 5
- `user@.service` drop-ins (not needed: Quadlet orders user units after `podman-user-wait-network-online.service`)
- Podman 5.x VM legs (floor covered by the preflight version check only)

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- Phase 2: Traefik (`rw-edge`) replaces the fixture on :80/:443 with Let's Encrypt (Pebble in CI); Panel stack under `rw-panel` behind a cookie/secret-path gate; subscription page — all deployed via the `quadlet` entry point
- Phase 3: Node under `rw-node` with Reality self-steal to Traefik on loopback, registered in Panel via collection modules
- Phase 4: LAN inbound + internal squad, negative leak tests in the VM tier
- Phase 5: operations, hardening, CI matrix, documentation
