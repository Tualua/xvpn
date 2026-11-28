# Phase 3: Нода с Reality self-steal и авто-регистрацией - Pattern Map

**Mapped:** 2026-11-28
**Files analyzed:** 41 (new/modified)
**Analogs found:** 33 / 41 (8 без аналога: весь `plugins/`, `tests/unit/`, `scripts/selfsteal/` частично)

Все пути аналогов проверены по `git ls-files` (tracked). Зеркал `.gsd/capabilities` в проекте нет.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `roles/node/defaults/main.yml` | config | n/a | `roles/panel/defaults/main.yml` | exact |
| `roles/node/vars/main.yml` | config | n/a | `roles/panel/vars/main.yml`, `roles/edge/vars/main.yml` | exact |
| `roles/node/meta/main.yml` | config | n/a | `roles/panel/meta/main.yml` | exact |
| `roles/node/meta/argument_specs.yml` | config | n/a | `roles/panel/meta/argument_specs.yml`, `roles/edge/meta/argument_specs.yml` | exact |
| `roles/node/tasks/main.yml` (present/absent dispatch, asserts) | service | request-response | `roles/panel/tasks/main.yml` | exact |
| `roles/node/tasks/gate.yml` (cert gate STEAL-05) | utility | request-response (probe) | `roles/panel/tasks/bootstrap.yml` (until/retries wait) | role-match |
| `roles/node/tasks/secret.yml` (generate-once SECRET_KEY) | service | file-I/O | `roles/panel/tasks/secrets.yml` | role-match |
| `roles/node/tasks/firewall.yml` (443 + rich rule 2222) | service | CRUD | `roles/common/tasks/firewalld.yml` | exact |
| `roles/node/tasks/register.yml` | service | request-response | `roles/panel/tasks/bootstrap.yml` (delegated API calls) + `roles/panel/tasks/subpage.yml` (token) | role-match |
| `roles/node/tasks/decommission.yml` | service | CRUD | `roles/panel/tasks/subpage.yml` (блок "switch off") | exact |
| `roles/node/templates/remnanode.container.j2` | config (Quadlet) | n/a | `roles/panel/templates/remnawave.container.j2` | exact |
| `roles/node/templates/node.env.j2` | config | n/a | `roles/panel/templates/backend.env.j2` | exact |
| `roles/node/templates/node-selfsteal.yml.j2` | route | n/a | `roles/panel/templates/subscription-routes.yml.j2` | exact |
| `roles/node/templates/config-profile.json.j2` | config | transform | `roles/panel/templates/panel-routes.yml.j2` (Jinja with secrets, `ansible_managed`) | partial |
| `roles/edge/tasks/decoy.yml` (new) + `roles/edge/tasks/main.yml` (mod) | service | file-I/O | `roles/edge/tasks/main.yml` lines 96-126 | exact |
| `roles/edge/files/decoy-templates/<name>/...` | static asset | n/a | `roles/edge/files/decoy/index.html` | role-match |
| `roles/edge/templates/decoy-nginx.conf.j2` (mod: strict 404 mode) | config | n/a | itself | exact |
| `roles/edge/defaults/main.yml`, `meta/argument_specs.yml` (mod) | config | n/a | itself | exact |
| `playbooks/node.yml` | playbook | n/a | `playbooks/panel.yml` | exact |
| `playbooks/site.yml` (mod) | playbook | n/a | itself | exact |
| `roles/preflight/defaults/main.yml` (мод. не нужен: `rw-node` уже есть) | config | n/a | itself | exact |
| `plugins/module_utils/remnawave.py` | utility | request-response | нет аналога | none |
| `plugins/modules/remnawave_{config_profile,node,host,internal_squad,node_secret}.py` | module | request-response / CRUD | нет аналога | none |
| `plugins/doc_fragments/remnawave.py` | utility | n/a | нет аналога | none |
| `meta/runtime.yml` (mod: action_groups) | config | n/a | itself (2 строки) | exact |
| `tests/unit/*.py` (unittest + fake Panel) | test | request-response | нет аналога (ближайшее `scripts/check_no_log.py` self_test) | none |
| `scripts/selfsteal/run.sh` | test (gate) | request-response | `scripts/gate/run.sh` | exact |
| `scripts/selfsteal/render.yml` | test | transform | `scripts/gate/render.yml` | exact |
| `scripts/check.sh` (mod: regex `node`) | config | n/a | itself lines 69-92 | exact |
| `scripts/check_no_log.py` (mod: SENSITIVE) | utility | n/a | itself lines 14-31 | exact |
| `.gitleaks.toml` (mod: allowlist `scripts/selfsteal/`) | config | n/a | itself last `[[allowlists]]` | exact |
| `extensions/molecule/container/{molecule,converge,verify}.yml` (mod/node scenario) | test | n/a | `extensions/molecule/container/*` | exact |
| `extensions/molecule/vm-e2e/{molecule,converge,verify,side_effect}.yml` (two-VM) | test | n/a | `extensions/molecule/vm/*` | role-match |
| `extensions/molecule/shared/verify_node.yml`, `verify_selfsteal.yml` | test | request-response | `extensions/molecule/shared/verify_edge.yml`, `verify_panel.yml` | exact |
| `extensions/molecule/vm*/tasks/pebble.yml` (reuse) | test | n/a | `extensions/molecule/vm/tasks/pebble.yml` | exact |
| `galaxy.yml` (build_ignore tests, при необходимости) | config | n/a | itself | exact |

