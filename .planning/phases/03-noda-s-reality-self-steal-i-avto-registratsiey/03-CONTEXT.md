# Phase 3: Нода с Reality self-steal и авто-регистрацией - Context

**Gathered:** 2026-11-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Оператор добавляет хост в группу нод inventory и запускает `playbooks/node.yml` (или `site.yml`). После прогона:
- remnanode (Xray) работает как rootless Quadlet-сервис под `rw-node` с `Network=host` (NODE-01);
- порт API ноды (2222) открыт только для IP Panel через firewalld rich rule (NODE-02);
- клиент подключается по VLESS Reality (xtls-rprx-vision) на 443 и выходит в интернет (NODE-03);
- Reality `target` указывает на loopback-entrypoint Traefik ноды (роль `edge`), который держит настоящий LE-сертификат домена ноды и отдаёт сайт-заглушку (STEAL-01..05);
- Ansible-модули `remnawave_config_profile`, `remnawave_node`, `remnawave_host`, `remnawave_internal_squad` (check_mode, diff, честный changed) регистрируют ноду в Panel без UI, ждут состояния connected и поддерживают decommission (API-01..05).

Сюда не входят: LAN-инбаунд, LAN-squad и маршрутизация в приватные подсети (фаза 4), бэкапы, hardening, оповещения о сертификатах и документация для публикации (фаза 5).

</domain>

<decisions>
## Implementation Decisions

### Reality-ключи и config profile (API-02, API-03)
- **D-01:** **Каждая нода получает собственный config profile**, по умолчанию с именем ноды. Внутри: её домен в `serverNames`, её x25519-ключи и shortIds. Общего профиля на группу нод нет. LAN-инбаунд фазы 4 добавляется в тот же профиль ноды. — **Reversibility:** costly — от этого зависят модуль профиля, связи host→inbound и squad→inbound, а также структура фазы 4.
- **D-02:** **Источник правды для Reality-ключей и shortIds — Panel.** Ключи генерируются один раз, при первом создании профиля (через keygen/x25519 API Panel либо локально в модуле, способ выбирает research по контракту 3.4.11). При повторных прогонах модуль читает private key и shortIds из существующего профиля и подставляет их в желаемое состояние. Новых ключей он не генерирует. Отдельного файла состояния на хосте ноды и на контроллере нет. Ключи живут в БД Panel, поэтому попадают в её бэкап (фаза 5, OPS-01). — **Reversibility:** costly — при потере БД Panel без бэкапа нужно перевыпускать клиентские конфиги, а смена источника правды потребует миграции.
- **D-03:** **Оператор не может задать свои ключи и shortIds из vault**: они только генерируются. Ротации нет (как Ф2 D-10, API-V2-01 остаётся в v2).
- **D-04:** **Дрейф профиля исправляется приведением к декларации.** Если профиль изменили в UI Panel, модуль перезаписывает его по шаблону коллекции, показывает `--diff` и возвращает `changed=true`. Ключи и shortIds при этом сохраняются из текущего профиля (D-02). Свои изменения оператор вносит через override JSON профиля в inventory (как в REQUIREMENTS Out of Scope: «доступен override JSON профиля»). Чтобы не было ложных `changed`, сравнивается нормализованный JSON.

### Inventory и что видит клиент (API-02, API-05)
- **D-05:** **Нода — это хост группы `remnawave_nodes`** (имя группы переопределяется, как у Panel в Ф2 D-18), её параметры лежат в host_vars. Обязательна одна переменная: `xvpn_node_domain` (полный FQDN). Имя ноды в Panel по умолчанию равно `inventory_hostname`, адрес ноды для Panel по умолчанию равен домену. Оба значения переопределяются. Список нод в group_vars не ведётся. Работает с `--limit <node>`. Домен ноды автоматически попадает в `xvpn_preflight_domains` (Ф1 D-19). — **Reversibility:** costly — это публичный интерфейс inventory для пользователей коллекции.
- **D-06:** **Squad'ы для публичного инбаунда задаются переменной-списком имён**, по умолчанию это дефолтный squad Panel (точное имя в 3.4.11 сверяет research, например `Default-Squad`). Модуль только добавляет инбаунд ноды в перечисленные squad'ы. Чужие инбаунды он из squad'ов не удаляет. Пустой список означает, что инбаунд ни в какой squad не добавляется. Фаза 4 создаёт LAN-squad этим же механизмом.
- **D-07:** **На каждую ноду создаётся один host**: address и SNI равны `xvpn_node_domain`, порт 443, fingerprint `chrome`. Remark по умолчанию равен имени ноды и переопределяется переменной (например, «🇩🇪 Frankfurt»). Ключ идемпотентности (remark или связка профиль+инбаунд) выбирает research по контракту; дубликатов быть не должно (API-03). Списка из нескольких hosts в v1 нет.
- **D-08:** **Decommission** запускается при `state: absent` плюс явном флаге подтверждения (рабочее имя `xvpn_node_decommission_confirm: true`; без флага роль падает с понятной ошибкой). Из Panel удаляются node, её hosts и её config profile, а инбаунд — из squad'ов. На хосте ноды останавливаются и удаляются Quadlet-юниты remnanode, удаляется self-steal маршрут edge (`tasks_from: route`, `state: absent`) и закрываются порты, которые открыла роль (443, rich rule 2222). **Остаются** пользователи `rw-node`/`rw-edge`, их home, ACME-хранилище и образы: их удаляет оператор. — **Reversibility:** reversible — после удаления нода регистрируется заново обычным прогоном, но с новыми ключами (D-02), поэтому клиентам нужно перевыдать конфиги.

