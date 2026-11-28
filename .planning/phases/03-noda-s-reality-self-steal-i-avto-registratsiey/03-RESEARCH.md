# Phase 3: Нода с Reality self-steal и авто-регистрацией - Research

**Researched:** 2026-11-28
**Domain:** Remnawave Node (Xray VLESS Reality self-steal) on rootless Podman/Quadlet behind a loopback Traefik, plus a Remnawave Panel REST API client delivered as Ansible modules
**Confidence:** HIGH for the self-steal path (executed spike) and the REST contract (read from the 3.4.11 source); MEDIUM for rootless/SELinux behaviour of `remnanode` (cannot be executed here, VM tier must prove it)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Reality-ключи и config profile (API-02, API-03)
- **D-01:** **Каждая нода получает собственный config profile**, по умолчанию с именем ноды. Внутри: её домен в `serverNames`, её x25519-ключи и shortIds. Общего профиля на группу нод нет. LAN-инбаунд фазы 4 добавляется в тот же профиль ноды. — **Reversibility:** costly — от этого зависят модуль профиля, связи host→inbound и squad→inbound, а также структура фазы 4.
- **D-02:** **Источник правды для Reality-ключей и shortIds — Panel.** Ключи генерируются один раз, при первом создании профиля (через keygen/x25519 API Panel либо локально в модуле, способ выбирает research по контракту 3.4.11). При повторных прогонах модуль читает private key и shortIds из существующего профиля и подставляет их в желаемое состояние. Новых ключей он не генерирует. Отдельного файла состояния на хосте ноды и на контроллере нет. Ключи живут в БД Panel, поэтому попадают в её бэкап (фаза 5, OPS-01). — **Reversibility:** costly — при потере БД Panel без бэкапа нужно перевыпускать клиентские конфиги, а смена источника правды потребует миграции.
- **D-03:** **Оператор не может задать свои ключи и shortIds из vault**: они только генерируются. Ротации нет (как Ф2 D-10, API-V2-01 остаётся в v2).
- **D-04:** **Дрейф профиля исправляется приведением к декларации.** Если профиль изменили в UI Panel, модуль перезаписывает его по шаблону коллекции, показывает `--diff` и возвращает `changed=true`. Ключи и shortIds при этом сохраняются из текущего профиля (D-02). Свои изменения оператор вносит через override JSON профиля в inventory (как в REQUIREMENTS Out of Scope: «доступен override JSON профиля»). Чтобы не было ложных `changed`, сравнивается нормализованный JSON.

#### Inventory и что видит клиент (API-02, API-05)
- **D-05:** **Нода — это хост группы `remnawave_nodes`** (имя группы переопределяется, как у Panel в Ф2 D-18), её параметры лежат в host_vars. Обязательна одна переменная: `xvpn_node_domain` (полный FQDN). Имя ноды в Panel по умолчанию равно `inventory_hostname`, адрес ноды для Panel по умолчанию равен домену. Оба значения переопределяются. Список нод в group_vars не ведётся. Работает с `--limit <node>`. Домен ноды автоматически попадает в `xvpn_preflight_domains` (Ф1 D-19). — **Reversibility:** costly — это публичный интерфейс inventory для пользователей коллекции.
- **D-06:** **Squad'ы для публичного инбаунда задаются переменной-списком имён**, по умолчанию это дефолтный squad Panel (точное имя в 3.4.11 сверяет research, например `Default-Squad`). Модуль только добавляет инбаунд ноды в перечисленные squad'ы. Чужие инбаунды он из squad'ов не удаляет. Пустой список означает, что инбаунд ни в какой squad не добавляется. Фаза 4 создаёт LAN-squad этим же механизмом.
- **D-07:** **На каждую ноду создаётся один host**: address и SNI равны `xvpn_node_domain`, порт 443, fingerprint `chrome`. Remark по умолчанию равен имени ноды и переопределяется переменной (например, «🇩🇪 Frankfurt»). Ключ идемпотентности (remark или связка профиль+инбаунд) выбирает research по контракту; дубликатов быть не должно (API-03). Списка из нескольких hosts в v1 нет.
- **D-08:** **Decommission** запускается при `state: absent` плюс явном флаге подтверждения (рабочее имя `xvpn_node_decommission_confirm: true`; без флага роль падает с понятной ошибкой). Из Panel удаляются node, её hosts и её config profile, а инбаунд — из squad'ов. На хосте ноды останавливаются и удаляются Quadlet-юниты remnanode, удаляется self-steal маршрут edge (`tasks_from: route`, `state: absent`) и закрываются порты, которые открыла роль (443, rich rule 2222). **Остаются** пользователи `rw-node`/`rw-edge`, их home, ACME-хранилище и образы: их удаляет оператор. — **Reversibility:** reversible — после удаления нода регистрируется заново обычным прогоном, но с новыми ключами (D-02), поэтому клиентам нужно перевыдать конфиги.

#### Сайт-заглушка (STEAL-02, STEAL-04)
- **D-09:** **Коллекция поставляет 3–4 встроенных многостраничных шаблона**, например портфолио студии, личный блог, лендинг малого бизнеса и страницу «идут работы». В каждом шаблоне 2–4 страницы, свой CSS, favicon, `robots.txt` и настоящая страница 404. Внешних CDN и ресурсов нет, всё отдаётся локально. Заголовок или имя бренда подставляется переменной.
- **D-10:** **Если шаблон не задан, он выбирается детерминированно по хешу `xvpn_node_domain`.** Разные ноды по умолчанию получают разные сайты, а выбор стабилен между прогонами (`changed=0`). Явный выбор шаблона в host_vars имеет приоритет.
- **D-11:** **Свой сайт оператор задаёт каталогом на контроллере**, тем же механизмом, что `xvpn_edge_decoy_src` в Ф2. Статика копируется идемпотентно, лишние файлы удаляются, каталог можно задать для каждой ноды. Загрузки архивов по URL нет.
- **D-12:** **Шаблоны лежат в роли `edge` и общие для Panel-гейта и ноды** (развитие Ф2 D-02 «общий decoy-механизм»). Заглушку гейта на Panel тоже можно выбрать из шаблонов. **Дефолт на Panel не меняется**: остаётся текущая страница `roles/edge/files/decoy/index.html`, чтобы конфиги уже развёрнутых Panel не дрейфовали.

#### Self-steal на Traefik и запасной план (STEAL-01, STEAL-03, STEAL-05)
- **D-13:** **На ноде websecure-entrypoint роли `edge` слушает только loopback** (`xvpn_edge_https_address` = `127.0.0.1:8443` или порт, который выберет спайк). В firewalld этот порт не открывается. На `:80` обслуживаются только ACME HTTP-01 и redirect на https для домена ноды (как Ф2 D-15). Заглушка по plain HTTP не отдаётся. Роль `edge` переиспользуется без форка: отличия ноды задаются переменными и drop-in маршрутом.
- **D-14:** **Фаза начинается со спайка.** Он проверяет Reality → Traefik `127.0.0.1:8443`: TLS 1.3 и h2, `xver: 0` по умолчанию, поведение при чужом или пустом SNI (STEAL-03: не показывать дефолтный сертификат и 404 Traefik, `sniStrict`) и выпуск сертификата по HTTP-01 на :80, когда 443 занят Xray. Внутри Traefik можно перебирать варианты: другой loopback-порт, `xver: 1` + `proxyProtocol.trustedIPs=127.0.0.1/32`, `tls.options`. **Заранее разрешённого перехода на nginx или Caddy нет.** Если вариантов внутри Traefik не хватило, исполнитель останавливается и эскалирует через `checkpoint:decision` с доказательствами из спайка (как Ф2 D-05). — **Reversibility:** costly — смена TLS-терминатора на ноде меняет роль edge и контракт self-steal.
- **D-15:** (из ROADMAP/STEAL-05, фиксируется явно) Reality-инбаунд включается или регистрируется активным только после того, как сертификат ноды выпущен и проверен пробой через loopback-entrypoint с SNI домена ноды.

