---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 04
subsystem: panel
tags: [secrets, no_log, panel, molecule, panel-02, doc-04]
status: complete

requires:
  - phase: 02-panel-za-traefik-s-zaschischennym-vhodom
    provides: panel role skeleton, edge role, VM tier edge verify (plans 02-02, 02-03)
provides:
  - generate-once secrets file /var/lib/xvpn/rw-panel/secrets/panel-secrets.yml (0600, dir 0700) with eight keys
  - full panel input surface (domains, images, seven vault override inputs)
  - guards: rotation refusal (D-10), lost-secrets refusal, corrupt-file refusal, placeholder/format asserts, gate path/cookie coupling (D-06)
  - scripts/check_no_log.py static DOC-04 gate wired into scripts/check.sh
affects: [02-05, 02-06, 02-07, 02-08, 02-09, 02-10, phase-03, phase-05]

actuals:
  tokens: 24000
  tasks: 2
  commits: 2
plan_head_before: 3ad147c83d2ce1c2d9575a4295ce719548c247f2
plan_head_after: aa5b6c10167dbec6c0b13df842c96e2b5c091a49

key-files:
  created:
    - roles/panel/tasks/secrets.yml
    - scripts/check_no_log.py
  modified:
    - roles/panel/defaults/main.yml
    - roles/panel/meta/argument_specs.yml
    - roles/panel/tasks/main.yml
    - playbooks/panel.yml
    - scripts/check.sh
    - extensions/molecule/container/converge.yml
    - extensions/molecule/container/verify.yml

key-decisions:
  - "Guard asserts read only boolean/key-list facts (corrupt verdict, divergent keys, invalid keys), so they fail with a visible message that names keys and never a value, while every task that touches a value keeps no_log"
  - "Placeholder/format check runs before the divergence check, so a placeholder override is reported as a placeholder even when a stored value exists"
  - "check.sh runs check_no_log.py with the interpreter of ansible-playbook (it ships PyYAML); falls back to python3"

requirements-completed: [PANEL-02, DOC-04]

duration: 75min
completed: 2026-11-25
---

# Phase 2 Plan 04: Panel secrets file and DOC-04 guards Summary

Generate-once Panel secrets file (eight keys, 0600) with refusal of rotation, loss, corruption and placeholders, plus a mutation-tested static no_log gate.

## What was built

- `roles/panel/tasks/secrets.yml`: read the stored file, generate missing values on the controller in memory (`password` lookup with `/dev/null`, shuffled segment passwords), merge override > stored > generated, write with one `copy` (0600, owner rw-panel, `no_log`, `diff: false`). The result is exposed as the run-scoped fact `xvpn_panel_secrets`.
- Guards: corrupt/empty/foreign-key file, lost secrets with existing `remnawave-db-data` volume, placeholder and format asserts for all eight keys, divergence refusal for app_secret, postgres_password, metrics_password, admin_password (D-10), gate path rotation regenerates the cookie value unless it is overridden (D-06).
- `roles/panel/defaults`, `argument_specs`, `tasks/main.yml` (subscription domain assert, service user check), `playbooks/panel.yml` (subscription domain in preflight and a required-input pre_task).
- `scripts/check_no_log.py` plus the call in `scripts/check.sh` (prints `check_no_log: OK`).
- Container tier: positive checks (modes, key set), five new negative cases (fourteen in total), and the positive `panel-gate-override` case.

## Verification

- `bash scripts/check.sh` exits 0, `check_no_log: OK` printed once.
- Task 1 HEAD 1cd0cf1: lint and molecule-container success. Task 2 HEAD aa5b6c1: lint (success), molecule-container run 45590474401 (success, idempotence changed=0, fourteen negative cases and gate-override), molecule-vm dispatched run 45591418140 (success).
- Mutation check: removing `no_log: true` from the secrets write task made `check_no_log.py` exit 1 ("task 'Panel secrets | write the secrets file' touches a secret without no_log/diff: false"); reverted, gate back to OK.
- Local pre-push test of secrets.yml on localhost: first run changed=2, second run changed=0, file mode 600; all guards produced the expected key-naming messages.
- Backend 3.4.11 admin password policy regex, read from upstream `libs/contract/commands/auth/register.command.ts` (main) at execution time: `/^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9]).{24,}$/`, min 24 (identical to RESEARCH).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Guard order and no_log on asserts**
- **Found during:** Task 2 local test
- **Issue:** with `no_log` on an assert the failure message is censored (negative cases could not match), and the divergence check ran before the placeholder check so a placeholder override was reported as a rotation.
- **Fix:** asserts read plain boolean/key-list facts computed in `no_log` set_fact tasks; the placeholder check is placed before the divergence check.
- **Files modified:** roles/panel/tasks/secrets.yml
- **Commit:** aa5b6c1

**2. [Rule 3 - Blocking] check_no_log.py needs PyYAML locally**
- **Issue:** the bare local `python3` has no PyYAML.
- **Fix:** `scripts/check.sh` picks the interpreter of `ansible-playbook`, falls back to `python3` (CI installs ansible via pip, so PyYAML is present).
- **Commit:** aa5b6c1

**3. [Rule 2 - Missing critical] Subscription domain input check in the playbook**
- **Issue:** `xvpn_subscription_domain` is a role default and is not visible in playbook vars; used bare it would be undefined at preflight.
- **Fix:** `| default('')` in `xvpn_preflight_domains` plus a pre_task requiring it while the sub-page is enabled.
- **Commit:** 1cd0cf1

**Total deviations:** 3 auto-fixed. **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- roles/panel/tasks/secrets.yml, scripts/check_no_log.py: present; commits 1cd0cf1 and aa5b6c1 are ancestors of HEAD.
