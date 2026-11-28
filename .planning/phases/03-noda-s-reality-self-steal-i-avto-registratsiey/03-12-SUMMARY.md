---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 12
subsystem: panel-api-modules
status: complete
tags: [internal-squad, node, wait-connected, fake-panel, unit-tests]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: API client and fake Panel (03-05), config profile module (03-10), profile registration (03-11)
provides:
  - module xvpn.remnawave.remnawave_internal_squad (union-only membership)
  - module xvpn.remnawave.remnawave_node (reconcile, address guard, bounded wait, async delete)
  - module_utils resolve_profile(client, name)
affects: [03-13, 03-16]
actuals:
  tokens: 16000
  tasks: 2
  commits: 1
plan_head_before: a2632df6c561ea774415329bb6f3aacc1dcc570e
plan_head_after: 145b8315463b52a5c774833b587e80c957e92582
key-files:
  created:
    - plugins/modules/remnawave_internal_squad.py
    - plugins/modules/remnawave_node.py
    - tests/unit/test_internal_squad.py
    - tests/unit/test_node.py
  modified:
    - plugins/module_utils/remnawave.py
    - tests/unit/fake_panel.py
key-decisions:
  - "Reserved seeded squad name in Panel 3.4.11 is Default-Squad (uuid 00000000-0000-0000-0000-000000000000, prisma/seed/seeders/7_seed-default-internal-squad.ts); Plan 03-13 uses it as the default of xvpn_node_squads. The RESEARCH Pitfall 6 assumption is confirmed."
  - "Node address guard compares the Panel address field of other nodes as a stripped, case-insensitive string; DNS is never resolved"
  - "Squad create rejects the reserved name and respects create: false; absent on a missing squad is a no-op"
requirements-completed: [API-01, API-02, API-03, API-04]
---

# Phase 3 Plan 12: Squad and node modules Summary

Two Panel modules with a unit contract against the fake Panel: squad membership is union-only (foreign inbounds are never removed) and the node is created once, never duplicated, and waited on with a bounded, diagnosable timeout.

## Upstream contract read (tag 3.4.11)

- Node create body: `name` 3..30, `address` (min 2, unique, error A034), `port` optional, `countryCode` max 2 default XX, `configProfile {activeConfigProfileUuid, activeInbounds[uuid]}`. Update PATCH `{uuid, ...}` with the same optional fields. `GET /api/nodes` returns `response[]`; `GET /api/nodes/{uuid}` returns `response` node with `isConnected`, `isConnecting`, `isDisabled`, `lastStatusMessage`, and `configProfile.activeInbounds` as objects with `uuid`. DELETE only queues (`isNeedToBeDeleted`).
- Squads: list `response.internalSquads[]` with `inbounds[]` objects; create `{name 2..30, inbounds[uuid]}`; PATCH `{uuid, name?, inbounds?}` replaces the whole set.
- Seeded squad: `Default-Squad`.

## What was built

- `remnawave_internal_squad`: PATCH with the sorted union of current and requested inbound uuids only when it adds something; `absent` removes only the listed ones; missing non-default squad is created, missing `Default-Squad` fails "does not exist"; check mode sends no write and treats a not-yet-existing profile as an addition; diff of inbound tags.
- `remnawave_node`: key `name`; one POST on create, PATCH only with changed fields; another node with the same address string fails naming `xvpn_node_address` before any POST; `wait_connected` polls `GET /api/nodes/{uuid}` `wait_retries` times with `wait_delay` (never sets changed, skipped in check mode); the timeout message carries the pinned substrings `not connected after`, `lastStatusMessage=`, `xvpn_node_panel_sources`, `remnanode.service`, `xvpn_node_rekey` and never suggests deleting node.env; `absent` DELETEs and polls the list until the node is gone.
- Fake Panel: nodes (per-test `connect_after`, status message, async delete via `delete_polls`) and internal-squads with full-replace PATCH.
- 14 new unit tests (9 node, 5 squad); whole unit suite (55 tests) passes inside `check.sh`.

## Deviations from Plan

None in behavior. Both tasks were implemented and verified together, so the modules, fake Panel and complete unit contract landed in one commit (`145b831`) instead of one per task. The fake Panel's node POST ignores bodies without `configProfile` so the pre-existing client test that posts `{"a": 1}` keeps working.

## CI

- lint: run 46168868379, success for 145b831.

## Known Stubs

None.

## Self-Check: PASSED

- plugins/modules/remnawave_node.py, plugins/modules/remnawave_internal_squad.py, tests/unit/test_node.py, tests/unit/test_internal_squad.py exist.
- Commit 145b831 is on origin/main.
