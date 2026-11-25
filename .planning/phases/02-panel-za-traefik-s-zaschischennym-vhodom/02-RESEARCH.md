# Phase 2: Panel за Traefik с защищённым входом - Research

**Researched:** 2026-11-25
**Domain:** Traefik v3.7 rootless edge (ACME HTTP-01, file provider, cookie/secret-path gate), Remnawave backend 3.4.11 + subscription-page 8.0.1 runtime contract, generate-once secrets, loopback admin/API-token bootstrap, Pebble-based e2e in the Molecule VM tier
**Confidence:** HIGH for the gate design, Traefik behaviour, Remnawave env/API contract and bootstrap state machine (all executed or read from upstream source this session); MEDIUM for Podman 6 networking details; LOW-MEDIUM for SELinux outcomes (can only be proven by AVC in an enforcing VM, flagged as spikes)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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

### Deferred Ideas (OUT OF SCOPE)
- Файл секретов Panel (D-07) нужно включить в бэкап и restore — фаза 5 (OPS-01/02).
- Ротация секретов — вне v1 (D-10).
- IP allowlist и forward-auth — уже в v2 (PANEL-V2-01/02).
- Subscription page на отдельном хосте — новая топология, вне v1.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EDGE-01 | Traefik v3 rootless Quadlet, host network, file provider, no Podman socket | `Network=host` chosen (see Network decision); file provider with `watch: true` on a bind-mounted directory; Spike S1 ran Traefik 3.7.19 with the file provider |
| EDGE-02 | Let's Encrypt HTTP-01 on :80, staging/production switch, persistent `acme.json` | Spike S2: Traefik 3.7.19 + Pebble 2.10.3 issued a cert via HTTP-01 from file-provider routers; `caServer` + `LEGO_CA_CERTIFICATES` for Pebble; `acme.json` mode 0600 |
| EDGE-03 | Real client IP in access log | `Network=host` (no NAT); JSON access log; untrusted `X-Forwarded-*` are overwritten (spike); verify recipe in Code Examples |
| PANEL-01 | backend + Postgres + Valkey as Quadlet on a private network with healthchecks/order | Compose contract from upstream `docker-compose-prod.yml`; Quadlet keys verified in the Podman 6.0.2 man page (`Notify=healthy`, `HealthCmd`, `ShmSize`, `Ulimit`, `NetworkAlias`) |
| PANEL-02 | Generate-once secrets | Only `APP_SECRET` is the JWT secret in 3.4.11 (no separate JWT vars); secret file design; controller-side `lookup('password','/dev/null ...')` verified; class-guarantee pitfall observed live |
| PANEL-03 | First admin on loopback before the Traefik router is published | `/api/auth/status` state machine read from source; backend rejects requests without `X-Forwarded-For` + `X-Forwarded-Proto: https`, loopback calls must send them |
| PANEL-04 | Long-lived API token, file 0600 on Panel host | `POST /api/tokens` (admin JWT only), token returned once, JWT signed with `APP_SECRET`, `expiresInDays` min 1 / no max; lost-token recovery flow |
| PANEL-05 | Panel over HTTPS on own domain | Per-route file with `tls.certResolver`, `sniStrict`, 80 to 443 redirect router |
| PANEL-06 | Cookie/secret-path gate | Pure-Traefik gate **works** (Spike S1, executed); test matrix included; amendment of REQUIREMENTS/ROADMAP wording (D-02) is a plan task |
| SUB-01 | Subscription page on its own domain over HTTPS | Image 8.0.1, port 3010, `/internal/health`, proxy-check, `TRUST_PROXY` |
| SUB-02 | Sub-page connected via API token, no manual steps | `REMNAWAVE_PANEL_URL=http://remnawave:3000` makes the page add the forwarded headers itself; required env is `REMNAWAVE_API_TOKEN`; `INTERNAL_JWT_SECRET` is generated by its entrypoint |
| QA-05 | CI uses Pebble, never production LE | Pebble v2.10.3 binaries + sha256 digests, challtestsrv flags, pitfalls (AAAA, DoH port, httpPort) |
| DOC-04 | `no_log`, placeholders rejected by assert | Placeholder list, `diff: false` on templates that embed secrets, no secret in `--diff`/loop labels |
</phase_requirements>

## Summary

The decisive risk of this phase (cookie/secret-path gate on plain Traefik, no plugins) is **resolved: it works with the main variant of D-05, no fallback needed.** I ran Traefik 3.7.19 (sha256-checked release binary) locally against stub backends and reproduced the whole matrix: a router `Host && Path(/<secret>)` with `service: noop@internal` and middlewares `[headers(customResponseHeaders Set-Cookie), redirectRegex]` answers `302` with `Location: /` and the `Set-Cookie` with `Secure; HttpOnly; SameSite=Strict`; a router with `HeaderRegexp(Cookie, ...)` sends cookie holders to the backend; everything else falls through to a catch-all that goes to the decoy with HTTP 200; `/api/*` except `/api/auth/*` is always routed to the backend. The secret-path request does **not** appear in the access log (internal router; do not enable `accessLog.addInternals`). A second spike ran Traefik + Pebble 2.10.3 + challtestsrv end to end: HTTP-01 through a file-provider router, `sniStrict` handshake abort for unknown/absent SNI, `:80` redirect only for known hosts, 404 otherwise, `acme.json` 0600.

Remnawave 3.4.11 specifics that change the plan relative to STACK.md assumptions: (1) there is **one** secret, `APP_SECRET` (it is also the JWT signing key, API tokens are JWTs signed with it); no separate `JWT_*` secrets; (2) the backend **destroys the socket** of any request that lacks `X-Forwarded-For` and `X-Forwarded-Proto: https`, so the loopback bootstrap must send both headers by hand; (3) admin password policy is min 24 chars with upper, lower and digit; (4) `/api/auth/status` gives a clean state machine (0 admins: register; exactly 1: login; more than 1: both false) that makes bootstrap idempotent; (5) the API token is shown **once** and can only be created with an admin JWT, so a lost token must be recreated; (6) subscription-page 8.0.1 requires `REMNAWAVE_API_TOKEN` and generates its own `INTERNAL_JWT_SECRET` in its entrypoint.

Also: Traefik **v3.7.20** (2026-11-23, image on Docker Hub 2026-11-24) fixes three advisories (one on trailing-dot Host handling, one on provider credentials in debug logs); STACK.md pinned 3.7.19 a day earlier. Recommend pinning `v3.7.20`. Traefik 3.7 allows all encoded path characters by default; the entrypoint must set `http.encodedCharacters.*: false`.