### Claude's Discretion
- Что делает playbook, если нода не перешла в состояние connected за отведённое число попыток (API-04): fail с диагностикой (рекомендуется) или warning; сколько попыток и какой интервал.
- Блокировать ли `geoip:private` для публичного инбаунда уже в фазе 3 или оставить это фазе 4 (LAN-03). Решать с учётом того, что фаза 4 добавит правило LAN-инбаунда перед блоком.
- Как проверить клиента в VM-тире (NODE-03): Xray-клиент в контейнере или на контроллере, через Pebble-сертификат.
- Где выполняются вызовы API: делегирование на Panel-хост и `127.0.0.1:3000` (Ф2 D-09) или иначе, если это обоснует research. Токен на контроллер не попадает.
- Общий `module_utils` для HTTP-клиента Remnawave, обработка ошибок и таймауты, формат diff.
- Точные имена переменных в конвенции `xvpn_node_*` / `xvpn_edge_*` и имя новой роли (`node`).
- Нужны ли `NET_ADMIN` и SELinux boolean `container_connect_any`. Включать только по доказанному AVC, иначе эскалация (Ф1 D-20, FND-05).
- Как передать `SECRET_KEY` в remnanode: env-файл 0600 или Podman secret (по аналогии с Ф2).
- Набор shortIds (количество, длина) и параметры Reality-инбаунда (fingerprint, `spiderX` и т.п.) по рекомендациям Xray.

### Deferred Ideas (OUT OF SCOPE)
- Ротация Reality-ключей и shortIds: v2 (API-V2-01).
- Несколько hosts на ноду (разные remark, адреса, fingerprint): после v1, если попросит сообщество.
- Загрузка сайта-заглушки архивом по URL: не в v1.
- Полная очистка хоста при decommission (пользователи, данные, образы): остаётся на операторе.
- Бэкап БД Panel с Reality-ключами: фаза 5 (OPS-01). Важно: без него потеря Panel означает перевыдачу клиентских конфигов.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NODE-01 | remnanode (Xray) as rootless Quadlet service with host network | `remnawave/node:3.4.6` env contract (`NODE_PORT`, `SECRET_KEY`), no `NET_ADMIN`, `Ulimit nofile=524288`, Quadlet skeleton in Code Examples |
| NODE-02 | Node API port 2222 reachable only from the Panel IP | firewalld rich rule via `ansible.posix.firewalld` (works offline); Panel-IP discovery rules and `--limit` pitfall |
| NODE-03 | Client connects with VLESS Reality (xtls-rprx-vision) on 443 and reaches the internet | Spike: real Xray 26.11.9 client through Reality to Traefik loopback target; freedom `finalRules` default blocks private destinations (test sink hook) |
| STEAL-01 | Reality target = loopback Traefik entrypoint with a real LE certificate | Spike results (TLS1.3, h2, `xver` 0 and 1, ACME HTTP-01 with websecure on loopback); edge variables |
| STEAL-02 | Plausible site with a valid certificate for scanners | Decoy template mechanism (hash selection, strict 404, prune of extra files), probe results |
| STEAL-03 | Foreign/absent SNI does not reveal the default certificate or Traefik 404 | Executed: `sniStrict` yields TLS alert 112 and no certificate, both directly and through Reality; verify recipe |
| STEAL-04 | Choice of built-in templates or a custom directory | Template layout in `roles/edge/files/`, deterministic selection filter, filetree copy + prune |
| STEAL-05 | Reality inbound only after the certificate is issued and verified | Ordering: cert gate -> start remnanode -> register profile (inbound exists only after gate); 443 is closed until registration |
| API-01 | Modules with check_mode, diff and honest `changed` | Module design (names instead of UUIDs, normalized-JSON diff, redaction), stdlib HTTP client, fake-Panel unit tests |
| API-02 | Node auto-registered: profile, node, SECRET_KEY, hosts | Verified endpoint contract of 3.4.11, registration sequence, keygen semantics |
| API-03 | Re-run creates no duplicates and keeps keys/shortIds (`changed=0`) | Natural keys (names, tags), Panel-side config mutations to pre-apply, key preservation algorithm |
| API-04 | Wait for connected with bounded retries | `GET /api/nodes` fields, 10 s health-check cron, recommended retry budget, diagnostics |
| API-05 | Decommission with explicit flag | Deletion order and async node deletion, host orphaning on profile delete, node-host cleanup list |
</phase_requirements>

## Summary

The decisive risk of the phase (Reality -> Traefik TLS on loopback) is **resolved in favour of Traefik**: I executed it in this session with the exact pinned binaries (Traefik v3.7.20, Xray-core v26.11.9 which is the core inside `remnawave/node:3.4.6`, Pebble v2.10.3). A real Xray Reality+Vision client reached a "private" sink through Xray, scanners got the decoy over TLS 1.3 + h2 with a Pebble-issued, fully verified certificate for the node domain, and unknown or absent SNI produced a TLS `unrecognized_name` alert with no certificate at all (no `TRAEFIK DEFAULT CERT`, no `404 page not found`). ACME HTTP-01 worked with `websecure` bound to `127.0.0.1` only. No `checkpoint:decision` about replacing Traefik is needed; the planner should keep the escalation clause only as a regression tripwire.

Four findings change the plan versus the CONTEXT assumptions: (1) the Reality server dials the target on **every** client handshake, so Traefik availability and a correct `xver`/`proxyProtocol` pairing are part of the VPN data path; (2) Xray 26.11.9 `freedom` blocks private/reserved destinations (including loopback) for VLESS inbounds **by default**, so LAN-03 is default-deny already, and both the NODE-03 test sink and Phase 4's LAN access need `finalRules` allow entries; (3) `GET /api/keygen` returns a **fresh node certificate on every call**, so `SECRET_KEY` must be fetched once and persisted on the node host (the node cert is valid 3 years); (4) `PATCH /api/config-profiles` restarts every node on the profile whenever a `config` is sent, Postgres JSONB reorders keys, and the Panel rewrites `settings.clients` to `[]`, so the module must pre-apply the Panel's mutations and compare normalized JSON before writing.

`NET_ADMIN` and `container_connect_any` are both **not needed**: `CAP_NET_ADMIN` only gates the node's optional nftables plugin and its absence is a logged warning, and container-selinux 2.250.0 puts `container_t` into `corenet_unconfined`. A Galaxy search found three Remnawave collections; the only API-module one (`kenyawest.remnawave` 1.6.0) is 18 days old with one author, so the recommendation is to write the four required modules in this collection and use that repository only as a design reference.

