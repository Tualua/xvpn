---
phase: 01-rootless-fundament-i-testovyy-stend
plan: 02
subsystem: testing
tags: [molecule, podman, galaxy, quadlet, requirements]
requires:
  - phase: 01-01
    provides: podman_rootless role with the quadlet entry point, playbooks/foundation.yml
provides:
  - Exact, justified and human-approved Galaxy pins (requirements.yml)
  - ansible.cfg with pipelining
  - Molecule-only fixture Quadlet unit
  - Container Molecule scenario (molecule/prepare/converge) driving the tracer path
affects: [01-03, 01-04, 01-07, 01-08, 01-09, 01-10, 01-11]
tech-stack:
  added: [fedora.linux_system_roles 2.5.0, ansible.posix 2.2.2, community.general 14.0.1, containers.podman 1.21.2, community.vagrant 1.0.1]
  patterns: [getenforce test double + secure_path drop-in in container tier only]
key-files:
  created:
    - requirements.yml
    - ansible.cfg
    - extensions/molecule/shared/templates/xvpn-fixture.container.j2
    - extensions/molecule/container/molecule.yml
    - extensions/molecule/container/prepare.yml
    - extensions/molecule/container/converge.yml
  modified: []
key-decisions:
  - "Container scenario test_sequence ships without verify; Plan 04 adds it together with verify.yml"
  - "user-manager start/wait is off in the container tier (xvpn_podman_rootless_manage_user_manager: false); proven only by the VM tier"
requirements-completed: []
status: complete
actuals:
  tokens: 6000
  tasks: 3
  commits: 2
plan_head_before: 6384609aab1fbd480ac0c5003b7ad06dabcff38e
plan_head_after: c6fa697bc7a8bc55cf12ce34e611f66c6dabbe0f
---

# Phase 1 Plan 02: Container Molecule scenario and pinned Galaxy dependencies Summary

Exactly pinned, human-approved Galaxy collections plus a container Molecule scenario that runs the foundation playbook and deploys a pinned nginx fixture through the single `quadlet` entry point.

## Tasks

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | Pinned and justified Galaxy dependencies, ansible.cfg, fixture unit | 3ad38d2 |
| 2 | Galaxy legitimacy gate (checkpoint:human-verify, blocking-human) | no files: approved by human |
| 3 | Container scenario: molecule.yml, prepare.yml, converge.yml | c6fa697 |

## Galaxy pin justification (Task 2: approved by the human, all five pins as written)

| Collection | Pin | Publisher / source | Evidence |
| ---------- | --- | ------------------ | -------- |
| fedora.linux_system_roles | 2.5.0 | linux-system-roles (Red Hat) | tarball read in RESEARCH, roles/podman inspected |
| ansible.posix | 2.2.2 | Ansible core team | Galaxy API |
| community.general | 14.0.1 | Ansible community | Galaxy API |
| containers.podman | 1.21.2 | Podman project | runtime dependency of fedora.linux_system_roles, pinned so the transitive install cannot float |
| community.vagrant | 1.0.1 | Ansible community | module source read in RESEARCH (VM tier only) |

The first install from `requirements.yml` happened only after this approval (Task 3 verify). The install also pulled a transitive `community.library_inventory_filtering_v1` 1.1.5 (dependency of community.vagrant or community.general); it was not in the approved set and is noted here for the Plan 09 review.

## Verification

- Task 3 automated verify: collections installed from `requirements.yml` into a temp path, `ansible-playbook --syntax-check` passed for prepare.yml and converge.yml, `tracer-ok` printed.
- Acceptance greps: `tasks_from: quadlet` 1, `import_playbook` 1, `xvpn-test-path` under roles/playbooks 0, no `roles/podman_rootless/templates`; molecule.yml gate prints `1 1` (both platforms systemd/privileged, no verify step).

## Deferred verification

- Behavioural run of `molecule test -s container` (converge + idempotence on rocky10/alma10): not possible in the devcontainer (no Podman, no Molecule). First run is the GitHub Actions push in Plan 09. Flagged assumptions remain open: sudo `secure_path` on the init images (prepare asserts it loudly), fixture `Network=pasta` (container tier does not activate it).

## Deviations from Plan

None. The first Task 3 verify used a python without PyYAML for one acceptance one-liner; re-run with the ansible interpreter, passed.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

All six files exist; commits 3ad38d2 and c6fa697 are in HEAD history.
