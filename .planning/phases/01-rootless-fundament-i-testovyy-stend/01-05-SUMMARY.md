---
phase: 01-rootless-fundament-i-testovyy-stend
plan: 05
subsystem: preflight
tags: [preflight, selinux, getenforce, playbooks]
requires: [01-03, 01-09]
provides: [role xvpn.remnawave.preflight (OS + SELinux), two-play foundation.yml, standalone playbooks/preflight.yml]
affects: [01-06, 01-07, 01-08]
tech-stack:
  added: []
  patterns: [error aggregation with one final fail, read-only first play with any_errors_fatal]
key-files:
  created:
    - roles/preflight/defaults/main.yml
    - roles/preflight/meta/main.yml
    - roles/preflight/meta/argument_specs.yml
    - roles/preflight/tasks/main.yml
    - playbooks/preflight.yml
  modified:
    - playbooks/foundation.yml
key-decisions:
  - "getenforce is run as a bare command (PATH lookup) and the selinux fact is not used"
  - "Play 1 of foundation.yml and playbooks/preflight.yml are identical literal plays (no import_playbook)"
requirements-completed: []
duration: n/a
completed: 2026-11-24
status: complete
actuals:
  tokens: 4000
  tasks: 2
  commits: 2
plan_head_before: 90d77f7cc1a70c8ca2f75664b6ccfaa893b7e480
plan_head_after: 2ea0c203061727641b78439e60af97c89fabea59
---

# Phase 1 Plan 05: Preflight OS/SELinux Summary

Role `preflight` collects OS and SELinux (getenforce) errors into one list and fails once with "nothing was changed"; it runs as the read-only first play of `foundation.yml` and standalone via `playbooks/preflight.yml`.

## Task results

- 01eb4e1 `feat(01-05)`: role with defaults, meta, argument_specs (distribution choices narrowed to Rocky/AlmaLinux), aggregated tasks. A missing or failing `getenforce` yields an aggregated message ending with "install libselinux-utils".
- 2ea0c20 `feat(01-05)`: preflight play (`any_errors_fatal: true`, tag `preflight`) inserted before Foundation; identical single-play `playbooks/preflight.yml`.

## Deviations from Plan

None - plan executed as written. TDD note: the plan's behavior cases are exercised by the preflight scenario in Plan 08, so no separate RED commit exists in this plan; behavior was instead checked locally (below).

## Verification

- `bash scripts/check.sh`: `check.sh: OK`.
- Local behavioral run on the devcontainer (Ubuntu host, `getenforce` double on PATH): Permissive plus unsupported OS gave one fail listing both lines; absent `getenforce` gave "getenforce not found or failed (rc 2); install libselinux-utils". The Enforcing success path was not run locally (host is not EL10); in CI the container tier covers it.
- CI on 2ea0c20: `lint` and `molecule-container` success (two-play foundation converges, idempotence holds).
- The structural python check from the plan (`python3 -c "import yaml..."`) was not run: PyYAML is absent in the devcontainer. The same facts hold by inspection of the two files and the grep acceptance criteria; Plan 08 re-asserts identity.

## Flagged assumptions

- In the container tier `getenforce` is a test double (Plan 02 prepare); real SELinux mode is only read in the VM tier (Plans 11-12).
- FND-01 and FND-06 stay open: `requirements.ready-ids` lists both as blocked (remaining plans close them).

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
