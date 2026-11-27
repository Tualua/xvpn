---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
reviewed: 2026-11-27T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - README.md
  - roles/panel/meta/argument_specs.yml
  - roles/panel/tasks/stack.yml
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-11-27
**Depth:** standard (incremental: commit 054071a, failure log dir allowlist)
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Commit 054071a replaces the denylist with the regex `^/(var/log|opt|srv)(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)+$` plus two home-directory checks. It closes the earlier problems: `..`, `.` and empty components, trailing slashes and `/var/log` itself are all rejected. The home check works for the `xvpn_panel_home` default, including when `xvpn_panel_home` has a trailing slash. `xvpn_panel_home` is defined in the role defaults, so the assert cannot hit an undefined variable.

Two gaps remain. `$` accepts a trailing newline. The allowlist also does not guarantee a "dedicated" directory, which is the claim the README and the argument_specs make.

## Warnings

### WR-01: `$` in the regex accepts a trailing newline

**File:** `roles/panel/tasks/stack.yml:18`
**Issue:** The Jinja `match` test uses Python `re.match`, and `$` also matches just before a final `\n`. A value such as `"/var/log/xvpn\n"` passes the assert. This is easy to produce with a YAML `|` or `>` scalar, or with `-e` input. The value is then used in `file path:`, in `dest:` and in the fail message. The result is a directory whose name ends in a newline, which is awkward to handle later. The task comment and the README promise that the pattern admits no stray components. This one slips through.
**Fix:** Anchor with `\Z`, or add an explicit check:
```yaml
- xvpn_panel_failure_log_dir is match('^/(var/log|opt|srv)(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)+\Z')
```

### WR-02: The allowlist admits existing system directories, so "dedicated" is not enforced

**File:** `roles/panel/tasks/stack.yml:18`
**Issue:** The allowlist accepts any directory below `/var/log`, `/opt` or `/srv`. That includes `/var/log/journal`, `/var/log/audit`, `/var/log/sssd`, `/var/log/httpd`, `/var/log/nginx`, `/opt/containerd` and `/srv/www`. The `file` task at line 144 forces whatever it is given to `root:root 0700`. A user who points the variable at one of these directories would break the owning service. For example, `journal` is `root:systemd-journal 2755`, and the web server logs belong to other service accounts. The previous finding concerned exactly this "forced to 0700 on a shared directory" hazard. The allowlist only narrows it. A known-system-directory check, or at least a conflict check against already existing directories, is missing.
**Fix:** Either of these works:
- Add a pre-task `stat` of the path and `assert` that it does not exist, or is already `root:root 0700`. This is the cleanest option.
- Or add a deny-list for first components below `/var/log` (`journal`, `audit`, `private`, `sa`, and so on). Note this is weaker.

## Info

### IN-01: Negative tests for the failure log dir assert are still missing

**File:** `extensions/molecule/container/converge.yml` (and `verify.yml`)
**Issue:** No Molecule scenario exercises the assert. The `extensions/molecule/preflight` scenario only covers the `preflight` role, via its `run_case.yml` and the case matrix in its `converge.yml`. The rejected inputs below have never been run, and the new regex's edge cases (WR-01) would have been caught by them.
**Fix:** Add a negative-case play to the `container` scenario. The `container` scenario is the one that already converges the `panel` role. Include `xvpn.remnawave.panel` with `tasks_from: stack` inside `block/rescue` for each bad value, and assert that the rescue was reached and that `ansible_failed_result.msg` contains `dedicated absolute directory`. Alternatively, copy the `preflight` case-matrix pattern (`run_case.yml` plus an `expect_in` list) into a new `extensions/molecule/shared` task file. Cases that must be rejected: `/var/log`, `/var/log/`, `/var/log/xvpn/`, `/var/log/./x`, `/var/log/../etc`, `/var//log/x`, `/tmp/x`, `/etc/x`, `/var/log/xvpn\n` (WR-01), a path equal to `xvpn_panel_home`, and a path that is a parent of it. Cases that must pass: `/var/log/xvpn`, `/opt/xvpn-logs`, `/srv/a.b/c`.

### IN-02: The accepted character set is undocumented

**File:** `README.md:93`, `roles/panel/meta/argument_specs.yml:133`, `roles/panel/tasks/stack.yml:23`
**Issue:** The regex limits each component to `[A-Za-z0-9_.-]`, and a component cannot start with `.`. Spaces and non-ASCII characters are rejected, as are hidden-directory components. None of the three places mention this, so a user with `/srv/xvpn logs` or `/opt/.xvpn` gets an error message that does not explain the cause.
**Fix:** Add "components use only letters, digits, `_`, `-` and `.`, and do not start with `.`" to the README row, the argument_specs description and the `fail_msg`.

---

_Reviewed: 2026-11-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