**Primary recommendation:** Reuse the edge role unchanged except for variables and a node drop-in route, gate the Panel registration on a loopback TLS probe, fetch `SECRET_KEY` once, and implement the four `remnawave_*` modules as stdlib-only, name-addressed, normalized-JSON modules executed on the Panel host against `127.0.0.1:3000` reading the token from a file on that host; convert the executed spike into a native regression gate (`scripts/selfsteal/`) before building anything on top.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Reality inbound on 443 | Node host: `remnanode` (Xray, `Network=host`) | Panel (owns the config) | Xray binds 443 in the host netns; the config lives in the Panel DB and is pushed to the node |
| TLS termination and real LE certificate for the node domain | Node host: Traefik (`rw-edge`) on `127.0.0.1:8443` | ACME CA over :80 | Reality only forwards to it; HTTP-01 needs :80 on the same host |
| Decoy site | Node host: nginx-unprivileged behind Traefik | Controller (template source) | Traefik cannot serve static files; content is copied from the collection or an operator directory |
| Panel API access control for node port 2222 | Node host: firewalld rich rule | Node API mTLS + JWT (upstream) | Network layer limits to the Panel IP; the application layer authenticates anyway |
| Reality keys and shortIds | Panel DB (source of truth, D-02) | Module (generate-once via Panel x25519 tool) | No state file elsewhere; backed up with the Panel DB in Phase 5 |
| Registration logic (profile, squad, node, host, wait) | Ansible module on the Panel host (`delegate_to`) | Node role (orchestration) | Token never leaves the Panel host; API listens on loopback only |
| `SECRET_KEY` handoff | Panel API -> controller memory (`no_log`) -> node host env file 0600 | - | Two different hosts; unavoidable in-memory hop, generate-once |
| Client reachability checks | Controller / Panel VM (test only) | - | Verify tier probes from outside |

## Standard Stack

### Core
| Library / Image | Version | Purpose | Why Standard |
|-----------------|---------|---------|--------------|
| `docker.io/remnawave/node` | **3.4.6** (Docker Hub tags: `3.4.6`, `3.4.5`, `latest`, `dev`; Latest release 2026-11-14) | remnanode with Xray-core v26.11.9 inside | Pinned pair with backend 3.4.11 (lockstep 3.4.x); upstream compose uses `:latest`, never default to it |
| `docker.io/library/traefik` | **v3.7.20** (already the edge default) | Loopback TLS terminator for self-steal | Spike-verified in this session |
| `docker.io/nginxinc/nginx-unprivileged` | 1.31-alpine (already the edge default) | Decoy backend | Existing edge role |
| ansible-core | 2.21 primary, 2.22 installed locally | Engine | Project stack |
| `ansible.posix` | 2.2.2 | `firewalld` rich rules, `seboolean` (not needed) | Already pinned in requirements.yml |
| `community.general` | 14.0.1 | `filetree` lookup for decoy copy + prune | Already pinned; plugin present at `community/general/plugins/lookup/filetree.py` |
| `ansible.builtin` (module_utils `urls`) | core | HTTP client of the new modules | Stdlib-based, no `requests`, works on target Python 3.12 |

### Supporting (test tier only, not installed by roles)
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| Xray-core release `Xray-linux-64.zip` | v26.11.9, sha256 `b651f7e1d9966ee2c1b1ee1bf8b52c72771824d3065dce96bbc8bcc19ed95f82` (matches the published `.dgst`) | Real Reality client and native server for the regression gate and the VM e2e | Same core version as the node image |
| Pebble + pebble-challtestsrv | v2.10.3 (sha256 values already pinned in `extensions/molecule/vm/tasks/pebble.yml`) | Mock ACME CA | Reuse the Phase 2 tasks; run one Pebble per VM |
| Python `unittest` + `unittest.mock` + stdlib `http.server` | stdlib | Unit tests of the modules against a fake Panel | Container tier cannot run a real Panel |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Own `remnawave_*` modules | `kenyawest.remnawave` 1.6.0 (MIT repo, GPL-3 headers; modules `config_profile`, `node`, `host`, `internal_squad`, full check/diff) | 1 star, single author, first published 2026-11-10, no key-preservation semantics (D-02/D-04) and API-01 names modules in this collection; adopting adds a supply-chain dependency on an admin-token-bearing component. Use as design reference only. [VERIFIED: Galaxy API + GitHub repo listing] |
| Own modules | `ilyagulya.remnawave` 0.1.0 (2026-01-22), `lagomvpn.remnawave` 1.0.0 (Docker node role, 2025-09) | Older API generation / Docker based, not applicable |
| Stdlib `unittest` | `pytest` | pytest returns verdict SUS from the legitimacy seam (`unknown-downloads` only, repo `pytest-dev/pytest`); stdlib avoids the new dependency and the checkpoint |
| Env file 0600 for `SECRET_KEY` | Podman secret | Env file matches the Phase 2 pattern (`EnvironmentFile=`, 0600, `no_log`), no extra moving part |

**Installation:** nothing new at runtime. Dev: no new pip lines if `unittest` is used.

**Version verification:** `gh release list -R remnawave/node` -> 3.4.6 Latest (2026-11-14); `gh release list -R remnawave/backend` -> 3.4.11 Latest (2026-11-14); `gh release view v3.7.20 -R traefik/traefik` assets and checksums file; Docker Hub tags API for `remnawave/node`. [VERIFIED: GitHub CLI / Docker Hub API, 2026-11-28]

## Package Legitimacy Audit

No new package from a package registry is installed by any role. Test-time binaries are release tarballs verified by sha256.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| pytest (optional only) | PyPI | many yrs | unknown to the seam | github.com/pytest-dev/pytest | SUS (`unknown-downloads` only) | Not recommended; if the planner chooses it, add `checkpoint:human-verify` before adding it to requirements-dev.txt |
| kenyawest.remnawave 1.6.0 | Galaxy | 18 days | n/a | github.com/Kenya-West/remnawave-ansible-collection | not run through the seam (Galaxy not covered) | Evaluated and NOT adopted (see Alternatives) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** pytest (optional, avoided by using stdlib `unittest`)

## Architecture Patterns

### System Architecture Diagram

```
 Operator inventory (host_vars: xvpn_node_domain ...)            Panel host (rw-panel, 127.0.0.1:3000)
        |                                                          ^        ^
        v                                                          | token  | HTTP + X-Forwarded-* headers
 playbooks/node.yml (hosts: remnawave_nodes)                       | file   |
   1 preflight (domain A-record, ports 80/443 free)                |   remnawave_* modules (delegate_to: Panel host,
   2 common (firewalld: 80/tcp, 443/tcp)                            |   run as root, read api token file locally)
   3 podman_rootless (rw-edge, rw-node)                             |        ^
   4 edge: Traefik web :80 (ACME HTTP-01 + redirect)                |        | profile -> squads -> node -> host -> wait connected
             websecure 127.0.0.1:8443 (sniStrict, TLS1.3, h2)       |        |
             node route (Host(node-domain) -> decoy)                |  7 node role (registration part, delegated)
   5 CERT GATE: openssl s_client 127.0.0.1:8443 -servername domain -+  
        |  (ok)                                                     
        v                                                           
   6 node role: SECRET_KEY generate-once --(keygen via module)--> Panel
        env file 0600 -> remnanode.container (rw-node, Network=host, no caps)
        firewalld rich rule: Panel IP -> 2222/tcp
        |                                                                       
 Internet client --443--> Xray (remnanode) --Reality auth ok--> VLESS/Vision --> freedom outbound (finalRules)
                              |  no auth / wrong SNI / no SNI (raw TLS relay)
                              +--target 127.0.0.1:8443--> Traefik --valid SNI--> decoy site (200, LE cert)
                                                                   --other SNI--> TLS alert 112, no certificate
 NOTE: for EVERY connection (also authenticated clients) Xray first dials the target to mirror its ServerHello:
       Traefik down => clients fail too (executed).
```

