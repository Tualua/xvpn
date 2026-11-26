---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
fixed_at: 2026-11-26T00:00:00Z
review_path: /workspaces/xvpn/.planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 2: Code Review Fix Report

**Fixed at:** 2026-11-26
**Source review:** /workspaces/xvpn/.planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: Denylist is bypassed by `.` components and by repeated or mid-path slashes

**Files modified:** `roles/panel/tasks/stack.yml`, `roles/panel/meta/argument_specs.yml`, `README.md`
**Commit:** 054071a
**Applied fix:** fixed: requires human verification (validation logic). The denylist and the `..` check were replaced by one allowlist regex, `^/(var/log|opt|srv)(/[A-Za-z0-9_-][A-Za-z0-9_.-]*)+$`. Every component must start with an alphanumeric, `_` or `-`, so `.`, `..`, empty components (`//`) and a trailing slash are rejected. Fixed together with WR-02 in one commit, because both are the same assert.

### WR-02: Denylist is incomplete, so many shared directories are still accepted

**Files modified:** `roles/panel/tasks/stack.yml`, `roles/panel/meta/argument_specs.yml`, `README.md`
**Commit:** 054071a
**Applied fix:** fixed: requires human verification (validation logic). The assert is now an allowlist: the path must lie strictly below `/var/log`, `/opt` or `/srv`. It must also not equal `xvpn_panel_home` and must not be a parent of it. `/var/lib` was dropped from the reviewer's suggested prefixes, because the service home lives under `/var/lib/xvpn`. README and argument_specs describe the same rule.

Verification: the assert expression was run in a throwaway playbook in the scratchpad directory, with `xvpn_panel_home=/var/lib/xvpn/svc`.
- Pass: `/var/log/xvpn`, `/var/log/xvpn/sub` (a nested dedicated directory is allowed and documented), `/opt/xvpn`.
- Fail: `/var/log`, `/var/log/`, `/var/log/.`, `/var/./log/x`, `/etc/ssh`, `/usr/bin`, `relative/path`, `/tmp/x/../..`, `/var/log/xvpn/`, `/var/log/x/../..`, `/var//log/x`, `/var/lib/xvpn/svc`, `/var/lib/xvpn`.
- Fail with an overridden home: `/opt/xvpn` is rejected when `xvpn_panel_home=/opt/xvpn/svc`.

`ansible-lint` (production profile) reports 0 failures and 0 warnings. The checks ran in the main checkout, because `workflow.use_worktrees` is not set to a worktree path here, so the results are reproducible from the current tree.

Known limitation: `/var/log/<existing system dir>` (for example `/var/log/audit`) still passes the allowlist. The documentation requires a dedicated directory.

---

_Fixed: 2026-11-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
