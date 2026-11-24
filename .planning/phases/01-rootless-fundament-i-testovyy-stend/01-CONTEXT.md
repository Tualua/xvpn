# Phase 1: Rootless-фундамент и тестовый стенд - Context

**Gathered:** 2026-11-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Фаза поставляет фундамент, на котором проверяются все следующие фазы:
- роль `preflight` (read-only проверки хоста: ОС, SELinux, Podman, порты 80/443, DNS A-запись);
- роль `common` (базовый firewalld, SELinux-assert, нужные пакеты);
- роль `podman_rootless` (сервисные rootless-пользователи, linger, subuid/subgid, sysctl `ip_unprivileged_port_start`, механизм развёртывания Quadlet);
- Molecule: контейнерный тир (быстрый, каждый push) и VM-тир (SELinux enforcing, reboot, ноль AVC) на AlmaLinux 10 и Rocky 10;
- CI на GitHub Actions: ansible-lint, yamllint, контейнерный тир, VM-тир;
- `galaxy.yml` (`xvpn.remnawave`), `meta/argument_specs.yml` у всех ролей.

Hardening (SSH, fail2ban, dnf-automatic) — Phase 5. LAN-зона firewalld — Phase 4. Traefik/Panel — Phase 2.

</domain>

<decisions>
## Implementation Decisions

### Preflight (FND-01, FND-07)
- **D-01:** Хост может иметь два интерфейса (внешний с публичным IP и внутренний LAN); NAT не предполагается. A-запись домена сравнивается с IP **внешнего** интерфейса.
- **D-02:** Внешний интерфейс по умолчанию — интерфейс default route (`ansible_default_ipv4`); переопределяется переменными `xvpn_public_interface` / `xvpn_public_ip`. Тот же паттерн позже будет для `xvpn_lan_interface` (Phase 4).
- **D-03:** Детекция проксирования Cloudflare **не делается** — настройка DNS полностью ответственность оператора. Это сужает FND-07 (в REQUIREMENTS/ROADMAP формулировка про Cloudflare убрана). — **Reversibility:** reversible
- **D-04:** Несовпадение A-записи с внешним IP — жёсткий fail; проверка отключается флагом `xvpn_preflight_dns_check: false`.
- **D-05:** Занятые 80/443 определяются по владельцу слушающего процесса (`ss -ltnp`): если порт держит процесс нашего сервисного пользователя (`rw-*`), это не ошибка (повторный прогон идемпотентен); любой другой владелец — fail с именем процесса.
- **D-06:** Preflight не меняет хост (read-only); провал preflight = ничего не изменено (критерий успеха 1).

### Пользователи и роли (FND-02, FND-06)
- **D-07:** Rootless-пользователи по домену доверия: `rw-edge` (Traefik + заглушка), `rw-panel` (backend/Postgres/Valkey/sub-page), `rw-node` (remnanode). Имена настраиваются переменными. В Phase 1 создаётся механизм и тестовый `rw-edge`; остальные пользователи появятся в своих фазах через тот же механизм. — **Reversibility:** costly — имена пользователей и пути данных зашиты в развёрнутые хосты; смена требует миграции владельцев и home
- **D-08:** Сервисные учётки: обычные UID (>= 1000, чтобы `user@.service`/linger/subuid работали штатно), shell `/sbin/nologin`, без пароля, home в `/var/lib/xvpn/<user>`. Research обязан проверить SELinux-контексты нестандартного home (`semanage fcontext` эквивалентность `/home`, `user_home_dir_t`/`container_file_t` для `~/.config/containers` и `~/.local/share/containers`) и применить идемпотентно. — **Reversibility:** costly — переезд home = перенос хранилища контейнеров
- **D-09:** Роли Phase 1: `preflight` (отдельная, read-only, запускается сама по себе), `common` (firewalld base, SELinux-assert, пакеты), `podman_rootless` (пользователи, linger, subuid/subgid, sysctl, развёртывание Quadlet). Без `meta`-зависимостей, порядок в playbook.

