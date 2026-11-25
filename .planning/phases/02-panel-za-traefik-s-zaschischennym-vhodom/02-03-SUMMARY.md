---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 03
subsystem: testing
tags: [molecule, vm-tier, pebble, traefik, selinux, acme, edge-01, edge-02, edge-03, qa-05]
status: complete

requires:
  - phase: 02-panel-za-traefik-s-zaschischennym-vhodom
    provides: playbooks/panel.yml and the edge role (plans 02-01, 02-02)
provides:
  - VM tier runs playbooks/panel.yml instead of the Phase 1 fixture
  - Pebble and challtestsrv (sha256-pinned) in VM prepare with an AVC canary
  - shared/verify_edge.yml (HTTPS via Pebble chain, strict SNI, :80, real client IP, log hygiene, acme.json)
  - vm/vars/panel.yml with the Panel domains and the Pebble CA pin
affects: [02-04, 02-05, 02-07, 02-10, phase-03-node]

actuals:
  tokens: 14000
  tasks: 2
  commits: 5
plan_head_before: 973556d
plan_head_after: 191500d56b5d4d5abb9c9a76c90a24a0e36b64ef

key-files:
  created:
    - extensions/molecule/vm/vars/panel.yml
    - extensions/molecule/vm/tasks/pebble.yml
    - extensions/molecule/shared/verify_edge.yml
  modified:
    - extensions/molecule/vm/prepare.yml
    - extensions/molecule/vm/converge.yml
    - extensions/molecule/vm/side_effect.yml
    - extensions/molecule/vm/verify.yml
    - extensions/molecule/vm/molecule.yml
    - extensions/molecule/shared/verify_runtime.yml
    - extensions/molecule/shared/verify_common.yml
    - extensions/molecule/shared/verify_rootless.yml

key-decisions:
  - "The Pebble issuing root is stored on the VM by the first verify_edge run (before the reboot) because Pebble builds a new in-memory CA on every start"
  - "The controller address is read as SSH_CLIENT in the SSH session without become (sudo resets the environment; gathered facts carry no SSH_CLIENT)"

requirements-completed: [EDGE-01, EDGE-02, EDGE-03, QA-05]

coverage:
  - id: D1
    description: "After the VM converge of panel.yml, https://panel.xvpn.test/ serves the decoy through a Pebble-issued certificate (HTTP-01 on :80); idempotence changed=0, reboot, zero AVC"
    requirement: EDGE-02
    verification:
      - kind: integration
        ref: "molecule-vm run 45587287337 (alma10, rocky10) success for 191500d"
        status: pass
    human_judgment: false
  - id: D2
    description: "Strict SNI (no certificate for unknown or absent SNI), :80 redirect/404, /a%2Fb gives 400, acme.json 0600 owned by rw-edge, 80/443 listeners owned by the rw-edge uid"
    requirement: EDGE-01
    verification:
      - kind: integration
        ref: "extensions/molecule/shared/verify_edge.yml in molecule-vm run 45587287337"
        status: pass
    human_judgment: false
  - id: D3
    description: "Traefik logs the controller address as ClientHost despite a forged X-Forwarded-For; cookie and path absent from the log"
    requirement: EDGE-03
    verification:
      - kind: integration
        ref: "verify_edge.yml probe-line assertions in molecule-vm run 45587287337"
        status: pass
    human_judgment: false
  - id: D4
    description: "No scenario talks to production Let's Encrypt: the VM tier pins the ACME CA to Pebble on 127.0.0.1:14000"
    requirement: QA-05
    verification:
      - kind: other
        ref: "bash scripts/check.sh (check_acme_ca: OK) and vm/vars/panel.yml"
        status: pass
    human_judgment: false

duration: 150min
completed: 2026-11-25
---

# Phase 2 Plan 03: VM tier on the real Panel playbook Summary

**The enforcing-SELinux VM tier now converges `playbooks/panel.yml` with Pebble as the ACME CA and proves HTTPS on the Panel domain, strict SNI, :80 behaviour, the real client IP in the Traefik log, `acme.json` 0600, idempotence, reboot and zero AVC, in CI on alma10 and rocky10.**

## Accomplishments

