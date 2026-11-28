---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 11
subsystem: node-registration
status: complete
tags: [config-profile, reality, node-role, molecule-node-vm, drift]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: remnawave_config_profile module (03-10), node role gate and secret steps (03-07, 03-08), node-vm matrix (03-09)
provides:
  - roles/node/tasks/register.yml (profile step, delegated to the Panel host, gated by xvpn_node_register and xvpn_node_gate_passed)
  - variable xvpn_node_profile_override (recursive merge, lists replaced)
  - node-vm proof of creation, key stability, drift repair, override and BLOCK-rule refusal
affects: [03-13, 03-14, 03-15, 03-16]
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: 0d2fd85
plan_head_after: a808d68c7d34a6bbc1a0a855687e9021759689b0
key-files:
  created:
    - roles/node/tasks/register.yml
    - extensions/molecule/shared/node_panel_read.yml
    - extensions/molecule/shared/verify_node_panel.yml
    - extensions/molecule/node-vm/side_effect.yml
  modified:
    - roles/node/defaults/main.yml
    - roles/node/meta/argument_specs.yml
    - roles/node/tasks/present.yml
    - extensions/molecule/node-vm/converge.yml
    - extensions/molecule/node-vm/verify.yml
    - extensions/molecule/node-vm/molecule.yml
    - plugins/modules/remnawave_config_profile.py
key-decisions:
  - "register.yml is included from present.yml after firewall.yml only when xvpn_node_register and xvpn_node_gate_passed are true (D-15, STEAL-05)"
  - "Drift and override VM cases call the role with tasks_from: register (not the full role) to keep the side_effect fast; the gate and edge are covered by converge"
  - "The drift edit is a raw API PATCH of the stored config with only log.loglevel changed, so the module is not tested against itself"
requirements-completed: [API-01, API-02, API-03]
---

# Phase 3 Plan 11: Node config profile registration Summary

The node role now creates its own Reality config profile in the real Panel after the loopback certificate gate. The profile keeps its keys across re-runs, UI drift is reverted, and operator overrides survive without being able to touch the keys or drop the private-destination BLOCK rule.

## What was built

- `roles/node/tasks/register.yml`: one block delegated to `xvpn_node_panel_host` with `module_defaults` for the remnawave action group; the profile task passes the template merged with `xvpn_node_profile_override`, the managed inbound (tag, shortId count and length, target `xvpn_edge_https_address`, serverNames `[xvpn_node_domain]`) and `required_block_cidrs`. The token and keys never leave the Panel host.
- `present.yml` includes it only after the gate passed (second guard next to the assert of 03-08).
- Converge records sha256(privateKey + shortIds) on the Panel VM; `verify_node_panel.yml` asserts one profile, tag, port 443, reality, target, xver 0, serverNames, key and two 16-hex shortIds, last rule BLOCK and the equal checksum.
- `side_effect.yml` (added to the node-vm sequence after idempotence): loglevel drift repaired with keys and target/xver/serverNames kept; override loglevel applied and idempotent; key-carrying override leaves the checksum unchanged; `profile-override-drops-block` refused naming `xvpn_node_profile_override`; restore run and verify.

## Module hardening (orchestrator note)

Pyright flagged Optional dereferences in `remnawave_config_profile.py`. `inject_keys` now fails with a clear message when a managed tag is absent from the desired config (it was already caught earlier by `enforce_declared`, so this is defence in depth), and the "differs" branch no longer dereferences `stored` through a combined condition. The other reported lines are guarded by earlier `fail_json` paths (`after is None` is checked before use).

## Mutation landing

None needed: the idempotence run of the real Panel reported changed=0 and the module emitted no read-back warning, so `module_utils/remnawave.py`, `fake_panel.py` and `test_config_profile.py` stay untouched.

## Deviations from Plan

None - plan executed as written. Drift/override cases use `tasks_from: register` instead of the whole role, as the plan's wording allows ("a play running include_role xvpn.remnawave.node").

## CI

| Step | Run | Result |
|------|-----|--------|
| lint (HEAD 21966a5) | 46163422013 | success |
| molecule-container (21966a5) | 46163422180 | success |
| molecule-node-vm (21966a5, Task 1) | 46164935780 | success |
| lint (HEAD a808d68) | 46166351777 | success |
| molecule-node-vm (a808d68, Task 2) | 46166546444 | success |

## Known Stubs

None.

## Self-Check: PASSED