### Recommended Project Structure
```
roles/
├── edge/                         # extended, not forked (D-12, D-13)
│   ├── files/decoy/index.html    # unchanged Panel default (no drift)
│   ├── files/decoy-templates/<name>/...   # 3-4 sites: pages, css, favicon.ico, robots.txt, 404.html
│   ├── templates/decoy-nginx.conf.j2      # add strict mode (real 404) next to the catch-all mode
│   └── tasks/decoy.yml           # select template, copy via filetree, prune extras
├── node/                         # new role (name: node)
│   ├── defaults/ vars/ meta/argument_specs.yml
│   ├── tasks/main.yml            # present/absent dispatch, asserts
│   ├── tasks/gate.yml            # STEAL-05 loopback cert probe
│   ├── tasks/secret.yml          # generate-once SECRET_KEY
│   ├── tasks/firewall.yml        # rich rule 2222, 443
│   ├── tasks/register.yml        # profile -> squads -> node -> host -> wait
│   ├── tasks/decommission.yml
│   └── templates/{remnanode.container.j2, node.env.j2, node-selfsteal.yml.j2, config-profile.json.j2}
plugins/
├── modules/{remnawave_config_profile,remnawave_node,remnawave_host,remnawave_internal_squad,remnawave_node_secret}.py
├── module_utils/remnawave.py     # client, normalize, redact, error mapping
└── doc_fragments/remnawave.py
meta/runtime.yml                  # add action_groups so tasks use module_defaults
playbooks/node.yml                # site.yml appends import_playbook: node.yml
scripts/selfsteal/run.sh          # regression gate from the executed spike (native binaries or podman)
tests/unit/                       # unittest + fake Panel (stdlib http.server)
extensions/molecule/{container,vm-e2e}  # node render scenario; two-VM Panel+Node e2e
```

### Pattern 1: Loopback self-steal on the existing edge (spike-verified)
**What:** set `xvpn_edge_https_address: 127.0.0.1:8443`, keep `xvpn_edge_http_address: ":80"`; the existing `00-edge.yml.j2` already provides `sniStrict: true`, `minVersion: VersionTLS12`, the `xvpn-decoy` service and the `xvpn-to-https` middleware. The node role adds one drop-in (`tasks_from: route`) with a TLS router for `Host(<domain>)` and an HTTP redirect router.
**When to use:** every node host.
**Executed evidence:** TLS 1.3, ALPN `h2`, issuer `Pebble Intermediate CA`, `Verification: OK`, `Verified peername: node.test` through the Xray port; HTTP: `301 -> https://node.test/` for the known host, `404` for an unknown host.
**Example (route drop-in, the rendered shape that was executed):**
```yaml
# node-selfsteal.yml.j2  (source: spike in this session, Traefik v3.7.20)
http:
  routers:
    xvpn-node-https:
      entryPoints: [websecure]
      rule: "Host(`{{ xvpn_node_domain }}`)"
      service: xvpn-decoy
      tls:
        certResolver: le
    xvpn-node-http:
      entryPoints: [web]
      rule: "Host(`{{ xvpn_node_domain }}`)"
      middlewares: [xvpn-to-https]
      service: noop@internal
```

### Pattern 2: Config profile desired state (Panel-normalised form)
**What:** the role renders the desired JSON without keys; the module injects `privateKey` and `shortIds` (preserved from the stored profile, or generated once) and compares normalized JSON.
```json
{
  "log": {"loglevel": "warning"},
  "inbounds": [{
    "tag": "vless-reality-<sanitized-node-name>",
    "port": 443,
    "protocol": "vless",
    "settings": {"clients": [], "decryption": "none"},
    "streamSettings": {
      "network": "tcp",
      "security": "reality",
      "realitySettings": {
        "show": false,
        "target": "127.0.0.1:8443",
        "xver": 0,
        "serverNames": ["<node-domain>"],
        "privateKey": "<managed by module>",
        "shortIds": ["<managed by module>"]
      }
    },
    "sniffing": {"enabled": true, "destOverride": ["http", "tls", "quic"]}
  }],
  "outbounds": [
    {"tag": "DIRECT", "protocol": "freedom", "settings": {"finalRules": []}},
    {"tag": "BLOCK", "protocol": "blackhole"}
  ],
  "routing": {"rules": [{"type": "field", "ip": ["geoip:private"], "outboundTag": "BLOCK"}]}
}
```
`flow` is not written: the Panel derives `xtls-rprx-vision` for `reality` + `tcp|raw` (`getVlessFlow`). The Panel derives the **public key itself** from `privateKey` (`resolveInboundAndPublicKey`) and puts `shortIds[0]` plus `serverNames[0]` into client links, so nothing else must be stored. `network: tcp` was executed on 26.11.9; `raw` was not tested.

### Pattern 3: Registration sequence (all calls on the Panel host, names not UUIDs)
1. `remnawave_config_profile` (state present): GET list, match by `name`; build desired (+ preserved/generated keys); diff normalized; POST or PATCH; returns profile uuid and inbound uuids by tag.
2. `remnawave_internal_squad` for each name in `xvpn_node_squads`: GET list; ensure the inbound uuid is in the squad (union, never remove foreign); PATCH replaces the whole set, so send current + ours. Create the squad if missing (not for the reserved `Default-Squad`, which always exists).
3. `remnawave_node`: key `name`; fields address, port, countryCode, `configProfile {activeConfigProfileUuid, activeInbounds}`; `wait_connected` with retries inside the module.
4. `remnawave_host`: bound to the node's inbound; see Pattern 5 for the idempotency key.
Addressing by `config_profile: <name>` and `inbound: <tag>` (resolved inside the module) keeps `--check` working when the profile does not exist yet (report "would create", never fail on a missing uuid).

### Pattern 4: Generate-once `SECRET_KEY`
`GET /api/keygen` returns `{response: {secretKey}}` and builds a new node certificate on every call. Fetch it only when `~rw-node/env/node.env` is missing (module `remnawave_node_secret`, read-only, `no_log` result), write the file 0600 with `no_log` and `diff: false`, and never refetch. Deleting the file is the documented way to re-key. Restart the unit with the existing `restart_stale` task when the env file changes.

### Pattern 5: Host idempotency key (answers D-07)
Match the node's host as: hosts whose `inbound.configProfileUuid` equals the node's profile. Exactly one -> update it (remark is a managed field, so renaming the remark var does not duplicate). None -> create. More than one -> match by `remark`, else fail with a message (never create a second). Host has no unique constraint in the DB (`remark` is not unique), so this rule is the only duplicate guard. Defaults: `address` and `sni` = node domain, `port` 443, `fingerprint` `chrome`, `securityLayer` `DEFAULT`.

