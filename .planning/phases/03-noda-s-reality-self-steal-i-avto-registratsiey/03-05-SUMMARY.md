---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 05
subsystem: panel-api-client
status: complete
tags: [ansible-module, module_utils, api-client, unittest, no_log]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: role skeleton and check.sh gates (plans 03-01..03-04)
provides:
  - plugins/module_utils/remnawave.py shared Panel API client (RemnawaveClient, RemnawaveError, normalize, redact, common_argument_spec)
  - plugins/doc_fragments/remnawave.py common options
  - plugins/modules/remnawave_node_secret.py (guard_node_name, secret_key, node_exists)
  - meta/runtime.yml action group remnawave (five module names)
  - tests/unit fake Panel and unittest suite, check.sh line "unit: OK"
  - check_no_log SENSITIVE names for node secrets
affects: [03-06, 03-07, 03-10]
actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: 8004250
plan_head_after: eaae190e2f29767a4ab7020c576693dd0454350a
tech-stack:
  added: []
  patterns: [stdlib unittest with subprocess module runs, in-process fake Panel on ThreadingHTTPServer]
key-files:
  created:
    - plugins/module_utils/remnawave.py
    - plugins/doc_fragments/remnawave.py
    - plugins/modules/remnawave_node_secret.py
    - tests/unit/fake_panel.py
    - tests/unit/test_node_secret.py
    - tests/unit/test_client.py
  modified:
    - meta/runtime.yml
    - scripts/check.sh
    - scripts/check_no_log.py
key-decisions:
  - "Own remnawave_* modules instead of kenyawest.remnawave (confirmed by user 2026-11-28)"
  - "stdlib unittest only; modules tested as subprocesses with ANSIBLE_MODULE_ARGS on stdin"
requirements-completed: [API-01, API-02]
---

# Phase 3 Plan 05: Panel API client and node secret module Summary

The collection now has a tested Panel API client (loopback-only plain http, Bearer plus forwarded headers, version pin to 3.4.x before the first write, token-free errors) and the `remnawave_node_secret` module that fetches a node SECRET_KEY, all run by `check.sh` as `unit: OK`.

## Upstream contract (backend 3.4.11, libs/contract)

- `GET /api/keygen` -> `{response: {secretKey: string}}`; the module reads exactly `response.secretKey`.
- `GET /api/system/metadata` -> `{response: {version, build{time,number}, git{...}}}`; the client reads `response.version` and requires the `3.4.` prefix.
- `GET /api/nodes` -> `{response: [NodesSchema]}` (array); the guard compares each item's `name`.

## What was done

**Task 1 (tracer), commit 3998d27.** Client, doc fragment, module, action group, FakePanel and 7 module tests (normal, check mode, empty token, guard hit, guard miss, check+guard hit, check+guard miss). check.sh runs `unittest discover` and prints `unit: OK`.

**Task 2, commit eaae190.** test_client.py (11 tests): non-loopback http refusal (before the token is read), loopback and https accepted, Bearer/X-Forwarded-For/X-Forwarded-Proto on every request, error text with HTTP status and code and no token, redact/normalize, version pin (3.5.0 refused with no write sent, one metadata GET per client, `panel_version_check: false`, GETs send no metadata request), timeout with a never-answering server. check_no_log gained xvpn_node_secret, secret_key, SECRET_KEY, privateKey, xvpn_node_reality* and a decoy self-test. The client and doc fragment needed no changes (the Task 1 implementation already included the pin and `panel_version_check`).

## CI results (pushed to origin/main)

| Commit | lint |
|--------|------|
| 3998d27 | success, run 46142340263 |
| eaae190 | success, run 46142676146 |

## Deviations from Plan

None. Notes: `tests/__init__.py` and `tests/unit/__init__.py` were added so `unittest discover -t $ROOT` can import `tests.unit.fake_panel`. The version pin and its option were implemented in Task 1 (same file) and covered by Task 2 tests.

## Known pre-existing issues (out of scope)

- `state update-progress` skips: STATE.md milestone is "v3.7.20" with no ROADMAP milestone headings.
- ansible-lint jinja[spacing] warnings in roles/edge/tasks/decoy.yml (pre-existing, warnings only).

## Known Stubs

None.

## Threat Flags

None beyond the plan threat model (T-03-12, T-03-33, T-03-46 mitigated by unit tests).

## Self-Check: PASSED
