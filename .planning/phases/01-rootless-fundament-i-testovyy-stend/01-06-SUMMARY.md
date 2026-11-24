---
phase: 01-rootless-fundament-i-testovyy-stend
plan: 06
subsystem: preflight
tags: [preflight, podman, ports, dns, readme]
requires: [01-05]
provides: [preflight Podman floor, port-owner and DNS A-record checks, named input validation, README Usage for preflight]
affects: [01-07, 01-08]
tech-stack:
  added: []
  patterns: [error aggregation with one final fail, warn-only AAAA in block/rescue, merged accepted-user set]
key-files:
  created:
    - roles/preflight/tasks/check_podman.yml
    - roles/preflight/tasks/check_ports.yml
    - roles/preflight/tasks/check_dns.yml
  modified:
    - roles/preflight/defaults/main.yml
    - roles/preflight/meta/argument_specs.yml
    - roles/preflight/tasks/main.yml
    - README.md
key-decisions:
  - "Regexes in check_ports.yml use character classes and regex_findall, not backslashes or back-references (Jinja string literals process escapes)"
  - "getent ahostsv4/v6 hits are keyed by address and a miss is {domain: null}; resolved sets are built by rejecting null values"
requirements-completed: []
duration: n/a
completed: 2026-11-24
status: complete
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: fe45c99
plan_head_after: f921dc5
---

# Phase 1 Plan 06: Preflight Podman, Ports, DNS Summary

Preflight now validates inputs with named messages and aggregates Podman floor, port-owner and DNS A-record errors (AAAA warn-only) into the single final failure, all read-only; README documents the variables.

## Task results

- 173f1dd `feat(01-06)`: defaults, argument_specs, entry asserts ("Invalid port/domain/xvpn_public_ip/xvpn_public_interface/service user name"), `check_podman.yml`, `check_ports.yml`, `check_dns.yml`, empty-domains warning, warnings printed once before the final fail. Accepted user set is `xvpn_preflight_service_users` UNION `xvpn_podman_rootless_users` names.
- f921dc5 `docs(01-06)`: README `### Preflight checks` (variable table, example invocations, punycode, tags, resolver note).

## Deviations from Plan

None in scope. TDD note: as in Plan 05, behavior cases are executed by the Plan 08 scenario, so no separate RED commit; behavior was checked locally instead.

## Verification

- `bash scripts/check.sh`: `check.sh: OK`; all grep acceptance criteria hold.
- Local behavioral runs (Ubuntu devcontainer, real `ss`/`getent`): foreign listener gives "Port 8081/tcp is in use by python3 (pid N, uid 1000 dev)"; owner in `xvpn_preflight_service_users` passes; owner only in `xvpn_podman_rootless_users` passes (W-5); unresolvable domain and wrong-IP domain give the named errors; matching `xvpn_public_ip` passes; all five invalid inputs fail with their named messages.
- CI on f921dc5: `lint` and `molecule-container` success (the container has no Podman, so the `dnf list` path runs there).

## Deferred verification

- Root-owned listener (missing `uid:` treated as uid 0), the installed-Podman path, empty-domains warning on the full role, and the AAAA rescue path were not exercised locally (devcontainer is Ubuntu: no rpm, no root listener). Plan 08 cases cover them in CI.

## Flagged assumptions

- ss prints no `uid:` field for root-owned sockets; the parser treats a missing uid as 0 (FND-01, edge-probe unresolved).
- `requirements.ready-ids` lists FND-01 and FND-07 as blocked; not marked complete.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
