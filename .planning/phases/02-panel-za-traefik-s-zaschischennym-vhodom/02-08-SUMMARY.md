---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 08
subsystem: ci
tags: [gate, traefik, pebble, ci, panel-06, qa-05]
status: complete

requires:
  - phase: 02-panel-za-traefik-s-zaschischennym-vhodom
    provides: gate routers and verify_gate case ids (02-07), check_acme_ca (02-02), Pebble pins (02-03), ci_watch.sh (02-01)
provides:
  - scripts/gate/render.yml renders the production traefik.yml.j2, 00-edge.yml.j2 and panel-routes.yml.j2 with non-secret fixtures
  - scripts/gate/run.sh runs the pinned Traefik image against sha256-verified Pebble and loopback stubs and executes the gate matrix by case id
  - .github/workflows/gate.yml (push, pull_request, workflow_dispatch input break)
  - check.sh syntax-checks scripts/gate/render.yml and check_acme_ca scans scripts/gate/*.yml
affects: [02-09, 02-11]

actuals:
  tokens: 45000
  tasks: 2
  commits: 5
plan_head_before: 32ea3b7f881cd0c2359353c5072e94fc182e0bb4
plan_head_after: 725314ec0cca141e3892352a444b3cb5e2548c16

key-files:
  created:
    - scripts/gate/render.yml
    - scripts/gate/run.sh
    - .github/workflows/gate.yml
  modified:
    - scripts/check.sh

key-decisions:
  - "Fixture values are read by run.sh from the marked lines of render.yml, never re-typed"
  - "Random test tokens come from python3 secrets (a tr|head pipe dies with SIGPIPE under pipefail)"

requirements-completed: [PANEL-06, QA-05]
duration: 40min
completed: 2026-11-25
---

# Phase 2 Plan 08: Gate regression in CI Summary

The admin gate is re-proven on every push: the production edge and panel templates are rendered, the pinned Traefik v3.7.20 gets a Pebble certificate over HTTP-01 on the runner, and the verify_gate case ids run against stub backends.

## Tasks

1. Tracer (0e885bb, fixes cb09895, bbd9339): render.yml, run.sh with port pre-flight, sha256-verified Pebble, stubs, the XVPN_GATE_BREAK hook and the cases root-no-cookie, gate-sets-cookie, root-with-cookie; gate.yml. Green on the runner.
2. Full matrix (b85a38c, fix 725314e): remaining verify_gate cases (including sub-public-no-cookie, encoding and cookie negatives, sni-strict, http-gate-redirect, log-gate-variants, log-no-gate-path) and the check.sh changes.

## Evidence

- Gate for HEAD 725314e: success, prints `gate-matrix: OK`; lint success.
- Deliberate-break run (`gh workflow run gate --ref main -f break=auth-regex`): https://github.com/Tualua/xvpn/actions/runs/45642014816 failed with `FAIL auth-uppercase` and `FAIL api-uppercase` (case-sensitive auth exclusion lets the upper-case auth paths through to the backend). No throwaway commit. Podman is not installed in the executor shell, so the local route was not available.
- QA-05 mutation: the production directory as `xvpn_edge_acme_ca_server` in scripts/gate/render.yml makes check.sh print `QA-05: scripts/gate/render.yml points xvpn_edge_acme_ca_server at the production Let's Encrypt directory` and fail; reverted.

## Threats

T-02-24 (Pebble sha256, pinned image and action SHAs), T-02-34 (negative matrix on every push plus the break proof), T-02-41 (render.yml pins the Pebble URL, check_acme_ca scans scripts/gate/*.yml, mutation-tested) are mitigated.

## Deviations from Plan

**1. [Rule 1 - Bug] Unpacked Pebble binaries lacked the execute bit** - Found during: Task 1 CI (FAIL pebble-root). Fix: chmod +x after tar; also added Pebble log diagnostics on that failure. Commits bbd9339, cb09895.

**2. [Rule 1 - Bug] SIGPIPE from `tr | head` under pipefail killed the matrix** - Found during: Task 2 CI. Fix: `rand_alnum` helper via python3. Commit 725314e.

**3. [Rule 3 - Blocking] Acceptance counts** - the header comment and the dispatch condition repeated `gate-matrix: OK` / `workflow_dispatch`; reworded so the counts equal 1.

**Total deviations:** 3 auto-fixed. **Impact:** none on scope.

## Known Stubs

None. The python stub servers in run.sh are intentional test doubles.

## Self-Check: PASSED

scripts/gate/render.yml, scripts/gate/run.sh, .github/workflows/gate.yml exist; commits 0e885bb, cb09895, bbd9339, b85a38c, 725314e are on main; gate and lint green for HEAD.
