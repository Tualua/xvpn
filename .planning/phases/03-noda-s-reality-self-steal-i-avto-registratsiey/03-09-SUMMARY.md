---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 09
subsystem: molecule-node-vm
status: complete
tags: [molecule, matrix, alma10, rocky10, oracle10, gate, avc, steal-05]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: certificate gate and node firewall (03-08), two-VM stand (03-06)
provides:
  - molecule-node-vm matrix over alma10, rocky10, oracle10 (env XVPN_NODE_VM_BOX, _VERSION, _URL, _SHA256, _SHA256_TYPE)
  - verify case gate-no-certificate (message and unchanged firewall-cmd --list-ports)
affects: [03-10, 03-16]
actuals:
  tokens: 9000
  tasks: 2
  commits: 5
plan_head_before: cfdaced
plan_head_after: 38a179fd997316d8fae0401f75635dbf379510d7
key-files:
  modified:
    - extensions/molecule/node-vm/molecule.yml
    - .github/workflows/molecule-node-vm.yml
    - extensions/molecule/node-vm/verify.yml
key-decisions:
  - "Box per leg through env interpolation; empty box_url/checksum/type accepted by the vagrant driver for the Alma catalog box"
  - "Vagrant rejects a box_version constraint with a direct box file (even empty), so the workflow deletes the box_version lines for Rocky/Oracle legs before molecule runs"
  - "Interpolation default ':-' with an empty value is invalid in Molecule; variables without default are used"
requirements-completed: [NODE-01, NODE-02, STEAL-05]
---

# Phase 3 Plan 09: node-vm matrix and gate failure case Summary

Two-VM node stack (Panel VM + node VM of the same OS) passes converge, idempotence and verify on AlmaLinux 10, Rocky Linux 10 and Oracle Linux 10; a missing certificate fails the gate with "certificate for ..." and "STEAL-05" and leaves the firewall ports unchanged; zero AVC on both VMs.

## CI evidence

Final run (dispatched, HEAD 38a179f): molecule-node-vm run 46159644747, success on all legs. Lint run 46159630240 success.

| Leg | Duration |
|-----|----------|
| rocky10 | 14 min 8 s |
| alma10 | 14 min 13 s |
| oracle10 | 11 min 30 s |

All far below the 90-minute limit. No AVC on any leg (the AVC check of verify_runtime.yml runs on both VMs).

Earlier failed runs (46157358678, 46157657244, 46158199018) were configuration issues fixed within plan scope, see deviations.

## Deviations from Plan

**1. [Rule 3 - Blocking] Molecule rejects `${VAR:-}` with empty default** — found in run 46157358678; replaced with `${VAR}` for url/checksum.

**2. [Rule 3 - Blocking] box_download_checksum_type must accompany checksum** — run 46157657244; type now comes from XVPN_NODE_VM_BOX_SHA256_TYPE (empty for Alma).

**3. [Rule 3 - Blocking] Vagrant rejects box version constraint with a direct box file** — run 46158199018 (Rocky/Oracle); a workflow step removes the `box_version` lines when the matrix version is empty. This is a small variant of the plan's fallback; check.sh still syntax-checks the scenario (check.sh passed).

**4. [Rule 1 - Bug] gate-no-certificate case lacked xvpn_edge_https_address** — the node role does not load edge defaults; the verify case passes `127.0.0.1:8443`.

No SELinux boolean, capability or permissive domain was added.

## Known Stubs

None.

## Self-Check: PASSED

Commits 85f4001, 4ce5feb, 2731c16, 2091f73, 38a179f present; modified files exist; CI green for HEAD.
