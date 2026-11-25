---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 01
subsystem: infra
tags: [traefik, quadlet, acme, nginx, rootless-podman, molecule, ci]

requires:
  - phase: 01-rootless-fundament-i-testovyy-stend
    provides: podman_rootless quadlet entry point, rw-edge service user, container-tier Molecule scenario
provides:
  - Role xvpn.remnawave.edge (entry points main and route) with rootless Traefik v3.7.20 and decoy nginx units
  - Drop-in route interface (D-16) and shared names xvpn-decoy, xvpn-to-https, le, web/websecure in 00-edge.yml
  - Container-tier checks of the rendered edge and two executed negative cases
  - scripts/ci_watch.sh, dispatch-and-wait helper bound to the HEAD commit
affects: [02-02, 02-03, 02-04, 02-08, phase-03-node]

actuals:
  tokens: 7356
  tasks: 2
  commits: 2
plan_head_before: 6b753ef7ebdb731adfc511507074a404b53cbab7
plan_head_after: 8a2d8ccabf2b813d2d9c46b482d2bc28d6347034

tech-stack:
  added: [traefik v3.7.20, nginx-unprivileged 1.31-alpine]
  patterns:
    - "role_path resolved by set_fact before include_role of podman_rootless"
    - "route files written with setype container_file_t, no restart (file provider watch: true)"
    - "access log drops RequestPath and all headers except User-Agent"

key-files:
  created:
    - roles/edge/defaults/main.yml
    - roles/edge/meta/main.yml
    - roles/edge/meta/argument_specs.yml
    - roles/edge/tasks/main.yml
    - roles/edge/tasks/route.yml
    - roles/edge/templates/traefik.container.j2
    - roles/edge/templates/xvpn-decoy.container.j2
    - roles/edge/templates/traefik.yml.j2
    - roles/edge/templates/00-edge.yml.j2
    - roles/edge/templates/decoy-nginx.conf.j2
    - roles/edge/files/decoy/index.html
    - scripts/ci_watch.sh
  modified:
    - extensions/molecule/container/converge.yml
    - extensions/molecule/container/verify.yml

key-decisions:
  - "Traefik pinned to v3.7.20 (fixes three advisories over the v3.7.19 of STACK.md)"
  - "Container tier always renders against the staging ACME CA; verify asserts the production URL is absent"
  - "Access log drops RequestPath (D-19); the EDGE-03 probe is found by its User-Agent"

patterns-established:
  - "Edge route interface: include_role edge tasks_from route with xvpn_edge_route_* inputs"
  - "Every Phase 2 verify calls scripts/ci_watch.sh so it passes only on the green run of the committed HEAD"

requirements-completed: [EDGE-01, QA-05]

coverage:
  - id: D1
    description: "Edge role renders hardened rootless Traefik unit, static config and 00-edge route file, passing the Quadlet generator dry-run"
    requirement: EDGE-01
    verification:
      - kind: integration
        ref: "molecule container scenario (converge, idempotence, verify), CI run 45572822992"
        status: pass
    human_judgment: false
  - id: D2
    description: "CI points the edge at the staging ACME CA only"
    requirement: QA-05
    verification:
      - kind: integration
        ref: "extensions/molecule/container/verify.yml assert on acme-staging-v02, CI run 45572822992"
        status: pass
    human_judgment: false
  - id: D3
    description: "Invalid edge inputs fail before any change (custom CA without server, bad route name)"
    verification:
      - kind: integration
        ref: "verify.yml negative cases edge-custom-ca-without-server and edge-bad-route-name"
        status: pass
    human_judgment: false
  - id: D4
    description: "ci_watch.sh waits for the exact HEAD run and re-selects cancelled runs"
    verification:
      - kind: other
        ref: "bash -n scripts/ci_watch.sh; used for lint and molecule-container of this plan"
        status: pass
    human_judgment: true
    rationale: "Cancelled-run and dispatch branches were not exercised in this plan; they are first used by later plans"

