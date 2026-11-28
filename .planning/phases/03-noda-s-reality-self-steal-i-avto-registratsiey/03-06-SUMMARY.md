---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 06
subsystem: molecule-vm-tier
status: complete
tags: [molecule, vagrant, libvirt, pebble, selinux, loopback-tls, ci]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: node role, edge route, playbooks/node.yml (plans 03-01..03-05)
provides:
  - extensions/molecule/node-vm two-VM scenario (panel + node, AlmaLinux 10, Pebble on each VM)
  - extensions/molecule/shared/verify_node.yml (loopback certificate and 8443 binding assertions)
  - .github/workflows/molecule-node-vm.yml (pull_request, dispatch, nightly; Memory budget step)
  - xvpn_prepare_hosts_names parameter of vm/tasks/pebble.yml
  - VM file /var/lib/xvpn-molecule/pebble-issuer-root.pem on every VM
affects: [03-07, 03-08, 03-09, 03-15]
actuals:
  tokens: 14000
  tasks: 2
  commits: 3
plan_head_before: 929338d
plan_head_after: db6f290e971dde3e67ea9a2527c6ee917d9fc1ff
key-files:
  created:
    - extensions/molecule/node-vm/molecule.yml
    - extensions/molecule/node-vm/prepare.yml
    - extensions/molecule/node-vm/converge.yml
    - extensions/molecule/node-vm/verify.yml
    - extensions/molecule/node-vm/vars/node-vm.yml
    - extensions/molecule/shared/verify_node.yml
    - .github/workflows/molecule-node-vm.yml
  modified:
    - extensions/molecule/vm/tasks/pebble.yml
key-decisions:
  - "Zero-AVC and runtime proof on both VMs reuse shared/verify_runtime.yml (traefik.service, bare-IP status 404) instead of a new AVC-only file"
  - "Task 2 commit was pushed together with the Task 1 fix, so one CI run on db6f290 proves both tasks"
requirements-completed: [STEAL-01]
---

# Phase 3 Plan 06: Two-VM node-vm stand Summary

Panel VM plus node VM converge in one Molecule scenario on enforcing AlmaLinux 10; the node's own domain holds a Pebble-issued certificate on 127.0.0.1:8443 that verifies with the issuer root, and from the Panel VM the node shows only the :80 redirect while 8443 is unreachable.

## What was built

- `node-vm` scenario: platforms `panel` (remnawave_panel, `XVPN_NODE_VM_PANEL_MEMORY`, default 4096) and `node` (remnawave_nodes, `XVPN_NODE_VM_NODE_MEMORY`, default 2048); converge runs `playbooks/panel.yml` then `playbooks/node.yml`; subscription page disabled for the runtime budget; Pebble custom ACME (QA-05, check.sh `check_acme_ca: OK`).
- `prepare.yml` imports `../vm/prepare.yml` with per-group `xvpn_prepare_hosts_names`, stores the Pebble issuer root on each VM, then maps the names of the other VM into `/etc/hosts` (one play gathering facts of both VMs first).
- `verify_node.yml`: `openssl s_client -verify_hostname -verify_return_error` against the stored root (30 x 5 s) with `Verification: OK`; `ss` assertion that 8443 binds `127.0.0.1` only.
- `verify.yml`: node-side verifier, runtime plus AVC-since-marker check on both VMs, and from the Panel VM the redirect probe (301/308 to https://node.xvpn.test/) and the negative case `loopback-entrypoint-from-panel`.
- Workflow `molecule-node-vm`: KVM gate, step "Memory budget" (floors Panel 3072, node 1536 MiB, required = panel + node + 1024 MiB, fails with `::error::` naming required and available MiB), then `molecule test -s node-vm`. Triggers: pull_request to main, workflow_dispatch, nightly cron `47 3 * * *`; never push.

## CI evidence (HEAD db6f290)

| Workflow | Run id | Result |
|----------|--------|--------|
| lint | 46145420767 | success |
| molecule-container | 46145420795 | success |
| molecule-node-vm (dispatched) | 46146662440 | success |

- Runner memory printed by the Memory budget step: `MemTotal: 15701 MiB, MemAvailable: 14842 MiB, nproc: 4` (required 7168 MiB). The first run (46144003808) printed 15983 / 15017 MiB, nproc 4.
- Leg duration: 10m19s (12:50:44 to 13:01:03 UTC); the first run took 11m26s.
- Idempotence: node ok=238 changed=0, panel ok=570 changed=0. Verify recap: node ok=42, panel ok=40, failed=0 (zero AVC on both VMs).
- No memory fallback checkpoint was needed (no allocation error, no oom-kill); the Panel VM RSS was not sampled because the budget never tripped.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Verification assertion parsed as a YAML mapping**
- **Found during:** Task 1 first CI run (46144003808, verify step; converge and idempotence were already green)
- **Issue:** `- xvpn_verify_node_tls.stdout is search('Verification: OK')` in an assert `that` list contains `: `, so YAML read it as a dict ("Conditional expressions must be strings"). The same colon had also broken the `until` expression at check.sh time.
- **Fix:** quoted the assert expression; folded the `until` expression.
- **Files modified:** extensions/molecule/shared/verify_node.yml
- **Commit:** 5dba3a0

**2. [Process] One CI run for both tasks**
- The Task 1 fix (5dba3a0) and Task 2 (db6f290) were pushed together to save a 10-minute VM leg; the single green dispatched run on db6f290 covers both tasks' acceptance. Each task still has its own commit.

## Known Stubs

None.

## Threat Flags

None. T-03-34 (no production Let's Encrypt): vars/node-vm.yml pins `xvpn_edge_acme_ca: custom` with Pebble, grep for acme-v02 / api.letsencrypt.org is 0. T-03-35 (loopback entrypoint reachable from outside): executed negative connect from the Panel VM plus `ss` assertion, both green.

## Notes

- `state update-progress` skipping (STATE.md milestone "v3.7.20" has no ROADMAP milestone headings) is the known pre-existing issue and was not touched.

## Self-Check: PASSED

Files found: extensions/molecule/node-vm/{molecule,prepare,converge,verify}.yml, vars/node-vm.yml, extensions/molecule/shared/verify_node.yml, .github/workflows/molecule-node-vm.yml. Commits fdf99e1, 5dba3a0, db6f290 are on origin/main.
