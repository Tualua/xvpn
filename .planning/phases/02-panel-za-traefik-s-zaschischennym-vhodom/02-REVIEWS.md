---
phase: 2
reviewers: [opencode, qwen]
reviewed_at: 2026-11-25T07:03:55Z
plans_reviewed: [02-01-PLAN.md, 02-02-PLAN.md, 02-03-PLAN.md, 02-04-PLAN.md, 02-05-PLAN.md, 02-06-PLAN.md, 02-07-PLAN.md, 02-08-PLAN.md, 02-09-PLAN.md, 02-10-PLAN.md]
models:
  opencode: "unknown"
  qwen: "unknown"
model_sources:
  opencode: "unknown"
  qwen: "unknown"
---

# Cross-AI Plan Review — Phase 2

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

# Cross-AI Plan Review — Phase 2 (Panel за Traefik)

I verified plan claims against the actual repo: `roles/podman_rootless/tasks/quadlet.yml`, `quadlet_validate.yml`, `roles/preflight/*`, `roles/common/tasks/firewalld.yml`, `scripts/check.sh`, `extensions/molecule/{container,vm,shared}/*`, `playbooks/foundation.yml`, `.github/workflows/{lint,molecule-container,molecule-vm}.yml`, and `galaxy.yml`. The repo state matches the plans' `HEAD=` expectations (6 negative cases in `container/verify.yml:266`, fixture in converge, `build_ignore` contains `scripts`, etc.). External claims (Traefik 3.7.20, Remnawave 3.4.11 contract, Pebble pins) could not be verified from the repo and are taken as research-attested.

One **HIGH cross-plan integration defect** found (02-05 ↔ 02-07, detailed below). Everything else is MEDIUM/LOW.

---

## 02-01

**Summary** — Well-scoped first plan: the `edge` role (Traefik v3.7.20 + decoy + D-16 route interface) renders in the container tier with generator dry-run, input guards, D-19 path-free access log baked into the static config, and the `ci_watch.sh` dispatch-and-wait helper all later plans depend on. Referenced Phase 1 interfaces check out (`quadlet.yml:31-36` skips absent specs in validation; `check.sh:30-34` enforces argument_specs; `container/verify.yml` block/rescue pattern exists).

**Strengths**
- Templates written "in final hardened form now" (encoded chars off, sniStrict, D-19 log fields) instead of a throwaway tracer; guard mutations (`grep -ci 'sock' == 0`, `Network=host` == 1) are real tripwires.
- Correct reading of Traefik access-log semantics: `RequestPath: drop` + headers default-drop with only `User-Agent: keep` is internally consistent, and the EDGE-03 probe strategy (select log line by unique UA) is coherent with it.
- Negative cases (`edge-custom-ca-without-server`, `edge-bad-route-name`) assert both the failure text and that no file was written.
- `ci_watch.sh` design matches the actual workflow triggers: lint/molecule-container run on push (`.github/workflows/lint.yml:4-8`), molecule-vm only on dispatch/PR/cron (`.github/workflows/molecule-vm.yml:4-9`), justifying `--dispatch`.

**Concerns**
- MEDIUM: `gh run list --commit <sha>` plus concurrency `cancel-in-progress: true` (all three workflows) means a fast follow-up push cancels the in-flight run for HEAD; ci_watch will then watch a cancelled run and fail. The "repair" loop tolerates this, but the plan should state that a cancelled (not failed) run is a retry, not a code defect — otherwise the executor may burn repair rounds on it.
- MEDIUM: the verify asserts the *rendered* decoy file mode 0644/0755 for uid 101 (nginx-unprivileged), but the site dir is mounted `:ro,Z` from a 0755 tree under rw-edge's 0700 home — reachable only via the bind mount, fine, but the plan never asserts the decoy answers in the container tier (it can't, units aren't activated). Acceptable; the VM tier covers it.
- LOW: `xvpn_edge_route_sensitive` as a *templated* `no_log` value is clever but is also load-bearing for `check_no_log.py` in 02-04; the contract "`xvpn_edge_route_sensitive` templated no_log counts as set" must be implemented exactly or the static gate false-positives.

**Suggestions**
- In ci_watch.sh, treat `conclusion == "cancelled"` for the selected run as "poll again / refetch newest run" rather than an immediate failure.
- Document in `route.yml`'s header that `watch: true` (A6) is the *only* reason no restart is triggered, so Phase 3 doesn't cargo-cult a restart-less route into a scenario where A6 failed.

**Risk Assessment** — LOW-MEDIUM. Straightforward tracer on a proven Phase 1 interface; main uncertainties (A6, ci_watch races) have declared fallbacks.

---

## 02-02

**Summary** — Creates the one-command `playbooks/panel.yml` (role order preflight → common → podman_rootless → edge → panel, D-18), moves the container tier onto the real playbook, and adds the QA-05 static `check_acme_ca` guard. The playbook shape mirrors `playbooks/foundation.yml` accurately; check.sh's syntax-check loop (`scripts/check.sh:43-55`) will indeed pick up panel.yml/site.yml automatically.

**Strengths**
- The QA-05 guard is mutation-tested (staging → production must flip check.sh to exit 1), which is the right standard for a static gate.
- The `xvpn-panel-http` router gets an explicit `observability.accessLogs: false` because the research spike only proved the HTTPS gate router unlogged — good defensive reasoning that doesn't overclaim the spike (D-01 for `http://<domain>/<gate_path>`).
- Preflight wiring is consistent with the existing role: `xvpn_preflight_domains` exists (`roles/preflight/defaults/main.yml:17`), and the repeat-run port ownership is already tolerated by design (`roles/preflight/tasks/check_ports.yml:2`, accepted users include rw-edge/rw-panel via `xvpn_preflight_service_users` + podman_rootless users).

**Concerns**
- MEDIUM: `check_acme_ca` only scans `extensions/molecule/*/converge.yml` (+ scenario vars). Plan 02-08 later adds `scripts/gate/render.yml`, which *also* renders the edge templates with a CA setting and is not covered by this guard — 02-08 compensates with its own acceptance (`grep -c 'acme-v02...' render.yml == 0`), but the static guard itself has a blind spot for any future non-molecule consumer of the edge role.
- MEDIUM: Task 1 creates `roles/panel/meta/argument_specs.yml` but defers `meta/main.yml` to Task 2; `check.sh:27-34` only demands argument_specs, so this passes, but ansible-lint may emit `role` metadata warnings between Task 1 and Task 2 commits — cosmetic, transient.
- LOW: converge passes `xvpn_subscription_domain` "consumed from Plan 02-04 on" — defining an input two plans before the role declares it is harmless but should be commented as forward-wiring to avoid executor confusion.

**Suggestions**
- Extend `check_acme_ca` to also scan any file matching `scripts/gate/*.yml` (or generally, any file that sets `xvpn_edge_acme_ca`) when 02-08 lands — or at least note the gap in 02-08.
- In `playbooks/panel.yml` play 1, guard against `xvpn_panel_domain` being empty with a fail-before-preflight assert; today an unset domain surfaces as an obscure preflight domain-format error.

**Risk Assessment** — LOW. Mostly wiring; the guard is mutation-proven.

---

## 02-03

**Summary** — The highest-leverage plan of the phase: switches the VM tier to the real playbook with Pebble HTTP-01 end-to-end, sniStrict, real-client-IP proof, acme.json 0600, idempotence/reboot/zero-AVC. The escalation discipline (no silent booleans, `checkpoint:decision` with AVC evidence) is correctly inherited from Phase 1. Existing VM plumbing (AVC marker ordering in `vm/prepare.yml:86-106`, InvocationID pattern in `vm/converge.yml:58-65`, `verify_runtime.yml` inputs) is accurately referenced.

**Strengths**
- The bind-probe ports are correctly rethought: side_effect passes `[81]` because Traefik now holds 80 *and* 443 — avoiding the EADDRINUSE trap that would otherwise false-fail `verify_rootless.yml:148-182` (only PermissionError → rc 13 is handled).
- Real-IP proof identified by `request_User-Agent`, not by path — fully consistent with D-19's global `RequestPath: drop`, and the plan explicitly forbids falling back to path-based selection (`## CHECKPOINT REACHED` instead).
- Pebble pins with sha256 for 5 artifacts, challtestsrv flag set matching Pitfall 9, `/etc/hosts` wiring for the preflight DNS check — all coherent.
- Port-label diagnostics (`semanage port -l`) added informationally, per the resolved Open Question 2.