**Primary recommendation:** Build `roles/edge` (Traefik host-network Quadlet + decoy-nginx + `tasks_from: route` drop-in interface) and `roles/panel` (secrets file on the Panel host, three-container stack on a Quadlet `.network`, loopback bootstrap through `uri` with forged forwarded headers, then publish a route file into the edge dynamic directory). Start Plan 1 with a **scripted spike** that reproduces the verified gate configuration so the gate is a regression test from day one.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TLS termination, ACME HTTP-01, SNI strictness | Edge (Traefik, `rw-edge`) | Firewall (80/443 open) | Traefik owns certs and handshake policy; backend never sees TLS |
| Admin gate (secret path to cookie, decoy for the rest) | Edge (Traefik routers/middlewares) | Decoy (nginx) | Pure routing/headers decision; backend must not know about the gate |
| Decoy site content | Decoy nginx (`rw-edge`) | — | Traefik cannot serve static files |
| Panel API/UI, auth, token issuing | Backend container (`rw-panel`) | Postgres, Valkey | Business logic and state |
| Real client IP and forwarded headers | Edge | Backend (consumes `X-Forwarded-*`) | Traefik is the only trusted hop; it overwrites untrusted `X-Forwarded-*` |
| Admin/API-token bootstrap | Ansible on the Panel host over loopback `127.0.0.1:3000` | Backend `/api/auth/*`, `/api/tokens` | Must run before the public route exists (PANEL-03) |
| Secret generation and persistence | Ansible (generate on controller in memory, persist on Panel host) | Panel host filesystem (0600) | D-07: no controller state |
| Subscription rendering | sub-page container (`rw-panel`) | Backend over the private network | Separate image/major line; talks to backend with the API token |
| Cert/route interface for later phases | `edge` role `tasks_from: route` | — | D-16: panel and node only add route files |
| ACME/DNS test doubles | Molecule VM prepare (Pebble + challtestsrv) | — | QA-05: never production LE |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `docker.io/library/traefik` | **v3.7.20** (recommended; STACK.md has v3.7.19) | Edge proxy | v3.7.20 published 2026-11-23, Hub tag present; fixes GHSA-3rh5-223h-cpwr (Brotli memory), GHSA-42x2-976f-ph52 (provider credentials in debug logs), GHSA-9657-c2gv-wjpj (trailing-dot hosts evade TLS-option conflict detection) [VERIFIED: api.github.com/repos/traefik/traefik/releases/tags/v3.7.20, hub.docker.com tags v3.7.20]. v3.8.0 stable exists (2026-11-23); do not jump a minor in this phase |
| `docker.io/remnawave/backend` | 3.4.11 | Panel | Tag exists on Hub (pushed 2026-11-14) [VERIFIED: hub.docker.com remnawave/backend tags] |
| `docker.io/remnawave/subscription-page` | 8.0.1 | Sub-page | Tag exists (2026-10-22); pins `@remnawave/backend-contract` 3.1.1 while backend 3.4.11 ships contract 3.4.17 (see Open Question 4) |
| `docker.io/library/postgres` | 18.4 | DB | Tag exists; mount the volume at `/var/lib/postgresql` |
| `docker.io/valkey/valkey` | 9-alpine | Cache/queue | Tag exists (2026-11-19) |
| `docker.io/nginxinc/nginx-unprivileged` | 1.31-alpine | Decoy | Tag family exists (2026-10-19); listens on 8080, has busybox `wget` |
| `fedora.linux_system_roles` | 2.5.0 (already pinned in `requirements.yml`) | Quadlet deployment (via `podman_rootless` `tasks_from: quadlet`) | Phase 1 D-10 interface, reused unchanged |
| `ansible.builtin` (`uri`, `slurp`, `template`, `assert`, `lookup('password')`) | core | Bootstrap and secrets | No new collections needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pebble + pebble-challtestsrv | v2.10.3 (2026-11-11) | ACME test CA + mock DNS | VM-tier prepare only; sha256 pins below |
| `ansible.posix` 2.2.2, `community.general` 14.0.1, `containers.podman` 1.21.2 | pinned in `requirements.yml` | firewalld, sefcontext, LSR runtime dep | unchanged from Phase 1 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Env-file (0600) for container secrets | Podman `Secret=` | `Secret=` needs `podman secret create` idempotency and recreation on change; both put the value in the container environment anyway. Env-file is a plain `template`, consistent with D-07's file-centric model. **Use env-file.** |
| Traefik `Network=host` | `Network=pasta` + `PublishPort` | pasta cannot reach `127.0.0.1:3000` of the host without extra mapping and gives no benefit for client IP when Traefik terminates connections on the host netns. **Use `Network=host`** (EDGE-01 text, ARCHITECTURE.md). The CLAUDE.md "Network=pasta for Traefik" line is superseded for the edge role |
| Galaxy Traefik roles (`arillso.traefik` 484k downloads, `sbaerlocher.traefik`, ...) | Own `edge` role | All are Docker-oriented and last modified 2023-10 [VERIFIED: galaxy.ansible.com search]; none renders rootless Quadlet or our gate. Not reusable |
| Galaxy collections `kenyawest.remnawave` 1.6.0 (2026-11-10), `ilyagulya.remnawave` 0.1.0, `lagomvpn.remnawave` 1.0.0 | Own `uri` calls for 4 bootstrap requests | They manage panel entities over the API (relevant to Phase 3 research, not to this phase); bootstrap needs only status/register/login/token-create. Adding a root-executed third-party dependency for four calls is not justified. Re-evaluate in Phase 3 [VERIFIED: galaxy.ansible.com API metadata] |

**Installation:** no new collections or PyPI packages. Images are variables; Pebble is downloaded in VM prepare only.

```bash
# Pebble pins (VM prepare); sha256 computed this session from the GitHub release assets
# pebble-linux-amd64.tar.gz                7e33cf3e426b67e9e647c44e8cc91683caa8ab331f7a99e5e27fcee291c4c7e2
# pebble-challtestsrv-linux-amd64.tar.gz   00b2c5ef525cd8ad56cda898a7cac6169a10b0fd3f2a7456fe0cec92e7b36cb6
# test/certs/pebble.minica.pem  (raw @v2.10.3) 0c502e52627ff7de972c7e9e065640103b4589b4e2d23d3fcf21bef1e3c8c67c
# test/certs/localhost/cert.pem (raw @v2.10.3) c87fb918d9bac8db11aa54493b5f0cf6e0725a3fe73f617d1c64737e1ab4caf9
# test/certs/localhost/key.pem  (raw @v2.10.3) 0977979255b0e0721c17335c056b627f66a43cf56e5a52f3cda81fb111ecf00e
```
The release API reports identical `digest` values for the two tarballs [VERIFIED: api.github.com/repos/letsencrypt/pebble/releases/tags/v2.10.3]. The pebble localhost cert has SAN `localhost, pebble, 127.0.0.1` and is valid to 2027-10-03, so `https://127.0.0.1:14000/dir` validates.

**Version verification:** image tags and release dates checked against Docker Hub and GitHub APIs on 2026-11-25 (see Sources).

## Package Legitimacy Audit

This phase installs **no new registry packages** (no npm/PyPI/crates, no new Galaxy collection; `requirements.yml` is unchanged). The `gsd-tools package-legitimacy` seam covers npm/PyPI/crates only and was not applicable. Non-registry artifacts introduced:

