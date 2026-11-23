# Phase 1: Rootless-фундамент и тестовый стенд - Research

**Researched:** 2026-11-23
**Domain:** Ansible collection scaffolding, rootless Podman + Quadlet on EL10 (SELinux enforcing), preflight checks, Molecule container + VM tiers, GitHub Actions CI
**Confidence:** MEDIUM-HIGH (tooling, LSR role internals, package facts, lint behaviour verified this session; VM-on-runner stability, SELinux AVC outcomes and the nologin/linger/user-manager race can only be proven in an enforcing VM and are flagged as spikes)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Preflight (FND-01, FND-07)**
- **D-01:** Хост может иметь два интерфейса (внешний с публичным IP и внутренний LAN); NAT не предполагается. A-запись домена сравнивается с IP **внешнего** интерфейса.
- **D-02:** Внешний интерфейс по умолчанию — интерфейс default route (`ansible_default_ipv4`); переопределяется переменными `xvpn_public_interface` / `xvpn_public_ip`. Тот же паттерн позже будет для `xvpn_lan_interface` (Phase 4).
- **D-03:** Детекция проксирования Cloudflare **не делается** — настройка DNS полностью ответственность оператора. Это сужает FND-07 (в REQUIREMENTS/ROADMAP формулировка про Cloudflare убрана). — **Reversibility:** reversible
- **D-04:** Несовпадение A-записи с внешним IP — жёсткий fail; проверка отключается флагом `xvpn_preflight_dns_check: false`.
- **D-05:** Занятые 80/443 определяются по владельцу слушающего процесса (`ss -ltnp`): если порт держит процесс нашего сервисного пользователя (`rw-*`), это не ошибка (повторный прогон идемпотентен); любой другой владелец — fail с именем процесса.
- **D-06:** Preflight не меняет хост (read-only); провал preflight = ничего не изменено (критерий успеха 1).

**Пользователи и роли (FND-02, FND-06)**
- **D-07:** Rootless-пользователи по домену доверия: `rw-edge` (Traefik + заглушка), `rw-panel` (backend/Postgres/Valkey/sub-page), `rw-node` (remnanode). Имена настраиваются переменными. В Phase 1 создаётся механизм и тестовый `rw-edge`; остальные пользователи появятся в своих фазах через тот же механизм. — **Reversibility:** costly — имена пользователей и пути данных зашиты в развёрнутые хосты; смена требует миграции владельцев и home
- **D-08:** Сервисные учётки: обычные UID (>= 1000, чтобы `user@.service`/linger/subuid работали штатно), shell `/sbin/nologin`, без пароля, home в `/var/lib/xvpn/<user>`. Research обязан проверить SELinux-контексты нестандартного home (`semanage fcontext` эквивалентность `/home`, `user_home_dir_t`/`container_file_t` для `~/.config/containers` и `~/.local/share/containers`) и применить идемпотентно. — **Reversibility:** costly — переезд home = перенос хранилища контейнеров
- **D-09:** Роли Phase 1: `preflight` (отдельная, read-only, запускается сама по себе), `common` (firewalld base, SELinux-assert, пакеты), `podman_rootless` (пользователи, linger, subuid/subgid, sysctl, развёртывание Quadlet). Без `meta`-зависимостей, порядок в playbook.

**Механизм развёртывания Quadlet (FND-04) — по запросу пользователя «не изобретать велосипед»**
- **D-10:** Предпочтительно использовать `fedora.linux_system_roles.podman` (Linux System Roles; в RHEL — `rhel-system-roles.podman`) для развёртывания rootless Quadlet (`podman_quadlet_specs` с нашими `template_src`, `run_as_user`), а наш `podman_rootless` отвечает за создание пользователей, home и sysctl (LSR требует, чтобы пользователь уже существовал). **Условие:** research/spike подтверждает на EL10 + Podman 6: (a) поддержку нужных Quadlet-ключей (`Notify=healthy`, `HealthCmd`, `.network`/`.volume`, raw `[Service]`), (b) идемпотентность (`changed=0`), (c) перезапуск только изменённых юнитов, (d) работу с home в `/var/lib/xvpn`, (e) возможность добавить generator dry-run валидацию (своим шагом до/после). Если хотя бы одно не выполняется — пишем собственный тонкий хелпер `deploy_quadlet` (template + `podman-system-generator --user --dryrun` + daemon-reload + restart changed) и фиксируем обоснование в RESEARCH.md. — **Reversibility:** costly — от выбора зависит интерфейс, через который все роли Phase 2-4 разворачивают юниты
- **D-11:** Мелкие community-роли (`safeaim/podman_rootless`, `voidquark/podman_play`) не использовать (bus-factor, `.kube` запрещён в STACK).

**Тестовый сервис и firewalld (FND-03, FND-05)**
- **D-12:** «Тестовый Quadlet-сервис на :80» — только Molecule-фикстура: в converge через механизм D-10 разворачивается `nginx-unprivileged` под `rw-edge`, слушает 80. В коллекции не остаётся; Phase 2 заменит его Traefik.
- **D-13:** firewalld — только добавляем своё: роль открывает нужные ей порты в зоне внешнего интерфейса, чужие правила оператора не трогает. Verify проверяет, что внутренние порты (3000/3010/8443/2222) снаружи не открыты.
- **D-14:** SSH не трогаем (порт и правила — у оператора); роль лишь проверяет, что сервис ssh остаётся разрешён, чтобы не потерять доступ. LAN-зона — Phase 4.

**Molecule и CI (QA-01, QA-02, QA-03)**
- **D-15:** VM-тир обязателен: SELinux, AVC, boolean'ы и reboot невозможно проверить в контейнере (dind/podman-in-podman делят ядро хоста; на Ubuntu-раннерах SELinux выключен). Контейнерный тир (podman-драйвер, не Docker) — для рендера, dry-run, идемпотентности, логики preflight, lint.
- **D-16:** VM-тир запускается на GitHub-hosted раннерах с `/dev/kvm` (PR в main + nightly) и локально одной командой. Если research покажет, что KVM на раннерах не работает — VM-тир остаётся локальным, это документируется.
- **D-17:** Репозиторий — GitHub, CI — GitHub Actions (`.github/workflows`).
- **D-18:** VM-тир покрывает и AlmaLinux 10, и Rocky 10.

### Claude's Discretion
- Драйвер VM для Molecule: Vagrant+libvirt (box `almalinux/10`, Rocky из cloud-образа) или delegated + официальные GenericCloud-образы через virt-install/cloud-init — выбирает research по стабильности на GitHub-раннерах.
- Резолвер для проверки A-записи (системный резолвер хоста по умолчанию; Cloudflare-детекции нет).
- Использовать ли LSR `firewall`/`selinux` роли вместо `ansible.posix.firewalld`/`seboolean` — при условии соблюдения D-13 (только добавлять своё).
- Формат сообщений preflight и структура переменных (`xvpn_<role>_*`).

### Deferred Ideas (OUT OF SCOPE)
- `xvpn_lan_interface` и firewalld-зона для LAN — Phase 4.
- Управление SSH (порт, sshd_config) — Phase 5 (hardening).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FND-01 | Понятная ошибка preflight (ОС, SELinux, Podman < 5.4, порты 80/443) | Preflight pattern: `getenforce`, `dnf list` for podman candidate, `ss -H -ltnpe` (uid field), aggregated error list + single `fail`; separate first play with `any_errors_fatal` |
| FND-02 | Выделенный rootless-пользователь, linger, subuid/subgid, `systemctl --user` из Ansible | `ansible.builtin.user` (no subid options -> verify with `getsubids`), `loginctl enable-linger` with `creates:`, start `user@UID.service`, `environment: XDG_RUNTIME_DIR` (documented in `ansible-doc ansible.builtin.systemd`) |
| FND-03 | Rootless-контейнеры слушают 80/443 | `ansible.posix.sysctl` `net.ipv4.ip_unprivileged_port_start` persisted in `/etc/sysctl.d/` + `reload: true`, applied BEFORE first unit start; verify = fixture answers on :80 after reboot |
| FND-04 | Quadlet из шаблонов, dry-run генератора, переживает reboot | LSR `podman_quadlet_specs` + own pre-validation step with `QUADLET_UNIT_DIRS` + `podman-system-generator --user --dryrun`; reboot test via Molecule `side_effect` |
| FND-05 | firewalld + SELinux без permissive и AVC | `ansible.posix.firewalld` (only own ports, zone of external iface), SELinux assert via `getenforce`, home fcontext equivalence via `community.general.sefcontext substitute`, AVC check via `ausearch` + `semodule -DB` in VM tier |
| FND-06 | `galaxy.yml`, `argument_specs`, Galaxy-ready структура | Verified scratch collection: required `galaxy.yml` tags, `changelogs/`, `meta/runtime.yml`, `.ansible-lint` config (see Pitfalls 1-3) |
| FND-07 | A-запись каждого домена -> IP внешнего интерфейса | `ansible.builtin.getent database=ahostsv4` (host resolver, verified output shape), compare with `ansible_facts[iface].ipv4(.address + secondaries)` / `xvpn_public_ip` |
| QA-01 | ansible-lint + yamllint в CI | Verified: ansible-lint 26.11.0 `production` passes on a scratch collection with the config in Code Examples |
| QA-02 | Molecule контейнерный тир | `podman` driver, `extensions/molecule/container`, images `docker.io/rockylinux/rockylinux:10-ubi-init` / `docker.io/almalinux/10-init:10` |
| QA-03 | Molecule VM-тир (SELinux, AVC=0, idempotence, reboot) | `vagrant` driver + libvirt, boxes verified, KVM on hosted runners (cited, spike-gated), fallback documented |
</phase_requirements>

## Summary