### Сайт-заглушка (STEAL-02, STEAL-04)
- **D-09:** **Коллекция поставляет 3–4 встроенных многостраничных шаблона**, например портфолио студии, личный блог, лендинг малого бизнеса и страницу «идут работы». В каждом шаблоне 2–4 страницы, свой CSS, favicon, `robots.txt` и настоящая страница 404. Внешних CDN и ресурсов нет, всё отдаётся локально. Заголовок или имя бренда подставляется переменной.
- **D-10:** **Если шаблон не задан, он выбирается детерминированно по хешу `xvpn_node_domain`.** Разные ноды по умолчанию получают разные сайты, а выбор стабилен между прогонами (`changed=0`). Явный выбор шаблона в host_vars имеет приоритет.
- **D-11:** **Свой сайт оператор задаёт каталогом на контроллере**, тем же механизмом, что `xvpn_edge_decoy_src` в Ф2. Статика копируется идемпотентно, лишние файлы удаляются, каталог можно задать для каждой ноды. Загрузки архивов по URL нет.
- **D-12:** **Шаблоны лежат в роли `edge` и общие для Panel-гейта и ноды** (развитие Ф2 D-02 «общий decoy-механизм»). Заглушку гейта на Panel тоже можно выбрать из шаблонов. **Дефолт на Panel не меняется**: остаётся текущая страница `roles/edge/files/decoy/index.html`, чтобы конфиги уже развёрнутых Panel не дрейфовали.

### Self-steal на Traefik и запасной план (STEAL-01, STEAL-03, STEAL-05)
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Требования и roadmap
- `.planning/REQUIREMENTS.md` — NODE-01..03, STEAL-01..05, API-01..05; Out of Scope (override JSON профиля, пользователи и подписки не создаются).
- `.planning/ROADMAP.md` §Phase 3 — цель, критерии успеха, research flag (HIGH RISK спайк Reality → Traefik loopback; REST-контракт из OpenAPI backend 3.4.11; `NET_ADMIN`/SELinux для `container_t`).
- `.planning/PROJECT.md` — ограничения и Key Decisions (Traefik для self-steal проверяется в фазе 3).
- `.planning/STATE.md` §Blockers/Concerns — риски фазы 3.