### Pattern 6: Decoy templates (D-09..D-12)
Selection: explicit `xvpn_edge_decoy_template` wins; else `xvpn_edge_decoy_src`; else for the node role `templates[(domain | hash('sha256'))[:8] | int(base=16) % templates | length]`; Panel default stays the current single page. Keep the template list **append-only and sorted**, otherwise adding a template re-maps existing nodes (drift). Node templates need `try_files $uri $uri/ =404` plus `error_page 404 /404.html`; the Panel catch-all mode (every path 200) stays for the default page. `ansible.builtin.copy` of a directory never deletes extras (D-11 requires deletion): copy file by file from `lookup('community.general.filetree', ...)` and prune with `find` against the desired list, files `0644`, dirs `0755` (nginx runs as uid 101 in the userns).

### Anti-Patterns to Avoid
- **Chaining registered UUIDs between tasks:** breaks `--check` for new resources; use names and tags.
- **`ansible.builtin.uri` chains for registration:** the Phase 2 bootstrap tolerates them for a one-off token, but profile/node/host need diff, redaction and normalization; keep them in modules.
- **Fetching the token with `slurp`:** puts the long-lived token into controller memory; let the module read `api_token_file` on the Panel host.
- **Deleting a config profile before its hosts:** `Hosts.config_profile_inbound_uuid` is `onDelete: SetNull`, hosts become orphans (verified in `prisma/schema.prisma`).
- **Sending `config` on every run:** each PATCH with `config` restarts all nodes of the profile.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| x25519 keypair | local crypto in the module | `GET /api/system/tools/x25519/generate` (30 keypairs, base64url without padding, same encoding as Xray) | No `cryptography` dependency on targets; the Panel then derives the public key with the same implementation |
| JSON key ordering | custom ordering rules | recursive `json.dumps(sort_keys=True)` on both sides | Postgres JSONB does not keep key order; only top-level order is touched by the Panel's `sortXrayConfig` |
| HTTP client | `requests`/curl subprocess | `ansible.module_utils.urls.open_url` | In core, proxies/timeouts/TLS handled |
| Firewall source restriction | `firewall-cmd` shell | `ansible.posix.firewalld` with `rich_rule` (check mode, offline permanent config supported by the module source) | Idempotent |
| Directory sync of the decoy | `ansible.posix.synchronize` | `filetree` lookup + `copy` + `find` prune | `synchronize` needs rsync on target and controller and sudo plumbing |
| ACME | custom certbot | Traefik `le` resolver (already in edge) | Phase 2 |
| Waiting for a certificate | sleep loops | `until` + `openssl s_client` with bounded retries (not combined with `set_fact`, see `scripts/check_until_set_fact.py`) | Matches existing guard |

**Key insight:** the registration is a small declarative reconciliation loop over four resource kinds; everything fragile (ordering, normalisation, duplicate protection) belongs in one tested module_utils, not in YAML.

## Common Pitfalls

### Pitfall 1: Traefik is in the data path of every Reality handshake
**What goes wrong:** with Traefik stopped, an authenticated client fails (curl via SOCKS `rc=56`); with `xver: 1` and a Traefik entrypoint without `proxyProtocol`, both scanners and real clients fail. **Why:** the Reality server dials `target` for every incoming connection to mirror its ServerHello. **Avoid:** `Restart=always` on Traefik, keep `xver: 0` default; if `xver: 1` is exposed it must set `proxyProtocol.trustedIPs: [127.0.0.1/32]` on the websecure entrypoint in the same change; verify must include a client e2e, not only a scanner probe. **Evidence:** executed (xver mismatch and Traefik down both broke the client; restart restored it from the stored `acme.json`). Boot ordering across users (`rw-edge` vs `rw-node`) cannot be expressed in systemd, so a few seconds of failure after reboot are expected.

### Pitfall 2: Xray `freedom` blocks private and reserved destinations by default
**What goes wrong:** the client authenticates but the connection to a private sink times out; the server log shows `target blocked by a finalrule: tcp:127.0.0.1:18090, blackholing connection for 43s`. **Why:** documented fallback policy: VLESS/VMess/Trojan/Shadowsocks/Hysteria/WireGuard inbound traffic blocks private and reserved IP ranges unless an explicit rule matches. **Consequences:** (a) the NODE-03 test needs either public egress or an explicit `finalRules` allow for the sink (planning resolved this through the operator override `xvpn_node_profile_override`, see Open Question 3 (RESOLVED); Phase 4 adds its LAN `finalRules` allow the same way); (b) LAN-03 is default-deny even without the `geoip:private` routing rule, so the explicit BLOCK rule is belt and braces only; (c) Phase 4 must add allow `finalRules`, not only a routing rule. **Evidence:** executed on 26.11.9 for loopback; private ranges beyond loopback are from the docs. [CITED: xtls.github.io/en/config/outbounds/freedom.html]

### Pitfall 3: `GET /api/keygen` is not stable
**What goes wrong:** calling it every run changes `SECRET_KEY` every run, restarting remnanode on each run (breaks `changed=0`) . **How to avoid:** fetch only if the node env file is absent. **Also:** the node certificate inside the payload is valid 3 years (`notAfter ... + 3` in `generate-certs.util.ts`, CA 10 years); schedule an ops note for Phase 5 and document the re-key procedure (delete the env file, re-run). **Warning sign:** node env file mtime changes between runs.

### Pitfall 4: Config profile PATCH side effects and server-side mutations
- Any PATCH containing `config` triggers `startAllNodesByProfile` (restart) and cache invalidation: write only on a normalized diff.
- On update the Panel calls `cleanInboundClients(false)` (sets `settings.clients = []` for vless/trojan/shadowsocks/hysteria), `fixIncorrectServerNames()` (splits comma lists, dedupes) and `validateOutbounds()` (a config without outbounds is rejected on update). Pre-apply the same transformations to the desired JSON or the diff never converges.
- Create validates only inbounds; update additionally requires non-empty `outbounds`. Always render outbounds.
- Names: profile `^[A-Za-z0-9_\s-]+$`, 2..30 chars, **no dots**; `Default-Profile` is reserved; node `name` 3..30 chars, unique, **address unique**; inbound `tag` is unique across **all** profiles and may not contain a comma. A default `inventory_hostname` such as `node1.example.com` breaks the profile name rule: sanitize for the profile (`regex_replace('[^A-Za-z0-9_ -]', '-')`) and assert lengths with a message naming the override variable.

### Pitfall 5: Deleting things in the wrong order (decommission)
`DELETE /api/nodes/{uuid}` only queues a stop job (`isNeedToBeDeleted: true`); poll `GET /api/nodes` until the node is gone before deleting the profile. Delete the host first (SetNull orphans otherwise). Inbound removal from squads happens by cascade when the profile is deleted (`InternalSquadInbounds` onDelete Cascade); no squad PATCH needed (it would restart nodes for nothing).

### Pitfall 6: Squad PATCH replaces the full inbound set
`PATCH /api/internal-squads {uuid, inbounds[]}` calls `cleanInbounds` then `createInbounds`. Read the current inbound uuids, union with ours. A new inbound belongs to **no** squad until the module adds it (the default seed only covers the default profile), so users get nothing from a fresh node unless `xvpn_node_squads` is respected. `Default-Squad` cannot be created (reserved) but exists after install.

### Pitfall 7: Secrets in diff and results
`--diff` before/after of a profile contains `privateKey`. Redact `privateKey` (and any key matching `(?i)(private|secret|password|seed)`) in both sides and in `invocation`; `no_log` on token params; the controller sees `SECRET_KEY` only through a `no_log` task result. No fact caching is configured (`ansible.cfg` has none), so `set_fact` of a secret is memory only.

