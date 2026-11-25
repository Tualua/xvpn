# Phase 2: Panel за Traefik с защищённым входом - Context

**Gathered:** 2026-11-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Оператор разворачивает Panel-хост одной командой (`playbooks/panel.yml`). В фазу входит:
- Traefik v3 как rootless Quadlet-сервис под `rw-edge` с ACME HTTP-01 (EDGE-01..03);
- стек Remnawave backend + Postgres + Valkey под `rw-panel` (PANEL-01);
- секреты, которые генерируются один раз (PANEL-02);
- bootstrap первого админа на loopback и долгоживущий API-токен (PANEL-03/04);
- HTTPS на собственном домене (PANEL-05);
- cookie/secret-path гейт админки (PANEL-06);
- subscription page на отдельном домене, подключённая по API-токену (SUB-01/02);
- Pebble в CI (QA-05), `no_log` и assert'ы на placeholder-значения (DOC-04).

Нода, Reality и бэкапы в фазу не входят (фазы 3 и 5).

</domain>

<decisions>
## Implementation Decisions

### Админ-гейт (PANEL-06)
- **D-01:** Точка входа — секретный путь: `https://<panel-domain>/<secret>`. Запрос на него ставит cookie и делает redirect на `/`. Query-параметр не используется. В access log Traefik секретный путь нужно маскировать или исключать; research должен найти, как это сделать.
- **D-02:** Запрос к UI без cookie получает **нейтральную заглушку: статичный сайт с HTTP 200**, а не голый 404. Это осознанное отступление от буквы PANEL-06 и критерия успеха 2 фазы («без cookie отдаётся 404»). В REQUIREMENTS/ROADMAP формулировку нужно поменять на «без cookie отдаётся заглушка, UI и логин недоступны». Заглушку отдаёт тот же decoy-механизм (nginx-unprivileged, контент из переменной/файла), который фаза 3 переиспользует на ноде. — **Reversibility:** reversible — меняется только маршрут Traefik и контент
- **D-03:** Без cookie доступен `/api/*`: внешние интеграции ходят по Bearer-токену. `/api/auth/*` (login/register) и весь UI закрыты cookie. Браузер админа после входа по секретному пути шлёт cookie сам. Исключения для других путей research сверяет с backend 3.4.11: какие префиксы использует frontend и есть ли публичные пути вроде `/api/sub/*`.
- **D-04:** Cookie: флаги `Secure; HttpOnly; SameSite=Strict`. `Max-Age` задаётся переменной, по умолчанию 30 дней.
- **D-05:** Основной вариант — чистый Traefik без плагинов: роутер на секретный путь с middleware (headers/redirect) ставит Set-Cookie и делает 302, проверка cookie идёт через `HeaderRegexp(Cookie, ...)`. Это проверяется ранним спайком. **Заранее разрешённый fallback, без нового решения пользователя:** роутер секретного пути ведёт на decoy-nginx, и уже он отвечает `302 + Set-Cookie`; Traefik при этом только проверяет cookie. Traefik-плагины и отдельные auth-сервисы (forward-auth и т.п.) запрещены: если не сработали ни основной вариант, ни fallback, нужна эскалация через `checkpoint:decision`.
- **D-06:** Секрет гейта (секретный путь и значение cookie) генерируется один раз (D-07); оператор может переопределить его из vault. В конце прогона печатается путь к файлу с секретным URL на Panel-хосте, сам URL не печатается. Секрет гейта разрешено менять свободно, это всего лишь конфиг Traefik (исключение из D-10).

### Секреты и креды (PANEL-02/03/04, DOC-04)
- **D-07:** Секреты Panel (JWT/APP-секреты в том виде, в каком их требует backend 3.4.11; пароль Postgres; metrics-креды; секрет гейта; пароль админа) **хранятся на Panel-хосте**: файл(ы) 0600 в home `rw-panel`, владелец `rw-panel`. Роль сначала читает существующие значения и генерирует только недостающие. На контроллере состояния нет, прогон можно запускать с любой машины. В контейнеры секреты передаются через Podman secrets (`Secret=`) или env-файл, механизм выбирает research. Файл секретов должен попасть в бэкап фазы 5 (OPS-01): это зафиксировано для фазы 5. — **Reversibility:** costly — от расположения и формата файла зависят роль panel, фаза 3 (чтение токена) и бэкапы фазы 5
- **D-08:** Логин первого админа задаётся переменной; дефолт выбирает research, но это не `admin`. Пароль генерируется один раз с учётом политики паролей Remnawave 3.4.11 (длина и классы символов) и хранится вместе с остальными секретами (D-07). Оператор может задать свой пароль в vault. Bootstrap выполняется на loopback до публикации роутера Traefik; повторный прогон логинится, а не регистрирует.
- **D-09:** API-токен лежит в файле 0600 на Panel-хосте. Фаза 3 получает его во время прогона: задачи делегируются на Panel-хост, токен читается через `slurp` с `no_log`, запросы идут на `127.0.0.1:3000`. **На контроллер токен не копируется.** — **Reversibility:** costly — это интерфейс между ролью panel и модулями Panel API фазы 3
- **D-10:** Ротации секретов в v1 нет. Если значение из vault расходится с уже применённым секретом (пароль PG, JWT/APP-секреты, пароль админа), роль падает с понятной ошибкой: что разошлось и почему молча менять нельзя. Исключение — секрет гейта (D-06).
- **D-11:** Все задачи, которые трогают токены, пароли и ключи, выполняются с `no_log: true`. Placeholder-значения (`CHANGE_ME` и т.п., точный список выбирает planner) отвергаются assert'ом (DOC-04).

