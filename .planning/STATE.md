---
gsd_state_version: "1.0"
milestone: v3.7.20
current_phase: 2
current_phase_name: Panel за Traefik с защищённым входом
status: executing
stopped_at: Phase 2 context gathered
last_updated: "2026-11-25T05:19:19.608Z"
last_activity: 2026-11-25
last_activity_desc: Phase 01 complete, transitioned to Phase 2
state_head: "0bf4be5a97fcd417db70207135675e382f9ef6b8"
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 22
  completed_plans: 12
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-25)

**Core value:** Из inventory одной командой получается рабочая, защищённая и идемпотентная инсталляция Remnawave на RHEL 10 с SELinux enforcing: Panel за прокси с защищённым входом, ноды авто-регистрируются через API, Reality self-steal.
**Current focus:** Phase 2 — Panel за Traefik с защищённым входом

## Current Position

Phase: 2 (Panel за Traefik с защищённым входом) — READY TO EXECUTE
Plan: Not started
Status: Ready to execute
Last activity: 2026-11-25 — Phase 01 complete, transitioned to Phase 2

Progress: [██░░░░░░░░] 20%

## Performance Metrics

**Velocity:**
- Total plans completed: 12
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 12 | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 12 min | 1 tasks | 9 files |
| Phase 01 P02 | 30min | 3 tasks | 6 files |
| Phase 01 P03 | n/a | 2 tasks | 7 files |
| Phase 1 P09 | n/a | 3 tasks | 5 files |
| Phase 01 P04 | n/a | 2 tasks | 7 files |
| Phase 01 P05 | n/a | 2 tasks | 6 files |
| Phase 01 P06 | 25m | 2 tasks | 7 files |
| Phase 01 P07 | n/a | 2 tasks | 9 files |
| Phase 01 P08 | n/a | 2 tasks | 7 files |
| Phase 01 P11 | 25 min | 2 tasks | 6 files |
| Phase 01 P10 | 10min | 1 tasks | 1 files |
| Phase 01 P12 | 3h | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Coarse vertical MVP, 5 phases; research's 8 horizontal phases compressed (self-steal node + API registration merged into Phase 3; ops + hardening + CI/docs merged into Phase 5)
- [Roadmap]: Molecule container tier + VM tier (EL10, SELinux enforcing) built in Phase 1; every later phase is verified on it
- [Roadmap]: Pebble/LE staging (QA-05) introduced in Phase 2 together with the first ACME usage; DOC-04 (no_log/placeholder asserts) introduced in Phase 2 with the first secrets
- [Research]: Pinned versions — backend 3.4.11, node 3.4.6, subscription-page 8.0.1, Postgres 18.4, Valkey 9, Traefik v3.7.19; Traefik and remnanode on `Network=host`; Reality dest `127.0.0.1:8443`, `xver: 0`; env files (0600) instead of Podman secrets in v1
- [Phase 01]: containers.podman declared only because LSR 2.5.0 needs it at runtime; podman_rootless fails fast when useradd allocates no subids; passt-selinux optional
- [Phase 01]: Container Molecule scenario ships without verify step; Plan 04 adds it with verify.yml
- [Phase 01]: ansible-lint production profile with var-naming[no-role-prefix] skip is the accepted lint bar; yamllint mandatory in CI
- [Phase 1]: CI runs ansible-core 2.21 only; container scenario starts systemd-logind in prepare (01-09)
- [Phase 01]: Generator dry-run rc is non-zero on a bad unit (A5 confirmed in CI); loop assert failures matched via whole failed result
- [Phase 01]: Preflight regexes avoid backslashes (Jinja escapes); getent ahosts misses are {domain: null}
- [Phase 01]: 01-07: SSH guard inlined twice in roles/common/tasks/firewalld.yml; FND-05 left open until VM-tier zero-AVC proof
- [Phase 01]: 01-08: failed case messages recorded as to_json of ansible_failed_result (loop asserts)
- [Phase 01]: VM boxes pinned via community.vagrant box_download_checksum(_type); box_checksum is not a driver key
- [Phase 01]: 01-12: alma10 box via Vagrant Cloud catalog mode (pinned version); Dontaudit parsed with (?:^|\s) regex; policy packages installed in prepare before semodule -DB

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 2 (HIGH RISK, reduced): cookie/secret-path admin gate in pure Traefik was proven in the research spike (Traefik 3.7.19 + Pebble); remaining risk is SELinux AVCs for Traefik `Network=host` (A1/A2) — escalate via checkpoint:decision, never a silent boolean.
- [Phase 2 plan-phase] Plan-checker override accepted by user (2026-11-25): 02-08 Task 3 gitleaks scan has known residual DOC-04 bypasses — (a) the `xvpn-secret-key-pathlike` FHS-path allowlist matches case-insensitively, so a value like `/var/<base64>` under a `*_file/_dir/_path` key is not flagged; (b) upstream global allowlist/stopwords pulled in by `useDefault = true` (e.g. substrings `false`, `null`, prefix `changeme`) can suppress `xvpn-secret-key` findings without the fixture marker, contrary to the plan's must_haves/T-02-35 wording; (c) secret-named keys with other suffixes (e.g. `_file_v2`) are not scanned. Executor of 02-08 should make the path exemption case-sensitive (or require a file-suffix discriminator), add a self-test case `/var/` + mixed-case base64 (expect exit 3), and correct the must_haves/T-02-35 wording — validating against the real gitleaks 8.30.1 binary. Checker evidence: plan-phase session scratchpad (not persisted).
- Phase 3 (HIGH RISK): Reality -> Traefik loopback TLS self-steal has no verified precedent; spike with hand-written configs first; fallback is revisiting the Traefik decision.
- Phase 3: Remnawave REST contract must be read from the pinned backend 3.4.11 OpenAPI before writing modules.
- [Phase 1] Follow-up: make `molecule-vm` a required check on main (deferred policy item).
- [Phase 1] IN-03 skipped (01-REVIEW-DISPOSITION.md): getenforce gate runs before libselinux-utils is installed; role fails with a clear message instead of installing it.

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-11-25T02:36:15.800Z
Stopped at: Phase 2 context gathered
Resume file: .planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-CONTEXT.md