### Pitfall 8: Panel IP for the rich rule and `--limit`
With `--limit node1` facts of the Panel host are absent. Resolve in this order: explicit `xvpn_node_panel_sources` (list of IPs/CIDRs, NAT/multi-IP Panels), else `xvpn_public_ip` of the Panel host, else delegated `setup` with `gather_subset: [network]` and `delegate_facts: true`. Validate with a regex before it enters the rich rule string; the rule is `rule family="ipv4" source address="<ip>" port port="2222" protocol="tcp" accept`.

### Pitfall 9: Rootless limits
`Ulimit=nofile=1048576` (upstream) failed for rootless db in Phase 2 and was lowered to `524288` (the systemd user-manager hard limit). Use `524288:524288` for remnanode. Do not add `AddCapability=NET_ADMIN`: in a rootless container the capability would be scoped to the user namespace and gives nothing in the host netns; the node only warns without it.

### Pitfall 10: Panel backend resolving the node domain from a container
In the VM tier the node domain resolves through `/etc/hosts` on the Panel VM. Whether a rootless Podman container sees host `/etc/hosts` entries is not verified. Set `xvpn_node_address` to the node VM IP in the e2e scenario and keep SNI/host fields on the domain; production default stays the domain (D-05).

### Pitfall 11: Repository gates that must be extended
`scripts/check_no_log.py` `SENSITIVE` list needs the new variable/register names (node secret, reality keys, api token vars used by the node role). `scripts/check.sh` `check_acme_ca` greps converge files for `playbooks/(panel|site)\.yml|xvpn\.remnawave\.edge|traefik\.yml\.j2`; a node scenario using `playbooks/node.yml` would escape the QA-05 production-CA guard, add `node` to the regex. `.gitleaks.toml` flags any literal 12+ char value under `xvpn_*secret*|password|token|cookie_value|gate_path` keys: fixtures need `# xvpn-test-fixture: non-secret` in `extensions/molecule/` or `scripts/gate/`; put new native-gate fixtures under `scripts/gate/` or extend that allowlist path deliberately. Never paste real-looking Reality private keys in docs or tests.

### Pitfall 12: Residual fingerprints that are accepted
`http://<node-ip>/` answers Traefik's plain `404 page not found` for an unknown Host (Phase 2 D-15 behaviour, `:80` serves only ACME + redirect); foreign/absent SNI on 443 ends in alert 112 rather than a page. Both are locked by D-13/Phase 2 and are consistent with "no default certificate". `server_tokens off` is already set in the decoy nginx.

## Code Examples

### Remnanode Quadlet (shape, keys per Phase 2 conventions)
```ini
# remnanode.container.j2  (rw-node)
[Unit]
Description=xvpn Remnawave node (Xray)

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
`node.env` (0600, `no_log`, `diff: false`): `NODE_PORT=2222` and `SECRET_KEY=<payload>` as a raw value without quotes (Podman `--env-file` takes the value literally; to be confirmed in the VM tier, see A1).

### Cert gate (STEAL-05), probe on loopback with the node SNI
```bash
echo | openssl s_client -connect 127.0.0.1:8443 -servername "$DOMAIN" -verify_hostname "$DOMAIN" 2>&1 \
  | grep -E 'subject=|Protocol|ALPN|Verif'
# production: add -verify_return_error (system roots). Test CAs: -CAfile <pebble root>
```
Gate = handshake succeeds (with `sniStrict` a missing certificate cannot complete a handshake) and the peer certificate SAN contains the domain. Retries bounded (for example 30 x 5 s) with a failure message that mentions ACME staging/rate limits, DNS and port 80 reachability.

### Scanner / STEAL-03 verify recipe (from the spike, run on the controller)
```bash
# valid SNI through Reality: certificate for the domain, TLS1.3, ALPN h2, HTTP 200 decoy
curl -sk --resolve "$DOMAIN:443:$NODE_IP" "https://$DOMAIN/" -o /dev/null -w '%{http_code} %{http_version}\n'
# foreign SNI and no SNI: handshake alert, no certificate
echo | openssl s_client -connect "$NODE_IP:443" -servername evil.invalid 2>&1 | grep -E 'alert number 112|no peer certificate'
echo | openssl s_client -connect "$NODE_IP:443" -noservername 2>&1 | grep -E 'alert number 112|no peer certificate'
# assert the output contains neither "TRAEFIK DEFAULT CERT" nor "404 page not found"
```
Observed: `SSL alert number 112`, `no peer certificate available`, `New, (NONE)`; Xray logs `REALITY: processed invalid connection ... server name mismatch` and relays the raw connection to Traefik.

### API contract (read from tag 3.4.11, `libs/contract`)
- Base `ROOT = '/api'`; controllers `config-profiles`, `nodes`, `hosts`, `internal-squads`, `keygen`, `system` (`tools/x25519/generate`, `metadata`). All accept `ROLE.ADMIN, ROLE.API`; scope guard accepts the `*` wildcard the Phase 2 token carries.
- Profile create body `{name, config}`; update `{uuid, name?, config?}` (PATCH); delete by `/{uuid}`; list returns `{response: {total, configProfiles[]}}` with `config` and `inbounds[{uuid, profileUuid, tag, ...}]`.
- Node create `{name (3..30), address, port?, countryCode='XX', isTrafficTrackingActive=false, configProfile: {activeConfigProfileUuid, activeInbounds[]}, ...}`; update PATCH `{uuid, ...}`; list `GET /api/nodes` -> `response[]` with `isConnected`, `isConnecting`, `isDisabled`, `lastStatusMessage`, `configProfile.activeInbounds[]`.
- Host create `{inbound: {configProfileUuid, configProfileInboundUuid}, remark (1..100), address, port, sni?, fingerprint?, ...}`; update PATCH `{uuid, ...}`; list `GET /api/hosts` -> `response[]`.
- Squad create `{name, inbounds[]}`, update PATCH `{uuid, name?, inbounds?}`, list `response.internalSquads[]` each with `inbounds[]`.
- Errors carry `code` (for example `A011` node not found, `A033`/`A034` name/address exists, `A111` profile not found, `A113` duplicate tag, `A114` duplicate profile name).
- Panel version for a pin check: `GET /api/system/metadata` -> `response.version`.

### Module task shape (check-mode safe, runs on the Panel host)
```yaml
- name: Node register | config profile
  xvpn.remnawave.remnawave_config_profile:
    name: "{{ xvpn_node_profile_name }}"
    config: "{{ lookup('ansible.builtin.template', 'config-profile.json.j2') | from_json }}"
    managed_reality:
      - inbound: "{{ xvpn_node_inbound_tag }}"
        short_ids: 2
        short_id_length: 16
  delegate_to: "{{ xvpn_node_panel_host }}"
  register: xvpn_node_profile
```
Module defaults carry `api_url: http://127.0.0.1:3000` and `api_token_file`; headers sent by the client: `Authorization: Bearer`, `X-Forwarded-For: 127.0.0.1`, `X-Forwarded-Proto: https` (Phase 2 Pitfall 1; the admin-JWT-only header `X-Remnawave-Client-Type` is not needed for API tokens). Refuse a non-loopback `http://` URL so a token never travels in clear text.

