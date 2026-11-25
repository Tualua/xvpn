---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 07
subsystem: panel
tags: [traefik, gate, cookie, secret-path, decoy, panel-05, panel-06]
status: complete

requires:
  - phase: 02-panel-za-traefik-s-zaschischennym-vhodom
    provides: edge route interface (02-01/02-02), VM edge verify with Pebble (02-03), secrets with gate values (02-04), bootstrap and API token (02-06)
provides:
  - gate routers xvpn-panel-gate, xvpn-panel-cookie, xvpn-panel-api, middlewares xvpn-panel-gate-setcookie and xvpn-panel-gate-redirect, service xvpn-panel-backend in panel-routes.yml.j2
  - admin entry URL file /var/lib/xvpn/rw-panel/secrets/admin-url (0600, rw-panel); only the path is printed
  - role variables xvpn_panel_gate_cookie_max_age, xvpn_panel_gate_cookie_samesite (Strict|Lax), xvpn_panel_admin_url_file
  - extensions/molecule/shared/verify_gate.yml (+ verify_gate_requests.yml, verify_gate_log.yml) with stable case ids reused by Plan 02-08
  - PANEL-06 and ROADMAP criterion 2 reworded to the decoy (HTTP 200) per D-02
affects: [02-08, 02-09, 02-10, 02-11, phase-05]

actuals:
  tokens: 40000
  tasks: 3
  commits: 3
plan_head_before: 90fd411
plan_head_after: c1e7ce3530fec8c3a29b321200d21506d9c03e7f

key-files:
  created:
    - extensions/molecule/shared/verify_gate.yml
    - extensions/molecule/shared/verify_gate_requests.yml
    - extensions/molecule/shared/verify_gate_log.yml
  modified:
    - roles/panel/defaults/main.yml
    - roles/panel/meta/argument_specs.yml
    - roles/panel/tasks/main.yml
    - roles/panel/tasks/routes.yml
    - roles/panel/templates/panel-routes.yml.j2
    - extensions/molecule/vm/verify.yml
    - extensions/molecule/vm/side_effect.yml
    - extensions/molecule/container/verify.yml
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "Primary variant of D-05 worked in the VM tier on first run (headers customResponseHeaders + redirectRegex on noop@internal); the nginx decoy fallback was not needed"
  - "Cookie attributes are resolved with set_fact in routes.yml before include_role, because panel defaults are not guaranteed visible inside the included edge role"
  - "verify_gate.yml requires verify_edge.yml to have run first (it reuses the controller-side Pebble root file)"
  - "Requests are judged in one included task file (verify_gate_requests.yml) with expect classes decoy/backend/ok200/json/sub/bad400; failures name case ids only"

requirements-completed: [PANEL-05, PANEL-06]
---

# Phase 2 Plan 07: Panel gate Summary

Pure-Traefik cookie/secret-path gate for the Panel domain (routers, headers and redirectRegex only, no plugin and no auth service), the admin-url file, a VM-tier positive and negative matrix with log masking and gate rotation, and the PANEL-06 wording amended to the decoy.

## Tasks

1. **Tracer: gate and admin URL (commit 1919f31).** Gate router (priority 1000, exact `Path`, 302 plus Set-Cookie, access logs off), cookie router (priority 500, anchored `HeaderRegexp`), API router (priority 400, `(?i)^/api(/|$)` minus `(?i)^/+api/+auth(/|$)`), decoy catch-all and the `:80` redirect unchanged. Route file is written with `xvpn_edge_route_sensitive: true`. `verify_gate.yml` covers root-no-cookie, gate-sets-cookie, root-with-cookie, auth-status-with-cookie, auth-status-no-cookie, api-bearer-no-cookie, sub-public-no-cookie, admin-url-file, route-file-mode. Included from `vm/side_effect.yml` (before reboot, with rotation) and `vm/verify.yml` (after reboot).
2. **Negative matrix, log masking, rotation (1919f31, 674b8d9).** Bypass variants (case, double slash, dot segments, `%61`, `..`, bare `/api/auth`, `/login`, `/dashboard`, `%2F` -> 400, `/api/authx` -> backend), anchored cookie cases, http-gate-redirect, log-gate-variants (3 decoy lines found by User-Agent, no RequestPath key), log-no-gate-path, and gate-rotation-old-cookie with the `force: true` re-point of `secrets_checksum_after_first_converge` followed by a `verify_panel.yml` include. Container tier asserts the rendered `panel.yml` holds the new path and neither the old path nor the old cookie value.
3. **Wording (c1e7ce3).** REQUIREMENTS.md PANEL-06 and ROADMAP Phase 2 criterion 2 now say the decoy site (HTTP 200) is served without the cookie.

## Verification

- `bash scripts/check.sh`: `check.sh: OK`.
- CI for HEAD c1e7ce3: lint run 45632220943 success; molecule-container run 45632221216 success; molecule-vm run 45634439077 (dispatched) success, jobs `vm (rocky10)` 12 min 36 s and `vm (alma10)` 14 min 48 s, far below the 90 min checkpoint threshold (the runtime budget rule is satisfied, timeout not touched).
- Observed status of `sub-public-no-cookie`: the case passes (neither 400 nor 5xx, body differs from the decoy and from `404 page not found`); the exact status is printed by the case in the VM log and not re-read here.
- The human check (browser login through the admin URL on a real host) is collected in the end-of-phase UAT (`human_verify_mode: end-of-phase`).

## Deviations from Plan

**1. [Rule 3 - Blocking] Rotation tasks inlined into verify_gate.yml.** Found during: Task 2. The plan acceptance greps look for the rotation case, the checksum re-point and `force: true` in `verify_gate.yml`, so the rotation block lives there (guarded by `xvpn_verify_gate_rotation`) instead of a separate file. The rotation scan message reads "the rotated or the old gate path is traced in the Traefik log" so the single `gate secret path found in the Traefik log` message stays unique. Commit 1919f31.

**2. [Rule 1 - Bug] ansible-lint jinja[spacing] and line-length on the verdict template.** Replaced the long `elif` chain with a `verdicts` mapping. Commit 1919f31.

**3. Process note.** `ci_watch.sh molecule-vm --dispatch` hit a transient GitHub API HTTP 500 while the dispatched run was still in progress; the run was watched to completion with `gh run watch 45634439077` instead of dispatching again.

**Total deviations:** 3 (1 blocking, 1 lint, 1 process). **Impact:** none on behaviour.

## Known Stubs

None.

## Threat Flags

None: no new surface beyond the plan threat model (T-02-20..T-02-22 mitigated and tested).

## Self-Check: PASSED

Files verified present: panel-routes.yml.j2, verify_gate.yml, verify_gate_requests.yml, verify_gate_log.yml. Commits 1919f31, 674b8d9, c1e7ce3 are ancestors of HEAD; lint, molecule-container and molecule-vm green for HEAD.
