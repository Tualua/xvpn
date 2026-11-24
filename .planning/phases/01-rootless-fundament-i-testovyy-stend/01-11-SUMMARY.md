---
phase: 01-rootless-fundament-i-testovyy-stend
plan: 11
subsystem: testing
tags: [molecule, vagrant, libvirt, selinux, dontaudit, reboot, avc]
requires: [01-04, 01-05, 01-06, 01-07]
provides: [molecule scenario vm (alma10, rocky10), shared verify_runtime task file]
affects: [01-12]
tech-stack:
  added: []
  patterns: [dontaudit positive control via seinfo, AVC window from a prepare marker, policy sha256 pinned across reboot, per-path label comparison against the /home twin]
key-files:
  created:
    - extensions/molecule/vm/molecule.yml
    - extensions/molecule/vm/prepare.yml
    - extensions/molecule/vm/converge.yml
    - extensions/molecule/vm/side_effect.yml
    - extensions/molecule/vm/verify.yml
    - extensions/molecule/shared/verify_runtime.yml
  modified: []
key-decisions:
  - "Box integrity keys are community.vagrant's box_download_checksum / box_download_checksum_type; the plan's box_checksum is not a key the driver reads and would silently drop the pin"
  - "The four D-08 label paths are defined once, in the vars of a block, and looped by the label tasks"
  - "policycoreutils-python-utils is installed in prepare so audit2why diagnostics work; it is diagnostics only"
requirements-completed: []
duration: n/a
completed: 2026-11-24
status: complete
actuals:
  tokens: 16000
  tasks: 2
  commits: 2
plan_head_before: 7e0eb7ef85ae5c6436d66b22c8f22a09bd19aec7
plan_head_after: be18c177576fcc4bb54b12f8db26123b7e3163eb
---

# Phase 1 Plan 11: VM Molecule Scenario Summary

Scenario `extensions/molecule/vm` boots checksum-pinned AlmaLinux 10 and Rocky 10 libvirt boxes, proves dontaudit is off, converges the real foundation, reboots, and asserts runtime, labels and zero AVC before and after. It has not been executed: the devcontainer has no Vagrant, libvirt or KVM.

## Task results

- 1a7e524 `feat(01-11)`: `molecule.yml` (both boxes versioned and sha256-pinned, `cpu_mode: host-passthrough`, full test sequence with `side_effect`), `prepare.yml` (auditd, seinfo positive control > 0, `semodule -DB`, count == 0, only then the AVC marker), `converge.yml` (foundation without container overrides, fixture activated, InvocationID recorded with `force: false`).
- be18c17 `test(01-11)`: `shared/verify_runtime.yml`, `vm/side_effect.yml` (unchanged-unit InvocationID check, `systemctl --user` restart round-trip, policy sha256, reboot), `vm/verify.yml` (policy sha256 unchanged, shared verifies).

## Box pins

- Alma: `10.2.20260914` libvirt/amd64, sha256 `24b3ff7c...e2f9c1` taken from the Vagrant Cloud API provider record (publisher-supplied, no trust-on-first-use needed).
- Rocky: `Rocky-10-Vagrant-Libvirt-10.3-20261112.0`, sha256 `491cf68a...159ea` from the `CHECKSUM` file on dl.rockylinux.org (never the `latest` symlink).

## Deviations from Plan

**1. [Rule 1 - Bug] Wrong checksum key name in the plan**
- **Found during:** Task 1
- **Issue:** The plan and its acceptance regex use `box_checksum`. The `community.vagrant` module (which molecule-plugins passes `platforms` to) reads `box_download_checksum` and `box_download_checksum_type`; an unknown key is ignored, so T-01-19 would have had no effect.
- **Fix:** Used the real keys. The acceptance regex `box_checksum: [0-9a-f]{64}` therefore prints 0, not 2; the equivalent check on `box_download_checksum: [0-9a-f]{64}` prints 2.
- **Files modified:** extensions/molecule/vm/molecule.yml
- **Commit:** 1a7e524

**2. [Rule 3 - Blocking] Literal `semodule -DB` count**
- **Found during:** Task 1
- **Issue:** The verify requires exactly one line containing `semodule -DB`, but the mandated fail_msg text mentioned it.
- **Fix:** The two fail messages say "the dontaudit disable" instead; only the command line carries the literal.
- **Commit:** 1a7e524

**3. [Rule 2 - Missing diagnostics] audit2why package**
- **Issue:** `audit2why` ships in `policycoreutils-python-utils`, absent from the plan's prepare package list.
- **Fix:** Added to the prepare dnf list (distro AppStream, VM tier only). The audit2why task has `failed_when: false`, so it never masks the AVC assertion.
- **Commit:** be18c17

**4. Block-level `vars` for the label paths**
The acceptance regex requires the four relative paths to occur exactly once as list items, so the label tasks sit in one `block` whose `vars` define `xvpn_verify_label_paths` (looped with `loop_var: xvpn_label_rel`).

**Total deviations:** 4 (1 bug, 1 blocking, 1 missing diagnostics, 1 structural). **Impact:** none on scope.

## Verification

- `bash scripts/check.sh`: `check.sh: OK` (ansible-lint production, syntax-check of all vm playbooks, collection build). yamllint is not installed locally (CI lint job enforces it); no line exceeds 160.
- The Jinja expressions for the dontaudit count, twin type and dynamic argv were evaluated locally with `ansible-playbook` on sample strings.
- All Task 1 and Task 2 acceptance greps and python checks pass, except the `box_checksum` regex (Deviation 1).
- **Deferred to plan 01-12:** running the scenario (`molecule test -s vm`). The devcontainer has no Vagrant, libvirt or KVM, so no VM-run verify was executed or faked.

## Accepted and flagged items

- Alma box checksum: from the Vagrant Cloud API (not trust-on-first-use).
- D-10(c): the unchanged-unit half is executed (InvocationID unchanged across idempotence); the changed-unit half rests on reading the LSR source and is accepted.
- D-08 (`/var/lib/xvpn` with the `/home` equivalence) is the highest-risk unproven decision. It is proven or escalated when plan 01-12 first runs this scenario. Any AVC or label mismatch stops there at the conditional Task 3 `checkpoint:decision`; nothing is auto-fixed.
- Unverified until the first VM run: `box_architecture: amd64` on URL boxes, `seinfo` reflecting the loaded kernel policy, `ausearch` printing `<no matches>` with rc 1, `matchpathcon` presence (fallback `selabel_lookup -b file -k` is built in).
- Podman 5.x is not covered by a VM leg (D-22, deferred to QA-06).

## Requirements

QA-03, FND-02, FND-03, FND-04 and FND-05 are left pending. They are proven only when the VM scenario actually runs in plan 01-12; static checks alone do not prove them.

## Known Stubs

None.

## Self-Check: PASSED

- All six key files exist; commits 1a7e524 and be18c17 are on `main`; `check.sh: OK`.
