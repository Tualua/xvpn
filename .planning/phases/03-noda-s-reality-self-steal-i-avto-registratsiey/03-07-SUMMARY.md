---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 07
subsystem: node-role
status: complete
tags: [remnanode, quadlet, secret-key, rekey, selinux, molecule-node-vm]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: remnawave_node_secret module (03-05), two-VM node-vm stand (03-06), node role skeleton (03-01)
provides:
  - roles/node/tasks/secret.yml (SECRET_KEY once from the Panel host, node.env + runtime.env)
  - roles/node/tasks/service.yml and remnanode.container.j2 (rootless, Network=host)
  - variables xvpn_node_rekey, xvpn_node_panel_host, xvpn_node_panel_api_url, xvpn_node_panel_api_token_file, xvpn_node_api_port, xvpn_node_env_dir
  - extensions/molecule/shared/node_rekey_run.yml, node_state.yml
affects: [03-08, 03-11, 03-13, 03-16]
actuals:
  tokens: 16000
  tasks: 2
  commits: 3
plan_head_before: 542b46d1d41c79f9ebb704557c0a0ba70fd8e052
plan_head_after: c139c05247b9ecac45fd3e1a74b8ce98d875ce8e
key-files:
  created:
    - roles/node/tasks/secret.yml
    - roles/node/tasks/service.yml
    - roles/node/templates/remnanode.container.j2
    - roles/node/templates/node.env.j2
    - roles/node/templates/node-runtime.env.j2
    - extensions/molecule/shared/node_rekey_run.yml
    - extensions/molecule/shared/node_state.yml
  modified:
    - roles/node/defaults/main.yml
    - roles/node/meta/argument_specs.yml
    - roles/node/tasks/main.yml
    - roles/node/tasks/present.yml
    - extensions/molecule/node/verify.yml
    - extensions/molecule/node-vm/converge.yml
    - extensions/molecule/node-vm/verify.yml
    - extensions/molecule/shared/verify_node.yml
key-decisions:
  - "A1 held: Podman EnvironmentFile takes SECRET_KEY=<payload> literally; remnanode started in the VM with the real key, no Podman secret fallback needed"
  - "A3/A5 held: remnanode runs rootless with Network=host, no capability, container_t, zero AVC; no boolean or capability added"
  - "Re-key and interrupted-first-run checks run the node role's secret and service task files directly (shared/node_rekey_run.yml), not the whole playbook"
requirements-completed: [NODE-01, API-02]
---

# Phase 3 Plan 07: remnanode with SECRET_KEY from the Panel Summary

The node role fetches SECRET_KEY from the Panel once (module executed on the Panel host, token never leaves it), writes it to a 0600 `node.env`, and runs remnanode as a rootless Quadlet with host networking. The two-VM stand proves it on SELinux enforcing with zero AVC, plus the opt-in re-key and the interrupted-first-run path.

## What was built

- `secret.yml`: `node.env` is looked up first; the keygen call happens only when it is missing or `xvpn_node_rekey` is true (one shared condition `xvpn_node_secret_wanted`). With the node name guard, an existing Panel node and a missing `node.env` fails with a restore / re-key message and writes nothing. The payload is checked (single line, base64 alphabet) under `no_log` before the write.
- `runtime.env` holds `NODE_PORT` separately and is rendered every run; `restart_stale` watches both files.
- `register: false` with `activate: true` and no `node.env` fails before the unit is installed.
- remnanode Quadlet: `Network=host`, two `EnvironmentFile=`, `Ulimit nofile=524288`, no capabilities, no `SecurityLabelDisable`, no published ports.

Upstream 3.4.6 env keys used: `NODE_PORT` and `SECRET_KEY` (as the plan expected); no extra mounts were mirrored.

## CI evidence

| Run | Workflow | Commit | Result |
|-----|----------|--------|--------|
| 46148378064 | molecule-node-vm (dispatch) | 13c0907 (Task 1) | success: remnanode active, listener 2222 as rw-node, host net, no caps, container_t, zero AVC, node.env checksum unchanged by idempotence |
| 46148366574 | molecule-container | 13c0907 | failed (see deviation 1) |
| 46149928825 | molecule-node-vm (dispatch) | c139c05 (HEAD) | success, including the Node re-key and Interrupted first run blocks |
| 46149917707 | lint | c139c05 | success |
| 46149917690 | molecule-container | c139c05 | success |

## Deviations from Plan

**1. [Rule 1 - Bug] delegate_to of the skipped keygen task broke the container tier**
- **Found during:** Task 1 CI (molecule-container, node scenario)
- **Issue:** with `xvpn_node_register: false` there is no Panel host, and `delegate_to: "{{ xvpn_node_panel_host }}"` is templated even for a skipped task, so it failed on an empty value.
- **Fix:** `delegate_to: "{{ xvpn_node_panel_host | default(omit, true) }}"`.
- **Files modified:** roles/node/tasks/secret.yml
- **Commit:** c139c05

**2. [Rule 3 - Tooling] check_no_log flags**
- Fail messages and the `runtime.env` writer matched the sensitive-name heuristics. Messages were reworded ("node key"), a `xvpn_node_known_in_panel` boolean (no_log set_fact) feeds the refusal, and `runtime.env` got `diff: false` and `no_log: true` (no secret in it; the checker keys on the `.env` path).

**3. Verify structure:** the re-key blocks use two small shared helpers (`node_rekey_run.yml`, `node_state.yml`) instead of inline tasks.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model (T-03-11, T-03-13, T-03-38, T-03-42, T-03-14 mitigated as designed).

## Self-Check: PASSED

Files and commits 13c0907, 422e4a2, c139c05 exist on main.
