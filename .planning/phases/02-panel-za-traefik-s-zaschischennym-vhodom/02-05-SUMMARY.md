---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 05
subsystem: panel
tags: [quadlet, postgres, valkey, remnawave-backend, rootless, panel-01, panel-02]
status: complete

requires:
  - phase: 02-panel-za-traefik-s-zaschischennym-vhodom
    provides: generate-once panel secrets (02-04), edge and VM tier harness (02-02, 02-03)
provides:
  - rw-panel Quadlet units remnawave.network, remnawave-db.volume (remnawave-db-data), remnawave-valkey.volume (remnawave-valkey-socket), remnawave-db, remnawave-redis, remnawave
  - 0600 env files postgres.env and backend.env in /var/lib/xvpn/rw-panel/env, rendered no_log with diff false
  - loopback-only backend API on 127.0.0.1:3000, nothing else published
  - extensions/molecule/shared/verify_panel.yml with the xvpn_verify_secrets_checksum_file contract
  - VM state files invocation_backend_after_first_converge and secrets_checksum_after_first_converge
affects: [02-06, 02-07, 02-08, 02-09, 02-10, phase-03, phase-05]

actuals:
  tokens: 60000
  tasks: 2
  commits: 7
plan_head_before: 91fa93254b4679ee0a68672bd98cfd939a46c043
plan_head_after: 8656cb2fa7988290df3103a6d3317e031a56ff2e

key-files:
  created:
    - roles/panel/tasks/stack.yml
    - roles/panel/templates/remnawave.network.j2
    - roles/panel/templates/remnawave-db.volume.j2
    - roles/panel/templates/remnawave-valkey.volume.j2
    - roles/panel/templates/remnawave-db.container.j2
    - roles/panel/templates/remnawave-redis.container.j2
    - roles/panel/templates/remnawave.container.j2
    - roles/panel/templates/postgres.env.j2
    - roles/panel/templates/backend.env.j2
    - extensions/molecule/shared/verify_panel.yml
  modified:
    - roles/panel/tasks/main.yml
    - extensions/molecule/vm/converge.yml
    - extensions/molecule/vm/verify.yml
    - extensions/molecule/vm/side_effect.yml

key-decisions:
  - "Ulimit=nofile lowered from 1048576 to 524288 (the systemd user manager hard limit): the higher value made remnawave-db fail to start rootless (flagged assumption confirmed)"
  - "Valkey Exec= has no empty quoted word: Quadlet truncates the command at it, so valkey ran with the default config (TCP 6379, no socket); a bare --save followed by another option disables snapshots, verified by config get save"
  - "Unit start failures are reported with the system journal of the service uid and podman logs through a rescue block in stack.yml, so a VM run shows the cause"
  - "getent_passwd is one fact that each lookup replaces: the VM harness keeps uids in separate facts and verify_panel reads the uid with id -u"
  - "No User=/Group= on the Valkey volume was needed (A12): valkey created the socket in the named volume as is"

requirements-completed: [PANEL-01, PANEL-02]

duration: 6h wall clock (mostly VM CI waits)
completed: 2026-11-25
---

# Phase 2 Plan 05: Panel stack (Postgres, Valkey, backend 3.4.11) Summary

**Postgres 18.4, Valkey 9 and Remnawave backend 3.4.11 run as rootless rw-panel Quadlet units on the user-defined network `remnawave`, with the backend on 127.0.0.1:3000 only and secrets fed through 0600 env files; proven healthy in the enforcing Alma and Rocky VMs, idempotent and unchanged across reboot.**

## Accomplishments

- Task 1 (tracer): network, db volume, Postgres unit with `Notify=healthy`, `postgres.env`, restart on env change, `verify_panel.yml`, secrets checksum recording. Task 2: Valkey on a shared named socket volume, backend unit requiring and ordered after db and redis, `backend.env` per the 3.4.11 schema, loopback `PublishPort`, backend InvocationID check.
- VM run 45619945670 for HEAD 8656cb2 (alma10 and rocky10) is green: stack healthy, `GET /api/auth/status` answers 200 on loopback with forwarded headers, 3000 bound to 127.0.0.1 only, nothing on 5432/3001, secrets checksum and backend InvocationID unchanged across idempotence and reboot, the `volumes/remnawave-db-data` path exists, zero AVC. lint and molecule-container are green for the same HEAD.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ulimit nofile above the rootless limit**
- **Found during:** Task 1 VM run (remnawave-db failed to start immediately)
- **Fix:** `Ulimit=nofile=524288:524288` in the db and backend units (user manager hard limit); the plan's flagged assumption, no security relaxation
- **Commit:** 25dc615

**2. [Rule 1 - Bug] Empty quoted word truncates Quadlet Exec=**
- **Found during:** Task 2 VM run (redis never healthy; generated ExecStart ended at `valkey-server --save`)
- **Fix:** bare `--save` before the next option (empty save list), plus a verify assertion on `config get save`
- **Commit:** 526b3b0, 8656cb2

**3. [Rule 3 - Blocking] Start failures had no visible cause**
- **Fix:** rescue block in stack.yml collecting the journal of the service uid and `podman logs`
- **Commits:** 58fbb1e, da7fb5d

**4. [Rule 1 - Bug] VM harness getent fact collision**
- **Found during:** side_effect.yml after the Panel uid lookup replaced `getent_passwd`
- **Fix:** separate uid facts in side_effect.yml, `id -u` in verify_panel.yml
- **Commit:** 92fb804

**Total deviations:** 4 auto-fixed. **Impact:** Task 1 and Task 2 were verified together by the final VM run (the Task 1 tracer run failed on the ulimit and was fixed within the combined iteration), so there is no separate green VM run for the Postgres-only commit.

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None. The only published port is 127.0.0.1:3000 (T-02-12); env files are 0600 with no_log and diff false (T-02-33); images are pinned, no AutoUpdate (T-02-SC).

## Issues Encountered

- GitHub API rate limit was hit by parallel run watchers (about 30 minutes lost); later runs used a single watcher.

## Self-Check: PASSED

- Files exist: roles/panel/tasks/stack.yml, all eight templates, extensions/molecule/shared/verify_panel.yml.
- Commits 4328c74, 25dc615, 58fbb1e, da7fb5d, 526b3b0, 92fb804, 8656cb2 are on main; acceptance greps pass; check.sh OK; CI green for 8656cb2.
