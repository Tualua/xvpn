---
phase: 3
reviewers: [opencode, qwen]
reviewed_at: 2026-11-28T07:15:36Z
plans_reviewed: [03-01-PLAN.md, 03-02-PLAN.md, 03-03-PLAN.md, 03-04-PLAN.md, 03-05-PLAN.md, 03-06-PLAN.md, 03-07-PLAN.md, 03-08-PLAN.md, 03-09-PLAN.md, 03-10-PLAN.md, 03-11-PLAN.md, 03-12-PLAN.md, 03-13-PLAN.md, 03-14-PLAN.md]
models:
  opencode: "unknown"
  qwen: "unknown"
model_sources:
  opencode: "unknown"
  qwen: "unknown"
---

# Cross-AI Plan Review — Phase 3

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

## OpenCode Review

# Cross-AI Plan Review — Phase 3 (Node with Reality self-steal + auto-registration)

**Repo access:** yes. All load-bearing claims below were checked against the working tree at HEAD `9f884f2` (docs-only commits so far; the plans describe files to be created, which is why many acceptance criteria are marked `[HEAD=error:2]` — file absent — that is consistent, not an error).

**Coverage:** all 14 plan ids reviewed below, each with its own section; requirement→plan coverage (NODE-01..03, STEAL-01..05, API-01..05) is complete with no orphan requirement and no plan without a requirement anchor.

---

## 03-01

**Summary** — Creates the `node` role skeleton (validation + self-steal route drop-in), `playbooks/node.yml`, and a container-tier Molecule scenario running the real playbook. Verified claims: `scripts/check.sh:74` currently has `playbooks/(panel|site)\.yml` (the regex extension is real and needed); `roles/edge/templates/00-edge.yml.j2:6` already renders `sniStrict: true` (so "do not duplicate" is correct); `roles/edge/tasks/route.yml` supports `tasks_from: route` with `state absent` (used later by 03-14); the two-play `playbooks/panel.yml` shape exists to copy; the container converge pattern (converge.yml vars) matches `extensions/molecule/container/converge.yml:4-25`.

**Strengths**
- Hard-pinning `xvpn_edge_https_address: "127.0.0.1:8443"` in play vars beats inventory host_vars in Ansible precedence — the loopback constraint cannot be silently overridden via inventory (D-13 enforced structurally, not by convention).
- Negative-case infrastructure (`# xvpn_negative_case:` + derived `xvpn_negative_expected` list, no literal count in the assert) is extensible without edit-among-plans churn; later plans (03-04, 03-08) correctly account for the growing count (9→10→11→13).
- Precondition grep against `03-RESEARCH.md` markers operationalizes the D-14 spike gate at plan-execution time, not just in prose.
- Injection guard for `xvpn_node_domain` (backtick case) tested before rendering — matches the threat model row T-03-01.

**Concerns**
- **LOW**: `verify.yml` hardcodes `/var/lib/xvpn/rw-edge/...` paths; fine today since `xvpn_podman_rootless_home_root` defaults there, but a scenario override of the home root would break the verify silently. Acceptable.
- **LOW**: `xvpn_node_state: absent` interim refusal is correct now, but the Plan 03-14 replacement of that assert must keep the same negative-case id (`node-state-absent`) — 03-14 indeed plans only a message change; coordination is sound but fragile (two plans touch one assert).
- **MEDIUM (schedule, not correctness)**: CI-wide acceptance requires *both* `lint` and `molecule-container` workflows green via `ci_watch.sh` on every plan; the node leg adds a third scenario to that matrix from wave 1, lengthening every subsequent plan's verify loop.

**Suggestions**
- Document in the role defaults that `xvpn_edge_https_address` is pinned by `playbooks/node.yml` and changing the port requires editing the playbook (D-13 says "or the port the spike chooses" — operators should know inventory cannot change it).
- Add the id `node-domain-empty` as an explicit negative case for the required-variable pre-task (currently only covered implicitly by the playbook assert).

**Risk Assessment** — LOW. Rendering-only plan, no runtime behavior claimed, guard mutations (no `roles/edge` modification) are verifiable via `git diff` exactly as stated.

---

## 03-02

**Summary** — Converts the research spike into a push-gated regression script (`scripts/selfsteal/`) with 9 cases on the production templates. The Pebble approach is validated against the existing `scripts/gate/run.sh:79-89` (Pebble `httpPort: 8080` + challtestsrv with `-http01 ""` + DNS at 8053), so the plan's claim that HTTP-01 works with web entrypoint on `:8080` and Traefik in host networking follows a proven in-repo pattern, not a new invention.

**Strengths**
- Renders production templates (`traefik.yml.j2`, `00-edge.yml.j2`, `node-selfsteal.yml.j2`) instead of re-typed copies — the gate actually protects the shipped code path.
- QA-05 will genuinely catch `render.yml`: the filter regex `traefik\.yml\.j2` at `scripts/check.sh:74` matches the renderer, and `xvpn_edge_acme_ca: custom` is set — verified the guard logic applies.
- Keys/UUID/shortId generated at runtime; explicit decision *not* to add a `.gitleaks.toml` allowlist is consistent with `.gitleaks.toml:63-74` (the only project allowlist is for `scripts/gate/` fixtures).
- Deliberate-break proof (`break=sni-strict` → `FAIL foreign-sni`) prevents the classic "test that cannot fail".

**Concerns**
- **MEDIUM**: the action text embeds an ordering correction mid-numbering ("(Runs after the Xray server of step 6 is listening… execute step 6 before this step.)" between steps 5 and 6). Renumber the steps; an executor following the list literally will issue ACME while Xray doesn't hold 4443 yet, producing a subtly weaker proof.
- **MEDIUM**: 9 cases incl. container start/stop and restarts make this the slowest push workflow; it runs on *every* push with no path filter (deliberate, per the gate decision), but binary downloads per run (Xray zip ~25 MB, Pebble) will add minutes and network flakiness. No caching strategy is specified.
- **LOW**: `xver1-mismatch`/`xver1-proxyprotocol` mutate only the work-dir copy — good — but the "restore" step after xver1-proxyprotocol is a manual sequence; a failed restore poisons subsequent runs in the same job only (workdir is per-run), so impact is bounded.

**Suggestions**
- Cache the Xray/Pebble downloads with `actions/cache` keyed on the sha256 to cut runtime and flakiness.
- Renumber steps so the execution order is linear (Xray server setup before the cert wait).

**Risk Assessment** — MEDIUM. The protocol semantics were executed at research time (high confidence in feasibility), but the script itself is the most complex new shell artifact in the phase and every case must pass in CI deterministically.

---

## 03-03

**Summary** — Decoy mechanism: selection chain, filetree-based install with prune, strict-404 nginx mode, first `studio` template; Panel default page provably unchanged. Verified: `sha256sum roles/edge/files/decoy/index.html` = `23058096c8cfee85dc93123782ca96719293b09b55aad6e91d60b1b25a64c379` — **matches the plan's pin exactly**; the current single copy task to be replaced is `roles/edge/tasks/main.yml:110-117`; catch-all `try_files $uri $uri/ /index.html;` exists at `roles/edge/templates/decoy-nginx.conf.j2:14`.

**Strengths**
- Guard acceptance `git diff --name-only 9943e20..HEAD -- roles/edge/files/decoy/index.html` empty is a strong, mechanical no-drift proof for D-12.
- The no-external-URL grep guard is correctly written (`grep -rEc … | grep -v ':0$' | wc -l == 0` — with `-c`, every file is listed, so filtering `:0` lines is the right idiom), unlike the subtly wrong variants this kind of check usually takes.
- Filetree (already pinned: `community.general` in requirements.yml, verified plugin path in research) with explicit skip of `link` state addresses T-03-32 (symlink exfil) at the mechanism level.

**Concerns**
- **MEDIUM**: prune correctness depends on the "desired list" (rendered names + parent dirs) being computed identically to the install step, including the `.j2` → rendered-name mapping and directory entries. A mismatch deletes or keeps the wrong files. The plan describes both but the invariant lives only in prose.
- **MEDIUM (time-bounded, acknowledged)**: interim `xvpn_edge_decoy_templates: [studio]` means hash selection is degenerate until 03-04 lands the final list. Since waves are serial and nothing ships between plans, risk is nil *if* 03-04 completes; if 03-03 merged and the phase stalled, deployed nodes would all be `studio`. The assumption documents this — acceptable.
- **LOW**: `favicon.ico` committed as a binary generated "once with python3 struct" — reproducibility of the committed artifact is not required, but a generation one-liner in the SUMMARY would help future edits.

**Suggestions**
- Have `decoy.yml` compute the desired set once into a fact used by *both* install and prune so the invariant is structural.
- Pin the selection formula in a unit-testable filter or a doc example (`sha256('node.xvpn.test')[:8] mod 4`) so node verify and role cannot diverge.

**Risk Assessment** — LOW-MEDIUM. Mechanism is standard; the prune/install consistency is the only real hazard.

---

## 03-04

**Summary** — Completes the decoy story: three more templates, final sorted list, gate cases `decoy-template`/`decoy-404` serving through Reality, explicit choice, operator directory, brand escaping. Builds directly on 03-03's mechanism and 03-02's gate.

**Strengths**
- Pairwise-distinct CSS acceptance (`sha256 … style.css | sort -u | wc -l == 4`) is a concrete anti-fingerprint check for T-03-07 rather than a style guideline.
- The negative-case count bookkeeping (10 ids) matches the file's state after 03-01's 9 + this plan's 1 — cross-plan arithmetic verified.
- Gate bodies compared against rendered files (index/404 equality) — proves the served bytes, not just status codes.

