# Phase 2: Panel за Traefik с защищённым входом - Pattern Map

**Mapped:** 2026-11-25
**Files analyzed:** 33 (new/modified)
**Analogs found:** 27 / 33 (все analog-пути проверены как git-tracked, зеркал `.gsd/capabilities` в репозитории нет)

Важно: в `roles/*` пока нет ни одного `templates/*.j2` и `files/`; единственные Quadlet-шаблоны лежат в `extensions/molecule/shared/templates/`. Шаблоны Quadlet, Traefik и env берутся из RESEARCH.md (Code Examples), а структура ролей, assert-стиль, Quadlet-деплой и Molecule-сценарии копируются из кода фазы 1.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `roles/edge/defaults/main.yml` | config | n/a | `roles/podman_rootless/defaults/main.yml` | exact |
| `roles/edge/meta/main.yml` | config | n/a | `roles/podman_rootless/meta/main.yml` | exact |
| `roles/edge/meta/argument_specs.yml` | config | n/a | `roles/podman_rootless/meta/argument_specs.yml` (секции `main` + `quadlet`) | exact |
| `roles/edge/tasks/main.yml` | service | file-I/O + request-response | `roles/podman_rootless/tasks/main.yml` + `playbooks/foundation.yml` (вызов quadlet) | role-match |
| `roles/edge/tasks/route.yml` (entry point для drop-in маршрутов) | utility | file-I/O | `roles/podman_rootless/tasks/quadlet.yml` | exact (тот же паттерн entry point) |
| `roles/edge/templates/traefik.container.j2`, `decoy.container.j2` | config (Quadlet unit) | event-driven (systemd) | `extensions/molecule/shared/templates/xvpn-fixture.container.j2` | exact |
| `roles/edge/templates/traefik.yml.j2`, `00-tls-options.yml.j2`, `decoy-nginx.conf.j2` | config | transform | нет (RESEARCH Code Examples) | no analog |
| `roles/edge/files/decoy/index.html` | config (static) | n/a | нет | no analog |
| `roles/panel/defaults/main.yml` | config | n/a | `roles/podman_rootless/defaults/main.yml`, `roles/preflight/defaults/main.yml` | exact |
| `roles/panel/meta/main.yml`, `meta/argument_specs.yml` | config | n/a | см. edge | exact |
| `roles/panel/tasks/main.yml` (asserts, порядок include) | controller | request-response | `roles/common/tasks/main.yml` (asserts + `include_tasks`) | role-match |
| `roles/panel/tasks/secrets.yml` | service | file-I/O (generate-once) | нет полного; частично `roles/podman_rootless/tasks/user.yml` (getent/assert/register) | partial |
| `roles/panel/tasks/stack.yml` | service | file-I/O + event-driven | `extensions/molecule/vm/converge.yml` (вызов quadlet) + `roles/podman_rootless/tasks/quadlet.yml` | role-match |
| `roles/panel/tasks/bootstrap.yml` | service | request-response (HTTP) | `extensions/molecule/shared/verify_runtime.yml` (`uri` + `until/retries`) | role-match |
| `roles/panel/tasks/subpage.yml`, `routes.yml` | service | file-I/O | `roles/podman_rootless/tasks/quadlet.yml` | role-match |
| `roles/panel/templates/*.container.j2`, `*.network.j2`, `*.volume.j2` | config (Quadlet) | event-driven | `extensions/molecule/shared/templates/xvpn-fixture.container.j2` | role-match |
| `roles/panel/templates/*.env.j2`, `panel-routes.yml.j2` | config | transform | нет (RESEARCH Code Examples) | no analog |
| `roles/podman_rootless/defaults/main.yml` (MOD: добавить `rw-panel`) | config | n/a | сам файл, строки 3-4 | exact |
| `roles/preflight` / `playbooks/panel.yml` (`xvpn_preflight_domains`) | playbook | n/a | `playbooks/foundation.yml` | exact |
| `playbooks/panel.yml` | playbook | batch | `playbooks/foundation.yml` | exact |
| `playbooks/site.yml` | playbook | batch | `playbooks/foundation.yml` (`import_playbook`) | role-match |
| `extensions/molecule/container/{converge,verify}.yml` (MOD) | test | batch | сами файлы | exact |
| `extensions/molecule/vm/{prepare,converge,verify,molecule}.yml` (MOD: Pebble, e2e) | test | request-response | сами файлы | exact |
| `extensions/molecule/shared/verify_panel.yml`, `verify_gate.yml` | test | request-response | `extensions/molecule/shared/verify_runtime.yml` | exact |
| `extensions/molecule/shared/templates/*.j2` (MOD: убрать fixture :80) | test | n/a | `xvpn-fixture.container.j2` | exact |
| gate-spike script (Traefik + Pebble, container tier) | test | request-response | `scripts/check.sh` (стиль bash) | partial |
| `requirements.yml`, `galaxy.yml`, `README.md`, `.planning/REQUIREMENTS.md`/`ROADMAP.md` (D-02 wording) | config/docs | n/a | `requirements.yml` | exact |