Phase 1 is a scaffolding + proof phase: three roles (`preflight`, `common`, `podman_rootless`), one throwaway nginx-unprivileged Quadlet fixture, and two Molecule tiers wired into GitHub Actions. The decisive technical findings are: (1) the `fedora.linux_system_roles.podman` role (LSR 2.5.0) satisfies all five D-10 conditions after reading its source, **provided** we set `podman_pull_image: false` (the role otherwise runs `podman_image` with `force: true` on every run), pass absolute `template_src` paths, and add our own pre-validation step - so D-10 resolves to "use LSR, no custom `deploy_quadlet`"; (2) the `user@.service` drop-in research flag is largely moot: Podman >= 5.3 already makes every rootless Quadlet unit `After=podman-user-wait-network-online.service`, and that unit ships in the real EL10 RPMs for Podman 5.4.0 and 6.1.4 (verified by listing the RPMs); (3) KVM on GitHub-hosted standard Linux runners is documented by GitHub staff/changelog since April 2024 (needs a udev rule), but not on the official runner reference page, so the VM tier needs a first-job `/dev/kvm` gate and a documented local fallback.

The biggest hidden costs found: `ansible-lint` `production` profile (a) rejects `requires_ansible: ">=2.20.0"` unless `supported_ansible_also` is configured, (b) demands `galaxy.yml` tags and a changelog, and (c) enforces `var-naming[no-role-prefix]` which conflicts with the locked `xvpn_<role>_*` / `xvpn_preflight_dns_check` names (D-04) - resolve by `skip_list` for that one rule, not by renaming user-facing variables. The VM driver recommendation is Vagrant+libvirt through the official `molecule-plugins[vagrant]` (boxes exist for both distros), but `vagrant-libvirt` upstream has had no release since 2023-06 and no commit since 2023-12, so the first plan must contain a time-boxed spike with a pre-designed fallback (delegated driver + GenericCloud qcow2 + cloud-init).

**Primary recommendation:** Build the collection scaffold first (lint-clean from commit 1), implement `preflight` as a read-only first play that aggregates all failures into one message, implement `podman_rootless` as user/home/SELinux-equivalence/sysctl/linger/user-manager plumbing that then calls LSR `podman` per user via `include_role` (never `meta` dependency), and prove everything in an enforcing AlmaLinux 10 + Rocky 10 VM (converge, `changed=0`, reboot, zero AVC with `dontaudit` disabled) while the container tier covers preflight logic, rendering, generator dry-run and negative tests.

## Project Constraints (from CLAUDE.md)

- Reply to user in Russian; code, paths, technical terms stay English (RESEARCH.md stays English).
- Platform: Rocky/Alma Linux 10 only; SELinux enforcing mandatory, never permissive; no `SecurityLabelDisable`, no `--privileged` containers, no `setenforce 0`.
- Runtime: rootless Podman + Quadlet (systemd user units), no Docker; `.kube`/`.pod` not used; `AutoUpdate=` off.
- TLS Let's Encrypt HTTP-01 on port 80; Traefik (Phase 2) - not needed here but port 80 sysctl is.
- Quality: idempotence, Molecule + CI, ansible-lint; collection is public/open-source (README/examples are Phase 5, but structure must be Galaxy-ready now).
- `containers.podman >= 1.21.2`, `ansible.posix 2.2.2`, `community.general 14.0.1`; `requires_ansible >=2.20.0`; Molecule/ansible-lint 26.11.0; Podman floor 5.4 asserted via `podman --version`.
- Do not depend on `community.postgresql`. Pin image tags; never `latest`.
- Variable convention `xvpn_<role>_*`, `meta/argument_specs.yml` in every role, no `meta` dependencies between roles, inter-role calls via `include_role ... tasks_from` (ARCHITECTURE.md, CONTEXT code_context).
- GSD workflow: file-changing work goes through GSD commands (planner/executor concern, not research).
- User memory: prefer maintained Galaxy roles/collections over bespoke helpers; justify rejections (done in "D-10 verdict").

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Host eligibility checks (OS, SELinux, Podman, ports, DNS) | Target host (read-only commands) | Control node (assert/aggregate) | Facts live on the target; the decision/message is rendered by Ansible |
| Service users, subuid/subgid, linger, home | Target host (OS accounts, systemd-logind) | - | Pure host state |
| SELinux file-context equivalence for `/var/lib/xvpn` | Target host (policy store) | - | `semanage` local policy, persistent across reboot |
| Port 80/443 for unprivileged users | Target host kernel (sysctl) | - | Host-global sysctl in `/etc/sysctl.d/` |
| Quadlet unit rendering | Control node (Jinja render) | Target host (generator dry-run + systemd) | LSR renders `template_src` via `lookup('template')` on the controller; the generator validates on target |
| Service lifecycle (start, restart-on-change, boot) | Target host (systemd --user via linger) | - | systemd user manager owns it |
| Firewall base | Target host (firewalld) | - | Zone of the external interface |
| Test orchestration | CI runner / developer workstation | Ephemeral container (tier 1) / KVM VM (tier 2) | Tier 2 is the only place SELinux + user manager + reboot are real |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ansible-core | 2.21.x primary (local devcontainer has 2.22.0; GH Ubuntu 24.04 image has 2.21.6) | Engine | [VERIFIED: GH runner image readme "Ansible: 2.21.6"; `ansible --version` in this devcontainer = core 2.22.0] |
| molecule | 26.11.0 | Scenario runner | [VERIFIED: pip install in this session, `pip list`] |
| molecule-plugins | 26.11.0 (extras `podman`, `vagrant`) | Drivers `podman`, `vagrant` | [VERIFIED: entry points listed: `podman molecule_plugins.podman.driver:Podman`, `vagrant molecule_plugins.vagrant.driver:Vagrant`] |
| ansible-lint | 26.11.0 | Lint, profile `production` | [VERIFIED: run on scratch collection] |
| yamllint | 1.38.0 | YAML lint | [VERIFIED: pip list] |
| python-vagrant | 1.0.0 | Pulled by `molecule-plugins[vagrant]` | [VERIFIED: pip list after install] |
| `fedora.linux_system_roles` (role `podman`) | 2.5.0 (Galaxy, updated 2026-09-17; `requires_ansible >=2.16.0`) | Rootless Quadlet deployment | [VERIFIED: downloaded collection tarball, read `roles/podman/tasks/*`, `meta/runtime.yml`; deps in MANIFEST: ansible.posix, community.general, containers.podman] |
| `ansible.posix` | 2.2.2 | `firewalld`, `sysctl` | [VERIFIED: Galaxy API + `ansible-doc` options list] |
| `community.general` | 14.0.1 | `sefcontext` (has `substitute`) | [VERIFIED: `ansible-doc community.general.sefcontext` shows `substitute` = SELinux file-context equivalence] |
| `community.vagrant` | 1.0.1 (2026-09-30) | Module used by the molecule vagrant driver (`community.vagrant.vagrant`) | [VERIFIED: molecule_plugins/vagrant/playbooks/create.yml; Galaxy API] |
| `containers.podman` | >=1.21.2 | Pulled by LSR; `podman_image` used by LSR | [CITED: STACK.md] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Vagrant (HashiCorp) | 2.4.9 (2025-08-21) or distro `vagrant` | VM tier on runner | Only if the VM spike passes |
| vagrant-libvirt plugin | 0.12.2 (2023-06-24; last commit 2023-12-27) | libvirt provider | Dormant upstream; see Open Questions |
| libvirt + QEMU + libvirt-dev (apt) | distro | VM host on `ubuntu-24.04` | Runner prep step |
| Pebble | - | Mock ACME | Phase 2 (QA-05), not Phase 1 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LSR `podman` role | Own `deploy_quadlet` (template + generator dry-run + daemon-reload + restart) | Rejected: LSR meets D-10 (a)-(d); (e) is addable as a pre-step. Own helper would re-implement restart-on-change, dependency restarts, rootless env handling |
| LSR `podman` role | `containers.podman.podman_quadlet` module | Rejected: wraps `podman quadlet install` which does not exist on the Podman 5.4 floor, and Podman 6 reworked the layout into subdirectories [CITED: Podman v6.0.0 release notes] |
| Vagrant+libvirt | delegated driver + GenericCloud qcow2 + cloud-init (`virt-install`) | Fallback if vagrant-libvirt fails on runner; ~150 lines of create/destroy playbooks we own |
| Vagrant+libvirt | `molecule-libvirt-ng` 1.0.3 (2026-02-16, Beta, single maintainer, no cloud-init mention) | Rejected: bus-factor (same logic as D-11) |
| Vagrant+libvirt | `molecule-qemu` 0.5.12 (2024-10-28) | Rejected: stale, small |
| LSR `firewall`/`selinux` roles | `ansible.posix.firewalld` + `community.general.sefcontext` | Use the modules: LSR `firewall` role manages whole-state semantics that fight D-13 (only add own rules) [ASSUMED: role semantics not re-read this session] |

