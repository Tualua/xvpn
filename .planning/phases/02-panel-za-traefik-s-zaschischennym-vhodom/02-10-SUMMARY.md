---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 10
subsystem: panel
tags: [subscription-page, traefik, quadlet, sub-01, sub-02, molecule-vm]
requires:
  - phase: 02-06
    provides: bootstrap API token file and the xvpn_panel_api_token fact
  - phase: 02-07
    provides: Panel gate (the subscription domain stays outside it)
provides:
  - remnawave-subscription-page 8.0.1 as a rw-panel Quadlet unit on 127.0.0.1:3010
  - subpage.env (0600) rendered from the bootstrap token, unit restarted on a token change
  - subscription route file on the subscription domain (own ACME certificate, no cookie rule)
  - verify_subpage.yml with probe A, probe B and the expectation switch, plus the wrong-token negative control
affects: [02-11, 03, 05]
tech-stack:
  added: [docker.io/remnawave/subscription-page:8.0.1]
  patterns: [authenticated end-to-end probe with a negative control of a fixed outcome]
key-files:
  created:
    - roles/panel/tasks/subpage.yml
    - roles/panel/templates/remnawave-subscription-page.container.j2
    - roles/panel/templates/subpage.env.j2
    - roles/panel/templates/subscription-routes.yml.j2
    - extensions/molecule/shared/verify_subpage.yml
  modified:
    - roles/panel/defaults/main.yml
    - roles/panel/meta/argument_specs.yml
    - roles/panel/tasks/main.yml
    - extensions/molecule/vm/verify.yml
    - extensions/molecule/vm/side_effect.yml
key-decisions:
  - "Sub-page 8.0.1 + backend 3.4.11 (A8) confirmed compatible: the page logs '[OK] Connected to Remnawave v3.4.11' at start-up"
  - "Healthcheck uses curl against /internal/health: the image ships curl, the unit became healthy (A13)"
  - "No separate sub-page token in v1 (T-02-26 accepted)"
requirements-completed: [SUB-01, SUB-02]
status: complete
actuals:
  tokens: 40000
  tasks: 2
  commits: 3
plan_head_before: 685d1fbe797224117f0fda61469e7a5f46204ba5
plan_head_after: 5c2ac8ac7d0baf73478e0b07d15a7f07609ce225
duration: 130min
completed: 2026-11-25
---

# Phase 2 Plan 10: Subscription page Summary

**Subscription page 8.0.1 on its own domain over HTTPS, authenticated to the Panel with the bootstrap token, proven by an authenticated lookup of a probe user and by a wrong-token control that fails with HTTP 502.**

## Accomplishments

- `subpage.yml` runs after the bootstrap: token from the bootstrap fact or the token file, `subpage.env` 0600 rw-panel with `no_log`/`diff: false`, Quadlet unit via the shared deployment interface, restart only when the env file changed, route file `subscription.yml` (routers `xvpn-sub`, `xvpn-sub-http`, service `xvpn-sub-page`; no cookie rule).
- Unit: `Requires=/After=remnawave.service`, `Network=remnawave.network`, `PublishPort=127.0.0.1:3010:3010` only, `Notify=healthy`, `Restart=always`, no `AutoUpdate=`.
- `verify_subpage.yml`: step 0 start-up diagnostic (A8), static checks (env mode, loopback-only listener, TLS chain and routing), probe user fixture, probe A (token held by the container accepted by the Panel, 200), probe B (Mozilla request on `https://<sub>/<shortUuid>` gives 200 with a `data-panel` JSON with isFound, probe username and shortUuid). `xvpn_verify_subpage_expect_auth: false` additionally asserts probe A not 200, probe B 502, no `data-panel`.
- `side_effect.yml`: default verify after the gate verify, then block "Sub-page wrong-token control" (random JWT-shaped token, restart, expectation false, role re-run, InvocationID changed, `subpage.env` sha256 equal to the pre-control value, default verify again).
- CI for HEAD 5c2ac8a: lint, molecule-container, dispatched molecule-vm (run 45659433621) all success.

## Recorded contract facts

- 3.4.11 routes used by the fixture: `GET /api/users/by-username/<username>` and `POST /api/users` with `username` (3-36, `[A-Za-z0-9_-]`) and `expireAt` (ISO datetime, required); response `response.shortUuid`.
- Healthcheck command actually used: `curl -fsS -o /dev/null --max-time 2 http://127.0.0.1:3010/internal/health`.
- Rejected-token answer through Traefik: HTTP 502 and no `data-panel` attribute (asserted in the negative control, passed). A non-browser request for an unknown id on the page also returns 502 (the page closes the socket), which is why the unknown-path check only judges chain and routing.
- Start-up line: `[AxiosService] [OK] Connected to Remnawave v3.4.11`.
- molecule-vm durations (final run): rocky10 15 min, alma10 19 min (well below the 90 min budget).

## Deviations from Plan

**1. [Rule 1 - Bug] Unknown-path check expected a non-5xx answer**
- **Found during:** Task 1 (first VM run)
- **Issue:** the page answers a non-browser request for an unknown id with a closed socket, so Traefik returns 502.
- **Fix:** the check now asserts TLS chain, routing and body differing from the decoy and from `404 page not found`; the authenticated behaviour is probe B.
- **Files modified:** extensions/molecule/shared/verify_subpage.yml
- **Commit:** 7c22738

**2. [Rule 3 - Blocking] Placement of the post-recovery verify**
- **Found during:** Task 2
- **Issue:** the plan puts the default verify right after the token recovery block, but the Pebble root (verify_edge.yml) is only available later in side_effect.yml.
- **Fix:** the default verify runs after the gate verify; it still proves the page holds the recovered token.
- **Commit:** 5c2ac8a

**3. [Rule 2] `no_log` on the token-file stat**
- check_no_log.py flags any task naming the token fact; added `no_log: true` to the stat task.

**4. [Scope] `when: xvpn_panel_subscription_enabled` on the include in main.yml** was added already here (the toggle semantics and README remain in 02-11).

**Total deviations:** 3 auto-fixed, 1 note. **Impact:** none on the plan goal.

## Known Stubs

None.

## Threat Flags

None beyond the plan threat model.

## Self-Check: PASSED

Files exist, commits 081b001, 7c22738, 5c2ac8a are ancestors of HEAD, CI green for HEAD.