**Concerns**
- HIGH (bounded): the first enforcing proof that `container_t` under `Network=host` may bind 80/443 and connect to loopback services (A1/A2) happens here. The plan handles denial correctly (stop, escalate), but this is a genuine coin-flip on EL10.3 policy; if option (B) (pasta) is chosen, 02-04..02-10 assumptions about loopback `PublishPort` reach change too. The plan should state that a pasta fallback re-opens the EDGE-03 real-IP analysis (pasta NATs; ClientHost may become the pasta address) — currently only the boolean/pasta choice is listed, not its downstream blast radius.
- MEDIUM: Pebble/challtestsrv run as *system* services before the AVC marker, but they keep running during the whole converge; any AVC they generate post-marker pollutes the zero-AVC gate (A7). The flag is present, but the mitigation ("run them as a separate rootless user/container instead") is a nontrivial mid-execution redesign. Consider pre-validating in the VM prepare diagnostics that both services are quiet for a few seconds before the marker.
- MEDIUM: the real-IP check keys off `ansible_env.SSH_CLIENT` — correct under Molecule/libvirt NAT (same source for SSH and curl), but brittle if the molecule driver ever proxies or the controller connects via a different route than curl does (e.g., IPv6 vs IPv4). The SUMMARY-mandated IPv4-only disclaimer covers the family issue, not the route mismatch issue.
- LOW: verify_edge asserts the decoy body equals `roles/edge/files/decoy/index.html` via controller-side sha1 — fine, but the curl body capture and checksum comparison are left underspecified (content file, `stat.checksum` sha1 comparison).

**Suggestions**
- Add one sentence to the escalation rule: "if (B) pasta is selected, 02-05/02-09 loopback PublishPort assumptions and the EDGE-03 probe must be re-derived before continuing" — turning the blast radius into an explicit obligation.
- In VM prepare, after starting Pebble services, run a short "AVC canary" (`ausearch -m AVC -ts recent` for the Pebble units) and fail prepare early with evidence if they already deny.

**Risk Assessment** — MEDIUM-HIGH. Inherent platform risk (SELinux + host networking) is unavoidable and well-fenced, but it is the plan most likely to hit its checkpoint, and a pasta fallback would cascade.

---

## 02-04

**Summary** — Generate-once secrets on the Panel host (D-07) with divergence/loss refusal, placeholder asserts, the static `check_no_log.py` gate, and the full panel input surface. The design correctly implements D-06 (gate secret freely rotatable) including the subtle path→cookie-value coupling so a path rotation invalidates old cookies.

**Strengths**
- The lost-secrets guard (file missing + `remnawave-db-data` volume exists → refuse) directly addresses Pitfall 6, the most realistic operator footgun; the volume name matches 02-05's `VolumeName=remnawave-db-data` (cross-plan consistency verified).
- Class-guaranteed password construction (segments + shuffle, Pitfall 3) with a format assert before write; alnum-only constraint keeps values URL/YAML/regex-safe.
- `check_no_log.py` design (recursive block/rescue/always walk, inherited no_log, `diff: false` requirement for template/copy, loop-label safety) is sound and mutation-tested.
- The acceptance `grep -c 'cacheable' == 0` plus the "do not mention it in comments" note is a cute self-aware guard against the persistent-fact-cache footgun.

