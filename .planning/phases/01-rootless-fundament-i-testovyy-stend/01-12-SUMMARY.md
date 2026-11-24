PLAN_START: bc5fa2adb021d697ff9047f981e477be28adf778

---
phase: 01-rootless-fundament-i-testovyy-stend
plan: 12
subsystem: testing
tags: [github-actions, molecule, vagrant, libvirt, kvm, selinux, reboot, avc]
requires: [01-10, 01-11]
provides: [molecule-vm workflow (alma10, rocky10) green in CI, README Testing section]
affects: [phase verification, all later phases (VM tier)]
tech-stack:
  added: []
  patterns: [KVM gate that fails loudly, catalog-mode pinned Vagrant box, dontaudit probe parsed from any seinfo column]
key-files:
  created:
    - .github/workflows/molecule-vm.yml
  modified:
    - README.md
    - extensions/molecule/vm/molecule.yml
    - extensions/molecule/vm/prepare.yml
    - extensions/molecule/shared/verify_runtime.yml
key-decisions:
  - "alma10 uses Vagrant Cloud catalog mode (box almalinux/10, box_version 10.2.20260914, amd64) instead of a direct box_url; Vagrant verifies the catalog sha256 (identical to the previously pinned 24b3ff7c...); user accepted this deviation (no extra repo-checksum enforcement)"
  - "Dontaudit count is parsed with (?:^|\\s)Dontaudit:\\s+ and regex_findall; assertion semantics unchanged (> 0 before semodule -DB, == 0 after, == 0 at verify before and after reboot)"
  - "No SELinux boolean, module or file-context rule was added; D-08 /var/lib/xvpn unchanged and proven by zero AVC and label equality"
requirements-completed: [QA-03, FND-02, FND-03, FND-04, FND-05]
duration: ~3h wall clock (CI-bound)
completed: 2026-11-24
status: complete
estimate_ref: 50000
actuals:
  tokens: 60000
  tasks: 2
  commits: 11
plan_head_before: bc5fa2adb021d697ff9047f981e477be28adf778
plan_head_after: 2314474cbca15a237006942f83267f6ef5ccaad9
---

# Phase 1 Plan 12: VM tier in CI Summary

The VM scenario runs in GitHub Actions on hosted KVM runners for AlmaLinux 10 and Rocky 10, and both legs are green: converge, idempotence, reboot in side_effect, runtime/label/zero-AVC verify before and after reboot.

## Result

Run https://github.com/Tualua/xvpn/actions/runs/45360051173 (workflow `molecule-vm`, dispatched on main, head 2314474): jobs `vm (alma10)` and `vm (rocky10)` both `success`. Each leg shows destroy, syntax, create, prepare, converge, idempotence, side_effect (reboot), verify, destroy all `Executed: Successful`.

Verification command (Task 2 automated): latest `molecule-vm` run on main is `success`; `bash scripts/check.sh` exits 0.

Note: this molecule version prints `idempotence: Executed: Successful` rather than the literal text `Idempotence completed successfully`; the step passes only when the second converge reports changed=0.

### D-08 label proof (verify_runtime.yml output, before and after reboot, identical on both legs)

| Path under /var/lib/xvpn/<user> | on-disk type | /home twin type |
|---|---|---|
| .config/containers | config_home_t | config_home_t |
| .config/containers/systemd | config_home_t | config_home_t |
| .local/share/containers | data_home_t | data_home_t |
| .local/share/containers/storage | data_home_t | data_home_t |

Zero AVC since the marker on alma10 and rocky10 (the zero-AVC assertion passed before and after the reboot). D-08 (/var/lib/xvpn) and RESEARCH A6 hold; no boolean, module or fcontext rule was needed.

### Git-range gates (PLAN_START from line 1)

- No `seboolean`, `semodule -i` or `xvpn_podman_rootless_home_root` change in `roles/` between PLAN_START and HEAD (0 commits each).
- `extensions/molecule/shared/verify_runtime.yml` changed in two commits (fa45862, e5adbc0), both the user-approved Dontaudit parse fix (see Escalations); no assertion semantics changed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] alma10 box not downloadable via direct vagrantcloud.com URL**
- Found during: Task 2, run 45340722552 (`'utf-8' codec can't decode byte 0x8b` from the community.vagrant module, reading a binary vagrant stderr).
- Root cause: `vagrant box add` reported "The metadata for the box was malformed": the first redirect of the vagrantcloud.com box URL has `Content-Type: application/json`, so Vagrant treats the URL as catalog metadata.
- Fix: catalog mode (`box: almalinux/10`, `box_version: 10.2.20260914`, `box_architecture: amd64`). Vagrant verifies the sha256 published in the catalog for that exact version/provider; it equals the earlier pinned `24b3ff7cd6810e5bf63614ab5c31496cb5496c329c3074ad29885ab370e2f9c1`. Rocky10 keeps the direct URL with the pinned sha256.
- Deviation recorded: the repo-pinned `box_download_checksum` is not passed for alma10 (Vagrant does not accept it in catalog mode). The user chose to keep catalog mode without an additional repo-side checksum check.
- Commit: 8c8e242.

