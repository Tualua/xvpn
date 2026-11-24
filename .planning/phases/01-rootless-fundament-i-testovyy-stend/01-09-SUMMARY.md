---
phase: 01-rootless-fundament-i-testovyy-stend
plan: 09
subsystem: ci
tags: [github-actions, molecule, ansible-lint, supply-chain]
requires: [01-03]
provides: [requirements-dev.txt, lint workflow, molecule-container workflow, first green CI run of the tracer]
affects: [01-04, 01-05, 01-10, 01-12]
tech-stack:
  added: [molecule 26.11.0, molecule-plugins 26.11.0, ansible-lint 26.11.0, yamllint 1.38.0]
  patterns: [SHA-pinned actions, permissions contents read, CI-hard quality gate]
key-files:
  created: [requirements-dev.txt, .github/workflows/lint.yml, .github/workflows/molecule-container.yml]
  modified: [extensions/molecule/container/prepare.yml, roles/podman_rootless/tasks/main.yml]
key-decisions:
  - "CI runs ansible-core 2.21 only; the 2.22 leg is deferred to QA-06 (D-23)"
  - "Container scenario starts systemd-logind in prepare.yml (fallback a); VM tier untouched"
requirements-completed: []
duration: n/a
completed: 2026-11-24
status: complete
actuals:
  tokens: 40000
  tasks: 3
  commits: 4
plan_head_before: 914f230
plan_head_after: 09c5393
---

# Phase 1 Plan 09: CI workflows and first green tracer Summary

PLAN_START: 7a19a6ac225b46c68bada8618d8609df47fd9ee9 (HEAD at push time, after Task 1 commit)

Pinned dev tooling and two SHA-pinned least-privilege workflows (`lint`, `molecule-container`); the tracer from Plans 01-02 converges and is idempotent (changed=0) on rocky10 and alma10 in CI.

## Task results

- Task 1 (7a19a6a): `requirements-dev.txt`, `lint.yml`, `molecule-container.yml`. Actions: `actions/checkout` v7.0.1 (3d3c42e5...), `actions/setup-python` v7.1.0 (6d4fd22b...), SHAs from `git ls-remote`.
- Task 2: blocking checkpoint, answer "approved, push ok". Part A approved as presented: PyPI pins (molecule, molecule-plugins[podman,vagrant], ansible-lint, yamllint, ansible-core) incl. transitive python-vagrant 1.0.0; RubyGems vagrant-libvirt 0.12.2 and HashiCorp apt as conditional fallbacks for Plan 12; transitive Galaxy `community.library_inventory_filtering_v1` 1.1.5. Part B confirmed: origin `https://github.com/Tualua/xvpn.git`, visibility PUBLIC, gh auth exit 0, 15 local commits pushed.
- Task 3: `galaxy.yml` repository already equals origin (no change). Pushed with plain `git push origin main`; three fix rounds on distinct failures (below); final runs green.
- Task 4: not triggered (every failure was fixed in 1 round, fallback (a) resolved).

## Deviations from Plan

### Auto-fixed Issues (CI repair loop, one round each)

**1. [Rule 1 - Bug] prepare bootstrap used `&&` through raw without a shell**
- Log (run 45329980682): `test: extra argument '&&'`
- Fix: wrap in `/bin/sh -c '...'`; file `extensions/molecule/container/prepare.yml`; commit 48439bb

**2. [Rule 1 - Bug] sysctl drop-in directory missing in the image**
- Log (run 45330303997): `[Errno 2] No such file or directory: '/etc/sysctl.d/.ansible_m_sysctl_*.conf'`
- Fix: role now creates the drop-in directory before writing (genuine robustness fix, no assertion relaxed); file `roles/podman_rootless/tasks/main.yml` (outside `files_modified`, recorded as required); commit 464a5e2

**3. [Fallback a] systemd-logind not running, linger failed**
- Log (run 45331157489): `Could not enable linger: Could not activate remote peer 'org.freedesktop.login1': activation request failed: unit is invalid`
- Fix: unmask and start `systemd-logind` in container prepare.yml only; no expectation changed; commit 09c5393

**4. [Transient] lint run 45331597799 failed on Galaxy `HTTP Error 502: Bad Gateway`**
- Not a code defect; the failed job was re-run and passed.

**5. [Wording] acceptance criterion "Idempotence completed successfully" not literally present**
- Molecule 26.11 logs `idempotence: Executed: Successful`; recap shows `changed=0` for rocky10 and alma10 in the idempotence play. Criterion intent met.

**Total deviations:** 3 auto-fixed + 1 transient + 1 wording. No assertion, guard or expectation was weakened (prohibition QA-02 honoured).

## Evidence

- Latest `lint` and `molecule-container` runs on main for 09c5393: success (molecule run 45331597683; all jobs `["success"]`).
- `git ls-remote origin refs/heads/main` equals local HEAD 09c5393 at that time.

## Escalations

None. Task 4 not triggered.

## Authentication Gates

None (gh already authenticated).

## Known Stubs

None.

## Requirements

`requirements.ready-ids` reported QA-01, QA-02, FND-06 as blocked (shared with sibling plans that have no SUMMARY yet); none marked complete here.

## Threat Flags

None.

## Self-Check: PASSED

Files exist (requirements-dev.txt, both workflows); commits 7a19a6a, 48439bb, 464a5e2, 09c5393 are on origin/main; `bash scripts/check.sh` passes locally.
