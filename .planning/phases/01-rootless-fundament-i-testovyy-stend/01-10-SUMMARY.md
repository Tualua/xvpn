PLAN_START: 54dfdc187dd8da44a0b3879cbf301546b802afbd

---
phase: 01-rootless-fundament-i-testovyy-stend
plan: 10
subsystem: ci
tags: [github-actions, molecule, preflight]
requires: [01-07, 01-08, 01-09]
provides: [container-tier CI with container + preflight scenarios, green CI evidence for guards of Plans 04-08]
affects: [01-12]
key-files:
  modified: [.github/workflows/molecule-container.yml]
key-decisions:
  - "No fix commits were needed: all guards from Plans 04-08 were green on first CI run"
requirements-completed: [QA-01, QA-02]
completed: 2026-11-24
status: complete
actuals:
  tokens: 3000
  tasks: 1
  commits: 1
plan_head_before: 54dfdc187dd8da44a0b3879cbf301546b802afbd
plan_head_after: 1a2bddf46fbd86c52c79604ae121b06e887fa6c0
---

# Phase 1 Plan 10: Preflight scenario in CI, guards green Summary

The container-tier matrix is now `scenario: [container, preflight]`; the first push (1a2bddf) made both `lint` (run 45339786162) and `molecule-container` (run 45339786193) green on main.

## Evidence

- molecule-container jobs: `container (container)` success, `container (preflight)` success.
- Idempotence: container scenario rocky10/alma10 changed=0 (ok=127); preflight 18 cases re-run changed=0 (ok=393).
- `bash scripts/check.sh` passes locally; origin/main equals local HEAD.
- Gates: no `# xvpn_negative_case:` line removed; `quadlet_validate.yml` and `verify_rootless.yml` not touched.

## Deviations from Plan

None - plan executed exactly as written. No fix commits; fallbacks (a)-(d) not applied in this plan (fallback a was already applied in Plan 09).
Wording note: Molecule 26.11 does not print "Idempotence completed successfully"; idempotence is evidenced by changed=0 in the idempotence play (same as Plan 09).

## Escalations

Task 2: not triggered.

## Known open items

- Plan 01-06 deferred branches (root-socket-without-uid, Podman-installed, empty-domains) are covered by the preflight scenario, which is now green in CI.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

Workflow edit present, commit 1a2bddf on origin/main, both runs success.
