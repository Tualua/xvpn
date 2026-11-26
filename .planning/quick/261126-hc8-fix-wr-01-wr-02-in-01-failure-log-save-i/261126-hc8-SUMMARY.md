---
phase: quick-261126-hc8
plan: 01
status: complete
commits: 1
plan_head_before: 805ee56
tags: [panel, failure-log, review-fix]
key-files:
  modified:
    - roles/panel/tasks/stack.yml
    - roles/panel/defaults/main.yml
    - roles/panel/meta/argument_specs.yml
    - README.md
---

# Quick 261126-hc8: failure-log save fix (WR-01, WR-02, IN-01)

Nested block/rescue with the `xvpn_panel_start_log_saved` flag replaces `failed_when: false` on the mkdir and copy in the stack-start rescue, and the log directory is now the variable `xvpn_panel_failure_log_dir`.

- WR-01: the copy sits after the mkdir in a nested block, so it cannot run after a failed mkdir.
- WR-02: the flag is set true only after both succeed, and false in the nested rescue. The final fail message conditions on it.
- The failed task name is recorded first (`xvpn_panel_start_failed_task`), because a failure inside the nested block overwrites `ansible_failed_task`.
- IN-01: `xvpn_panel_failure_log_dir` (default `/var/log/xvpn`) added to defaults, argument_specs and README. No hardcoded path remains in stack.yml.
- `no_log: true` and `diff: false` kept on the copy. No `ignore_errors`, no stat check.

Tasks 1 and 2 touch the same file in overlapping hunks, so they went into one commit.

Verification: `ansible-lint roles/panel` passed (production profile), `check_no_log.py` OK. yamllint is not installed locally, so it was not run.

## Deviations
None.

## Self-Check: PASSED
