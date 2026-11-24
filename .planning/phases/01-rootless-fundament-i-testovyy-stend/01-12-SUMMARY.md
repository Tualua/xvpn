PLAN_START: bc5fa2adb021d697ff9047f981e477be28adf778

(DRAFT, plan 01-12 paused at the Task 3 checkpoint; this file is completed by the continuation agent)

## Progress log

- Task 1 done: `.github/workflows/molecule-vm.yml` (KVM gate, matrix alma10/rocky10, timeout 120) and README `## Testing`.
- Task 2 in progress: VM spike in CI.
  - Vagrant + vagrant-libvirt 0.12.2 on ubuntu-24.04: works. Ubuntu has no `vagrant-libvirt` candidate, so the HashiCorp apt + gem 0.12.2 path (approved at 01-09) is the one in use. `/dev/kvm` is available on hosted runners (KVM gate green).
  - Failure 1 (alma10, create): `'utf-8' codec can't decode byte 0x8b`. Root cause: Vagrant treats the direct `vagrantcloud.com/.../vagrant.box` URL as catalog metadata (first redirect has `Content-Type: application/json`), "The metadata for the box was malformed". Fix (commit "fix(01-12): use Vagrant Cloud catalog mode for the alma10 box"): `box: almalinux/10`, `box_version: 10.2.20260914`, `box_architecture: amd64`; Vagrant verifies the catalog sha256 (identical to the previously pinned `24b3ff7c...`). Deviation: the repo-pinned `box_download_checksum` is no longer passed for alma10 (Vagrant rejects it in catalog mode); rocky10 keeps the pinned URL + sha256.
  - Failure 2 (both legs, prepare): see Escalations.
  - CI infrastructure note: the Ubuntu mirror on hosted runners was very slow on several runs (apt install 10+ min); libvirt packages are now installed with `--no-install-recommends`.

## Escalations

### Task 3, trigger 2 (seinfo positive control), both legs, run https://github.com/Tualua/xvpn/actions/runs/45351709513

Failing step: `extensions/molecule/vm/prepare.yml` "Assert the dontaudit probe sees dontaudit rules" (alma10 and rocky10, identical).
Observed `seinfo` output (the loaded kernel policy is already the one read):

```
Statistics for policy file: /sys/fs/selinux/policy
Policy Version:             33 (MLS enabled)
...
  Allow:             57947    Neverallow:            0
  Auditallow:          149    Dontaudit:          7802
  Type_trans:       228581    Type_change:          74
...
  Allowxperm:            0    Neverallowxperm:       0
  Auditallowxperm:       0    Dontauditxperm:        0
```

Classification: the policy has 7802 dontaudit rules, the probe reads the right artifact, but the regex `(?m)^\s*Dontaudit:\s+([0-9]+)` is anchored to the line start while `Dontaudit:` is the second column on the `Auditallow:` line, so it cannot parse it. Same pattern in `extensions/molecule/vm/prepare.yml` (lines 31, 32, 50, 51) and `extensions/molecule/shared/verify_runtime.yml` (lines 289, 290). No assertion was edited; no fix commits for this failure.

(user answer: pending)
