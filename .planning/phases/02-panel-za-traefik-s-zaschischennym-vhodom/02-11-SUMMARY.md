---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 11
subsystem: panel
tags: [subscription-page, toggle, readme, doc-04, molecule-vm]
requires:
  - phase: 02-10
    provides: subscription page unit, env file, route file and verify_subpage.yml
provides:
  - disabled path of the subscription page (stop, then remove unit, subpage.env and route)
  - container case panel-subpage-toggle and VM block "Sub-page toggle cycle"
  - README section "Panel host" with "Known limitations"
affects: [03, 05]
tech-stack:
  added: []
  patterns: [explicit stop before removal; activate-aware removal path]
key-files:
  created: []
  modified:
    - roles/panel/tasks/subpage.yml
    - roles/panel/tasks/main.yml
    - extensions/molecule/container/verify.yml
    - extensions/molecule/vm/side_effect.yml
    - README.md
key-decisions:
  - "main.yml always includes subpage.yml; the file holds both the enabled and the disabled branch (blocks on xvpn_panel_subscription_enabled)"
  - "The LSR cleanup always needs the user manager bus, so with xvpn_panel_activate false (nothing was ever started) the unit file is removed directly instead of through the quadlet entry point"
requirements-completed: [SUB-01, DOC-04]
status: complete
commits: 3
plan_head_before: 00402cb283803108fd9dfa3955856a664cf14659
plan_head_after: 5d2952718f47e5738ce40c5b8d07eaac4b7864e8
actuals:
  tokens: 9000
  tasks: 2
  commits: 3
---

# Phase 2 Plan 11: Sub-page toggle and Panel README Summary

The subscription page can be switched off with one variable: the running unit is stopped first, then the unit file, `subpage.env` (it holds the API token) and the route file are removed; switching back restores them. The README now documents the whole Panel playbook.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Tracer: toggle off stops and removes, toggle on restores | 4a00ddc, 5d29527 (fix) |
| 2 | README "Panel host" section | ef0a8b9 |

## CI for the final HEAD (5d29527)

- lint, gate, molecule-container: success.
- molecule-vm (dispatched run 45669968510): success. Job durations: vm (alma10) 18m57s, vm (rocky10) 24m48s, both far below the 90 minute budget.
- The first container run for ef0a8b9 failed (see deviations); intermediate pushes were cancelled or superseded, so the green runs above are for the final HEAD.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] LSR cleanup fails without a user manager**
- **Found during:** Task 1 (container tier, panel-subpage-toggle)
- **Issue:** the quadlet entry point with `state: absent` runs the LSR cleanup, which stops the service through the user manager; the container tier has none (`Failed to connect to user scope bus`).
- **Fix:** quadlet removal runs only when `xvpn_panel_activate` is true; otherwise the unit file is removed with `ansible.builtin.file`.
- **Files modified:** roles/panel/tasks/subpage.yml
- **Commit:** 5d29527

**2. [Rule 3 - Blocking] main.yml gated the include**
- **Found during:** Task 1
- **Issue:** `main.yml` included `subpage.yml` only when the page was enabled, so a disabled branch could never run.
- **Fix:** the gate moved into `subpage.yml` (two blocks); `main.yml` includes it unconditionally.
- **Commit:** 4a00ddc

**Total deviations:** 2 auto-fixed. **Impact:** none on scope.

## Known Stubs

None.

## Notes

- `check_secrets` (gitleaks) does not run locally (gitleaks not installed); it ran in the CI lint job and passed on the README.
- molecule-vm was dispatched with `gh workflow run` and watched with `gh run watch` instead of `ci_watch.sh --dispatch`, to avoid a long-lived watcher process; the result was confirmed with `gh run view`.

## Self-Check: PASSED