**Concerns**
- **MEDIUM**: append-only+sorted invariant of `xvpn_edge_decoy_templates` is enforced only by comment and assumption; a future contributor inserting a template re-maps every existing node's site silently (the exact drift D-10 exists to avoid). One `assert` in `decoy.yml` (`list == list | sort`) or a check.sh guard would make it structural.
- **LOW**: the operator-directory verify uses `delegate_to: localhost` tempfile — works, but the controller path must exist on the executor; fine in molecule, will fail if someone runs verify standalone without controller perms. Minor.
- **LOW**: `argument_specs` choices list must be regenerated whenever the list changes (two places to edit); the unknown-template assert covers drift, so acceptable.

**Suggestions**
- Add the sorted-list assert with a message pointing at the D-10 rationale.
- Consider a gate case iterating all four templates (render ×4, 200+404 each) — cheap, closes the "only node.test's template is proven through Reality" gap.

**Risk Assessment** — LOW. Content work (HTML/CSS) plus one gate extension; no new mechanisms.

---

## 03-05

**Summary** — Panel API client (`module_utils`), doc fragment, `remnawave_node_secret` module, action group, stdlib fake-Panel unit tests wired into `check.sh`, no_log checker extension. Verified extension points: `scripts/check_no_log.py:14-30` SENSITIVE list exists as described; `meta/runtime.yml:1-2` currently only `requires_ansible` (action_groups addition is real work); `check.sh` already creates the `.ansible/collections` symlink (lines 48-49), so the unit tests' collection import path is sound.

**Strengths**
- The no-token-argument rule (`api_token_file` only) plus the `grep -Ec 'api_token[^_]' == 0` acceptance is a clean structural privacy guarantee (token never crosses to the controller), matching the Phase 2 D-09 lineage.
- Client refuses non-loopback plain http *before reading the token* — correct ordering for a secret-handling module; unit-tested.
- `guard_node_name` semantics (no keygen when the Panel node already exists) is the right primitive for 03-07's "generate-once / never silently re-key" story.
- Legitimacy seam respected: stdlib `unittest` instead of pytest (rated SUS), recorded with rationale.

**Concerns**
- **MEDIUM**: running a collection module as a bare subprocess requires `ansible.module_utils.basic` import machinery to resolve from the installed ansible package; this works for simple modules but any use of `AnsibleModule` internals that expect the Ansiballz environment (e.g., `console_log` handling, `_ansible_*` param injection) can behave subtly differently from a real run. The harness approach is common and probably fine, but the first real delegated execution (03-07, VM tier) is the first *true* validation — a module bug found there costs a wave.
- **MEDIUM**: the SENSITIVE addition `r"\bsecret_key\b"` is broad — any future role var containing `secret_key` (even a non-secret path like `xvpn_node_secret_path`) will force `no_log` on unrelated tasks. Self-inflicted friction risk, not a security hole.
- **LOW**: check-mode behavior with `guard_node_name` set is under-specified (does the read-only `/api/nodes` GET happen in check mode? Plan says the guard GET is "read-only, also in check mode" — fine — but then `node_exists: true` in check mode should arguably suppress `changed: true`; current spec would report `changed: true, node_exists: true`? The truth says check mode returns `node_exists: false` unconditionally). Ambiguity; executor should resolve in favor of the guard GET result.

**Suggestions**
- Spell out the check-mode + `guard_node_name` interaction matrix (4 combinations) in the module doc.
- After 03-07 lands, add one VM-tier assert that the subprocess-tested keygen field name matches reality (the assumption already demands recording it in the SUMMARY — good).

**Risk Assessment** — MEDIUM. New Python surface area in a YAML-centric repo; mitigated heavily by unit tests and the extension of existing checkers.

---

## 03-06

**Summary** — Two-VM Molecule stand (Panel VM + node VM, enforcing SELinux, per-VM Pebble), proving the loopback certificate for the node domain and loopback-only binding from another host. Verified: `extensions/molecule/vm/tasks/pebble.yml` exists and the parameterization (`xvpn_prepare_hosts_names | default(...)`) preserves the vm scenario byte-for-byte; `extensions/molecule/shared/verify_runtime.yml:298-308` has the AVC-marker mechanism the plan reuses; `extensions/molecule/shared/verify_edge.yml:18` shows the roots/0 pattern.

**Strengths**
- Cert gate probe uses `-verify_hostname` + `-verify_return_error` + Pebble root from the prepare step — a real chain validation, not `--insecure`.
- Negative connect to 8443 from the Panel VM *and* an `ss` assertion that 8443 binds only 127.0.0.1 — two independent proofs of D-13 in the VM.
- Reusing the AVC-marker + `ausearch` machinery means the "zero AVC" claim is measured from the prepare marker, not since boot (avoids false passes from earlier noise).

**Concerns**
- **HIGH (feasibility)**: two Vagrant/libvirt VMs (4096 + 2048 MB) plus host overhead on a standard GitHub runner (~7 GB RAM, 2 vCPU) is tight to over budget; libvirt + Vagrant + two concurrent VMs with KVM may OOM or swap-thrash. The plan carries a 90-minute runtime checkpoint but no memory budget checkpoint. This is the single most likely plan to fail in CI for environmental reasons.
- **MEDIUM**: `vars/node-vm.yml` references `hostvars['node']['ansible_facts']['default_ipv4']` — hardcoded platform name `node` and requires facts gathered before the var is first *used* (it is lazily evaluated, so it works, but only because usage is inside plays after gather). Brittle if the platform is renamed.
- **LOW**: HTTP-01 for `node.xvpn.test` is validated locally on the node VM via `/etc/hosts` → 127.0.0.1 (assumption). Sound, but it means the "DNS points at this host" precondition of production is only simulated; the gate failure message from 03-08 still tells operators to check real DNS — consistent.

**Suggestions**
- Add an explicit memory check to the workflow (fail fast with a clear message if the runner can't host both VMs), or pre-define a split (two scenarios) as the fallback instead of discovering it at 03-06 execution time.
- Derive the node platform name into a var (`xvpn_node_vm_name: node`) used by both molecule.yml and vars.

**Risk Assessment** — MEDIUM-HIGH on execution feasibility, LOW on design. Everything else on this stand is proven Phase 2 machinery.

---

## 03-07

**Summary** — remnanode rootless Quadlet with `Network=host`, generate-once `SECRET_KEY` via the 03-05 module (delegated, `no_log`), explicit `xvpn_node_rekey` opt-in, interrupted-first-run convergence. The refusal message ("node.env missing but node exists in Panel") matches the established "secrets never rotate silently" pattern and closes the T-03-38 hazard.

**Strengths**
- Single shared condition `xvpn_node_secret_wanted` (set_fact + module + fail + template all gated on it, acceptance `>= 4` occurrences) prevents the classic drift where the module call and the file write disagree.
- `grep -Ec 'slurp|fetch:' secret.yml == 0` mechanically enforces "token never travels to the controller" (T-03-13).
- The "Interrupted first run" block is explicitly scheduled for removal in 03-12 with a comment explaining why — honest lifecycle management of a temporary test.
- Quadlet template forbids `AddCapability|SecurityLabelDisable|PublishPort|privileged` by acceptance grep, matching Phase 1 D-20/FND-05 discipline.

**Concerns**
- **MEDIUM**: `node.env` is written only when `xvpn_node_secret_wanted`; if it exists, a *changed* `xvpn_node_api_port` will never be re-rendered into the env file (the template is skipped), so `NODE_PORT` silently stays stale while firewalld opens the new port. One-variable edge case, but a real operator trap.
- **MEDIUM**: inter-play race — edge (rw-edge user) and remnanode (rw-node) are separate user managers; boot ordering cannot be expressed (research Pitfall 1). The plan accepts seconds of post-reboot failure. Fine, but `Restart=always` on remnanode + Traefik availability is the only recovery; worth an explicit README line (03-14 covers Traefik-down semantics in the gate, README could mention it).
- **LOW**: assumption A1 (env-file literal value handling) correctly has a fallback (Podman secret) pre-declared.

**Suggestions**
- Add a stat/compare on `node.env` *content* for `NODE_PORT` (not the secret) when the file exists, so a port change converges without touching `SECRET_KEY`.
- When `xvpn_node_register: false` and env is missing, service.yml will deploy a unit whose `EnvironmentFile` is absent → unit fails to start. Either assert the combination (register false + activate true + no env) or document it.

**Risk Assessment** — MEDIUM. Rootless/host-net/SELinux behavior of the node image is the phase's residual unknown (A3/A5), correctly fenced by the checkpoint rule.

---

## 03-08

**Summary** — STEAL-05 cert gate before 443 opens; Panel-only rich rule for 2222 with a 3-step source resolution and injection guard; exact-set rich-rule verification. Verified: the `until`+separate-fail pattern matches `roles/panel/tasks/bootstrap.yml` and `scripts/check_until_set_fact.py`'s set_fact restriction; `roles/preflight/defaults/main.yml:22` confirms `xvpn_public_ip` is a role default (invisible via hostvars) — the plan's guarded-lookup assumption is correct and the `grep` acceptance enforcing `default('')` on every read is well aimed.

**Strengths**
- `xvpn_node_activate: false` + `xvpn_node_register: true` rejected at input validation (plus the independent runtime condition on `register.yml` in 03-11) — two guards for D-15, one at parse time, one at execution time.
- Rich-rule exact-set assertion in `verify_common.yml` (ports + forward ports + rich rules not in expected) is the right negative-space test: any *new* open port fails verify.
- NAT hint in both the failure message and a visible debug line — addresses the most common real-world misconfiguration of `xvpn_node_panel_sources` proactively.

**Concerns**
- **MEDIUM (cross-plan)**: source resolution asserts a non-empty list. In 03-14's decommission path, `register` is false and `--limit node` means no Panel hostvars and (per 03-08's design) setup delegation only runs when register is true → resolution yields empty → assert fails → decommission blocked unless the operator supplies `xvpn_node_panel_sources`. The 03-14 plan does not address this. Decommission of a node without explicit sources will require an extra variable, which the README does not currently promise.
- **LOW**: the `api-port-from-controller` negative (timeout from controller) is weak alone — a routing failure also times out — but it is paired with the positive Panel-VM connect, so combined they are meaningful.
- **LOW**: gate installs `openssl` via dnf (idempotent, BaseOS) — fine; in the container tier the gate is skipped so no dnf runs there.