## Pattern Assignments

### `roles/node/tasks/main.yml` (service, request-response)

**Analog:** `roles/panel/tasks/main.yml` (+ `roles/edge/tasks/main.yml` 1-38 для assert/getent).

**Validate domain** (panel/main.yml 3-9): FQDN-regex и запрет `example.*`; для ноды домен идёт в backticked `Host()` Traefik, поэтому assert обязателен до рендера (Security: rule injection).
```yaml
- name: Panel | validate the Panel domain
  ansible.builtin.assert:
    that:
      - xvpn_panel_domain is regex('^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?[.])+([a-z]{2,63}|xn--[a-z0-9]([a-z0-9-]{0,57}[a-z0-9])?)$')
      - not (xvpn_panel_domain is regex('(^|[.])example[.](com|org|net)$'))
    fail_msg: "xvpn_panel_domain must be a real lowercase FQDN, got '{{ xvpn_panel_domain }}'"
    quiet: true
```
**Service-user check** (panel/main.yml 24-35): `getent` + `fail_key: false` + assert "run xvpn.remnawave.podman_rootless first".
**Dispatch:** `include_tasks: x.yml` с префиксом имени задачи `Node | ...` (как `Panel | ...`). Для `state: absent` без `xvpn_node_decommission_confirm` - `ansible.builtin.assert` с понятным `fail_msg` (D-08).
**Образ:** assert из edge/main.yml 6-9: `is search(':[^/:]+$')` и `not (... is search(':latest$'))`.

### `roles/node/templates/remnanode.container.j2` (Quadlet, n/a)

**Analog:** `roles/panel/templates/remnawave.container.j2` (всё, 29 строк) и `roles/edge/templates/xvpn-decoy.container.j2` (Restart/RestartSec).
```ini
[Container]
Image={{ xvpn_node_image }}
ContainerName=remnanode
Network=host
EnvironmentFile={{ xvpn_node_env_dir }}/node.env
Ulimit=nofile=524288:524288
LogDriver=k8s-file
LogOpt=max-size=50m

[Service]
Restart=always
RestartSec=5
TimeoutStartSec=900

[Install]
WantedBy=default.target
```
Нет `PublishPort` (host net), нет `AddCapability`, нет `SecurityLabelDisable`. Не копировать `Requires=`/`Notify=healthy` из panel: у ноды нет зависимых юнитов, health-check образа не подтверждён (A5).

### `roles/node/templates/node.env.j2` + env-запись (config, file-I/O)

