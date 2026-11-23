# Phase 1: Rootless-фундамент и тестовый стенд - Pattern Map

**Mapped:** 2026-11-23
**Files analyzed:** 33 (new files; no modified files)
**Analogs found:** 0 in-repo / 33 (greenfield). 33 have an external reference captured in 01-RESEARCH.md (line numbers below refer to that file).

## Greenfield statement

`git ls-files` outside `.planning/` returns only `.claude/CLAUDE.md`. `.devcontainer/` is untracked and holds only `devcontainer.json`. There is no source code to copy from, so no in-repo analog exists for any file below. The tracked-source gate is trivially satisfied: no mirror or gitignored path is named. The "analog" column points to verified external patterns in RESEARCH.md (`fedora.linux_system_roles.podman` 2.5.0 source, the lint configs verified green on a scratch collection, the Molecule config shapes verified via `molecule list`).

**Rule for the planner:** the first files written (Wave 0 scaffold, plus the first role) become the in-repo analogs for everything after. Later plans and Phases 2-4 should cite them, not RESEARCH.md. Plan the scaffold and `preflight` first, and keep them lint-clean from the first commit.

## File Classification

| New file | Role | Data flow | Reference pattern (external) | Match |
|----------|------|-----------|------------------------------|-------|
| `galaxy.yml` | config | n/a | RESEARCH "galaxy.yml" (L412-431) | external-verified |
| `meta/runtime.yml` | config | n/a | RESEARCH L431, Pitfall 1 | external-verified |
| `changelogs/changelog.yaml` | config | n/a | Pitfall 2 (L331-334) | external-verified |
| `README.md` | docs | n/a | none (full README is Phase 5) | none |
| `requirements.yml` | config | n/a | Installation (L137-142) | external-verified |
| `requirements-dev.txt` | config | n/a | Installation (L137-142) | external-verified |
| `ansible.cfg` | config | n/a | Pitfall 13 (`pipelining = True`) | external-assumed |
| `.ansible-lint` | config | n/a | Code Examples (L387-397) | external-verified |
| `.yamllint` | config | n/a | Code Examples (L398-409) | external-verified |
| `roles/preflight/tasks/main.yml` | role tasks | request-response (read-only checks) | Pattern 1 (L222-232) | external-verified |
| `roles/preflight/defaults/main.yml` | config | n/a | argument_specs skeleton (L433-450) | external-verified |
| `roles/preflight/meta/argument_specs.yml` | config | n/a | L433-450 | external-verified |
| `roles/preflight/meta/main.yml` | config | n/a | none; no `meta` dependencies (D-09) | none |
| `roles/common/tasks/main.yml` | role tasks | CRUD (packages, firewalld) | Pattern 4 (L287-291) | external-verified |
| `roles/common/defaults/main.yml`, `meta/argument_specs.yml`, `meta/main.yml` | config | n/a | L433-450 | external-verified |
| `roles/podman_rootless/tasks/main.yml` | role tasks | CRUD (host state) | Pattern 2 (L234-241) | external-verified |
| `roles/podman_rootless/tasks/user.yml` | role tasks | CRUD | Pattern 2 steps 1-7 | external-verified |
| `roles/podman_rootless/tasks/quadlet.yml` | role tasks (wrapper) | file-I/O + event-driven (daemon-reload/restart) | Pattern 3 + "LSR call" (L476-488) | external-verified |
| `roles/podman_rootless/tasks/quadlet_validate.yml` | role tasks | transform / request-response | Validation pre-step (L265-285) | external-assumed (A5) |
| `roles/podman_rootless/defaults/main.yml`, `meta/argument_specs.yml`, `meta/main.yml` | config | n/a | L433-450 | external-verified |
| `extensions/molecule/container/{molecule,prepare,converge,verify}.yml` | test | request-response | Pattern 5 (L293-298) | external-verified |
| `extensions/molecule/vm/{molecule,prepare,converge,side_effect,verify}.yml` | test | request-response + reboot | L491-511, Pattern 5 | external-partial (spike) |
| `extensions/molecule/shared/templates/xvpn-fixture.container.j2` | template (Quadlet) | n/a | Fixture Quadlet (L452-474) | external-assumed (A7, A8) |
| `extensions/molecule/shared/verify_*.yml` | test | request-response | Verify tasks (L513-541) | external-verified |
| `.github/workflows/lint.yml` | CI | batch | Validation Architecture "Quick run" (L632-636) | external-verified |
| `.github/workflows/molecule-container.yml` | CI | batch | Pattern 5 (L297) | external-verified |
| `.github/workflows/molecule-vm.yml` | CI | batch | GH Actions VM skeleton (L543-563) | external-assumed (central spike) |

