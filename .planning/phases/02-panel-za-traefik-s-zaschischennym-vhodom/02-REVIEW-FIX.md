---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
fixed_at: 2026-11-27T00:00:00Z
review_path: /workspaces/xvpn/.planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-11-27
**Source review:** /workspaces/xvpn/.planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: `$` in the regex accepts a trailing newline

**Files modified:** `roles/panel/tasks/stack.yml`
**Commit:** 8ea2677
**Applied fix:** The pattern now ends in `\Z` instead of `$`; the task comment explains why. Status: fixed: requires human verification (regex logic).

### WR-02: The allowlist admits existing system directories, so "dedicated" is not enforced

**Files modified:** `roles/panel/tasks/stack.yml`, `roles/panel/meta/argument_specs.yml`, `README.md`
**Commit:** 2115ba3
**Applied fix:** A `stat` plus `assert` right after the validation, so it runs on every converge and before the directory is created. A missing path is accepted. An existing path is accepted only when it is a real directory (not a symlink or file) owned by root:root with mode 0700. This covers the idempotent re-run. README and argument_specs describe the rule. Status: fixed: requires human verification (guard logic).

### IN-01: Negative tests for the failure log dir assert are still missing

**Files modified:** `extensions/molecule/container/verify.yml`, `extensions/molecule/shared/panel_failure_log_dir_case.yml` (new)
**Commit:** dfe1f55
**Applied fix:** The container scenario (it already converges the panel role) runs 16 cases through a shared case file with `block/rescue`, following the existing `xvpn_negative_rejected` convention (new id `panel-failure-log-dir`, added to the final sorted list). Accepted: `/var/log/xvpn`, `/opt/xvpn-logs`, `/srv/a.b/c`, an existing root:root 0700 fixture. Rejected: `/var/log`, `/var/log/`, `/var/log/xvpn/`, `/var/log/./x`, `/var/log/../etc`, `/var//log/x`, `/tmp/x`, `/etc/x`, `/var/log/xvpn\n`, the service home, its parent, and an existing 0755 fixture directory. Fixtures are created before and removed after.

### IN-02: The accepted character set is undocumented

**Files modified:** `roles/panel/tasks/stack.yml`, `roles/panel/meta/argument_specs.yml`, `README.md`
**Commit:** fadc5fe
**Applied fix:** The character set (letters, digits, `_`, `-`, `.`, no leading `.`) is stated in the README row, the argument_specs description and the `fail_msg`.

## Verification

Gates ran in an isolated worktree (merged by fast-forward into `main` and removed afterwards), not in the main checkout.

Verified by running:
- `ansible-lint` (production profile): 0 failures, 0 warnings, run before each of the four commits.
- `ansible-playbook --syntax-check` on `extensions/molecule/container/verify.yml`: passed.
- Throwaway playbooks in the scratchpad: the final regex and home checks accepted exactly `/var/log/xvpn`, `/opt/xvpn-logs`, `/srv/a.b/c` and rejected all the bad values including `"/var/log/xvpn\n"` (a Python `re.match` check confirmed the old `$` accepted it). The stat guard was run against a missing path (accepted), `/root` (root:root 0700, accepted), a 0700 dir owned by a non-root user, a 0755 dir, a symlink and a regular file (all rejected). The shared case file was run with a stub `xvpn.remnawave.panel` role that contains the real validation and stat tasks. 8 cases gave the expected pass/fail outcomes and the judging filter on the failure messages held.

Verified only by reading (not run):
- Molecule itself (container scenario, `verify.yml` end to end) was not run. The root-owned fixture directories (`/var/log/xvpn-foreign` 0755, `/opt/xvpn-own-logs` 0700) could not be created in the throwaway run (no root), so the "existing foreign directory is rejected" and "existing root:root 0700 is accepted" cases were checked by the stat tests above, not through the scenario.
- The new `verify.yml` judge assertion (case count of 16, the pass list and the message filter) was not executed in full.
- The full role flow with a failed stack start (directory creation, idempotence with changed=0 on a second run) was not run.

---

_Fixed: 2026-11-27_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