**Analog:** `roles/panel/templates/backend.env.j2` (plain `KEY=value`, первая строка `# {{ ansible_managed }}`) и задача `roles/panel/tasks/stack.yml` 22-31:
```yaml
- name: Panel stack | render the backend env file
  ansible.builtin.template:
    src: backend.env.j2
    dest: "{{ xvpn_panel_env_dir }}/backend.env"
    owner: "{{ xvpn_panel_user }}"
    group: "{{ xvpn_panel_user }}"
    mode: "0600"
  register: xvpn_panel_backend_env
  diff: false
  no_log: true
```
Каталог env: `file state=directory mode "0700"` (stack.yml 13-20). Путь env `*.env`/`/secrets/` попадает под `SECRET_FILE` guard `check_no_log.py`, поэтому `no_log: true` и `diff: false` обязательны. Рестарт при смене env: `include_role podman_rootless tasks_from: restart_stale` как в `subpage.yml` 66-76 (`restart_files`, `restart_changed: "{{ xvpn_node_env is changed }}"`).

### `roles/node/tasks/secret.yml` (service, file-I/O, generate-once)

**Analog:** `roles/panel/tasks/secrets.yml` (паттерн stat файла - читать - сгенерировать только если нет; no_log + diff:false на всё). Отличие: источник SECRET_KEY - `remnawave_node_secret` (GET /api/keygen, делегируется на Panel-хост), вызывается **только** если `node.env` отсутствует (stat, строки 13-16 паттерна). Fresh-key-per-call (Pitfall 3) требует stat-gate перед модулем.
```yaml
- name: Panel secrets | stat the secrets file
  ansible.builtin.stat:
    path: "{{ xvpn_panel_secrets_file }}"
  register: xvpn_panel_secrets_stat
```
Учесть `check_mode: false` на read-only stat/slurp, как в bootstrap.yml 134-143.

### `roles/node/tasks/gate.yml` (STEAL-05 cert gate)

**Analog:** `roles/panel/tasks/bootstrap.yml` 7-32 (until + retries + `failed_when: false` + `changed_when: false` + `check_mode: false`, затем отдельный `fail` с диагностикой).
```yaml
  register: xvpn_panel_bs_status
  until: xvpn_panel_bs_status.status | default(-1) == 200
  retries: "{{ xvpn_panel_bootstrap_retries }}"
  delay: 5
  failed_when: false
  changed_when: false
  check_mode: false
```
Применить: `ansible.builtin.command` с `openssl s_client -connect 127.0.0.1:8443 -servername <domain> -verify_hostname <domain>` (RESEARCH Code Examples); **нельзя** совмещать `until` с `set_fact` (`scripts/check_until_set_fact.py`). `fail` с сообщением про ACME staging/rate limits, DNS, порт 80. Тест-CA: `-CAfile` из `xvpn_edge_acme_trusted_ca_file`.

### `roles/node/tasks/firewall.yml` (443/tcp + rich rule 2222)

**Analog:** `roles/common/tasks/firewalld.yml` 80-88 (add-only) и 22-46 (определение зоны; `xvpn_common_fw_zone` уже set_fact после роли `common`).
```yaml
- name: Common | open the declared ports (add-only)
  ansible.posix.firewalld:
    zone: "{{ xvpn_common_fw_zone }}"
    port: "{{ item }}"
    permanent: true
    immediate: "{{ not xvpn_common_firewalld_offline }}"
    offline: "{{ xvpn_common_firewalld_offline }}"
    state: enabled
  loop: "{{ xvpn_common_firewall_ports }}"
```
Для rich rule заменить `port:` на `rich_rule: 'rule family="ipv4" source address="{{ item }}" port port="{{ xvpn_node_api_port }}" protocol="tcp" accept'` (RESEARCH Firewall block). Валидировать IP/CIDR regex до рендера. `443/tcp` и `80/tcp` лучше задать через `vars: xvpn_common_firewall_ports` в `playbooks/node.yml` (как panel.yml 36). `8443` не открывать. Decommission: тот же модуль `state: disabled` только для того, что открыла роль.

### `roles/node/tasks/register.yml` (service, request-response)