## Pattern Assignments

### `roles/edge/**` и `roles/panel/**`: каркас роли (defaults, meta, argument_specs)

**Analog:** `roles/podman_rootless/` (defaults, meta/main.yml, meta/argument_specs.yml)

**meta/main.yml** (полностью, `roles/podman_rootless/meta/main.yml`): без зависимостей (D-09 фазы 1, D-18).
```yaml
---
galaxy_info:
  author: Dmitry Popovich
  description: Rootless Podman service users, SELinux home context, unprivileged ports and Quadlet deployment
  license: GPL-3.0-or-later
  min_ansible_version: "2.20"
  platforms:
    - name: EL
      versions:
        - "10"
  galaxy_tags: []
dependencies: []
```

**defaults** (`roles/podman_rootless/defaults/main.yml` 1-6, 26-29): комментарий-ссылка на решение (D-xx), все переменные `xvpn_<role>_*`, входы entry point-а с пустым дефолтом.
```yaml
# Inputs of the quadlet entry point (tasks_from: quadlet).
xvpn_podman_rootless_quadlet_user: ""
xvpn_podman_rootless_quadlet_specs: []
xvpn_podman_rootless_quadlet_activate: true
```
Скопировать для `roles/edge` (`xvpn_edge_route_name`, `xvpn_edge_route_src`, `xvpn_edge_route_state`) и общих имён `xvpn_panel_domain`, `xvpn_subscription_domain`.

**argument_specs** (`roles/podman_rootless/meta/argument_specs.yml`): отдельная секция на каждый entry point (`main`, `quadlet`), у каждой опции `description/type/default/required`, закрытые наборы ключей, `choices`. Для `route`-entry point повторить секцию `quadlet:` (строки 48-76). Обязательно для каждой роли (`scripts/check.sh` падает без `meta/argument_specs.yml`).

---

### `roles/edge/tasks/route.yml` (utility, file-I/O; entry point drop-in маршрутов, D-16)

**Analog:** `roles/podman_rootless/tasks/quadlet.yml`

**Заголовок и валидация входов** (строки 1-20):
```yaml
---
# Single deployment interface for Quadlet units (D-10). Inputs:
#   xvpn_podman_rootless_quadlet_user, xvpn_podman_rootless_quadlet_specs,
#   xvpn_podman_rootless_quadlet_activate
- name: Validate quadlet inputs
  ansible.builtin.assert:
    that:
      - xvpn_podman_rootless_quadlet_user is match('^[a-z_][a-z0-9_-]{0,30}$')
    fail_msg: "Invalid service user name: {{ xvpn_podman_rootless_quadlet_user }}"
    quiet: true

- name: Validate quadlet template paths
  ansible.builtin.assert:
    that:
      - item.template_src is match('^/')
    fail_msg: "template_src must be an absolute path: {{ item.template_src }}"
    quiet: true
  loop: "{{ xvpn_podman_rootless_quadlet_specs }}"
  loop_control:
    label: "{{ item.template_src }}"
```
Для `route.yml`: тот же стиль (комментарий с входами, `assert` на `xvpn_edge_route_name is match('^[a-z0-9-]+$')` и абсолютный `xvpn_edge_route_src`), затем `ansible.builtin.template` в `{{ xvpn_edge_dynamic_dir }}/<name>.yml` (owner `rw-edge`, mode `0600`, `diff: false`, `no_log` по флагу). Перезапуск Traefik не нужен (file provider `watch: true`).

---

### Развёртывание Quadlet из `edge` и `panel` (stack.yml, subpage.yml, edge/tasks/main.yml)

**Analog:** вызов entry point в `extensions/molecule/vm/converge.yml` и сам `quadlet.yml`.