- Tracer: the VM converge of `playbooks/panel.yml` issues a certificate through Pebble over HTTP-01 and `https://panel.xvpn.test/` serves the decoy page (body sha1 equals `roles/edge/files/decoy/index.html`). Traefik ran as `rw-edge` under `Network=host` on enforcing SELinux with no AVC and no boolean, port label or policy module. The Option-B (pasta) checkpoint was not needed.
- `vm/tasks/pebble.yml`: Pebble v2.10.3 and challtestsrv from sha256-pinned tarballs and certs, systemd units, `/etc/hosts` entries for the test domains, and an `ausearch` AVC canary for both Pebble processes before converge.
- `verify_edge.yml` matrix: `openssl s_client` with unknown and absent SNI aborts the handshake (no certificate, no TRAEFIK DEFAULT CERT), :80 known Host redirects, unknown Host 404, `/a%2Fb` 400, probe line selected by its unique User-Agent with `ClientHost` equal to the controller address although `X-Forwarded-For: 6.6.6.6` is forged, cookie and path strings absent from the log and no `RequestPath`/`request_Cookie` keys, `acme.json` mode 0600 owner `rw-edge` with the domain, :80/:443 listeners owned by the `rw-edge` uid.
- `side_effect.yml` and `verify.yml` track `traefik.service` (InvocationID unchanged by the idempotence re-run, restart, reboot, post-reboot verify); `verify_common.yml` guards the decoy port 18080; the firewall holds exactly 80/tcp and 443/tcp.

## Task Commits

1. Task 1 (tracer): `9bd03bd` feat, `c961cf8` fix (Pebble root kept across the reboot)
2. Task 2 (edge matrix): `896b3f2` feat, `3595bad` fix, `191500d` fix (SSH_CLIENT read)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pebble root changes across the reboot**
- **Found during:** Task 1 (first molecule-vm run; verify runs after the side_effect reboot)
- **Issue:** Pebble generates a new in-memory CA on every start, so `roots/0` after the reboot did not issue the certificate in `acme.json` (curl error 60).
- **Fix:** the first `verify_edge.yml` run (before the reboot) stores the root at `/var/lib/xvpn-molecule/pebble-root.pem` on the VM; later runs reuse it.
- **Files modified:** extensions/molecule/shared/verify_edge.yml
- **Commit:** c961cf8

**2. [Rule 1 - Bug] SSH_CLIENT not available through `ansible_env` or gathered facts**
- **Found during:** Task 2 (two molecule-vm runs)
- **Issue:** `ansible_env` injection is off, and `ansible_facts['env']` has no `SSH_CLIENT` because fact gathering runs under sudo, which resets the environment.
- **Fix:** read `${SSH_CLIENT:-$SSH_CONNECTION}` with a `become: false` command task in the SSH session itself.
- **Files modified:** extensions/molecule/shared/verify_edge.yml
- **Commits:** 3595bad (first attempt), 191500d

**Total deviations:** 2 auto-fixed (2 bugs in the test harness). **Impact:** none on role code; both fixes are verify-side.

## Assumptions and limits

- Renewal is delegated to Traefik's built-in ACME renewal and is not exercised in CI (Pebble certificates are fresh); expiry monitoring is OPS-05 (Phase 5).
- The real-IP proof covers IPv4 from the Molecule controller only. IPv6 clients and proxies/CDN in front of the host are out of scope (operator responsibility); the Traefik code path is address-family independent.
- A4 (k8s-file log readable through `podman logs` as `rw-edge`) held: no bind-mounted log file fallback was needed.
- A1/A2/A6/A7 held: Traefik bound 80/443 and reached 127.0.0.1:18080 as `container_t`, the file provider picked up the route files, and Pebble under systemd produced no AVC.

## Known Stubs

None.

## Threat Flags

None. Pebble is test-only, downloaded with sha256 pins (T-02-07), and never shipped in a role.

## Self-Check: PASSED

- Created files exist: vm/vars/panel.yml, vm/tasks/pebble.yml, shared/verify_edge.yml
- Commits 9bd03bd, c961cf8, 896b3f2, 3595bad, 191500d are ancestors of HEAD
- CI for 191500d: lint, molecule-container and the dispatched molecule-vm (alma10, rocky10) are success