**Suggestions**
- In 03-14 (or here), let the decommission path run the delegate `setup` fallback regardless of `xvpn_node_register`, or document that decommission requires `xvpn_node_panel_sources` when running with `--limit`.
- Consider asserting the gate's `until` loop cannot combine with `set_fact` (already covered by `check_until_set_fact.py` — just confirm the new register var is not named in that checker's blocklist).

**Risk Assessment** — LOW-MEDIUM. The gate logic mirrors a proven pattern; the decommission/source-resolution interaction is the main gap.

---

## 03-09

**Summary** — Three-platform matrix (alma/rocky/oracle) for the two-VM stand plus the gate-failure case and dual-VM AVC checks. Verified: the Rocky box checksum `491cf68af9e485bdd9317051ccfeb68301e86d04476a15b5cfd065d0bd7159ea` matches `extensions/molecule/vm/molecule.yml:30` exactly (copied, not re-derived, as required).

**Strengths**
- Box pins copied verbatim from the Phase 1-approved source; `fail-fast: false` keeps one flaky platform from masking another.
- The gate-failure case asserts *firewall state unchanged* on failure — closing the loop on "gate failure must not open 443" (STEAL-05 prohibition tested, not just asserted).
- Runtime budget rule (90-min checkpoint) inherited explicitly.

**Concerns**
- **MEDIUM**: 3 parallel matrix legs × two VMs each on shared runners multiplies the 03-06 memory concern threefold; also Oracle UEK is called out in project constraints as a default kernel — box `oraclelinux10-libvirt-10.1.710` from yum.oracle.com is an external download with a checksum pinned in vm/molecule.yml (verified present); runtime availability of yum.oracle.com is historically flaky.
- **LOW**: env-var interpolation for box selection in molecule.yml is flagged with a fallback (one platform block per OS) — good; but the fallback changes molecule.yml structure and could silently diverge from vm/molecule.yml. If the fallback triggers, re-check the QA-05 syntax-check still covers the file.

**Suggestions**
- Record per-leg duration in the SUMMARY (already planned) and set a CI-level `timeout-minutes` per leg (planned: 120) — ensure the 90-minute checkpoint alert actually fires before the 120-minute kill.
- Pre-flight the Oracle box URL in the first run with a retry, and note a mirror fallback if yum.oracle.com is unstable.

**Risk Assessment** — MEDIUM, dominated by CI environment risk rather than plan logic.

---

## 03-10

**Summary** — Declared config-profile template (no keys), gate rebuilt from the production template, and `remnawave_config_profile` with key preservation, Panel-mutation pre-apply, redacted diff, check mode. The blocked-CIDR list decision (explicit CIDRs instead of `geoip:private`) is recorded with rationale and Phase 4 implications.

**Strengths**
- Building the gate's Xray server config from the rendered production template is the strongest anti-drift move in the phase: the profile template is exercised end-to-end through Reality on every push.
- Key handling is airtight by construction: desired config has *no* key fields (acceptance grep, case-insensitive); the module deletes any incoming `privateKey/publicKey/shortIds` for managed tags (T-03-37) before filling stored/generated values; unit tests assert over *all* request bodies that override values never appear.
- Check mode placeholder `<generated on apply>` avoids a gratuitous x25519 call and keeps the diff honest.

**Concerns**
- **MEDIUM**: the python mutation of `profile.json` → `xs.json` (set port/listen, inject keys + client, replace DIRECT `finalRules`, insert a routing rule) reimplements, in a script, the same override semantics the VM scenario expresses via `xvpn_node_profile_override` (03-13). Two implementations of "inject test sink" invite divergence; the gate passing is the only guard.
- **MEDIUM**: the assumption "no other Panel mutation besides the three known" is explicitly falsifiable at 03-11's idempotence run — good — but the pre-apply list in `apply_panel_mutations` then grows; module tests must be updated in lockstep (plan does not say where the update lands if a fourth mutation is found in 03-11).
- **LOW**: `xvpn_node_blocked_cidrs` includes `"::1/128"` etc. as quoted strings mixed with unquoted v4 — Jinja `to_json` handles it; cosmetic.

**Suggestions**
- Share the sink-injection logic: have 03-13's scenario override and the gate use one documented shape (the plan already notes "the same shape the VM override uses" — make it literal, e.g. both render from the template + one shared python helper).
- Pre-decide the mutation-update path: a fourth Panel mutation found at 03-11 lands in `module_utils` + `fake_panel` + a new unit test in the same wave (one sentence would do).

**Risk Assessment** — MEDIUM. Highest-assurance plan of the phase in design; complexity concentrated in the gate mutation script.

---

## 03-11

**Summary** — First registration step (config profile) in the role with delegated module calls, key checksum stability across converge/idempotence/drift, override semantics, gate-gated inclusion. Verified: `extensions/molecule/vm/side_effect.yml` exists as the pattern source; converge checksum recording with `force: false` matches the vm scenario convention; `register.yml` inclusion conditioned on `xvpn_node_gate_passed` is the second D-15 guard.

**Strengths**
- The key checksum (`sha256(privateKey + shortIds)`, computed on the Panel host, `no_log`) is the right observable: it proves key stability without ever moving key material.
- `lookup('template', 'config-profile.json.j2')` resolves against the role's templates dir (controller side), and the module runs delegated — the rendered config crosses to the Panel host as task input, not via any file transfer; consistent with the no-fetch/slurp rule.
- Drift + override + restore-to-scenario sequencing in side_effect leaves the stand converged for later plans; the assumption that the override restore reads the scenario var (not a hardcoded empty dict) shows awareness of the 03-13 interplay.

**Concerns**
- **MEDIUM**: recursive `combine` with list replacement means an override setting `routing.rules` silently discards the managed BLOCK rule (the override's rules list replaces it). D-04 grants this, and the module's key deletion still protects keys, but the *security* rule (private-CIDR block) can be removed by inventory — acknowledged as T-03-21/`accept`, documented in README. Reasonable, but consider asserting in the module that a managed tag's reality `target`/`serverNames` cannot be overridden either (currently only keys are stripped; `serverNames` override could de-sync the host record's SNI from the inbound).
- **LOW**: side_effect role runs need the Panel reachable from the node play (module delegation) — the delegated tasks run on the Panel host regardless of the executing play's host; fine.
- **LOW**: drift case PATCHes loglevel "debug" — if a future template changes the default loglevel var name, the drift case's assert needs updating; acceptable.

**Suggestions**
- Consider extending the module's managed-field protection from keys only to `realitySettings.serverNames` (or at least warn) so the host SNI and inbound serverNames cannot diverge via override.
- In the drift case, also assert the Panel-side `xver`/`target` fields survive — the checksum covers keys only.

**Risk Assessment** — LOW-MEDIUM. Real-Panel behavior is the unknown (Panel mutations), and the plan explicitly instrumented the idempotence run to catch a fourth mutation.

---

## 03-12

**Summary** — `remnawave_internal_squad` (union-only) + `remnawave_node` (reconcile + bounded wait with diagnostics), role wiring, foreign-member preservation, not-connected failure, missing-env refusal case. Largest plan by estimate (85k tokens, 12 files).

**Strengths**
- Union-only squad PATCH computed from current state (research Pitfall 6: PATCH replaces the full set) directly prevents the T-03-22 hazard; both unit test and VM block prove it.
- Wait-for-connected lives inside the module with explicit bounds (30×5s default) and a diagnostic message that names the rich-rule variable, the service and the re-key flag — but explicitly *not* "delete node.env" (acceptance `grep -c 'delete it to re-key' == 0` guards the misleading advice out).
- The missing-env-with-registered-node refusal is executed here (03-12), where the precondition (registered node) actually exists — correct placement; and 03-07's temporary "Interrupted first run" block is removed in the same plan, keeping the stand honest.
- Address-collision failure (A034 mapped, message names `xvpn_node_address`) prevents silent duplicate nodes.

**Concerns**
- **HIGH (scope/schedule)**: two modules + fake-Panel extensions (async delete semantics, controllable status fields) + three side_effect blocks + role wiring in one plan. This is the wave most likely to blow past one execution session; a split (modules+tests / role wiring+VM blocks) would reduce blast radius without changing the wave graph.
- **MEDIUM**: failure-diagnostic message text embeds role variable names (`xvpn_node_panel_sources`, `xvpn_node_rekey`) inside a generic module — couples the collection module to this collection's role naming. It *is* this collection, so acceptable, but if the message is the contract, unit tests must pin the exact strings (the VM rescue matches on `not connected` only — fine).
- **LOW**: `wait_connected` skipped in check mode (`"{{ not ansible_check_mode }}"`) — correct; verify the arg_specs document it.

**Suggestions**
- Split into 03-12a (modules + unit tests) and 03-12b (register.yml steps + VM side_effect blocks); the dependency graph barely changes.
- Pin the diagnostic message's stable substrings in unit tests so a wording edit doesn't break the VM rescue matching.

**Risk Assessment** — MEDIUM-HIGH for schedule; LOW for design correctness.

---

## 03-13

**Summary** — `remnawave_host` (profile-keyed single host, remark disambiguation), full out-of-phase-goal e2e: real Xray client from a real subscription link, private-destination negatives, scanner/SNI matrix against the real node from the Panel VM. Largest scope (90k tokens).