## Pattern Assignments

### Collection scaffold (`galaxy.yml`, `meta/runtime.yml`, `changelogs/changelog.yaml`, `.ansible-lint`, `.yamllint`)

**Reference:** RESEARCH L387-431 (verified: `ansible-lint --profile production`, `yamllint -s` and `ansible-galaxy collection build` all pass on a scratch collection with these files).

```yaml
# .ansible-lint
---
profile: production
supported_ansible_also: ["2.20", "2.21", "2.22"]   # else meta-runtime[unsupported-version]
skip_list:
  - var-naming[no-role-prefix]   # project convention is xvpn_<role>_* (D-04)
exclude_paths:
  - .github/
```

```yaml
# galaxy.yml essentials
namespace: xvpn
name: remnawave
tags: [linux, infrastructure, security]    # production profile needs a tag from a fixed list
dependencies:
  fedora.linux_system_roles: ">=2.5.0"
  ansible.posix: ">=2.2.2"
  community.general: ">=14.0.1"
  containers.podman: ">=1.21.2"
```

`meta/runtime.yml` holds `requires_ansible: ">=2.20.0"`. `changelogs/changelog.yaml` is `ancestor: null` plus `releases: {}`. `.yamllint` is the config at L398-409. `requirements.yml` is the same set plus `community.vagrant` (used by the VM tier driver).

**Planner notes:** `.ansible-lint` and `.yamllint` are copied verbatim from RESEARCH. The `var-naming` skip needs a comment explaining it. `ansible.cfg` sets `pipelining = True`, because become to an unprivileged user needs it or `acl`.

---

### `roles/preflight/tasks/main.yml` (role tasks, read-only request-response)

**Reference:** Pattern 1, RESEARCH L222-232. Every check runs with `check_mode: false` and `changed_when: false`. Results are appended to a list and one final `ansible.builtin.fail` prints them all.

**Check recipes (exact modules from RESEARCH):**
- OS: `ansible_facts['distribution'] in [...]` and `distribution_major_version == '10'`. The list is a variable.
- SELinux: `command: getenforce`, expect `Enforcing`. Do not use `ansible_facts.selinux`, which is `Missing selinux Python library` without `python3-libselinux`.
- Podman: if installed, parse `podman --version`; otherwise `ansible.builtin.dnf: list: podman` (read-only). Compare with `is version('5.4', '>=')`.
- Ports: `ss -H -ltnpe 'sport = :80'` with `become: true`. The `-e` flag appends `uid:NNNN`. Map the uid with `getent passwd`. A listener owned by a managed `rw-*` user passes (D-05); any other owner fails with the process name and pid.
- DNS: `ansible.builtin.getent` with `database: ahostsv4`, `key: <domain>`, `fail_key: false`. The result `getent_ahostsv4` is a dict keyed by address, so use `| dict2items | map(attribute='key') | unique`. Compare with `xvpn_public_ip`, or with `ansible_facts[iface].ipv4.address` plus `ipv4_secondaries`, where `iface` defaults to `ansible_facts['default_ipv4']['interface']` (D-02). AAAA mismatch: warn only. A mismatch fails unless `xvpn_preflight_dns_check: false` (D-04).

**Invocation pattern (playbook level, not inside the role):** preflight is its own first play with `any_errors_fatal: true`, separate from the changing roles (L302). This satisfies D-06 and success criterion 1 across all hosts.

**Security (V5):** validate domain and user names with a regex in `argument_specs` before they reach `ss`, `getent` or `loginctl`. Use `| quote` or `argv`, never `shell:`.

---

### `roles/*/meta/argument_specs.yml` (config, all three roles)

**Reference:** RESEARCH L433-450. Copy this shape, accepted by lint and core validation:

```yaml
---
argument_specs:
  main:
    short_description: Read-only host checks
    options:
      xvpn_preflight_dns_check:
        description: Enable the DNS check (D-04).
        type: bool
        default: true
```

Cross-role inputs (`xvpn_public_interface`, `xvpn_public_ip`) must be listed in the spec of every role that reads them. There are no `meta/main.yml` dependencies (D-09).

---

### `roles/common/tasks/main.yml` (role tasks, CRUD)

**Reference:** Pattern 4, RESEARCH L287-291.

