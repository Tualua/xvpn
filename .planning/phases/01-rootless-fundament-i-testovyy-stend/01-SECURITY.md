---
phase: "01"
slug: "rootless-fundament-i-testovyy-stend"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-24"
---

# Phase 01 — Security

> Контракт безопасности фазы: реестр угроз, принятые риски и журнал аудита.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| inventory -> target host commands | operator-supplied user names and template paths reach `command:` argv on the target as root | — |
| controller -> Galaxy | collections fetched at install time run as root on targets | — |
| root -> service user | become_user to rw-edge; units run in the service user's namespace | — |
| controller -> Galaxy | pinned collections are downloaded and later run as root on targets | — |
| test fixture -> container host | a test double replaces getenforce and a sudoers drop-in widens secure_path, in disposable Molecule containers only | — |
| controller -> Galaxy | check.sh installs pinned collections | — |
| CI -> lint result | a skipped linter would make CI green without checking | — |
| inventory -> target host commands | user names and template paths reach `command:` argv on the target as root | — |
| Quadlet template -> systemd | a malformed unit could be installed and fail at boot | — |
| operator -> target hosts | the preflight entry points run with become on every inventory host | — |
| inventory -> target commands | domains, ports, interface, user names reach `ss`/`getent` on the target as root | — |
| DNS resolver -> decision | the host resolver's answer decides pass/fail | — |
| internet -> host | firewalld zone of the public interface decides what is reachable | — |
| inventory -> firewalld | operator-supplied port list becomes permanent firewall rules | — |
| inventory -> target commands | domains, ports, interface, IP, user names reach `ss`/`getent` on the target as root | — |
| PyPI / RubyGems / HashiCorp apt -> CI runner | third-party packages execute on the runner with the workflow token | — |
| GitHub Marketplace actions -> CI | third-party action code runs in every job | — |
| repository -> public | local commits become public on push; the history up to 3b54bcc (including `.planning/`) is already public (D-21) | — |
| CI -> product code | pressure to make the first run green could weaken code | — |
| CI -> product code | pressure to make CI green could weaken guards | — |
| image mirrors -> test VM | box images run as test hosts | — |
| SELinux -> test result | hidden denials would make the tier pass falsely | — |
| image mirrors -> CI VM | box/qcow2 images run as test hosts | — |
| Ubuntu archive / HashiCorp apt / RubyGems -> runner | vagrant and its plugin run on the runner | — |
| runner -> /dev/kvm | world-writable KVM device on the ephemeral runner | — |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Tampering | podman_rootless `loginctl`/`getsubids`/`restorecon` commands | high | mitigate | user names asserted against `^[a-z_][a-z0-9_-]{0,30}$` (fail_msg "Invalid service user name") before use; all values passed as `argv` list items; no shell module (acceptance gate). Executed negative test: Plan 04 container verify runs the role with an injected name and asserts the failure and that no user was created | closed |
| T-01-02 | Elevation of Privilege | host-wide `net.ipv4.ip_unprivileged_port_start=80` | medium | accept | conscious, documented trade-off (PITFALLS #4): value 80, not 0; no untrusted local users assumed; README states it (Plan 12) | closed |
| T-01-03 | Elevation of Privilege | service accounts rw-* | medium | mitigate | `/sbin/nologin`, `password_lock: true`, home 0700; asserted by `extensions/molecule/shared/verify_rootless.yml` (Plan 04) | closed |
| T-01-04 | Tampering | SELinux labels of `/var/lib/xvpn` | medium | mitigate | equivalence scoped to `/var/lib/xvpn` only (`substitute: /home`), `restorecon` limited to that tree and only on change; VM tier asserts labels and zero AVC | closed |
| T-01-05 | Tampering | Galaxy collection supply chain | medium | mitigate | galaxy.yml declares minimums only for consumers; exact pins and their recorded justification live in `requirements.yml` (Plan 02); LSR is Red Hat-maintained | closed |
| T-01-06 | Tampering | unit image drift through the quadlet interface | low | mitigate | `podman_pull_image: false` in the LSR call (acceptance gate); exact image tags and no auto-update key are enforced on the fixture in Plan 02 | closed |
| T-01-07 | Tampering | `ss`/`getent` invocations in roles/preflight | high | mitigate | named-message regex/range asserts on domains, ports, interface, IP, user names at role entry; argv-only commands; no shell module (acceptance gate). Executed negative cases for each input class in the Plan 08 scenario | closed |
| T-01-08 | Tampering | preflight mutating a host it rejects | high | mitigate | separate first play with `any_errors_fatal: true` (structural check in Task 2 verify); standalone playbook contains no mutating role (acceptance gate); read-only allow-list and nothing-changed proof in Plan 08 | closed |
| T-01-09 | Information Disclosure | process names/pids in failure messages | low | accept | shown only to the operator running the playbook on their own host; needed for actionable errors | closed |
| T-01-10 | Spoofing | poisoned host resolver making a wrong A record look right | low | accept | the check guards against operator mistakes, not an attacker-resistant control; LE validates DNS independently | closed |
| T-01-11 | Denial of Service | SSH access during firewall changes | high | mitigate | SSH guard (service ssh or ansible_port/tcp) asserted before and after any change; role never changes SSH (D-14). Executed negative case `no-ssh-zone`: removing the guard makes 8088/tcp appear in zone xvpn-nossh and verify fails | closed |
| T-01-12 | Tampering | operator's existing firewalld rules | medium | mitigate | add-only `state: enabled` tasks; acceptance gate forbids removal states and the whole-state LSR firewall role (D-13) | closed |
| T-01-13 | Elevation of Privilege | SELinux mode | high | mitigate | enforcing gate in common (defence in depth after preflight); executed negative case `selinux-permissive`; acceptance gate forbids mode-changing code in roles/ | closed |
| T-01-14 | Information Disclosure | internal service ports (3000/3010/8443/2222) | medium | mitigate | never in defaults; verify_common asserts the public zone's ports equal exactly the declared set, services stay within the declared allow-list, and no forward port or rich rule names an internal port, on both tiers | closed |
| T-01-15 | Tampering | port list injection | low | mitigate | regex + range assert with named message; executed negative case `port-without-protocol`; passed as module parameter, not shell | closed |
| T-01-16 | Tampering | third-party GitHub actions | medium | mitigate | `actions/checkout` and `actions/setup-python` pinned by full commit SHA resolved via `git ls-remote` at implementation time | closed |
| T-01-17 | Elevation of Privilege | workflow GITHUB_TOKEN | medium | mitigate | `permissions: contents: read` on both workflows; no secrets used in Phase 1 | closed |
| T-01-18 | Information Disclosure | public `.planning/` history in Tualua/xvpn (already PUBLIC; origin/main 3b54bcc already contains `.planning/`) | low | accept | risk accepted by the user (D-21, 2026-11-24): the repository stays public. Residual controls: Task 2 verifies origin URL, PUBLIC visibility and gh auth and lists the local commits before Task 3 pushes them; Phase 1 introduces no secrets (workflows use `permissions: contents: read` and no repository secrets, T-01-17) | closed |
| T-01-19 | Tampering | Vagrant boxes | medium | mitigate | versioned box URLs for both distros (no moving symlink) and a sha256 `box_checksum` for both: Rocky from the publisher's CHECKSUM file, Alma from the Vagrant Cloud API provider checksum; if Vagrant Cloud publishes none, a trust-on-first-use sha256 is pinned and the accepted residual risk (first download unverified against a publisher value) is recorded in SUMMARY — ОТКЛОНЕНИЕ: alma10 в catalog mode (box_version 10.2.20260914, sha256 только из каталога); риск принят, см. AR-01 | closed |
| T-01-20 | Tampering | vagrant / vagrant-libvirt installation | medium | mitigate | Ubuntu archive packages first; otherwise HashiCorp's signed apt repo and the exact gem version 0.12.2 — both human-approved at the Plan 09 legitimacy checkpoint — остаточный риск WR-08 принят, см. AR-02 | closed |
| T-01-21 | Elevation of Privilege | `/dev/kvm` MODE=0666 udev rule | low | accept | only on ephemeral GitHub-hosted runners; README warns against copying it to self-hosted runners | closed |
| T-01-22 | Repudiation | SELinux denials hidden by dontaudit | high | mitigate | `semodule -DB` in prepare with a seinfo positive control and a Dontaudit == 0 assertion before the marker; the same assertion (without re-disabling) immediately before every ausearch; binary policy sha256 unchanged across the reboot; AVC assertion before and after reboot (acceptance gate forbids ignore_errors), escalation instead of auto-fix; executed by the VM runs in Plan 12 | closed |
| T-01-23 | Repudiation | yamllint step in `scripts/check.sh` | medium | mitigate | missing yamllint with `CI` set exits 1 (executed negative check in Task 1 verify); Plan 09 lint.yml also asserts `command -v yamllint` | closed |
| T-01-24 | Denial of Service | malformed Quadlet unit reaching the user manager | medium | mitigate | generator dry-run before LSR; executed negative case `broken-unit` asserts no unit file is installed | closed |
| T-01-25 | Tampering | guards weakened to obtain green CI | medium | mitigate | prohibition QA-02; only workflow/harness fixes pre-authorized; anything weakening goes through `checkpoint:decision`; an exhausted repair budget becomes the conditional Task 4 `checkpoint:decision` with log excerpts instead of improvised changes; every fix listed in SUMMARY with its log line | closed |
| T-01-26 | Elevation of Privilege | test-only getenforce double and sudoers drop-in | low | accept | live only in `extensions/molecule/*/prepare.yml` of disposable containers that Molecule destroys at both ends of the test sequence; acceptance gate: no `xvpn-test-path` under `roles/` or `playbooks/`; never applied to the VM tier (Plan 11 gate forbids the double and the drop-in in `extensions/molecule/vm/prepare.yml`), so the bare `getenforce` in the shared `verify_common.yml` (Plan 07) resolves to the real binary there, and `verify_runtime.yml` (Plan 11) additionally calls `/usr/sbin/getenforce` by absolute path | closed |
| T-01-27 | Tampering | Galaxy pin approval before first install (control for T-01-05, Plan 01) | medium | mitigate | exact pins (acceptance gate forbids ranges), per-collection pin justification recorded in the `requirements.yml` header, version/namespace existence confirmed against the Galaxy API in Task 1, blocking human approval in Task 2 before the first install (Task 3 verify); LSR is Red Hat-maintained | closed |
| T-01-28 | Tampering | fixture image drift (instance of T-01-06, Plan 01) | low | mitigate | exact tag `1.31-alpine`, `podman_pull_image: false` in the quadlet entry point, no auto-update key (acceptance gate) | closed |
| T-01-29 | Tampering | collection install in the quality gate (control for T-01-05, Plan 01) | medium | mitigate | check.sh installs only the exact pins of `requirements.yml`, which a human approved at the Plan 02 Task 2 blocking checkpoint before the first install | closed |
| T-01-30 | Tampering | executed proof of the podman_rootless input asserts (control for T-01-01, Plan 01) | high | mitigate | executed negative cases `bad-user-name` and `relative-template` in container verify; removing either assert makes verify fail (user gets created / LSR runs on a relative path) | closed |
| T-01-31 | Tampering | executed proof of the preflight input asserts (control for T-01-07, Plan 06) | high | mitigate | executed negative cases 13-17 (domain, service user, public IP, interface, port) each assert the named failure; nothing-changed verify after all cases; removing any assert makes its case pass or fail with a different message, failing converge | closed |
| T-01-32 | Tampering | executed proof that preflight never mutates a rejected host (control for T-01-08, Plan 05) | high | mitigate | read-only module allow-list asserted by verify (recursing into block/rescue/always, no ignore_errors); separate first play with any_errors_fatal asserted; nothing-changed verify | closed |
| T-01-33 | Repudiation | yamllint presence in the CI workflow (control for T-01-23, Plan 03) | medium | mitigate | explicit `command -v yamllint` step plus check.sh CI-hard tool gate (Plan 03) | closed |
| T-01-34 | Tampering | guards from Plans 04-08 weakened during the convergence loop (instance of T-01-25, Plan 09) | medium | mitigate | prohibition QA-02; explicit conditional Task 2 `checkpoint:decision` when the repair budget is exhausted; acceptance gate that no `# xvpn_negative_case:` line was removed; every fix listed in SUMMARY with its log line | closed |
| T-01-35 | Tampering | fallback GenericCloud qcow2 images (box integrity is T-01-19, Plan 11) | medium | mitigate | boxes: versioned URLs + sha256 `box_checksum` for both distros (Plan 11); fallback qcow2: versioned file names verified against the publisher's CHECKSUM sha256, create fails on mismatch | closed |
| T-01-36 | Repudiation | CI execution of the dontaudit/AVC checks (design is T-01-22, Plan 11) | high | mitigate | AVC assertion before and after reboot executed on both legs here; a failing seinfo positive control goes to the decision rule 4 checkpoint, never to an edited assertion; escalation instead of auto-fix; git-log gates that no boolean/module was added and verify_runtime.yml was not changed without an answer | closed |
| T-01-SC | Tampering | third-party package installs (Galaxy, PyPI, RubyGems, apt); one phase-wide supply-chain threat, reserved ID kept in every plan with this exact component text | high | mitigate | Phase-wide controls (canonical): Galaxy pins human-approved at Plan 02 Task 2 and PyPI/RubyGems/apt sources at Plan 09 Task 2, both blocking and before the first install of that source. This plan: installs nothing (the verify reuses collections already present under ~/.ansible). — остаточный риск WR-08 принят, см. AR-02 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

Доказательства по каждой угрозе (file:line, CI-прогоны) — в вердикте gsd-security-auditor от 2026-11-24; CI на f63864f: lint 45374652725, molecule-container 45374652801, molecule-vm 45374658629 (alma10, rocky10).

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-01-19 | Бокс alma10 для VM-тира берётся из каталога Vagrant Cloud в catalog mode с закреплённой версией `10.2.20260914`; Vagrant сверяет sha256 из каталога (совпадает с прежним пином `24b3ff7c…`), но sha256 из репозитория не передаётся, поэтому хеш и бокс приходят из одного источника. Прямой `box_url` Vagrant не принимает (01-12). Затрагивает только эфемерный CI-стенд, не коллекцию. rocky10 остаётся на sha256-пине из репозитория. | пользователь (secure-phase 01) | 2026-11-24 |
| AR-02 | T-01-20, T-01-SC | WR-08: в CI ключ `apt.releases.hashicorp.com/gpg` скачивается без сверки отпечатка, gem `vagrant-libvirt` 0.12.2 ставится без хеша, его транзитивные зависимости не запинены. Плановая мера (подписанный apt-репозиторий, точная версия gem, одобрение человеком в 01-09) выполнена. Затрагивает только эфемерный CI-раннер. **Доработка позже:** запинить отпечаток ключа HashiCorp после сверки с официальным источником (и рассмотреть запрет запуска `molecule-vm` для PR из форков). | пользователь (secure-phase 01) | 2026-11-24 |

*Accepted risks do not resurface in future audit runs.*

### Замечания аудитора (не меняют статус)

- Комментарий в `extensions/molecule/vm/molecule.yml:3` («Boxes are versioned and sha256-pinned») для alma10 больше не точен.
- `community.library_inventory_filtering_v1` 1.1.5 (одобрен) не закреплён в `requirements.yml`; транзитивные PyPI-пакеты ставятся без `--require-hashes`.
- IN-03: роль проверяет SSH по `xvpn_common_ssh_port`, а `verify_common.yml:135` по-прежнему берёт `ansible_port` (при значениях по умолчанию совпадают).

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-24 | 37 | 37 | 0 | gsd-security-auditor (36 closed по коду) + принятие T-01-19 пользователем |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-24