### Firewall (node role)
```yaml
- name: Node firewall | allow the Panel to reach the node API
  ansible.posix.firewalld:
    zone: "{{ xvpn_common_fw_zone }}"
    rich_rule: 'rule family="ipv4" source address="{{ item }}" port port="{{ xvpn_node_api_port }}" protocol="tcp" accept'
    permanent: true
    immediate: "{{ not xvpn_common_firewalld_offline }}"
    offline: "{{ xvpn_common_firewalld_offline }}"
    state: enabled
  loop: "{{ xvpn_node_panel_sources }}"
```
Read: `ansible.posix` 2.2.2 `firewalld.py` `RichRuleTransaction` (lines 642-690 normalise the rule through `Rich_Rule` before comparing, so the task is idempotent). A negative test needs no extra VM: connect to 2222 from the controller (not the Panel IP) and expect failure, then from the Panel VM and expect success.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| nginx/Caddy on a unix socket as Reality target (`xver: 1`) | Traefik on loopback TCP works (executed) | this research | Keeps the project's Traefik decision |
| Xray `dest` | `target` (both accepted; `target` used in the executed config) | Xray 2025/26 | Use `target` |
| `xray x25519` prints `Public key` | prints `Password (PublicKey)` and `Hash32` | Xray 26.x | Do not parse CLI output; use the Panel API tool |
| freedom allows everything | freedom blocks private/reserved for proxy inbounds unless `finalRules` allow | Xray 26.x | Phase 4 LAN needs `finalRules`; tests need a sink rule |
| Compose `network_mode: host` + `NET_ADMIN` | host net, no caps in rootless | - | `NET_ADMIN` only for the optional nftables plugin |

**Deprecated/outdated:** docs pages about `inbounds` on nodes (Remnawave v1); this phase uses the v2+ model (config profiles, internal squads, hosts).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Podman `--env-file` treats `SECRET_KEY=<base64 payload>` literally (no quote handling needed, line length is fine for ~4 KB) | Code Examples | remnanode fails to start with "Invalid SECRET_KEY payload"; VM tier catches it, fallback Podman secret |
| A2 | Rootless containers see host `/etc/hosts` entries | Pitfall 10 | VM-tier node never connects if `xvpn_node_address` is a name; mitigated by using the IP in tests |
| A3 | `remnawave/node:3.4.6` runs rootless with `Network=host`, no caps, `container_t`, 0 AVC | Summary | Needs an SELinux boolean or an extra capability; escalate per D-20 (policy shows no port denial for `container_t`, remaining risk is file/device access inside the image) |
| A4 | Private/reserved ranges beyond loopback (RFC1918, link-local) are blocked by the default freedom fallback | Pitfall 2 | Docs-based; loopback was executed. If private ranges were allowed, the explicit `geoip:private` BLOCK rule becomes the only guard, so keep it |
| A5 | Rootless `Ulimit=nofile=524288` is accepted for the node like for db/backend | Pitfall 9 | Unit start fails; lower or drop the key |
| A6 | `network: raw` would also work with Panel 3.4.11 and Xray 26.11.9 | Pattern 2 | Not used; `tcp` executed |
| A7 | Panel (backend container) default outbound resolver reaches the node domain in production DNS | Pitfall 10 | Operator DNS issue, not a collection issue |

## Open Questions (RESOLVED)

All four questions were settled during planning; the decision and the plan that carries it are recorded per question.

1. **API-04 failure policy** — RESOLVED
   - Known: Panel health-check cron runs every 10 s (`NODE_HEALTH_CHECK: CronExpression.EVERY_10_SECONDS`), a freshly created node is started through a queue.
   - RESOLVED: the run fails with diagnostics (node `isConnecting`/`isDisabled`/`lastStatusMessage` plus hints for the 2222 rich rule, `remnanode.service` and `node.env`), it never only warns; budget 30 x 5 s through `xvpn_node_connect_retries` / `xvpn_node_connect_delay`. Carried by Plan 03-12 (`remnawave_node` `wait_connected`, VM case `node-not-connected`).
2. **`geoip:private` in Phase 3?** — RESOLVED
   - Known: default-deny exists via `finalRules` fallback; explicit routing BLOCK is cheap.
   - RESOLVED: the explicit BLOCK is included now as the last routing rule, but as an explicit CIDR list `xvpn_node_blocked_cidrs` in `roles/node/vars/main.yml` (loopback, RFC1918, CGNAT, link-local, ULA, IPv6 loopback/link-local) instead of `geoip:private`, so the block does not depend on a geo database inside the node image. Phase 4 prepends its LAN allow rule before it and adds its own `finalRules` allow on a LAN outbound. Carried by Plan 03-10 (profile template) and proven by Plan 03-13 (negatives `client-private-node`, `client-private-lan`).
3. **Test sink for NODE-03** — RESOLVED
   - RESOLVED: Xray client (v26.11.9, sha256-pinned) on the Panel VM; the deterministic sink is a loopback HTTP server on the **node** VM (`127.0.0.1:18090`, unit `xvpn-molecule-sink.service`), because a loopback sink on the node is exactly the destination class the private block must otherwise deny. The allow for that sink is supplied through the existing operator override `xvpn_node_profile_override` in `extensions/molecule/node-vm/vars/node-vm.yml` (DIRECT freedom `settings.finalRules` allowing only `127.0.0.1/32` port 18090, plus a routing rule for the sink placed before the BLOCK rule). No dedicated `xvpn_node_freedom_final_rules` variable is introduced (the name in Pitfall 2 is superseded by the override mechanism of D-04). Negative checks: the same client cannot reach `127.0.0.1:22` on the node nor the Panel VM private address. Public egress (`https://github.com`) is run as an additional case `client-public` because CI runners have egress; a network outage shows as that case failing, not as a collection defect. Carried by Plan 03-13.
4. **Whether to surface the `kenyawest.remnawave` decision to the user** — RESOLVED
   - Memory says prefer maintained Galaxy components. It was checked and rejected (young, single author, wrong semantics, API-01 names our modules).
   - RESOLVED: no `checkpoint:decision`; the choice is recorded as a `<reversibility rating="costly">` block on Plan 03-05 Task 1 (own `remnawave_*` modules; switching later means rewriting `register.yml`, not migrating data).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| ansible-core / ansible-lint | all | yes (dev box) | 2.22.0 locally, CI pins 2.21 | - |
| Podman, molecule, rpm | container tier, VM tier | no on this dev box | - | CI only (GitHub runner); local checks = ansible-lint + unit tests + native spike binaries |
| Traefik, Xray, Pebble native binaries | self-steal regression gate | yes via pinned release downloads (executed here) | v3.7.20, 26.11.9, 2.10.3 | podman variant like `scripts/gate/run.sh` |
| libvirt/KVM with Vagrant | VM e2e | CI runner only | per workflow | none |
| openssl CLI on controller | verify probes | yes | 3.5.5 | - |
| Internet from the node VM | image pull | yes in CI | - | - |