**Installation (CI / developer controller):**
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install "molecule==26.11.0" "molecule-plugins[podman,vagrant]==26.11.0" "ansible-lint==26.11.0" "yamllint==1.38.0" "ansible-core>=2.21,<2.22"
ansible-galaxy collection install -r requirements.yml   # fedora.linux_system_roles, ansible.posix, community.general, containers.podman, community.vagrant
```

**Version verification:** molecule/molecule-plugins/ansible-lint 26.11.0 resolved by `pip install` in this session; Galaxy API returned `fedora.linux_system_roles` 2.5.0, `community.vagrant` 1.0.1, `ansible.posix` 2.2.2.

## Package Legitimacy Audit

Seam (`gsd-tools query package-legitimacy check --ecosystem pypi ...`) returned **SUS for every package**. The reasons are heuristic artefacts of the seam (`unknown-downloads`/`no-repository` because PyPI metadata carries no download counts; `too-new` = latest release published Nov 2026), not real red flags: first PyPI uploads date 2012-2023 and all are the long-standing ansible-community / pycontribs projects already pinned in STACK.md.

| Package | Registry | Age (first upload) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| molecule | PyPI | 2017-02 | n/a (seam) | github.com/ansible/molecule | SUS (heuristic: too-new, unknown-downloads, no-repository) | Flagged - single batched human-verify checkpoint, hash/version-pin in requirements |
| molecule-plugins | PyPI | 2023-01 | n/a | github.com/ansible-community/molecule-plugins | SUS (same) | Flagged - same checkpoint |
| ansible-lint | PyPI | 2014-09 | n/a | github.com/ansible/ansible-lint | SUS (same) | Flagged - same checkpoint |
| yamllint | PyPI | 2016-01 | n/a | github.com/adrienverge/yamllint | SUS (unknown-downloads, no-repository) | Flagged - same checkpoint |
| python-vagrant | PyPI | 2012-06 | n/a | github.com/pycontribs/python-vagrant | SUS (unknown-downloads) | Flagged - same checkpoint |
| ansible-core | PyPI | - | n/a | github.com/ansible/ansible | SUS (too-new, unknown-downloads) | Flagged - same checkpoint |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** all above - planner inserts ONE `checkpoint:human-verify` ("confirm pinned versions in `requirements-dev.txt` against upstream repos") before the first install task, not one per package. Galaxy collections are not covered by the seam; all were resolved from the Galaxy API and downloaded/inspected this session (`fedora.linux_system_roles`, `community.general`, `ansible.posix`, `containers.podman`, `community.vagrant`) [VERIFIED: Galaxy API].

## Architecture Patterns

### System Architecture Diagram

```
Operator / CI                       Target host (EL10, SELinux enforcing)
-----------                         ------------------------------------------------------
ansible-playbook
  |
  |- Play 1 (hosts: all, any_errors_fatal)        READ-ONLY, runs on every host first
  |    role preflight --ssh--> getenforce | dnf list podman | ss -H -ltnpe | getent ahostsv4
  |         |                  (check_mode:false, changed_when:false)
  |         '--> collect ALL failures --> one fail() with all messages  --> STOP, host untouched
  |
  |- Play 2 (only if Play 1 passed everywhere)
       role common -----------> dnf (podman, passt, container-selinux, firewalld, acl, sudo,
       |                              python3-libselinux, policycoreutils-python-utils, audit?)
       |                        firewalld: enabled+started; assert ssh allowed; open own ports
       |                        assert getenforce == Enforcing
       role podman_rootless --> /var/lib/xvpn (root:root 0755)
            |                   sefcontext substitute /var/lib/xvpn -> /home ; restorecon
            |                   user rw-edge (uid>=1000, nologin, home /var/lib/xvpn/rw-edge)
            |                   subuid/subgid present? (getsubids) else usermod --add-sub*
            |                   sysctl net.ipv4.ip_unprivileged_port_start=80 (file + live)
            |                   loginctl enable-linger ; systemd: user@UID.service started
            |                   wait /run/user/UID/systemd/private
            |
            '--include_role--> fedora.linux_system_roles.podman  (podman_pull_image:false)
                 per quadlet spec: validate (QUADLET_UNIT_DIRS dry-run) -> copy unit into
                 ~/.config/containers/systemd/ -> daemon-reload (user) -> start/restart iff changed
                                       |
                              podman-system-generator --user  -->  xvpn-fixture.service (user mgr)
                                       |  After=podman-user-wait-network-online.service
                                       v
                              pasta + nginx-unprivileged (:8080) published on host :80
  Verify (Molecule): systemctl --user is-active | curl :80 | firewall-cmd | ausearch AVC=0
                     reboot (side_effect) -> same asserts again
```

### Recommended Project Structure
```
galaxy.yml                      # namespace xvpn, name remnawave; tags linux/infrastructure; dependencies
README.md
requirements.yml                # collection deps for dev/CI (same set as galaxy.yml dependencies + community.vagrant)
requirements-dev.txt            # molecule, molecule-plugins[podman,vagrant], ansible-lint, yamllint (pinned)
.ansible-lint  .yamllint
ansible.cfg                     # pipelining = True (needed for become to unprivileged users)
changelogs/changelog.yaml       # required by galaxy[no-changelog]
meta/runtime.yml                # requires_ansible: ">=2.20.0"
roles/
  preflight/       {defaults,tasks,meta/{main,argument_specs}.yml}
  common/          {defaults,tasks,templates?,meta/...}
  podman_rootless/ {defaults,tasks (main, user.yml, quadlet.yml), meta/...}
extensions/molecule/            # collection-mode scenarios (MOLECULE_COLLECTION_ROOT = "extensions/molecule")
  container/  {molecule.yml,converge.yml,verify.yml,prepare.yml}
  vm/         {molecule.yml,prepare.yml,converge.yml,side_effect.yml,verify.yml}
  shared/     fixture quadlet templates, verify tasks (included by both tiers)