```yaml
# ansible.posix.firewalld: only add our own rules (D-13)
zone: <zone of external iface>   # firewall-cmd --get-zone-of-interface=<iface>; empty -> --get-default-zone
port: 80/tcp
permanent: true
immediate: true
state: enabled
```

- Ports come from the variable `xvpn_common_firewall_ports` (default empty). Phase 2+ roles append their own.
- The container tier has no running firewalld, so use `offline: true` and assert the permanent config.
- SSH guard (D-14): after firewalld is enabled, `firewall-cmd --zone=<z> --query-service=ssh` must hold, and the role fails before closing anything. Do not change SSH.
- Packages: podman, passt, passt-selinux, container-selinux, firewalld, acl, sudo, python3-libselinux, policycoreutils-python-utils, and audit if needed. The `getenforce == Enforcing` assert goes here.
- Not an analog: do not use the LSR `firewall` or `selinux` roles (whole-state semantics conflict with D-13, L135).

---

### `roles/podman_rootless/tasks/user.yml` (role tasks, CRUD; order is the idempotency story)

**Reference:** Pattern 2, RESEARCH L234-241. The order is mandatory:

1. `file`: `/var/lib/xvpn`, `root:root`, `0755`.
2. `community.general.sefcontext: target=/var/lib/xvpn substitute=/home state=present`, then `restorecon -R /var/lib/xvpn` only when the previous task changed. This must come BEFORE creating users. The source must be exactly `/home` (Pitfall 5).
3. `ansible.builtin.user`: `home: /var/lib/xvpn/<u>`, `shell: /sbin/nologin`, `password_lock: true`, `create_home: true`. The module has no subuid option, so assert with `getsubids <u>` and `getsubids -g <u>`, with a `usermod --add-subuids/--add-subgids` fallback guarded by `when: rc != 0`.
4. `ansible.posix.sysctl: name=net.ipv4.ip_unprivileged_port_start value=80 sysctl_file=/etc/sysctl.d/99-xvpn-unprivileged-ports.conf sysctl_set=true reload=true state=present`. This must come before any unit start.
5. Linger: `command: loginctl enable-linger {{ user }}` with `args: creates: /var/lib/systemd/linger/{{ user }}` (the same idiom LSR uses, `roles/podman/tasks/manage_linger.yml`).
6. `ansible.builtin.systemd: name=user@{{ uid }}.service state=started`, then `wait_for: path=/run/user/{{ uid }}/systemd/private` with retries. LSR does NOT wait for the user manager (A2, to be proven in the VM).
7. Every user-scope task uses `become: true`, `become_user: <svc>`, `become_method: sudo` (not `su`) and `environment: {XDG_RUNTIME_DIR: /run/user/<uid>}`.

**Loop shape:** the role is driven by a variable listing service users (default: `rw-edge` for the Phase 1 test). Phases 2-4 add `rw-panel` and `rw-node` through the same mechanism (D-07).

---

### `roles/podman_rootless/tasks/quadlet.yml` (wrapper, file-I/O + event-driven)

**Reference:** "LSR call", RESEARCH L476-488 and Pattern 3 (L243-263). This is the single interface that Phases 2-4 call: `{user, specs[]}` -> validate -> LSR.

```yaml
- name: Deploy Quadlet specs for one service user
  ansible.builtin.include_role:
    name: fedora.linux_system_roles.podman
  vars:
    podman_pull_image: false          # default true re-pulls with force:true on every run
    podman_run_as_user: "{{ xvpn_user }}"
    podman_activate_systemd_unit: "{{ xvpn_podman_rootless_activate | default(true) }}"
    podman_quadlet_specs:
      - template_src: "{{ xvpn_quadlet_template_dir }}/xvpn-fixture.container.j2"   # absolute path
        run_as_user: "{{ xvpn_user }}"
```

Rules:
- Call it via `include_role`, never via `meta` dependencies.
- `template_src` is rendered on the controller. Compute an absolute path in our own role first (A4).
- LSR also installs `iptables-nft`. Document it; do not fight it.
- The `.container`, `.network` and `.volume` types are written verbatim, so `Notify=healthy`, `HealthCmd` and `[Service]` pass through. This is D-10 conditions (a), (c) and (d).
- Without systemd as PID 1 (the container tier) LSR skips service start. Run the container tier with `systemd: always` and `/usr/sbin/init`.

### `roles/podman_rootless/tasks/quadlet_validate.yml` (generator dry-run, runs BEFORE the LSR call)