**Вызов** (`extensions/molecule/vm/converge.yml` 12-22):
```yaml
- name: Deploy and activate the fixture unit through the quadlet entry point
  ansible.builtin.include_role:
    name: xvpn.remnawave.podman_rootless
    tasks_from: quadlet
  vars:
    xvpn_podman_rootless_quadlet_user: rw-edge
    xvpn_podman_rootless_quadlet_activate: true
    xvpn_podman_rootless_quadlet_specs:
      - template_src: "{{ (playbook_dir ~ '/../shared/templates/xvpn-fixture.container.j2') | realpath }}"
```
В роли использовать `{{ role_path }}/templates/<x>.j2` (абсолютный путь; `template_src` обязан начинаться с `/`). Ключ spec закрыт: допустимы только `template_src` и `state`; нужен ключ больше, расширить `argument_specs` `quadlet`.

**Важные свойства интерфейса** (из `quadlet.yml`, строки 22-48): dry-run генератора под сервисным пользователем до записи, `podman_pull_image: false`, перезапуск LSR-ролью только при изменении текста юнита. Следствие (Pitfall 7 RESEARCH): env-файлы и `traefik.yml` не перезапускают юнит, нужна явная задача `ansible.builtin.systemd_service scope: user` при `changed`.

**systemctl --user как сервисный пользователь** (шаблон для рестарта; `extensions/molecule/vm/converge.yml` 29-51 и `quadlet_validate.yml` 5-10):
```yaml
  become: true
  become_user: rw-edge
  become_method: ansible.builtin.sudo
  environment:
    XDG_RUNTIME_DIR: "/run/user/{{ ansible_facts['getent_passwd']['rw-edge'][1] }}"
```
Uid брать через `ansible.builtin.getent: database: passwd, key: <user>`.

**Quadlet unit analog** (`extensions/molecule/shared/templates/xvpn-fixture.container.j2`, целиком): структура `[Unit]/[Container]/[Service]/[Install]`, `Notify=healthy` + `HealthCmd`, `Restart=always`, `TimeoutStartSec=900`, `WantedBy=default.target`.
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
Для `decoy.container.j2` скопировать целиком (образ из переменной, `PublishPort=127.0.0.1:18080:8080`, `Network=pasta` или bridge); для Traefik заменить `Network=pasta` на `Network=host`, добавить `Volume=...:Z`, `Environment=LEGO_CA_CERTIFICATES=` только в Pebble-сценарии. Для panel-юнитов (db/redis/backend/sub-page) формы даны в RESEARCH "Quadlet units"; `.network`/`.volume` юниты проверяет dry-run (`quadlet_validate.yml` уже знает суффиксы `-network.service`, `-volume.service`).

---

### `roles/edge/tasks/main.yml`, `roles/panel/tasks/main.yml` (порядок, assert-ы, DOC-04)

**Analog:** `roles/common/tasks/main.yml` и `roles/podman_rootless/tasks/main.yml`

**Стиль assert** (`roles/common/tasks/main.yml` 1-18): имя задачи с префиксом роли `Common | ...`, `quiet: true`, `fail_msg` с подставленным значением.
```yaml
- name: Common | validate the firewall port entries
  ansible.builtin.assert:
    that:
      - item is match('^[0-9]{1,5}/(tcp|udp)$')
    fail_msg: "Invalid firewall port entry '{{ item }}'; expected <1-65535>/<tcp|udp>"
    quiet: true
  loop: "{{ xvpn_common_firewall_ports }}"
```
Для DOC-04 (placeholder-assert): `that: xvpn_panel_x not in [...]`, но `no_log: true` и `fail_msg`, которое называет КЛЮЧ, не значение (RESEARCH Pitfall 4/6).

**Regex-валидация в Jinja без обратных слешей** (`roles/podman_rootless/tasks/main.yml`, home root): `is regex('^/[A-Za-z0-9_-]+(/[A-Za-z0-9_-]+)*', match_type='fullmatch')`. Для FQDN использовать `[.]`, не `\.`. `ansible_failed_result`/`rescue` паттерны см. `extensions/molecule/container/verify.yml` (negative cases).

**Defence in depth** (`roles/common/tasks/main.yml` 20-42): повторять проверку Enforcing не нужно, но роли `edge`/`panel` должны одинаково падать на отсутствии пользователя (`getent` + assert, как в `user.yml` 11-31).

---

### `roles/panel/tasks/secrets.yml` (service, file-I/O generate-once, D-07/D-10)