duration: 45min
completed: 2026-11-25
status: complete
---

# Phase 2 Plan 01: Edge role Summary

**Reusable rootless edge role: Traefik v3.7.20 (file provider, ACME HTTP-01, path-free JSON access log) plus a loopback decoy nginx, a drop-in route interface and a HEAD-bound CI wait helper, proven in the container tier.**

## Performance

- **Duration:** about 45 min
- **Completed:** 2026-11-25T08:10:56Z
- **Tasks:** 2
- **Files modified:** 14 (694 insertions, 1 deletion)

## Accomplishments
- Role `edge` renders `traefik.container` (Network=host, no engine socket, no API/dashboard) and `xvpn-decoy.container` (127.0.0.1:18080 only) through the Phase 1 quadlet entry point; generator dry-run passes.
- `tasks_from: route` writes `<name>.yml` (0600, `container_file_t`, no restart); `00-edge.yml` defines sniStrict TLS options, `xvpn-to-https` and `xvpn-decoy`.
- Container verify asserts the staging `caServer`, the access-log field drops (D-19), file ownership/modes and eight negative cases.
- `scripts/ci_watch.sh` selects the run by commit, re-checks `headSha`/`conclusion`, retries cancelled runs up to 3 times.

## Task Commits

1. **Task 1: Tracer, Traefik unit, static config, route interface, ci_watch** - `cec3f19` (feat)
2. **Task 2: Decoy site, container verify, negative cases** - `8a2d8cc` (feat)

**Plan metadata:** committed with this SUMMARY (docs)

## Files Created/Modified
- `roles/edge/**` - the edge role (defaults, specs, tasks, templates, decoy page)
- `extensions/molecule/container/converge.yml` - edge play (activate false, staging CA)
- `extensions/molecule/container/verify.yml` - rendered-edge asserts, two negative cases
- `scripts/ci_watch.sh` - dispatch-and-wait CI helper

## Decisions Made
- Traefik v3.7.20 instead of the v3.7.19 pin, per RESEARCH advisories.
- `setype: container_file_t` kept alongside the `:Z` mount: `:Z` relabels only at container start.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] YAML parse error in verify.yml**
- **Found during:** Task 2 (check.sh)
- **Issue:** a plain scalar containing `{'User-Agent': 'keep'}` did not parse
- **Fix:** quoted the assertion
- **Files modified:** extensions/molecule/container/verify.yml
- **Verification:** `scripts/check.sh` OK, CI green
- **Committed in:** 8a2d8cc

**2. [Rule 1 - Bug] Acceptance grep for `gh run watch` counted a comment**
- **Found during:** Task 1
- **Issue:** a code comment repeated the phrase, giving 2 matches instead of 1
- **Fix:** reworded the comment
- **Files modified:** scripts/ci_watch.sh
- **Committed in:** cec3f19

---

**Total deviations:** 2 auto-fixed (2 bug). **Impact on plan:** none on scope.

## Issues Encountered
- During the Task 2 CI wait, `ci_watch.sh` hit a transient GitHub API TLS timeout and exited non-zero, but the verify loop piped it through `tail`, which hid the exit code and printed the success marker. The run was then checked directly (`gh run view`): lint and molecule-container (container, preflight) concluded success for `8a2d8cc`. Lesson: never pipe `ci_watch.sh` through a filter; the helper has no retry for transient API errors yet.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None.

## Next Phase Readiness
- The edge role and route interface are ready for Plans 02-02..02-10. Real ACME issuance, the A6 file-provider watch assumption and live log assertions are proven in the VM tier by Plan 02-03.

## Self-Check: PASSED

All created files exist and both task commits are ancestors of HEAD; lint and molecule-container for `8a2d8cc` concluded success.

---
*Phase: 02-panel-za-traefik-s-zaschischennym-vhodom*
*Completed: 2026-11-25*