**Reference:** RESEARCH L265-285 (D-10 condition (e), which LSR lacks):

```yaml
- name: Render candidate units into a scratch dir
  ansible.builtin.template:
    src: "{{ item.template_src }}"
    dest: "{{ xvpn_scratch.path }}/{{ item.template_src | basename | regex_replace('[.]j2$', '') }}"
    mode: "0600"
  loop: "{{ xvpn_quadlet_specs }}"
- name: Generator dry-run (fails the play on any generator error)
  ansible.builtin.command: /usr/lib/systemd/system-generators/podman-system-generator --user --dryrun
  environment:
    QUADLET_UNIT_DIRS: "{{ xvpn_scratch.path }}"
    XDG_RUNTIME_DIR: "/run/user/{{ xvpn_uid }}"
  become: true
  become_user: "{{ xvpn_user }}"
  register: xvpn_dryrun
  changed_when: false
  check_mode: false
```

The scratch dir needs a prior `tempfile` task, and it must be removed afterwards. The exit code on error is assumed (A5), so the container tier needs a negative test with a deliberately broken unit, and the task also asserts on stderr.

---

### `extensions/molecule/shared/templates/xvpn-fixture.container.j2` (Quadlet template)

**Reference:** RESEARCH L452-474. It is a Molecule fixture only and does not ship in the collection roles (D-12).

```ini
[Container]
Image=docker.io/nginxinc/nginx-unprivileged:1.31-alpine
ContainerName=xvpn-fixture
Network=pasta
PublishPort=80:8080
HealthCmd=wget -q -O /dev/null http://127.0.0.1:8080/
Notify=healthy

[Service]
Restart=always
RestartSec=5
TimeoutStartSec=900

[Install]
WantedBy=default.target
```

No `AutoUpdate=`, no `SecurityLabelDisable`, and the image tag is pinned.

---

### `extensions/molecule/container/*` (test, podman driver)

**Reference:** Pattern 5, RESEARCH L293-298 (the layout was discovered by `molecule list` in the scratch collection).

- Scenarios live under `extensions/molecule/<name>/molecule.yml` (collection mode).
- Use the `ansible:` config key, not `provisioner:`.
- Platforms: `docker.io/rockylinux/rockylinux:10-ubi-init` and `docker.io/almalinux/10-init:10`. Platform keys: `systemd: always`, `privileged: true`, `command: /usr/sbin/init`.
- Install only `molecule-plugins[podman,vagrant]`. Never install the old standalone `molecule-podman` or `molecule-vagrant`.
- Covers: preflight positive and negative cases, the "nothing changed after a preflight failure" assertion (no `rw-edge`, no `/etc/sysctl.d/99-xvpn*`, no linger file, `/var/lib/xvpn` absent), `/etc/hosts` as the DNS stand-in, generator dry-run with the negative broken unit, idempotence, and the `argument_specs.yml`-exists-per-role test.
- Cannot cover: SELinux, the real user manager, reboot. Those belong to the VM tier.

### `extensions/molecule/vm/*` (test, vagrant+libvirt)

**Reference:** RESEARCH L491-511 and the verify tasks at L513-541.

```yaml
driver: {name: vagrant, provider: {name: libvirt}}
platforms:
  - {name: alma10, box: almalinux/10, memory: 4096, cpus: 2, provider_options: {cpu_mode: host-passthrough}}
  - name: rocky10
    box: rocky10-libvirt
    box_url: https://dl.rockylinux.org/pub/rocky/10/images/x86_64/Rocky-10-Vagrant-Libvirt.latest.x86_64.vagrant.libvirt.box
    box_checksum: <from published .CHECKSUM>
```

- The Vagrant Cloud `rockylinux/10` box is stale, so use `box_url`.
- Test sequence: `converge, idempotence, verify, side_effect (reboot), verify`. The reboot lives in `side_effect.yml`, never in the container tier.
- `prepare.yml` runs `semodule -DB`, ensures auditd is up, and records an `avc_marker` timestamp.
- The `verify.yml` assertions come from L513-541:
  - `systemd` `scope: user` with `become_user: rw-edge` and `XDG_RUNTIME_DIR`, checking `ActiveState == 'active'`.
  - `uri` to :80 delegated to localhost.
  - `firewall-cmd --list-all` must not match `3000|3010|8443|2222`.
  - `ausearch -m avc,user_avc,selinux_err,user_selinux_err -ts <marker>` must return rc 1 after converge and after reboot.
  - Also assert `matchpathcon /var/lib/xvpn/rw-edge` is not `var_lib_t` or `default_t`, `systemctl is-active network-online.target`, and `loginctl` linger.