.github/workflows/{lint.yml,molecule-container.yml,molecule-vm.yml}
```

### Pattern 1: Read-only preflight that reports everything at once
**What:** Every check is a read-only module/command (`check_mode: false`, `changed_when: false`); results append to a `list`; one final `ansible.builtin.fail` prints all messages. Preflight is its own first play with `any_errors_fatal: true`, so no later role runs on ANY host if ANY host fails (D-06 / success criterion 1).
**When to use:** Always for FND-01/FND-07.
**Key implementation facts (all verified this session):**
- OS: `ansible_facts['distribution'] in ['Rocky','AlmaLinux']` and `ansible_facts['distribution_major_version'] == '10'` (make the list a variable; CLAUDE.md constrains to Rocky/Alma).
- SELinux: use `command: getenforce` (rc 0, stdout `Enforcing`). Do NOT rely on `ansible_facts.selinux` - without `python3-libselinux` the fact is `Missing selinux Python library` [VERIFIED: ansible/module_utils/facts/system/selinux.py:49 `selinux_facts['status'] = 'Missing selinux Python library'`].
- Podman: if installed, parse `podman --version`; if not yet installed, `ansible.builtin.dnf: list: podman` (read-only) and take the newest `available` version. Compare `is version('5.4', '>=')`. Preflight must not install anything.
- Ports: `ss -H -ltnpe 'sport = :80'` (run with `become: true`) - the `-e` flag appends `uid:NNNN` per socket [VERIFIED: local `ss -H -ltnpe` output shows `... users:(("claude",pid=30217,fd=23)) uid:1000 ...`]. Map uid -> user via `getent passwd`; a listener whose uid belongs to the managed service-user set passes (idempotent re-run, D-05); any other uid fails with process name (`users:(("name",...))`) and pid.
- DNS: `ansible.builtin.getent` with `database: ahostsv4`, `key: <domain>`, `fail_key: false` uses the host's NSS resolver (D discretion: host resolver). Returned shape: dict keyed by address, e.g. `getent_ahostsv4: {"127.0.0.1": [["STREAM","localhost"],["DGRAM"],...]}` [VERIFIED: ran `ansible localhost -m getent -a "database=ahostsv4 key=localhost"`]. Use `getent_ahostsv4 | dict2items | map(attribute='key') | unique`.
- Public IP: `xvpn_public_ip` if set; else addresses of `xvpn_public_interface` (default `ansible_facts['default_ipv4']['interface']`) = `ansible_facts[iface]['ipv4']['address']` + `ipv4_secondaries[*].address`. Require every resolved A record to be in that set (a stray record breaks HTTP-01 intermittently).
- Output language of messages: operator-facing messages in English (collection is public); Russian docs come in Phase 5.

### Pattern 2: `podman_rootless` ordering (the order IS the idempotency story)
1. `file` `/var/lib/xvpn` (root:root 0755).
2. `community.general.sefcontext: target=/var/lib/xvpn substitute=/home state=present` then `restorecon -R` (only when the sefcontext task changed - register + `when: ... is changed`, or `command: restorecon -R -n` pre-check). Do this BEFORE creating users so `useradd` labels the new home correctly.
3. `ansible.builtin.user`: `uid` optional (>=1000 default allocation), `home`, `shell: /sbin/nologin`, `password_lock: true`, `create_home: true`. `ansible.builtin.user` has no subuid/subgid parameter [VERIFIED: `ansible-doc ansible.builtin.user | grep -i subuid` empty], so rely on `useradd` defaults and then assert with `getsubids <user>` / `getsubids -g <user>`; guard a fallback `usermod --add-subuids ... --add-subgids ...` with `when: getsubids rc != 0`.
4. `ansible.posix.sysctl: name=net.ipv4.ip_unprivileged_port_start value=80 sysctl_file=/etc/sysctl.d/99-xvpn-unprivileged-ports.conf sysctl_set=true reload=true state=present` [VERIFIED: option names in `ansible-doc ansible.posix.sysctl`]. Must happen before any unit start (PITFALLS #4).
5. Linger: `command: loginctl enable-linger {{ user }}` with `args: creates: /var/lib/systemd/linger/{{ user }}` (same idiom LSR uses: `creates: /var/lib/systemd/linger/{{ __podman_linger_user }}` [VERIFIED: roles/podman/tasks/manage_linger.yml]).
6. Immediately start and wait for the user manager - LSR does NOT wait (no `wait_for`/`/run/user` wait anywhere in its tasks [VERIFIED: grep of roles/podman/tasks]): `ansible.builtin.systemd: name=user@{{ uid }}.service state=started` (system scope) then `ansible.builtin.wait_for: path=/run/user/{{ uid }}/systemd/private` (retries). [ASSUMED: that `user@UID.service` Type=notify only turns active once the manager is up, and that `/run/user/UID/systemd/private` is the socket - confirm in VM spike].
7. Every user-scope task: `become: true`, `become_user: <svc>`, `environment: {XDG_RUNTIME_DIR: /run/user/<uid>}` [CITED: ansible-doc ansible.builtin.systemd `scope` note and example "Run a user service when XDG_RUNTIME_DIR is not set on remote login"]. Use `become_method: sudo` (not `su`: `nologin` shell breaks `su`) [ASSUMED]; install `sudo` and `acl` in `common`, and set `pipelining = True`.

### Pattern 3: Quadlet deployment through LSR (D-10 verdict)

| D-10 condition | Result | Evidence |
|---|---|---|
| (a) arbitrary Quadlet keys (`Notify=healthy`, `HealthCmd`, `.network`, `.volume`, raw `[Service]`) | PASS | Role writes the rendered text verbatim: `copy: content: "{{ __podman_quadlet_str }}"`; `.network/.volume/.container/.pod/.kube` types handled; service names derived `-network.service`/`-volume.service` [VERIFIED: tasks/create_update_quadlet_spec.yml, tasks/handle_quadlet_spec.yml]. No key-level parsing of file content except `Image=` and `Volume=` regex |
| (b) idempotency | PASS only with `podman_pull_image: false` | Default `podman_pull_image: true` runs `containers.podman.podman_image` with `force: true` on every run [VERIFIED: tasks/handle_images.yml `force: true`; defaults/main.yml `podman_pull_image: true`] - this both hits the registry each run (Docker Hub rate limits) and would silently move floating tags. Set false; the first unit start pulls (Quadlet default `Pull=missing`; set `TimeoutStartSec=900`). `sr_fingerprint` returns `changed=False` [VERIFIED: plugins/modules/sr_fingerprint.py:315,337] |
| (c) restart only changed units | PASS | `Start service` / `Restart service` tasks guarded by `__podman_copy_content is changed or ... __podman_template_file is changed`; dependency (`.network/.volume`) changes queue deferred restarts [VERIFIED: create_update_quadlet_spec.yml; flush_pending_restarts.yml] |
| (d) home in `/var/lib/xvpn` | PASS | Quadlet path = `getent_passwd[user][4]` (home field) + `/.config/containers/systemd` [VERIFIED: handle_quadlet_spec.yml `__podman_user_home_dir: "{{ ansible_facts['getent_passwd'][__podman_user][4] }}"`] |
| (e) generator dry-run validation | NOT built in -> add own pre-step | No `dryrun` string anywhere in the role [VERIFIED: grep of tasks/main.yml, set_vars.yml, handle_quadlet_spec.yml returned no dryrun/generator]. The role starts units right after writing them, so validation must run BEFORE `include_role` |

**Verdict:** use LSR; do not write `deploy_quadlet`. Wrap it in ONE internal task file of `podman_rootless` (`tasks/quadlet.yml`, entered with `include_role: tasks_from`) so Phase 2-4 roles call a single interface: `{user, specs[]}` -> validate -> `include_role: fedora.linux_system_roles.podman`.

**Known behaviours of LSR that the wrapper must handle** (all from reading the 2.5.0 source):
- `template_src` is rendered with `lookup('template', ...)` on the **controller** [VERIFIED: handle_quadlet_spec.yml]. A relative path resolves in the LSR role's context, not ours. Compute an absolute path in OUR role first (`set_fact: xvpn_quadlet_template_dir: "{{ role_path }}/templates"`) and pass the resolved string. [ASSUMED: relative-path resolution semantics - confirm in container tier].
- Role also installs `iptables-nft`, `podman`, `shadow-utils-subid` on EL10 [VERIFIED: vars/Rocky_10.yml, AlmaLinux_10.yml `__podman_packages`]. `iptables-nft` is harmless but surprising on a Podman 6 (nftables-only) host; document it. Our `common` installs the real package set first.
- `podman_run_as_user` defaults to `root`; set `run_as_user: <svc>` per spec (spec-level key is stripped from the rendered unit by `__del_params`). Multi-user in one call works because user is resolved per spec.
- Version gates are only minimums (4.2/4.4/5.0 for pod) - Podman 6 is not rejected [VERIFIED: tasks/main.yml lines 56-100].
- It enables linger itself but without waiting for the user manager (see Pattern 2 step 6) - always do our own plumbing first.
- `__podman_is_booted` = `systemctl is-system-running` != `offline`; in a container tier without systemd as PID 1 the role silently skips service start [VERIFIED: tasks/set_vars.yml]. Container tier must run with systemd PID 1 or explicitly set `podman_activate_systemd_unit: false`.
- "Cancel linger" runs for a user when ALL its specs are `state: absent` (Phase 5 decommission concern) [VERIFIED: tasks/cancel_linger.yml, main.yml].
- Role needs `fedora.linux_system_roles` as a collection dependency (2.7 MB, ~30 roles); on RHEL proper the downstream name is `rhel-system-roles` (out of scope: Rocky/Alma use the Galaxy collection) [CITED: CONTEXT D-10].

**Validation pre-step (our own):**
```yaml
# tasks/quadlet_validate.yml (runs as the service user; no host change besides a temp dir)
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
`QUADLET_UNIT_DIRS` and `podman-system-generator {--user} --dryrun` are documented in `podman-systemd.unit(5)` [CITED: docs.podman.io podman-systemd.unit.5]; both `/usr/lib/systemd/system-generators/podman-system-generator` and `/usr/lib/systemd/user-generators/podman-user-generator` exist in the EL10 RPMs for 5.4.0 and 6.1.4 (31-byte symlinks) [VERIFIED: listed contents of podman-5.4.0-13.el10_0 and podman-6.1.4-1.el10_3 RPMs from dl.rockylinux.org]. Exit-code-on-error behaviour is [ASSUMED]; the container tier must include a deliberately broken unit as a negative test and assert the task fails (if rc is 0 on errors, additionally assert no `Error` in stderr).

### Pattern 4: firewalld (D-13/D-14)
- `ansible.posix.firewalld` with `zone: <zone of external iface>`, `port: 80/tcp`, `permanent: true`, `immediate: true`, `state: enabled`. Zone discovery: `firewall-cmd --get-zone-of-interface=<iface>` (empty -> `--get-default-zone`). Option names verified in `ansible-doc` (`zone`, `immediate`, `permanent`, `port`, `service`, `offline`, `interface`).
- Container tier has no running firewalld: use `offline: true` (module "Ignores immediate if permanent=true and firewalld is not running") and assert the permanent config.
- Never replace/purge existing rules. Phase 1 opens only what the Phase-1 fixture needs (80/tcp) - the ports list is a role variable (`xvpn_common_firewall_ports`), default empty; Phase 2+ roles append their own.
- SSH guard (D-14): after firewalld is enabled, assert ssh is allowed in the effective zone (`firewall-cmd --zone=<z> --query-service=ssh` or the `ansible_port` as `--query-port`), fail BEFORE closing anything. Do not change SSH.

### Pattern 5: Molecule layout (verified discoverable)
- Molecule 26.11.0 collection mode: scenarios under `extensions/molecule/<name>/molecule.yml` [VERIFIED: `MOLECULE_COLLECTION_ROOT = "extensions/molecule"` in molecule/constants.py:26; `molecule list` found `container` (podman) and `vm` (vagrant) scenarios in the scratch collection].
- New default scenario sequence includes `side_effect` [VERIFIED: generated molecule.yml `test_sequence: dependency, cleanup, destroy, syntax, create, prepare, converge, idempotence, side_effect, verify, cleanup, destroy`] - put the **reboot** in `side_effect.yml` and re-assert in `verify.yml` (or run verify twice by a custom sequence: `converge, idempotence, verify, side_effect, verify`).
- Molecule 26 config accepts both `provisioner:` and `ansible:` keys [VERIFIED: molecule.json top-level properties `['ansible', ..., 'provisioner', ...]`; generated scenario uses `ansible:`]. Pick `ansible:` (new) and keep it consistent.
- Container tier images (exist, updated 2026-11): `docker.io/rockylinux/rockylinux:10-ubi-init` (10.3-based, 2026-11-22), `docker.io/almalinux/10-init:10` (10.3, 2026-11-16) [VERIFIED: Docker Hub tags API]. The container tier runs `podman` driver on the runner (runner has Podman 4.9.3 [VERIFIED: GH Ubuntu2404 readme]); platform keys `systemd: always`, `privileged: true`, `command: /usr/sbin/init`.
- VM tier boxes: Alma - Vagrant Cloud `almalinux/10`, current 10.2.20260914, providers include `libvirt` [VERIFIED: Vagrant Cloud API]. Rocky - the vagrant Cloud `rockylinux/10` box is stale (version 0.0.0, 10.0-era, created 2025-05 [VERIFIED: API]) so use the official file `https://dl.rockylinux.org/pub/rocky/10/images/x86_64/Rocky-10-Vagrant-Libvirt.latest.x86_64.vagrant.libvirt.box` (HTTP 200, last-modified 2026-11-13; 10.3 variant also listed) via platform `box_url` [VERIFIED: directory listing + `curl -I`; `box_url`/`box_version`/`box_checksum`/`memory`/`cpus`/`provider_options` are platform keys of `community.vagrant.vagrant` - plugins/modules/vagrant.py lines 61-120]. Add `box_checksum` from the published `.CHECKSUM` file.

