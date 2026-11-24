---
phase: 01-rootless-fundament-i-testovyy-stend
plan: 04
subsystem: testing
tags: [quadlet, podman-system-generator, molecule, selinux, negative-tests]
requires: [01-03, 01-09]
provides: [generator dry-run before LSR, shared rootless verify, container verify with three negative cases]
affects: [01-05, 01-07, 01-10, 01-11]
tech-stack:
  added: []
  patterns: [dry-run validation before deployment, rescue-based executed negative cases]
key-files:
  created:
    - roles/podman_rootless/tasks/quadlet_validate.yml
    - extensions/molecule/shared/verify_rootless.yml
    - extensions/molecule/shared/templates/xvpn-broken.container.j2
    - extensions/molecule/container/verify.yml
  modified:
    - roles/podman_rootless/tasks/quadlet.yml
    - extensions/molecule/container/molecule.yml
    - .ansible-lint
key-decisions:
  - "Generator rc is non-zero on a bad unit (RESEARCH A5 confirmed in CI: rc=1, 'converting \"xvpn-broken.container\": no Image or Rootfs key specified')"
  - "Negative cases for assert-in-loop failures are matched against the whole ansible_failed_result (to_json), because a loop failure hides the per-item msg"
requirements-completed: []
duration: n/a
completed: 2026-11-24
status: complete
actuals:
  tokens: 14000
  tasks: 2
  commits: 3
plan_head_before: d01a954cd5682e4d6d06340775078581cc51c312
plan_head_after: a797e488b23d4b0eed9975cb4a9c56240b2a5518
---

# Phase 1 Plan 04: Unit and input guards Summary

Quadlet specs are validated by `podman-system-generator --user --dryrun` as the service user before `fedora.linux_system_roles.podman` writes anything, and the container verify proves three rejections (broken unit, injected user name, relative template path) with no host change; CI run on a797e48 is green (lint and molecule-container, rocky10 and alma10, including verify).

## Task results

- Tasks were committed in TDD order (test first, then implementation); the test commit cannot be run locally (no Podman in the devcontainer), so CI is the behavioral tier.
- 1ed0242 `test(01-04)`: `shared/verify_rootless.yml` (packages, optional passt-selinux, user, shadow lock, home, subids, linger, sysctl, fixture unit, rw-edge bind probes for [80, 443] in the container tier with the :79 negative control), `container/verify.yml` with three marked negative cases, broken fixture, `verify` added to the container `test_sequence`.
- 5f4fa9d `feat(01-04)`: `quadlet_validate.yml` and its include in `quadlet.yml` before the LSR call. Specs with `state: absent` are skipped. Failure messages start with `Quadlet dry-run` and name the unit; positive assertion that each expected `.service` appears in stdout.
- a797e48 `fix(01-04)`: see deviations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ansible-lint treated shared task file as a playbook and rejected `become_method: sudo`**
- Found during: Task 2 (check.sh)
- Fix: `kinds: tasks` entry for `extensions/molecule/shared/*.yml` in `.ansible-lint` (outside `files_modified`, required); FQCN `ansible.builtin.sudo`
- Commit: 1ed0242

**2. [Rule 1 - Bug] bad-user-name and relative-template cases were not recorded**
- Found during: CI run 45332980389 (verify, both distros): final assert listed only `['broken-unit']`
- Issue: the role assert runs in a loop, so `ansible_failed_result.msg` is the generic loop message and the expected text sits in per-item results
- Fix: match the expected text against `ansible_failed_result | to_json` for those two cases; broken-unit keeps the strict `startswith('Quadlet dry-run')` check
- Commit: a797e48; CI run 45333612337 green

## Verification

- `bash scripts/check.sh`: `check.sh: OK`, including `syntax-check: extensions/molecule/container/verify.yml`.
- CI on a797e48: `lint` success, `molecule-container` success (converge, idempotence changed=0, verify with probes :80/:443, :79 negative control, three negative cases).

## Flagged assumptions

- RESEARCH A5 (generator rc non-zero on a bad unit) is now confirmed by CI output (rc=1); the stderr pattern and the stdout positive assertion remain as secondary signals.
- Regex-level input checks have executed negative tests; wrong-typed input is covered only by ansible-core argument_specs entry validation (unchanged).
- The VM tier (Plan 11) remains the authoritative before/after-reboot proof of the :443 bind.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

All created files exist; commits 1ed0242, 5f4fa9d, a797e48 are on origin/main.
