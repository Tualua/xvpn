---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
plan: 09
subsystem: qa
tags: [gitleaks, secret-scan, doc-04, ci, check-sh]
requires:
  - phase: 02-08
    provides: marked gate test fixtures in scripts/gate/render.yml; check.sh gate steps
provides:
  - pinned gitleaks v8.30.1 scan of every tracked file (.planning/ included) in scripts/check.sh and the lint workflow
  - .gitleaks.toml (upstream rules plus xvpn-secret-key, xvpn-secret-key-pathlike, xvpn-url-userinfo, fixture-scoped allowlist)
  - sixteen-case executed self-test with per-case FAIL output
affects: [02-11, every later plan and phase]
tech-stack:
  added: [gitleaks 8.30.1 (release binary, sha256-verified)]
  patterns: [executed negative self-test before a scan; secret-named keys assembled from fragments in scanned sources]
key-files:
  created: [.gitleaks.toml]
  modified: [scripts/check.sh, .github/workflows/lint.yml, galaxy.yml, extensions/molecule/vm/side_effect.yml]
key-decisions:
  - "Key rules use [ \\t]* instead of \\s* around the separator so a key line followed by an indented next line is never read as key plus value"
  - "Pathlike FHS exemption keeps the explicit (?-i) flag: without it the fhs-root-base64-secret-dir case exits 0 (observed)"
  - "Random fixture values avoid false/null/true/changeme and the two global stopwords instead of copying the long rule-scoped stopword list"
requirements-completed: [DOC-04]
status: complete
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: 5f747f70c207faaa12226005d12b87dd3aa006c8
plan_head_after: 26ccf528f3cff1822329d26bc79aadda3eeef3ee
duration: 55min
completed: 2026-11-25
---

# Phase 2 Plan 09: Repository secret scan Summary

**Pinned gitleaks 8.30.1 scans every tracked file on every check.sh run and every push, with a sixteen-case executed self-test proving planted secrets still fail the gate.**

## Accomplishments
- `.gitleaks.toml`: `useDefault = true` plus three project rules and one allowlist (marked `# xvpn-test-fixture: non-secret` lines in `scripts/gate/` and `extensions/molecule/`, rule `xvpn-secret-key` only). Excluded from the collection through `build_ignore`.
- `scripts/check.sh`: tool gate (notice and skip locally, hard fail with CI set, version pin check), self-test, scan of a copy of the tracked tree (`git ls-files -z` into tar), leaks exit 3 so a tool error never counts as a detection.
- `.github/workflows/lint.yml`: `Install gitleaks` step with the literal release URL and `sha256sum -c` before extraction.
- CI: lint and gate green for both task commits (413058f, 26ccf52).

## Task Commits
1. Task 1 (tracer): `413058f` config, tool gate, three-case self-test, scan, CI install. Tracer verified end to end in CI before expansion.
2. Task 2: `26ccf52` sixteen cases, `build_ignore`.

## Self-test output
```
check_secrets self-test: OK
check_secrets: OK
```
15 consecutive runs of the sixteen cases in a harness produced no FAIL line (no flakiness).

## Observations required by the plan
- **Residual (a), case `fhs-root-base64-secret-dir`:** exits 3 with the final exemption
  `(?-i)^[:=][ \t]*["']?/(?:var|etc|run|srv|opt|usr|home|tmp)(?:/[a-z0-9._-]+)+$`. With the `(?-i)` removed the case exits 0 (observed on the real 8.30.1 binary), so the flag is load-bearing and no fallback discriminator was needed. The `placeholders` case (lower-case FHS path under `xvpn_panel_secrets_file`) still exits 0.
- **Stopword choice:** the two global stopwords of the upstream config are tiny, the long list belongs to a rule-scoped allowlist and does not apply to the xvpn rules. The global allowlist regex `(?i)^true|false|null$` is unanchored, so random values are regenerated until their lower-cased form contains none of `false`, `null`, `true`, `changeme`, `abcdefghijklmnopqrstuvwxyz`.
- **Real-tree planted run:** a clone with a line `xvpn_panel_app_secret: <40 random alnum>` appended to `roles/panel/defaults/main.yml` and `git add`-ed produced `RuleID: xvpn-secret-key`, `File: roles/panel/defaults/main.yml`, `Line: 63`, `Secret: REDACTED`; the clone was deleted.
- **Wall time of check.sh locally:** 75 s without gitleaks, 92 s with it (about +17 s: sixteen self-test runs plus the tree scan).
- Residuals (b) and (c) are not closed (user-accepted): the upstream global allowlist and stopwords can suppress a value containing such a word, and secret-named keys with other suffixes (for example `_file_v2`) match neither xvpn rule.

## Deviations from Plan

**1. [Rule 1 - Bug] Key rules crossed line ends**
- **Found during:** Task 1 first scan of the tracked tree
- **Issue:** `\s*` around the separator let `xvpn_panel_app_secret:` at the end of a line match the next line (`description: ...`) in `roles/panel/meta/argument_specs.yml`, six false positives.
- **Fix:** `[ \t]*` instead of `\s*` before and after the separator in both key rules and the placeholder allowlists.
- **Files modified:** .gitleaks.toml
- **Commit:** 413058f

**2. [Rule 1 - Bug] Real literal admin password in a Molecule side effect**
- **Found during:** Task 1 first scan
- **Issue:** `extensions/molecule/vm/side_effect.yml` carried a fixed divergent admin password (the plan expected a finding in `container/verify.yml`, not here).
- **Fix:** value now from `ansible.builtin.password` lookup (30 letters and digits); no marker used.
- **Files modified:** extensions/molecule/vm/side_effect.yml
- **Commit:** 413058f

**3. [Rule 1 - Bug] Trap on EXIT referenced a function-local variable**
- **Found during:** Task 1 (`set -u`: `work: unbound variable` after the function returned)
- **Fix:** work dir kept in a global `SECRETS_WORK`.
- **Commit:** 413058f

**Total deviations:** 3 auto-fixed (3 Rule 1). **Impact:** none on scope; no marker, path allowlist or baseline was added for any finding.

## Known Stubs
None.

## Threat Flags
None.

## Issues Encountered
yamllint is not installed in the devcontainer, so `lint.yml` was validated by CI only (green).

## Self-Check: PASSED
- `.gitleaks.toml`, `scripts/check.sh`, `.github/workflows/lint.yml`, `galaxy.yml` present; commits 413058f and 26ccf52 in history; lint and gate success for 26ccf52.