### Домены, ACME и CI (EDGE-02, EDGE-03, QA-05)
- **D-12:** Домены задаются двумя обязательными полными FQDN: `xvpn_panel_domain` и `xvpn_subscription_domain`. Схемы «базовый домен + префиксы» нет. Оба домена автоматически попадают в preflight DNS-check (`xvpn_preflight_domains`, фаза 1 D-19).
- **D-13:** ACME по умолчанию ходит в **production** Let's Encrypt. Переключатель `staging`/`production` плюс произвольный `caServer` (для Pebble) задаётся переменной (точное имя — на усмотрение planner, например `xvpn_edge_acme_ca`). Email необязателен. `acme.json` персистентный, права 0600.
- **D-14:** Выпуск сертификата и полный стек проверяются e2e в **VM-тире с Pebble**: Pebble и тестовый DNS поднимаются в prepare VM-сценария, production LE из CI никогда не вызывается. VM-тир проверяет HTTPS, гейт (заглушка без cookie, вход по секретному пути, `/api/*` по Bearer), sub-page, реальный IP клиента в access log, `changed=0` на втором прогоне и ноль AVC. Контейнерный тир проверяет рендер конфигов, dry-run Quadlet, логику генерации и чтения секретов и assert'ы.
- **D-15:** На неизвестный SNI Traefik сбрасывает TLS-рукопожатие (`sniStrict`): дефолтный «TRAEFIK DEFAULT CERT» не отдаётся, и по скану IP домен Panel не узнать. На `:80` обслуживаются только ACME challenge и redirect на HTTPS для известных доменов, остальные запросы получают 404.

### Раскладка ролей и playbook
- **D-16:** Отдельная переиспользуемая роль для edge (рабочее имя `edge`; `edge` или `traefik` — выбирает planner) под `rw-edge`. В неё входят Traefik (static config, ACME, file provider, без Podman socket), decoy-nginx и интерфейс добавления маршрутов (routers/services из переменных или drop-in файлов dynamic config). Роли `panel` и позже `node` только добавляют свои маршруты. — **Reversibility:** costly — фаза 3 строит self-steal на интерфейсе маршрутов этой роли
- **D-17:** Subscription page — часть роли `panel`: тот же пользователь `rw-panel` (фаза 1 D-07), та же Podman-сеть, токен из bootstrap той же роли. Отдельный task-файл; включена по умолчанию и выключается переменной.
- **D-18:** Playbook `playbooks/panel.yml` запускает роли в порядке preflight → common → podman_rootless → edge → panel для группы `remnawave_panel` (имя группы переопределяется). Есть и `playbooks/site.yml`, который импортирует `panel.yml`, а в фазе 3 будет импортировать и `node.yml`. Meta-зависимостей между ролями нет (фаза 1 D-09).

### Claude's Discretion
- Как Traefik работает в сети: `Network=host` (EDGE-01, ARCHITECTURE.md) или pasta (строка в CLAUDE.md). Разночтение снимает research. Обязательные условия: реальный IP клиента в access log (EDGE-03), бинд 80/443, доступ к backend и sub-page на `127.0.0.1`.
- Как передавать секреты в контейнеры: Podman `Secret=` или env-файл 0600.
- Формат файла секретов (один файл или несколько; env, YAML или JSON).
- Содержимое заглушки по умолчанию (нейтральный статичный сайт) и как оператор его переопределяет.
- Точные имена переменных в рамках конвенции `xvpn_<role>_*`.
- Как маскировать секретный путь в access log.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Требования и roadmap
- `.planning/REQUIREMENTS.md` — EDGE-01..03, PANEL-01..06, SUB-01/02, QA-05, DOC-04. Формулировку PANEL-06 нужно поменять (D-02).
- `.planning/ROADMAP.md` §Phase 2 — цель, критерии успеха, research flag (спайк гейта; `APP_SECRET` vs JWT-секреты; forwarded-заголовки backend 3.4.11).
- `.planning/PROJECT.md` — ограничения (SELinux enforcing, rootless, Traefik, HTTP-01) и Key Decisions.