### Механизм развёртывания Quadlet (FND-04) — по запросу пользователя «не изобретать велосипед»
- **D-10:** Предпочтительно использовать `fedora.linux_system_roles.podman` (Linux System Roles; в RHEL — `rhel-system-roles.podman`) для развёртывания rootless Quadlet (`podman_quadlet_specs` с нашими `template_src`, `run_as_user`), а наш `podman_rootless` отвечает за создание пользователей, home и sysctl (LSR требует, чтобы пользователь уже существовал). **Условие:** research/spike подтверждает на EL10 + Podman 6: (a) поддержку нужных Quadlet-ключей (`Notify=healthy`, `HealthCmd`, `.network`/`.volume`, raw `[Service]`), (b) идемпотентность (`changed=0`), (c) перезапуск только изменённых юнитов, (d) работу с home в `/var/lib/xvpn`, (e) возможность добавить generator dry-run валидацию (своим шагом до/после). Если хотя бы одно не выполняется — пишем собственный тонкий хелпер `deploy_quadlet` (template + `podman-system-generator --user --dryrun` + daemon-reload + restart changed) и фиксируем обоснование в RESEARCH.md. — **Reversibility:** costly — от выбора зависит интерфейс, через который все роли Phase 2-4 разворачивают юниты
- **D-11:** Мелкие community-роли (`safeaim/podman_rootless`, `voidquark/podman_play`) не использовать (bus-factor, `.kube` запрещён в STACK).

### Тестовый сервис и firewalld (FND-03, FND-05)
- **D-12:** «Тестовый Quadlet-сервис на :80» — только Molecule-фикстура: в converge через механизм D-10 разворачивается `nginx-unprivileged` под `rw-edge`, слушает 80. В коллекции не остаётся; Phase 2 заменит его Traefik.
- **D-13:** firewalld — только добавляем своё: роль открывает нужные ей порты в зоне внешнего интерфейса, чужие правила оператора не трогает. Verify проверяет, что внутренние порты (3000/3010/8443/2222) снаружи не открыты.
- **D-14:** SSH не трогаем (порт и правила — у оператора); роль лишь проверяет, что сервис ssh остаётся разрешён, чтобы не потерять доступ. LAN-зона — Phase 4.

### Molecule и CI (QA-01, QA-02, QA-03)
- **D-15:** VM-тир обязателен: SELinux, AVC, boolean'ы и reboot невозможно проверить в контейнере (dind/podman-in-podman делят ядро хоста; на Ubuntu-раннерах SELinux выключен). Контейнерный тир (podman-драйвер, не Docker) — для рендера, dry-run, идемпотентности, логики preflight, lint.
- **D-16:** VM-тир запускается на GitHub-hosted раннерах с `/dev/kvm` (PR в main + nightly) и локально одной командой. Если research покажет, что KVM на раннерах не работает — VM-тир остаётся локальным, это документируется.
- **D-17:** Репозиторий — GitHub, CI — GitHub Actions (`.github/workflows`).
- **D-18:** VM-тир покрывает и AlmaLinux 10, и Rocky 10.

### Решения пользователя, принятые во время планирования (датированы)
- **D-19 (2026-11-23, ответ «Явный warning» в сессии планирования):** если `xvpn_preflight_dns_check: true`, а `xvpn_preflight_domains` пуст, preflight не падает, а продолжает работу и печатает видимое предупреждение `A-record check skipped: xvpn_preflight_domains is empty`. Проверка A-записи активна только когда оператор задал домены (в Phase 1 домены задаёт оператор; роли panel/node заполнят их в Phases 2-4). — **Reversibility:** reversible
- **D-20 (2026-11-24):** пользователь принимает, что эквивалентность home `/var/lib/xvpn` (D-08) и SELinux-контексты проверяются только в VM-тире (wave 9, планы 01-11/01-12), без раннего spike. Любой AVC по-прежнему эскалируется через `checkpoint:decision` (без автопочинки, без смены D-08 без решения пользователя). Фазы 2-4 планируются только после завершения Phase 1. — **Reversibility:** costly (риск принят пользователем; при AVC решение пересматривается через checkpoint)
- **D-21 (2026-11-24):** репозиторий `Tualua/xvpn` уже PUBLIC, `origin/main` (3b54bcc) уже содержит историю `.planning/`; пользователь решил оставить его публичным. План 01-09 не создаёт репозиторий и не добавляет remote, а проверяет существующее состояние (`git remote get-url origin` == `https://github.com/Tualua/xvpn.git`, `gh repo view Tualua/xvpn --json visibility` == `PUBLIC`, `gh auth status` == 0) и пушит локальные коммиты. Риск раскрытия `.planning/` принят пользователем. — **Reversibility:** one-way (история уже опубликована)
- **D-22 (2026-11-23, решение пользователя в сессии планирования; ранее записано только в RESEARCH Open Question 3, перенесено сюда 2026-11-24):** VM-тир Phase 1 гоняет обе ноги (AlmaLinux 10, Rocky 10) на Podman 6.1.x; отдельной VM-ноги на Podman 5.4-5.8 (EL10.0-10.2) нет. Пол 5.4 обеспечивается только version-check в preflight (план 01-06, негативный кейс в 01-08). Пользователь принимает риск, что ключ Quadlet или поведение LSR, отличающиеся на Podman 5.x, не ловятся CI до QA-06 (Phase 5). README (план 01-12) раскрывает этот остаточный риск. Планы 01-11/01-12 ссылаются на это решение. — **Reversibility:** reversible (нога добавляется в QA-06)
- **D-23 (2026-11-24, решение пользователя):** нога CI-матрицы на ansible-core 2.22 откладывается до QA-06 (Phase 5) — сознательное отступление от строки CLAUDE.md «Matrix: ansible-core {2.21, 2.22}». CI Phase 1 пинит только ansible-core 2.21 (`requirements-dev.txt`: `ansible-core>=2.21,<2.22`, план 01-09); `scripts/check.sh` локально в devcontainer идёт на 2.22. Записано также как Key Decision в `.planning/PROJECT.md`. — **Reversibility:** reversible (нога добавляется в QA-06)