### Anti-Patterns to Avoid
- **`meta/main.yml` role dependencies / calling LSR via `dependencies:`** - violates D-09 and breaks `argument_specs` validation ordering. Use `include_role`.
- **Letting preflight share a play with changing roles** - lockstep execution means host A may change state before host B's preflight fails. Separate first play + `any_errors_fatal`.
- **Relying on LSR to wait for the user manager** - it does not (race, PITFALLS #5).
- **`podman_pull_image: true` (default)** - re-pulls every run (idempotency + registry rate limits + silent tag drift).
- **`/var/lib/xvpn` without fcontext equivalence** - labels would be `var_lib_t`, not `user_home_dir_t`/container home contexts (see Pitfall 5).
- **Using `su` for become with a `nologin` account.**
- **Putting the reboot test in the container tier.**

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deploy Quadlet files + daemon-reload + restart changed | `deploy_quadlet` helper | `fedora.linux_system_roles.podman` (`podman_quadlet_specs`, `restarts_on`) | D-10 satisfied (see table); handles dependency restarts, per-user env |
| fcontext equivalence `/var/lib/xvpn -> /home` | `command: semanage fcontext -a -e` + grep | `community.general.sefcontext` with `substitute: /home` | Idempotent, check-mode aware, `substitute` is the `equal` functionality [VERIFIED: ansible-doc] |
| Persistent + live sysctl | `lineinfile` + `command: sysctl -w` | `ansible.posix.sysctl` (`sysctl_file`, `reload`, `sysctl_set`) | One module, idempotent |
| Port/service firewall rules | `command: firewall-cmd` | `ansible.posix.firewalld` (`offline` for container tier) | idempotent, check_mode |
| A-record lookup | `dig` + parsing, controller-side `community.general.dig` | `ansible.builtin.getent database=ahostsv4` | Uses the target host's own resolver (what LE sees from the host's perspective is a DNS-zone matter, but the locked decision is the host resolver); no extra package |
| VM provisioning for Molecule | Our own libvirt/cloud-init scripts (initially) | `molecule-plugins[vagrant]` | Official, maintained by ansible-community; own scripts only as spike fallback |
| Collection linting rules | Custom pre-commit scripts | `ansible-lint --profile production` + `.yamllint` | Same output as Galaxy-quality checks |
| Argument validation | `assert` blocks for types | `meta/argument_specs.yml` | Validated automatically at role entry (FND-06) |

**Key insight:** the genuinely custom code in this phase is small: preflight check logic, the user/home/SELinux/sysctl/linger plumbing (no Galaxy module covers it - LSR deliberately requires the user to pre-exist), the Quadlet pre-validation step, and the Molecule verify tasks.

## Common Pitfalls

### Pitfall 1: `meta-runtime[unsupported-version]` on `requires_ansible: ">=2.20.0"`
**What goes wrong:** ansible-lint 26.11.0 reports "'requires_ansible' key must refer to a currently supported version such as: >=2.15.0 ... >=2.19.0" [VERIFIED: scratch collection lint run].
**How to avoid:** `.ansible-lint`: `supported_ansible_also: ["2.20", "2.21", "2.22"]` [VERIFIED: config key in ansiblelint/config.py; lint passes with it].
**Warning signs:** CI red on a fresh scaffold.

### Pitfall 2: Galaxy metadata rules (`galaxy[no-changelog]`, `galaxy[tags]`)
**What goes wrong:** production profile needs a changelog and at least one tag from a fixed list [VERIFIED: lint output lists allowed tags: application, cloud, database, eda, infrastructure, linux, monitoring, networking, security, storage, tools, windows].
**How to avoid:** `tags: [linux, infrastructure, security]` in `galaxy.yml`; `changelogs/changelog.yaml` (`ancestor: null`, `releases: {}`) [VERIFIED: made the rule pass]. Exclude `.github`, `molecule`/`extensions` from the build via `build_ignore` if you do not want them in the tarball (decide; `extensions/molecule` is conventionally kept).

### Pitfall 3: `var-naming[no-role-prefix]` vs the locked `xvpn_<role>_*` names
**What goes wrong:** the rule requires variables defined inside role `preflight` to start with `preflight_`; `xvpn_preflight_dns_check` (D-04, user-facing name) fails [VERIFIED: 5 failures on scratch collection; rule source `var_naming.py` requires `startswith(f"{prefix.value}_")` where prefix = role dir name].
**How to avoid:** keep the locked names and add `skip_list: [var-naming[no-role-prefix]]` to `.ansible-lint` [VERIFIED: scratch collection then passes `production`]. Do not rename user-facing variables. (Alternative `xvpn_`-prefixed role directory names were rejected as ugly and as changing FQCNs.) Document the exception in `.ansible-lint` with a comment.

### Pitfall 4: LSR re-pulls images every run
See Pattern 3 (b). Set `podman_pull_image: false` globally in the wrapper; add an idempotency assertion in the VM tier (second converge `changed=0`).

### Pitfall 5: Non-standard home and SELinux labels (D-08)
**What goes wrong:** `/var/lib/xvpn/rw-edge` gets `var_lib_t`-family labels by default; `user@.service`/Podman expect home-type labels. container-selinux's file contexts are written against `HOME_DIR`, e.g. `HOME_DIR/\.local/share/containers/storage/overlay(/.*)? gen_context(system_u:object_r:container_ro_file_t,s0)` and `HOME_DIR/\.local/share/containers/storage/volumes/[^/]*/.* gen_context(system_u:object_r:container_file_t,s0)` [VERIFIED: container-selinux/container.fc `main`; no `.config/containers` rule exists there].
**Why equivalence works:** `semanage fcontext -a -e /home /var/lib/xvpn` makes the subtree take `/home` labels (including `HOME_DIR` expansions) [CITED: semanage-fcontext(8)]. The source MUST be exactly `/home` (a custom-path equivalence has no effect) [CITED: Red Hat KB 7044073 via search].
**How to avoid:** (1) create parent dir, (2) `sefcontext` substitute, (3) `restorecon -R /var/lib/xvpn`, (4) then create users. Verify in VM tier: `matchpathcon /var/lib/xvpn/rw-edge` and `ls -Zd` show `user_home_dir_t`; `ls -Z ~/.config/containers/systemd` shows `config_home_t`/`user_home_t` family [ASSUMED expected values - assert only "not var_lib_t / not default_t"]; zero AVC after converge + reboot is the actual acceptance. Fallback if AVCs appear: keep home in `/home/<user>` (D-08 is `Reversibility: costly`, so decide in Plan 1 spike BEFORE any other phase builds on it).

