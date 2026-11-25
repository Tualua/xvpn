---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 06
subsystem: panel
tags: [bootstrap, remnawave-api, api-token, rootless, panel-03, panel-04, doc-04]
status: complete

requires:
  - phase: 02-panel-za-traefik-s-zaschischennym-vhodom
    provides: Panel stack on 127.0.0.1:3000 (02-05), generate-once secrets with admin_password (02-04), VM harness (02-03)
provides:
  - roles/panel/tasks/bootstrap.yml loopback state machine (auth status, register or login, token validate or create)
  - 0600 token file /var/lib/xvpn/rw-panel/secrets/api-token (D-09 interface, owner rw-panel)
  - run-scoped no_log facts xvpn_panel_admin_jwt and xvpn_panel_api_token for Plan 02-10
  - role variables xvpn_panel_admin_username, xvpn_panel_api_token_name, xvpn_panel_api_token_days, xvpn_panel_bootstrap_retries, xvpn_panel_api_token_file and internal xvpn_panel_api_token_probe_route
  - VM state file token_checksum_after_first_converge and a Token recovery block in side_effect.yml
affects: [02-07, 02-09, 02-10, phase-03]

actuals:
  tokens: 45000
  tasks: 2
  commits: 3
plan_head_before: f1a37b1d5d9743df662a199b0917ba3c89484c18
plan_head_after: 947829eb9bcd27e04f7b4002b0735b05c80193d7

key-files:
  created:
    - roles/panel/tasks/bootstrap.yml
  modified:
    - roles/panel/defaults/main.yml
    - roles/panel/meta/argument_specs.yml
    - roles/panel/tasks/main.yml
    - extensions/molecule/vm/converge.yml
    - extensions/molecule/vm/side_effect.yml
    - extensions/molecule/shared/verify_panel.yml

key-decisions:
  - "Admin JWT requests carry X-Remnawave-Client-Type: browser; without it backend 3.4.11 answers 403 on /api/tokens list, create and delete"
  - "Register runs only when isRegisterAllowed is true and isLoginAllowed is false; if both are true the role logs in, so a second admin is never created"
  - "The login failure message names the secrets key through the internal variable xvpn_panel_bootstrap_password_key so the fail task needs no no_log"
  - "verify_panel.yml reads the token checksum file at verify time (xvpn_verify_token_checksum_file); side_effect re-points it after the deliberate recovery"

requirements-completed: [PANEL-03, PANEL-04, DOC-04]
---

# Phase 2 Plan 06: Panel bootstrap Summary

Loopback bootstrap that registers the first admin, creates a long-lived automation API token as a 0600 file on the Panel host, and logs in only on re-runs; a lost token is recreated with the old one revoked.

## Contract confirmed from remnawave/backend 3.4.11 (libs/contract and src)

- Register body: `username` is a plain string with no constraint, so `rwoperator` is valid; password needs >= 24 chars with upper, lower and digit (already enforced by the Plan 02-04 format check).
- Register and login answer `{response: {accessToken}}`; the roles accept 200 and 201.
- Status: `{response: {isLoginAllowed, isRegisterAllowed, ...}}`.
- Token list: `GET /api/tokens` returns `{response: {tokens: [{uuid, name, ...}]}}`; delete is `DELETE /api/tokens/<uuid>` (HTTP 204, cache entry `api:<uuid>` is cleared on delete); create is `POST /api/tokens {name (2-30 chars), expiresInDays >= 1, scopes}` returning `{response: {..., token}}`.
- Nodes list route is `GET /api/nodes`; accepted with an API token (role API).
- Admin JWT requests additionally require `X-Remnawave-Client-Type: browser` (request-auth service); API-token requests do not.

## Tasks

1. Task 1 (tracer): bootstrap state machine, ordering before the Panel route file, variables and argument_specs, VM converge records the token checksum, verify_panel asserts closed registration, 0600 token file, Bearer 200 and unchanged checksum. Commits 9a5fe8e, 7558b69 (fix).
2. Task 2 (tdd): Token recovery block in side_effect.yml (token file deleted, role re-run, new content with 0600 rw-panel, new token 200, old token 401 or 403, exactly one token named xvpn-automation, converged re-run, checksum file re-pointed, divergent admin password fails naming admin_password, stored password still logs in). Commit 947829e.

## Verification

- `bash scripts/check.sh`: `check.sh: OK` including check_no_log over bootstrap.yml.
- Acceptance greps: bootstrap.yml before routes.yml in main.yml; `X-Forwarded-Proto: https` 7 (>= 4); `no_log: true` 12 (>= 5); `delegate_to|fetch:|cacheable` 0; `isRegisterAllowed` 3; `not a password problem` 1; probe route variable 1.
- CI for HEAD 947829e: lint success, molecule-container success, dispatched molecule-vm run 45627885748 success on rocky10 and alma10 (converge registers the admin, idempotence logs in with changed=0, token valid and unchanged across idempotence and reboot, recovery and revocation proven).
- molecule-vm job durations: rocky10 11 m 20 s, alma10 13 m 52 s (well under the 90-minute threshold, timeout 120). Token recovery block: 75 s on rocky10, 91 s on alma10.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Admin JWT requests were answered 403 by the backend**
- **Found during:** Task 1 first molecule-vm run (run 45625448939, list API tokens)
- **Issue:** backend 3.4.11 `verifyAdmin` requires `X-Remnawave-Client-Type: browser` for admin JWT requests; the plan's contract notes did not list it.
- **Fix:** added the header to the token list, delete and create requests in bootstrap.yml and to the token list request in side_effect.yml.
- **Files modified:** roles/panel/tasks/bootstrap.yml, extensions/molecule/vm/side_effect.yml
- **Commit:** 7558b69 (bootstrap.yml; the side_effect.yml part is in 947829e)

**2. [Rule 1 - Bug] Line-length lint on two bootstrap messages**
- Fixed before the first commit by folding the long lines (no separate commit).

**Total deviations:** 2 auto-fixed (2 bug). **Impact:** none on scope; Task 1 needed a second CI cycle.

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None. The only new surface is loopback HTTP calls from Ansible on the Panel host; the token never leaves the host (no controller delegation, fetch or fact caching) and is printed nowhere.

## Self-Check: PASSED

- FOUND: roles/panel/tasks/bootstrap.yml
- FOUND commits: 9a5fe8e, 7558b69, 947829e
