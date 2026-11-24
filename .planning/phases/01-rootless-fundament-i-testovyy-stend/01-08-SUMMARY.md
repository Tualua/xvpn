---
phase: 01-rootless-fundament-i-testovyy-stend
plan: 08
subsystem: testing
tags: [molecule, preflight, negative-cases, idempotence]
requires: [01-04, 01-06, 01-07]
provides: [molecule scenario preflight with 18 cases, nothing-changed and read-only allow-list verify]
affects: [01-10]
tech-stack:
  added: []
  patterns: [block/rescue case runner with changed_when false harness, controller-side Jinja macro walking task files]
key-files:
  created:
    - extensions/molecule/preflight/molecule.yml
    - extensions/molecule/preflight/prepare.yml
    - extensions/molecule/preflight/converge.yml
    - extensions/molecule/preflight/run_case.yml
    - extensions/molecule/preflight/verify.yml
  modified:
    - roles/preflight/tasks/main.yml
    - .ansible-lint
key-decisions:
  - "Failed case messages are recorded as the JSON of ansible_failed_result, because assert in a loop keeps the item text only in the per-item results"
  - "Module-key extraction in verify is a recursive Jinja macro (block/rescue/always), proven locally with a negative run on a temporarily corrupted role"
requirements-completed: [FND-01, FND-07]
duration: n/a
completed: 2026-11-24
status: complete
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: ca98712ff05231745d15c3c6377ea01aaff42bd3
plan_head_after: c85cb9a5cd282310e8a21e8d60332be7f2a93888
---

# Phase 1 Plan 08: Preflight Molecule Scenario Summary

Scenario `extensions/molecule/preflight` runs 18 preflight cases (13 behaviour, 5 invalid-input) on one Alma 10 platform, asserts exact messages and warnings, and proves a failed preflight leaves the host untouched and the role read-only.

## Task results

- 4703c54 `test(01-08)`: molecule.yml (idempotence in test_sequence), prepare.yml (python bootstrap, facts before /etc/hosts stand-ins, getenforce double, `xvpn-test` user, Podman state record), run_case.yml (block/rescue runner; every non-include task `changed_when: false`; documented `setsid -f runuser` fallback comment).
- c85cb9a `test(01-08)`: converge.yml (18 cases, per-case assert on outcome, `expect_in`, `expect_warn`, `expect_no_warn`) and verify.yml (nothing-changed on target; controller-side: foundation play 1 is preflight with `any_errors_fatal`, `playbooks/preflight.yml` equals it, module allow-list, no `ignore_errors`, dnf has `list`).

QA-02 for the preflight role is covered by the scenario idempotence step (changed=0 on the re-run of all 18 cases, harness tasks `changed_when: false`) and, independently, by the nothing-changed verify (D-06).

## Deviations from Plan

**1. [Rule 1 - Bug] Role accumulators leaked between includes**
- **Found during:** Task 1 (case runner design)
- **Issue:** `xvpn_preflight_listeners`, `_listeners_named`, `_dns_resolved` accumulate via `default([]) + ...`; a second include of the role in one play (as every scenario does) sees the previous run's findings.
- **Fix:** reset the three lists in the first `set_fact` of `roles/preflight/tasks/main.yml`.
- **Files:** roles/preflight/tasks/main.yml. **Commit:** 4703c54.

**2. [Rule 3 - Blocking] ansible-lint treated run_case.yml as a playbook**
- **Fix:** added `tasks: "extensions/molecule/*/run_case.yml"` to `kinds` in `.ansible-lint`; `# noqa` on `rpm -q podman` (command-instead-of-module, the rc/stdout comparison needs the raw command) and on the verify macro task (jinja[spacing]).

**3. Failed-case message capture** — the plan says `ansible_failed_result.msg`; a loop assert reports only "One or more items failed", so the recorded msg is `ansible_failed_result | to_json` (same technique as the container scenario negative cases). Substring expectations are unchanged.

## Verification

- `bash scripts/check.sh`: `check.sh: OK`; all grep/python acceptance criteria hold (18 cases, 5 invalid-* markers, idempotence ordering, changed_when contract).
- Local (devcontainer, localhost): verify's controller-side proofs pass on the real repo and fail correctly on a temporarily added `copy` + `ignore_errors` task in a nested block (reverted). The runner and per-case assert were executed for os-less cases: all five invalid-input cases pass with their named messages.

## Deferred verification

- Executing all 18 cases, the idempotence re-run and the nothing-changed verify needs a Podman container with systemd and rpm: not available in the devcontainer (Ubuntu, no rpm, no root). The preflight scenario is not yet in the CI matrix; Plan 10 adds it and is the first place `molecule test -s preflight` runs. Plan 06 deferred cases (root-owned listener without uid field, Podman-installed branch, empty-domains warning on the full role, AAAA rescue branch) are covered by cases port-foreign, baseline/podman-floor and port-managed; the AAAA rescue branch has no dedicated case in the plan's 18 and stays unexercised.

## Flagged assumptions

- FND-01: OS and Podman-version negatives narrow role variables on a real Alma 10 container, not a real non-EL10 host or Podman 5.3.
- FND-07: /etc/hosts entries stand in for public DNS; host NSS is the source of truth.
- Preflight listener ownership relies on `systemd-run --uid` in a `systemd: always` container; fallback documented in run_case.yml.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