### Pitfall 6: User manager race after `enable-linger`
**What goes wrong:** `systemctl --user` fails with "Failed to connect to bus"/"No medium found" immediately after linger is enabled (PITFALLS #5).
**How to avoid:** Pattern 2 steps 5-7; also never rely on `DBUS_SESSION_BUS_ADDRESS` - `XDG_RUNTIME_DIR` is enough for `systemctl --user` [CITED: ansible-doc systemd example]. Bus-dependent commands (`machinectl`) are not used.

### Pitfall 7: Boot ordering - the `user@.service` drop-in is (mostly) not needed
**What goes wrong (feared):** rootless units start before network is up after reboot.
**Finding:** Quadlet user units get `After=podman-user-wait-network-online.service` instead of `network-online.target` (user managers cannot see system targets) [CITED: podman-systemd.unit(5); Podman 5.3 change per Podman blog]. The helper unit is shipped in `/usr/lib/systemd/user/` in the EL10 RPMs for both 5.4.0 and 6.1.4 [VERIFIED: RPM contents] and is `Type=oneshot`, `TimeoutStartSec=90s`, `ExecStart=/bin/sh -c 'until systemctl is-active network-online.target; do sleep 0.5; done'`, `RemainAfterExit=yes` [VERIFIED: extracted unit text from podman-5.4.0-13.el10_0 RPM].
**Residual risks:** (a) if `network-online.target` never becomes active (NetworkManager-wait-online disabled) the unit times out after 90 s and the Quadlet start is delayed/fails - add a VM-tier assertion `systemctl is-active network-online.target` and a `Restart=always`/`RestartSec=` on every Quadlet service (PITFALLS #7); (b) a `user@.service` drop-in is only warranted later for `LimitNOFILE` (PITFALLS) - **not in Phase 1**. Planner: do not create a `user@.service.d` drop-in in Phase 1.

### Pitfall 8: Podman 5.x vs 6.x differences that matter for this phase
| Topic | Podman 5.4 - 5.8 (EL10.0-10.2) | Podman 6.1 (EL10.3) | Impact |
|---|---|---|---|
| Versions per minor | 10.0: 5.4.0, 10.1: 5.6.0, 10.2: 5.8.2 [VERIFIED: Rocky vault AppStream package listings] | 10.3: 6.1.4 (6.1.0, 6.1.1 also present) [VERIFIED: Rocky `pub/rocky/10` listing] | Preflight floor `>=5.4` passes on all EL10 minors |
| Generator / unit dirs | `~/.config/containers/systemd/` etc. | same; adds `/usr/share/containers/systemd/users` and `/usr/share/containers/systemd/users/${UID}` [CITED: Podman v6.0.0 release notes] | Our file-copy approach is identical |
| `podman quadlet` CLI | exists from 5.6 | reworked: files go in subdirectories, no `.app` tracking [CITED: v6.0.0 notes] | We do not use it (LSR copies files) |
| `.volume` keys | no `UID=/GID=/Options=` | added [CITED] | Do not use in shared templates |
| Removed in 6 | - | cgroups v1, iptables, CNI, slirp4netns, BoltDB [CITED] | EL10 already cgroups v2/nftables/netavark/pasta; `Network=pasta` fine on both |
| Network isolation default | - | on [CITED] | Irrelevant for Phase 1 fixture |
| Rootless port forwarder | rootlessport default | default still `rootlessport`; `pasta` forwarder experimental [CITED: v6.0.0 notes] | Use explicit `Network=pasta` + `PublishPort=` in fixture to mirror Phase 2 |
| `podman-user-wait-network-online.service` | present in 5.4.0 RPM | present in 6.1.4 RPM [VERIFIED] | same ordering behaviour |
**Matrix consequence:** by default both VM legs will install Podman 6.1.x (repos resolve `$releasever` = 10 -> latest). Podman 5.x legs require pinning vault repos (see Open Questions Q3).

### Pitfall 9: AVCs hidden by `dontaudit` and boot-time races in the AVC check
**How to avoid:** In VM `prepare.yml` run `semodule -DB` (disable dontaudit) and ensure `auditd` is running/ `audit` package installed; record a timestamp before converge in the format `ausearch -ts` expects; assert `ausearch -m avc,user_avc,selinux_err,user_selinux_err -ts <marker>` returns rc 1 (`<no matches>`) after converge AND after reboot. Always print the matches (`audit2why`) on failure. [ASSUMED: practitioner approach; `ausearch` exit code 1 = no match - confirm in VM]. Never "fix" with a boolean until an AVC proves the need (STACK/PITFALLS).

### Pitfall 10: Rocky 10 / RHEL 10 need x86-64-v3 CPUs
**What goes wrong:** a VM with a baseline `qemu64`/TCG CPU model cannot run Rocky 10 (v3 required; AlmaLinux 10 also ships a v2 build) [CITED: Red Hat RHEL 10 deprecation notice, Rocky 10 release notes via search results; the `qemu64` consequence itself is unverified].
**How to avoid:** libvirt `cpu_mode: host-passthrough` (needs KVM) via `provider_options`; a no-KVM TCG fallback needs `cpu_mode: custom` with a v3-capable model (e.g. `Haswell`/`max`) [ASSUMED]. `community.vagrant.vagrant` has a `no_kvm` path that forces `libvirt.driver='qemu'` and sets a CPU model [VERIFIED: vagrant.py template lines ~330-345] - treat TCG as emergency only (very slow).

### Pitfall 11: GitHub-hosted runner KVM is documented outside the official runner reference
Staff stated "All Linux runners are now on a SKU that supports nested virtualization" (2024-04-05, Discussion #7191) and the 2024-04-02 changelog gives the udev rule `KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"`; the official runner reference page says nothing about KVM; private repos have 2 vCPU/8 GB vs public 4 vCPU/16 GB [CITED: github.com/actions/runner-images discussion #7191; github.blog changelog 2024-04-02; docs.github.com runners reference]. One report in the thread says the first udev rule attempt failed "No such file or directory" - i.e. availability varies. **Mitigation:** first step of the VM job: apply udev rule, `sudo udevadm control --reload-rules && sudo udevadm trigger --name-match=kvm`, `test -c /dev/kvm || { echo 'KVM unavailable'; exit 1; }`; keep the VM job non-required for merge until it has N consecutive green runs; document the local one-command path.

### Pitfall 12: `ansible-lint`/Molecule install side-effects
`ansible-lint` logs "Another version of 'xvpn.remnawave' ... only the first one will be used" when a copy exists under `~/.ansible/collections` [VERIFIED: scratch run]. In CI start from a clean runner (no stale copy); locally run lint from the collection root with `ANSIBLE_COLLECTIONS_PATH` pointing at a path where the repo itself sits as `ansible_collections/xvpn/remnawave`, or use the `extensions/molecule` collection-mode discovery.

### Pitfall 13: Become to unprivileged users needs pipelining or ACL
When connecting as a non-root sudo user and `become_user: rw-edge`, Ansible needs `setfacl` (package `acl`) or pipelining to hand temp files to the unprivileged user [ASSUMED - standard Ansible behaviour, not re-tested]. Mitigation: `ansible.cfg` `pipelining = True` (examples/CI) and `acl` in `common` packages.

## Code Examples

### `.ansible-lint`, `.yamllint` (verified green on the scratch collection)
```yaml
# .ansible-lint
---
profile: production
supported_ansible_also: ["2.20", "2.21", "2.22"]
skip_list:
  - var-naming[no-role-prefix]   # project convention is xvpn_<role>_* (D-04, ARCHITECTURE)
exclude_paths:
  - .github/
```
```yaml
# .yamllint
---
extends: default
rules:
  line-length: {max: 160, level: warning}
  truthy: {allowed-values: ["true", "false"], check-keys: false}
  comments: {min-spaces-from-content: 1}
  comments-indentation: false
  braces: {max-spaces-inside: 1}
  octal-values: {forbid-implicit-octal: true, forbid-explicit-octal: true}
```
(`yamllint -s .` printed nothing = pass on the scratch tree.)

### `galaxy.yml` (essentials that satisfied `production` + `ansible-galaxy collection build`)
```yaml
---
namespace: xvpn
name: remnawave
version: 0.1.0
readme: README.md
authors: ["..."]
description: Remnawave Panel and Node on Rocky/Alma Linux 10 (rootless Podman, Quadlet, SELinux enforcing)
license: [GPL-3.0-or-later]
repository: https://github.com/<org>/xvpn.remnawave
tags: [linux, infrastructure, security]
dependencies:
  fedora.linux_system_roles: ">=2.5.0"
  ansible.posix: ">=2.2.2"
  community.general: ">=14.0.1"
  containers.podman: ">=1.21.2"
build_ignore: [.github, ".venv"]
```
`meta/runtime.yml`: `requires_ansible: ">=2.20.0"`. [VERIFIED: `ansible-galaxy collection build` produced `xvpn-remnawave-0.1.0.tar.gz` with a similar file.] The license value is the maintainer's call (GPL-3.0-or-later was used only in the scratch test).

### `meta/argument_specs.yml` skeleton (accepted by lint and by Ansible core validation)
```yaml
---
argument_specs:
  main:
    short_description: Read-only host checks
    options:
      xvpn_preflight_domains:
        description: Domains whose A records must resolve to this host.
        type: list
        elements: str
        default: []
      xvpn_preflight_dns_check:
        description: Enable the DNS check (D-04).
        type: bool
        default: true
```
Cross-role inputs (`xvpn_public_interface`, `xvpn_public_ip`) must appear in each role's spec that reads them.

### Fixture Quadlet (Molecule only; mirrors Phase 2 networking)
```ini
# extensions/molecule/shared/templates/xvpn-fixture.container.j2
[Unit]
Description=xvpn molecule fixture (nginx-unprivileged on host :80)

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
Tag `1.31-alpine` exists (updated 2026-10-19) [VERIFIED: Docker Hub tags API]. `wget` in the alpine image and `Network=pasta` + `PublishPort` combination are [ASSUMED] until the VM spike.

### LSR call (inside `podman_rootless/tasks/quadlet.yml`)
```yaml
- name: Deploy Quadlet specs for one service user
  ansible.builtin.include_role:
    name: fedora.linux_system_roles.podman
  vars:
    podman_pull_image: false
    podman_run_as_user: "{{ xvpn_user }}"
    podman_activate_systemd_unit: "{{ xvpn_podman_rootless_activate | default(true) }}"
    podman_quadlet_specs:
      - template_src: "{{ xvpn_quadlet_template_dir }}/xvpn-fixture.container.j2"
        run_as_user: "{{ xvpn_user }}"
```
(`template_src`, `run_as_user`, `activate_systemd_unit`, `state` are the spec-level keys stripped before the unit is rendered [VERIFIED: `__del_params` regex].)

### Molecule VM scenario (config shape verified via `molecule list`)
```yaml
# extensions/molecule/vm/molecule.yml
---
driver:
  name: vagrant
  provider:
    name: libvirt
platforms:
  - name: alma10
    box: almalinux/10
    memory: 4096
    cpus: 2
    provider_options: {cpu_mode: host-passthrough}   # [ASSUMED key name; vagrant-libvirt option]
  - name: rocky10
    box: rocky10-libvirt
    box_url: https://dl.rockylinux.org/pub/rocky/10/images/x86_64/Rocky-10-Vagrant-Libvirt.latest.x86_64.vagrant.libvirt.box
    memory: 4096
    cpus: 2
    provider_options: {cpu_mode: host-passthrough}
```

### Verify tasks (shared by tiers; VM-only where noted)
```yaml
- name: Fixture is active as the service user
  ansible.builtin.systemd:
    name: xvpn-fixture.service
    scope: user
  become: true
  become_user: rw-edge
  environment: {XDG_RUNTIME_DIR: "/run/user/{{ uid }}"}
  register: st
  failed_when: st.status.ActiveState != 'active'

- name: Answers on :80 from the controller (VM tier)
  ansible.builtin.uri: {url: "http://{{ ansible_host }}:80/", status_code: 200}
  delegate_to: localhost
  become: false

- name: Internal ports are not open in the external zone
  ansible.builtin.command: firewall-cmd --zone={{ zone }} --list-all
  register: fw
  changed_when: false
  failed_when: fw.stdout is search('\\b(3000|3010|8443|2222)/tcp')

- name: Zero AVC since marker
  ansible.builtin.command: ausearch -m avc,user_avc,selinux_err,user_selinux_err -ts {{ avc_marker }}
  register: avc
  changed_when: false
  failed_when: avc.rc != 1          # rc 1 == "<no matches>"  [ASSUMED]
```

### GitHub Actions VM job skeleton (to be validated by the spike)
```yaml
jobs:
  vm:
    runs-on: ubuntu-24.04          # public repo: 4 vCPU / 16 GB
    strategy: {fail-fast: false, matrix: {platform: [alma10, rocky10]}}
    steps:
      - uses: actions/checkout@v5
      - name: Enable KVM for the runner user
        run: |
          echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules
          sudo udevadm control --reload-rules && sudo udevadm trigger --name-match=kvm
          test -c /dev/kvm
      - name: Install libvirt + Vagrant + plugin
        run: |   # exact package list is a spike deliverable
          sudo apt-get update && sudo apt-get install -y qemu-system-x86 libvirt-daemon-system libvirt-dev ruby-dev build-essential vagrant ...
          vagrant plugin install vagrant-libvirt
      - run: pip install -r requirements-dev.txt && ansible-galaxy collection install -r requirements.yml
      - run: molecule test -s vm --platform-name ${{ matrix.platform }}
```
The `actions/checkout@v5` version and the apt package list are [ASSUMED]; no complete working recipe for Vagrant + libvirt on `ubuntu-24.04` hosted runners was found in search (only partial examples) - this is the central spike.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `network-online.target` ordering for user units (ineffective) | `podman-user-wait-network-online.service` auto-added by Quadlet | Podman 5.3 | No `user@.service` drop-in needed |
| Molecule scenarios under `molecule/` + `provisioner:` | `extensions/molecule/` collection mode + `ansible:` key | Molecule 25/26 | Use collection mode |
| Standalone `molecule-podman`/`molecule-vagrant` | `molecule-plugins[podman,vagrant]` | 2023 | Do not install old standalone packages (duplicate entry points) |
| CNI / slirp4netns / iptables | netavark / pasta / nftables | Podman 6 (already default on EL10) | Nothing to configure |
| GH hosted runners without KVM | Linux hosted runners with `/dev/kvm` (udev rule) | 2024-04 | VM tier on hosted runners is feasible, needs a gate |
| `ansible-lint` supported-versions list (2.15-2.19) | needs `supported_ansible_also` for 2.20+ | ansible-lint 26.11.0 lags core | Configure it |

**Deprecated/outdated:** `molecule-vagrant` 2.0.0 (2023-01) standalone; `vagrant-libvirt` 0.12.2 (2023-06, no commits since 2023-12) is the weak link of the VM tier but still the only plugin behind the official driver.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `useradd` on EL10 auto-allocates subuid/subgid for regular users (hence guard with `getsubids` + `usermod --add-subuids` fallback) | Pattern 2 | Low: fallback covers it |
| A2 | `systemctl start user@UID.service` returns only after the user manager is up; `/run/user/UID/systemd/private` is the right readiness path | Pattern 2 / Pitfall 6 | Medium: could still race; add retries on a `systemctl --user is-system-running` probe |
| A3 | `become_method: sudo` works with `nologin` accounts and `su` does not | Pattern 2 | Low-Medium: affects all rootless tasks; proven in first VM converge |
| A4 | Relative `template_src` resolves in LSR's context, so absolute paths are required | Pattern 3 | Low: absolute path is harmless either way |
| A5 | `podman-system-generator --user --dryrun` exits non-zero on a bad unit | Pattern 3 | Medium: add stderr assertion + negative test |
| A6 | `/var/lib/xvpn` + `-e /home` equivalence yields zero AVCs for rootless Podman under `unconfined_t` user managers | Pitfall 5 | High (D-08 costly): decide in Plan-1 spike; fallback `/home` |
| A7 | `Network=pasta` + `PublishPort=80:8080` works as rootless on both Podman 5.8 and 6.1 under SELinux without extra booleans | Fixture | Medium: AVC-proven in VM; fix only with evidence |
| A8 | `nginx-unprivileged:*-alpine` has busybox `wget` for `HealthCmd` | Fixture | Low |
| A9 | `ausearch` rc 1 means no matches; `semodule -DB` surfaces dontaudit-hidden denials | Pitfall 9 | Low |
| A10 | libvirt `cpu_mode: host-passthrough` key is accepted via `provider_options`; qemu64 CPU cannot boot Rocky 10 | Pitfall 10 | Low-Medium |
| A11 | vagrant-libvirt 0.12.2 works with Vagrant 2.4.9 / distro Vagrant on `ubuntu-24.04` runner | VM tier | High for the tier: this is the spike; fallback delegated driver |
| A12 | LSR `firewall`/`selinux` roles have whole-state semantics that conflict with D-13 | Alternatives | Low: we use modules anyway |
| A13 | AAAA records: HTTP-01 prefers IPv6 but falls back to IPv4 (so AAAA mismatch = warn, not fail) | Preflight | Low: discretion area; Let's Encrypt docs page fetched says nothing on IPv6 |
| A14 | Standard `ubuntu-24.04` runners keep `/dev/kvm` available across image updates | Pitfall 11 | Medium: gate job |
| A15 | Pinning Podman 5.x/5.4 floor in a VM by pointing dnf at `vault.rockylinux.org/10.0|10.2` repos installs cleanly on a 10.3 box | Open Questions | Medium |
| A16 | `ansible-core 2.22` as controller works with LSR 2.5.0 and Molecule 26.11.0 (devcontainer has 2.22.0, CI target primary is 2.21) | Stack | Low: CI matrix (QA-06 is Phase 5) |

## Open Questions (RESOLVED)

1. **Does Vagrant + vagrant-libvirt run reliably on `ubuntu-24.04` hosted runners?**
   - Known: KVM is claimed available (staff statement 2024-04, changelog udev rule); both boxes exist; the molecule driver and platform keys are valid. Not known: a working recipe (apt `vagrant` 2.3.x + distro `vagrant-libvirt` vs HashiCorp 2.4.9 + gem build), boot time, `box_url` download time (~hundreds of MB).
   - Recommendation: a spike in CI. If it fails twice with distinct root causes, switch to the **fallback**: `driver: default` (delegated) with `create.yml`/`destroy.yml` using `virt-install --import` of versioned AlmaLinux/Rocky GenericCloud qcow2 images + a cloud-init seed ISO; checksums from the published `CHECKSUM` files [VERIFIED: both directory listings].
   - **RESOLVED:** Plan 12 Task 2 is the spike with pre-decided decision rules: (1) no `/dev/kvm` twice -> VM tier local-only per D-16 with a human-action checkpoint for local evidence; (2) Vagrant/vagrant-libvirt fails twice with distinct causes -> delegated GenericCloud fallback with versioned, sha256-verified images. Package sources (gem, HashiCorp apt) are approved at the Plan 09 legitimacy checkpoint.
2. **Does the `/var/lib/xvpn` home cause AVCs?** Unknown until an enforcing VM run. The original recommendation was a comparative spike of `/var/lib/xvpn` + equivalence versus `/home`.
   - **RESOLVED:** the `/home` variant is NOT evaluated as a separate leg. D-08 (`/var/lib/xvpn/<user>`) is a locked user decision; the VM tier (Plans 11-12) is the decision criterion: zero AVC (dontaudit disabled, before and after reboot) plus the `user_home_dir_t` label assertion proves D-08. Any AVC naming `/var/lib/xvpn` stops execution with a `checkpoint:decision` offering (a) keep `/var/lib/xvpn` + the specific file-context rule the denial proves, or (b) move homes to `/home/<user>` (changes D-08). No plan overrides `xvpn_podman_rootless_home_root`.
3. **Podman 5.x coverage.** Both default VM legs get 6.1.x. Cheap option: an optional nightly leg with dnf repo overrides pointing at `https://dl.rockylinux.org/vault/rocky/10.2/{BaseOS,AppStream}/x86_64/os/` (Podman 5.8.2 [VERIFIED listing]) or `.../10.0/...` (Podman 5.4.0, the exact floor [VERIFIED listing]). Needs confirmation that dependency resolution works on a 10.3 base.
   - **RESOLVED (accepted risk):** no Podman 5.x VM leg in Phase 1. The 5.4 floor is enforced only by the preflight version check (Plan 06, exercised in Plan 08 by narrowing the floor). Risk accepted: a Quadlet key or LSR behaviour that differs on Podman 5.4-5.8 is not caught by CI. Recorded as a FLAGGED ASSUMPTION in Plan 11; revisit with the CI matrix work (QA-06, Phase 5).
4. **Does LSR's role-level work stay `changed=0` on the second run with empty `podman_containers_conf` etc.?** Source suggests yes.
   - **RESOLVED:** proven by the idempotence steps of the container tier (Plan 10) and VM tier (Plan 12); a non-zero change is a genuine defect fixed at the source under the Plan 10/12 fix rules, never by disabling idempotence.
5. **Is `network-online.target` active on the Vagrant/GenericCloud images at boot?**
   - **RESOLVED:** asserted by `verify_runtime.yml` (Plan 11) before and after reboot; the post-reboot wait uses 60 x 10 s retries, which covers the up-to-90 s `podman-user-wait-network-online` helper.
6. **AAAA handling** in preflight (warn vs fail) - discretion item.
   - **RESOLVED:** warn only (A13); A-record mismatch fails hard (D-04). Implemented in Plan 06 `check_dns.yml`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| ansible-core | all | yes (devcontainer) | 2.22.0 | venv with `ansible-core>=2.21,<2.22` |
| Python 3 | Molecule | yes | 3.14 (devcontainer); 3.12 system on GH runner | - |
| Network (Galaxy, PyPI, mirrors) | research/installs | yes | - | - |
| podman | container tier (local) | **no** in devcontainer | - | CI only; or run on a workstation with Podman |
| `/dev/kvm`, libvirt, vagrant | VM tier (local) | **no** in devcontainer | - | CI hosted runner (spike) or a KVM-capable workstation (D-16: document) |
| gh CLI | repo/CI ops | yes | - | - |
| GitHub-hosted `ubuntu-24.04` | CI | n/a here | image 20261116.376.1: Podman 4.9.3, Python 3.12.3, Ansible 2.21.6, Docker 28.0.4; Vagrant/libvirt/QEMU/virt-install NOT preinstalled [VERIFIED: runner-images readme] | install via apt in job |
| Rocky/Alma mirrors, Vagrant Cloud | VM images | yes (probed) | Alma box 10.2.20260914; Rocky libvirt box 10.3 (2026-11-13) | GenericCloud qcow2 |

**Missing dependencies with no fallback:** none for planning. **Consequence:** neither Molecule tier can be executed inside the current devcontainer; the first runnable verification of any Phase-1 plan is on a CI runner or an external KVM host. Plans must therefore keep local checks to `ansible-lint`, `yamllint`, `ansible-playbook --syntax-check`, `ansible-galaxy collection build`, and template rendering unit checks.

## Validation Architecture

> `.planning/config.json` has `workflow.nyquist_validation: false`, but the orchestrator explicitly requested this section, so it is included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Molecule 26.11.0 (drivers `podman`, `vagrant`) + `ansible.builtin.assert` verifiers; ansible-lint 26.11.0; yamllint 1.38.0 |
| Config file | `extensions/molecule/{container,vm}/molecule.yml`, `.ansible-lint`, `.yamllint` (Wave 0) |
| Quick run command | `ansible-lint && yamllint -s . && ansible-galaxy collection build --force` (seconds; works in devcontainer) |
| Container tier | `molecule test -s container` (needs Podman; per-push in CI) |
| VM tier | `molecule test -s vm` (needs KVM + Vagrant/libvirt; PR to main + nightly; locally one command) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FND-01 | Preflight fails with clear message on: non-EL10 (fact override), non-enforcing (VM: `setenforce 0` in a dedicated negative scenario or mocked command), Podman < 5.4 (mocked version), occupied 80/443 by a foreign process (container: `python -m http.server` as root), and passes when `rw-edge` holds 80 | container + vm negative cases | `molecule test -s container` (negative `converge` with `ignore_errors` + assert message + assert "nothing changed") | Wave 0 |
| FND-01 / success crit. 1 | "Nothing changed" after preflight failure: no user `rw-edge`, no `/etc/sysctl.d/99-xvpn*`, no linger file, no podman package state change, `/var/lib/xvpn` absent | container | same scenario, verify asserts absence | Wave 0 |
| FND-07 | A-record mismatch fails; `xvpn_preflight_dns_check: false` skips; `/etc/hosts` entry used as the resolver stand-in in container tier | container | molecule container | Wave 0 |
| FND-02 | user exists uid>=1000, nologin, home `/var/lib/xvpn/rw-edge`, subuid/subgid, linger file, `systemctl --user` works via become | vm (container partial: user/subid/home) | `molecule test -s vm` | Wave 0 |
| FND-03 | sysctl file + live value 80; fixture answers on :80 as non-root | vm (+ container for file/live value in privileged container) | molecule vm | Wave 0 |
| FND-04 | Rendered unit passes dry-run; deliberately broken unit fails the validation step; unit active after converge, `changed=0` on rerun, active after reboot | container (dry-run + negative) + vm (runtime/reboot) | molecule | Wave 0 |
| FND-05 | firewalld opens only own port in external-iface zone; 3000/3010/8443/2222 not open; ssh still allowed; `getenforce` Enforcing; zero AVC since marker (after converge and after reboot) | vm | molecule vm verify | Wave 0 |
| FND-06 | `ansible-galaxy collection build` succeeds; every role has `meta/argument_specs.yml`; role entry rejects bad types | quick | `ansible-galaxy collection build --force`; a test asserting `argument_specs.yml` exists per role | Wave 0 |
| QA-01 | ansible-lint production + yamllint pass | quick | `ansible-lint && yamllint -s .` | Wave 0 |
| QA-02 | container tier green (syntax, converge, idempotence) | container | `molecule test -s container` | Wave 0 |
| QA-03 | vm tier green on Alma + Rocky: converge, idempotence, reboot, AVC=0 | vm | `molecule test -s vm` (matrix alma10, rocky10) | Wave 0 |

### Sampling Rate
- **Per task commit:** quick run (lint + yamllint + `collection build` + `--syntax-check`).
- **Per wave merge / every push:** container tier.
- **Phase gate (PR to main) + nightly:** VM tier on both distros; green before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `.ansible-lint`, `.yamllint`, `ansible.cfg`, `galaxy.yml`, `meta/runtime.yml`, `changelogs/changelog.yaml`, `requirements*.{yml,txt}`
- [ ] `extensions/molecule/container/*` and `extensions/molecule/vm/*` skeletons + shared verify tasks and the fixture template
- [ ] `.github/workflows/{lint,molecule-container,molecule-vm}.yml`
- [ ] VM spike (Open Question 1) and home-path spike (Open Question 2)
- [ ] Framework install: see Installation block

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high`.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (Phase 2 owns Panel auth) | - |
| V3 Session Management | no | - |
| V4 Access Control | yes | Dedicated non-login service users (`nologin`, locked password, home mode 0700), per-trust-domain users (D-07), firewalld only exposes own ports, `become_user` instead of shared accounts |
| V5 Input Validation | yes | `meta/argument_specs.yml` types; validate domain names/user names with regex in specs or asserts before they reach shell commands (`ss`, `getent`, `loginctl`, `usermod`); always pass user-controlled values through `| quote` or as module params |
| V6 Cryptography | no (no secrets/crypto in this phase; none generated) | - |
| V14 Configuration | yes | SELinux enforcing asserted (never permissive); no `SecurityLabelDisable`, no `--privileged` containers; pinned image tag; sysctl relaxation documented |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Host-wide `ip_unprivileged_port_start=80` lets any local unprivileged process bind 80-1023 (port hijack when the service is down) | Spoofing / EoP | Document as a conscious host-wide trade-off (PITFALLS #4); no other untrusted local users assumed; keep value as low as needed (80, not 0); verify in README later |
| Command injection via inventory-controlled names into `command:`/`shell:` tasks | Tampering | Strict regex validation in argument specs; use `argv`/`| quote`; avoid `shell:` |
| Service user with login shell/password | EoP | `nologin`, `password_lock: true`; asserted in verify |
| Silent label drift/relabel of broad directories | Tampering | Equivalence only on `/var/lib/xvpn`; never `:Z` on broad paths; `restorecon` limited to that tree |
| Secrets in logs | Info disclosure | Phase 1 has no secrets; keep `podman_secure_logging` default (true), `no_log` on any registry credentials later |
| Third-party role supply chain (LSR, Galaxy collections) | Tampering | Pin collection versions in `requirements.yml`; LSR is Red Hat-maintained (`linux-system-roles`) |
| Container image drift | Tampering | Pinned tag in fixture; `podman_pull_image: false`; no `latest` |
| Public-repo CI with `MODE=0666` on `/dev/kvm` | EoP (runner-local) | Ephemeral hosted runner; acceptable, do not copy to self-hosted runners |

## Sources

### Primary (HIGH confidence) - verified this session
- Downloaded and read `fedora.linux_system_roles` 2.5.0 (Galaxy artifact): `roles/podman/tasks/{main,set_vars,handle_quadlet_spec,create_update_quadlet_spec,manage_linger,handle_user_group,handle_images,flush_one_pending_restart}.yml`, `defaults/main.yml`, `vars/{Rocky,AlmaLinux,RedHat}_10.yml`, `meta/runtime.yml`, `MANIFEST.json`, `plugins/modules/sr_fingerprint.py`
- `podman-5.4.0-13.el10_0` and `podman-6.1.4-1.el10_3` RPMs (dl.rockylinux.org): file lists and `podman-user-wait-network-online.service` text
- Rocky vault/pub and Alma mirror package listings (podman 5.4.0 / 5.6.0 / 5.8.2 / 6.1.x; passt-selinux present on 10.3)
- `pip install molecule==26.11.0 molecule-plugins[podman,vagrant]==26.11.0 ansible-lint==26.11.0 yamllint ansible-core 2.21`; `molecule list` on a scratch collection; scratch `ansible-lint --profile production`, `yamllint -s`, `ansible-galaxy collection build`
- `ansible-doc` for `ansible.builtin.systemd`, `ansible.builtin.user`, `ansible.builtin.getent`, `community.general.sefcontext`, `ansible.posix.firewalld`, `ansible.posix.sysctl`; `community.vagrant` 1.0.1 module source
- Docker Hub tags API (rockylinux/rockylinux `10-ubi-init`, almalinux/10-init, nginxinc/nginx-unprivileged `1.31-alpine`), Vagrant Cloud API (almalinux/10, rockylinux/10), Rocky `Vagrant-Libvirt` box URL (HTTP 200)
- GitHub runner-images Ubuntu 24.04 readme (image 20261116.376.1)
- container-selinux `container.fc` (raw GitHub `main`)

### Secondary (MEDIUM confidence) - fetched docs
- https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html (generator dry-run, `QUADLET_UNIT_DIRS`, rootless search paths, network-online behaviour)
- https://github.com/podman-container-tools/podman/releases/tag/v6.0.0 (breaking changes, Quadlet changes)
- https://github.com/linux-system-roles/podman README (variables, user must pre-exist, subuid check)
- https://github.com/actions/runner-images/discussions/7191 ; https://github.blog/changelog/2024-04-02-github-actions-hardware-accelerated-android-virtualization-now-available/ ; https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://letsencrypt.org/docs/challenge-types/ (HTTP-01 port 80, redirects)
- semanage-fcontext(8) man page and Red Hat KB 7044073 (equivalence rules), Red Hat RHEL 10 x86-64-v3 notices / Rocky 10 release notes / AlmaLinux 10 announcement (via web search)

### Tertiary (LOW confidence)
- Partial community examples for vagrant-libvirt on GitHub Actions (no complete recipe found); `molecule-libvirt-ng` PyPI page; practitioner knowledge for `ausearch`/`semodule -DB`, `become` + nologin behaviour

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions installed/resolved this session; LSR source read.
- Architecture (roles, LSR integration, lint/config): HIGH for verified items; MEDIUM for user-manager readiness and SELinux outcomes (VM-proven only).
- VM tier on hosted runners: MEDIUM-LOW - KVM cited, Vagrant+libvirt recipe unproven, upstream plugin dormant.
- Pitfalls: MEDIUM-HIGH.

**Research date:** 2026-11-23
**Valid until:** 2026-12-23 (stable tooling) / re-check runner image and Podman minor releases earlier if the VM spike is delayed