**Missing dependencies with no fallback:** none for planning. **Missing with fallback:** Podman/SELinux proof exists only in the VM tier.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Panel API token (Phase 2), node mTLS + JWT from `SECRET_KEY`; token read from a 0600 file on the Panel host |
| V3 Session Management | no | - |
| V4 Access Control | yes | firewalld rich rule 2222 to Panel IP only; 8443 never opened; token scope `*` (least-privilege scopes are a Phase 5 hardening note) |
| V5 Input Validation | yes | domain regex (reuse the Phase 2 FQDN regex before it enters Traefik rules), name/tag regexes from the contract, IP/CIDR regex before the rich rule, loopback-only `http://` for the API URL |
| V6 Cryptography | yes | keys from the Panel tool, TLS from Traefik/LE, no hand-rolled crypto; secrets 0600 |
| V8 Data Protection | yes | `no_log`, `diff: false`, diff redaction of `privateKey` |
| V14 Configuration | yes | pinned image tags (assert rejects `latest`), no SELinux relaxation |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Reality private key or SECRET_KEY in logs/diff | Information Disclosure | redaction + `no_log` + env file 0600 |
| Node control port reachable from the internet | Elevation / Tampering | rich rule, verify from a non-Panel address |
| Default certificate or Traefik 404 reveals the stack | Information Disclosure | `sniStrict` (alert 112), per-domain template choice |
| Traefik rule injection through the domain variable | Tampering | strict FQDN assert before rendering backticked `Host()` |
| Token sent in clear to a remote URL | Information Disclosure | module refuses non-loopback `http://` |
| LAN or loopback reachable by ordinary clients | Elevation | freedom default fallback plus explicit `geoip:private` BLOCK |
| Duplicate/rotated keys on re-run | Denial of Service (clients dropped) | key preservation from the Panel, diff-before-write |

## Project Constraints (from CLAUDE.md)

- Communication with the user in Russian; code, paths, prompts to subagents in English.
- Platform Rocky/Alma 10 only (Oracle Linux 10 added by a quick task); SELinux enforcing, never permissive; no `SecurityLabelDisable`, no `--privileged`, no `setenforce 0`.
- Rootless Podman + Quadlet, no Docker; Traefik for proxying (decision is confirmed again by the spike); Let's Encrypt HTTP-01 on :80; Panel and nodes on separate hosts.
- Idempotence, Molecule + CI, ansible-lint profile `production`; public open-source collection, so README/examples remain a Phase 5 duty.
- `containers.podman` Quadlet via `fedora.linux_system_roles.podman` through `roles/podman_rootless/tasks/quadlet.yml` (Phase 1 D-10); do not use `.pod`/`.kube`/AutoUpdate.
- Work enters through GSD commands only; no direct edits outside a GSD workflow.
- Memory: prefer existing maintained Galaxy components (evaluated above).

## Plan Decomposition Guidance (3 plans from ROADMAP, may be split)

1. **03-01 Self-steal foundation (Wave 1):** commit the spike as `scripts/selfsteal/` regression gate (native pinned Traefik + Xray + Pebble; cases: Vision client e2e, valid SNI 200 + h2 + verified chain, foreign SNI alert, no SNI alert, Traefik-down failure semantics, optional `xver: 1` with `proxyProtocol`); edge role changes: decoy templates + selection + strict 404 + prune, argument_specs for new `xvpn_edge_decoy_*` variables, container-tier render test; keep Panel default byte-identical (no drift test).
2. **03-02 Node role (Wave 2):** user `rw-node`, firewall (443/tcp, rich rule), env file, `remnanode.container`, cert gate, `playbooks/node.yml`, `site.yml` import, preflight wiring (`xvpn_preflight_domains` from the node domain), argument_specs, `check_no_log.py`/`check.sh` extensions, container-tier node scenario (render + generator dry-run, `xvpn_node_register: false`).
3. **03-03 API modules and e2e (Wave 3):** module_utils + five modules + doc fragment + `meta/runtime.yml` action group, unit tests with a fake Panel, `register.yml`/`decommission.yml`, two-VM e2e scenario (Panel VM + node VM per platform; Pebble on each VM; user created by the verify via `POST /api/users` with `expireAt`, `vlessUuid` and `activeInternalSquads`; client config from the subscription link or from known values), idempotence `changed=0`, `--check`/`--diff` runs, decommission case, SELinux 0-AVC check on both users.

## Sources

### Primary (HIGH confidence)
- Executed spike (this session, scratchpad): Traefik v3.7.20 (sha256 checked against `traefik_v3.7.20_checksums.txt`), Xray-core v26.11.9 (sha256 equals the published `.dgst`), Pebble v2.10.3 + challtestsrv (hashes equal the Phase 2 pins): Reality->Traefik loopback, SNI matrix, xver 0/1, proxyProtocol, ACME HTTP-01 with websecure on loopback, Traefik-down behaviour, freedom `finalRules` block.
- `remnawave/backend` tag 3.4.11 source: `libs/contract/api/routes.ts` and `api/controllers/*.ts`, `commands/{config-profiles,nodes,hosts,internal-squads,keygen,system,users}/*.ts`, `models/*.ts`, `src/modules/config-profiles/config-profile.service.ts`, `src/modules/internal-squads/internal-squad.service.ts`, `src/modules/nodes/nodes.service.ts`, `src/modules/keygen/keygen.service.ts`, `src/common/helpers/xray-config/*.ts`, `src/common/utils/flow/get-vless-flow.ts`, `src/scheduler/intervals.ts`, `prisma/schema.prisma`, `prisma/seed/*`.
- `remnawave/node` tag 3.4.6: `docker-compose-prod.yml`, `.env.sample`, `docker/Dockerfile` (Xray `v26.11.9`), `src/common/config/app-config/config.schema.ts`, `src/modules/handler/handler.service.ts`, `src/main.ts`.
- container-selinux `container.te` at v2.250.0 (the EL10 version in STACK.md): line 962 `typeattribute container_t container_domain, container_net_domain, container_user_domain;`, line 1140 `corenet_unconfined(container_t)`, lines 1158-1159 `corenet_tcp_bind_all_ports(container_net_domain)` / `corenet_tcp_connect_all_ports(container_net_domain)`; the `container_connect_any` tunable (line 804 area on main) only widens `container_runtime_domain`.
- `ansible.posix` 2.2.2 `plugins/modules/firewalld.py` (rich rule transaction, offline handling) read from `.ansible/collections`.
- This repository: `roles/edge/**`, `roles/panel/**`, `roles/common/tasks/firewalld.yml`, `roles/podman_rootless/**`, `roles/preflight/**`, `playbooks/*.yml`, `extensions/molecule/**`, `scripts/**`, `.gitleaks.toml`, Phase 1-2 summaries (`Ulimit=nofile` finding).

### Secondary (MEDIUM confidence)
- [Xray freedom outbound docs (finalRules)](https://xtls.github.io/en/config/outbounds/freedom.html): default fallback policy text; introduction version not stated.
- Galaxy API v3 search and version metadata for `kenyawest.remnawave`, `ilyagulya.remnawave`, `lagomvpn.remnawave`; GitHub repo listings (licence, activity).

### Tertiary (LOW confidence)
- None relied upon for decisions; assumptions are listed in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, versions confirmed against GitHub/Docker Hub on 2026-11-28.
- Architecture: HIGH for self-steal and API sequence (executed + source), MEDIUM for rootless/SELinux behaviour of the node image (VM tier decides).
- Pitfalls: HIGH for items marked executed or read from source; A1-A7 flagged.

**Research date:** 2026-11-28
**Valid until:** 2026-12-12 (Remnawave 3.4.x patch releases land weekly; re-read the contract diff before bumping the pins)