| Artifact | Source | Age | Source Repo | Verdict | Disposition |
|----------|--------|-----|-------------|---------|-------------|
| Traefik image `v3.7.20` | Docker Hub official image | 8+ yrs project | github.com/traefik/traefik | Official image | Approved |
| Remnawave `backend` 3.4.11, `subscription-page` 8.0.1 | Docker Hub `remnawave/*` (project's own, matches CLAUDE.md STACK) | project 2024+ | github.com/remnawave/* | Upstream | Approved (pinned by tag; consider digest pin) |
| Pebble / challtestsrv v2.10.3 binaries | GitHub release assets of letsencrypt/pebble | 8+ yrs | github.com/letsencrypt/pebble | Official Let's Encrypt test tool; digest published by GitHub API and matched to locally computed sha256 | Approved for CI/VM prepare only, sha256-pinned |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Internet client
   |  :80 (HTTP)                         :443 (TLS, SNI)
   v                                      v
+---------------- Panel host (firewalld: 80/443 + operator ssh) ------------------------+
|  rw-edge (rootless, Network=host)                                                     |
|   Traefik v3.7                                                                        |
|    entrypoint web :80  --ACME HTTP-01 challenge router (internal, top priority)       |
|                        --per-domain redirect router (Host known) --> 301 https        |
|                        --unknown Host --> no router --> 404                           |
|    entrypoint websecure :443 (sniStrict: unknown/absent SNI => handshake abort)       |
|      Host(panel):                                                                     |
|        P1000 Path(/<secret>)        -> headers(Set-Cookie) -> redirectRegex 302 /     |
|                                        service noop@internal (not logged)            |
|        P500  HeaderRegexp(Cookie)   -> backend 127.0.0.1:3000   (UI + all /api)       |
|        P400  /api/* except /api/auth -> backend 127.0.0.1:3000   (Bearer, public sub) |
|        P1    catch-all              -> decoy 127.0.0.1:18080  (200 static site)       |
|      Host(sub): all paths           -> sub-page 127.0.0.1:3010                        |
|    file provider dir: dynamic/*.yml (watch)   <--- drop-in route files from roles     |
|    acme.json 0600 (persistent), access log JSON (real ClientHost)                     |
|   decoy nginx-unprivileged  (PublishPort 127.0.0.1:18080 -> 8080)                     |
|                                                                                       |
|  rw-panel (rootless, user-defined Quadlet network "remnawave")                        |
|   remnawave-db (PG18, volume)  <--5432-- remnawave (backend)  --unix socket-->        |
|   remnawave-redis (Valkey)  valkey-socket volume       ^   PublishPort 127.0.0.1:3000 |
|   remnawave-subscription-page --http://remnawave:3000 (Bearer API token)--^           |
|                                PublishPort 127.0.0.1:3010                             |
|   secrets: ~/secrets/panel-secrets.yml (0600), ~/env/*.env (0600), ~/secrets/api-token|
|                                                                                       |
|  Ansible (on host, loopback only, BEFORE the panel route file exists):                |
|   GET /api/auth/status -> register | login -> POST /api/tokens -> write token file    |
|   (every request carries X-Forwarded-For + X-Forwarded-Proto: https by hand)          |
+---------------------------------------------------------------------------------------+
```

### Recommended Project Structure
```
roles/
├── edge/                         # D-16 (planner may name it `traefik`)
│   ├── defaults/main.yml         # xvpn_edge_* (image, acme ca, email, decoy, dynamic dir)
│   ├── meta/{main,argument_specs}.yml
│   ├── tasks/main.yml            # user dirs, static config, quadlet units, sysctl check
│   ├── tasks/route.yml           # entry point for other roles: xvpn_edge_route_name/_src/_state
│   ├── templates/
│   │   ├── traefik.container.j2  decoy.container.j2
│   │   ├── traefik.yml.j2        # static config
│   │   ├── 00-tls-options.yml.j2 # sniStrict + minVersion
│   │   └── decoy-nginx.conf.j2   # try_files => 200
│   └── files/decoy/index.html    # default neutral site
├── panel/
│   ├── defaults/main.yml         # xvpn_panel_* (images, domains, admin, token days, gate vars)
│   ├── meta/{main,argument_specs}.yml
│   ├── tasks/main.yml            # asserts -> secrets -> stack -> bootstrap -> routes
│   ├── tasks/secrets.yml         # read existing, generate missing, divergence check, write
│   ├── tasks/stack.yml           # network/volumes/db/redis/backend units + env files
│   ├── tasks/bootstrap.yml       # status/register/login/token (loopback)
│   ├── tasks/subpage.yml         # D-17, when xvpn_panel_subscription_enabled
│   ├── tasks/routes.yml          # include edge route for panel + sub + gate
│   └── templates/                # *.container.j2 *.network.j2 *.volume.j2 *.env.j2 panel-routes.yml.j2
playbooks/panel.yml, playbooks/site.yml
extensions/molecule/shared/{pebble prepare tasks, verify_panel.yml, verify_gate.yml}
```

### Pattern 1: Cookie/secret-path gate in pure Traefik (VERIFIED by execution)
**What:** Four routers per panel domain, ordered by explicit `priority`; the secret-path router has no backend (`noop@internal`) and answers itself through `redirectRegex`, with `headers.customResponseHeaders` adding `Set-Cookie` (the headers middleware wraps the response writer, so the cookie is applied to the redirect issued by a later middleware).
**When to use:** the whole Panel domain. Reuse the decoy pattern on the node in Phase 3.
**Example:** see Code Examples, "Gate dynamic config". Executed results:

| Request (no cookie unless stated) | Result in spike |
|---|---|
| `GET /` | 200 decoy |
| `GET /<secret>` | 302, `location: https://<host>/`, `set-cookie: ...; Max-Age=2592000; Path=/; Secure; HttpOnly; SameSite=Strict` |
| `GET /` with `Cookie: a=b; gate=<v>; c=d` | backend |
| same, two `Cookie` header fields over HTTP/2 | backend (Go merges them) |
| `Cookie: gate=<v>4` or `xgate=<v>` | decoy (anchoring works) |
| `Cookie: a=b;gate=<v>` (no space after `;`) | decoy with regex `(^|; )`; use `(^|;) ?` to also accept it |
| `GET /api/x` | backend (public API) |
| `/api/auth/login`, `/api/AUTH/login`, `/API/auth/login`, `//api/auth/login`, `/api//auth/login`, `/api/./auth/login`, `/api/%61uth/login`, `/api/x/../auth/login`, `/api/auth` | decoy (path is sanitised and matched case-insensitively by the exclusion regex) |
| `/api/auth%2Flogin` | 400 with `allowEncodedSlash: false` |
| `/api/authx` | backend (not the auth controller) |
| TLS to IP without SNI, or SNI of an unknown host | handshake aborted, alert 112 `unrecognized_name` |
| Client-sent `X-Forwarded-For: 6.6.6.6`, `X-Forwarded-Proto: http` | backend receives `X-Forwarded-For: 127.0.0.1` (real peer) and `X-Forwarded-Proto: https` |

### Pattern 2: Loopback bootstrap state machine (VERIFIED from backend source)
```
GET  /api/auth/status  (headers: X-Forwarded-For: 127.0.0.1, X-Forwarded-Proto: https)
  isRegisterAllowed=true  (0 admins)       -> POST /api/auth/register {username,password} -> accessToken (admin JWT)
  isLoginAllowed=true     (exactly 1 admin)-> POST /api/auth/login    {username,password} -> accessToken
  both false                                -> >1 admins or DB not ready: retry for N seconds, then fail with a clear message
then (with admin JWT):
  token file present and `GET /api/nodes` with Bearer returns 200 -> done (no-op, changed=false)
  else: GET /api/tokens -> if an entry with our name exists: DELETE /api/tokens/<uuid>
        POST /api/tokens {name, expiresInDays, scopes:["*"]} -> response.token -> write file 0600 (no_log)
```
Failure window: the token is returned once; if the file write fails after creation, the next run finds the name but no file and recreates (the "delete by name, create" branch).

### Pattern 3: Route drop-in interface of the edge role (D-16)
`tasks_from: route` with inputs `xvpn_edge_route_name` (`^[a-z0-9-]+$`), `xvpn_edge_route_src` (absolute template path, same convention as `xvpn_podman_rootless_quadlet_specs[].template_src`), `xvpn_edge_route_state`. It writes `{{ xvpn_edge_dynamic_dir }}/<name>.yml` (owner `rw-edge`, mode 0600 because panel routes embed the gate secret), `diff: false`, `no_log` when the caller marks it sensitive. Traefik reloads on its own (`providers.file.watch: true`); no restart. Static-config changes still restart the unit (LSR restarts when the unit file changes; the static config is a bind-mounted file, so notify an explicit restart, see Pitfall 7).

### Anti-Patterns to Avoid
- **Matching `/api/auth` case-sensitively or with `PathPrefix`:** Express routing and the backend's public-path check are case-insensitive (`toLowerCase()` in `preParseAuthMiddleware`), so a case-sensitive deny rule leaves `/api/AUTH/...` reachable. Use `PathRegexp` with `(?i)` as in the verified rule.
- **Enabling `accessLog.addInternals` or DEBUG logging:** the secret-path request is only absent from the log because the internal router is not logged by default; debug logging prints routes (with the secret) in the Traefik log.
- **A Traefik entrypoint-level HTTP→HTTPS redirect:** it would redirect unknown hosts too (violates D-15). Use per-domain redirect routers.
- **Mounting the Podman socket or using the Podman provider:** forbidden by EDGE-01.
- **Putting the sub-page behind the cookie gate:** it is the public subscription surface (SUB-01).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ACME issuance/renewal | Own certbot flow | Traefik `certificatesResolvers.<n>.acme.httpChallenge` | Verified end to end with Pebble; renewal is built in |
| Cookie issue + redirect | Auth service / plugin | `headers` + `redirectRegex` on `noop@internal` | Verified; plugins/forward-auth are forbidden by D-05 |
| Quadlet deployment | Own template+restart helper | `podman_rootless` `tasks_from: quadlet` (LSR) | Phase 1 D-10 decision, already validated with a generator dry-run |
| Random secrets | Shell `openssl rand` per run | `lookup('ansible.builtin.password','/dev/null chars=... length=N')` | Verified distinct per call, nothing written; NOTE no class guarantee (see Pitfall 3) |
| Test ACME CA/DNS | Self-made fake CA | Pebble + pebble-challtestsrv | Standard Let's Encrypt test pair; digest-pinned |
| Admin API client | Third-party collection (this phase) | 4 `uri` calls | Four endpoints; a root-run external dependency is not worth it |
| Real-IP logic | Custom header parsing | Traefik overwrites untrusted `X-Forwarded-*`; do not set `forwardedHeaders.trustedIPs` on the public entrypoints | Verified in spike |

**Key insight:** every hard part of this phase has an off-the-shelf piece (Traefik routers, Pebble, LSR, `uri`); the work is wiring and proving it under SELinux, not building components.

## Runtime State Inventory

Not a rename/refactor/migration phase (greenfield roles). Omitted per instructions.

## Common Pitfalls

### Pitfall 1: Backend kills requests without forwarded headers
**What goes wrong:** every call to `127.0.0.1:3000` from Ansible or a healthcheck is answered by a closed socket.
**Why:** `proxyCheckMiddleware` (applied to all routes outside development): `const isProxy = Boolean(req.headers['x-forwarded-for']); const isHttps = Boolean(req.headers['x-forwarded-proto'] === 'https'); if (!isHttps || !isProxy) { ... res.socket?.destroy(); ...}` [VERIFIED: remnawave/backend@3.4.11 `src/common/middlewares/proxy-check.middleware.ts`, wired in `src/common/utils/startup-app/http-pipeline.ts` via `app.use(proxyCheckMiddleware)`].
**How to avoid:** all bootstrap/probe `uri` tasks send `X-Forwarded-For: 127.0.0.1` and `X-Forwarded-Proto: https`. The container healthcheck uses the **metrics port** (`curl -f http://localhost:3001/health`, as upstream compose does), which is a separate listener.
**Warning signs:** `uri` fails with "Remote end closed connection", `status: -1`.

### Pitfall 2: Gate bypass through `/api/auth` path variants
**What goes wrong:** login reachable without cookie.
**Why:** case-insensitive backend routing, `//`, dot-segments, encoded characters (`%61`), encoded slash.
**How to avoid:** exclusion regex `(?i)^/+api/+auth(/|$)`; `sanitizePath` left at its default `true`; set all `http.encodedCharacters.allowEncoded*: false` on both entrypoints (Traefik 3.7 default is **allowed** for all seven) [CITED: traefik v3.7.19 docs/content/reference/install-configuration/entrypoints.md]. Verify with the matrix above in `verify_gate.yml` (negative tests are mandatory).

### Pitfall 3: Generated password lacks a required character class
**What goes wrong:** `POST /api/auth/register` returns 400 on first run.
**Why:** policy `^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9]).{24,}$`, min 24 [VERIFIED: remnawave/backend@3.4.11 `libs/contract/commands/auth/register.command.ts`]. A 40-char `ascii_letters,digits` password generated during this research had no digit (observed once, output `digit=False`).
**How to avoid:** build the password from segments: `lookup(password,'/dev/null chars=ascii_lowercase length=8') ~ lookup(... ascii_uppercase length=8) ~ lookup(... digits length=8) ~ lookup(... ascii_letters,digits length=16)`, then `| list | shuffle | join`; assert the regex before writing. Alnum only so it is safe inside `DATABASE_URL` and shell/YAML. Same rule for the Postgres password (URL-safe) and the cookie value (regex-safe).

### Pitfall 4: Secrets in diff, facts or loop labels
**What goes wrong:** secret or secret-path appears in `--diff` output, `-v` task results or callback logs.
**How to avoid:** `no_log: true` and `diff: false` on every `template`/`copy`/`uri`/`slurp`/`set_fact` that carries a secret; `loop_control.label` never the item; do not use `set_fact` with `cacheable: true`; the final summary prints **file paths only**.

### Pitfall 5: `isLoginAllowed: false` and `isRegisterAllowed: false` are ambiguous
**What goes wrong:** bootstrap loops or registers a second admin.
**Why:** both are false when the DB query failed (not ready) and when more than one admin exists (log says "restart Remnawave to clear unknown admins") [VERIFIED: `src/modules/auth/auth.service.ts` `getStatus`]. Also `login` fails if an operator disabled password auth (`passwordSettings.enabled`).
**How to avoid:** retry the status call (e.g. 60 x 5 s) before declaring failure; the fail message distinguishes "not ready within N s" from "inconsistent admin state"; never call register unless `isRegisterAllowed` is true.

### Pitfall 6: Postgres password is applied only at first initialisation
**What goes wrong:** the secrets file is lost or regenerated while the data volume exists; backend cannot authenticate and the operator "fixes" it by regenerating.
**How to avoid:** if the secrets file is absent **and** the named volume (explicit `VolumeName=remnawave-db-data`) exists, fail with an explanation instead of generating new values (extends D-10). Divergence check: compare vault overrides with the stored value for `APP_SECRET`, PG password, admin password; fail naming the **key**, never the value.

### Pitfall 7: Env-file and static-config changes do not restart units
**What goes wrong:** a changed env file or `traefik.yml` is not picked up; LSR restarts only when the unit text changes (Phase 1 D-10(c)).
**How to avoid:** a handler/task that restarts the specific user unit (`ansible.builtin.systemd_service scope: user`, `XDG_RUNTIME_DIR`, as Phase 1 does) when the env/static file task reports `changed`. Never restart on a no-op run (idempotence gate `changed=0`).

### Pitfall 8: SELinux relabel and root-written files
**What goes wrong:** files written by `template` as root into the service user's tree are not readable by the container after a replace.
**How to avoid:** bind mounts use `:Z` (single owner container); the unit restart after a change relabels. Do not set `setype` on those files. Mount **directories** (acme, dynamic, decoy) rather than single files. Keep `acme.json` at 0600: Traefik refuses wider permissions [ASSUMED from Traefik behaviour, spike used 0600].

### Pitfall 9: Pebble specifics
**What goes wrong:** validation fails with "dial tcp [::1]:5002: connection refused".
**Why:** challtestsrv answers AAAA with `::1` by default; Pebble's `httpPort` defaults to 5002 and challtestsrv itself binds 5002/5003/5001 and DoH `:8443` (clash with Traefik).
**How to avoid:** `pebble-challtestsrv -http01 "" -https01 "" -tlsalpn01 "" -doh "" -dnsserver 127.0.0.1:8053 -management 127.0.0.1:8055 -defaultIPv4 127.0.0.1 -defaultIPv6 ""`; Pebble config `"httpPort": 80` on the VM (Traefik is on 80), env `PEBBLE_VA_NOSLEEP=1`, `-dnsserver 127.0.0.1:8053`; Traefik gets `LEGO_CA_CERTIFICATES=/path/pebble.minica.pem` (mounted read-only) [VERIFIED by spike S2]. Preflight resolves domains with the host resolver, so VM prepare also adds `/etc/hosts` entries domain -> VM public IP (preflight compares with the interface address).

### Pitfall 10: SameSite=Strict breaks cross-site entries
**What goes wrong:** (a) clicking a panel link from another site shows the decoy; (b) OAuth2 login (`/api/auth/oauth2/callback`, Telegram callback) returns from the IdP as a cross-site navigation without the cookie and hits the closed `/api/auth/*`.
**How to avoid:** D-04 is locked, so keep Strict by default but expose `xvpn_panel_gate_cookie_samesite` (Strict|Lax) and document in README that v1 supports password/passkey login only with Strict.

### Pitfall 11: First start exceeds systemd's default timeout
Backend runs `prisma migrate deploy` + seed in its entrypoint, images are pulled at unit start. Use `TimeoutStartSec=900`, backend `HealthStartPeriod=30s`+, `Notify=healthy`, and give Postgres `HealthInterval`/`HealthRetries` generous enough for first init.

## Code Examples

### Traefik static config (`traefik.yml.j2`) — the spike-verified skeleton
```yaml
# Source: structure executed in Spike S2 (Traefik 3.7.19); option names per Traefik 3.7 docs
global:
  checkNewVersion: false
  sendAnonymousUsage: false
entryPoints:
  web:
    address: ":80"
    http:
      encodedCharacters: &enc
        allowEncodedSlash: false
        allowEncodedBackSlash: false
        allowEncodedNullCharacter: false
        allowEncodedSemicolon: false
        allowEncodedPercent: false
        allowEncodedQuestionMark: false
        allowEncodedHash: false
  websecure:
    address: ":443"
    http:
      encodedCharacters: *enc
providers:
  file:
    directory: /etc/traefik/dynamic
    watch: true
certificatesResolvers:
  le:
    acme:
      caServer: "{{ xvpn_edge_acme_ca_server }}"   # staging/production URL or Pebble dir
      email: "{{ xvpn_edge_acme_email }}"          # omit the key when empty
      storage: /acme/acme.json
      httpChallenge:
        entryPoint: web
log:
  level: INFO            # never DEBUG: it prints routes and the gate secret
accessLog:
  format: json           # stdout; do NOT set addInternals
  fields:
    headers:
      defaultMode: drop  # Cookie/Authorization must never be logged
```

### Gate dynamic config (rendered by the `panel` role; verified router set)
```yaml
# Source: executed in Spike S1 on Traefik 3.7.19 (values here are templated)
tls:
  options:
    default: { sniStrict: true, minVersion: VersionTLS12 }   # lives in 00-tls-options.yml (edge role)
http:
  middlewares:
    xvpn-gate-setcookie:
      headers:
        customResponseHeaders:
          Set-Cookie: "{{ cookie_name }}={{ cookie_value }}; Max-Age={{ max_age }}; Path=/; Secure; HttpOnly; SameSite={{ samesite }}"
    xvpn-gate-redirect:
      redirectRegex:
        regex: "^https://([^/]+)/{{ secret_path }}$"      # no backslashes
        replacement: "https://${1}/"
        permanent: false
    xvpn-to-https:
      redirectScheme: { scheme: https, permanent: true }
  services:
    xvpn-backend: { loadBalancer: { servers: [ { url: "http://127.0.0.1:3000" } ] } }
    xvpn-decoy:   { loadBalancer: { servers: [ { url: "http://127.0.0.1:18080" } ] } }
  routers:
    xvpn-panel-gate:
      entryPoints: [websecure]
      rule: "Host(`{{ panel }}`) && Path(`/{{ secret_path }}`)"
      priority: 1000
      middlewares: [xvpn-gate-setcookie, xvpn-gate-redirect]   # order matters as written
      service: noop@internal
      tls: { certResolver: le }
      observability: { accessLogs: false }
    xvpn-panel-cookie:
      entryPoints: [websecure]
      rule: "Host(`{{ panel }}`) && HeaderRegexp(`Cookie`, `(^|;) ?{{ cookie_name }}={{ cookie_value }}($|;)`)"
      priority: 500
      service: xvpn-backend
      tls: { certResolver: le }
    xvpn-panel-api:
      entryPoints: [websecure]
      rule: "Host(`{{ panel }}`) && PathRegexp(`(?i)^/api(/|$)`) && !PathRegexp(`(?i)^/+api/+auth(/|$)`)"
      priority: 400
      service: xvpn-backend
      tls: { certResolver: le }
    xvpn-panel-decoy:
      entryPoints: [websecure]
      rule: "Host(`{{ panel }}`)"
      priority: 1
      service: xvpn-decoy
      tls: { certResolver: le }
    xvpn-panel-http:
      entryPoints: [web]
      rule: "Host(`{{ panel }}`)"
      middlewares: [xvpn-to-https]
      service: noop@internal
```
Notes: the spike used the stricter variant `(^|; )name=value($|;)`; the `(^|;) ?` form is the recommended loosening (accepts `a=b;gate=v`). Cookie name and values are `[A-Za-z0-9_]` so they are regex-safe and need no escaping. Per-domain `Host()` rules also drive certificate issuance (one cert per Host, observed `domain=panel.test`); routes therefore trigger issuance only when the route file appears, i.e. after bootstrap. HTTPS verification must retry (e.g. 30 x 5 s).

### Quadlet units (shapes; keys verified in the Podman 6.0.2 `podman-systemd.unit(5)` page)
```ini
# remnawave-db.container (rw-panel). PG18: mount at /var/lib/postgresql, TZ must be UTC
[Unit]
Description=Remnawave PostgreSQL
[Container]
Image={{ xvpn_panel_postgres_image }}
ContainerName=remnawave-db
HostName=remnawave-db
Network=remnawave.network
Volume=remnawave-db.volume:/var/lib/postgresql
EnvironmentFile={{ home }}/env/postgres.env
Environment=TZ=UTC
ShmSize=512m
Ulimit=nofile=1048576:1048576
HealthCmd=pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}
HealthInterval=3s
HealthRetries=10
HealthStartPeriod=30s
Notify=healthy
LogDriver=k8s-file
LogOpt=max-size=50m
[Service]
Restart=always
TimeoutStartSec=900
[Install]
WantedBy=default.target
```
`HealthCmd` runs as `CMD-SHELL`-style string; `${POSTGRES_USER}` must be expanded inside the container, so write `$$`/escape as Quadlet requires or use a literal user from the variable at render time (render literal values; they are not secrets). Backend: `Network=remnawave.network`, `PublishPort=127.0.0.1:3000:3000`, `Volume=valkey-socket.volume:/var/run/valkey`, `EnvironmentFile=.../backend.env`, `HealthCmd=curl -f http://localhost:3001/health`, `After=`/`Requires=` on `remnawave-db.service remnawave-redis.service`, `Notify=healthy`, `ContainerName=remnawave` (also the DNS name the sub-page uses). Valkey: command `valkey-server --save "" --appendonly no --maxmemory-policy noeviction --loglevel warning --unixsocket /var/run/valkey/valkey.sock --unixsocketperm 777 --port 0`, `HealthCmd=valkey-cli -s /var/run/valkey/valkey.sock ping` [VERIFIED: upstream `docker-compose-prod.yml`].

### Backend env (generated `backend.env`, 0600) — only keys the 3.4.11 schema requires
```
# required by configSchema: DATABASE_URL, APP_SECRET (!= "change_me"), FRONT_END_DOMAIN, METRICS_USER, METRICS_PASS (min 1), SUB_PUBLIC_DOMAIN, and REDIS_SOCKET (or REDIS_HOST+REDIS_PORT, not both)
APP_PORT=3000
METRICS_PORT=3001
DATABASE_URL=postgresql://<pguser>:<pgpass>@remnawave-db:5432/<pgdb>
REDIS_SOCKET=/var/run/valkey/valkey.sock
APP_SECRET=<64 alnum>
JWT_AUTH_LIFETIME=12            # must be 12..168
FRONT_END_DOMAIN=*
PANEL_DOMAIN=<xvpn_panel_domain>
SUB_PUBLIC_DOMAIN=<xvpn_subscription_domain>     # no scheme, no trailing slash; "<panel>/api/sub" when sub-page is disabled
METRICS_USER=<generated>
METRICS_PASS=<generated>
```
[VERIFIED: `src/common/config/app-config/config.schema.ts`, `.env.sample` @3.4.11]. There is **no** separate JWT secret variable. `POSTGRES_*` are for the Postgres container only ("NOT USED BY THE APP ITSELF").

### Sub-page env (`subpage.env`, 0600)
```
APP_PORT=3010
REMNAWAVE_PANEL_URL=http://remnawave:3000
REMNAWAVE_API_TOKEN=<token read from the token file>
TRUST_PROXY=1
```
Because the URL starts with `http://`, the page sets `X-Forwarded-For: 127.0.0.1` and `X-Forwarded-Proto: https` itself; `INTERNAL_JWT_SECRET` is exported by its `docker-entrypoint.sh` (not set by us); it calls `/api/system/metadata` at startup and `exit(1)`s if the panel is unreachable, so `Restart=always` plus ordering after the token exists [VERIFIED: subscription-page@8.0.1 `axios.service.ts`, `config.schema.ts`, `docker-entrypoint.sh`]. Healthcheck for Quadlet (image HEALTHCHECK is not honoured for OCI images): `HealthCmd=curl -fsS -o /dev/null --max-time 2 http://127.0.0.1:3010/internal/health` (the endpoint only answers loopback requests without `X-Forwarded-For`).

### Loopback bootstrap tasks (shape)
```yaml
- name: Panel bootstrap | read auth status
  ansible.builtin.uri:
    url: http://127.0.0.1:3000/api/auth/status
    headers: { X-Forwarded-For: 127.0.0.1, X-Forwarded-Proto: https }
    return_content: true
  register: xvpn_panel_auth_status
  until: xvpn_panel_auth_status.status | default(0) == 200
  retries: 60
  delay: 5
  check_mode: false
  changed_when: false

- name: Panel bootstrap | register the first admin
  ansible.builtin.uri:
    url: http://127.0.0.1:3000/api/auth/register
    method: POST
    body_format: json
    body: { username: "{{ xvpn_panel_admin_username }}", password: "{{ xvpn_panel_secrets.admin_password }}" }
    headers: { X-Forwarded-For: 127.0.0.1, X-Forwarded-Proto: https }
    status_code: [200, 201]
    return_content: true
  when: xvpn_panel_auth_status.json.response.isRegisterAllowed
  register: xvpn_panel_register
  no_log: true
# login branch: same with /api/auth/login when isLoginAllowed
# token branch: POST /api/tokens {name, expiresInDays, scopes: ["*"]} with Authorization: Bearer <admin jwt>
```
Response shapes: `{"response": {"accessToken": "..."}}` for register/login, `{"response": {..., "token": "..."}}` for token create; auth status is `{"response": {"isLoginAllowed", "isRegisterAllowed", ...}}` [VERIFIED: contract command files]. HTTP success code of register/login (200 vs 201) is not stated in the contract files read; accept both.

### Verify recipes (VM tier)
```bash
# gate matrix (controller or VM): resolve to the VM, trust the Pebble root for the whole run
curl --resolve panel.xvpn.test:443:<ip> --cacert pebble-root.pem -i https://panel.xvpn.test/            # 200 decoy
curl ... -c jar -i https://panel.xvpn.test/<secret>                                                      # 302 + Set-Cookie
curl ... -b jar https://panel.xvpn.test/api/auth/status                                                  # backend JSON
openssl s_client -connect <ip>:443 -servername other.example </dev/null                                  # alert 112
# real client IP: parse the Traefik JSON access log (podman logs traefik as rw-edge) and assert
#   ClientHost == the address the request came from and != 127.0.0.1
# secret masking: assert the <secret> string occurs in NO line of the access log
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Traefik v2 `{name:regex}` rule syntax | v3 syntax (`HostRegexp(\`regex\`)`, `PathRegexp`), `ruleSyntax` field deprecated | v3 | Write rules in v3 syntax only |
| Redis for backend | Valkey 9 over a unix socket | upstream 2025/26 | As in STACK.md |
| Separate JWT secrets in older Remnawave | single `APP_SECRET`; API tokens are JWTs signed with it | 3.x | PANEL-02 has fewer secrets; rotating `APP_SECRET` invalidates every API token |
| UI-created API token (sub-page docs) | token created through `POST /api/tokens` with admin JWT | 3.4 | SUB-02 can be automated; endpoint is "forbidden to use via API-key", needs an admin JWT |
| Traefik v3.7.19 | v3.7.20 (security) / v3.8.0 stable | 2026-11-23 | Pin 3.7.20 now; 3.8 is a separate decision |

**Deprecated/outdated:** `ruleSyntax: v2`; Traefik default allowance of encoded path characters (must be tightened explicitly).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `container_t` may `name_bind` 80/443 under `Network=host` without a boolean or custom module | Network decision | Traefik fails to start under enforcing; resolution would be a `checkpoint:decision` (boolean vs pasta fallback), never permissive |
| A2 | `container_t` (Traefik) may `name_connect` to 127.0.0.1:3000, :3010, :18080 and `container_t` (backend) to 5432, without `container_connect_any` | Architecture | AVC on first VM run; same escalation as above. Phase 1 gate forbids silently adding booleans |
| A3 | Rootless user-defined bridge network + `PublishPort=127.0.0.1:3000:3000` works on Podman 6 / EL10 (Phase 1 only proved `Network=pasta` + PublishPort) | Stack | Loopback publishing or inter-container DNS fails; fallback is to put the stack's containers on pasta with published ports, losing name resolution |
| A4 | `LogDriver=k8s-file` + `LogOpt=max-size` + `podman logs` as the service user is a reliable way to read the access log in verify | EDGE-03 verify | Switch verify to a bind-mounted log file |
| A5 | Traefik refuses an `acme.json` wider than 0600 | Pitfall 8 | Only affects the error message; file is created 0600 anyway |
| A6 | Traefik file-provider `watch: true` sees atomic-rename writes in a rootless bind-mounted `:Z` directory | Pattern 3 | Route changes need a unit restart; fall back to restart-on-change |
| A7 | Pebble/challtestsrv run as systemd services from `/usr/local/bin` on EL10 without AVC (unconfined_service_t) | QA-05 | Prepare fails or adds AVCs that pollute the zero-AVC gate; run them as a separate rootless user/container instead |
| A8 | subscription-page 8.0.1 (contract 3.1.1) works against backend 3.4.11 (contract 3.4.17) | SUB-02 | Sub-page exits at start; version pair must be revisited |
| A9 | `expiresInDays` has no upper bound (3650 accepted) and scope `["*"]` is valid (it is the DTO default) | PANEL-04 | Token creation 400; adjust days or fetch `GET /api/tokens/scopes` |
| A10 | Docker Hub anonymous pull limits do not break the VM tier (about 6 images per run) | CI | Use `ghcr.io/remnawave/*` mirrors via the image variables |
| A11 | Registration/login HTTP status is 200 or 201 | Bootstrap | Handled by accepting both |

## Open Questions

1. **Traefik `Network=host` under SELinux (A1/A2).**
   - Known: Phase 1 proved pasta + PublishPort; host-network binding and loopback connects are untested here.
   - Unclear: AVC outcome on EL10.3.
   - Recommendation: Plan 1 includes a VM smoke (Traefik + decoy only, zero-AVC gate). On denial, `checkpoint:decision` (boolean `container_connect_any` vs targeted fcontext/port label vs pasta fallback). Do not pre-add booleans.
2. **Port label of 3000/3010/18080** could matter more than the boolean. Read `semanage port -l` in the VM prepare diagnostics before choosing published ports (cheap: add to the existing diagnostics step).
3. **Least-privilege token for sub-page.** D-17 uses the single bootstrap token (`scopes: ["*"]`). A second token with only the scopes the page needs is stronger, but scope names come from `GET /api/tokens/scopes`, unread here. Recommend one token in v1 (as decided) and record a v2 hardening item.
4. **8.0.1 vs 3.4.11 compatibility (A8).** Verification should include: sub-page log line `[OK] Connected to Remnawave v...`; `GET https://<sub>/<unknown>` returns an HTTP response from the page. A strong check (create a user via the API with the token and fetch its subscription page) needs the user-create contract, not read here; optional stretch.
5. **Access-log rotation.** `k8s-file` + `max-size` bounds growth for stdout logs; confirm in VM, otherwise add a log bind mount and hand rotation to Phase 5.
6. **Decoy default content.** Ship one neutral multi-purpose `index.html` (no brand, no title leaking "VPN"); the operator overrides with `xvpn_edge_decoy_dir` (a directory on the controller copied to the host) or inline `xvpn_edge_decoy_index`. Needs a one-line decision from the planner; Phase 3 reuses it.
7. **Requirement wording (D-02).** REQUIREMENTS.md PANEL-06 and ROADMAP success criterion 2 must be edited to "stub instead of 404". Make it an explicit first task so verification matches.

## Environment Availability

| Dependency | Required By | Available (research sandbox) | Version | Fallback |
|------------|------------|------------------------------|---------|----------|
| ansible-core | all | yes | 2.22.0 | — |
| ansible-lint | QA | yes | present at /usr/local/bin | — |
| Traefik binary | Spike S1/S2 (dev) | downloaded + sha256 verified (not installed) | 3.7.19 | — |
| Pebble + challtestsrv | Spike S2, VM tier | downloaded | 2.10.3 | — |
| podman, molecule, vagrant, virsh, yamllint | Molecule tiers | **no** in this sandbox | — | Run in the devcontainer/CI; the plan must not assume local Molecule execution during research |
| Network access to GitHub/Docker Hub | spikes, pulls | yes | — | — |

**Missing dependencies with no fallback:** none for planning. **Missing with fallback:** Molecule/VM execution happens in CI or the project devcontainer.

Note for the planner: the two spikes ran without root or Podman (unprivileged ports 8443/5002, plain processes). Plan 1 should commit them as a script (download with sha256 check into a temp dir, run, assert the matrix) so the gate is regression-tested in the **container tier** (no SELinux/Podman needed) in addition to the VM tier.

## Security Domain

(`security_enforcement` is enabled; ASVS level 1.)

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Remnawave password policy (24+ chars, 3 classes) satisfied by generated password; admin login only through the cookie-gated UI |
| V3 Session Management | yes | Gate cookie `Secure; HttpOnly; SameSite=Strict`, random value, 30 d default; admin JWT lifetime `JWT_AUTH_LIFETIME` (12..168 h) |
| V4 Access Control | yes | Cookie gate on UI and `/api/auth/*`; Bearer API token for `/api/*`; backend roles/scopes unchanged; backend and sub-page published on `127.0.0.1` only; firewalld opens only 80/443 |
| V5 Input Validation | yes | `argument_specs` for all roles; domain and name regex assertions; route names `^[a-z0-9-]+$`; gate secrets restricted to `[A-Za-z0-9_]` |
| V6 Cryptography | yes | Secrets from the Ansible password lookup (CSPRNG); TLS via Traefik (min TLS 1.2, `sniStrict`); never hand-roll |
| V7 Error/Logging | yes | `no_log`, `diff: false`, access-log header dropping, secret-path not logged, no DEBUG |
| V14 Configuration | yes | Pinned image tags, no `SecurityLabelDisable`, no privileged, no Podman socket, API/dashboard not enabled |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Gate bypass via path normalisation (case, `//`, `%61`, `%2F`, dot-segments) | Elevation of Privilege | Case-insensitive exclusion regex, `sanitizePath` true, `allowEncoded*: false`, negative test matrix in verify |
| Secret path leaking into logs | Information Disclosure | Internal `noop@internal` router, no `addInternals`, INFO log level, assert in verify that the secret never appears in access logs |
| Forged `X-Forwarded-For`/`Proto` from the internet | Spoofing | Do not configure `forwardedHeaders.trustedIPs`/`insecure` on public entrypoints (spike: client values are overwritten) |
| Panel discoverable by IP scan | Information Disclosure | `sniStrict` handshake abort; unknown hosts 404 on :80; no default cert served |
| Secrets in repo or logs | Information Disclosure | Generate on first run on the Panel host; placeholder assert; `no_log`; 0600 files; Phase 5 backs up the secrets file |
| Secret rotation by accident (PG/JWT/admin) | Tampering/DoS | D-10 divergence check, refuse to regenerate when data volume exists |
| API token theft on the Panel host | Information Disclosure | File 0600 owned by `rw-panel`; read only through delegated `slurp` with `no_log`; never copied to the controller |
| Traefik advisories | various | Pin v3.7.20 or newer patch; no Brotli `compress` middleware used |
| Docker Hub tag drift | Tampering | Exact tags (optionally digests) in variables, `AutoUpdate` off |

Placeholder values for the DOC-04 assert (planner may extend): empty string, `change_me`, `changeme`, `CHANGE_ME`, `CHANGEME`, `postgres`, `password`, `admin`, `secret`, `example`, `<...>`-style angle placeholders, and values shorter than the backend minima. The backend itself already rejects `APP_SECRET=change_me` [VERIFIED: config.schema.ts].

## Sources

### Primary (HIGH confidence)
- remnawave/backend @3.4.11 (raw GitHub, read in full): `.env.sample`, `docker-compose-prod.yml`, `docker-entrypoint.sh`, `Dockerfile`, `src/common/config/app-config/config.schema.ts`, `src/common/config/jwt/jwt.config.ts`, `src/common/middlewares/proxy-check.middleware.ts`, `src/common/utils/startup-app/http-pipeline.ts`, `src/common/middlewares/pre-parse-auth.middleware.ts`, `src/modules/auth/auth.service.ts` (`register`, `getStatus`), `src/modules/api-tokens/api-tokens.service.ts` and `.controllers.ts`, `src/modules/auth/commands/sign-api-token/sign-api-token.handler.ts`, `libs/contract/commands/auth/{register,login,get-status}.command.ts`, `libs/contract/commands/api-tokens/create.command.ts`, `libs/contract/api/{routes.ts,controllers/auth.ts,controllers/api-tokens.ts,controllers/subscription.ts}`
- remnawave/subscription-page @8.0.1: `.env.sample`, `docker-compose-prod.yml`, `Dockerfile`, `backend/docker-entrypoint.sh`, `backend/src/main.ts`, `backend/src/common/config/app-config/config.schema.ts`, `backend/src/common/axios/axios.service.ts`, `check-assets-cookie.middleware.ts`, `backend/package.json`
- Traefik v3.7.19 docs from the repo tag: `reference/routing-configuration/http/routing/{rules-and-priority,observability}.md`, `reference/install-configuration/entrypoints.md` (sanitizePath, encodedCharacters, forwarded headers), `middlewares/{redirectregex,headers}.md`
- **Executed spikes** (this session, scratchpad): Traefik 3.7.19 release binary (sha256 `97534a68...f89be` matched the release checksums), Pebble/challtestsrv v2.10.3 — gate matrix, sniStrict, port-80 behaviour, ACME HTTP-01 via file provider, access-log masking, forwarded-header overwrite
- Podman 6.0.2 `podman-systemd.unit(5)`: https://docs.podman.io/en/v6.0.2/markdown/podman-systemd.unit.5.html (keys `Notify=healthy`, `HealthCmd`, `HealthStartPeriod`, `ShmSize`, `Ulimit`, `NetworkAlias`, `EnvironmentFile`, `LogDriver`, `LogOpt`, `Network=host`)
- GitHub API: traefik releases (v3.7.20 body, advisories), letsencrypt/pebble release v2.10.3 (assets + digests); Docker Hub tag APIs for backend, subscription-page, postgres, valkey, nginx-unprivileged, traefik
- Galaxy API (search for traefik/remnawave roles and collections)
- Repo files read this session (via shell, so cited rather than tagged verified): `roles/podman_rootless/tasks/quadlet.yml`, `roles/podman_rootless/defaults/main.yml`, `roles/preflight/defaults/main.yml` and `tasks/check_dns.yml`, `roles/common/defaults/main.yml` and `tasks/firewalld.yml`, `playbooks/foundation.yml`, `extensions/molecule/vm/{molecule,converge,prepare,verify}.yml`, `extensions/molecule/shared/templates/xvpn-fixture.container.j2`, `requirements.yml`, `requirements-dev.txt`

### Secondary (MEDIUM confidence)
- Phase 1 RESEARCH/SECURITY/VERIFICATION (LSR behaviour, AVC gate rules, zero-AVC VM tier proven for pasta + PublishPort)

### Tertiary (LOW confidence)
- SELinux behaviour of `container_t` for host-network bind and loopback connects; Pebble under systemd on EL10; rootless bridge + PublishPort on Podman 6 (all in the Assumptions Log)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — tags and release dates checked against registries/APIs; only the sub-page/backend contract pairing is open (A8)
- Architecture (gate, routers, ACME, bootstrap): HIGH — executed or read from source
- SELinux/Podman 6 networking: LOW-MEDIUM — not testable without an enforcing VM; mitigated by the zero-AVC gate and escalation rules
- Pitfalls: HIGH — most observed directly

**Research date:** 2026-11-25
**Valid until:** 2026-12-09 (fast-moving: Remnawave releases roughly weekly, Traefik patches monthly)
