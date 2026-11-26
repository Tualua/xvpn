---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
reviewed: 2026-11-26T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - roles/edge/tasks/main.yml
  - roles/panel/tasks/main.yml
  - roles/panel/tasks/secrets.yml
  - roles/panel/tasks/stack.yml
  - scripts/check_no_log.py
  - scripts/ci_watch.sh
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
  necessity: 0
status: issues_found
---

# Phase 2: Code Review Report (incremental re-review)

**Reviewed:** 2026-11-26
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

I re-reviewed the fixes for WR-03, WR-04, WR-05 and IN-02 to IN-05 (`git diff 60dbb9e..HEAD`). The edge port-range asserts, the stricter email and IDN regexes, the `ci_watch.sh` baseline error handling and the new `check_no_log.py` writer and reader coverage are correct. I found no regressions in them.

The rework of the rescue block in `stack.yml` has two defects. Both come from `failed_when: false` interacting with the `is succeeded` test. The result is a guard that never triggers and a success message that can be false. The stale-log cleanup also depends on privilege that the file does not set up itself. No secret reaches the output.

`check_no_log.py` could not be run in this environment (PyYAML is missing), so I checked it by reading the code only.

## Warnings

### WR-01: `when: xvpn_panel_start_log_dir is succeeded` is a dead guard, because `failed_when: false` forces `failed=false`

**File:** `roles/panel/tasks/stack.yml:125-140`
**Issue:** The directory task sets `failed_when: false`, so its registered result always has `failed: false`. `is succeeded` therefore always evaluates true, and the `when:` on the copy task never skips it. If `/var/log/xvpn` cannot be created, the copy task still runs and fails silently (it also has `failed_when: false` and `no_log`). The intent of the fix was to skip the copy when the directory is missing.
**Fix:** Drop `failed_when: false` from the directory task. Add `ignore_errors: true` instead, which keeps `failed: true` in the result. Alternatively test `xvpn_panel_start_log_dir.failed | default(false)` explicitly. Use `ignore_errors` the same way on the copy task (see WR-02).

### WR-02: The failure message can claim the log was saved when the copy failed

**File:** `roles/panel/tasks/stack.yml:139-153`
**Issue:** The copy task has `failed_when: false`, so a real write failure (disk full, permissions) still gives `failed=false`. The final message checks `xvpn_panel_start_log_file is succeeded and is not skipped`, which stays true after a failed write. The operator is then told the journals are in `/var/log/xvpn/panel-start-failure.log` when that file does not exist. That is the only diagnostic channel, since the module error text is deliberately suppressed.
**Fix:** Use `ignore_errors: true` instead of `failed_when: false` on both tasks. Then `xvpn_panel_start_log_file is succeeded` is accurate, and the `is not skipped` clause and the dead dir guard from WR-01 become meaningful. Or test `xvpn_panel_start_log_file.changed | default(false) or ... is not failed`.

## Info

### IN-01: The stale-log cleanup and the log directory rely on the play's `become`

**File:** `roles/panel/tasks/stack.yml:118-124, 155-159`
**Issue:** The new tasks write and remove files under root-owned `/var/log/xvpn`, but they carry no `become: true`. The same holds for the `journalctl` collection task. If the role is ever run without play-level `become`, the cleanup fails (and, since it is unguarded, it aborts a successful run). The `/var/log/xvpn` path is also hardcoded in three places.
**Fix:** Introduce a role variable for the log directory. Either set `become: true` on these tasks explicitly or document that the role requires privilege escalation.

### IN-02: `check_no_log.py` does not cover other ways of reading a secret file

**File:** `scripts/check_no_log.py:36-43, 86`
**Issue:** The guard flags a secret path only for `WRITER_MODULES` and `READER_MODULES` tasks. `command`/`shell` with `cat {{ xvpn_panel_secrets_file }}`, `include_vars file=<secrets_file>` and `lookup('file', ...)` are not caught. `xvpn_panel_secrets_file` is also not matched by `\bxvpn_panel_secrets\b` in `SENSITIVE`, because `\b` does not fall between `s` and `_`. Current roles do not use these patterns, so this is a future-proofing gap.
**Fix:** Add `SECRET_FILE_VAR` to the generic `PATTERN` for non-module tasks, so any task that mentions the secret-file variables requires `no_log`. Exclude the plain `stat` and `file` modules if that creates noise.

---

_Reviewed: 2026-11-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