**Strengths**
- The host idempotency key (hosts bound to the node's profile; remark disambiguation; several-matches → fail, never create) directly answers D-07's open choice with a rule that cannot create duplicates (research-verified against `prisma/schema.prisma`: no unique constraint — so this client-side rule *is* the only guard; correctly designed as fail-closed).
- Client e2e uses the genuine Panel-issued `vless://` link (not hand-built config) — validating host fields (SNI, fingerprint, flow) end-to-end through the subscription path.
- The test sink on node loopback:18090 with an override-supplied `finalRules` allow is exactly the destination class the private block must deny — the negative cases (`client-private-node`, `client-private-lan`) therefore test the real control, not a synthetic one. Public egress case `client-public` cleanly separates CI network failure from collection defect (flagged assumption).
- Scanner matrix runs *from another host* against the real node — the first place STEAL-03 is proven outside the gate's loopback harness.

**Concerns**
- **HIGH (scope)**: same as 03-12 — module + role wiring + prepare (Xray install, sink unit) + two shared verifiers + scenario override + remark-rename block. Most complex wave; consider splitting host-module work from the e2e verifiers.
- **MEDIUM**: creating a Panel user in the scenario (test-only, documented) writes to the Panel DB from the verify; repeated CI runs get-or-create, but the user is never cleaned up — in a throwaway VM acceptable, but the assumption should note user cleanup on decommission-style reruns is not attempted (harmless).
- **MEDIUM**: `github.com` egress from the *node VM's* Xray freedom outbound — CI runner egress is asserted, but the request egresses from the node VM via the libvirt network; any runner-level DNS/IPv6 quirk inside the VM shows up as `client-public` flakiness. The fallback interpretation (network outage ≠ defect) is documented, but repeated flakes will erode trust in the gate.
- **LOW**: the subscription decode must handle the raw-link format and User-Agent rules of 3.4.11 — flagged in read_first; a format change in a future pin would break only this verifier.

**Suggestions**
- Split: 03-13a (`remnawave_host` + unit tests + register step), 03-13b (client e2e + SNI matrix).
- Add a retry/second-target (e.g., `https://www.gnu.org` or a pinned-IP HTTPS check) to `client-public` to reduce egress flakiness.

**Risk Assessment** — MEDIUM-HIGH scope risk; design is the strongest of the phase for the security-critical requirement (NODE-03/STEAL-03 real-world proof).

---

## 03-14

**Summary** — Decommission (flag-gated, ordered host→node(polled)→profile, cascade-verified against the full squad list), `--check --diff` honesty on the real Panel, README node section, `site.yml` import. Verified: `README.md:58` contains "node plays are added later" (the expected replacement target exists); `roles/panel/tasks/subpage.yml` has the stop/absent/route-absent pattern referenced; `playbooks/site.yml` currently has the "Phase 3 appends node.yml" comment.

**Strengths**
- Decommission order implements research Pitfall 5 exactly (host before profile to avoid `SetNull` orphans; poll node deletion before profile; no squad PATCH because cascade handles it) and *proves the cascade* by asserting the old inbound uuid is absent from **every** squad in the full list — not just Default-Squad. The `xvpn-molecule-decom` non-default squad makes the cascade proof meaningful.
- D-06 integrity is preserved while still cleaning up the test squad: the DELETE is explicit test-harness work with route verification instructions and is deliberately excluded from the role/module semantics — the survival assert of the squad itself proves the role never deletes squads.
- README guard `grep -ci 're-key by deleting|delete node.env to re-key' == 0` encodes the orchestrator decision (opt-in flag is the only re-key procedure) as a checkable invariant — subtle and good.
- `--check --diff` honesty test (changed=0 converged; drift previewed without write; no key in output) is the last mile of API-01.

**Concerns**
- **MEDIUM**: the nested `ansible-playbook --check --diff` run inside side_effect is the flakiest test in the phase — any module that reports spurious `changed` in check mode (common: `command`/`shell` without `check_mode` handling, `firewalld` offline quirks) fails the changed=0 assertion. The plan treats this as a feature (it *should* surface noise), but the fix loop could be long; the MOLECULE_INVENTORY_FILE assumption flags awareness but not a mitigation.
- **MEDIUM**: decommission's rich-rule removal depends on 03-08's source resolution which (see 03-08 review) requires non-empty sources — with `--limit node` and no explicit sources, decommission fails. The README documents `xvpn_node_panel_sources` for *deployment*; it should also state it for decommission runs.
- **LOW**: preflight `end_host` skip for absent state — correct, but `end_host` in a pre_task requires `gather_facts` already done or it errors? `meta: end_host` works in pre_tasks; fine.

**Suggestions**
- In the "Check and diff" block, run the check against the converged inventory *twice* (idempotence-style) and only then assert changed=0, to separate first-check-mode noise from real drift.
- Add one README line: decommission with `--limit <node>` requires `xvpn_node_panel_sources` (or run without limit).
- Record the internal-squads DELETE route verification in the SUMMARY as planned (executor instruction present — hold them to it).

**Risk Assessment** — MEDIUM. Logically the safest plan (all destructive paths fenced and tested), operationally the most assert-dense.

---

## Cross-plan comparison and phase-level assessment

**Ordering / dependency integrity** — Sound. The wave graph is strictly linear and each dependency is real: 03-01 (render) → 03-02 (protocol gate on those templates) → 03-03/03-04 (decoy, extends both role and gate) → 03-05 (modules foundation) → 03-06 (VM stand) → 03-07 (remnanode needs stand + secret module) → 03-08 (gate/firewall needs running service) → 03-09 (matrix over the finished stack) → 03-10 (profile module; gate rebuild) → 03-11 (role registration) → 03-12 (node/squad) → 03-13 (host + e2e) → 03-14 (decommission + docs). Cross-plan state handoffs (negative-case counts 9→10→11→13; the 03-07 temporary block removed in 03-12; the 03-11 override restore surviving 03-13's override) are all accounted for explicitly — verified arithmetic.

**Requirement coverage** — Complete. Every NODE/STEAL/API requirement maps to at least one plan with an executable verification; API-04's failure policy, the geoip question, the test-sink question and the kenyawest decision from the research Open Questions all landed in specific plans with `<reversibility>`/assumption records.

**Security posture** — Strong and consistently mechanical: no_log/redaction enforced by grep and by unit tests over request bodies; key material never on the controller; loopback constraints pinned at play-var precedence; firewalld exact-set verification; injectable strings (domain, source IPs) regex-gated with executed negative cases; destructive paths flag-gated with executed refusal cases. The residual risks (Traefik 404 on :80 unknown Host; `xver:1` exposure needing proxyProtocol) are documented rather than hidden, and the latter is tested both ways (mismatch fails, pairing passes).

**Top phase-level risks (ranked)**
1. **CI environment** (03-06/03-09): two-VM libvirt stand memory/runtime on shared runners — the most probable source of non-logic failures. Mitigation exists (checkpoints) but no pre-planned split.
2. **Plan size** (03-12, 03-13): 85–90k token estimates with module + role + scenario work each; both are natural split candidates.
3. **Check-mode noise** (03-14): the `--check --diff` honesty assertion will surface any check-mode-impure module used by `node.yml`; treat the resulting fix list as expected work, not a plan defect.
4. **Divergence of sink-injection logic** (03-02 vs 03-13): two implementations of the test-sink override shape.
5. **Decommission + `--limit` + source resolution** (03-08 × 03-14): operator-facing interaction not yet documented.

**Overall risk: MEDIUM** — unusually well-evidenced plans (the executed spike, contract read from pinned source, every guard mutation greppable), with residual risk concentrated in CI feasibility and execution scope rather than architecture. The D-14 escalation clause remains a correctly preserved tripwire: if 03-02's gate cannot pass on Traefik, the plan stops instead of silently swapping proxies — that is the right failure mode for this phase.


---

## Qwen Review

I now have sufficient context to provide a thorough review. Let me compile my findings.

---

# Phase 3 Plan Review

## Overall Assessment

This is an exceptionally thorough set of 14 plans for deploying a Remnawave Node with VLESS Reality self-steal and automatic Panel API registration. The plans demonstrate deep understanding of the existing codebase, consistent use of established patterns, and meticulous attention to security, idempotency, and testability. The wave-based dependency structure is sound, and the research phase has already de-risked the highest-technical-risk element (Reality → Traefik loopback).

---

## 03-01

**Summary:** Creates the `node` role skeleton with input validation, the self-steal drop-in route template, `playbooks/node.yml`, and a container-tier Molecule scenario. Well-scoped at 14 files with clear analogs to existing Panel role patterns.

**Strengths:**
- Correctly reuses the edge role's `tasks_from: route` pattern (verified at `roles/edge/tasks/route.yml:1-35`) without forking — the route interface accepts exactly the inputs the plan specifies (`xvpn_edge_route_name`, `xvpn_edge_route_src`, `xvpn_edge_route_state`).
- Input validation mirrors `roles/panel/tasks/main.yml:1-35` (FQDN regex, example domain rejection, getent user check, image tag assert) — proven pattern.
- The `xvpn_node_tag_sanitized` regex `[^A-Za-z0-9_-]` correctly handles the inbound tag validator (no spaces, no commas), while `xvpn_node_name_sanitized` allows spaces for profile names — matches RESEARCH Pitfall 4 constraints.
- The negative-case framework with `# xvpn_negative_case:` markers and derived count from `xvpn_negative_expected` list is elegant and extensible.
- `playbooks/site.yml` currently contains only a comment `# Phase 3 appends node.yml` (verified at `playbooks/site.yml:2`), confirming the plan's decision to defer the import to Plan 03-14.

**Concerns:**
- **MEDIUM:** The plan states `xvpn_node_inbound_tag` default is `"vless-reality-{{ xvpn_node_tag_sanitized }}"` in `defaults/main.yml`, but `xvpn_node_tag_sanitized` is defined in `vars/main.yml`. Ansible resolves defaults before vars in the precedence chain, but since `xvpn_node_inbound_tag` is itself a default that references a var, the templating is lazy and will resolve correctly at task execution time. However, this cross-file dependency between defaults and vars is subtle and should be documented with a comment.
- **LOW:** The plan's `xvpn_node_profile_name` default `"{{ xvpn_node_name_sanitized }}"` means a default `inventory_hostname` like `node1.example.com` becomes `node1-example-com` (dots replaced by dashes). The plan asserts length 2..30, but `node1-example-com` is 18 chars — fine. However, very long hostnames could produce profile names exceeding 30 chars after sanitization; the assert catches this but the error message should suggest `xvpn_node_profile_name` override explicitly.

**Suggestions:**
- Add a comment in `defaults/main.yml` noting that `xvpn_node_inbound_tag` and `xvpn_node_profile_name` depend on vars from `vars/main.yml` and are lazily evaluated.
- Consider adding a `xvpn_node_name` length assert message that says "set xvpn_node_name or xvpn_node_profile_name to a shorter value".

**Risk Assessment:** LOW — well-understood patterns, minimal new surface area, container-tier only.

---

## 03-02

**Summary:** Converts the executed research spike into a durable CI regression gate (`scripts/selfsteal/`) with 9 test cases covering valid SNI, foreign/absent SNI, client e2e, private-blocked, Traefik-down, and xver pairing. Mirrors the existing `scripts/gate/` structure precisely.

**Strengths:**
- Correctly mirrors `scripts/gate/run.sh` structure: tool gate, port preflight, `mktemp -d` + trap cleanup, pinned Pebble with sha256, image pins read with `sed` from `roles/edge/defaults/main.yml` (verified at line 5: `xvpn_edge_traefik_image: docker.io/library/traefik:v3.7.20`).
- Keys generated at runtime only — no committed secrets. The acceptance grep for `privatekey:` literals is a good guard.
- The deliberate-break proof (`XVPN_SELFSTEAL_BREAK=sni-strict`) mirrors `scripts/gate/run.sh:33-36` (`XVPN_GATE_BREAK=auth-regex`) — proven pattern.
- Xray sha256 `b651f7e1d9966ee2c1b1ee1bf8b52c72771824d3065dce96bbc8bcc19ed95f82` matches the RESEARCH document and published `.dgst`.
- The `render.yml` correctly reads production templates from role paths rather than re-typing them — any template regression is caught automatically.

**Concerns:**
- **MEDIUM:** The gate uses `podman run --network host` for Traefik, which means the gate's Traefik binds the runner's actual ports 8080/8443. The port preflight checks 8080, 8443, 4443, etc. — but the gate's Xray server binds port 4443 (standing in for 443). If a stale process holds 4443, the preflight catches it. However, the gate's `challtestsrv` uses port 8053 for DNS — this is also in the preflight list. Good.
- **MEDIUM:** The `render.yml` renders `node-selfsteal.yml.j2` which doesn't exist yet (created by Plan 03-01). The plan correctly depends on 03-01, but the `render.yml` also needs `roles/node/vars/main.yml` for `xvpn_node_blocked_cidrs` (Plan 03-10 adds this). For Plan 03-02, the template only needs `xvpn_node_domain` which is passed as an extra var — this is correct.
- **LOW:** The gate downloads Xray from GitHub releases on every CI run. With a 25 MB zip and `--retry 3`, this adds ~10-20s to the job. Caching could help but isn't worth the complexity at this stage.

**Suggestions:**
- Consider adding a `--retry 3` delay progress indicator so CI logs show download progress.
- The `cleanup()` function should also kill the `python3 -m http.server` sink PIDs — the plan mentions this ("killing background PIDs") but the sink PIDs are started in step 7, after the trap is set. Ensure they're added to `PIDS=()`.

**Risk Assessment:** LOW — mirrors proven `scripts/gate/` pattern, no role changes, pure test infrastructure.

---

## 03-03

**Summary:** Extends the shared `edge` role with the decoy template mechanism: selection chain (template > operator dir > hash > Panel default), file-by-file install with prune, strict-404 nginx mode, and the first bundled template `studio`. 10 files modified.

**Strengths:**
- The selection chain priority order (explicit template > operator dir > hash > Panel default) correctly implements D-10, D-11, D-12.
- The `filetree` lookup + prune pattern is the right choice — `synchronize` would need rsync on both ends.
- Panel no-drift proof: the default `roles/edge/files/decoy/index.html` is served byte-for-byte when no node variables are set. The sha256 checksum `23058096...` in the acceptance criteria is a concrete guard against accidental edits.
- The `xvpn_edge_decoy_strict` boolean cleanly separates Panel catch-all mode from node strict-404 mode in the same nginx template.
- The append-only sorted template list invariant (D-10) is documented in `vars/main.yml` — critical for preventing node re-mapping.

**Concerns:**
- **MEDIUM:** The plan modifies `roles/edge/tasks/main.yml` to replace the existing `Edge | install the decoy site` task (lines 96-126 verified) with `include_tasks: decoy.yml`. The existing task uses `ansible.builtin.copy` with `src:` and `directory_mode:`. The new `decoy.yml` uses `filetree` + per-file `copy`/`template`. This is a behavioral change for the Panel scenario: the old `copy` created directories with `0755` and files with `0644` in one task; the new approach does it file-by-file. The plan must ensure the Panel scenario's existing verify (which checks the decoy body sha1) still passes. The `verify_edge.yml` at line 90-104 checks body checksum — this should still work since the same `index.html` is served.
- **MEDIUM:** The `favicon.ico` is described as "a valid 16x16 ICO produced once with python3 struct, committed as a binary". Binary files in git are fine but should be small. A 16x16 ICO is typically ~1KB. The plan should specify a maximum size to prevent accidental bloat.
- **LOW:** The `xvpn_edge_decoy_templates: [studio]` interim list (Plan 03-03) changes to `[blog, business, maintenance, studio]` in Plan 03-04. Any node deployed between these two plans would get `studio` by hash; after Plan 03-04, the same domain would get a different template (since the list length changes from 1 to 4, the modulo changes). This is acceptable since Plan 03-04 runs in the same phase before any production deployment, but it should be noted.

**Suggestions:**
- Add a size guard for `favicon.ico` files (e.g., assert < 5KB) in `check.sh` or `decoy.yml`.
- Consider adding a `decoy.yml` task that logs which template was selected (at `debug` level) for operator visibility.

**Risk Assessment:** LOW-MEDIUM — modifies the shared edge role but with careful backward compatibility guards.

---

## 03-04

**Summary:** Completes the decoy template set (blog, business, maintenance), adds gate cases for decoy-template and decoy-404, and proves explicit choice, operator directory, brand escaping, and unknown-template rejection.

**Strengths:**
- The final sorted list `[blog, business, maintenance, studio]` with append-only invariant is well-documented.
- Pairwise-distinct CSS check (`sha256sum ... | sort -u | wc -l == 4`) prevents accidental fingerprint sharing between templates.
- The brand escape test (`<b>Acme</b>` → `&lt;b&gt;Acme&lt;/b&gt;`) validates HTML escaping.
- The gate now uses `include_tasks: ../../roles/edge/tasks/decoy.yml` — proving the production decoy mechanism end-to-end through Reality.
- Operator directory test uses `ansible.builtin.tempfile` on the controller + prune verification — thorough.

**Concerns:**
- **MEDIUM:** Writing 3 complete multi-page HTML templates from scratch is a significant amount of content that's hard to review for quality, external resource references, and cross-template fingerprint uniqueness. The grep guards (`https?://`, `xvpn`) catch the most obvious issues, but subtle fingerprinting (identical CSS class names, identical HTML structure comments, identical JS patterns) could slip through.
- **LOW:** The `decoy-template` and `decoy-404` gate cases compare the served body against the rendered template file. The comparison method (body equals rendered `index.html`) is exact — but the rendered file is a Jinja2 template, so the comparison must be against the rendered output, not the `.j2` source. The plan says "body equals the rendered `index.html`" which implies the rendered version. This should work since `decoy.yml` renders `.j2` files to the site directory.

**Suggestions:**
- Add a check that no two templates share identical CSS class names for their main layout elements (e.g., `grep -h 'class=' roles/edge/files/decoy-templates/*/assets/style.css | sort | uniq -d` should be empty for layout classes).
- Consider adding a `robots.txt` content check to ensure each template has a unique `robots.txt` (or at least a different comment).

**Risk Assessment:** LOW — content-only changes with good grep guards.

---

## 03-05

**Summary:** Creates the Panel API client (`module_utils/remnawave.py`), doc fragment, `remnawave_node_secret` module, action group in `meta/runtime.yml`, and unit tests against a fake Panel. First Python code in the collection.

**Strengths:**
- Correctly uses `ansible.module_utils.urls.open_url` (stdlib-based, no `requests` dependency) — verified as the right choice for targets without pip.
- The `api_token_file` approach (read on the Panel host, never passed as argument) matches Phase 2's D-09 pattern and avoids token exposure on the controller.
- The loopback-only http refusal (`refusing to send the API token over plain http to a non-loopback host`) is a critical safety check, well-tested.
- `guard_node_name` option is a clever design: it prevents accidental re-keying of an existing node by checking the Panel first.
- The `redact()` function with regex `(?i)(private|secret|password|seed|token)` catches all sensitive key names.
- `normalize()` with `json.dumps(sort_keys=True, separators=(',', ':'))` correctly handles Postgres JSONB key reordering.
- The `check_no_log.py` extension with self-test decoys is consistent with the existing pattern at `scripts/check_no_log.py:62-82`.

**Concerns:**
- **MEDIUM:** The plan creates `plugins/modules/remnawave_node_secret.py` but the module name in `meta/runtime.yml` action_groups lists five modules including `remnawave_node_secret`. The plan correctly includes all five names. However, `remnawave_node_secret` is not a "resource" module like the other four — it's a utility module that fetches a secret. The action group name `remnawave` is fine, but the module's `common_argument_spec()` includes `api_url` and `api_token_file` which are also needed by the other four modules. This is correct.
- **MEDIUM:** The fake Panel uses `http.server.ThreadingHTTPServer` bound to `127.0.0.1:0` (random port). The module under test receives the port via `api_url: http://127.0.0.1:<port>`. This is correct but the test must ensure the fake Panel is fully started before the module connects. Using `__enter__` with a thread start and a readiness probe (or a small sleep) is necessary. The plan mentions `FakePanel` context manager — the implementation must ensure thread readiness.
- **LOW:** The plan rates `pytest` as SUS from the "legitimacy seam" and uses stdlib `unittest`. This is fine — `unittest` is sufficient for the test cases described. However, the test output format is less readable than pytest's, which may slow debugging of CI failures.

**Suggestions:**
- Add a `conftest.py`-equivalent setup in `tests/unit/__init__.py` or a `tests/unit/helpers.py` to share the fake Panel setup across test files.
- Consider adding a test for connection timeout (module should fail gracefully when the Panel is unreachable, not hang for 30s).

**Risk Assessment:** LOW — well-designed module infrastructure with thorough unit test coverage planned.

---

## 03-06

**Summary:** Builds the two-VM Molecule scenario `node-vm` (Panel VM + node VM, SELinux enforcing, Pebble ACME) and proves the loopback certificate and loopback-only binding from outside.

**Strengths:**
- Correctly reuses the existing `extensions/molecule/vm/` infrastructure (Vagrant boxes, Pebble tasks, prepare playbook).
- The `xvpn_prepare_hosts_names` parameterization of `tasks/pebble.yml` is a clean extension — the existing vm scenario keeps its current `/etc/hosts` line byte-for-byte.
- The `verify_node.yml` shared verifier with `openssl s_client -verify_hostname -verify_return_error` is the correct STEAL-05 probe.
- The negative connect test (8443 unreachable from Panel VM) proves D-13 loopback-only binding from outside.
- The `xvpn_node_address` override to the node VM IP (Pitfall 10) correctly handles the container DNS resolution uncertainty.

**Concerns:**
- **MEDIUM:** The plan creates a new `extensions/molecule/node-vm/molecule.yml` with two platforms (`panel`, `node`) but uses the AlmaLinux 10 box only (matrix comes in Plan 03-09). The `panel` platform needs `groups: [remnawave_panel]` and the `node` platform needs `groups: [remnawave_nodes]`. The existing `vm/molecule.yml` has three platforms all in `groups: [remnawave_panel]`. The new scenario's `panel` platform needs memory 4096 (Panel stack is heavy) and `node` needs 2048. This is reasonable but the Panel VM also runs the edge (Traefik + decoy), so 4096 is the right choice.
- **MEDIUM:** The prepare playbook adds cross-VM `/etc/hosts` entries. The plan says "a play on all hosts adding `/etc/hosts` lines for the other VM from `hostvars[...]['ansible_facts']['default_ipv4']['address']`". This requires that `gather_facts: true` has run on both VMs before the hosts entries are written. The prepare playbook structure must ensure this — either through two plays (first gather, then write) or through `gather_facts: true` on the first play that writes. The existing `vm/prepare.yml` has `gather_facts: true` on its single play on `all` hosts — the node-vm prepare can follow the same pattern.
- **LOW:** The Pebble issuer root is fetched from `https://127.0.0.1:15000/roots/0` on each VM. Since each VM runs its own Pebble, the node VM's Pebble issues the node domain's certificate, and the Panel VM's Pebble issues the Panel domain's certificate. The verify needs the node VM's issuer root to verify the node's certificate from the Panel VM. The plan handles this correctly by storing the root at `/var/lib/xvpn-molecule/pebble-issuer-root.pem` on each VM.

**Suggestions:**
- Add a comment in `node-vm/prepare.yml` explaining that each VM runs its own Pebble instance and the cross-VM certificate verification requires copying the issuer root.
- Consider adding a `wait_for` for port 80 on the node VM before the cert gate verify, to ensure Traefik is fully up.

**Risk Assessment:** LOW-MEDIUM — new Molecule scenario but reuses proven VM infrastructure.

---

## 03-07

**Summary:** Adds SECRET_KEY generate-once and remnanode Quadlet service to the node role, proves them in the two-VM scenario with zero AVC, and proves re-key only on explicit opt-in.

**Strengths:**
- The `xvpn_node_secret_wanted` single condition shared by all four tasks (module, fail, template, and the set_fact) is elegant — ensures consistency.
- `guard_node_name` prevents silent re-keying of an existing Panel node when `node.env` is missing — critical safety.
- The `remnanode.container.j2` correctly omits `PublishPort` (host network), `AddCapability`, `SecurityLabelDisable` — verified against RESEARCH findings.
- `Ulimit=nofile=524288:524288` matches the Phase 2 finding (1048576 failed for rootless db).
- The `delegate_to: "{{ xvpn_node_panel_host }}"` pattern with `api_token_file` read on the Panel host correctly keeps the token off the controller.
- The re-key opt-in (`xvpn_node_rekey: true`) with the fail-with-diagnostic when `node.env` is missing but the node exists in Panel is well-designed.

**Concerns:**
- **HIGH:** The plan assumes Podman `EnvironmentFile` takes `SECRET_KEY=<payload>` literally without quotes (Assumption A1). The `SECRET_KEY` payload from `GET /api/keygen` is a base64-encoded value that may contain `+`, `/`, `=` characters. Podman's `--env-file` documentation says it reads `KEY=VALUE` lines and does NOT process quotes. However, if the payload contains a newline character (unlikely for base64 but possible for the full keygen response), it would break the env file. The plan should validate that the `secret_key` value is a single line before writing it.
- **MEDIUM:** The `node.env.j2` template writes `SECRET_KEY={{ xvpn_node_secret.secret_key }}` as a raw value. If `xvpn_node_secret.secret_key` contains characters that Podman interprets specially (e.g., `$` for variable expansion), this could cause issues. Podman's `--env-file` does NOT expand `$` variables (unlike `docker run --env-file`), so this should be safe, but it's worth verifying in the VM tier.
- **MEDIUM:** The `restart_stale` task for `remnanode.service` uses `restart_files: ["{{ xvpn_node_env_dir }}/node.env"]`. The `restart_stale.yml` (verified at `roles/podman_rootless/tasks/restart_stale.yml`) compares file mtime with `ExecMainStartTimestamp`. After the first converge, the env file is written and the unit starts. On re-run, the env file is not rewritten (same content, `template` is idempotent), so mtime doesn't change, and `restart_stale` correctly skips the restart. Good.

**Suggestions:**
- Add a `failed_when` or `assert` task after the keygen module that validates `xvpn_node_secret.secret_key` is a single line (no newlines) and matches a base64-like regex.
- Add a comment in `node.env.j2` noting that Podman `--env-file` does not expand `$` variables (unlike Docker).

**Risk Assessment:** MEDIUM — the SECRET_KEY handoff is the most security-critical path in the phase, and the Podman env-file behavior with the keygen payload is an unverified assumption (A1).

---

## 03-08

**Summary:** Adds the STEAL-05 certificate gate and node firewall (443 after gate, Panel-only rich rule for 2222) to the node role.

**Strengths:**
- The gate ordering (route → gate → secret → service → firewall) correctly implements D-15: 443 opens only after the certificate is proven.
- The `xvpn_node_gate_passed` fact gates both 443/tcp and the registration step (Plan 03-11) — defense in depth.
- The Panel source resolution chain (explicit > `xvpn_public_ip` hostvars > delegated `setup`) with IPv4/CIDR regex validation is thorough.
- The `activate false + register true` input assert correctly prevents registration without the gate.
- The negative case `node-activate-register-mismatch` in the container tier proves the assert fires.
- The rich rule uses `ansible.posix.firewalld` which normalizes rules through `Rich_Rule` before comparing (verified at `ansible.posix` 2.2.2 source) — idempotent.

**Concerns:**
- **MEDIUM:** The Panel IP resolution falls back to `ansible.builtin.setup` with `delegate_to` and `delegate_facts: true`. This gathers facts on the Panel host during the node role execution. With `--limit node1`, the Panel host facts may not be gathered yet. The `delegate_facts: true` flag ensures the facts are available in `hostvars` for the current play. However, this adds a `setup` call on the Panel host for every node host in the play. For a single node, this is fine; for many nodes, it's redundant. The plan could cache the result in a play-level variable.
- **MEDIUM:** The `xvpn_node_panel_sources` resolution reads `hostvars[xvpn_node_panel_host].xvpn_public_ip | default('')`. But `xvpn_public_ip` is a default of `roles/preflight` (verified at `roles/preflight/defaults/main.yml:22`). Role defaults are visible through `hostvars` only if the role has been applied to that host. In the two-VM scenario, the Panel VM runs `playbooks/panel.yml` which includes `preflight`, so `xvpn_public_ip` would be in the Panel host's vars. But in production, if the operator runs `playbooks/node.yml` separately (without the Panel play in the same run), the Panel host's role defaults may not be loaded. The plan correctly handles this by falling back to `setup` + `default_ipv4`.
- **LOW:** The `gate.yml` installs `openssl` with `ansible.builtin.dnf`. On a minimal EL10 install, `openssl` may already be present. The `dnf` task with `state: present` is idempotent and fast if the package is already installed.

**Suggestions:**
- Add a `debug` task after Panel source resolution that prints the resolved sources (the plan mentions this for the `default_ipv4` fallback case — good).
- Consider adding a `xvpn_node_panel_sources` validation that rejects private IPs (10.x, 172.16.x, 192.168.x) unless the operator explicitly opts in, since the rich rule is meant for the public-facing Panel IP.

**Risk Assessment:** LOW-MEDIUM — well-structured gate and firewall with good negative testing.

---

## 03-09

**Summary:** Extends the two-VM scenario to a three-platform matrix (AlmaLinux 10, Rocky Linux 10, Oracle Linux 10) and adds the gate failure case.

**Strengths:**
- Correctly copies the box pins from `extensions/molecule/vm/molecule.yml` (verified: Rocky box URL and sha256 `491cf68af9e485bdd9317051ccfeb68301e86d04476a15b5cfd065d0bd7159ea` match at `extensions/molecule/vm/molecule.yml:26-33`).
- `fail-fast: false` ensures all three platforms run even if one fails.
- The `gate-no-certificate` negative case proves that a failed gate leaves firewall state unchanged.
- AVC check on both VMs of every leg — comprehensive SELinux validation.
- 90-minute runtime budget with checkpoint proposal is a practical CI constraint.

**Concerns:**
- **MEDIUM:** The three-platform matrix triples CI cost and time. Each leg runs two VMs (Panel + node) with converge, idempotence, side_effect, and verify. The existing `molecule-vm` workflow already runs three platforms for the Panel-only scenario. Adding three more for `node-vm` means 6 VM-based CI jobs total. The `timeout-minutes: 120` per job is generous but the cumulative CI cost is significant.
- **LOW:** The environment-variable interpolation for box selection (`XVPN_NODE_VM_BOX`, etc.) assumes the Vagrant driver supports this. The existing `vm/molecule.yml` uses static box values per platform, not env-var interpolation. The plan should verify that Molecule's Vagrant driver supports env-var interpolation in `box`, `box_version`, `box_url`, and `box_download_checksum` fields.

**Suggestions:**
- Consider running the three-platform matrix on a schedule (nightly) rather than every push, to reduce CI cost. Push CI could run only the AlmaLinux leg.
- Add a fallback in case env-var interpolation doesn't work: use three separate platform blocks selected by a Molecule `--platform-name` filter.

**Risk Assessment:** LOW — straightforward matrix extension of proven infrastructure.

---

## 03-10

**Summary:** Implements `remnawave_config_profile` module with key preservation, the declared profile template, and integrates the template into the selfsteal gate.

**Strengths:**
- The key preservation algorithm (delete keys from desired → copy from stored or generate once) correctly implements D-02/D-03.
- `apply_panel_mutations()` pre-applies Panel server-side transformations (`cleanInboundClients`, `fixIncorrectServerNames`, `validateOutbounds`) — critical for idempotency.
- The `redact()` function in diff output prevents key leakage in `--diff` mode.
- The selfsteal gate rendering the production `config-profile.json.j2` template is brilliant — any template regression breaks the gate.
- Check mode returns `<generated on apply>` placeholder without calling x25519 — correct behavior.
- The override-key-discarded test (D-03) ensures inventory/vault values can never override Panel-generated keys.

**Concerns:**
- **HIGH:** The plan states `PATCH /api/config-profiles` restarts every node on the profile whenever a `config` is sent. The module compares `normalize(desired)` with `normalize(stored config)` and only PATCHes when different. However, the Panel applies mutations on both create AND update. The `apply_panel_mutations()` function must replicate ALL mutations the Panel applies, or the diff will never converge. The plan lists `cleanInboundClients(false)`, `fixIncorrectServerNames()`, and `validateOutbounds()`, but there may be additional mutations (e.g., `sortXrayConfig` mentioned in RESEARCH Pitfall 4). If any mutation is missed, every run will see a diff and PATCH, restarting nodes on every run.
- **MEDIUM:** The `xvpn_node_blocked_cidrs` list in `vars/main.yml` uses explicit CIDRs instead of `geoip:private`. This is correct (no geo database dependency), but the list must be complete. The plan lists `127.0.0.0/8, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 100.64.0.0/10, 169.254.0.0/16, 0.0.0.0/8, "::1/128", "fc00::/7", "fe80::/10"`. Missing: `::ffff:0:0/96` (IPv4-mapped IPv6), `::/128` (unspecified). These are edge cases but could leak through the block.
- **MEDIUM:** The module calls `GET /api/system/tools/x25519/generate` which returns 30 keypairs. The module takes the first one. If the Panel's keygen endpoint changes the number or order of keypairs, the module still works (it always takes the first). But the plan should document this dependency.

**Suggestions:**
- Add a unit test that verifies `apply_panel_mutations()` produces the exact same output as the Panel for a complex config (e.g., with multiple inbounds, comma-separated serverNames, missing outbounds).
- Add `::ffff:0:0/96` to `xvpn_node_blocked_cidrs` for completeness.
- Consider adding a `xvpn_node_profile_name` regex assert in the module (matching the Panel's `^[A-Za-z0-9_\s-]{2,30}$`) to fail early with a clear message.

**Risk Assessment:** MEDIUM-HIGH — the config profile module is the most complex piece, and the Panel mutation replication is a potential source of idempotency failures.

---

## 03-11

**Summary:** Adds the registration step (config profile) to the node role and proves creation, key stability, drift repair, and override in the two-VM scenario.

**Strengths:**
- The `register.yml` correctly uses `module_defaults: {group/xvpn.remnawave.remnawave: ...}` with `delegate_to: "{{ xvpn_node_panel_host }}"` — clean pattern.
- The `xvpn_node_gate_passed` guard on the include ensures no Panel objects are created before the certificate gate passes.
- The `xvpn_node_profile_override` with `combine(recursive=True)` correctly handles operator JSON overrides while the module discards key overrides.
- The side_effect "Profile drift" block proves drift repair with key preservation on the real Panel.
- The key checksum recording (`reality_checksum_after_first_converge`) is a robust idempotency proof.

**Concerns:**
- **MEDIUM:** The `xvpn_node_profile_override` uses `combine(recursive=True)` which replaces lists. This means an override that sets `routing.rules` replaces the entire rules list, including the blocked CIDRs rule. The operator must include the blocked CIDRs rule in their override if they want to keep it. The plan acknowledges this ("lists replaced") but the README should make this very clear.
- **MEDIUM:** The side_effect "Profile drift" block PATCHes the stored config with `loglevel: debug` through the API. This requires the Panel API token, which is slurped on the Panel host with `no_log: true`. The PATCH body must include the full config (not just the changed field) because `PATCH /api/config-profiles` replaces the config. The plan says "keys untouched" — the PATCH body must preserve `privateKey` and `shortIds` from the stored config.
- **LOW:** The `xvpn_node_profile_override` default is `{}` (empty dict). The `combine` with an empty dict is a no-op, so the default case is clean.

**Suggestions:**
- Add a comment in `register.yml` explaining that `combine(recursive=True)` replaces lists, so operator overrides must include the full `routing.rules` list.
- The side_effect drift PATCH should be done through the module itself (to prove the module handles it) rather than through a raw API call.

**Risk Assessment:** LOW-MEDIUM — builds on the module from Plan 03-10 with real-Panel proof.

---

## 03-12

**Summary:** Implements `remnawave_internal_squad` (union-only membership) and `remnawave_node` (reconcile + bounded wait), with thorough failure diagnostics.

**Strengths:**
- Union-only squad membership (never remove foreign inbounds) is critical for multi-operator safety.
- The `wait_connected` failure message includes actionable diagnostics: rich rule hint, `remnanode.service` hint, `node.env` hint, `xvpn_node_rekey` hint.
- The duplicate address detection (fail when another node has the same address) prevents accidental hijacking.
- The async node deletion polling (poll until uuid is gone) correctly handles the Panel's queued deletion.
- The `resolve_profile()` helper shared by both modules reduces code duplication.

**Concerns:**
- **HIGH:** The plan states the `remnawave_node` module should fail with "another Panel node already uses address <address>" when a different node has the same address. However, the default `xvpn_node_address` is `xvpn_node_domain` (D-05). If two nodes have different domains but the same IP (e.g., multiple domains on one host), this would false-positive. The plan should clarify that this check is for the `address` field, not the domain.
- **MEDIUM:** The `wait_connected` budget is 30 x 5s = 150s. The Panel health check runs every 10s. In the worst case, the node is created, the Panel waits up to 10s for the next health check, the health check fails (node not reachable), and this repeats. If the node takes 60s to start (image pull, container init), the health check succeeds on the 6th-7th attempt. 30 retries is generous but the 5s delay between polls means the module waits 5s even after the Panel has already detected the node as connected. Consider reducing the delay to 2s or using the Panel's `isConnecting` field to short-circuit.
- **MEDIUM:** The "Missing node.env" negative case moves `node.env` to a backup path and expects the run to fail. But the `secret.yml` logic is: if `node.env` is missing AND the node exists in Panel → fail. The test must ensure the node is already registered in the Panel before this case runs. The plan correctly places this in `side_effect.yml` after the node is registered.

**Suggestions:**
- Add a `xvpn_node_address` uniqueness check that considers the full address (IP or domain), not just the domain.
- Consider making `wait_delay` configurable separately from `wait_retries` to allow faster polling.

**Risk Assessment:** MEDIUM — complex module logic with real-Panel proof, but the address uniqueness check needs clarification.

---

## 03-13

**Summary:** Implements `remnawave_host` and the last registration step, then proves the whole phase goal from outside: real Xray client, private-destination block, and scanner/SNI matrix.

**Strengths:**
- The host idempotency key (bound to node profile, disambiguated by remark) correctly prevents duplicate hosts.
- The real client e2e test using the Panel subscription link is the ultimate proof of NODE-03.
- The private-destination negatives (`client-private-node`, `client-private-lan`) prove the BLOCK routing rule.
- The scanner/SNI matrix against the real node (not just the gate) proves STEAL-01..03 in production-like conditions.
- The scenario override for the test sink (`xvpn_node_profile_override` with `finalRules` allow) is a clean solution for the loopback sink test.

**Concerns:**
- **HIGH:** The plan creates a test user `xvpn-molecule-client` through the Panel API in the verify. This is a test fixture, but it means the verify depends on the Panel API being available and the token being valid. If the token expires or is revoked, the verify fails. The plan sets `expireAt: now + 1 day`, which should be sufficient for a single CI run.
- **MEDIUM:** The Xray client binary is installed on the Panel VM from a GitHub release. The sha256 pin (`b651f7e1...`) is correct, but the binary is ~25 MB. Downloading it on every CI run adds time. The existing `scripts/gate/run.sh` also downloads Xray — the two downloads could be cached, but this is a CI optimization, not a correctness issue.
- **MEDIUM:** The `verify_selfsteal.yml` copies the node VM's Pebble issuer root to the Panel VM via slurp + copy. This is necessary because the Panel VM needs to verify the node's certificate. However, the slurp + copy pattern is verbose. A simpler approach would be to have the node VM's prepare write the root to a shared location, but VMs don't share filesystems.
- **LOW:** The plan acknowledges the residual that plain HTTP on :80 with an unknown Host answers Traefik's 404 text (Phase 2 D-15 behavior). This is acceptable but should be documented in the README.

**Suggestions:**
- Add a comment in `verify_client.yml` explaining that the test user creation is a test fixture only and the roles never create users.
- Consider adding a `client-public-negative` case that verifies the client cannot reach a known-bad public destination (e.g., a blocked port).

**Risk Assessment:** MEDIUM — the most comprehensive verify in the phase, with real client e2e proof.

---

## 03-14

**Summary:** Implements decommission with explicit confirmation flag, proves check/diff honesty on the real Panel, documents the node host in README, and adds `site.yml` import of `node.yml`.

**Strengths:**
- The decommission confirmation flag (`xvpn_node_decommission_confirm`) with a clear failure message prevents accidental deletion.
- The deletion order (host → node (polled) → profile) correctly handles the Panel's cascade behavior (Pitfall 5).
- The squad cascade proof (old inbound uuid absent from ALL squads, not just Default-Squad) is thorough.
- The check/diff honesty proof (converged state → changed=0, drifted state → changed>0 with redacted diff, no write in check mode) is critical for operator trust.
- The README section covers all operator-facing variables and procedures.
- The `site.yml` import of `node.yml` (Panel first, then nodes) correctly implements the dependency.

**Concerns:**
- **MEDIUM:** The decommission removes `node.env` (which contains `SECRET_KEY`). The plan acknowledges this ("the key is useless once the node is deleted from the Panel"). However, if the operator accidentally runs decommission and then re-registers, the new registration gets new keys (D-02), so all clients must be re-issued. The README should make this consequence very prominent.
- **MEDIUM:** The test cleanup in side_effect deletes the `xvpn-molecule-decom` squad via `DELETE /api/internal-squads/<uuid>`. This is test-harness cleanup, not a role capability. The plan correctly notes this doesn't violate D-06 (the role and module never delete squads). However, the DELETE route must be verified against the actual Panel API — the plan references `libs/contract/api/controllers/internal-squads.ts` but the actual route may differ.
- **MEDIUM:** The `ansible-playbook --check --diff` command in the side_effect block runs against the scenario inventory. The `MOLECULE_INVENTORY_FILE` or `MOLECULE_EPHEMERAL_DIRECTORY/inventory` path must be resolved correctly. Molecule's inventory file format may differ from a standard Ansible inventory.
- **LOW:** The README's "Known limitations" section should mention that `xvpn_node_panel_sources` is IPv4-only in v1.

**Suggestions:**
- Add a prominent warning in the README about the consequence of decommission (new keys on re-registration, clients must be re-issued).
- Consider adding a `--dry-run` option to decommission that shows what would be deleted without actually deleting.
- The side_effect "Check and diff" block should also verify that the check run's output doesn't contain the Panel API token (not just the Reality private key).

**Risk Assessment:** LOW-MEDIUM — decommission is well-guarded, README is comprehensive.

---

## Cross-Plan Observations

**Strengths:**
1. **Wave-based dependency structure** is sound — each wave builds on the previous one's proven artifacts.
2. **Research-first approach** de-risked the highest-technical-risk element (Reality → Traefik loopback) before any planning.
3. **Consistent patterns** across all plans: `no_log`, `diff: false`, `argument_specs`, negative-case markers, `check.sh` guards.
4. **Security-first design**: token never leaves Panel host, keys generated once, loopback-only websecure, rich rule for 2222, explicit CIDR block.
5. **Testability**: container tier for fast feedback, VM tier for SELinux/rootless proof, selfsteal gate for protocol proof, unit tests for module logic.

**Concerns:**
1. **HIGH — Panel mutation replication (Plans 03-10, 03-11):** The `apply_panel_mutations()` function must replicate ALL Panel server-side mutations or idempotency breaks. This is the single highest risk in the phase. A missed mutation means every run PATCHes the profile, restarting all nodes.
2. **MEDIUM — SECRET_KEY env-file handling (Plan 03-07, Assumption A1):** Podman `--env-file` behavior with the keygen payload (base64 with `+`, `/`, `=`) is unverified. A parsing issue would prevent remnanode from starting.
3. **MEDIUM — CI cost:** Three-platform matrix for both `vm` and `node-vm` scenarios means 6 VM-based CI jobs, each with 2 VMs. Total: 12 VMs per CI run. This is expensive and slow.
4. **MEDIUM — Plan complexity:** 14 plans with 9-14 files each means ~150 files modified/created. The cognitive load for review and maintenance is high.
5. **LOW — Template content quality:** Plans 03-03/03-04 create 4 multi-page HTML templates from scratch. Quality and uniqueness are hard to verify automatically.

**Suggestions:**
1. Prioritize the `apply_panel_mutations()` implementation and add extensive unit tests covering every known Panel mutation.
2. Verify Podman `--env-file` behavior with a base64 payload in the VM tier's first converge.
3. Consider running the three-platform matrix nightly rather than on every push.
4. Add a cross-plan integration test that runs the full converge → idempotence → drift → re-converge cycle on the VM tier.

**Overall Risk Assessment:** MEDIUM — the plans are thorough and well-structured, but the Panel mutation replication and SECRET_KEY env-file handling are unverified assumptions that could cause idempotency or startup failures. The research phase has de-risked the protocol-level concerns, and the test infrastructure is comprehensive.


---

## Consensus Summary

Both reviewers had repo access and cited `file:line` evidence (no discount markers). Note: the Qwen lane ran with `run_shell_command` denied (file reads only), so it could not execute probes — its claims about runtime behaviour are reasoned, not executed. Both rate overall phase risk **MEDIUM**: architecture and security posture are judged strong; residual risk sits in CI feasibility, plan size and Panel-side behaviour that only the VM tier can confirm.

### Agreed Strengths
- Strictly linear wave graph with real dependencies; cross-plan state handoffs (negative-case counts 9→10→11→13, temporary 03-07 block removed in 03-12) are explicit and consistent.
- Complete requirement coverage (NODE/STEAL/API) with executable verification per requirement; research open questions landed in specific plans.
- Security mechanics are structural, not prose: `no_log`/redaction gated by grep and unit tests over request bodies, keys never on the controller, exact-set firewalld verification, regex-gated injectable inputs with executed negative cases, destructive paths behind flags with executed refusal cases.
- Edge role reused via `tasks_from: route` without forking (`roles/edge/tasks/route.yml`); D-14 escalation preserved as a tripwire rather than a silent proxy swap.

### Agreed Concerns
1. **Two-VM CI feasibility and cost (03-06, 03-09)** — OpenCode HIGH (4096+2048 MB VMs on a ~7 GB GitHub runner, OOM/swap risk, no memory-budget checkpoint), Qwen MEDIUM (three-platform matrix × two VMs, cumulative CI cost). Most probable source of non-logic failures.
2. **Config-profile idempotency depends on replicating every Panel-side mutation (03-10, 03-11)** — Qwen HIGH (any missed mutation, e.g. `sortXrayConfig`, makes every run PATCH and restart all nodes on the profile), OpenCode MEDIUM (a fourth mutation found in 03-11 has no stated landing place for the module + test update).
3. **`xvpn_node_profile_override` recursive combine replaces lists (03-11)** — both MEDIUM: an override of `routing.rules` silently drops the managed private-CIDR BLOCK rule; OpenCode adds that `realitySettings.target`/`serverNames` overrides are not stripped and can de-sync host SNI from the inbound.
4. **Plan size of 03-12 / 03-13** — OpenCode HIGH (85–90k token estimates, module + role + scenario work in one plan; natural split candidates), Qwen MEDIUM (overall plan complexity).
5. **Nested `ansible-playbook --check --diff` in 03-14 side_effect** — both MEDIUM: check-mode-impure tasks and the Molecule inventory path resolution make it the flakiest assertion of the phase.
6. **Per-run binary downloads without caching (03-02, 03-13)** — both MEDIUM: Xray (~25 MB) and Pebble fetched on every push/run, adding time and network flakiness.

### Divergent Views
- **SECRET_KEY env-file handoff (03-07, assumption A1)** — Qwen HIGH (payload format through Podman `EnvironmentFile` unverified; validate single-line before writing); OpenCode treats A1/A3 as correctly fenced by the 03-07 checkpoint rule. Worth a cheap single-line/charset assert in 03-07.
- **Decommission with `--limit node` (03-08 × 03-14)** — OpenCode only: source resolution asserts non-empty Panel sources, but setup delegation runs only when `register` is true, so decommission without explicit `xvpn_node_panel_sources` fails; README does not say so. Qwen does not raise it. Looks like a real gap — verify.
- **Stale `NODE_PORT` (03-07)** — OpenCode only: `node.env` is rendered only when the secret is wanted, so changing `xvpn_node_api_port` later never reaches the env file while firewalld opens the new port.
- **Address-uniqueness check in `remnawave_node` (03-12)** — Qwen HIGH: two domains on one host could false-positive; plan should state the check compares the Panel `address` field. OpenCode silent.
- **Blocked CIDR list (03-10)** — Qwen MEDIUM: missing `::ffff:0:0/96` (IPv4-mapped IPv6) and `::/128`. OpenCode silent.
- **03-02 step ordering** — OpenCode MEDIUM: an inline "execute step 6 before this step" correction between steps 5 and 6; renumber so ACME runs while Xray holds 4443.
- **Decoy template list invariant (03-04)** — OpenCode MEDIUM: append-only + sorted order of `xvpn_edge_decoy_templates` enforced only by comment; an `assert list == list | sort` would make it structural.
- Qwen's 03-13 "test user token may expire" HIGH is weak (expireAt = now + 1 day for a single CI run) — low priority.
