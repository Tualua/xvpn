---
phase: 1
reviewers: [opencode, qwen]
reviewed_at: 2026-11-24T01:45:45Z
reviewed_at_by_lane:
  qwen: 2026-11-23T15:25:32Z
  opencode: 2026-11-24T01:45:45Z
plans_reviewed: [01-01-PLAN.md, 01-02-PLAN.md, 01-03-PLAN.md, 01-04-PLAN.md, 01-05-PLAN.md, 01-06-PLAN.md, 01-07-PLAN.md, 01-08-PLAN.md, 01-09-PLAN.md, 01-10-PLAN.md, 01-11-PLAN.md, 01-12-PLAN.md]
models:
  opencode: "unknown"
  qwen: "unknown"
model_sources:
  opencode: "unknown"
  qwen: "unknown"
---

# Cross-AI Plan Review — Phase 1

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

> Re-run on 2026-11-24 after granting OpenCode `external_directory` read access to `~/.ansible/**` (the first run auto-rejected those reads and returned no output). Source-grounded: cites installed LSR 2.5.0 files by `path:line`.

# Cross-AI Plan Review — Phase 1 (12 plans)

**Verification basis:** the repo is greenfield (`/workspaces/xvpn` contains only `.planning/`, `.claude/`, `.devcontainer/` — confirmed via directory listing), so product-file claims were checked against the planning artifacts (`SKELETON.md`, `01-PATTERNS.md`, `01-CONTEXT.md`, `01-RESEARCH.md`) and, where plans assert external-role behavior, against the **actually installed** `fedora.linux_system_roles` 2.5.0 source in the devcontainer. Environment claims spot-checked: `ansible --version` = core 2.22.0, `ansible-lint` on PATH, no `yamllint`/`podman`/`molecule` on PATH, stale `~/.ansible/collections/ansible_collections/xvpn` scratch build present (matches Plan 01's housekeeping step exactly).

**Cross-plan checks performed:** dependency graph vs. waves (all consistent: 04/05←{03,09}; 06←05; 07←{04,05}; 08←06; 09←03; 10←{07,08,09}; 11←{04,05,06,07}; 12←{10,11}); requirement coverage (FND-01…07, QA-01…03 all mapped to ≥1 plan); file-ownership overlap between parallel waves (04 vs 05: disjoint; verified); verify-command executability (parsed each `<automated>` block for syntax/logic).

---

## 01-01

**Summary:** Solid tracer plan: collection identity + `podman_rootless` with the user/SELinux/sysctl/linger plumbing and the single LSR-backed `quadlet` entry point. Correctly sequences the fcontext equivalence before user creation and sysctl before any unit install.

**Strengths**
- Claims verified against real LSR source: `podman_pull_image: false` is genuinely required — `roles/podman/tasks/handle_images.yml:11` of the installed collection shows `force: true` on every image task. The plan's central mitigation is grounded, not assumed.
- The stale scratch-collection housekeeping step matches the actual devcontainer state (`~/.ansible/collections/ansible_collections/xvpn` exists right now) — Pitfall 12 handled concretely.
- argv-only commands, name-regex asserts before any account mutation, `nologin`/`password_lock` — the threat-model mitigations are executable gates, with the executed negative test deferred to Plan 04 (declared, not lost).
- uid>=1000 asserted both before `user` runs (explicit uid and pre-existing accounts) and after (allocated uid) — closes the "system account silently adopted" hole.

**Concerns**
- **MEDIUM:** `xvpn_podman_rootless_packages` includes `passt-selinux` unconditionally. Research states passt-selinux is "present on 10.3" — on an EL10.0/10.2 host (allowed by the 5.4 preflight floor) this package may be absent and `dnf` fails mid-converge. Plan 11's `verify_rootless.yml` even asserts `rpm -q passt passt-selinux` rc 0, hard-coding the 10.3 assumption into the shared verify.
- **LOW:** `user@<uid>.service` start + `wait_for /run/user/<uid>/systemd/private` rests on A2 (manager readiness); already flagged as a FLAGGED ASSUMPTION with VM-tier proof — acceptable.
- **LOW:** `verify` uses `grep -c 'podman_rootless'` on `--list-tasks` output; a task *name* containing the string would also count. Cosmetic, given the other gates.

**Suggestions**
- Guard `passt-selinux` (and the `rpm -q` verify) behind a package-presence check or drop it from the Phase-1 default set; Phase 2/3 roles that actually need pasta should own it.
- State in SUMMARY explicitly that `containers.podman` is a transitive-only pin (the plan already instructs this — keep it).

**Risk Assessment: LOW-MEDIUM** — well-grounded; the passt-selinux version skew is the only real defect vector.

---

## 01-02

**Summary:** Pins all five Galaxy collections exactly with a written justification header and a *blocking* human approval before the first install; builds the container Molecule scenario that drives the Plan-01 tracer with a clever getenforce test-double via sudo `secure_path`.

**Strengths**
- Supply-chain discipline is unusually good: pin justification → Galaxy API confirmation → blocking checkpoint → only then install (Task 3's verify is the first install). This closes a real gap (Galaxy not covered by the PyPI seam).
- The getenforce double + sudoers `secure_path` design solves a genuine problem (container tier shares the runner kernel with SELinux off) and asserts its own reachability ("fails loudly if the double is still not reached") — self-checking harness.
- I verified the container-tier approach against LSR source: `create_update_quadlet_spec.yml:116-118,147-151` gates all systemd user-scope tasks on `__podman_is_booted` **and** `__podman_activate_systemd_unit` — so `podman_activate_systemd_unit: false` plus `manage_user_manager: false` genuinely avoids user-bus calls in the container. The `activate: false` container-tier design is sound, not hopeful.

**Concerns**
- **MEDIUM:** the scenario's `test_sequence` includes `verify` from Plan 02, but `verify.yml` arrives in Plan 04 — the first green CI run (Plan 09) happens *before* verify exists. The FLAGGED ASSUMPTION plus pre-decided fallback (temporary sequence without verify) covers it, but consider just omitting `verify` from the initial sequence and letting Plan 04 add it; removes a known flake from the first-push path.
- **LOW:** `converge.yml` imports `playbooks/foundation.yml` via a relative path — Plan 05/07 later add plays to that file, silently changing what the container tier converges. This is intentional (tracer drifts forward), but Plan 10's guards don't pin the container converge's play inventory; acceptable.
- **LOW:** the acceptance gate `grep -c 'systemd: always' >= 2` is satisfied by one platform with two occurrences; a one-platform regression would pass.

**Suggestions**
- In Task 3, add a one-line comment in `molecule.yml` that `verify` is a placeholder until Plan 04, so the Plan-09 fallback decision is traceable.

**Risk Assessment: LOW** — the riskiest part (first install of root-running collections) is behind a blocking human gate.

---

## 01-03

**Summary:** Quality gate (`check.sh`) with a CI-hard yamllint rule, lint configs from verified scratch runs, GPL-3 LICENSE, README stub. The "missing linter in CI is a failure, never a skip" invariant is exactly right.

**Strengths**
- Lint-config claims are backed by the research session's actual scratch runs (Pitfalls 1–3 with verified fixes), and the `var-naming[no-role-prefix]` skip preserves the locked `xvpn_<role>_*` convention instead of renaming user-facing vars — correct trade-off, documented.
- The Task-1 verify constructs a yamllint-free PATH with shims so *both* branches (CI-fail / local-notice) execute regardless of local tooling — a well-engineered verify.

**Concerns**
- **MEDIUM:** `scripts/check.sh` syntax-checks "every existing `extensions/molecule/*/{converge,prepare,verify,side_effect,create,destroy}.yml`". Bash globs that match nothing expand to the literal pattern (no `nullglob` in the plan's `set -euo pipefail`), so at Plan-03 time — when `container/verify.yml` does not yet exist — `ansible-playbook --syntax-check extensions/molecule/container/verify.yml` fails and the whole gate goes red. Task 2's verify (`bash scripts/check.sh` must end `check.sh: OK`) would surface it, but the executor may "fix" it by excluding extensions entirely, silently dropping Molecule files from syntax coverage in later plans. The plan should specify the mechanism (nullglob or a per-file existence test) and an acceptance gate that extensions stay covered.
- **LOW:** Task-1's verify tolerates `local-missing-exit` non-zero "only because of lint findings Task 2 fixes" — but per the above it could equally be the glob bug; the fails_when wording can't distinguish them.

**Suggestions**
- Add an acceptance criterion like `bash -c 'shopt -s nullglob; ...'` or `for f in ...; do [ -e "$f" ] || continue; done` in the action text, plus a guard that at least one extensions playbook was syntax-checked.

**Risk Assessment: MEDIUM** — small defect, but it sits on the path every later plan uses as its verify, so it would be discovered late and expensively.

---

## 01-04

**Summary:** Puts teeth on the tracer: generator dry-run before LSR, and a container verify with three executed negative cases (broken unit, injected user name, relative template path) plus the shared rootless verify with the FND-03 bind probes (:80/:443 pass, :79 EACCES negative control).

**Strengths**
- The negative-case design (block/rescue, `# xvpn_negative_case:` markers, expected-message matching that *rejects unrelated failures* like sudo errors) is the strongest test design in the set — guards fail loudly when removed, and Plan 10's diff-based guards then protect them from regression.
- The dry-run verdict pattern (`failed_when: false` on the command, stable message from a follow-up `fail`) avoids Ansible's noisy default error rendering and gives the negative case a matchable prefix.
- Bind probe design is correct: exit-13-on-PermissionError + the :79 negative control genuinely proves FND-03 rather than inferring it, and the port list is a variable so Phase 2+ can override when :443 becomes occupied.

**Concerns**
- **MEDIUM:** the dry-run stderr check `search('(?i)error|converting')` is a known false-positive source (A5 is explicitly unverified). The plan handles it correctly — Plan 10 fallback (c) requires a `checkpoint:decision`, no silent edit — but expect this to trigger; it is the single most likely CI-blocking item in waves 5–8.
- **LOW:** acceptance `grep -c '443' verify_rootless.yml >= 1` is trivially satisfiable by a comment; the GUARD MUTATION intent isn't enforced. The Plan-10 diff guard covers regressions better.
- **LOW:** `bad-user-name` asserts `getent passwd` rc 2 afterwards — but the role's `main` asserts *before* `dnf install`; if the assert fires first as designed, no side effects occur. Verified consistent with the Plan-01 task order (asserts first in `tasks/main.yml` action). Good.

**Suggestions**
- Narrow the stderr pattern now to Quadlet's known error prefixes and keep the rc check as the primary signal, so the checkpoint is less likely to be needed.

**Risk Assessment: MEDIUM** — high design quality; residual risk is concentrated in one flagged assumption with a proper escalation path.

---

## 01-05

**Summary:** Read-only preflight first play with aggregated single-fail, wired as play 1 of `foundation.yml` with `any_errors_fatal`, plus the standalone `xvpn.remnawave.preflight` entry point (D-09). Smallest plan; correctly scoped.

**Strengths**
- The "separate first play" anti-pattern guidance from RESEARCH is implemented structurally *and* verified structurally (the Task-2 python check compares play dicts, and Plan 08 re-asserts identity later — consistent duplication).
- Correctly rejects `ansible_facts.selinux` (missing python3-libselinux yields a misleading fact) in favor of `getenforce`, with a guard mutation forbidding the fact — evidence-based choice carried through to an executable gate.

**Concerns**
- **LOW:** `tags: [preflight]` on play 1 means `--tags preflight` skips play 2 — desirable, but nothing documents that play 2 needs `--skip-tags` inverse behavior awareness; Phase 2 roles must remember to carry tags or accept default-tag behavior.
- **LOW:** play-1/preflight.yml identity is asserted as YAML equality (`s[0]==f[0]`); any future cosmetic divergence (e.g., a comment) passes silently — fine, since Plan 08 re-checks.

**Suggestions**
- None material.

**Risk Assessment: LOW**

---

## 01-06

**Summary:** Completes preflight: Podman floor, port-owner check via `ss -H -ltnpe`, DNS A-record vs public-IP set, AAAA warn-only, input validation with five named messages, W-5 merged service-user allow-list, README docs.

**Strengths**
- W-5 (preflight's accepted port-owner set = its own list ∪ `xvpn_podman_rootless_users` from inventory) is the kind of cross-role coupling usually missed; it's explicitly reasoned (role defaults not visible across plays) and executed as case 18 in Plan 08.
- `iface | replace('-', '_')` for fact lookup shows real Ansible-fact awareness (fact keys munge dashes); the "missing uid field → uid 0" parse fallback is flagged rather than hidden.
- Named-message validation ("Invalid port", "Invalid domain", …) is executed as five negative cases in Plan 08 with exact-substring matching — validation that cannot rot silently.

**Concerns**
- **MEDIUM:** `check_dns.yml` runs a second `getent database=ahostsv6` per domain and parses `ansible_facts[iface].ipv6[]` — extra complexity in the most environment-variable part of the role, for a warn-only check that D-03/D-04 didn't require. If the AAAA parse misbehaves (interface without `ipv6` key, v4-mapped edge cases), preflight fails on hosts that should pass. Suggest making the AAAA comparison fully exception-tolerant or deferring it.
- **LOW:** the domain regex is reasonable but anchors little about IDN/punycode; inventory with punycode domains may false-fail "Invalid domain". Acceptable for v1; document.
- **LOW:** `xvpn_preflight_service_users` default hard-codes `rw-panel`/`rw-node` before those users exist in Phase 1 — harmless (allow-list), but the README table should say they're forward-declared.

**Suggestions**
- Wrap the AAAA section in `block/rescue` that downgrades any error to a warning, matching its warn-only contract.

**Risk Assessment: MEDIUM** — correct and thorough; the AAAA gold-plating is the main flake source on real hosts.

---

## 01-07

**Summary:** Role `common`: baseline packages, SELinux enforcing gate (defence-in-depth), add-only firewalld in the public-interface zone with an SSH lock-out guard, wired into foundation play 2 and the container scenario with three more executed negative cases (6 total).

**Strengths**
- D-13/D-14 are enforced by machine-checkable gates, not prose: acceptance criteria forbid `state: disabled/absent`, forbid the whole-state LSR firewall role, forbid a second owner of `xvpn_public_interface` — the shared-variable ownership rule (preflight owns, common reads with `default('')`) is guarded.
- SSH guard runs twice (before and after the port loop) and the `no-ssh-zone` negative case *pre-asserts the zone resolution* outside the rescue, so a wrong offline-cmd assumption fails loudly rather than vacuously — the flagged assumption has a real tripwire.
- `coupling_justified` for the 01-06 shared default is correctly argued (role defaults don't cross plays; order-independent).

**Concerns**
- **MEDIUM:** verify_common's exact-set port check (`--list-ports == declared set`) will fail on any *operator* pre-existing port in the zone on real hosts — correct per D-13's spirit for managed targets, but this verify runs on operator machines too (local VM tier is fine; a user's workstation run of `molecule test -s vm` is fine; but if a Phase-2 role later adds ports, it must update the declared set — a maintenance coupling). Document that `xvpn_verify_expected_ports` is the cross-phase contract.
- **LOW:** `--add-interface=xvpndummy0` in permanent config for a nonexistent interface — plausible but unverified; already flagged, and the precondition assert contains the blast radius.
- **LOW:** `immediate: "{{ not xvpn_common_firewalld_offline }}"` — `ansible.posix.firewalld` historically warns/errors when `immediate: false` with a running firewalld; ensure the module accepts the boolean expression rendering.

**Suggestions**
- Add one sentence to the README (or the role doc) that the exact-set verify is the declaration contract later phases extend.

**Risk Assessment: MEDIUM** — strong plan; the residual risks are all container-tier environment assumptions with tripwires.

---

## 01-08

**Summary:** Dedicated preflight Molecule scenario: 18 cases (13 behavior + 5 invalid-input) run through a reusable `run_case.yml` block/rescue runner, plus a nothing-changed verify, read-only module allow-list assertion, and controller-side structural checks of the playbooks. This is what makes success criterion 1 an executable test.

**Strengths**
- The nothing-changed proof is thorough: user absent, `/var/lib/xvpn` absent, sysctl file absent, linger absent, *podman package state compared against a recorded before-JSON* — the last one catches dnf side effects other verifications would miss.
- Controller-side parse of `roles/preflight/tasks/*.yml` asserting the read-only module allow-list (and `dnf` only with `list:`) converts D-06 from a convention into a regression test. Genuinely excellent.
- The QA-02 deviation (no idempotence step in a case-runner scenario) is recorded rather than papered over.

**Concerns**
- **MEDIUM:** `systemd-run --unit=xvpn-case-listener --uid=<user> --property=Type=simple …` — `systemd-run` with `--uid` and a `Type=` property implies a service unit; this generally works, but inside a `systemd: always` podman container systemd-run is another untested path (dbus, varlink). It's within the same risk class as the rest of the container tier (Plan 09/10 fix rules cover harness fixes), but it's a second exotic mechanism in one scenario; a plain `become_user` + `nohup`/`setsid` fallback would be simpler if it trips.
- **LOW:** the module-key extraction in verify.yml relies on a hardcoded list of "task keywords"; a task using an unlisted keyword (e.g. `retries`, `delay`, `register` is listed…) would be misclassified. Low blast radius (verify only), but the list should include `retries/delay/until/ignore_errors/loop_control/throttle`.
- **LOW:** `/etc/hosts` stand-in with `unsafe_writes` for the DNS check is sound, but the verify's nothing-changed check doesn't exclude `/etc/hosts` mutation — prepare writes it, verify compares only the listed artifacts; consistent.

**Suggestions**
- Add a fallback listener mechanism (documented one-liner) in case systemd-run fails in the container.

**Risk Assessment: MEDIUM** — the most complex test code in the phase, but its failure modes are contained to CI.

---

## 01-09

**Summary:** CI definitions (pinned, least-privilege), combined blocking checkpoint (PyPI/RubyGems/HashiCorp legitimacy + GitHub prerequisites + public-push consent), repository alignment, and the first behavioural tracer run in CI — deliberately placed before Plans 04–08 build on it (W-6). Right sequencing.

**Strengths**
- The W-6 decision (tracer green in CI before dependent plans start) is the single best process property of the whole plan set: it converts "FLAGGED ASSUMPTION: no local Podman" from a phase-end surprise into a wave-4 checkpoint with 5 plans of slack.
- Actions pinned by full SHA resolved via unauthenticated `git ls-remote` — correct given `gh` isn't authenticated yet; `permissions: contents: read` everywhere; explicit public-push consent for `.planning/` (T-01-18) is a thoughtful disclosure step most reviews would have missed.
- Pre-decided fallbacks (a)–(c) are symptom-scoped, and any assertion-weakening change is excluded from pre-authorization — the anti-"green at any cost" guard (T-01-25) has both a prohibition and SUMMARY-traceability.

**Concerns**
- **MEDIUM:** Task 3 is a debug loop (push → watch → fix → repeat) with a node_repair budget of 2 fix rounds *per distinct failure* — the first-ever run of the podman driver on a hosted runner plausibly exceeds this across multiple distinct failures. The budget should be per-attempt-cycle with an explicit escalation to the user rather than a hard stop mid-wave; otherwise waves 5–9 block on a stalled plan.
- **LOW:** pushing to `main` directly from a detached-HEAD working copy (`git push origin HEAD:refs/heads/main`) is functional but fragile (no branch protection can be assumed on a brand-new repo; concurrent local work could diverge). Acceptable for a solo public repo; note it.
- **LOW:** lint.yml triggers on all-branch push *and* PR — duplicate runs on PR branches; cost only.

**Suggestions**
- Define the Task-3 stop condition as "2 rounds per distinct failure, then `checkpoint:human-verify` with log excerpts" instead of bare stop — the text already reports excerpts; make the handoff explicit.

**Risk Assessment: MEDIUM** — the plan is well-designed; the risk is environmental (first podman-driver run) and already has fallbacks, but the repair budget is tight.

---

## 01-10

**Summary:** Append `preflight` to the CI matrix and drive lint + container workflows to green with all guards from Plans 04–08 active, using PLAN_START-scoped diff guards so no negative case or shared-verify weakening can slip through.

**Strengths**
- The acceptance gates are unusually concrete: a diff over `PLAN_START..HEAD` that must contain *zero removed* `# xvpn_negative_case:` lines, and a gate on edits to `verify_rootless.yml`/`quadlet_validate.yml` that requires a quoted user checkpoint answer in SUMMARY — this is mechanical enforcement of the "no guard weakened for green" prohibition.
- Correctly avoids re-applying Plan-09 fallbacks (references 01-09-SUMMARY).

**Concerns**
- **LOW:** the diff guard only detects *removed* marker lines; a case whose *expected message* is loosened (e.g. broadened `expected text`) passes the gate. Acceptable — the SUMMARY traceability requirement covers the rest.
- **LOW:** fallback (c) in this plan duplicates the Plan-10-fix of Plan 04's stderr concern — consistent, but ensure only one plan owns the final pattern text.

**Suggestions**
- None material.

**Risk Assessment: LOW** — this is a convergence plan whose main risk (inherited CI flakiness) is bounded by Plan 09's already-green baseline.

---

## 01-11

**Summary:** The VM scenario: pinned/checksummed Alma+Rocky boxes, dontaudit-off *proven* via seinfo counts (not assumed), binary-policy sha256 across the reboot to cover boot-window denials, the InvocationID restart round-trip proving Ansible *manages* the user unit (SC2), and runtime/label/AVC verifies shared as reusable task files.

**Strengths**
- The B-2 design (positive control `Dontaudit > 0` before `-DB`, `== 0` asserted at every ausearch window *without re-disabling*, plus policy sha256 across reboot) is the most rigorous SELinux test design I've seen in an Ansible plan set — it correctly identifies that "we ran semodule -DB once" proves nothing if a policy rebuild re-enables dontaudit, and turns that into loud failures.
- Guard mutations are extensive and meaningful (`box_checksum` count == 2, no `latest` symlink, no `manage_user_manager`/`home_root` overrides in VM converge, no `ignore_errors`, no `semodule` in verify_runtime, marker written after dontaudit proven off — ordering checked by index comparison).
- AVC policy: escalation to `checkpoint:decision` with options, never auto-fix, D-08 immutable without the user — exactly right for a `Reversibility: costly` decision.
- Box sourcing verified: versioned Vagrant Cloud URL for Alma + checksummed `dl.rockylinux.org` box for Rocky (the stale `rockylinux/10` Vagrant Cloud box is documented and avoided), matching the recorded Key Decision.

**Concerns**
- **MEDIUM:** `seinfo` Dontaudit-count semantics (loaded-policy reporting, count reaching 0 after `-DB`) is [ASSUMED] with a positive control — good — but if `seinfo`'s default policy source is a file rather than the kernel policy, the positive control could pass while the check measures the wrong artifact. The first VM run will disambiguate; ensure the checkpoint on that failure is pre-scripted (it partially is, via the fail_msg).
- **MEDIUM:** same `passt-selinux`/EL10.3 skew as Plan 01 — `verify_rootless.yml` asserts `rpm -q passt passt-selinux` on VMs that are 10.3 today; if a future leg pins an older minor (the deferred QA-06 matrix), this verify fails spuriously.
- **LOW:** `ausearch -ts <date> <time>` with `LC_ALL=C` marker format is the classic locale-sensitive pattern; the plan handles format but a re-created VM (fresh marker per molecule run) is required — the "only if file does not exist" logic assumes persistent `/var/lib/xvpn-molecule` across molecule reruns on the same VM instance; after `destroy/create` it's fresh. Consistent, just subtle.

**Suggestions**
- Add to the Plan-12 decision rules: "seinfo positive control fails → checkpoint with observed seinfo output", so the disambiguation path is pre-authorized.

**Risk Assessment: MEDIUM** — highest technical sophistication in the set; assumptions are flagged and tripwired, execution reality is the unknown.

---

## 01-12

**Summary:** VM CI workflow with a fail-loud KVM gate, ordered decision rules (KVM-missing → local-only per D-16; Vagrant failure ×2 → delegated GenericCloud fallback), README Testing disclosures, and git-log gates proving no SELinux/D-08 change since PLAN_START.

**Strengths**
- Decision rules are pre-ordered with evidence requirements and SUMMARY recording — the fallback machinery (GenericCloud qcow2 + CHECKSUM-verified sha256 + cloud-init) is fully specified rather than hand-waved, and keeps the same image-integrity posture as the primary path.
- The D-16 local-fallback path is honest: it demands a `checkpoint:human-action` with pasted local evidence and encodes it as `VM-LOCAL-FALLBACK:` in SUMMARY that the verify accepts — no silent downgrade.
- README discloses exactly the right residuals: Podman 5.4–5.8 untested beyond preflight, host-wide sysctl trade-off, `iptables-nft` surprise package (verified present in the installed LSR `vars/Rocky_10.yml:5`), KVM udev rule scope warning.
- Git-log gates (`-G seboolean`, `-G 'semodule -i'`, `-G xvpn_podman_rootless_home_root` empty) enforce the prohibitions archaeologically — cheap and effective.

**Concerns**
- **MEDIUM:** the "not a required merge check until 5 consecutive green runs" policy is flagged as *pending user confirmation* at verify-work — fine, but the README will state it before the user confirms; if the user changes the policy, README+workflow both need edits. Acceptable churn.
- **LOW:** 90-minute job timeout per leg with box download (~1 GB for Rocky) + image pull + converge + idempotence + reboot + post-reboot wait (up to ~10 min of retries alone) is tight on a 4-vCPU public runner; TCG fallback (no KVM) would blow it — but the KVM gate failing loudly makes that moot.
- **LOW:** decision rule 2's `create.yml` uses `virsh domifaddr` lease waiting — dnsmasq on the default network is installed, good; note that `ebtables` on newer Ubuntu is a no-op transitional package (harmless).

**Suggestions**
- Consider `timeout-minutes: 120` headroom or move the box download into a cached step.

**Risk Assessment: MEDIUM** — dominated by the already-flagged A11/A14 environment unknowns, with pre-decided, integrity-preserving fallbacks.

---

## Cross-Plan Assessment

**Coverage:** all 12 plan ids reviewed; requirement traceability is complete (FND-01→05/06/08, FND-02→01/04/11, FND-03→01/04/11, FND-04→01/02/04/11, FND-05→07/11, FND-06→01/03/05/07, FND-07→06/08, QA-01→03/09/10, QA-02→02/08/09/10, QA-03→11/12), and all four phase success criteria have executable tests. Dependency graph and waves are internally consistent; parallel waves (04∥05, 06∥07-partially, 08∥11) own disjoint files.

**Systemic strengths:** (1) verification is consistently *executed* rather than asserted, with guard mutations against removal; (2) supply-chain gating is layered (Galaxy→Plan 02, PyPI/gem/apt→Plan 09, both blocking before first install); (3) SELinux testing (dontaudit proven, boot-window covered, escalation-not-autofix) is best-in-class; (4) the W-6 early-tracer-in-CI decision de-risks the whole wave structure.

**Systemic risks (ranked):**
1. **MEDIUM** — `scripts/check.sh` unmatched-glob bug potential (01-03) sits on every later plan's verify path; specify nullglob/existence filtering now.
2. **MEDIUM** — `passt-selinux` unconditional package + `rpm -q` verify hard-codes EL10.3 while the supported floor is 10.0 (01-01, inherited by 01-04/11).
3. **MEDIUM** — first-run CI debug loops (01-09 Task 3, 01-10, 01-12 Task 2) with tight repair budgets; make the escalation-to-user handoff explicit.
4. **MEDIUM** — dry-run stderr false-positive (01-04→01-10 fallback c) and `systemd-run` in the preflight scenario (01-08) are the two most likely CI tripwires; both have correct escalation paths.
5. **LOW** — AAAA warn-only check complexity (01-06); task-keyword list brittleness (01-08).

**Overall risk: MEDIUM.** The plan set is exceptionally internally consistent, evidence-grounded (several central claims verified against the installed LSR 2.5.0 source in this container), and defensively engineered. The residual risk is concentrated exactly where the plans themselves say it is: environment-dependent first executions (rootless podman driver on hosted runners, Vagrant+libvirt, enforcing-VM SELinux behavior), each of which carries a flagged assumption, a tripwire, and a pre-decided fallback that does not weaken the product.

---

## Qwen Review

> [reviewed-without-source-citations] This reviewer declared source-grounded evidence but cited no file:line source evidence, so it reviewed the pasted plan text only — down-weight its verdict in the Consensus Summary.

Now I have sufficient context to provide a comprehensive review. Let me analyze each plan systematically.

---

# Phase 1 Plan Review: Rootless-фундамент и тестовый стенд

## Overall Assessment

This is an exceptionally thorough set of plans for a greenfield Ansible collection. The research is deep, the technical claims are mostly verified against source code and documentation, and the wave-based dependency structure is sound. However, the sheer complexity and number of flagged assumptions create execution risk.

---

## 01-01

### Summary
Plan 01 establishes the collection identity (`galaxy.yml`, `meta/runtime.yml`) and the `podman_rootless` role with its core plumbing: user creation, SELinux file-context equivalence, sysctl for unprivileged ports, linger, and the Quadlet deployment interface backed by LSR. This is the "tracer" — the thinnest end-to-end path that later plans extend.

### Strengths
- **Clear scope boundaries**: The plan correctly identifies itself as a tracer, deferring Molecule scenarios to Plan 02 and lint configs to Plan 03. This prevents scope creep.
- **D-10 verdict well-documented**: The decision to use LSR `fedora.linux_system_roles.podman` rather than writing a custom `deploy_quadlet` is justified with a 5-condition verification table (RESEARCH Pattern 3).
- **Order-is-idempotency insight**: Pattern 2's ordering (sefcontext BEFORE user creation, sysctl BEFORE unit start) is correctly identified as critical and documented with evidence.
- **Security-conscious**: Input validation with regex asserts (`^[a-z_][a-z0-9_-]{0,30}$`), argv-only commands, and explicit prohibition of `shell:` module.
- **`podman_pull_image: false`**: Correctly identified as essential for idempotence (RESEARCH Pitfall 4).

### Concerns
- **MEDIUM — User manager wait path unproven**: The plan acknowledges that `wait_for: path=/run/user/<uid>/systemd/private` is an assumption (A2) that can only be proven in the VM tier. This is a critical path — if the socket path is wrong or `user@.service` doesn't behave as expected, the entire rootless plumbing fails. The container tier cannot catch this.
- **MEDIUM — `become_method: sudo` with `nologin` shell**: The plan assumes `sudo` works with `/sbin/nologin` but `su` does not. This is correct for typical configurations, but some hardened systems configure `sudo` to require a valid shell. The plan should verify this in the first VM run.
- **LOW — No `argument_specs` validation test**: While `argument_specs.yml` is created, there's no test that wrong-typed inputs are actually rejected at role entry. Plan 04 mentions this gap but doesn't address it.

### Suggestions
1. Add a pre-flight check in `user.yml` that verifies `sudo` works for the created user before proceeding (a simple `command: sudo -u {{ user }} true`).
2. Document in SUMMARY that the user-manager wait path is the highest-risk unproven assumption.
3. Consider adding an explicit `failed_when` on the `wait_for` task with a message pointing to the linger/user-manager race (Pitfall 6).

### Risk Assessment
**MEDIUM** — The plan is well-designed but relies on assumptions about user-manager behavior that can only be proven in the VM tier. The tracer verify (syntax-check only) cannot catch runtime failures.

---

## 01-02

### Summary
Plan 02 adds the pinned `requirements.yml` with Galaxy legitimacy checkpoint, `ansible.cfg`, the Molecule-only fixture (`xvpn-fixture.container.j2`), and the container scenario that drives the tracer path end-to-end.

### Strengths
- **Galaxy legitimacy gate**: The human-approval checkpoint (Task 2) before any install is excellent supply-chain hygiene. Each collection's publisher namespace and upstream repo are recorded.
- **Exact pins with justification**: The `requirements.yml` header documenting why each collection is pinned addresses the RESEARCH audit's SUS flags.
- **Test double for getenforce**: The container tier correctly recognizes that SELinux is off on the runner and creates a test double at `/usr/local/sbin/getenforce` with a sudoers drop-in to ensure `become` reaches it.
- **Fixture is Molecule-only**: The fixture correctly lives under `extensions/molecule/shared/templates/` and never ships in the collection (D-12).

### Concerns
- **HIGH — `secure_path` test-only drop-in**: The plan adds `/etc/sudoers.d/xvpn-test-path` with `Defaults secure_path = /usr/local/sbin:...` to ensure the test double is reached. This is a test-only change, but if the cleanup fails or the container is reused, it could affect later tests. The plan should ensure this is container-scoped.
- **MEDIUM — `xvpn_podman_rootless_manage_user_manager: false` in container tier**: The container tier disables the user manager start because there's no real systemd-logind. This means the container tier cannot prove the user-manager wait path works — that proof is deferred entirely to the VM tier (Plans 11-12). This is a significant gap: the tracer's most complex plumbing is untested until wave 7.
- **MEDIUM — Fixture `Network=pasta` assumption**: The fixture uses `Network=pasta` + `PublishPort=80:8080`, which RESEARCH A7 marks as assumed to work under SELinux. If pasta doesn't work as expected in the container tier, the fixture fails without clear diagnostics.

### Suggestions
1. Add a comment in the container `converge.yml` explaining that the user-manager path is intentionally disabled and proven only in the VM tier.
2. Consider adding a diagnostic task in `prepare.yml` that prints `podman info` output to help debug pasta/networking issues.
3. The `secure_path` drop-in should be explicitly cleaned up in a `cleanup.yml` or documented as container-ephemeral.

### Risk Assessment
**MEDIUM** — The plan correctly identifies and works around container-tier limitations, but the user-manager gap means critical plumbing is untested until much later.

---

## 01-03

### Summary
Plan 03 adds the quality gate: `.ansible-lint`, `.yamllint`, `.gitignore`, `changelogs/changelog.yaml`, `scripts/check.sh`, `README.md` stub, and `LICENSE`. This makes the collection lint-clean and buildable.

### Strengths
- **CI-hard yamllint step**: The `scripts/check.sh` correctly fails in CI when yamllint is missing (`CI=true` + missing yamllint = exit 1) but prints a notice outside CI. This prevents silent CI skips.
- **`var-naming[no-role-prefix]` skip documented**: The lint skip for the project's `xvpn_<role>_*` convention is documented with a comment, addressing RESEARCH Pitfall 3.
- **`supported_ansible_also` configuration**: Correctly addresses RESEARCH Pitfall 1 (`meta-runtime[unsupported-version]` on `requires_ansible: ">=2.20.0"`).
- **LICENSE matches galaxy.yml declaration**: GPL-3.0-or-later is fetched verbatim from gnu.org.

### Concerns
- **LOW — README is a stub**: The README is explicitly minimal (full docs are Phase 5), which is fine, but operators finding the collection before Phase 5 will see almost no usage information.
- **LOW — No `.gitignore` for `.venv/`**: The plan mentions `.venv/` in `.gitignore` but developers might also create `__pycache__/` directories that should be ignored.

### Suggestions
1. Consider adding a "Status: Development" banner to the README stub to set expectations.
2. Add `__pycache__/` and `*.pyc` to `.gitignore` explicitly.

### Risk Assessment
**LOW** — This is a straightforward scaffolding plan with well-understood tooling. The lint configs are verified green on a scratch collection.

---

## 01-04

### Summary
Plan 04 adds the generator dry-run validation step (`quadlet_validate.yml`) before the LSR call, and the container verify with executed negative cases for broken templates and input injection.

### Strengths
- **D-10 condition (e) satisfied**: The plan correctly identifies that LSR lacks generator dry-run validation and adds it as a pre-step. The `QUADLET_UNIT_DIRS` environment variable is correctly used.
- **Executed negative cases**: Three negative cases (broken-unit, bad-user-name, relative-template) with specific expected failure messages prove the guards work. The `# xvpn_negative_case:` marker comments enable structural verification.
- **FND-03 bind probe**: The `:443` bind probe as `rw-edge` (plus `:79` negative control) is a clever way to prove the sysctl works without needing a real listener.
- **`changed_when: false` on validation tasks**: Correctly ensures idempotence stays green.

### Concerns
- **MEDIUM — `podman-system-generator --dryrun` exit code assumed**: RESEARCH A5 explicitly marks the exit-code-on-error behavior as assumed. The plan mitigates this with a stderr assertion AND a negative test, but if the generator returns 0 on errors AND produces no "error" in stderr, the validation silently passes. The container tier's negative test is the only proof.
- **MEDIUM — Bind probe in container tier**: The `:443` bind probe runs in the container tier's network namespace, which is the runner's network namespace. This proves the sysctl is set, but not that it works in the host namespace after reboot (VM tier). The plan acknowledges this but the dependency chain means FND-03 is not fully proven until wave 7.
- **LOW — `xvpn-broken.container.j2` deliberately has no image**: The broken template has only `ContainerName` and `WantedBy`, no `Image=`. This is a valid negative test, but the error message from the generator might vary between Podman versions.

### Suggestions
1. Add a comment in `quadlet_validate.yml` explaining that the stderr pattern `(?i)error|converting` is based on assumed generator behavior and should be verified in the first VM run.
2. Consider adding a positive assertion that the dry-run stdout contains the expected service name (e.g., `xvpn-fixture.service`), which the plan mentions but doesn't make explicit in the acceptance criteria.

### Risk Assessment
**MEDIUM** — The plan is well-designed but relies on assumptions about generator behavior that are mitigated by negative tests. The bind probe's container-tier limitation is acknowledged.

---

## 01-05

### Summary
Plan 05 creates the `preflight` role with OS and SELinux checks, makes it the read-only first play of `foundation.yml`, and adds the standalone `playbooks/preflight.yml` entry point (D-09).

### Strengths
- **Read-only aggregation pattern**: The plan correctly implements Pattern 1 (RESEARCH): every check appends to `xvpn_preflight_errors`, one final `fail` prints all messages. This satisfies D-06 (nothing changed on failure).
- **Separate first play with `any_errors_fatal: true`**: This is the structural guarantee that no host changes if any host fails preflight. The plan correctly identifies this as critical.
- **Standalone `preflight.yml`**: D-09 requires preflight to be runnable on its own; the plan delivers this with identical play structure.
- **No `ansible_facts.selinux`**: The plan correctly avoids the gathered SELinux fact (which reports "Missing selinux Python library" without `python3-libselinux`) and uses `command: getenforce` instead.

### Concerns
- **LOW — Preflight runs before packages are installed**: The preflight play runs before `common` installs `python3-libselinux`. This means `getenforce` might not be on PATH on a truly bare host. The plan should handle this case (e.g., check for `getenforce` existence and fail with a helpful message).
- **LOW — `tags: [preflight]` on the first play**: The tag is added but never used in the plan. It's useful for operators who want to run only preflight via `--skip-tags` or `--tags`, but this isn't documented.

### Suggestions
1. Add a task in `preflight/tasks/main.yml` that checks for `getenforce` existence and fails with "python3-libselinux is not installed; install it or run the full playbook" if missing.
2. Document the `preflight` tag in the README (Plan 06).

### Risk Assessment
**LOW** — The plan implements a well-understood pattern with clear structural guarantees.

---

## 01-06

### Summary
Plan 06 completes the preflight role with Podman floor, port ownership, and DNS A-record checks, plus input validation and README documentation.

### Strengths
- **Comprehensive input validation**: Five named-message asserts (Invalid port, domain, xvpn_public_ip, xvpn_public_interface, service user name) at role entry prevent command injection (T-01-07).
- **Port owner check via `ss -H -ltnpe`**: The `-e` flag's `uid:NNNN` field is correctly parsed, and the managed-user allow-list (D-05) ensures idempotent re-runs.
- **W-5 merged allow-list**: The plan correctly merges `xvpn_preflight_service_users` with `xvpn_podman_rootless_users` so a user managed by podman_rootless in inventory is never missing from preflight's port-owner allow-list.
- **DNS check with `ahostsv4`**: Uses the host's NSS resolver (D discretion), correctly compares resolved addresses with the public IP set, and handles the `xvpn_preflight_dns_check: false` opt-out.
- **AAAA warn-only**: Correctly implements the user decision (2026-11-23) that AAAA mismatches warn but don't fail.

### Concerns
- **MEDIUM — `ss` uid field for root-owned sockets**: The plan acknowledges (flagged assumption) that `ss` might not print a `uid:` field for root-owned sockets, treating missing as uid 0. This could cause false positives if a root-owned process holds a port. The plan should verify this behavior in the container tier.
- **MEDIUM — `package_facts` for Podman version**: The plan uses `ansible.builtin.package_facts` (manager rpm) to get the installed Podman version. If Podman is not installed, it falls back to `dnf list podman` to get the available version. This is correct but adds complexity; the plan should ensure the fallback is tested.
- **LOW — Domain regex allows 253-character domains**: The regex `^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?[.])+[a-z][a-z0-9-]{0,62}$` is correct but might reject valid IDN domains. This is acceptable for v1 (English-only).

### Suggestions
1. Add a test case in Plan 08 for a root-owned port holder to verify the uid-field-missing behavior.
2. Document in the README that the DNS check uses the host's resolver, not a specific DNS server.

### Risk Assessment
**LOW-MEDIUM** — The plan is comprehensive and well-tested by the Plan 08 scenario. The `ss` uid assumption is the main risk.

---

## 01-07

### Summary
Plan 07 creates role `common` (baseline packages, SELinux enforcing gate, add-only firewalld with SSH guard), wires it into `foundation.yml`, and adds the container verify with executed negative cases.

### Strengths
- **Add-only firewalld (D-13)**: The plan correctly uses `state: enabled` only, never `state: disabled` or `absent`. The acceptance criteria explicitly forbid removal states.
- **SSH guard (D-14)**: The plan asserts SSH is allowed BEFORE and AFTER any port changes, failing with a clear message if SSH would be lost. This is critical for operator safety.
- **Exact-set port verify**: The `verify_common.yml` asserts that the public zone's ports equal exactly the declared set, not just a subset. This catches accidental port additions.
- **Three executed negative cases**: `no-ssh-zone`, `port-without-protocol`, `selinux-permissive` each prove a specific guard works.
- **`xvpn_common_firewalld_offline: true` for container tier**: Correctly handles the no-running-firewalld case.

### Concerns
- **MEDIUM — `firewall-offline-cmd --get-zone-of-interface` assumption**: The plan acknowledges (flagged assumption) that `firewall-offline-cmd` might not resolve an interface bound with `--add-interface` in the permanent config. The `no-ssh-zone` test verifies this, but if the assumption is wrong, the test fails loudly instead of passing against the wrong zone.
- **MEDIUM — No SELinux boolean/port management in Phase 1**: The plan explicitly defers SELinux booleans/ports to the VM tier's zero-AVC proof. This is correct (don't add without evidence) but means Phase 1 roles might fail on first real run if booleans are needed.
- **LOW — `xvpn_public_interface` owned by preflight, read by common**: The plan correctly avoids a second owner of the shared default, but the `| default('')` pattern in common means an empty interface silently falls back to `ansible_default_ipv4`. This could hide configuration errors.

### Suggestions
1. Add a warning in `common/tasks/firewalld.yml` when `xvpn_public_interface` is empty and the default route interface is used.
2. Document in the README that Phase 1 does not add SELinux booleans; any needed booleans are added in later phases based on AVC evidence.

### Risk Assessment
**LOW-MEDIUM** — The plan is well-designed with strong guards. The `firewall-offline-cmd` assumption is tested.

---

## 01-08

### Summary
Plan 08 creates the preflight Molecule scenario with 18 cases (13 behavior + 5 invalid-input), proving every preflight failure path and the nothing-changed invariant.

### Strengths
- **Comprehensive case coverage**: 18 cases cover every check (OS, SELinux, Podman, ports, DNS) plus every input validation assert. The `xvpn_case_id:` markers enable structural verification.
- **Nothing-changed proof**: The verify asserts no `rw-edge` user, no `/var/lib/xvpn`, no sysctl file, no linger file, and Podman package state unchanged. This proves D-06.
- **Read-only module allow-list**: The verify loads every `roles/preflight/tasks/*.yml` and asserts the module set is a subset of the allow-list. This is a structural guarantee of read-only behavior.
- **`/etc/hosts` as DNS stand-in**: The container tier correctly uses `/etc/hosts` entries to simulate DNS, with `unsafe_writes: true` for podman bind-mount compatibility.
- **Warnings for empty domains**: The plan correctly implements the user decision that `xvpn_preflight_dns_check: true` with empty `xvpn_preflight_domains` prints a warning, not an error.

### Concerns
- **MEDIUM — No idempotence step**: The plan explicitly notes this scenario has no idempotence step (it's a case runner). The container scenario keeps the real idempotence check. This is a QA-02 deviation that should be documented.
- **MEDIUM — OS and Podman negatives use variable narrowing**: The plan acknowledges (flagged assumption) that OS and Podman-version negatives are driven by narrowing role variables on a real Alma 10 container, not by a real non-EL10 host or a real Podman 5.3 install. This means the "Unsupported OS" and "Podman too old" paths are not tested with real inputs.
- **LOW — Case 18 (port-managed-rootless-users) tests W-5 merge**: This case proves the merged allow-list works, but it requires the `xvpn_podman_rootless_users` variable to be visible in the preflight play. The plan should verify this cross-play variable visibility.

### Suggestions
1. Add a comment in the scenario's `molecule.yml` explaining the QA-02 deviation (no idempotence step).
2. Consider adding a real non-EL10 test (e.g., a Fedora container) to prove the OS check works with a real different distribution.

### Risk Assessment
**LOW** — The plan is comprehensive and well-structured. The flagged assumptions are acceptable for v1.

---

## 01-09

### Summary
Plan 09 adds pinned dev tooling (`requirements-dev.txt`), the lint and container-tier GitHub Actions workflows, passes the package legitimacy gate, aligns `galaxy.yml` with origin, makes the first push, and drives lint + container tier to green.

### Strengths
- **SHA-pinned GitHub Actions**: The plan correctly pins `actions/checkout` and `actions/setup-python` by full 40-character commit SHA, resolved via `git ls-remote`. This prevents supply-chain attacks.
- **`permissions: contents: read`**: Least-privilege workflows.
- **Human legitimacy checkpoint**: Task 2 covers PyPI, RubyGems, HashiCorp apt, AND GitHub prerequisites (origin, gh auth, public push confirmation) in one blocking checkpoint. This is efficient.
- **Tracer exercised early (W-6)**: The plan correctly identifies that the first push is the behavioural gate of the tracer path, before Plans 04-08 build on it.
- **Pre-decided fallbacks**: The plan has explicit fallbacks for known failure modes (logind not running, podman driver can't start privileged containers, Molecule fails on missing verify).

### Concerns
- **HIGH — First behavioural run of tracer in CI**: The devcontainer has no Podman, so the tracer path (foundation playbook + quadlet entry point + fixture) runs behaviourally for the first time in CI. If it fails, the plan's fix budget (2 rounds per failure) might not be enough to diagnose and fix root cause. This is the highest-risk moment in Phase 1.
- **MEDIUM — `ansible-core 2.22` deferred to QA-06**: The devcontainer has 2.22.0 but CI runs 2.21. This means local development and CI use different Ansible versions, which could hide compatibility issues.
- **MEDIUM — Public push of `.planning/`**: The plan explicitly confirms the public push includes `.planning/` (planning documents). This is intentional but exposes internal decision-making to the public.

### Suggestions
1. Consider running a local Podman test (e.g., in a disposable VM) before the first push to catch obvious failures.
2. Document in the README that the collection is developed with ansible-core 2.22 but CI tests 2.21.
3. Add a `.planning/README.md` explaining the planning structure for public visitors.

### Risk Assessment
**HIGH** — This is the highest-risk plan because it's the first behavioural run of the tracer. The fix budget and fallbacks are well-designed, but the uncertainty is significant.

---

## 01-10

### Summary
Plan 10 appends the preflight scenario to the container-tier CI matrix, pushes, and drives lint + molecule-container to green with all guards from Plans 04-08 proven.

### Strengths
- **All guards proven in CI**: This is the "make everything green" plan that proves every negative case, every input validation, and every preflight check works in CI.
- **No guard weakening prohibition**: The plan explicitly forbids removing or relaxing assertions to obtain green CI. The acceptance criteria verify no `# xvpn_negative_case:` line was removed.
- **Fix commits documented**: Every fix commit is listed in SUMMARY with the log line that motivated it, ensuring traceability.

### Concerns
- **MEDIUM — Fix budget exhaustion**: If multiple guards fail simultaneously, the 2-round fix budget per failure might not be enough. The plan should prioritize which guards to fix first.
- **LOW — Dependency on Plan 09 green**: The plan requires Plan 09's lint + container runs to be green. If Plan 09 is red, Plan 10 cannot start.

### Suggestions
1. Add a priority order for fixing failures (e.g., input validation first, then negative cases, then preflight checks).
2. Consider increasing the fix budget to 3 rounds for the first run, given the number of new guards.

### Risk Assessment
**MEDIUM** — The plan is well-designed but depends on Plan 09's success and has a limited fix budget.

---

## 01-11

### Summary
Plan 11 creates the VM Molecule scenario (QA-03) on AlmaLinux 10 and Rocky 10 with SELinux enforcing: converge, idempotence, reboot, runtime + label + zero-AVC assertions.

### Strengths
- **Pinned, checksummed boxes**: Both Alma and Rocky boxes have versioned URLs and sha256 checksums. Rocky uses the official `dl.rockylinux.org` image (D-18 deviation from CLAUDE.md accepted by user).
- **Dontaudit proven, not assumed**: The plan correctly implements B-2: `seinfo` positive control (>0 before `-DB`), `semodule -DB`, assertion (==0 after), and the same assertion WITHOUT re-disabling before every `ausearch`. This proves dontaudit stayed off.
- **Boot-time policy integrity**: The plan records the sha256 of the binary policy before reboot and asserts it's unchanged after, proving the boot-time policy is the dontaudit-free one.
- **`:443` bind probe in VM tier**: The plan correctly runs the bind probe before and after reboot in the host network namespace, proving the sysctl works persistently.
- **Ansible controls user unit (SC2)**: The plan proves Ansible can restart the user unit via `systemctl --user`, not just observe it.
- **AVC escalation, not auto-fix**: Any AVC naming `/var/lib/xvpn` stops execution with a `checkpoint:decision`, never auto-fixed. This protects D-08.

### Concerns
- **HIGH — D-08 home path unproven until this plan**: The `/var/lib/xvpn` home with SELinux equivalence is a locked decision (D-08, `Reversibility: costly`), but it's only proven in this plan (wave 7). If AVCs appear, Phases 2-4 have already hardcoded this path. The plan correctly escalates to the user, but the cost of changing D-08 at this point is high.
- **MEDIUM — Podman 5.x not tested in VM**: Both VM legs install Podman 6.1.x. The 5.4 floor is covered only by the preflight version check. This is an accepted risk (RESEARCH Open Question 3) but means Quadlet key differences between 5.x and 6.x are not tested.
- **MEDIUM — `semodule -DB` persistence across policy rebuilds**: The plan acknowledges that `container-selinux` installed during converge might rebuild the policy with dontaudit re-enabled. The pre-decided harness fix is to install policy packages in `prepare.yml` before `-DB`. This adds complexity.

### Suggestions
1. Consider adding a Podman 5.x VM leg (even optional/nightly) to catch version-specific issues.
2. Document in SUMMARY that D-08 is the highest-risk unproven decision at the start of this plan.
3. Add a diagnostic task in `verify_runtime.yml` that prints `seinfo | grep Dontaudit` and `sha256sum /etc/selinux/targeted/policy/*` for debugging.

### Risk Assessment
**HIGH** — This plan proves the most critical assumptions (D-08, SELinux labels, zero AVC) but is also the most likely to reveal showstoppers.

---

## 01-12

### Summary
Plan 12 runs the VM scenario in GitHub Actions with a KVM gate, spikes the Vagrant + libvirt recipe, applies the pre-decided fallback if needed, and drives both legs to green.

### Strengths
- **KVM gate fails loudly**: The plan correctly applies the udev rule and fails with `::error::` if `/dev/kvm` is not available, never silently skipping.
- **Pre-decided fallback**: If Vagrant/vagrant-libvirt fails twice, the plan switches to the delegated driver with GenericCloud qcow2 + cloud-init. This is well-designed.
- **README Testing section**: Documents all three tiers, the KVM rule scope, the `ip_unprivileged_port_start=80` trade-off, the Podman 5.x residual risk, and the `iptables-nft` package.
- **VM-LOCAL-FALLBACK evidence**: If KVM is unavailable, the plan accepts a local `molecule test -s vm` summary as evidence.

### Concerns
- **HIGH — Vagrant + vagrant-libvirt on hosted runners unproven**: RESEARCH A11 marks this as an assumption. The `vagrant-libvirt` upstream has had no release since 2023-06 and no commit since 2023-12. If the spike fails, the fallback adds ~150 lines of custom create/destroy playbooks.
- **MEDIUM — VM workflow not a required merge check until 5 consecutive greens**: This is a pragmatic decision (RESEARCH Pitfall 11) but means Phase 1 can complete without VM CI being stable.
- **MEDIUM — HashiCorp apt repo as fallback**: The plan uses HashiCorp's signed apt repo only if Ubuntu's `vagrant-libvirt` package has no candidate. This adds another trusted source.

### Suggestions
1. Time-box the Vagrant spike to 2 hours; if it fails, switch to the fallback immediately.
2. Document the fallback decision criteria in the README Testing section.
3. Consider adding a `workflow_dispatch` input to manually trigger the VM tier for debugging.

### Risk Assessment
**HIGH** — This plan depends on unproven infrastructure (KVM on hosted runners, vagrant-libvirt). The fallback is well-designed but adds complexity.

---

## Cross-Plan Analysis

### Dependency Chain
The wave-based dependency structure is sound:
- Wave 1-3: Scaffold (no runtime dependencies)
- Wave 4: CI + first push (behavioural tracer gate)
- Wave 5-6: Guards and preflight (build on tracer)
- Wave 7-8: Scenarios and CI green (prove guards)
- Wave 9: VM CI (prove SELinux/reboot)

The `depends_on` declarations are correct, and the precondition checks (e.g., Plan 04 requires Plan 09's CI green) prevent building on a broken foundation.

### Flagged Assumptions Summary
The plans flag 16+ assumptions (A1-A16, plus edge-probe markers). The highest-risk unproven assumptions are:
1. **A2**: User manager wait path (`/run/user/<uid>/systemd/private`)
2. **A6**: `/var/lib/xvpn` SELinux labels (D-08)
3. **A7**: `Network=pasta` + `PublishPort` under SELinux
4. **A11**: Vagrant + vagrant-libvirt on hosted runners

These are all proven in Plans 11-12, which is late in the phase but unavoidable (they require real SELinux/KVM).

### Security Posture
The security posture is strong:
- Input validation with regex asserts (T-01-01, T-01-07)
- argv-only commands, no `shell:` module
- Add-only firewalld (D-13)
- SSH guard (D-14)
- SELinux enforcing asserted, never weakened
- AVC escalation, not auto-fix
- SHA-pinned GitHub Actions
- Human legitimacy checkpoints for package sources

### Quality Assurance
The QA strategy is comprehensive:
- Lint (ansible-lint production, yamllint)
- Container tier (syntax, converge, idempotence, negative cases)
- Preflight scenario (18 cases, nothing-changed proof)
- VM tier (SELinux enforcing, reboot, zero AVC)
- CI on every push (lint + container + preflight)
- VM CI on PR/nightly

---

## Overall Risk Assessment

**MEDIUM-HIGH**

The plans are exceptionally well-designed, with thorough research, clear dependencies, and strong security posture. However, the phase carries significant execution risk due to:

1. **Late proof of critical assumptions**: D-08 (home path), user-manager wait, and pasta networking are only proven in wave 7-9. If they fail, the cost of change is high.
2. **First behavioural run in CI**: The tracer path runs behaviourally for the first time in Plan 09's CI, with a limited fix budget.
3. **Unproven VM infrastructure**: KVM on hosted runners and vagrant-libvirt are assumed to work; the fallback adds complexity.

**Mitigations in place**:
- Wave-based dependencies prevent building on broken foundations
- Pre-decided fallbacks for known failure modes
- Human checkpoints for irreversible decisions
- Escalation (not auto-fix) for SELinux issues

**Recommendation**: Proceed with execution, but prioritize early local testing (disposable VM with Podman + SELinux) to catch obvious failures before CI. Consider adding a "Phase 1.5" spike if Plan 11 reveals D-08 issues, before Phases 2-4 hardcode the path.

---

## Consensus Summary

Two lanes produced reviews. **OpenCode** (re-run) is source-grounded: it verified central claims against the installed `fedora.linux_system_roles` 2.5.0 (`handle_images.yml:11` `force: true` → `podman_pull_image: false` is required; `create_update_quadlet_spec.yml:116-118,147-151` → container-tier `activate: false` design avoids user-bus calls; `vars/Rocky_10.yml:5` → `iptables-nft`). Overall verdict MEDIUM. **Qwen** carries `[reviewed-without-source-citations]` and is down-weighted. Neither reviewer rates any concern HIGH after weighting: OpenCode has no HIGH items; Qwen's four HIGH items are uncorroborated by the grounded reviewer.

### Agreed Strengths
- Wave/dependency structure is consistent; the W-6 decision (tracer green in CI in wave 4, before plans 04-08 build on it) de-risks the whole phase.
- Executed negative cases with regression guards; read-only preflight with aggregated fail and `any_errors_fatal`.
- Add-only firewalld with SSH lock-out guard (D-13/D-14 machine-checked).
- 01-11 SELinux design: dontaudit proven off with positive control, binary-policy sha256 across reboot, AVC → `checkpoint:decision`, never auto-fix.
- Supply chain: SHA-pinned actions, exact Galaxy pins, blocking legitimacy checkpoints before first install.

### Agreed Concerns
- **01-09 first-run CI repair budget (MEDIUM, both reviewers; Qwen rated HIGH).** 2 fix rounds per distinct failure on the first-ever podman-driver run is tight; make the stop condition an explicit `checkpoint:human-verify` with log excerpts rather than a bare stop (OpenCode applies the same to 01-10 and 01-12 Task 2).
- **01-12 Vagrant/libvirt on hosted runners (MEDIUM; Qwen HIGH).** Already a flagged assumption with an integrity-preserving GenericCloud fallback; OpenCode adds timeout headroom (`timeout-minutes: 120` or cached box download).
- **01-11 assumptions resolved only in the VM tier (MEDIUM).** Qwen: D-08 proven only in wave 7. OpenCode: `seinfo` may measure the policy file, not the loaded policy; pre-authorize "positive control fails → checkpoint with observed seinfo output" in 01-12's decision rules.
- **01-04 dry-run stderr pattern `(?i)error|converting` (MEDIUM).** Most likely CI tripwire; narrow to Quadlet error prefixes and keep rc as the primary signal.

### New grounded concerns (OpenCode only)
- **01-01 / 01-04 / 01-11: `passt-selinux` unconditional (MEDIUM).** Present on EL10.3 only per research; the 5.4 preflight floor admits 10.0-10.2, where `dnf` would fail and `verify_rootless.yml`'s `rpm -q passt passt-selinux` would fail spuriously. Verified: `01-01-PLAN.md:156` lists it in defaults, `01-04-PLAN.md:152` asserts it.
- **01-03 `check.sh` unmatched glob (MEDIUM).** The plan text says "every *existing*" molecule playbook (`01-03-PLAN.md:119`) but specifies no mechanism (`nullglob` or `[ -e ]`); under `set -euo pipefail` a literal unmatched pattern fails the gate before `verify.yml` exists. Specify the mechanism plus a guard that extensions stay covered.
- **01-02:** drop `verify` from the initial `test_sequence` until 01-04 adds `verify.yml`, or comment it as a placeholder.
- **01-06:** wrap the AAAA comparison in `block/rescue` that downgrades errors to a warning (warn-only contract).
- **01-08:** documented fallback listener if `systemd-run --uid` fails in the container; extend the task-keyword list (`retries/delay/until/ignore_errors/loop_control/throttle`).
- **01-07:** document `xvpn_verify_expected_ports` as the cross-phase contract later phases extend.

### Divergent Views
- **01-02 sudoers `secure_path` drop-in:** Qwen HIGH (must be provably container-scoped); OpenCode LOW-risk plan, calls the getenforce double a self-checking harness and verified the container-tier design against LSR source.
- **Overall risk:** Qwen flags four HIGH items; OpenCode rates the set MEDIUM and "exceptionally internally consistent", with residual risk exactly where the plans already flag it.
- Qwen-only suggestions (unconfirmed): guard `getenforce` absence on a bare host (01-05); warn on empty `xvpn_public_interface` (01-07); root-owned port holder case (01-06/01-08); positive `xvpn-fixture.service` assertion in the dry-run output (01-04).