**Analog:** `roles/panel/tasks/bootstrap.yml` (заголовки `X-Forwarded-For: 127.0.0.1`, `X-Forwarded-Proto: https`, `status_code` список, `no_log`) - как поведенческая спецификация клиента; `roles/panel/tasks/subpage.yml` 10-34 - как токен-файл читается (но модуль читает `api_token_file` сам, `slurp` НЕ использовать, Anti-pattern).
Заголовки для `module_utils`:
```yaml
    headers:
      X-Forwarded-For: 127.0.0.1
      X-Forwarded-Proto: https
```
Задачи делегируются: `delegate_to: "{{ xvpn_node_panel_host }}"` + `module_defaults` с `api_url: http://127.0.0.1:3000`, `api_token_file: <xvpn_panel_api_token_file>`. Путь токена: `roles/panel/defaults/main.yml` 55 (`{{ xvpn_panel_home }}/secrets/api-token`); на ноде-хосте переменные роли panel не видны, поэтому вынести в `xvpn_node_panel_api_token_file` с тем же дефолтом.
Паттерн блока "wait connected": until/retries как bootstrap.yml 7-32, но внутри модуля (`wait_connected`, `xvpn_node_connect_retries`/`delay`).

### `roles/node/tasks/decommission.yml` (CRUD, absent)

**Analog:** `roles/panel/tasks/subpage.yml` 95-153 (блок "switch off"): сначала stop unit через `systemd_service scope: user` с `become_user` + `XDG_RUNTIME_DIR`, затем `include_role podman_rootless tasks_from: quadlet` со `state: absent` спеком (только если `activate`), иначе `file state=absent` юнит-файла; затем `file state=absent` env-файла; затем route:
```yaml
- name: Panel subpage | remove the subscription-domain route file
  ansible.builtin.include_role:
    name: xvpn.remnawave.edge
    tasks_from: route
  vars:
    xvpn_edge_route_name: subscription
    xvpn_edge_route_state: absent
```
Порядок удаления в Panel: host - node (poll до исчезновения) - config profile (Pitfall 5).

### `roles/node/templates/node-selfsteal.yml.j2` (route)

**Analog:** `roles/panel/templates/subscription-routes.yml.j2` (22 строки; `# {{ ansible_managed }}`, routers `websecure`+`certResolver: le`, http-router `xvpn-to-https` + `noop@internal`). Вызов как `roles/panel/tasks/routes.yml` 3-20: `role_path` разрешить **до** include (`set_fact`), затем
```yaml
- name: Panel | write the Panel-domain route file
  ansible.builtin.include_role:
    name: xvpn.remnawave.edge
    tasks_from: route
  vars:
    xvpn_edge_route_name: panel
    xvpn_edge_route_src: "{{ xvpn_panel_routes_src }}"
```
Для ноды `xvpn_edge_route_name: node-selfsteal` (regex `^[a-z0-9-]+$`), `service: xvpn-decoy`. Контракт имён из `00-edge.yml.j2`: `xvpn-decoy`, `xvpn-to-https`, `le`. Другой Host-трафик: `sniStrict` уже в `00-edge.yml.j2` 3-7 - не дублировать.

### `roles/edge` изменения (decoy templates, STEAL-02/04)

**Analog:** `roles/edge/tasks/main.yml` 96-126 (каталоги `decoy`, `decoy/site`, `decoy/conf.d`, mode 0755/0644; `copy` с `src: role_path/files/decoy/`).
```yaml
- name: Edge | install the decoy site
  ansible.builtin.copy:
    src: "{{ ((xvpn_edge_decoy_src | length) > 0) | ternary(xvpn_edge_decoy_src ~ '/', role_path ~ '/files/decoy/') }}"
    dest: "{{ xvpn_edge_home }}/decoy/site/"
    owner: "{{ xvpn_edge_user }}"
    group: "{{ xvpn_edge_user }}"
    mode: "0644"
    directory_mode: "0755"
```
Изменение: вынести в `tasks/decoy.yml`; выбор источника: `xvpn_edge_decoy_template` > `xvpn_edge_decoy_src` > (нода) hash > текущая страница Panel (байт-в-байт без дрейфа, D-12). Копирование через `community.general.filetree` + `copy` по файлам + `find` prune (RESEARCH Pattern 6). Права: файлы 0644, каталоги 0755 (nginx uid 101). Добавить assert новых переменных в блок `Edge | validate the inputs` (main.yml 2-23) и записи в `argument_specs.yml` (формат `xvpn_edge_decoy_src`, строки 47-50) и `defaults/main.yml` (строка 20). Список шаблонов append-only и отсортирован.
**nginx конфиг:** `decoy-nginx.conf.j2` сейчас catch-all `try_files $uri $uri/ /index.html;` (строка 11). Добавить ветку `try_files $uri $uri/ =404; error_page 404 /404.html;` для шаблонов ноды; дефолт Panel остаётся с catch-all. Рестарт unit после смены конфига уже реализован (main.yml 168-178, `xvpn_edge_decoy_conf is changed`).
**Loopback websecure:** изменений в `traefik.yml.j2` нет: `address: "{{ xvpn_edge_https_address }}"` (строка 38); нода задаёт `xvpn_edge_https_address: 127.0.0.1:8443` через vars play. Assert-regex в main.yml 15-16 уже допускает `127.0.0.1:8443`.