- If vagrant-libvirt fails on the runner, use the pre-decided fallback (Open Question 1, L603): the delegated driver with GenericCloud qcow2 plus cloud-init.
- A time-boxed VM spike precedes this scenario. A home-path spike (`/var/lib/xvpn` + equivalence versus `/home`, comparing AVC counts) must finish before Phases 2-4 hard-code paths (D-08 is `costly`).

### `.github/workflows/*.yml` (CI, batch)

**Reference:** `lint.yml` runs `ansible-lint && yamllint -s . && ansible-galaxy collection build --force` (L632-636). `molecule-container.yml` runs `molecule test -s container` per push. `molecule-vm.yml` follows the skeleton at L543-563:

```yaml
runs-on: ubuntu-24.04
strategy: {fail-fast: false, matrix: {platform: [alma10, rocky10]}}
steps:
  - name: Enable KVM
    run: |
      echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules
      sudo udevadm control --reload-rules && sudo udevadm trigger --name-match=kvm
      test -c /dev/kvm
  - run: molecule test -s vm --platform-name ${{ matrix.platform }}
```

The VM job triggers on PR to main plus nightly, and starts with a hard `/dev/kvm` gate. Keep it non-required for merge until it has several consecutive green runs. The `actions/checkout@v5` version and the apt package list are assumed (L563). Run with a clean runner so no stale `xvpn.remnawave` copy sits in `~/.ansible/collections` (Pitfall 12). The `requirements-dev.txt` install needs ONE batched `checkpoint:human-verify` for the SUS-flagged pip packages, not one per package.

## Shared Patterns

These apply across the new roles. None of them has an in-repo source yet.

### Variable naming and `argument_specs`
**Source:** CONTEXT code_context and RESEARCH Pitfall 3.
**Apply to:** all roles. Variables use the `xvpn_<role>_*` prefix, with `xvpn_public_interface` and `xvpn_public_ip` as shared names. Every role has `meta/argument_specs.yml`. There are no `meta` dependencies. Inter-role calls use `include_role ... tasks_from`. The lint skip for `var-naming[no-role-prefix]` backs this convention.

### Read-only versus mutating
**Source:** Pattern 1.
**Apply to:** `preflight` only. `check_mode: false` plus `changed_when: false`, aggregated failure list, one `fail`. It runs in a separate first play with `any_errors_fatal: true`.

### Rootless become for service users
**Source:** Pattern 2 step 7.
**Apply to:** every task in `podman_rootless` and Molecule verify that touches a user unit: `become_user`, `become_method: sudo`, `XDG_RUNTIME_DIR`, and `pipelining = True` in `ansible.cfg`.

### SELinux enforcing
**Source:** Pitfall 9, Security Domain.
**Apply to:** `common` (assert) and the VM verify (AVC = 0, `dontaudit` disabled). Never `setenforce 0`, never `SecurityLabelDisable`. Add a boolean only after an AVC proves the need.

### Command-injection hygiene
**Source:** Security Domain V5.
**Apply to:** every `command:` task that interpolates inventory values. Use regex validation in `argument_specs`, and `argv` or `| quote`. Avoid `shell:`.

## No Analog Found

All 33 files lack an in-repo analog (greenfield). Besides the external references above, these have no reference at all and need the planner's judgment:

| File | Role | Data flow | Reason |
|------|------|-----------|--------|
| `README.md` | docs | n/a | Full README is Phase 5; only a minimal stub is needed for `galaxy.yml: readme` |
| `roles/*/meta/main.yml` | config | n/a | Minimal `galaxy_info` only; D-09 forbids dependencies |
| `extensions/molecule/vm/*` (driver config and recipe) | test | n/a | The Vagrant+libvirt recipe on hosted runners is unproven; spike first |
| `.github/workflows/molecule-vm.yml` apt package list | CI | batch | No complete working recipe found (RESEARCH L563) |

## Metadata

**Analog search scope:** whole repository (`git ls-files`, `.devcontainer/`). Only `.claude/CLAUDE.md` and `.planning/` are tracked; no source exists.
**Files scanned:** 3 (CONTEXT.md, RESEARCH.md, `.devcontainer/` listing).
**Pattern extraction date:** 2026-11-23
