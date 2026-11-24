---
phase: 01-rootless-fundament-i-testovyy-stend
plan: 01
subsystem: infra
tags: [ansible, collection, podman, quadlet, selinux, rootless]
requires: []
provides:
  - collection identity xvpn.remnawave 0.1.0
  - playbook xvpn.remnawave.foundation
  - role xvpn.remnawave.podman_rootless (entry points main, quadlet)
affects: [01-02, 01-03, 01-04, 01-05, phase-2, phase-3, phase-4]
tech-stack:
  added: [fedora.linux_system_roles podman role (via include_role)]
  patterns: [single quadlet entry point, argv-only command tasks, no meta dependencies]
key-files:
  created:
    - galaxy.yml
    - meta/runtime.yml
    - playbooks/foundation.yml
    - roles/podman_rootless/defaults/main.yml
    - roles/podman_rootless/meta/main.yml
    - roles/podman_rootless/meta/argument_specs.yml
    - roles/podman_rootless/tasks/main.yml
    - roles/podman_rootless/tasks/user.yml
    - roles/podman_rootless/tasks/quadlet.yml
key-decisions:
  - "containers.podman kept in galaxy.yml only because LSR 2.5.0 needs it at runtime; no xvpn task calls containers.podman.* directly"
  - "Missing subuid/subgid after useradd fails fast (getsubids assert) instead of guessing a range (RESEARCH A1)"
  - "passt-selinux is optional (dnf list lookup, NOTICE when absent) so EL10.0-10.2 do not fail"
requirements-completed: [FND-02, FND-03, FND-04, FND-06]
status: complete
commits: 1
plan_head_before: 6419083bbfed01b8e1888c883b2f8939f0eed330
plan_head_after: 433f7c7
actuals:
  tokens: 9000
  tasks: 1
  commits: 1
duration: 12 min
completed: 2026-11-24
---

# Phase 1 Plan 01: Tracer, collection identity and podman_rootless Summary

Collection `xvpn.remnawave` 0.1.0 with the operator playbook `foundation` and the `podman_rootless` role: rootless service user `rw-edge` (uid >= 1000 asserted before and after creation, nologin, locked password, home 0700 under `/var/lib/xvpn`), SELinux equivalence `/var/lib/xvpn` = `/home`, sysctl `ip_unprivileged_port_start=80`, linger, user manager, and a single `quadlet` entry point backed by `fedora.linux_system_roles.podman` with `podman_pull_image: false`.

## Task

1. Tracer task: commit 433f7c7 (all 9 files).

## Verification

- Structural gate (syntax-check and `--list-tasks`, count of `podman_rootless` lines = 13): PASS.
- All acceptance_criteria greps and the yaml gate for `passt-selinux`: PASS; no `ansible.builtin.shell` in the role; no `.ansible/` dir.
- Tracer gate: behavioural run is by design deferred to Plan 09 (container tier, first push); the devcontainer has no Podman.

## Deviations from Plan

**1. [Rule 3 - Blocking] Verify ran with stub collections**
- **Found during:** Task 1 verify
- **Issue:** `community.general` and `ansible.posix` are not installed in the devcontainer (the plan assumed they were), so syntax-check could not resolve `sefcontext`/`sysctl`. Installing from Galaxy is gated by human approval at Plan 02 Task 2 (T-01-SC), so nothing was installed.
- **Fix:** ran the same verify command with `ANSIBLE_COLLECTIONS_PATH` pointing at throw-away stub collections (empty module files) in the scratchpad plus the repo symlinked as `xvpn.remnawave`. Stubs are outside the repo.
- **Files modified:** none in the repo.
- **ansible-lint** could not run against the stubs; lint is Plan 03's gate.

**2. Housekeeping done:** removed the stale scratch build `~/.ansible/collections/ansible_collections/xvpn/remnawave` (0.1.0, real dir) as instructed.

**Total deviations:** 1 auto-fixed (Rule 3). **Impact:** none on repo content.

## Flagged assumptions (unproven here)

- Highest-risk unproven assumption of the tracer: the user-manager wait path (`user@UID.service` start, then `/run/user/UID/systemd/private`, RESEARCH A2). It is proven only by the VM tier (Plans 11-12).
- :443 bind and the sysctl namespace in the container tier, sefcontext correctness and zero AVCs: VM tier (D-20).
- Repository URL is an explicit literal `https://github.com/Tualua/xvpn`; Plan 09 re-checks it against origin.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model.

## Self-Check: PASSED

- All 9 files exist; commit 433f7c7 is an ancestor of HEAD.