**2. [Rule 1 - Bug] dontaudit probe could not parse seinfo output** (user-approved checkpoint, see Escalations)
- The count is the second column of the `Auditallow:` line; the line-anchored regex never matched. First attempt (`\b`) also failed because Jinja unescapes `\b` in string literals; final form `(?:^|\s)Dontaudit:\s+([0-9]+)` via `regex_findall`, verified locally with an assert playbook.
- Commits: fa45862, e5adbc0. Files: `extensions/molecule/vm/prepare.yml`, `extensions/molecule/shared/verify_runtime.yml`.

**3. [Rule 1 - Bug] AVC marker format rejected by ausearch**
- `ausearch -ts` under `LC_ALL=C` needs a two-digit year; the marker used `%m/%d/%Y` ("Error parsing start date (11/24/2026)"), so the zero-AVC check failed with a parse error (not an AVC). Marker now written with `LC_ALL=C date '+%x %X'`.
- Commit: 6d97daa. File: `extensions/molecule/vm/prepare.yml`.

**4. [Rule 1 - Bug, Plan 11 pre-decided harness fix] dontaudit re-enabled by a policy rebuild during converge (alma10)**
- Converge installed `container-selinux` on the AlmaLinux 10.2 box, rebuilt the policy (Types 4670 -> 4717, Dontaudit 8012) and re-enabled dontaudit rules, so the Dontaudit == 0 assertion failed. Applied the pre-decided fix: `container-selinux` (and `passt-selinux` when `dnf repoquery` offers it) are installed in `prepare.yml` before `semodule -DB` and the marker. The assertion was not touched and dontaudit is not re-disabled in verify.
- Commit: 2314474.

**5. [Rule 3 - CI infrastructure] slow Ubuntu mirror on hosted runners**
- apt installs of qemu/libvirt took 10+ minutes on several runs; libvirt packages are installed with `--no-install-recommends` (commit c7b0e4a). Temporary diagnostic steps (abe1add, 9935047, e2e7cba) were removed in 8c8e242.

### Spike findings (QA-03 flagged assumptions)

- A11 (Vagrant + vagrant-libvirt on ubuntu-24.04): works. Ubuntu has no `vagrant-libvirt` candidate, so the approved HashiCorp apt repository + `vagrant plugin install vagrant-libvirt --plugin-version 0.12.2` path is used (Vagrant 2.4.9). Decision rule 2 (delegated fallback) was not needed.
- A14 (/dev/kvm on hosted runners): available; the KVM gate passed on every run. Decision rule 1 not triggered.
- Open items from 01-11 now resolved by the green run: `box_architecture: amd64` accepted (catalog mode for alma10; URL box for rocky10), seinfo reads the loaded policy `/sys/fs/selinux/policy`, ausearch returns `<no matches>`/rc 1 with the corrected marker, D-08 label equivalence holds.

## Escalations

### Task 3 (trigger 2, seinfo positive control) - raised on run 45351709513, both legs

Evidence (seinfo reading the loaded kernel policy `/sys/fs/selinux/policy`):

```
Statistics for policy file: /sys/fs/selinux/policy
Policy Version:             33 (MLS enabled)
  Allow:             57947    Neverallow:            0
  Auditallow:          149    Dontaudit:          7802
  Allowxperm:            0    Neverallowxperm:       0
  Auditallowxperm:       0    Dontauditxperm:        0
```

Additional diagnostics captured in the next run (rocky10, prepare): `seinfo --version` 4.7.1; `sestatus`: SELinux enabled, loaded policy targeted, current mode enforcing, mode from config enforcing, MLS enabled, max kernel policy version 33; `/sys/fs/selinux/policy` present (`-r--r--r--`), `/etc/selinux/targeted/policy/policy.35` present.

Classification: the probe read the right artifact; only the regex was wrong (anchored to line start).

User answer (verbatim, relayed by the coordinator): "seinfo-parse-fix (no "+ repo-checksum", so keep alma10 on Vagrant Cloud catalog mode with the pinned version; record that deviation in the SUMMARY)". Applied: only the parse fix; positive control > 0, == 0 after `semodule -DB`, the verify checks before/after reboot and the policy sha256 check are unchanged.

Task 3 triggers 1 (AVC / D-08 label mismatch) and 3 (exhausted repair budget): not triggered. Task 4 (local VM run, D-16): not triggered.

## Known Stubs

None.

## Threat Flags

None (no new network endpoints or trust boundaries; the `/dev/kvm` MODE=0666 udev rule exists only in the workflow on ephemeral runners, T-01-21, documented in README).

## Pending user confirmation

The `molecule-vm` workflow is documented as not a required merge check until it has five consecutive green runs (README, RESEARCH Pitfall 11); to be confirmed at /gsd:verify-work. One green run so far.

## Self-Check: PASSED

- `.github/workflows/molecule-vm.yml`, README `## Testing`, `extensions/molecule/vm/molecule.yml`: present.
- Commits 5017478, 8c8e242, fa45862, e5adbc0, 6d97daa, 2314474 reachable from HEAD.
- Latest `molecule-vm` run on main: success on both legs.
