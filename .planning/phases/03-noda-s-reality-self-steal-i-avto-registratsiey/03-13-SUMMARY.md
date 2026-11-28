---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 13
subsystem: node-registration
status: complete
tags: [node, internal-squad, wait-connected, molecule-node-vm]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: squad and node modules (03-12), profile registration (03-11), SECRET_KEY guard (03-07)
provides:
  - role steps for squads and node registration with the connected wait
  - variables xvpn_node_squads, xvpn_node_country_code, xvpn_node_connect_retries, xvpn_node_connect_delay
  - two-VM proof of connection, union membership, not-connected diagnostics, missing node.env refusal
affects: [03-16]
actuals:
  tokens: 30000
  tasks: 2
  commits: 2
plan_head_before: f65a322cbb840226d1400db15609b54c54d42162
plan_head_after: a2365dc62f7fef24344bb0a52ace9aa65c5de5a9
key-files:
  created:
    - extensions/molecule/shared/node_registration_read.yml
  modified:
    - roles/node/defaults/main.yml
    - roles/node/meta/argument_specs.yml
    - roles/node/tasks/register.yml
    - extensions/molecule/shared/verify_node_panel.yml
    - extensions/molecule/node-vm/converge.yml
    - extensions/molecule/node-vm/side_effect.yml
    - extensions/molecule/node-vm/verify.yml
key-decisions:
  - "Default squad is Default-Squad (confirmed in 03-12); wait budget 30 x 5 s, failure never only a warning"
requirements-completed: [API-02, API-03, API-04]
---

# Phase 3 Plan 13: Node and squad registration Summary

One run of the node role now registers the node in the real Panel, puts its inbound into the declared squads (union only) and waits until the Panel reports it connected; a node that cannot connect fails the run with diagnostics.

## What was done
- register.yml: squad loop, then remnawave_node with wait_connected (skipped in check mode).
- converge records the node uuid; verify_node_panel asserts one node, fields, connected, inbound in Default-Squad, uuid stable.
- side_effect: Foreign squad member, Node not connected (3 x 2 s, message check, recovery), Missing node.env (refusal without keygen, restore, changed=0).
- verify.yml: removed the "Interrupted first run" block.

## CI
- lint 46173475751 success; molecule-container 46173475740 success (HEAD a2365dc).
- molecule-node-vm 46174896749 success on alma10, rocky10, oracle10 (about 18 min wall time; job durations 13-18 min, side_effect included).
- Task 1 commit 683292c: molecule-node-vm run 46171653085 passed converge, idempotence (changed=0) and side_effect, and failed only in verify on the old "Interrupted first run" block, which Task 2 removes (expected by the plan).

## Deviations from Plan
None in behavior. The Task 1 tracer gate was not green on its own for the reason above; Task 2 completed the green run.

## Known Stubs
None.

## Self-Check: PASSED