**Analog:** частичный. Паттерны для копирования:
- чтение/ветвление по существующему состоянию: `roles/podman_rootless/tasks/user.yml` 11-31 (`getent ... fail_key: false` затем assert/when `is not none`);
- `register` + `changed_when: false` + `check_mode: false` для read-only команд (`user.yml` 67-75);
- чтение файла с хоста: `ansible.builtin.slurp` (пример `extensions/molecule/vm/verify.yml` 9-12: `slurp` + `b64decode | trim`);
- запись 0600 с идемпотентностью: `ansible.builtin.copy ... force: false` (`extensions/molecule/vm/converge.yml` 55-62).
```yaml
- name: Record the InvocationID after the first converge
  ansible.builtin.copy:
    content: "{{ xvpn_converge_invocation.stdout | trim }}\n"
    dest: /var/lib/xvpn-molecule/invocation_after_first_converge
    owner: root
    group: root
    mode: "0600"
    force: false
```
Генерация (нет аналога в репо): `lookup('ansible.builtin.password', '/dev/null chars=... length=N')` сегментами + `shuffle` (RESEARCH Pitfall 3); все задачи `no_log: true`, `diff: false`; файл в `{{ xvpn_podman_rootless_home_root }}/rw-panel/secrets/` owner `rw-panel` 0600.

---

### `roles/panel/tasks/bootstrap.yml` (service, request-response на loopback)

**Analog:** `extensions/molecule/shared/verify_runtime.yml` 45-55 (`uri` с `until/retries/delay`)
```yaml
- name: Answer on the port from the controller
  ansible.builtin.uri:
    url: "http://{{ ansible_host | default(inventory_hostname) }}:{{ xvpn_verify_rt_port }}/"
    status_code: 200
  delegate_to: localhost
  become: false
  register: xvpn_verify_rt_http
  until: xvpn_verify_rt_http.status == 200
  retries: 12
  delay: 5
```
Для bootstrap: URL `http://127.0.0.1:3000/api/...` (без `delegate_to`), обязательные заголовки `X-Forwarded-For: 127.0.0.1` и `X-Forwarded-Proto: https`, `no_log: true`, `check_mode: false` на read-only GET. Конкретные тела запросов и state machine: RESEARCH "Loopback bootstrap tasks" и Pattern 2.

---

### `roles/preflight` и `xvpn_preflight_domains` (MOD через playbook)

**Analog:** `roles/preflight/defaults/main.yml` (`xvpn_preflight_domains: []`) и `roles/preflight/tasks/check_dns.yml` (цикл `loop: "{{ xvpn_preflight_domains }}"`). Роль preflight не менять; в `playbooks/panel.yml` передать домены переменной play:
```yaml
  vars:
    xvpn_preflight_domains: ["{{ xvpn_panel_domain }}", "{{ xvpn_subscription_domain }}"]
```
Учесть: preflight проверяет порты 80/443 и принимает листенеры пользователей из `xvpn_preflight_service_users` (там уже есть `rw-edge`, `rw-panel`), так что повторный прогон с Traefik на 80/443 не ошибка.

---

### `playbooks/panel.yml` и `playbooks/site.yml`

**Analog:** `playbooks/foundation.yml` (целиком)
```yaml
---
- name: Preflight (read-only)
  hosts: all
  become: true
  gather_facts: true
  any_errors_fatal: true
  tags: [preflight]
  roles:
    - xvpn.remnawave.preflight

- name: Foundation
  hosts: all
  become: true
  gather_facts: true
  roles:
    - xvpn.remnawave.common
    - xvpn.remnawave.podman_rootless
```
Для `panel.yml`: заменить `hosts: all` на `hosts: "{{ xvpn_panel_hosts_group | default('remnawave_panel') }}"`, повторить три play-блока (preflight с `tags: [preflight]`, foundation, затем edge и panel). FQCN ролей `xvpn.remnawave.<role>`. `site.yml`: `- ansible.builtin.import_playbook: panel.yml` (стиль `import_playbook` см. `extensions/molecule/container/converge.yml` 2-3). `scripts/check.sh` автоматически syntax-check-ает все `playbooks/*.yml`.

---

### `roles/podman_rootless/defaults/main.yml` (MOD)

