---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
reviewed: 2026-11-27T00:00:00Z
depth: standard
files_reviewed: 32
files_reviewed_list:
  - roles/edge/tasks/main.yml
  - roles/edge/templates/traefik.yml.j2
  - roles/edge/vars/main.yml
  - roles/panel/defaults/main.yml
  - roles/panel/meta/argument_specs.yml
  - roles/panel/tasks/secrets.yml
  - roles/panel/tasks/stack.yml
  - roles/panel/vars/main.yml
  - roles/preflight/defaults/main.yml
  - roles/preflight/meta/argument_specs.yml
  - roles/preflight/tasks/main.yml
  - scripts/check.sh
  - scripts/check_until_set_fact.py
  - scripts/gate/render.yml
  - extensions/molecule/container/molecule.yml
  - extensions/molecule/container/verify.yml
  - extensions/molecule/preflight/converge.yml
  - extensions/molecule/preflight/molecule.yml
  - extensions/molecule/shared/panel_failure_log_dir_case.yml
  - extensions/molecule/shared/verify_edge.yml
  - extensions/molecule/vm/molecule.yml
  - extensions/molecule/vm/prepare.yml
  - extensions/molecule/vm/side_effect.yml
  - examples/gitlab-deploy/.gitlab-ci.yml
  - examples/gitlab-deploy/inventory/hosts.yml
  - examples/gitlab-deploy/requirements.yml
  - .github/workflows/gate.yml
  - .github/workflows/lint.yml
  - .github/workflows/molecule-container.yml
  - .github/workflows/molecule-vm.yml
  - galaxy.yml
  - README.md
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
  necessity: 0
status: issues_found
---

# Phase 2: Code Review Report (incremental, diff base 75d71a4)

**Reviewed:** 2026-11-27
**Depth:** standard
**Files Reviewed:** 32
**Status:** issues_found
**Scope:** `git diff 75d71a4 HEAD`: plan 02-12 per-CA ACME storage, rejection-sampling password draw plus `check_until_set_fact.py`, Oracle Linux 10 support, the GitLab deploy example and the CI `paths-ignore` change. This review replaces the earlier 02-REVIEW.md (diff base 6244716e); `shared/panel_failure_log_dir_case.yml` was deleted by the diff and no longer exists.

## Summary

The core changes are sound.

- **Store names.** The per-CA store name uses only the validated enum or 12 hex characters of a sha256, so no path component can be injected. I recomputed the two hashes hard-coded in `side_effect.yml` (`6d8ba56d5d58`, `dd20adf377e3`) and they match the URLs.
- **Password draw.** The rejection-sampling template is correct. The Jinja loop filter is evaluated lazily, so `ns.value` is seen on each iteration. `failed_when` on the `set_fact` register is valid, and `no_log` keeps the draw out of logs.
- **`check_until_set_fact.py`.** The script copes with empty files and with non-list YAML.

The remaining problems are a CI coverage gap, a spec/defaults inconsistency, and a few robustness points.

## Warnings

### WR-01: `paths-ignore` skips the secret scan and the gate on planning-only and Markdown-only changes

**File:** `.github/workflows/gate.yml:6-13` (same block in `lint.yml`, `molecule-container.yml`)
**Issue:**
- `scripts/check.sh` states that the secret scan covers "every tracked file (.planning/ included)", and the planning documents are where the debug and UAT notes with pasted output live. A push or PR that touches only `.planning/**` or `*.md` now runs none of lint, gate or the secret scan. A secret committed there reaches `main` unscanned.
- If these workflows are required status checks, a PR that only changes `README.md` never gets a check run. GitHub leaves the checks pending as "Expected" and the PR cannot be merged without admin bypass.

**Fix:** Keep the secret scan outside the filter, for example a small always-run `secrets` job or workflow without `paths-ignore` that calls the scan part of `scripts/check.sh`. Keep `paths-ignore` only on the heavy Molecule workflows. If the checks are required, use a path-filter step inside the job (for example `dorny/paths-filter`) so the job always reports a status.

### WR-02: preflight `argument_specs` default contradicts `defaults/main.yml`

**File:** `roles/preflight/meta/argument_specs.yml:14-16`
**Issue:** `choices` gained `OracleLinux`, but the spec `default` is still `[Rocky, AlmaLinux]`, while `roles/preflight/defaults/main.yml:2-5` now defaults to all three. The spec is the user-facing documentation (`ansible-doc`) and says Oracle Linux is not supported by default. Spec defaults and role defaults must agree.

**Fix:** Add `- OracleLinux` to the spec `default`.

## Info

### IN-01: `check_until_set_fact.py` scans only `roles/*/tasks/*.yml`

**File:** `scripts/check_until_set_fact.py:34`
**Issue:** The glob is not recursive. Subdirectories of `tasks/`, `handlers/`, and the playbooks and Molecule files under `extensions/` are not covered. Tasks that use the `action:` or `local_action:` forms are also missed. The guard can silently pass on a task that contains the bug it targets.
**Fix:** Use `root.glob("roles/*/{tasks,handlers}/**/*.yml")` and also scan `extensions/**` and `playbooks/*.yml`. The name matching can recognise `action:` too.

### IN-02: the ACME CA-switch test hard-codes the derived store hashes

**File:** `extensions/molecule/vm/side_effect.yml` (the `acme-custom-6d8ba56d5d58.json` and `acme-custom-dd20adf377e3.json` literals)
**Issue:** The values match today, but they silently depend on the URL in `vm/vars/panel.yml` and on the hash scheme. Changing either gives a confusing failure in a slow VM job.
**Fix:** Compute the names in the test with `(url | hash('sha256'))[:12]`, as `roles/edge/vars/main.yml` does, or load `roles/edge/vars/main.yml` and reuse `xvpn_edge_acme_storage_file`.

### IN-03: old ACME stores are kept forever and the legacy `acme.json` is orphaned

**File:** `roles/edge/tasks/main.yml:74-95`
**Issue:**
- Every CA switch leaves another file with private keys on disk, and the role never prunes them.
- On upgrade, an operator with a valid production certificate in `acme.json` triggers a fresh order. Repeated re-deploys of new hosts or CA toggles can approach the Let's Encrypt duplicate-certificate limit (5 per week).
- Both points are documented in the README, so this is awareness only.

**Fix:** Consider an opt-in variable to remove stores of non-active CAs. Optionally migrate `acme.json` when `xvpn_edge_acme_ca == production` and no per-CA store exists, but that needs the CA to be known, which the README already says it is not.

### IN-04: `xvpn_panel_failure_log_dir` was removed without a deprecation notice

**File:** `roles/panel/vars/main.yml:4`, `roles/panel/meta/argument_specs.yml`
**Issue:** An inventory that sets the old variable is now silently ignored. The path is forced to `/var/log/xvpn` by role vars, and argument_specs no longer knows the name. This is acceptable at version 0.1.0 and it removes the foreign-directory takeover risk from the earlier review. It is a behaviour change that a changelog or README note should state.
**Fix:** Mention the removal in the README or changelog. Optionally add a `fail` or `debug` warning when `xvpn_panel_failure_log_dir is defined`.

---

_Reviewed: 2026-11-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
