---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
reviewed: 2026-11-26T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - README.md
  - roles/panel/meta/argument_specs.yml
  - roles/panel/tasks/stack.yml
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-11-26
**Depth:** standard (incremental, commit 9951cd2)
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Commit 9951cd2 adds an assert that validates `xvpn_panel_failure_log_dir` before it is forced to root:root 0700. The default `/var/log/xvpn` passes. The regex `^/[^/]+/[^/]` correctly rejects relative paths, `//x`, `/var//x`, and single-component paths. The assert is placed before any use of the variable. The docs match the behavior.

The guard is a denylist, and it has holes. Two paths that the fix is meant to block still get through.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Denylist is bypassed by `.` components and by repeated or mid-path slashes

**File:** `roles/panel/tasks/stack.yml:16-19`
**Issue:** The check blocks `..` but not `.`. It strips only trailing slashes before comparing with the denylist.
- `/var/log/.` passes: it has two components and is not in the denylist. It resolves to `/var/log`.
- `/var/log/./` and `/var/./log` do not match the denylist exactly either.
- The result is that `/var/log` gets chmod 0700 and chown root:root. That breaks log readers, journald-adjacent tooling and other services.

**Fix:** Normalize before comparing. Reject any `.` or empty component, and compare against a normalized path.
```yaml
- "'.' not in xvpn_panel_failure_log_dir.split('/')"
- "'' not in xvpn_panel_failure_log_dir.split('/')[1:]"
```
Alternatively, use a regex that allows only safe characters: `^/[A-Za-z0-9_.-]+(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)+$`.

### WR-02: Denylist is incomplete, so many shared directories are still accepted

**File:** `roles/panel/tasks/stack.yml:25-34`
**Issue:** The check needs only two path components. Only 9 exact paths are denied, so these are still accepted and would be forced to root:root 0700:
- `/etc/ssh`, `/etc/pki`, `/etc/sudoers.d`
- `/usr/bin`, `/usr/sbin`, `/usr/share`
- `/var/cache`, `/var/spool`, `/var/lib` (denied) but not `/var/www`
- `/home/<user>`, `/boot`-style paths, and the service user's own home (`xvpn_panel_home`)

This can break the host or the service. A 0700 chmod on `/home/<svc-user>` or `/etc/ssh` is a robust way to cause an outage.

**Fix:** Use an allowlist instead of a denylist. Require a prefix of `/var/log/` or `/var/lib/xvpn`, or a dedicated documented base. For example:
```yaml
- xvpn_panel_failure_log_dir is match('^/(var/log|var/lib|opt|srv)/[A-Za-z0-9_-][A-Za-z0-9_.-]*(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)*$')
```
Also assert that the value differs from `xvpn_panel_home` and from every other role directory variable.

## Info

### IN-01: Assert is unverified by tests

**File:** `roles/panel/tasks/stack.yml:12-34`
**Issue:** The fix report says the assert logic was not run, and that only lint and syntax-check passed. The bypasses above show this matters. There is no negative Molecule or verify case.
**Fix:** Add a small test that includes the task with `/var/log`, `/var/log/.`, `/var/log/`, `/tmp/x/../..` and `relative/path`, and expects the assert to fail for each. Then add one run with the default value that expects it to pass.

---

_Reviewed: 2026-11-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