### Решения предыдущих фаз
- `.planning/phases/01-rootless-fundament-i-testovyy-stend/01-CONTEXT.md` — D-07 (`rw-node`), D-08 (home `/var/lib/xvpn`), D-09 (роли без meta-зависимостей), D-10 (Quadlet через LSR podman), D-13 (firewalld только добавляет своё; 2222/8443 снаружи закрыты), D-19 (`xvpn_preflight_domains`), D-20 (AVC эскалируется).
- `.planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-CONTEXT.md` — D-02 (общий decoy-механизм), D-05 (паттерн эскалации через checkpoint), D-09 (токен на Panel-хосте, `slurp` + `no_log`, `127.0.0.1:3000`), D-10/D-11 (без ротации, `no_log`, placeholder-assert'ы), D-13/D-14 (ACME CA, Pebble в VM-тире), D-15 (`sniStrict`, :80 только ACME+redirect), D-16 (роль edge и интерфейс маршрутов), D-18 (`site.yml` импортирует `node.yml`), D-19 (access log без пути).
- `.planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-RESEARCH.md` — проверенное поведение Traefik v3.7.20, file provider watch (A6), ACME store на CA.

### Research проекта
- `.planning/research/ARCHITECTURE.md` — `node_registration`, `plugins/modules` + `module_utils`, передача данных между хостами через делегирование, два инбаунда в одном профиле (на будущее для фазы 4).
- `.planning/research/FEATURES.md` — авто-регистрация (keygen → node → SECRET_KEY), config profile/hosts/squads, self-steal, референсы vff-remnawave-auto и eGamesAPI.
- `.planning/research/PITFALLS.md` — подводные камни Reality, rootless, SELinux.
- `.planning/research/STACK.md` и `CLAUDE.md` §Technology Stack — пины `remnawave/node` 3.4.6, Traefik, nginx-unprivileged; оценка пригодности Traefik для self-steal.

### Upstream (читает research)
- `remnawave/backend` tag 3.4.11: `libs/contract` (keygen, config-profiles, nodes, hosts, internal-squads, x25519), OpenAPI.
- `remnawave/node` 3.4.6: `docker-compose-prod.yml`, `.env.sample` (`SECRET_KEY`, `NODE_PORT`).
- Xray Reality docs: https://xtls.github.io/en/config/transports/reality.html (`target`/`dest`, `serverNames`, `xver`, shortIds).
- Traefik v3.7: entrypoints на loopback, `tls.options` (`sniStrict`, minVersion, ALPN), `proxyProtocol`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `roles/edge` (`tasks/main.yml`, `tasks/route.yml`, `templates/traefik.yml.j2`, `templates/xvpn-decoy.container.j2`, `files/decoy/index.html`) — Traefik + decoy-nginx под `rw-edge`. Адреса задаются переменными `xvpn_edge_http_address`/`xvpn_edge_https_address`, свой сайт — `xvpn_edge_decoy_src`. Drop-in маршруты подключаются через `tasks_from: route` (`xvpn_edge_route_name/src/state/sensitive`) и подхватываются без рестарта (file provider `watch: true`).
- `roles/podman_rootless/tasks/quadlet.yml` и `tasks/user.yml` — развёртывание Quadlet с generator dry-run и создание `rw-node` с linger/subuid.
- `roles/panel` — чтение API-токена с Panel-хоста (Ф2 D-09), образец для делегированных API-вызовов.
- `roles/preflight` — DNS-check (домен ноды) и проверка владельцев портов 80/443.
- `roles/common/tasks/firewalld.yml` — паттерн «открыть только свои порты» (сюда добавляются 443 и rich rule 2222 только с IP Panel).
- `extensions/molecule/{container,vm}` и `shared/verify_*.yml`, Pebble из Ф2 — сюда добавляются сценарий ноды и e2e.

### Established Patterns
- Переменные `xvpn_<role>_*`, `argument_specs` на каждую роль, ansible-lint profile `production`, regex в Jinja без обратных слешей.
- `no_log: true` на всём, что трогает токены и ключи; gitleaks-сканирование (Ф2 D-20) — фикстуры только с маркером `# xvpn-test-fixture: non-secret`.
- Секреты генерируются один раз и не ротируются; при расхождении роль падает.
- Образы закреплены точным тегом, `:latest` отвергается assert'ом.

### Integration Points
- `playbooks/site.yml` (комментарий «Phase 3 appends node.yml») → новый `playbooks/node.yml`: preflight → common → podman_rootless → edge → node для группы `remnawave_nodes`. Регистрация в Panel требует, чтобы Panel уже был поднят.
- `plugins/modules/` и `plugins/module_utils/` коллекции появляются впервые.

</code_context>

<specifics>
## Specific Ideas

- У разных нод должны быть разные сайты-заглушки, чтобы их не связали по одинаковой странице. Отсюда детерминированный выбор по домену.
- Reality-ключи не должны лежать в нескольких местах: Panel — единственный источник правды.
- Модули должны вести себя как обычные декларативные Ansible-ресурсы: diff, check_mode, приведение к декларации.

</specifics>

<deferred>
## Deferred Ideas

- Ротация Reality-ключей и shortIds: v2 (API-V2-01).
- Несколько hosts на ноду (разные remark, адреса, fingerprint): после v1, если попросит сообщество.
- Загрузка сайта-заглушки архивом по URL: не в v1.
- Полная очистка хоста при decommission (пользователи, данные, образы): остаётся на операторе.
- Бэкап БД Panel с Reality-ключами: фаза 5 (OPS-01). Важно: без него потеря Panel означает перевыдачу клиентских конфигов.

</deferred>

---

*Phase: 03-noda-s-reality-self-steal-i-avto-registratsiey*
*Context gathered: 2026-11-28*