**Concerns**
- MEDIUM: divergence detection compares the *override* against the *stored* value in memory — correct — but an operator who changes a secret directly inside `panel-secrets.yml` and *also* passes the old value in vault gets a divergence failure naming the key, which is the desired loud behavior; however an operator who hand-edits the file has no path back except manual editing (documented). Acceptable for v1; the flagged assumption says as much.
- MEDIUM: the eight-key contract of `panel-secrets.yml` is now the D-07 "costly" interface; nothing in this plan writes the file format to a shared doc beyond the plan text. Phase 3 and 5 consume the *path*, not the format, so this is fine — but `check_no_log.py`'s sensitive-name list hardcodes facts like `xvpn_panel_secrets_stored`; keep that list in one place.
- LOW: `admin_password` 40 chars alnum — the backend policy regex is asserted, but the plan does not re-verify the policy against 3.4.11 at execution time (it's research-attested; Pitfall 3 cites the source). Fine, but the executor should record the observed policy in the SUMMARY like 02-06 does for username constraints.
- LOW: `xvpn_panel_secrets_generated` runs the password lookups on *every* run (values discarded when stored exist). Harmless, but in check mode or with a YAML parse hiccup this could mask "stored file unreadable" as "generate new" — the lost-secrets guard covers the volume case, not the malformed-file case. Add: if the file exists but fails `from_yaml`, fail loudly instead of treating as `{}`.

**Suggestions**
- Add an explicit guard: secrets file exists but unparseable → fail with "panel-secrets.yml is corrupt; restore from backup" rather than merging over `{}`.
- Record the 3.4.11 password/username policies in the SUMMARY for the traceability chain.

**Risk Assessment** — LOW-MEDIUM. Logic is thorough; residual risk is mostly executor fidelity to the no_log/diff discipline, which the static gate enforces.

---

## 02-05

**Summary** — The Panel stack (PG 18.4, Valkey 9, backend 3.4.11) as rw-panel Quadlet units on a private network with loopback-only publishing, env files 0600 rendered no_log from the secrets fact, restart-on-change per Pitfall 7. Quadlet keys match the research-verified Podman 6 contract; the incremental tracer (DB first, then Valkey+backend) is well split.

**Strengths**
- Env contract encoded with guard mutations that prevent classic mistakes: the `JWT_` grep enforces the verified "only `JWT_AUTH_LIFETIME` exists in 3.4.11" fact, and `FRONT_END_DOMAIN=*` is pinned with the CORS reasoning recorded.
- `PublishPort=127.0.0.1:3000:3000` guard (`PublishPort` absent from db/redis templates), `verify_common.yml`'s exact-port check (`verify_common.yml:95-102`) plus internal-port regexes (`:111-118`) give defense in depth for T-02-12.
- Restart-on-change is scoped to the affected unit only, and the backend InvocationID + secrets checksum recording in the VM converge gives a real idempotence proof (not just Molecule's changed=0).
- `Notify=healthy` + `HealthStartPeriod` + `TimeoutStartSec=900` address Pitfall 11 (first-start migration + pull time).

**Concerns**
- HIGH (cross-plan, see 02-07): `verify_panel.yml` asserts "the secrets file checksum equals the one recorded after the first converge", and it is included from `vm/verify.yml` *after* the reboot — but Plan 02-07's gate rotation rewrites the secrets file pre-reboot. The post-reboot checksum assertion will fail. See the 02-07 section for the full analysis.
- MEDIUM: A3 (rootless user-defined bridge + loopback PublishPort on Podman 6/EL10) is the load-bearing unproven assumption; the VM tier proves it, and the escalation rule is referenced — good — but unlike 02-03, this plan doesn't enumerate the fallback (pasta per-container + published ports) and its effect on `http://remnawave:3000` DNS-based wiring between backend/sub-page. If A3 fails, the sub-page `REMNAWAVE_PANEL_URL=http://remnawave:3000` (02-09) changes shape too.
- LOW: `HealthCmd=pg_isready -U remnawave -d remnawave` rendered literals — fine — but the plan should state the values come from `xvpn_panel_postgres_user`/`_db` so an operator override doesn't silently break the healthcheck.
- LOW: `Ulimit=nofile=1048576` on rootless — Podman may clamp to the user's systemd limits; the VM tier will reveal it, but it's worth a flagged note.

**Suggestions**
- After 02-07 lands, update this plan's verify_panel contract: make the checksum comparison input-driven (`xvpn_verify_secrets_checksum_file`), so the rotation case can repoint it exactly as 02-06 does for the token checksum.
- Add `systemd` user-manager `DefaultLimitNOFILE` check to the VM diagnostics if the ulimit assertion fails.

**Risk Assessment** — MEDIUM. Stack wiring is solid; risk concentrated in A3 and the cross-plan checksum interaction.

---

## 02-06

**Summary** — Loopback bootstrap state machine (status → register/login → token create/validate → 0600 token file) placed correctly between stack and route publication (PANEL-03 race closed by task order, enforced by a grep gate). Recovery/failure branches are executed in the VM tier, including old-token revocation and single-entry assertions.

**Strengths**
- The status state machine handles the ambiguous both-false case (Pitfall 5) with distinct failure messages and a retry window, and register is strictly gated on `isRegisterAllowed` — the second-admin threat (T-02-17) is properly closed.
- Token recovery implemented as delete-by-name → create → file write, with the side_effect proving old token rejected and exactly one entry remains; the token checksum file is *re-pointed* after recovery (`force: true`) so post-reboot verify stays consistent — exactly the mechanism 02-07 forgot (see below).
- The acceptance gates are unusually good: task-order gate (bootstrap.yml line < routes.yml line), `grep -Ec 'delegate_to|fetch:|cacheable' == 0` as a structural no-exfiltration guard, and minimum no_log/forwarded-header counts.
- Contract-first execution: the executor must read the 3.4.11 libs/contract files and record username schema/HTTP codes before writing tasks (A9/A11 flagged).

**Concerns**
- MEDIUM: Task 2's recovery block re-runs `include_role xvpn.remnawave.panel` inside side_effect — the full role, including quadlet deployment and (after 02-09) subpage. This is the plan most exposed to cumulative VM-tier runtime; combined with the later insertions from 02-07/02-09, side_effect grows into a long serial block. molecule-vm has `timeout-minutes: 120` (`.github/workflows/molecule-vm.yml:21`) — no stated budget for the side_effect additions.
- MEDIUM: token validity probe uses `GET /api/nodes` with the API token (A9: "GET /api/nodes accepts an API token" — to be confirmed). If tokens are restricted from some routes, a different probe route is needed; the plan already mandates contract confirmation, so this is contained, but the *verify* in verify_panel.yml hardcodes the same route — both must change together.
- LOW: login failure branch accepts status codes [200,201,400,401,403] then fails on non-2xx with the D-10 message — good — but a 5xx (backend crash mid-login) also lands in the "password changed or login disabled" message, which would mislead. Distinguish 5xx ("backend error, retry/fail plainly") from 401/403 (D-10 message).

**Suggestions**
- Add a rough VM-runtime budget note to the plan (e.g., "side_effect additions must keep the run under ~30 min"), so the 120-min platform timeout isn't discovered at 02-09.
- Parameterize the token-validation route (`xvpn_panel_api_token_probe_route`, default the nodes route) so verify and bootstrap share one definition.

**Risk Assessment** — MEDIUM. Well-designed; risks are runtime accumulation and the unconfirmed-but-flagged token probe route.

---

## 02-07

**Summary** — The phase's centerpiece: gate routers in `panel-routes.yml.j2`, admin-url file, the full positive/negative matrix in the VM tier, log-masking proofs over HTTPS and HTTP, gate rotation with old-cookie invalidation, and the D-02 wording amendments. The design follows the executed spike faithfully (noop@internal + headers + redirectRegex, priority-ordered routers, anchored case-insensitive auth exclusion).

**Strengths**
- The negative matrix is the strongest part of the whole phase plan set: path-normalization variants, encoding, cookie anchoring (`(^|;) ?`), `/api/authx` positive control, HTTP-entrypoint gate request, and variant-request log-line proofs identified by UA — each mapped to a threat ID and a grep-able acceptance gate.
- Rotation coupling (path rotation regenerates cookie value, Plan 02-04) is proven end-to-end in the VM (`gate-rotation-old-cookie`) — the threat that matters (stolen cookie survives rotation) is actually tested, not asserted.
- D-02 wording edits are scoped, single-sentence, and verify themselves against both files; the `human-check` deferral to end-of-phase is consistent with `human_verify_mode: end-of-phase`.
- Pre-authorized fallback (D-05 decoy-cookie issuer) has a precise trigger ("only if the VM tier proves the primary broken") and evidence-recording duty.

**Concerns**
- **HIGH (cross-plan defect): the gate rotation breaks 02-05's secrets checksum assertion.** Sequence: 02-05 records `secrets_checksum_after_first_converge` (converge, `force: false`); `verify_panel.yml` asserts "secrets file checksum equals the one recorded after the first converge" and is included from `vm/verify.yml` (after reboot) as well as pre-reboot in side_effect. Plan 02-07's `gate-rotation-old-cookie` re-runs the panel role with a new `xvpn_panel_gate_path`, which rewrites `panel-secrets.yml` (02-04: override replaces stored value) — so the post-reboot `verify_panel.yml` include compares the recorded *pre-rotation* checksum against the *rotated* file and fails. 02-06 solved exactly this pattern for the token (overwrite `token_checksum_after_first_converge` with `force: true` after recovery); 02-07 must do the same for `secrets_checksum_after_first_converge` after rotation, or 02-05 must make the checksum file an input. Neither plan says this. As written, the first green-gate VM run after 02-07 turns red at the post-reboot verify.
- MEDIUM: the rotation case relies on file-provider `watch: true` reload (A6, until 12×5 s). If A6 failed in 02-03 and the restart-on-change fallback was taken, the rotation case still passes (role restart), so no issue — but the 60 s budget is thin if image reload is slow; acceptable.
- MEDIUM: `sub-public-no-cookie` asserts "status not 400 and body differs from decoy" — loose by design, but a Traefik 404 ("page not found") also differs from the decoy; the plan should assert the body is *not* Traefik's 404 body either (02-09 does this for the sub domain; mirror it here).
- LOW: `xvpn-panel-cookie` at priority 500 matches *any* path with the cookie — including `/api/auth/*` (intended) — but also the decoy-only paths; correct. No issue, just confirming the matrix covers it.

**Suggestions**
- Fix the checksum interaction: after the rotation case, rewrite `/var/lib/xvpn-molecule/secrets_checksum_after_first_converge` with `force: true` (mirroring 02-06), and add an acceptance criterion for it in 02-07.
- Tighten `sub-public-no-cookie` to "body differs from decoy AND from Traefik's 404 body AND status in [200,404]" with the status recorded.
- In the wording task, add a one-line note to REQUIREMENTS pointing at D-19's fail2ban trade-off so Phase 5 planners find it in-context.

**Risk Assessment** — MEDIUM (dropping from HIGH once the checksum defect is fixed). The gate itself is spike-verified with an unusually complete test matrix; the defect found is a test-harness integration bug, not a design flaw.

---

## 02-08

**Summary** — Two heavyweight additions in one plan: (1) a push-triggered gate regression that renders the *production* templates and replays the verify_gate case ids against the pinned Traefik image + Pebble on the runner, and (2) the D-20 gitleaks secret scan with a 15-case self-test. Both are valuable; the gitleaks half is the most intricate spec in the phase and was at least prototyped by the planner.

**Strengths**
- "Test the production template, not a copy" is enforced by grep (`panel-routes.yml.j2` in render.yml) — the right guard against the classic drift-to-copy failure mode.
- The gitleaks rule design shows real understanding of the tool: separator-led capture groups to defeat the upstream global path allowlist, `--exit-code 3` so tool errors never count as detections, `--ignore-gitleaks-allow`, no `.gitleaksignore`/baseline, tracked-tree scan including `.planning/`, runtime-assembled fixture key names so check.sh never self-flags. The separator-led-group trick is the kind of thing that only survives if someone actually ran it — and the plan says the planner did (five runs, fresh values).
- Self-test enumerates ids and expected statuses as data (`<id>:<expected>`), and the acceptance loop cross-checks the enumeration — good against silent case drift.
- QA-05 for the new workflow is covered (`acme-v02` must not appear in render.yml).

**Concerns**
- HIGH (complexity, not correctness): this plan carries the full gate matrix *and* the gitleaks subsystem; Task 3 alone has ~18 acceptance criteria and a 15-case self-test. If any single gitleaks-case expectation drifts (e.g., upstream default-rule interplay with a fixture), debugging happens inside a CI workflow on a pinned tool with a hand-built config. Splitting Task 3 into its own plan (it's logically independent of the gate regression) would cut blast radius; alternatively ship the self-test cases as a small script invoked by check.sh so failures name the case in isolation.
- MEDIUM: the tracked-tree scan runs on every `check.sh` invocation (local and CI), and the self-test adds 15 gitleaks spawns + one full scan. On the lint workflow this is fine; for local dev loops it doubles check.sh cost. D-20 allows local skip only when gitleaks is absent — once installed, every local run pays. Acceptable, worth noting.
- MEDIUM: `scripts/gate/run.sh` starts rootful podman `--network host` on the runner. GitHub-hosted runners permit this, but the stub servers on :3000/:18080 and Pebble on :8080/:15000 all assume nothing else occupies those ports; the runner is ephemeral so this holds, but an explicit port pre-flight in run.sh would give clearer failures.
- LOW: `.gitleaks.toml` ships in the built collection (not in `galaxy.yml` `build_ignore`, verified: only `.github`, `.planning`, `.claude`, `.devcontainer`, `.ansible`, `.venv`, `scripts`, `*.tar.gz`). Harmless for Galaxy users but it publishes internal rule scope; consider adding it to build_ignore.
- LOW: the deliberate-break proof is "locally or in a throwaway CI commit" — ambiguous; prefer a named scratch branch + recorded run URL, since a throwaway commit on main pollutes the trunk history this process otherwise keeps clean.

**Suggestions**
- Split Task 3 into a follow-up plan (it has no wave-dependency on the gate workflow) or at minimum into a separately-committed sequence so a red gitleaks case doesn't block the gate-workflow delivery.
- Add `.gitleaks.toml` to `galaxy.yml` build_ignore.
- In run.sh, fail fast with a port-in-use check before starting Pebble/stubs/Traefik.

**Risk Assessment** — MEDIUM-HIGH (execution complexity), LOW for design correctness. The configuration was prototyped, which materially de-risks it, but the plan density is at the edge of what one autonomous executor run can carry reliably.

---

## 02-09

**Summary** — Subscription page as part of the panel role (D-17): env from the bootstrap token, own Quadlet unit on the panel network, restart on token change, own route file, and SUB-02 proven by a two-probe authenticated exchange with a *fixed* success marker (`data-panel` base64 contract) and a fixed rejected-token outcome (502, no attribute). The verified-contract approach (frontmatter record from upstream source) is the right way to make an integration test non-flaky.

**Strengths**
- Probe B's marker is derived from source, not observation: `data-panel` attribute → base64 → JSON with `isFound`, `username`, `shortUuid` — plus the explicit "no fallback probe; contradict the contract → checkpoint:decision" rule. This is the strongest anti-weakening stance in the phase.
- The negative control (wrong token of correct JWT shape → 502) closes the "test passes trivially" hole, and the InvocationID-based proof that the *role* (not the harness) restarts the page on token change directly evidences the Pitfall 7 restart-on-change wiring.
- Ordering gates again enforced structurally (bootstrap line < subpage line in `tasks/main.yml`); container tier correctly degrades (env skipped without token, unit still rendered/dry-run).
- Token handling stays on-host (probe A reads via `podman exec printenv` on the VM, `no_log`), consistent with D-09's "never on the controller".

**Concerns**
- MEDIUM: `HealthCmd=curl ...` depends on curl existing in the 8.0.1 image (A13). The plan's fallback ("use the tool the image actually ships") is fine, but the acceptance criterion `grep -c 'INTERNAL_JWT_SECRET' == 0` doesn't cover healthcheck drift; if the executor swaps to `wget`, nothing breaks, just note the SUMMARY requirement is only implied.
- MEDIUM: probe B's 502 expectation depends on sub-page "destroys the socket" behavior surfacing as 502 *through Traefik*. That's Traefik's upstream-error translation — plausible and research-attested, but if the page instead lingers and answers 500/503, the fixed outcome fails and forces a checkpoint. That's by design (good), but expect this to be the most likely checkpoint trigger in the plan.
- LOW: the wrong-token block runs *after* the recovery block and *before* the reboot; the post-reboot verify uses the restored real token — ordering is correct, but the plan should pin that the wrong-token block must leave `subpage.env` byte-identical to the pre-control state (the role re-run achieves it; assert env checksum before/after to make it explicit).
- LOW: `xvpn-molecule-probe` user creation is a write to the test panel using the full-scope token — accepted as T-02-30, fine.

**Suggestions**
- Add the env-checksum-unchanged assertion around the wrong-token control.
- Record in the SUMMARY the exact 502-translation observed (Traefik error page vs empty reply) so Phase 5 troubleshooting docs have it.

**Risk Assessment** — MEDIUM. Contract-verified design with honest failure rules; the main risk is the live 8.0.1 behavior diverging from the fixed outcomes, which triggers the designed checkpoint rather than silent breakage.

---

## 02-10

**Summary** — Small, well-scoped closer: the D-17 toggle's disabled path (remove unit/env/route, `SUB_PUBLIC_DOMAIN` fallback already handled in 02-05), a container-tier toggle case, the README "Panel host" section with no secret values, and the all-tiers-green phase close. Split from 02-09 was the right call.

**Strengths**
- The disabled branch is genuinely end-to-end (quadlet `state: absent`, env file absent, route absent) and the container tier asserts all of it; the quadlet entry point's absent-spec handling exists (`roles/podman_rootless/tasks/quadlet.yml:31-36`), so the interface claim is verified.
- README content enumeration covers every operator-facing decision (D-02 decoy, D-06 admin-url, D-10 no-rotation, SameSite trade-off, ports) and the check_secrets scan guards the no-secrets clause mechanically (`<from vault>` literal is scan-safe).
- Final verify runs *all four* CI tiers for the final HEAD — a real phase gate, not a per-plan gate.

**Concerns**
- MEDIUM: toggling off in the container tier asserts removal, but the toggle-back-on case runs with `xvpn_panel_activate: false` — so the VM tier only ever re-proves the default-on path; the "switch back to true restores" claim is never exercised with active units. The assumption block acknowledges this; acceptable for v1, but note that a stale running container after toggle-off (unit file removed while the user manager still runs the old unit) is untested — a real-world operator path.
- LOW: the disabled branch removes `subpage.env` and the unit file but does not stop/disable the running `remnawave-subscription-page.service` explicitly (LSR absent handling typically does daemon-reload; whether it stops a running unit depends on LSR behavior). If LSR only removes the file, the page keeps serving until reboot — worth an explicit `systemd_service state: stopped` before the spec removal, or a verify assertion in the VM tier.
- LOW: README insertion-point greps (`Preflight checks` < `Panel host` < `Development`) are brittle to future reorganization but fine now.

**Suggestions**
- In the disabled branch, stop `remnawave-subscription-page.service` explicitly before removing the unit file, and (VM tier, later phase) verify the unit is inactive after toggle-off.
- Add a README line pointing to `admin-url` retrieval (`cat` on the Panel host) — the plan implies it; make it an acceptance criterion if desired.

**Risk Assessment** — LOW. The only substantive gap (running-unit teardown on toggle-off) is narrow and easily patched.

---

## Cross-Plan Findings (summary)

1. **HIGH — 02-05 ↔ 02-07 secrets checksum collision.** The post-reboot `verify_panel.yml` assertion "secrets file checksum equals the one recorded after the first converge" will fail once 02-07's gate rotation rewrites `panel-secrets.yml` in side_effect. Fix: 02-07 must re-point `secrets_checksum_after_first_converge` (`force: true`) after rotation — the exact mechanism 02-06 already uses for `token_checksum_after_first_converge`. Evidence: 02-05 verify_panel truths + `vm/converge.yml:58-65` recording pattern + 02-06 Task 2 (`force: true` rewrite) + 02-07 Task 2 rotation re-running the role with a new gate path (02-04 merge rule rewrites the stored file).
2. **MEDIUM — pasta fallback blast radius under-specified (02-03).** The escalation menu lists pasta as option (B) without noting it invalidates loopback `PublishPort` assumptions (02-05) and the real-IP probe semantics (02-03 itself).
3. **MEDIUM — side_effect VM runtime accumulation (02-06/02-07/02-09).** Three plans each append serial blocks before the reboot; no runtime budget exists against `molecule-vm` `timeout-minutes: 120`.
4. **MEDIUM — plan density (02-08).** Gate regression + gitleaks subsystem in one plan; Task 3 is separable and should be split.
5. **LOW — coverage**: all Phase 2 requirements (EDGE-01..03, PANEL-01..06, SUB-01/02, QA-05, DOC-04) map to plans; D-19/D-20 checker decisions are consistently implemented (D-19: `RequestPath: drop` in 02-01, UA-based probes in 02-03/02-07/02-08; D-20: pinned gitleaks in 02-08). No unmapped work found.

**Overall risk: MEDIUM** — the phase is exceptionally well-fenced (spike-verified gate, mutation-tested guards, executed negative matrices, checkpoint discipline for every unproven assumption), but one concrete cross-plan test-harness bug (finding 1) will turn CI red if unfixed, and 02-03/02-08 carry the bulk of the platform/complexity risk.

---

## Qwen Review

---

# Cross-AI Plan Review: Phase 2 — Panel за Traefik с защищённым входом

## 02-01

### Summary
Plan 02-01 establishes the `edge` role — Traefik v3.7.20 + decoy nginx under `rw-edge` with a drop-in route interface. It is well-structured, correctly reuses the Phase 1 quadlet entry point, and includes a CI helper (`ci_watch.sh`). The plan is appropriately scoped for Wave 1.

### Strengths
- **Correct reuse of Phase 1 patterns**: `tasks_from: quadlet` with absolute `template_src`, generator dry-run, user-scope systemd restart — all verified against `roles/podman_rootless/tasks/quadlet.yml:1-48` and `quadlet_validate.yml`.
- **D-19 access log masking is concrete**: `RequestPath: drop`, `headers.defaultMode: drop`, single `User-Agent: keep` — directly implementable from the Traefik v3.7 static config reference.
- **Input guards are specific**: route name regex, absolute path check, ACME CA validation — all with `quiet: true` asserts matching the style in `roles/common/tasks/main.yml:1-18`.
- **`ci_watch.sh` dispatch-and-watch pattern** correctly handles `molecule-vm` being `workflow_dispatch`-only (verified: `.github/workflows/molecule-vm.yml:5-8` shows triggers are `pull_request`, `schedule`, `workflow_dispatch` — no `push`).

### Concerns
- **MEDIUM — `setype: container_file_t` in `route.yml`**: The plan writes drop-in route files with `setype: container_file_t`. However, the Traefik container bind-mounts the dynamic directory `:ro,Z` — the `:Z` flag relabels for single-container use. If the file is created with `container_file_t` by root (Ansible), and the directory is then `:Z`-labeled, there could be a label conflict or redundant relabel. The plan should clarify whether `setype` is needed at all given the `:Z` mount, or whether it's only needed when the file provider reads without relabel.
- **LOW — `ci_watch.sh` HEAD check**: The plan requires `git ls-remote origin refs/heads/main` to match HEAD. But the plan says "push to origin main" — there's a TOCTOU race: the push could fail after the check passes, or another push could interleave. This is acceptable for CI helper use but worth noting.
- **LOW — estimate confidence "low"**: 14 files in one task is aggressive. The plan acknowledges this but doesn't calibrate.

### Suggestions
- Clarify the SELinux labeling strategy for dynamic dir files: either rely on `:Z` relabel (remove `setype`) or document why both are needed.
- Consider splitting Task 1 and Task 2 into separate commits earlier — the decoy is independent of the Traefik static config.

### Risk Assessment
**LOW** — Well-scoped, builds on proven Phase 1 patterns, no novel untested mechanisms.

---

## 02-02

### Summary
Plan 02-02 creates the `panel` role skeleton with Panel-domain routes, the `playbooks/panel.yml` + `site.yml`, switches the container tier to the real playbook, and adds the QA-05 static guard. Clean and focused.

### Strengths
- **Correct playbook structure**: mirrors `playbooks/foundation.yml` (verified: two plays, preflight + main, same role order).
- **QA-05 static guard (`check_acme_ca`)** is mutation-tested — a strong enforcement mechanism that catches regressions before they reach CI.
- **`xvpn_verify_quadlet_unit` parameterization** of `verify_rootless.yml` is a clean cross-phase contract extension.
- **Negative case `panel-placeholder-domain`** catches the most likely operator error early.

### Concerns
- **MEDIUM — `xvpn_panel_domain` regex allows very long TLDs**: The regex `^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?[.])+[a-z]{2,63}$` allows TLDs up to 63 chars. While technically valid per DNS specs, real TLDs are ≤24 chars. Not a bug, but overly permissive. LOW risk.
- **MEDIUM — Container tier `import_playbook` with `xvpn_edge_activate: false`**: The plan imports `playbooks/panel.yml` which runs preflight. But preflight includes DNS checks (`xvpn_preflight_dns_check`). The plan sets `xvpn_preflight_dns_check: false` — correct. However, preflight also checks ports 80/443 ownership. In the container tier with `xvpn_edge_activate: false`, nothing binds those ports, so the port check should pass. But the `xvpn_preflight_service_users` includes `rw-panel` and `rw-node` which don't exist yet in the container tier. The preflight role's port check (`roles/preflight/tasks/main.yml`) accepts listeners from those users — if the users don't exist, `getent` would fail. Need to verify the preflight role handles missing users gracefully. Looking at `roles/preflight/defaults/main.yml:14-17`, the default includes `rw-panel` and `rw-node` — but the preflight tasks likely do a `getent` with `fail_key: false`. This should be fine.
- **LOW — `check_acme_ca` scans converge files + vars files**: The plan says it reads `vars/*.yml` of the same scenario directory. But the current `extensions/molecule/container/converge.yml` doesn't have a `vars/` directory. The plan creates `extensions/molecule/vm/vars/panel.yml` in Plan 02-03. The guard must handle the case where no vars directory exists.

### Suggestions
- Verify that `roles/preflight` handles non-existent service users in `xvpn_preflight_service_users` gracefully (it should, given `fail_key: false` pattern in `check_dns.yml`).
- The `check_acme_ca` implementation should gracefully handle scenarios with no `vars/` subdirectory.

### Risk Assessment
**LOW** — Straightforward wiring plan with good static guards.

---

## 02-03

### Summary
Plan 02-03 switches the VM tier to the real playbook with Pebble and proves HTTPS end-to-end. This is the highest-risk plan in the phase — it's the first SELinux-enforcing proof of `Network=host` Traefik.

### Strengths
- **Pebble pins are sha256-verified** with exact values from the GitHub release — supply chain is tight.
- **Escalation path is explicit**: on AVC denial, `checkpoint:decision` with evidence, never a silent boolean. This is critical for maintaining the SELinux enforcing invariant.
- **Real-IP proof via User-Agent** (D-19) is clever: since paths are never logged, the probe uses a unique `User-Agent` header to find its log line. This avoids the path-leakage problem entirely.
- **Idempotence + reboot + zero-AVC** is the correct proof sequence.

### Concerns
- **HIGH — `Network=host` + SELinux AVC is the single biggest risk**: The plan acknowledges this (assumptions A1/A2, RESEARCH Open Question 1) and has an escalation path. However, if the first VM run fails with AVC, the entire phase blocks. The plan should consider a **parallel spike** — running a quick `Network=host` Traefik probe in the VM prepare phase *before* the full converge, to fail fast with AVC evidence rather than after a 10-minute converge.
- **MEDIUM — Pebble `httpPort: 80` conflict**: The plan sets Pebble's `httpPort: 80` for ACME challenge validation. But Traefik also binds `:80`. The RESEARCH Pitfall 9 says challtestsrv handles the challenge responses, and Pebble's `httpPort` is the port Pebble's VA uses to *validate* challenges — it connects to the challenge responder (challtestsrv on 5002 by default). Wait — re-reading: the plan says Pebble config `"httpPort": 80` on the VM. But if Traefik is on 80 and Pebble VA tries to connect to port 80 to validate, it would hit Traefik, not challtestsrv. The RESEARCH says challtestsrv binds 5002 by default, and Pebble's VA is configured with `-dnsserver 127.0.0.1:8053` to resolve to challtestsrv. But the ACME HTTP-01 challenge validation goes: Pebble VA → resolves domain → connects to port 80 of the resolved IP. If the domain resolves to the VM IP and Traefik is on 80, Traefik receives the challenge request and proxies it... where? The ACME challenge router in Traefik is internal and answers directly. So Traefik *is* the challenge responder on port 80. Pebble's `httpPort: 80` in the config is the port the VA uses to send challenges — which is 80, hitting Traefik. This should work because Traefik's ACME challenge router handles `.well-known/acme-challenge/` on `:80`. **This is correct.**
- **MEDIUM — `podman logs` as rw-edge for access log verification**: The plan assumes `podman logs traefik` works as rw-edge (A4). If the k8s-file log driver writes to a path that requires different permissions, the verify fails. The plan has a fallback (bind-mounted log file) but this should be tested early.
- **LOW — IPv4-only real-IP proof**: Explicitly acknowledged in assumptions. Acceptable for v1.

### Suggestions
- Add a pre-converge SELinux smoke test in `prepare.yml`: start a minimal `Network=host` container that binds 80/443 and check for AVC before the full converge. This fails fast.
- Consider adding `audit2allow` output to the checkpoint:decision evidence template.

### Risk Assessment
**MEDIUM-HIGH** — The SELinux/Network=host interaction is untested and could block the phase. The escalation path is well-defined, which mitigates the risk.

---

## 02-04

### Summary
Plan 02-04 implements generate-once secrets with divergence/loss/placeholder guards and the static `no_log` check. This is a critical plan — the secrets file is the D-07 interface that Plans 02-05–02-09 and Phase 3 depend on.

### Strengths
- **Generate-once semantics are well-designed**: read existing → generate missing → merge with overrides → write. The `to_nice_yaml` ensures deterministic output for idempotence.
- **Password generation with class guarantees** (Pitfall 3): segmented generation (lower + upper + digit + filler) with shuffle is the correct approach. The plan explicitly avoids relying on `lookup('password')` to guarantee character classes.
- **D-10 divergence check** is clear: vault override ≠ stored value → fail with key name, never value.
- **Gate rotation coupling** (D-06): path rotation regenerates cookie value — this is a subtle but important security property.
- **`check_no_log.py` static gate** is a strong enforcement mechanism. Walking tasks recursively through `block`/`rescue`/`always` with inherited `no_log` is correct.
- **Lost-secrets guard** (Pitfall 6): secrets file missing + DB volume exists → fail. Prevents accidental regeneration.

### Concerns
- **HIGH — `set_fact` with secrets in memory**: The plan holds all secrets in `xvpn_panel_secrets_generated` and `xvpn_panel_secrets` facts. While `no_log: true` prevents them from appearing in output, Ansible facts are accessible to any subsequent task. If a later task has a bug (e.g., `debug: var=hostvars`), secrets could leak. The plan mitigates this with `check_no_log.py` and the prohibition on `cacheable: true`, but the risk surface is larger than necessary. Consider whether the secrets could be passed directly to templates without an intermediate fact.
- **MEDIUM — `slurp` + `from_yaml` for reading the secrets file**: If the YAML file has comments or non-standard formatting, `from_yaml` might behave unexpectedly. The plan writes with `to_nice_yaml` which is clean, but an operator hand-edit could introduce issues. The placeholder asserts on stored values (Task 2) partially mitigate this.
- **MEDIUM — Lost-secrets guard path**: The plan checks `{{ xvpn_panel_home }}/.local/share/containers/storage/volumes/remnawave-db-data`. But the actual volume path for rootless Podman depends on the storage driver and configuration. The plan uses `VolumeName=remnawave-db-data` (Plan 02-05), which creates a named volume. The path `~/.local/share/containers/storage/volumes/remnawave-db-data` is correct for the default VFS/overlay driver, but if the storage driver is different, the path would differ. This should be verified in the VM tier.
- **LOW — 13 negative cases in one verify**: The container verify grows from 6 to 13 negative cases. This is a lot of block/rescue blocks. Consider whether some could be combined.

### Suggestions
- Verify the rootless Podman named volume path in the VM tier before relying on it for the lost-secrets guard.
- Consider adding a `check_mode: true` run that verifies the secrets generation logic without writing anything.
- The `check_no_log.py` should also check for `debug: var=xvpn_panel_secrets` patterns, not just module-level `no_log`.

### Risk Assessment
**MEDIUM** — The secrets design is sound but the in-memory fact handling and volume path assumption need verification.

---

## 02-05

### Summary
Plan 02-05 deploys the Panel stack (Postgres 18.4, Valkey 9, backend 3.4.11) as rootless Quadlet units. This is the core infrastructure plan.

### Strengths
- **Correct Quadlet unit shapes**: Network, volumes, containers with proper ordering (`Requires=`/`After=`), healthchecks, `Notify=healthy`. All keys verified against Podman 6.0.2 man page.
- **Env-file approach** (0600, rw-panel) is simpler and more auditable than Podman secrets.
- **Restart-on-change** (Pitfall 7): only restart the specific unit when its env file changes, not the whole stack.
- **Backend healthcheck on metrics port 3001** (Pitfall 1): correct — the main port 3000 destroys connections without forwarded headers.
- **Loopback-only publishing**: `PublishPort=127.0.0.1:3000:3000` only. Verify asserts no external exposure.

### Concerns
- **HIGH — Rootless user-defined Quadlet network + PublishPort (A3)**: Phase 1 only proved `Network=pasta` + PublishPort. The `Network=remnawave.network` (user-defined bridge) + `PublishPort=127.0.0.1:3000:3000` combination is untested on Podman 6/EL10. If this fails, the fallback (pasta with published ports) loses inter-container DNS name resolution (`remnawave-db` as hostname). The plan should have a clear fallback strategy.
- **MEDIUM — Valkey socket permissions**: The plan sets `--unixsocketperm 777` on the Valkey socket. This is needed because the backend container runs as a different uid in the user namespace. But `777` is very permissive. Consider whether a shared group or `--unixsocketperm 770` with a common group would be safer.
- **MEDIUM — `FRONT_END_DOMAIN=*`**: The plan sets this to `*` based on RESEARCH analysis of the CORS config. If the backend's CORS implementation changes in a future version, this could become a security issue. The plan should document this as a known deviation from the `.env.sample` (which typically has a specific domain).
- **LOW — Postgres `ShmSize=512m`**: This is a large shared memory allocation for a rootless container. Verify the host has sufficient `/dev/shm` or that Podman handles this correctly in rootless mode.

### Suggestions
- Test the user-defined network + PublishPort combination early in the VM tier, before building the full stack.
- Consider documenting the `FRONT_END_DOMAIN=*` decision in the README as a known configuration.
- Add a `ss` check for the Valkey socket to verify it's not accessible outside the container.

### Risk Assessment
**MEDIUM** — The stack design is solid, but the untested Podman networking combination is a risk.

---

## 02-06

### Summary
Plan 02-06 implements the loopback bootstrap state machine: status → register/login → token create → 0600 token file. This is the bridge between the Panel stack and the public-facing gate.

### Strengths
- **State machine is correct**: `isRegisterAllowed` → register; `isLoginAllowed` → login; both false → retry/fail. Matches the upstream source code analysis.
- **Forwarded headers on every request** (Pitfall 1): `X-Forwarded-For: 127.0.0.1` and `X-Forwarded-Proto: https` are mandatory. The plan enforces this consistently.
- **Token recovery flow**: lost token file → delete by name → recreate. The old token is revoked. This is a clean self-healing mechanism.
- **Bootstrap before route publication** (PANEL-03): task ordering ensures the admin exists before the Panel is publicly reachable. This closes the first-admin race.
- **No controller-side token storage** (D-09): the token never leaves the Panel host. The acceptance gate greps for `delegate_to`, `fetch:`, `cacheable` — strong enforcement.

### Concerns
- **MEDIUM — HTTP status code ambiguity**: The plan accepts both 200 and 201 for register/login. The upstream contract files don't specify which. If the backend returns a different code (e.g., 204), the bootstrap would fail. The plan should log the actual status code on failure for debugging.
- **MEDIUM — Token creation race**: If two parallel runs hit the token creation branch simultaneously, both could create tokens. The plan acknowledges this (assumption) but has no lock. The "delete by name, create" pattern mitigates this — the second run would delete the first's token and create a new one. But the first run's token file might be written after the second run deletes it. This is a narrow race window and the plan's "next run converges" stance is acceptable.
- **LOW — `expiresInDays: 3650`**: 10-year token lifetime is very long. While acceptable for automation, consider documenting this as a known security trade-off.

### Suggestions
- Add the actual HTTP status code to the failure message for register/login.
- Consider adding a `--check` mode test that verifies the bootstrap state machine without making API calls.

### Risk Assessment
**LOW-MEDIUM** — The bootstrap logic is well-designed with correct ordering and recovery.

---

## 02-07

### Summary
Plan 02-07 implements the cookie/secret-path gate — the highest-risk feature of the phase. The gate is built on pure Traefik routers/middlewares (no plugins), verified by spike.

### Strengths
- **Spike-verified design**: The gate configuration was executed end-to-end in the research phase. The full positive/negative matrix was tested.
- **Case-insensitive auth exclusion** (`(?i)^/+api/+auth(/|$)`): correctly prevents bypass via `/API/AUTH/...`.
- **`allowEncoded*: false`** on both entrypoints: prevents encoded-character bypasses (`%61`, `%2F`).
- **`noop @internal` for the gate router**: the secret-path request doesn't appear in access logs. Combined with `RequestPath: drop` (D-19), this is defense in depth.
- **Gate rotation coupling**: path rotation regenerates cookie value, invalidating old cookies. This is a clean security property.
- **REQUIREMENTS/ROADMAP wording amendment** (D-02): correctly updates the requirement to match the implemented behavior (decoy instead of 404).

### Concerns
- **HIGH — Cookie regex anchoring**: The regex `(^|;) ?<name>=<value>($|;)` was tested with the stricter `(^|; )` variant in the spike. The plan uses the looser `(^|;) ?` form. While the plan says this accepts `a=b;gate=v` (no space), it also needs to be verified that it doesn't match `xgate=v` or `gate=v4`. The plan's negative test matrix includes these cases, which is good.
- **MEDIUM — SameSite=Strict consequences** (Pitfall 10): OAuth2/Telegram callbacks and cross-site links land on the decoy. The plan documents this and provides `xvpn_panel_gate_cookie_samesite=Lax` as an escape hatch. This is acceptable for v1 but should be prominently documented in the README.
- **MEDIUM — `human-check` in Task 1 with `autonomous: true`**: The plan includes a `<human-check>` tag for browser verification but marks the plan as `autonomous: true`. The human check is deferred to end-of-phase UAT (per `.planning/config.json` `workflow.human_verify_mode: end-of-phase`). This is correct but should be clearly communicated.
- **LOW — Gate path in redirect regex**: The `redirectRegex` pattern `^https://([^/]+)/<gate_path>$` uses the gate path literally. If the gate path contains regex-special characters, this would break. But the plan generates gate paths as `[A-Za-z0-9_]` only, so this is safe.

### Suggestions
- Prominently document the SameSite=Strict consequences in the README (Plan 02-10).
- Consider adding a `curl` test for the `Location` header value in the gate-sets-cookie verify case.

### Risk Assessment
**MEDIUM** — The gate design is spike-verified and well-tested, but the cookie regex and SameSite consequences need careful attention.

---

## 02-08

### Summary
Plan 02-08 turns the gate spike into a CI regression and adds the DOC-04 repository secret scan with gitleaks. This is the CI hardening plan.

### Strengths
- **Production template rendering**: The gate regression renders the actual `traefik.yml.j2`, `00-edge.yml.j2`, and `panel-routes.yml.j2` templates — not hand-maintained copies. This catches template regressions.
- **gitleaks v8.30.1 with sha256 verification**: supply chain is tight. The self-test with 15 cases (13 leak, 2 clean) is thorough.
- **`.gitleaks.toml` design**: upstream default rules + project-specific rules for `xvpn_*` secret keys and URL userinfo. The fixture-scoped allowlist (only `scripts/gate/` and `extensions/molecule/` with marker comment) is minimal and correct.
- **Deliberate-break proof**: the plan requires proving that a corrupted regex fails the gate with a case ID. This is excellent regression testing.
- **`--ignore-gitleaks-allow`**: inline `gitleaks:allow` comments are ignored, preventing accidental suppression.

### Concerns
- **HIGH — gitleaks self-test complexity**: 15 self-test cases with runtime-generated random values, base64 encoding, and specific constraint satisfaction (e.g., "regenerated until it contains a '+', at least one more '/', an upper-case letter and a digit"). This is a lot of bash logic that could itself have bugs. The plan should be prepared for the self-test to be the primary source of CI flakiness.
- **MEDIUM — `gitleaks dir` on a copy of tracked files**: The plan copies tracked files to a temp dir and scans there. This misses untracked files that might contain secrets (e.g., a newly created file not yet `git add`-ed). However, the plan explicitly chooses this over `gitleaks dir` on the repo root to avoid scanning `.ansible/collections` and `.venv`. The trade-off is documented and acceptable.
- **MEDIUM — Gate workflow on `ubuntu-24.04`**: The plan assumes rootful Podman on the GitHub runner can run `--network host` next to Pebble. SELinux is not enforced there, so this covers routing semantics only. The VM tier remains the SELinux proof. This is correct but means the gate workflow doesn't prove SELinux compatibility.
- **LOW — gitleaks version pin maintenance**: The plan acknowledges the pin needs manual updates. Consider adding a comment in the plan about a future automation (e.g., Dependabot for gitleaks).

### Suggestions
- Consider simplifying the self-test by using a smaller set of high-value cases (e.g., 8 instead of 15) and moving the rest to a separate integration test.
- Add a timeout to the gate workflow step to prevent hanging on CI.

### Risk Assessment
**MEDIUM** — The CI regression is well-designed but the gitleaks self-test complexity is a flakiness risk.

---

## 02-09

### Summary
Plan 02-09 adds the subscription page on its own domain, authenticated to the Panel with the bootstrap token. The plan includes an authenticated probe (SUB-02) and a wrong-token negative control.

### Strengths
- **VERIFIED CONTRACT in frontmatter**: The plan pins the exact success marker (`data-panel="<base64>"` with specific JSON fields) and rejected-token outcome (HTTP 502). This eliminates ambiguity in the probe.
- **Probe A + Probe B**: two independent proofs — token accepted by Panel API (A), and page performs authenticated lookup (B). Both must pass.
- **Wrong-token negative control**: deliberately wrong token → both probes fail → role re-run restores → both probes pass. This proves the token wiring is real, not accidental.
- **`http://remnawave:3000` URL**: the page adds forwarded headers itself when the URL starts with `http://`. This is verified from upstream source.
- **No `INTERNAL_JWT_SECRET` in env**: the image entrypoint generates it. Correct.

### Concerns
- **HIGH — subscription-page 8.0.1 + backend 3.4.11 compatibility (A8)**: The plan acknowledges the contract version mismatch (page pins contract 3.1.1, backend ships 3.4.17). If the pair is incompatible, the page exits at startup. The plan has a `checkpoint:decision` fallback, but this could block the phase. The plan should verify compatibility early (e.g., in the container tier with a startup log check).
- **MEDIUM — Probe user creation in the VM**: The plan creates a test user `xvpn-molecule-probe` via the Panel API. This requires knowing the create-user contract (username 3-36 `[A-Za-z0-9_-]`, required fields). The plan says the executor reads this from `libs/contract` before writing the tasks. If the contract is different from expected, the probe fails.
- **MEDIUM — `podman exec` for Probe A**: Reading `REMNAWAVE_API_TOKEN` from the running container via `podman exec printenv` is fragile — the container might not be running, or the env var might not be set. The plan handles this with `failed_when: false`, but the probe could give false negatives.
- **LOW — Sub-page healthcheck**: The plan uses `curl -fsS -o /dev/null --max-time 2 http://127.0.0.1:<port>/internal/health`. If the image doesn't have `curl` (A13), the healthcheck fails. The plan says to use whatever tool the image ships.

### Suggestions
- Verify subscription-page 8.0.1 + backend 3.4.11 compatibility as early as possible (container tier startup log check).
- Consider adding a fallback probe (startup log line `[OK] Connected to Remnawave v...`) if the authenticated probe fails due to contract mismatch.

### Risk Assessment
**MEDIUM-HIGH** — The contract version mismatch is a real risk that could block the phase.

---

## 02-10

### Summary
Plan 02-10 adds the subscription page disable toggle, the README "Panel host" section, and closes the phase with all CI tiers green. The smallest plan in the phase.

### Strengths
- **Clean toggle implementation**: `state: absent` for the unit, env file, and route file. The `SUB_PUBLIC_DOMAIN` fallback to `<panel-domain>/api/sub` when disabled is correct.
- **README without secret values**: only `<from vault>` placeholders. The `check_secrets` scan guards this.
- **Correct section placement**: between `### Preflight checks` and `## Development`, matching the existing README structure.

### Concerns
- **LOW — Toggle test in container tier only**: The toggle is tested in the container tier (render + dry-run) but not in the VM tier (full enable/disable cycle). The VM tier re-runs with the default (enabled). This is acceptable but means the disable path is not fully proven on a real host.
- **LOW — README completeness**: The plan lists many variables to document but doesn't include `xvpn_panel_api_token_days` or `xvpn_panel_bootstrap_retries`. These are advanced settings but should at least be mentioned.

### Suggestions
- Consider adding a VM-tier toggle test (disable → verify absence → enable → verify presence).
- Ensure the README documents the SameSite=Strict consequences prominently (from Plan 02-07).

### Risk Assessment
**LOW** — Small, well-scoped plan with minimal risk.

---

## Cross-Plan Observations

### Strengths (Phase-wide)
1. **Research-driven design**: Every major decision is backed by executed spikes or upstream source code analysis. The RESEARCH.md is exceptionally thorough.
2. **Defense in depth**: Multiple layers of guards — static (`check.sh`, `check_no_log.py`, `check_acme_ca`, gitleaks), runtime (negative test cases, assertion matrices), and CI (mutation testing, deliberate-break proofs).
3. **Consistent patterns**: All roles follow the same conventions (variable naming, assert style, Quadlet deployment, verify structure). This makes the codebase maintainable.
4. **Security-first approach**: `no_log` everywhere, secrets never on controller, SELinux enforcing invariant, no silent boolean additions, supply chain verification.
5. **Wave structure**: Each wave builds on the previous one, with clear dependencies. The phase can be stopped at any wave and still have a working (if incomplete) system.

### Concerns (Phase-wide)
1. **HIGH — Cumulative context pressure**: 10 plans, each 55-70% context estimate. By Plan 02-09, the executor must hold the entire phase in context. The wave structure helps, but later plans risk missing interactions with earlier ones.
2. **MEDIUM — SELinux `Network=host` is a single point of failure**: If `Network=host` Traefik fails under SELinux enforcing (Plan 02-03), the entire phase blocks. The escalation path is defined, but the fallback (pasta) loses functionality.
3. **MEDIUM — subscription-page/backend contract mismatch**: The 8.0.1 vs 3.4.11 version pair is untested and could fail at runtime (Plan 02-09).
4. **MEDIUM — Phase 2 is very large**: 10 plans covering edge, panel, secrets, stack, bootstrap, gate, CI regression, subscription page, and documentation. Consider whether this could be split into two phases (2a: edge + panel infrastructure, 2b: gate + subscription page).
5. **LOW — No rollback story**: If a later plan fails, there's no documented way to roll back to a previous wave's state. The idempotence guarantees help, but a partial phase completion could leave the system in an inconsistent state.

### Suggestions (Phase-wide)
1. Add a phase-level integration test that runs the full `playbooks/panel.yml` end-to-end in the VM tier after Plan 02-10, verifying all success criteria together.
2. Consider adding a `phase2-complete` tag that operators can use to run only the Phase 2 roles.
3. Document the known limitations (SameSite=Strict, no secret rotation, single full-scope token) in a "Known Limitations" section of the README.

### Overall Risk Assessment
**MEDIUM** — The phase is well-designed with thorough research and strong guards. The primary risks are the SELinux `Network=host` interaction and the subscription-page/backend contract mismatch, both of which have defined escalation paths. The phase's size and complexity are managed by the wave structure, but cumulative context pressure is a real concern for the executor.

---

## Consensus Summary

Both reviewers ran with repo access and cited `file:line` evidence (OpenCode densely, Qwen sparsely). Both rate the phase MEDIUM overall: the design is spike-verified and well-fenced, and the risk sits in platform assumptions (02-03, 02-05, 02-09) and in the density of 02-08.

### Agreed Strengths
- The gate design follows the executed spike: the negative matrix covers path normalization, encoding and cookie anchoring, and rotation proves that old cookies are invalidated (02-07).
- The escalation discipline for SELinux AVCs (`checkpoint:decision`, never a silent boolean) is inherited from Phase 1 (02-03).
- D-19 is applied consistently: the real-IP and log probes identify their lines by User-Agent, never by path (02-01, 02-03, 02-07).
- Static gates are mutation-tested: `check_acme_ca`, `check_no_log.py`, and the gitleaks self-test with a deliberate-break proof.
- Generate-once secrets include guards for divergence, loss and placeholders (02-04).
- 02-09 fixes the SUB-02 contract in the plan frontmatter and adds a negative control with a wrong token.

### Agreed Concerns
1. **HIGH: 02-08 is too dense.** The gate regression and the gitleaks subsystem (15 self-test cases) share one plan, so the self-test is a likely source of flakiness. Suggestion: split Task 3 into its own plan, or at least run the self-test from a separate script that reports which case failed.
2. **MEDIUM-HIGH: the fallback blast radius is not described (02-03, 02-05).** If `Network=host` gets AVCs and the escalation picks pasta (option B), or if A3 fails (user-defined network + loopback PublishPort), then loopback PublishPort, the `http://remnawave:3000` DNS wiring for the sub-page, and the EDGE-03 real-IP semantics all change. The escalation text should say these must be re-derived. Qwen also proposes an early SELinux smoke test in prepare.
3. **MEDIUM: compatibility of subscription-page 8.0.1 with backend 3.4.11 (02-09).** The 502 outcome for a wrong token and the startup itself are the most likely checkpoint triggers. A checkpoint exists, but nothing checks this early.
4. **LOW-MEDIUM: the VM tier never proves the disable-toggle path with active units (02-10).** OpenCode adds that the disabled branch does not explicitly stop the running `remnawave-subscription-page.service`.

### Single-Reviewer Findings Worth Acting On
- **HIGH (OpenCode, existence-class, confirmed by the orchestrator against the plan text):** `02-05-PLAN.md:132` records `secrets_checksum_after_first_converge` with `force: false`, and `verify_panel.yml` asserts it after the reboot. `02-07-PLAN.md:194` (`gate-rotation-old-cookie`) re-runs the panel role with a new `xvpn_panel_gate_path` before the reboot, which rewrites `panel-secrets.yml`. Unlike `02-06-PLAN.md:174` (the token checksum is overwritten with `force: true`), 02-07 does not update the recorded secrets checksum, so the post-reboot verify will fail. Fix: after the rotation, overwrite `secrets_checksum_after_first_converge` with `force: true` and add an acceptance criterion for that.
- MEDIUM (OpenCode): `ci_watch.sh` should treat a cancelled run (concurrency `cancel-in-progress`) as a retry, not as a code defect (02-01).
- MEDIUM (OpenCode): `sub-public-no-cookie` should also assert that the body is not Traefik's 404 (02-07).
- MEDIUM (OpenCode): the accumulated runtime of `side_effect` (02-06, 02-07, 02-09) has no budget set against `timeout-minutes: 120`.
- MEDIUM (OpenCode): 02-04 should fail loudly when the secrets file exists but cannot be parsed, instead of treating it as `{}`.
- LOW (OpenCode): add `.gitleaks.toml` to `build_ignore` in `galaxy.yml`; distinguish 5xx from 401/403 on login (02-06); assert that the env checksum is unchanged around the wrong-token control (02-09).
- LOW (Qwen): check whether `setype: container_file_t` and the `:Z` mount for the dynamic dir duplicate each other (02-01); `check_acme_ca` must not fail when there is no `vars/` (02-02).

### Divergent Views
- **Qwen HIGH, "secrets in set_fact" (02-04):** OpenCode does not consider this a problem. The plan already mitigates it with `no_log`, the `check_no_log.py` gate and the `cacheable` ban, so this reads as a judgment call and the risk is acceptable.
- **Qwen HIGH, "cookie regex anchoring" (02-07):** Qwen itself notes that the negative matrix covers `xgate=` and `gate=v4`, so this is not an open defect.
- **Qwen HIGH, "cumulative context pressure":** each plan is executed by a fresh executor with its own context, so the concern does not apply to the GSD execution model. Qwen's suggestion to split the phase into 2a/2b remains a matter of taste.
- Qwen considers the Pebble `httpPort: 80` setup correct after its own analysis; OpenCode raises no concern there.
