---
gsd_state_version: "1.0"
milestone: v3.7.20
current_phase: 03
current_phase_name: Нода с Reality self-steal и авто-регистрацией
status: executing
stopped_at: Completed 03-13-PLAN.md
last_updated: "2026-11-28T18:34:51.396Z"
last_activity: 2026-11-28
last_activity_desc: Phase 03 execution started
state_head: a2365dc62f7fef24344bb0a52ace9aa65c5de5a9
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 40
  completed_plans: 37
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-28)

**Core value:** Из inventory одной командой получается рабочая, защищённая и идемпотентная инсталляция Remnawave на RHEL 10 с SELinux enforcing: Panel за прокси с защищённым входом, ноды авто-регистрируются через API, Reality self-steal.
**Current focus:** Phase 03 — Нода с Reality self-steal и авто-регистрацией

## Current Position

Phase: 03 (Нода с Reality self-steal и авто-регистрацией) — EXECUTING
Plan: 14 of 16
Status: Ready to execute
Last activity: 2026-11-28 — Phase 03 execution started

Progress: [████░░░░░░] 40%

## Performance Metrics

**Velocity:**
- Total plans completed: 24
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 12 | - | - |
| 02 | 12 | - | - |

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
| Phase 02 P01 | 45 min | 2 tasks | 14 files |
| Phase 02 P02 | 25 min | 2 tasks | 14 files |
| Phase 02 P03 | 150 min | 2 tasks | 11 files |
| Phase 02 P04 | 75min | 2 tasks | 9 files |
| Phase 02 P05 | 6h | 2 tasks | 14 files |
| Phase 02 P06 | ~2h | 2 tasks | 7 files |
| Phase 02 P07 | 75min | 3 tasks | 13 files |
| Phase 02 P08 | 40min | 2 tasks | 4 files |
| Phase 02 P09 | 55min | 2 tasks | 6 files |
| Phase 02 P10 | 130min | 2 tasks | 10 files |
| Phase 02 P11 | ~3h | 2 tasks | 5 files |
| Phase 02 P12 | ~3h (CI waits) | 3 tasks | 8 files |
| Phase 03 P01 | 20min | 2 tasks | 14 files |
| Phase 03 P02 | 25min | 2 tasks | 4 files |
| Phase 03 P03 | 60 min | 2 tasks | 22 files |
| Phase 03 P04 | 45min | 2 tasks | 40 files |
| Phase 03 P05 | 25min | 2 tasks | 9 files |
| Phase 03 P06 | ~1h40m | 2 tasks | 8 files |
| Phase 03 P07 | 60min | 2 tasks | 15 files |
| Phase 03 P08 | 60min | 2 tasks | 11 files |
| Phase 03 P09 | ~1h40m | 2 tasks | 3 files |
| Phase 03 P10 | 25min | 2 tasks | 9 files |
| Phase 03 P11 | 60min | 2 tasks | 11 files |
| Phase 03 P12 | 25min | 2 tasks | 6 files |
| Phase 03 P13 | 90min | 2 tasks | 8 files |

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
- [Phase 02]: Traefik pinned to v3.7.20 (three advisories fixed over v3.7.19); container tier always uses the staging ACME CA
- [Phase 02]: Traefik access log drops RequestPath and all headers except User-Agent (D-19)
- [Phase 02]: Panel :80 router has accessLogs false so the gate secret path never reaches the access log (T-02-38)
- [Phase 02]: Pebble root is stored on the VM by the first verify_edge run because Pebble builds a new CA at every start (reboot)
- [Phase 02]: Controller address for the real-IP proof is read as SSH_CLIENT in the SSH session without become
- [Phase 02]: 02-04: guard asserts read only boolean/key-list facts so failures stay visible without exposing values; placeholder check precedes divergence check
- [Phase 02]: Quadlet Exec= is truncated at an empty quoted word; Valkey uses a bare --save, and Ulimit nofile is 524288 (rootless user manager hard limit)
- [Phase 02]: Admin JWT requests need X-Remnawave-Client-Type: browser (backend 3.4.11); register only when isRegisterAllowed and not isLoginAllowed
- [Phase 02]: Panel gate built from routers, headers and redirectRegex on noop@internal (D-05 primary variant); no fallback needed
- [Phase 02]: 02-08: gate fixtures read from render.yml marker lines; random test tokens via python3 secrets (no tr|head under pipefail)
- [Phase 02]: 02-09: gitleaks key rules use [ \t]* around the separator (no cross-line matches); (?-i) on the FHS exemption is load-bearing (observed)
- [Phase 02]: Sub-page 8.0.1 with backend 3.4.11 verified; rejected-token outcome is HTTP 502 without data-panel; healthcheck via curl /internal/health
- [Phase 02]: 02-11: sub-page toggle removes the unit directly when xvpn_panel_activate is false (LSR cleanup needs the user manager bus)
- [Phase 02]: 02-12: ACME store is one persistent 0600 file per CA (acme-production/staging/custom-<hash12>.json); legacy acme.json not migrated
- [Phase 03]: Node reuses edge unchanged: loopback websecure via play vars plus one node-selfsteal drop-in route
- [Phase 03]: Traefik stays the self-steal terminator: selfsteal gate passes 9 cases on v3.7.20
- [Phase 03]: Decoy template chosen by rendezvous rule over node domain; Panel page and catch-all unchanged
- [Phase 03]: 03-04: selfsteal gate installs the decoy through the production decoy.yml; node verify helpers live in extensions/molecule/shared
- [Phase 03]: Own remnawave_* modules with stdlib unittest and a fake Panel; client pins Panel 3.4.x before first write
- [Phase 03]: node-vm stand reuses shared/verify_runtime.yml for zero-AVC on both VMs; Task 2 pushed with Task 1 fix, one dispatched run (46146662440) proves both
- [Phase 03]: 03-08: 443 opens only after the loopback cert gate; node API 2222 only via Panel-source IPv4 rich rules
- [Phase 03]: 03-10: IPv4-mapped ::ffff:0:0/96 dropped from xvpn_node_blocked_cidrs (Xray 26.11.9 rejects it in routing ip)
- [Phase 03]: 03-10: config profile keys never from declaration; module.params config redacted so invocation carries no key
- [Phase 03]: Panel 3.4.11 seeds the reserved squad Default-Squad; node address guard compares the Panel address string, no DNS
- [Phase 03]: 03-13: node and squads registered in the role; connected wait 30x5s fails with diagnostics

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 2 plan-phase] Plan-checker override accepted by user (2026-11-25): the gitleaks scan (02-08 Task 3 at the time; since review round 1 it is Plan 02-09, which already carries the fixes below in its tasks and wording) has known residual DOC-04 bypasses — (a) the `xvpn-secret-key-pathlike` FHS-path allowlist matches case-insensitively, so a value like `/var/<base64>` under a `*_file/_dir/_path` key is not flagged; (b) upstream global allowlist/stopwords pulled in by `useDefault = true` (e.g. substrings `false`, `null`, prefix `changeme`) can suppress `xvpn-secret-key` findings without the fixture marker, contrary to the plan's must_haves/T-02-35 wording; (c) secret-named keys with other suffixes (e.g. `_file_v2`) are not scanned. Executor of 02-09 should make the path exemption case-sensitive (or require a file-suffix discriminator), add a self-test case `/var/` + mixed-case base64 (expect exit 3), and correct the must_haves/T-02-35 wording — validating against the real gitleaks 8.30.1 binary. Checker evidence: plan-phase session scratchpad (not persisted).
- Phase 3 (HIGH RISK): Reality -> Traefik loopback TLS self-steal has no verified precedent; spike with hand-written configs first; fallback is revisiting the Traefik decision.
- Phase 3: Remnawave REST contract must be read from the pinned backend 3.4.11 OpenAPI before writing modules.
- [Phase 1] Follow-up: make `molecule-vm` a required check on main (deferred policy item).
- [Phase 2] Open info findings in 02-REVIEW-DISPOSITION.md: IN-01 (until/set_fact guard scans only roles/*/tasks), IN-02 (hard-coded store hashes in VM side_effect), IN-04 (xvpn_panel_failure_log_dir removed without deprecation note); IN-03 deferred (orphaned acme.json, documented).
- [Phase 2] Deferred UAT follow-up: automated test for scripts/ci_watch.sh cancelled-run and dispatch branches (02-UAT.md, test 9).
- [Phase 1] IN-03 skipped (01-REVIEW-DISPOSITION.md): getenforce gate runs before libselinux-utils is installed; role fails with a clear message instead of installing it.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261126-hc8 | Fix WR-01/WR-02/IN-01: failure-log save in panel stack rescue via nested block/rescue, log dir as role variable | 2026-11-26 | 6bff6f0 | [261126-hc8-fix-wr-01-wr-02-in-01-failure-log-save-i](./quick/261126-hc8-fix-wr-01-wr-02-in-01-failure-log-save-i/) |
| 261127-40g | Hardcode panel failure log dir as /var/log/xvpn and drop its validation | 2026-11-27 | c4eadea | [261127-40g-hardcode-panel-failure-log-dir-as-var-lo](./quick/261127-40g-hardcode-panel-failure-log-dir-as-var-lo/) |
| 3 | Shorten COVERAGE.md capability cell (phase 02) to pass api-coverage gate | 2026-11-27 | 1745c4f | — |
| 4 | Add examples/gitlab-deploy GitLab CI template for Panel deploy | 2026-11-27 | 1865e10 | — |
| 5 | GitLab deploy template: community EE image, vendor/xvpn submodule, exact dependency pins | 2026-11-27 | 6669979 | — |
| 6 | GitLab deploy template: fail fast when SSH variables are not of type File | 2026-11-27 | a841c2e | — |
| 261127-ej4 | Add Oracle Linux 10 as a supported target OS with CI coverage | 2026-11-27 | 4c05877 | [261127-ej4-add-oracle-linux-10-as-a-supported-targe](./quick/261127-ej4-add-oracle-linux-10-as-a-supported-targe/) |
| 8 | CI: paths-ignore .planning/** and **.md on push/PR workflows | 2026-11-27 | 97a3f99 | — |
| 9 | Container-tier negative case: equal Panel and subscription domains rejected | 2026-11-27 | f111d61 | — |
| 10 | VM prepare installs tar (Oracle Linux 10 box lacks it; Pebble unarchive failed) | 2026-11-27 | 2d08b00 | — |
| 11 | Preflight argument_specs default lists OracleLinux (review WR-02) | 2026-11-27 | a7d502a | — |
| 12 | ci(gate): run gate/gitleaks on every push, lint and Molecule keep the skip (WR-01) | 2026-11-28 | f6f6786 | — |

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| *(none)* | | | | |

## Session Continuity

Last session: 2026-11-28T18:34:50.679Z
Stopped at: Completed 03-13-PLAN.md
Resume file: None