### Решения предыдущей фазы
- `.planning/phases/01-rootless-fundament-i-testovyy-stend/01-CONTEXT.md` — D-07 (пользователи `rw-edge`/`rw-panel`), D-08 (home `/var/lib/xvpn`), D-09 (роли без meta-зависимостей), D-10 (развёртывание Quadlet через LSR podman), D-13 (firewalld только добавляет своё), D-19 (`xvpn_preflight_domains`).
- `.planning/phases/01-rootless-fundament-i-testovyy-stend/01-RESEARCH.md` — проверенное поведение LSR podman, Molecule и VM-тира.
- `.planning/phases/01-rootless-fundament-i-testovyy-stend/01-REVIEW-DISPOSITION.md` — открытые follow-up'ы фазы 1.

### Research проекта
- `.planning/research/ARCHITECTURE.md` — топология Panel-хоста, Traefik `Network=host` в `rw-edge`, loopback-публикация backend.
- `.planning/research/PITFALLS.md` — ротация секретов, гонка регистрации админа, forwarded-заголовки, таймауты pull.
- `.planning/research/FEATURES.md` — схема cookie-гейта eGames (референс), bootstrap админа/токена.
- `.planning/research/STACK.md` и `CLAUDE.md` §Technology Stack — закреплённые образы (backend 3.4.11, subscription-page 8.0.1, postgres 18.4, valkey 9-alpine, traefik v3.7.19, nginx-unprivileged 1.31-alpine) и runtime-контракт Remnawave.

### Upstream (читает research)
- `remnawave/backend` `main` / tag 3.4.11: `.env.sample`, `docker-compose-prod.yml`, `libs/contract` (auth register/login, api-tokens).
- `remnawave/subscription-page` 8.0.1: `.env.sample`, `docker-compose-prod.yml`.
- Документация Traefik v3.7: ACME HTTP-01, `caServer`, `tls.options sniStrict`, matchers роутеров (`HeaderRegexp`, `Path`), middleware `headers`/`redirectRegex`, access log.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `roles/podman_rootless/tasks/quadlet.yml`: единый интерфейс развёртывания Quadlet (`xvpn_podman_rootless_quadlet_user`, `xvpn_podman_rootless_quadlet_specs` с абсолютным `template_src`, `xvpn_podman_rootless_quadlet_activate`) с generator dry-run (`quadlet_validate.yml`) поверх `fedora.linux_system_roles.podman`. Роли `edge` и `panel` разворачивают юниты через него.
- `roles/podman_rootless/tasks/user.yml`: создание rootless-пользователей (`xvpn_podman_rootless_users`) с linger и subuid; `rw-panel` добавляется так же, как `rw-edge`.
- `roles/preflight`: DNS-check по `xvpn_preflight_domains`, проверка владельца портов 80/443 (повторный прогон, где 80/443 держит `rw-edge`, не ошибка).
- `roles/common/tasks/firewalld.yml`: паттерн «открыть только свои порты» (80/443 на Panel-хосте).
- `extensions/molecule/{container,vm}` и `extensions/molecule/shared/verify_*.yml`: сценарии и общие verify, к ним добавляются Pebble и e2e-проверки фазы 2.

### Established Patterns
- Переменные `xvpn_<role>_*`, `argument_specs` для каждой роли (FND-06), ansible-lint profile `production`.
- Regex в Jinja без обратных слешей (фаза 1).
- Тестовая фикстура nginx-unprivileged на :80 из фазы 1 (D-12) заменяется Traefik.

### Integration Points
- `playbooks/foundation.yml` и `playbooks/preflight.yml`: новый `playbooks/panel.yml` выстраивает роли в том же порядке.
- `xvpn_preflight_domains` заполняется доменами Panel и sub-page.

</code_context>

<specifics>
## Specific Ideas

- Схема гейта по мотивам eGamesAPI/remnawave-reverse-proxy (секрет → cookie, без cookie — заглушка), но с секретным путём вместо query-параметра и на Traefik вместо nginx.
- Механизм decoy-сайта общий для Panel (заглушка гейта) и Node (self-steal в фазе 3).

</specifics>

<deferred>
## Deferred Ideas

- Файл секретов Panel (D-07) нужно включить в бэкап и restore — фаза 5 (OPS-01/02).
- Ротация секретов — вне v1 (D-10).
- IP allowlist и forward-auth — уже в v2 (PANEL-V2-01/02).
- Subscription page на отдельном хосте — новая топология, вне v1.

</deferred>

---

*Phase: 02-panel-za-traefik-s-zaschischennym-vhodom*
*Context gathered: 2026-11-25*