### `playbooks/node.yml` (playbook)

**Analog:** `playbooks/panel.yml` целиком (2 плея: preflight read-only + хост).
```yaml
- name: Panel preflight (read-only)
  hosts: "{{ xvpn_panel_hosts_group | default('remnawave_panel') }}"
  become: true
  gather_facts: true
  any_errors_fatal: true
  tags: [preflight]
  vars:
    xvpn_preflight_domains: >-
      {{ [xvpn_panel_domain] ... }}
  pre_tasks: [assert required domain]
  roles:
    - xvpn.remnawave.preflight
- name: Panel host
  hosts: ...
  vars:
    xvpn_common_firewall_ports: ["80/tcp", "443/tcp"]
    xvpn_podman_rootless_users:
      - name: rw-edge
      - name: rw-panel
  roles: [common, podman_rootless, edge, panel]
```
Для ноды: `hosts: "{{ xvpn_node_hosts_group | default('remnawave_nodes') }}"`, `xvpn_preflight_domains: ["{{ xvpn_node_domain }}"]`, users `rw-edge`, `rw-node`, vars `xvpn_edge_https_address: "127.0.0.1:8443"`, роли `common, podman_rootless, edge, node`. Pre-task assert `xvpn_node_domain | default('') | length > 0`. `playbooks/site.yml`: заменить комментарий `# Phase 3 appends node.yml` на `- name: Node hosts / import_playbook: node.yml` (порядок: panel, затем node; Panel должен быть поднят).

### `scripts/selfsteal/run.sh` + `render.yml` (regression gate)

**Analog:** `scripts/gate/run.sh` (set -euo pipefail, tool-gate, port preflight через `ss`, `mktemp -d` + `trap cleanup`, pinned+sha256 Pebble, `fixture()` из render.yml) и `scripts/gate/render.yml` (рендер production-шаблонов из ролей без ретайпа, фикстуры с `# xvpn-test-fixture: non-secret`).
```bash
for tool in podman curl openssl python3 ansible-playbook sha256sum ss tar; do
  command -v "$tool" >/dev/null 2>&1 || { echo "$tool is required but is not on PATH" >&2; exit 1; }
done
...
TRAEFIK_IMAGE="$(sed -n 's/^xvpn_edge_traefik_image:[[:space:]]*//p' roles/edge/defaults/main.yml)"
```
Pebble sha256 и URL брать из этого же файла (v2.10.3). Добавить: Xray v26.11.9 zip с sha256 из RESEARCH. Вывод: вердикт-строка или `FAIL <case id>`. Новые файлы в `scripts/gate/`-стиле: либо под `scripts/gate/`, либо расширить allowlist-путь в `.gitleaks.toml` (последний `[[allowlists]]`, `paths`).

### `scripts/check.sh` / `check_no_log.py` / `.gitleaks.toml` (modify)

- `check.sh` 74: `grep -Eq 'playbooks/(panel|site)\.yml|xvpn\.remnawave\.edge|traefik\.yml\.j2'` - добавить `node` в группу: `playbooks/(panel|node|site)\.yml`.
- `check_no_log.py` 14-31: добавить в `SENSITIVE` как `r"\bxvpn_node_secret\b"`, `r"\bxvpn_node_secret_key\b"`, `r"\bSECRET_KEY\b"`, `r"\bprivateKey\b"`, имена register'ов токена на ноде; guard автоматически покроет `node.env` по `SECRET_FILE` regex. Не забыть, что self_test декои-задачи уже ссылаются на `node.env.j2`.
- `.gitleaks.toml`: ключи вида `xvpn_node_*secret*` попадают под правило `xvpn-secret-key`; фикстуры в `extensions/molecule/` и `scripts/gate/` с маркером `# xvpn-test-fixture: non-secret`.