Добавить `- name: rw-panel` в `xvpn_podman_rootless_users` (комментарий в строке 2 уже анонсирует это: "Phases 2-4 append rw-panel, rw-node"). Синхронно обновить default в `argument_specs.yml` (строки 10-12). Роль `user.yml` создаёт пользователя одинаково для любого имени.

---

### Firewalld (80/443 на Panel-хосте)

**Analog:** `roles/common/tasks/firewalld.yml` (не менять): порты подаются переменной `xvpn_common_firewall_ports`, задача add-only с SSH-guard.
Применить в `playbooks/panel.yml`: `vars: xvpn_common_firewall_ports: ["80/tcp", "443/tcp"]` (формат `<n>/<tcp|udp>` валидируется в `common/tasks/main.yml`). 3000/3001/3010/18080 не открывать.

---

### `extensions/molecule/shared/verify_panel.yml`, `verify_gate.yml`, VM `prepare.yml`/`converge.yml`/`verify.yml`

**Analog:** `extensions/molecule/shared/verify_runtime.yml`, `extensions/molecule/vm/*.yml`

**Параметризованный shared-файл** (`verify_runtime.yml` 1-12): комментарий с входами, `set_fact` с `| default(...)` из `xvpn_verify_*`, `getent` + uid, ожидание юнита через `systemctl --user is-active` под `become_user` + `XDG_RUNTIME_DIR` и `until/retries: 60/delay: 10`.
```yaml
- name: Resolve the runtime verify inputs
  ansible.builtin.set_fact:
    xvpn_verify_rt_user: "{{ xvpn_verify_user | default('rw-edge') }}"
    xvpn_verify_rt_unit: "{{ xvpn_verify_unit | default('xvpn-fixture.service') }}"
    xvpn_verify_rt_port: "{{ xvpn_verify_port | default(80) }}"
```
`verify_runtime.yml` вызывается с дефолтом `xvpn-fixture.service`/порт 80; для фазы 2 передавать `xvpn_verify_unit: traefik.service`, `xvpn_verify_port: 443`/`80` или заменить fixture. Проверки владельца листенера через `ss -H -ltnpe` + `uid:<uid>` (строки 57-68) и SELinux Enforcing/метки (70-end) переиспользовать без изменений для `rw-edge` и `rw-panel`.

**Include из verify** (`extensions/molecule/vm/verify.yml` 30-43): `include_tasks: ../shared/verify_*.yml` с `vars:`. Новые `verify_panel.yml`/`verify_gate.yml` включать так же. Контейнерный verify (`extensions/molecule/container/verify.yml`) содержит блок "negative case" (`block/rescue` + `xvpn_negative_rejected` + `# xvpn_negative_case:` маркер): копировать для assert-ов placeholder (DOC-04) и расхождения секретов (D-10).

**VM prepare** (`extensions/molecule/vm/prepare.yml`): ставит auditd/seinfo, отключает dontaudit и пишет AVC-маркер. Pebble/challtestsrv добавить отдельным play ПОСЛЕ этой цепочки (и до converge), чтобы установка не пересобрала политику (комментарий в prepare 15-17). Нулевой AVC проверяет существующий verify_runtime/AVC-блок.

**Converge VM/container**: заменить блок "Deploy molecule fixture" на импорт `../../../playbooks/panel.yml` (стиль `import_playbook` + `vars:` из `container/converge.yml` 2-9). Container tier держит `xvpn_podman_rootless_manage_user_manager: false`, `xvpn_common_firewalld_offline: true`, `xvpn_podman_rootless_quadlet_activate: false` (юниты не активируются, проверяется только рендер и dry-run).

**molecule.yml (vm)** (`extensions/molecule/vm/molecule.yml`): `test_sequence` уже включает `idempotence` (`changed=0`), `side_effect` (перезагрузка), `verify`; новых сценариев не требуется, если Pebble ставится в prepare.

---

### Gate-spike script (контейнерный тир, регрессия гейта)

**Analog:** `scripts/check.sh` (bash-стиль): `#!/usr/bin/env bash`, `set -euo pipefail`, `ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`, проверка наличия инструментов с `echo ... >&2; exit 1`. Скачивание Traefik/Pebble с проверкой sha256 (значения в RESEARCH "Installation") во временный каталог, запуск, прогон матрицы Pattern 1. Подключить вызов в `.github/workflows/molecule-container.yml` по образцу существующих шагов.

---

## Shared Patterns