### Claude's Discretion
- Драйвер VM для Molecule: Vagrant+libvirt (box `almalinux/10`, Rocky из cloud-образа) или delegated + официальные GenericCloud-образы через virt-install/cloud-init — выбирает research по стабильности на GitHub-раннерах.
- Резолвер для проверки A-записи (системный резолвер хоста по умолчанию; Cloudflare-детекции нет).
- Использовать ли LSR `firewall`/`selinux` роли вместо `ansible.posix.firewalld`/`seboolean` — при условии соблюдения D-13 (только добавлять своё).
- Формат сообщений preflight и структура переменных (`xvpn_<role>_*`).
- Обработка AAAA-записей в preflight: только warning, никогда не fail (RESEARCH A13, Open Question 6 RESOLVED). Это выбор Claude в рамках discretion, а не решение пользователя.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Проект и требования
- `.planning/PROJECT.md` — core value, constraints, Key Decisions
- `.planning/REQUIREMENTS.md` — FND-01..07, QA-01..03 (формулировка FND-07 сужена: без Cloudflare)
- `.planning/ROADMAP.md` §Phase 1 — goal, success criteria, research flags (Podman 5.x vs 6.x, KVM на раннерах, drop-in `user@.service`)
- `.planning/STATE.md` — накопленные решения и blockers

### Research
- `.planning/research/STACK.md` — версии, Quadlet-фичи, SELinux/firewalld подход, Molecule-тиры
- `.planning/research/ARCHITECTURE.md` — роли, пользователи `rw-*`, конвенции переменных, anti-patterns
- `.planning/research/PITFALLS.md` — известные ловушки rootless/SELinux
- `.planning/research/SUMMARY.md` — сводка

### Внешние
- https://github.com/linux-system-roles/podman — LSR podman role (README: `podman_quadlet_specs`, `run_as_user`, ограничения)
- https://docs.redhat.com/en/documentation/Red_Hat_Enterprise_Linux/10/html/building_running_and_managing_containers/managing-containers-by-using-rhel-system-roles — RHEL 10 документация по роли

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Кода пока нет (greenfield): в репозитории только `.planning/` и `.devcontainer/devcontainer.json` (образ `ghcr.io/tualua/aidev:latest`).

### Established Patterns
- Из ARCHITECTURE.md: префикс переменных `xvpn_<role>_*`, `meta/argument_specs.yml` в каждой роли, роли не зависят друг от друга через `meta`, межролевое взаимодействие через `include_role ... tasks_from`.

### Integration Points
- Механизм развёртывания Quadlet (D-10) — общий интерфейс для ролей `traefik`, `panel`, `node`, `selfsteal` в Phase 2-4.
- Molecule VM-тир — стенд для всех следующих фаз.

</code_context>

<specifics>
## Specific Ideas

- Пользователь явно просил не изобретать велосипед: сначала проверять готовые Galaxy-роли/коллекции, свой код — только при обоснованной несовместимости.
- Типичная нода: два интерфейса (публичный + LAN), без NAT.

</specifics>

<deferred>
## Deferred Ideas

- `xvpn_lan_interface` и firewalld-зона для LAN — Phase 4.
- Управление SSH (порт, sshd_config) — Phase 5 (hardening).

</deferred>

---

*Phase: 01-rootless-fundament-i-testovyy-stend*
*Context gathered: 2026-11-23*
