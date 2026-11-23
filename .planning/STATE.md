---
gsd_state_version: "1.0"
current_phase: 1
current_phase_name: Rootless-фундамент и тестовый стенд
status: planning
stopped_at: Phase 1 context gathered
last_updated: "2026-11-23T10:36:46.530Z"
last_activity: 2026-11-23
last_activity_desc: Roadmap created (5 phases, 54/54 requirements mapped)
state_head: 34749552e6ad16a8e8ebfaca69b2261afb48b2f5
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-23)

**Core value:** Из inventory одной командой получается рабочая, защищённая и идемпотентная инсталляция Remnawave на RHEL 10 с SELinux enforcing: Panel за прокси с защищённым входом, ноды авто-регистрируются через API, Reality self-steal.
**Current focus:** Phase 1 — Rootless-фундамент и тестовый стенд

## Current Position

Phase: 1 of 5 (Rootless-фундамент и тестовый стенд)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-11-23 — Roadmap created (5 phases, 54/54 requirements mapped)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Coarse vertical MVP, 5 phases; research's 8 horizontal phases compressed (self-steal node + API registration merged into Phase 3; ops + hardening + CI/docs merged into Phase 5)
- [Roadmap]: Molecule container tier + VM tier (EL10, SELinux enforcing) built in Phase 1; every later phase is verified on it
- [Roadmap]: Pebble/LE staging (QA-05) introduced in Phase 2 together with the first ACME usage; DOC-04 (no_log/placeholder asserts) introduced in Phase 2 with the first secrets
- [Research]: Pinned versions — backend 3.4.11, node 3.4.6, subscription-page 8.0.1, Postgres 18.4, Valkey 9, Traefik v3.7.19; Traefik and remnanode on `Network=host`; Reality dest `127.0.0.1:8443`, `xver: 0`; env files (0600) instead of Podman secrets in v1

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 2 (HIGH RISK): cookie/secret-path admin gate in pure Traefik (no plugins) is unproven; user chose it for v1 with no IP-allowlist fallback (allowlist is PANEL-V2-01). Spike early; if infeasible, escalate to user.
- Phase 3 (HIGH RISK): Reality -> Traefik loopback TLS self-steal has no verified precedent; spike with hand-written configs first; fallback is revisiting the Traefik decision.
- Phase 3: Remnawave REST contract must be read from the pinned backend 3.4.11 OpenAPI before writing modules.
- Phase 1: KVM availability on CI runners for the libvirt VM tier is unconfirmed.

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-11-23T10:36:46.483Z
Stopped at: Phase 1 context gathered
Resume file: .planning/phases/01-rootless-fundament-i-testovyy-stend/01-CONTEXT.md
