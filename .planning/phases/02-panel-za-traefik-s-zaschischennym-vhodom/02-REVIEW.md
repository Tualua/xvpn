---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
reviewed: 2026-11-27T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - README.md
  - extensions/molecule/container/verify.yml
  - extensions/molecule/shared/panel_failure_log_dir_case.yml
  - roles/panel/meta/argument_specs.yml
  - roles/panel/tasks/stack.yml
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 2: Code Review Report (incremental)

**Reviewed:** 2026-11-27
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found
**Scope:** incremental review over `git diff 6244716e..HEAD` for the failure log dir fixes (`\Z` anchor, refusal to take over an existing directory, molecule cases, docs).

## Summary

The previous WR-01/WR-02/IN-01/IN-02 fixes are correct in substance. `\Z` is a valid Python anchor and survives YAML single quotes. `is match` uses `re.match`, so the pattern is anchored at both ends. The stat/assert pair runs under `become` (playbooks use `become: true`). It handles a symlink (`isdir` is false without follow) and a missing path. The molecule cases and the shared case file are structurally sound, and the Jinja test chains parse as intended. Remaining concerns: the "foreign directory" guard is weaker than the docs claim, and two of the new test cases do not exercise what their comments say.

## Warnings

### WR-01: The foreign-directory guard accepts existing system directories that are already root:root 0700

**File:** `roles/panel/tasks/stack.yml:38-48` (docs: `README.md:93`, `roles/panel/meta/argument_specs.yml:135-137`)
**Issue:** The check accepts any existing directory that is root:root 0700. Several standard directories under the allowed bases look exactly like that, for example `/var/log/audit` and `/var/log/private`. They pass the allowlist (`/var/log/audit`) and the stat check. On a failed start the role would then write `panel-start-failure.log` into the auditd directory. On every successful run it would try to remove a file there. The README states "so no existing system or service directory is taken over", which is too strong. It also does not detect a directory the role did not create, such as an operator-owned root-only directory, so a collision is silent.
**Fix:** Either narrow the claim in the docs ("only root:root 0700 directories are accepted; a pre-existing root-only directory of another service would still be reused"), or add a stricter guard. Examples are denying known system names (`/var/log/audit`, `/var/log/private`, `/var/log/journal`) in the assert, or requiring that an existing directory be empty or contain only `panel-start-failure.log` (`ansible.builtin.find` with `patterns` and an assert on the file count).

### WR-02: The home-directory guard is not exercised by the new test cases

**File:** `extensions/molecule/container/verify.yml:~821-823`
**Issue:** The cases `/var/lib/xvpn/rw-panel` and `/var/lib/xvpn` are commented as "the service user's home and a parent of it". Both lie outside `/var/log|/opt|/srv`, so they are rejected by the regex. The home assertions (`!= xvpn_panel_home`, `startswith`) never run. The final assert only checks the message for "dedicated absolute directory", which is the same message for all four assertions, so a regression in the home check would go unnoticed. The check can only matter when `xvpn_panel_home` is under an allowed base, and no case sets it that way.
**Fix:** Add cases where `xvpn_panel_home` is overridden, for example `/opt/xvpn/rw-panel`, with `dir: /opt/xvpn/rw-panel` and `dir: /opt/xvpn`. Pass the override through the case (an optional `xvpn_case.home` forwarded as `xvpn_panel_home`). Alternatively, drop the misleading comment.

## Info

### IN-01: Fixture cleanup is not in an `always` path

**File:** `extensions/molecule/container/verify.yml:~784-852`
**Issue:** If the results assert fails, the `/var/log/xvpn-foreign` and `/opt/xvpn-own-logs` fixtures remain. Molecule destroys the instance, so the impact is limited to local `verify`-only reruns. A leftover `/var/log/xvpn-foreign` also changes how the next run behaves.
**Fix:** Wrap the creation, the cases, and the assert in a `block` with the removal task in `always`.

### IN-02: Overlong line in the negative-case list

**File:** `extensions/molecule/container/verify.yml:~862`
**Issue:** The edited list has the line `'panel-secrets-corrupt', 'panel-secrets-lost-with-volume', 'panel-weak-admin-password', 'port-without-protocol', 'relative-template',`, which is well over 120 characters. This risks a yamllint `line-length` warning, depending on the project config.
**Fix:** Rewrap the list to keep the same sorted order, with one or two names per line.

---

_Reviewed: 2026-11-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
