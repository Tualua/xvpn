---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
reviewed: 2026-11-26T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - README.md
  - roles/panel/defaults/main.yml
  - roles/panel/meta/argument_specs.yml
  - roles/panel/tasks/stack.yml
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-11-26
**Depth:** standard (incremental, diff against 810ad39)
**Files Reviewed:** 4
**Status:** issues_found

## Summary

The previous WR-01, WR-02 and IN-01 fixes are confirmed correct.

- **WR-01/WR-02 (stale or unsaved log reported as saved):** `xvpn_panel_start_log_saved` is reset to `false` first in the outer rescue. It becomes `true` only after both the `file` and `copy` tasks succeed inside the nested block. The nested `rescue` sets it back to `false`. The hard failure is no longer swallowed by `failed_when: false`, and the status flag does not depend on `is succeeded` or `is not skipped` of a registered result. The earlier case where a skipped copy was reported as saved is gone.
- **`ansible_failed_task` overwrite:** the name is captured in the first rescue task, before any nested failure can replace it. The `fail` message uses the saved variable.
- **IN-01 (hardcoded path):** the path is now `xvpn_panel_failure_log_dir`. It appears consistently in defaults, argument_specs, README, the save tasks, the message and the cleanup task.
- **Line length:** the longest lines (163, 154 characters) stay under the yamllint limit of 160.

Two remaining defects are listed below. Neither is a regression of the fixed items.

## Warnings

### WR-01: `xvpn_panel_failure_log_dir` is a user-overridable path that is forced to root:root 0700 with no validation

**File:** `roles/panel/tasks/stack.yml:127-133` (also `roles/panel/meta/argument_specs.yml:130-135`)
**Issue:** The variable was hardcoded and is now public (README table, argument_specs). The `file` task with `state: directory, owner: root, mode: "0700"` runs against whatever value the user sets. A value such as `/var/log`, `/tmp` or `/var/lib/xvpn` would chmod that directory to 0700. That would break journald and other services that write to it, or lock out the service user's own paths. An empty string or a relative path would resolve relative to the working directory or fail with an unclear error. The cleanup task at line 168 runs on every successful run and does `state: absent` on `<dir>/panel-start-failure.log`. The same bad value is therefore also hit on the happy path. argument_specs only checks `type: str`.
**Fix:** Assert the value before use (for example in the stack validation task):
```yaml
- name: Panel stack | validate the failure log directory
  ansible.builtin.assert:
    that:
      - xvpn_panel_failure_log_dir is string
      - xvpn_panel_failure_log_dir is match('^/[^/]')
      - xvpn_panel_failure_log_dir | regex_replace('/+$', '') not in ['/var/log', '/tmp', '/var/tmp', '/var/lib', '/etc', '/root', '/home']
    quiet: true
```
Alternatively, document that the directory must be dedicated to this log, and keep the leaf name fixed (`/var/log/xvpn`).

## Info

### IN-01: Rescue state variables stay set for the rest of the play

**File:** `roles/panel/tasks/stack.yml:67-70`
**Issue:** `set_fact` stores `xvpn_panel_start_failed_task` and `xvpn_panel_start_log_saved` as host facts. Within one play they persist after the rescue. This is harmless today because the following `fail` ends the host. It would become stale state if the `fail` were ever removed or the block wrapped in a retry loop.
**Fix:** None required. Optionally use `vars:` or note in a comment that the `fail` is terminal.

---

_Reviewed: 2026-11-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
