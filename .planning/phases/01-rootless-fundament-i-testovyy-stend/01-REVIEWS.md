---
phase: 1
reviewers: [opencode, qwen]
reviewed_at: 2026-11-23T15:25:32Z
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

opencode review failed or returned empty output. stderr:
[93m[1m! [0mpermission requested: external_directory (/home/dev/.ansible/collections/ansible_collections/fedora/linux_system_roles/roles/podman/*); auto-rejecting
[93m[1m! [0mpermission requested: external_directory (/home/dev/.ansible/collections/ansible_collections/xvpn/remnawave/*); auto-rejecting

Raw response body:
OpenCode review returned no assistant text (#1936: agent ended its turn with no final message).
Diagnostic: stop reason=tool-calls, output tokens=197
Diagnosis: opencode ran at effort=high and exited cleanly inside the timeout — a clean exit that produced no output is most often a model ending its turn without writing a final message rather than a crash; if this lane carries a reasoning effort, raising it is the usual fix.


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

Only one lane produced a review. OpenCode failed: it auto-rejected reads outside the repo (`~/.ansible/collections/...`) and ended its turn without a final message (stub above). Qwen covered all 12 plans but carries the `[reviewed-without-source-citations]` marker — it reviewed the plan text only, with no `file:line` evidence — so its verdict is not weighted as a grounded review. There is no cross-reviewer consensus; treat the items below as single-reviewer, unconfirmed input.

### Agreed Strengths
None (single reviewer). Qwen's main strengths: wave/dependency structure, read-only preflight aggregation with `any_errors_fatal`, add-only firewalld with SSH guard, proven-not-assumed dontaudit handling and boot-policy hash in 01-11, SHA-pinned actions and human legitimacy checkpoints.

### Agreed Concerns
None corroborated. Qwen's HIGH items (single-reviewer, unconfirmed):
- 01-02: test-only sudoers `secure_path` drop-in should be provably container-scoped.
- 01-09: first behavioural run of the tracer happens only in CI; the 2-round fix budget may be tight.
- 01-11: D-08 (`/var/lib/xvpn` home + SELinux equivalence) is proven only in wave 7 — expensive if AVCs appear.
- 01-12: Vagrant + vagrant-libvirt on hosted runners is unproven (dormant upstream); fallback adds complexity.

Most of these restate risks already flagged in the plans (FLAGGED ASSUMPTION lines, pre-decided fallbacks, checkpoint:decision on AVC). Notable new MEDIUM/LOW suggestions: guard `getenforce` absence on a bare host (01-05); warn when `xvpn_public_interface` is empty and the default route is used (01-07); root-owned port holder case for the `ss` uid parsing (01-06/01-08); positive assertion of `xvpn-fixture.service` in generator dry-run output (01-04).

### Divergent Views
None (single reviewer).