### `extensions/molecule/*` (container + vm-e2e)

**Container-tier analog:** `extensions/molecule/container/converge.yml`:
```yaml
- name: Panel host
  ansible.builtin.import_playbook: ../../../playbooks/panel.yml
  vars:
    ansible_pipelining: true
    xvpn_podman_rootless_manage_user_manager: false
    xvpn_common_firewalld_offline: true
    xvpn_preflight_dns_check: false
    xvpn_edge_activate: false
    xvpn_panel_activate: false
    xvpn_edge_acme_ca: staging
```
Для ноды: `import_playbook: ../../../playbooks/node.yml`, `xvpn_node_activate: false`, `xvpn_node_register: false`, `xvpn_node_domain: node.xvpn.test`, `xvpn_edge_acme_ca: staging` (QA-05). Группа платформы `groups: [remnawave_nodes]` (molecule.yml строки 11, 17, 26).
**VM-tier analog:** `extensions/molecule/vm/{molecule.yml,converge.yml,verify.yml,side_effect.yml,tasks/pebble.yml,vars/panel.yml}`: pinned boxes (alma10/rocky10/oracle10 блоки скопировать целиком), `include_vars` в первом плее, `import_playbook`, запись InvocationID/checksum в `/var/lib/xvpn-molecule/` (`copy force: false`), Pebble `tasks/pebble.yml` (переиспользовать, один на VM, `httpPort: 80`). Для двух VM: группы `remnawave_panel` и `remnawave_nodes` в одном `molecule.yml`; `xvpn_node_address` = IP VM (Pitfall 10); `xvpn_edge_acme_ca: custom`, `xvpn_edge_acme_ca_server: https://127.0.0.1:14000/dir`, `xvpn_edge_acme_trusted_ca_file: /etc/pebble/certs/pebble.minica.pem` (vars/panel.yml 8-10).
**Verify analog:** `extensions/molecule/shared/verify_edge.yml` (читает Pebble root, tempfile на контроллере `delegate_to: localhost`, curl с `--resolve`) для `verify_selfsteal.yml`; `verify.yml` строки 20-60 для оркестрации `include_tasks: ../shared/verify_*.yml` с `vars:`. Новые shared-файлы автоматически линтуются (`.ansible-lint` `kinds: tasks: extensions/molecule/shared/*.yml`).

### `meta/runtime.yml` (modify)

Текущее содержимое (`requires_ansible: ">=2.20.0"`). Добавить:
```yaml
action_groups:
  remnawave:
    - remnawave_config_profile
    - remnawave_node
    - remnawave_host
    - remnawave_internal_squad
    - remnawave_node_secret
```
и использовать `module_defaults: group/xvpn.remnawave.remnawave:` в задачах register.

## Shared Patterns

### no_log / diff:false на секретах
**Source:** `roles/panel/tasks/secrets.yml` 235-243, `roles/panel/tasks/stack.yml` 22-31
**Apply to:** все задачи ноды, трогающие SECRET_KEY, Reality privateKey, токен, `node.env`
```yaml
  diff: false
  no_log: true
```
Для route с чувствительным содержимым: `xvpn_edge_route_sensitive: true` (routes.yml 20).

### Деплой Quadlet
**Source:** `roles/panel/tasks/subpage.yml` 49-62 и `roles/edge/tasks/main.yml` 136-151
**Apply to:** `roles/node` (remnanode)
```yaml
- name: ... build the Quadlet specs
  ansible.builtin.set_fact:
    xvpn_node_quadlet_specs:
      - template_src: "{{ role_path }}/templates/remnanode.container.j2"
- name: ... deploy
  ansible.builtin.include_role:
    name: xvpn.remnawave.podman_rootless
    tasks_from: quadlet
  vars:
    xvpn_podman_rootless_quadlet_user: "{{ xvpn_node_user }}"
    xvpn_podman_rootless_quadlet_specs: "{{ xvpn_node_quadlet_specs }}"
    xvpn_podman_rootless_quadlet_activate: "{{ xvpn_node_activate }}"
```
`role_path` разрешается в `set_fact` ДО include (комментарий в edge/main.yml 136-137).