### Единый вход развёртывания Quadlet
**Source:** `roles/podman_rootless/tasks/quadlet.yml` (строки 38-48)
**Apply to:** все юниты `edge` и `panel`. Не вызывать `fedora.linux_system_roles.podman` напрямую.

### Идентификаторы и именование
**Source:** `roles/*/defaults/main.yml`, `.ansible-lint` (`var-naming[no-role-prefix]` в skip_list)
**Apply to:** все новые роли: переменные `xvpn_<role>_*`, внутренние register-переменные с префиксом роли (`xvpn_panel_*`), имена задач с префиксом `Role | ...` (в `common`/`preflight`), FQCN модулей, `ansible.builtin.*` везде. Профиль lint `production`, yamllint `-s`.

### Запуск команд под сервисным пользователем
**Source:** `roles/podman_rootless/tasks/quadlet_validate.yml` 5-10
**Apply to:** любые `systemctl --user`, `podman exec/logs`, проверки под `rw-edge`/`rw-panel`.
```yaml
  become: true
  become_user: "{{ user }}"
  become_method: ansible.builtin.sudo
  environment:
    XDG_RUNTIME_DIR: "/run/user/{{ uid }}"
```

### Read-only команды
**Source:** `roles/podman_rootless/tasks/user.yml` 67-75: `changed_when: false`, `check_mode: false`, `failed_when: false` когда rc анализируется отдельным assert-ом. **Apply to:** все `uri` GET, `slurp`, `stat`, `command` без побочных эффектов (иначе нарушается `changed=0`).

### Сбор ошибок и сообщения
**Source:** `roles/preflight/tasks/main.yml` (накопление `xvpn_preflight_errors` и один финальный `fail`); `assert ... quiet: true` + подробный `fail_msg`. **Apply to:** `panel`/`edge` assert-ы; в `fail_msg` называть переменную, не значение секрета (D-10, D-11).

### Секреты (D-11, DOC-04)
**Source:** новых аналогов в репо нет, правила из RESEARCH Pitfall 4: `no_log: true` и `diff: false` на каждом `template/copy/uri/slurp/set_fact` с секретом; `loop_control.label` без item; без `cacheable: true`; в итоговом сообщении только пути файлов.

### Идемпотентность и рестарт
**Source:** `extensions/molecule/vm/converge.yml` + `side_effect.yml`: InvocationID не меняется на втором прогоне. **Apply to:** рестарт Traefik/backend только при `changed` env/static-файла (Pitfall 7).

### Firewalld
**Source:** `roles/common/tasks/firewalld.yml`: только добавление портов, SSH-guard. **Apply to:** `playbooks/panel.yml` через `xvpn_common_firewall_ports`.

## No Analog Found

Планировщик использует RESEARCH.md (Code Examples) как первоисточник:

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `roles/edge/templates/traefik.yml.j2`, `00-tls-options.yml.j2` | config | transform | В репо нет ни Traefik-конфигов, ни шаблонов внутри ролей; брать "Traefik static config" и "Gate dynamic config" из RESEARCH |
| `roles/edge/templates/decoy-nginx.conf.j2`, `files/decoy/index.html` | config | n/a | Нет статического контента; только fixture-юнит nginx без конфига |
| `roles/panel/templates/*.env.j2`, `panel-routes.yml.j2` | config | transform | Нет env-шаблонов; ключи из RESEARCH "Backend env"/"Sub-page env" |
| `roles/panel/templates/*.network.j2`, `*.volume.j2` | config | event-driven | Нет `.network`/`.volume` примеров в репо (dry-run их поддерживает); формы из Podman Quadlet docs и RESEARCH |
| `roles/panel/tasks/secrets.yml` (генерация случайных значений) | service | file-I/O | Нет генерации секретов в фазе 1; использовать `lookup('password')` по RESEARCH Pitfall 3 |
| Pebble/challtestsrv установка в VM prepare | test | batch | Нет загрузки бинарников с проверкой sha256; стиль задач брать из `vm/prepare.yml` (dnf/systemd_service), pins из RESEARCH |

## Metadata

**Analog search scope:** `roles/`, `playbooks/`, `extensions/molecule/`, `scripts/`, `requirements.yml`, `.ansible-lint` (весь tracked-код фазы 1; `git ls-files` показал 56 файлов вне `.planning`)
**Files scanned:** ~30 прочитано целиком или по секциям
**Tracked-source gate:** все analog-пути взяты из `git ls-files`, путей-зеркал нет
**Pattern extraction date:** 2026-11-25
