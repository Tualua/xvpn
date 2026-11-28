---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 02
subsystem: testing
tags: [traefik, xray, reality, self-steal, pebble, ci-gate]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: node-selfsteal.yml.j2 route and edge decoy templates (plan 03-01)
provides:
  - scripts/selfsteal/run.sh nine-case self-steal regression gate on production templates
  - scripts/selfsteal/render.yml renderer of edge and node templates
  - selfsteal workflow (push, PR, dispatch with break=sni-strict)
affects: [03-03, 03-04, 03-08, 03-10, 03-15]
actuals:
  tokens: 16000
  tasks: 2
  commits: 2
plan_head_before: c8de1fce63847f393efc15b5f4ebebfbbc5f1d4b
plan_head_after: 796482614c8c8627ee308604324fcb097509c3b6
tech-stack:
  added: [Xray-core v26.11.9 (CI only, sha256 pinned), actions/cache v6.1.0 (sha pinned)]
  patterns: [render production templates from role paths, sha256-verified cache, runtime-generated keys]
key-files:
  created:
    - scripts/selfsteal/run.sh
    - scripts/selfsteal/render.yml
    - .github/workflows/selfsteal.yml
  modified:
    - scripts/check.sh
key-decisions:
  - "Traefik stays as self-steal terminator: all nine cases pass on v3.7.20, no D-14 escalation needed"
requirements-completed: [STEAL-01, STEAL-03, NODE-03]
status: complete
---

# Phase 3 Plan 02: Self-steal regression gate Summary

Native CI gate that renders the production edge and node templates and proves, with a real Xray Reality plus Vision client, that Traefik behind Reality serves a verified decoy for the node SNI, leaks nothing for foreign or absent SNI, and keeps private destinations blocked.

## Results

- Task 1 (tracer, 167ba1d): valid-sni and client-e2e. CI: lint run 46135969887 success, selfsteal run 46135969885 success, `selfsteal: OK (2 cases)`.
- Task 2 (7964826): full matrix. CI: lint run 46136297320 success, selfsteal run 46136297341 success, `selfsteal: OK (9 cases)` (valid-sni, direct-loopback, foreign-sni, no-sni, client-e2e, client-private-blocked, traefik-down, xver1-mismatch, xver1-proxyprotocol).
- Deliberate-break proof: `gh workflow run selfsteal -f break=sni-strict`, run 46136473017 concluded `failure` with `FAIL foreign-sni` (also `FAIL no-sni` and `FAIL direct-loopback`).
- `actions/cache` v6.1.0 sha 55cc8345863c7cc4c66a329aec7e433d2d1c52a9 re-checked via the GitHub API.

## Deviations from Plan

None - plan executed as written. The deliberate break additionally fails direct-loopback and no-sni, which is consistent with removing sniStrict.

## Known Stubs

None.

## Self-Check: PASSED
