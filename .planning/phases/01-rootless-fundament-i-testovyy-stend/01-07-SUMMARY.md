---
phase: 01-rootless-fundament-i-testovyy-stend
plan: 07
subsystem: common
tags: [firewalld, selinux, ssh-guard, molecule, negative-cases]
requires: [01-04, 01-05, 01-06]
provides: [role xvpn.remnawave.common, shared verify_common.yml, executed guard negatives no-ssh-zone / port-without-protocol / selinux-permissive]
affects: [01-10, 01-11, 01-12]
tech-stack:
  added: []
  patterns: [add-only firewalld via ansible.posix.firewalld, SSH guard before and after the change, exact-set firewall verify]
key-files:
  created:
    - roles/common/defaults/main.yml
    - roles/common/meta/main.yml
    - roles/common/meta/argument_specs.yml
    - roles/common/tasks/main.yml
    - roles/common/tasks/firewalld.yml
    - extensions/molecule/shared/verify_common.yml
  modified:
    - playbooks/foundation.yml
    - extensions/molecule/container/converge.yml
    - extensions/molecule/container/verify.yml
key-decisions:
  - "SSH guard is written out twice inside firewalld.yml (before and after the port loop) instead of a separate include file, so the plan's grep gates hold"
  - "Task names use 'before -' / 'after -' because a colon inside an unquoted name breaks YAML"
requirements-completed: [FND-06]
duration: n/a
completed: 2026-11-24
status: complete
commits: 3
plan_head_before: 478330f
plan_head_after: 0df220d804bff730ccc745435829dbc6b63b82ff
actuals:
  tokens: 14000
  tasks: 2
  commits: 3
---

# Phase 1 Plan 07: Role common (SELinux gate, add-only firewalld, SSH guard) Summary

Role `xvpn.remnawave.common` installs the host baseline, refuses to run unless getenforce prints Enforcing, and only adds the declared ports to the public interface's firewalld zone, with an SSH-allowed assertion before and after the change.

## What was built

- `roles/common`: port and interface validation ("Invalid firewall port entry", "Invalid xvpn_public_interface"), dnf baseline packages, SELinux Enforcing gate ("SELinux must be Enforcing"), firewalld enable/start (skipped in offline mode), zone discovery with the default-zone fallback, a NOTICE when the default-route interface is used, and `ansible.posix.firewalld` additions with `state: enabled` only. `xvpn_public_interface` is read with `| default('')` and has no default in this role.
- `playbooks/foundation.yml`: play 2 runs `common` before `podman_rootless`.
- `verify_common.yml`: SELinux Enforcing, exact-set port check against `xvpn_verify_expected_ports`, services allow-list, no 3000/3010/8443/2222 in ports/forward ports/rich rules, SSH still allowed, firewalld active when online. The header documents the cross-phase contract of the expected-ports set.
- Container scenario: converge sets offline mode and `80/tcp`; verify includes `verify_common.yml` with `firewall-offline-cmd` and runs three new negative cases (six in total).

## TDD

RED commit 2494d98 added the verify and negative cases before the role existed; GREEN commits followed with the role and the wiring.

## Verification

- `bash scripts/check.sh` returns `check.sh: OK` locally (yamllint is not installed in the devcontainer; CI enforces it).
- CI on main for the final push (runs 45336575664 lint, 45336575587 molecule-container) both succeeded. The container tier executed verify_common and all six negative cases, including the flagged assumption that `firewall-offline-cmd --get-zone-of-interface` resolves a bound dummy interface.
- Deferred to the VM tier (Plans 11-12): online `firewall-cmd` path (`immediate: true`), real SELinux enforcing, and the zero-AVC proof that no boolean or port is needed.
- The foundation role-order check was run by grep because the devcontainer has no PyYAML. The playbook diff shows `common` before `podman_rootless`, and check.sh syntax-checks it.

## Deviations from Plan

**1. [Rule 3 - Blocking] SSH guard inlined in firewalld.yml**
- **Found during:** Task 1. A first draft used a separate `ssh_guard.yml`, which would have failed the plan's grep acceptance gate on `firewalld.yml`.
- **Fix:** Inlined the guard twice in `firewalld.yml` and removed the extra file.
- **Commit:** feat(01-07) role commit.

**2. [Rule 1 - Bug] yamllint line length and task-name colon**
- Wrapped a 176-character assertion in verify.yml and removed colons from task names. Both were caught by check.sh before the commit.

## Requirements

FND-06 is marked complete (ready per `requirements.ready-ids`). FND-05 is reported as blocked by the tool because the VM-tier verification (Plans 11-12) is not done, so it is intentionally left open.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

Role files exist, commits 2494d98 and the two feat commits are on main, CI green.
