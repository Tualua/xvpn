---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 02
subsystem: infra
tags: [ansible, panel, traefik, playbook, molecule, qa-05, ci]

requires:
  - phase: 02-panel-za-traefik-s-zaschischennym-vhodom
    provides: edge role with the route interface (plan 02-01)
provides:
  - Role xvpn.remnawave.panel skeleton (domain validation, Panel-domain decoy and :80 redirect routers)
  - playbooks/panel.yml (one command for the Panel host) and playbooks/site.yml
  - Container tier runs the real panel.yml instead of the Phase 1 fixture
  - QA-05 static guard check_acme_ca in scripts/check.sh
affects: [02-03, 02-04, 02-07, 02-08, phase-03-node]

actuals:
  tokens: 6500
  tasks: 2
  commits: 2
plan_head_before: a0e131429dd886f97cd44d6393bd524b73fc8ad1
plan_head_after: 8fed51a12c460a8cbcde489b0fe92407cafc6c4a

tech-stack:
  added: []
  patterns:
    - "Phase playbook sets xvpn_podman_rootless_users and xvpn_common_firewall_ports for its host type"
    - "verify_rootless takes xvpn_verify_quadlet_unit"

key-files:
  created:
    - roles/panel/defaults/main.yml
    - roles/panel/meta/main.yml
    - roles/panel/meta/argument_specs.yml
    - roles/panel/tasks/main.yml
    - roles/panel/tasks/routes.yml
    - roles/panel/templates/panel-routes.yml.j2
    - playbooks/panel.yml
    - playbooks/site.yml
  modified:
    - roles/podman_rootless/defaults/main.yml
    - extensions/molecule/container/converge.yml
    - extensions/molecule/container/molecule.yml
    - extensions/molecule/container/verify.yml
    - extensions/molecule/shared/verify_rootless.yml
    - scripts/check.sh

key-decisions:
  - "The :80 Panel router has observability.accessLogs false so the gate secret path never reaches the access log (T-02-38)"
  - "check_acme_ca reads converge.yml plus vars/*.yml of each scenario that runs the edge, comments stripped"

requirements-completed: [EDGE-01, QA-05]

coverage:
  - id: D1
    description: "One-command panel.yml installs edge and the Panel-domain decoy route; the container tier runs it"
    requirement: EDGE-01
    verification:
      - kind: integration
        ref: "molecule container scenario, CI run for 8fed51a (lint, molecule-container success)"
        status: pass
    human_judgment: false
  - id: D2
    description: "check_acme_ca fails on a production CA pin in an edge converge (mutation-tested) and prints OK otherwise"
    requirement: QA-05
    verification:
      - kind: other
        ref: "bash scripts/check.sh (check_acme_ca: OK); mutation staging->production gave exit 1 with a QA-05 line"
        status: pass
    human_judgment: false
  - id: D3
    description: "Placeholder Panel domain panel.example.com is rejected naming xvpn_panel_domain"
    verification:
      - kind: integration
        ref: "verify.yml negative case panel-placeholder-domain, nine cases total"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-25
status: complete
---

# Phase 2 Plan 02: Panel playbook Summary

**One-command `playbooks/panel.yml` (preflight, common, podman_rootless, edge, panel) with the Panel-domain decoy and unlogged HTTP-redirect routers, run by the container tier, plus the mutation-tested QA-05 `check_acme_ca` guard.**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-11-25
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- Role `panel` validates `xvpn_panel_domain` (lowercase FQDN, no example.* placeholder) and writes `panel.yml` routes via the edge route interface.
- `playbooks/panel.yml` fails early on an unset domain; `site.yml` imports it; the container tier converges only the real playbook, with firewalld holding exactly 80/tcp and 443/tcp.
- `check_acme_ca` in `scripts/check.sh`; mutation check (staging to production in the container converge) exited 1 with `QA-05: extensions/molecule/container/converge.yml does not pin xvpn_edge_acme_ca to staging or custom`, then reverted.
- Nine executed negative cases in the container verify.

## Task Commits

1. **Task 1: Tracer, panel.yml with edge and decoy route** - `cccca1b` (feat); lint and molecule-container success
2. **Task 2: site.yml, fixture removal, check_acme_ca, placeholder case** - `8fed51a` (feat); lint and molecule-container success

## Files Created/Modified
- `roles/panel/**` - routes-only role skeleton
- `playbooks/panel.yml`, `playbooks/site.yml` - Panel host entry points
- `extensions/molecule/container/*`, `extensions/molecule/shared/verify_rootless.yml` - real playbook converge, new verify checks
- `scripts/check.sh` - QA-05 guard

## Decisions Made
- Explicit `accessLogs: false` on the :80 router instead of relying on internal-router behaviour (D-01).
- The VM tier still deploys the fixture; `xvpn_verify_quadlet_unit` defaults to the fixture until Plan 02-03 flips it.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None. `ci_watch.sh` was run unfiltered; its exit status and `gh run list --commit` headSha both confirmed success.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None.

## Next Phase Readiness
- Plan 02-03 can flip the VM tier to panel.yml and the Pebble CA; later plans add routes to `panel-routes.yml.j2` and the subscription domain to the preflight list.

## Self-Check: PASSED

All created files exist; both task commits are ancestors of HEAD; lint and molecule-container concluded success for `8fed51a`.

---
*Phase: 02-panel-za-traefik-s-zaschischennym-vhodom*
*Completed: 2026-11-25*
