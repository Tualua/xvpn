---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 12
subsystem: edge
tags: [traefik, acme, letsencrypt, pebble, molecule, gap-closure]
requires:
  - phase: 02-panel-za-traefik-s-zaschischennym-vhodom
    provides: edge role with the le resolver (02-11)
provides:
  - per-CA ACME storage file (acme-production / acme-staging / acme-custom-<hash12>.json)
  - container-tier case edge-acme-storage-per-ca and VM-tier ACME CA switch block
  - README "Switching the ACME CA"
affects: [edge role, molecule tiers, README]
status: complete
commits: 4
plan_head_before: c11abd1
plan_head_after: ed8d4442e065fdfde4185129ad3685607209759b
actuals:
  tokens: 14000
  tasks: 3
  commits: 4
key-files:
  created: [roles/edge/vars/main.yml]
  modified:
    - roles/edge/templates/traefik.yml.j2
    - roles/edge/tasks/main.yml
    - scripts/gate/render.yml
    - extensions/molecule/shared/verify_edge.yml
    - extensions/molecule/container/verify.yml
    - extensions/molecule/vm/side_effect.yml
    - README.md
key-decisions:
  - "ACME store is one persistent 0600 file per CA; supersedes only the single acme.json name of D-13"
  - "Legacy acme.json is not migrated or read; only kept at 0600"
  - "VM CA switch uses the same Pebble with a query-string directory URL as a distinct CA identity (worked, no fallback needed)"
requirements-completed: [EDGE-02, QA-05]
---

# Phase 2 Plan 12: Per-CA ACME storage Summary

Closes UAT gap 02-UAT-G1: the le resolver now stores certificates in a file keyed by the selected CA, so changing `xvpn_edge_acme_ca` re-renders `traefik.yml`, restarts Traefik and orders from an empty store; switching back reuses the earlier store.

## Accomplishments

- `roles/edge/vars/main.yml` defines `xvpn_edge_acme_storage_file` and `xvpn_edge_acme_legacy_file`; the template, the gate render (`vars_files`) and `verify_edge.yml` (reads the active store from the rendered `traefik.yml`) all follow this single source.
- The role stats and chmods only the active and legacy stores (0600, rw-edge); it never creates, reads or prints a store (T-02-05, T-02-42).
- Container tier: staging path assertion plus the positive case `edge-acme-storage-per-ca` (five scratch renders; distinct per CA, same for a repeated value).
- VM tier: block "ACME CA switch" (restart on switch, new store issued with the Panel domain, original store sha256 unchanged, switch back restarts and serves the same leaf fingerprint).
- README: store table row and a "Switching the ACME CA" subsection.

## CI results (pushed HEAD ed8d444)

- lint: success; gate: success.
- molecule-vm (dispatched): rocky10 success, alma10 success (after one rerun of an unrelated flake), oracle10 failure (see Deferred).
- molecule-container: first attempt failed on rocky10 only (negative case `panel-divergent-secret` missing from the rejected list, an unrelated flake in the secrets role); the rerun of the failed job succeeded.
- Earlier HEAD 766d182: lint, molecule-container, gate all success.

## Deviations from Plan

**1. [Rule 1 - Bug] CA-switch probes used the openssl CLI, absent on the VM**
- **Found during:** Task 3 first dispatched VM run (rocky10, rc 127)
- **Fix:** probes use `python3` ssl (SNI handshake and sha256 of the DER certificate); no package installed
- **Files:** extensions/molecule/vm/side_effect.yml
- **Commit:** ed8d444

**2. [Rule 3 - Lint] ansible-lint name[casing]** for task names starting with lowercase `edge-acme-storage-per-ca`; names now start with `Edge-acme-storage-per-ca`. Commit 1c7993d.

## Deferred Issues (out of scope)

- oracle10 VM prepare fails in `extensions/molecule/vm/tasks/pebble.yml` ("Unable to find required tar"): oracle10 was added to the matrix by quick task ej4 after the last green VM run; not caused by this plan.
- Flaky `Panel secrets | draw passwords ...` retry exhaustion (alma10, first VM attempt) and flaky `panel-divergent-secret` negative case (rocky10 container): both pre-existing, passed on rerun/earlier runs.

## Human check pending

Re-run UAT test 2 on the real Panel host with `xvpn_edge_acme_ca: production`.

## Self-Check: PASSED

Files present (roles/edge/vars/main.yml, this SUMMARY); commits 95911d5, 1c7993d, 766d182, ed8d444 are on main.