### Рестарт при смене конфигурации
**Source:** `roles/podman_rootless/tasks/restart_stale.yml` (inputs `restart_user/unit/files/changed`), пример `roles/edge/tasks/main.yml` 155-166
**Apply to:** `remnanode.service` после смены `node.env`.

### become в user-scope systemd
**Source:** `roles/podman_rootless/tasks/restart_stale.yml` 56-66
```yaml
  become: true
  become_user: "{{ xvpn_podman_rootless_restart_user }}"
  become_method: ansible.builtin.sudo
  environment:
    XDG_RUNTIME_DIR: "/run/user/{{ ansible_facts['getent_passwd'][xvpn_podman_rootless_restart_user][1] }}"
```
**Apply to:** stop remnanode при decommission, любые `systemctl --user` вызовы.

### Конвенции переменных и argument_specs
**Source:** `roles/panel/defaults/main.yml`, `roles/edge/meta/argument_specs.yml`
Префикс `xvpn_node_*`, у каждой переменной в `defaults` есть запись в `argument_specs` (`description`, `type`, `default`, `choices`), `required: true` для `xvpn_node_domain`. Каждая роль обязана иметь `meta/argument_specs.yml` (check.sh 54-60). `meta/main.yml` копировать с `dependencies: []` (D-09). Внутренние константы - в `vars/main.yml` (не переопределяются). `xvpn_node_home` по образцу `xvpn_panel_home: "{{ xvpn_podman_rootless_home_root | default('/var/lib/xvpn') }}/{{ xvpn_panel_user }}"`.

### Regex в Jinja без обратных слешей
Использовать `\Z`, `[.]` как в `roles/edge/tasks/main.yml` 12-16 и preflight `check_dns`; не вводить `\.`/`\d` (convention проекта).

### Preflight
**Source:** `roles/preflight/tasks/main.yml`, `defaults/main.yml`
`rw-node` уже в `xvpn_preflight_service_users`; домен ноды передаётся через `xvpn_preflight_domains` в preflight-плее `playbooks/node.yml`. Новых изменений в роли не требуется.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `plugins/module_utils/remnawave.py` | utility | request-response | В репозитории нет `plugins/`; планировщик берёт RESEARCH (stdlib `ansible.module_utils.urls.open_url`, нормализация JSON, redaction, loopback-only http) |
| `plugins/modules/remnawave_*.py` (5 шт.) | module | CRUD | Первые Python-модули коллекции; дизайн-референс только внешний (`kenyawest.remnawave`, не зависимость) и поведенческая спека `roles/panel/tasks/bootstrap.yml` |
| `plugins/doc_fragments/remnawave.py` | utility | n/a | Нет аналога |
| `tests/unit/*.py` + fake Panel | test | request-response | Нет `tests/`; стиль self-test для guard-скриптов: `scripts/check_no_log.py` `self_test()` (decoy-кейсы, которые обязаны падать); использовать stdlib `unittest` + `http.server` (pytest - SUS) |
| `roles/node/templates/config-profile.json.j2` | config | transform | Нет JSON-шаблонов; формат из RESEARCH Pattern 2, ключи (`privateKey`, `shortIds`) инжектит модуль, не шаблон |
| `roles/edge/files/decoy-templates/<name>/*` | static asset | n/a | Только одна страница `files/decoy/index.html`; многостраничные шаблоны пишутся с нуля (без CDN) |
| CI workflow для двух-VM e2e | CI | n/a | Ближайшее: `.github/workflows/molecule-vm.yml` (читать при планировании), не разбирался подробно |
| `scripts/selfsteal/` Xray-клиент часть | test | streaming | В `scripts/gate/` нет Xray; брать из RESEARCH (zip + sha256) |

## Metadata

**Analog search scope:** `roles/{edge,panel,common,podman_rootless,preflight}`, `playbooks/`, `scripts/`, `extensions/molecule/`, `meta/`, `.gitleaks.toml`, `.ansible-lint`, `galaxy.yml`
**Files scanned:** ~75 tracked files (список `git ls-files`), около 30 прочитано
**Pattern extraction date:** 2026-11-28
