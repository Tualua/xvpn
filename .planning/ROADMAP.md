# Roadmap: xvpn.remnawave

## Overview

Путь от пустого репозитория до публичной Ansible-коллекции, которая из inventory одной командой поднимает Remnawave на Rocky/Alma 10 с SELinux enforcing. Сначала закладывается rootless-фундамент и тестовый стенд (Molecule: контейнерный тир + VM-тир), на котором проверяется каждая следующая фаза. Затем поднимается Panel за Traefik с защищённым входом и subscription page, потом нода с Reality self-steal, которая автоматически регистрируется в Panel через API, после этого доверенный LAN-доступ с негативными тестами на утечки, и в конце эксплуатация (бэкапы, обновления, мониторинг сертификатов), hardening хоста, CI-матрица и документация.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Rootless-фундамент и тестовый стенд** - Preflight, rootless-пользователи, Quadlet, firewalld/SELinux и Molecule (контейнер + VM) с проверкой перезагрузки и нуля AVC (completed 2026-11-25)
- [x] **Phase 2: Panel за Traefik с защищённым входом** - Traefik + LE, Panel (backend/Postgres/Valkey), первый админ, API-токен, cookie/secret-path гейт, subscription page (completed 2026-11-28)
- [ ] **Phase 3: Нода с Reality self-steal и авто-регистрацией** - remnanode + Traefik-заглушка на loopback, Ansible-модули Panel API, клиент подключается через зарегистрированную ноду
- [ ] **Phase 4: Доступ в LAN для доверенного squad'а** - Отдельный LAN-инбаунд и internal squad, маршрутизация в объявленные подсети, негативные e2e-тесты на утечки
- [ ] **Phase 5: Эксплуатация, hardening и готовность к публикации** - Бэкапы/restore, обновления с откатом, алерты по сертификатам, hardening хоста, CI-матрица, документация

## Phase Details

### Phase 1: Rootless-фундамент и тестовый стенд
**Goal**: Оператор запускает playbook на чистом Rocky/Alma 10 и получает проверенный rootless-хост: preflight отсекает неподходящие хосты, выделенный пользователь с linger запускает тестовый Quadlet-сервис (fixture из Molecule, D-12) на порту 80, который переживает перезагрузку при SELinux enforcing без AVC; всё это автоматически проверяется в Molecule и CI-линтерах.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: FND-01, FND-02, FND-03, FND-04, FND-05, FND-06, FND-07, QA-01, QA-02, QA-03
**Success Criteria** (what must be TRUE):
  1. На хосте не-EL10, с SELinux не в enforcing, с Podman ниже 5.4, с занятыми 80/443 или с A-записью, не указывающей на IP внешнего интерфейса хоста, playbook падает на preflight с понятным сообщением, ничего не изменив
  2. После прогона на чистом EL10 тестовый Quadlet-сервис под выделенным rootless-пользователем слушает порт 80, управляется через `systemctl --user` из Ansible и снова поднимается после перезагрузки хоста
  3. VM-тир Molecule (AlmaLinux 10 и Rocky 10, SELinux enforcing) проходит converge, идемпотентность (`changed=0`), reboot-тест и проверку нуля AVC-denial'ов; firewalld открывает только нужные порты
  4. Контейнерный тир Molecule, ansible-lint и yamllint проходят в CI; коллекция собирается из `galaxy.yml` (`xvpn.remnawave`), у ролей есть `argument_specs`
**Plans:** 12/12 plans complete
Plans:
**Wave 1**
- [x] 01-01-PLAN.md — Tracer: collection identity, podman_rootless (users, home, sysctl, linger) + LSR Quadlet interface, foundation playbook (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md — Container scenario: pinned + justified requirements.yml with Galaxy approval checkpoint, ansible.cfg, pinned fixture, converge through the quadlet entry point (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-03-PLAN.md — Quality gate: lint configs, scripts/check.sh with CI-hard yamllint, README stub, LICENSE (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 01-09-PLAN.md — CI definitions + first CI run: pinned dev tooling, lint + container workflows, PyPI/gem/apt legitimacy + GitHub prerequisites checkpoint, repository alignment, tracer green in CI (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 01-04-PLAN.md — Unit/input guards: generator dry-run before LSR, container verify with :443 bind probe and negative cases (wave 5)
- [x] 01-05-PLAN.md — Preflight base: OS/SELinux read-only first play + standalone xvpn.remnawave.preflight playbook (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 01-06-PLAN.md — Preflight: input validation, Podman floor, port owner, DNS A-record checks + README docs (wave 6)
- [x] 01-07-PLAN.md — Role common: SELinux gate, add-only firewalld with SSH guard, exact-port-set verify, executed guard negatives (wave 6)

**Wave 7** *(blocked on Wave 6 completion)*
- [x] 01-08-PLAN.md — Preflight Molecule scenario: 18 cases incl. invalid inputs, nothing-changed proof (wave 7)
- [x] 01-11-PLAN.md — VM scenario: AlmaLinux 10 + Rocky 10 enforcing, checksummed boxes, systemctl --user restart round-trip, reboot, proven dontaudit-off, zero AVC (wave 7)

**Wave 8** *(blocked on Wave 7 completion)*
- [x] 01-10-PLAN.md — CI all-green: preflight scenario added to CI, lint + container + preflight tiers green with all guards (wave 8)

**Wave 9** *(blocked on Wave 8 completion)*
- [x] 01-12-PLAN.md — VM CI: KVM-gated workflow, Vagrant spike with fallback, README Testing, VM tier green (wave 9)
**Research flag**: Podman 5.x vs 6.x для Quadlet на EL10.0-10.3; KVM на CI-раннерах для libvirt-тира; drop-in `user@.service` для порядка загрузки

### Phase 2: Panel за Traefik с защищённым входом
**Goal**: Оператор разворачивает Panel-хост одной командой: Panel доступна по HTTPS на собственном домене, вход в админку закрыт cookie/secret-path гейтом, первый админ и API-токен созданы автоматически, subscription page работает на отдельном домене, а повторный прогон ничего не ломает и не меняет секреты.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: EDGE-01, EDGE-02, EDGE-03, PANEL-01, PANEL-02, PANEL-03, PANEL-04, PANEL-05, PANEL-06, SUB-01, SUB-02, QA-05, DOC-04
**Success Criteria** (what must be TRUE):
  1. Оператор открывает `https://<panel-domain>` с валидным сертификатом (в CI — Pebble/LE staging, production LE не вызывается), а в access log Traefik виден реальный IP клиента
  2. Запрос к админке без cookie получает сайт-заглушку (HTTP 200), UI и логин недоступны; переход по секретному URL ставит cookie и открывает вход; подписки и API при этом остаются доступными без cookie
  3. После первого прогона существует администратор и долгоживущий API-токен (файл 0600 на Panel-хосте); повторный прогон логинится, а не регистрирует, секреты не меняются, `changed=0`
  4. Клиент открывает subscription page на отдельном домене по HTTPS, и она получает данные от Panel по API-токену без ручных шагов
  5. Токены, пароли и ключи не появляются в выводе Ansible (`no_log`), а placeholder-значения секретов отвергаются assert'ом
**Plans:** 12/12 plans complete
Plans:
**Wave 1**
- [x] 02-01-PLAN.md — Роль edge (Traefik v3.7.20 + decoy, ACME HTTP-01, route-интерфейс): рендер и dry-run в контейнерном тире, input-guards, CI-хелпер scripts/ci_watch.sh (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 02-02-PLAN.md — Роль panel (decoy-маршрут домена Panel), playbooks/panel.yml и site.yml, контейнерный тир на реальном playbook, статический QA-05 guard (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 02-03-PLAN.md — VM-тир с Pebble: HTTPS на домене Panel, sniStrict, :80, реальный IP клиента, acme.json 0600, ноль AVC (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 02-04-PLAN.md — Generate-once секреты на Panel-хосте, divergence/lost/placeholder guards, статический no_log gate (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 02-05-PLAN.md — Panel stack (Postgres/Valkey/backend 3.4.11) на loopback, env-файлы 0600, restart-on-change (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 02-06-PLAN.md — Loopback bootstrap: первый админ, API-токен 0600, login на повторном прогоне, восстановление токена (wave 6)

**Wave 7** *(blocked on Wave 6 completion)*
- [x] 02-07-PLAN.md — Cookie/secret-path гейт на чистом Traefik + HTTPS Panel, /api и /api/sub без cookie, admin-url файл, негативная матрица, правка формулировки PANEL-06 (wave 7)

**Wave 8** *(blocked on Wave 7 completion)*
- [x] 02-08-PLAN.md — CI-регрессия гейта на продакшн-шаблонах и закреплённом образе Traefik на каждый push (wave 8)

**Wave 9** *(blocked on Wave 8 completion)*
- [x] 02-09-PLAN.md — Secret-scan репозитория закреплённым gitleaks в check.sh и lint CI с самотестом (DOC-04, D-20) (wave 9)

**Wave 10** *(blocked on Wave 9 completion)*
- [x] 02-10-PLAN.md — Subscription page на своём домене, доказательство SUB-02 по зафиксированному маркеру data-panel и отрицательный контроль по неверному токену (502) (wave 10)

**Wave 11** *(blocked on Wave 10 completion)*
- [x] 02-11-PLAN.md — Переключатель subscription page (с остановкой юнита, цикл в VM), README Panel host без секретов, весь CI зелёный (wave 11)

**Wave 12** *(gap closure 02-UAT-G1)*
- [x] 02-12-PLAN.md — ACME-хранилище по CA (acme-production/staging/custom-<hash>.json): смена xvpn_edge_acme_ca выпускает сертификат нового CA, возврат переиспользует старое хранилище; container-кейс, переключение CA в VM, README (wave 12)
**UI hint**: yes
**Research flag**: HIGH RISK: cookie/secret-path гейт на чистом Traefik без плагинов не подтверждён, а пользователь выбрал его для v1 без fallback на IP allowlist (allowlist отложен в PANEL-V2-01). Нужен ранний спайк; при неудаче потребуется решение пользователя. Также проверить набор env (`APP_SECRET` vs JWT-секреты) и forwarded-заголовки backend 3.4.11

### Phase 3: Нода с Reality self-steal и авто-регистрацией
**Goal**: Оператор добавляет ноду в inventory, и после прогона она зарегистрирована в Panel через API без действий в UI, принимает клиентов по VLESS Reality на 443, а для всех остальных выглядит как обычный сайт с настоящим сертификатом своего домена.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: NODE-01, NODE-02, NODE-03, STEAL-01, STEAL-02, STEAL-03, STEAL-04, STEAL-05, API-01, API-02, API-03, API-04, API-05
**Success Criteria** (what must be TRUE):
  1. Клиент с выданным конфигом подключается к ноде по VLESS Reality (xtls-rprx-vision) на 443 и выходит в интернет; Reality-инбаунд включается только после выпуска и проверки сертификата ноды
  2. Браузер или сканер на `https://<node-domain>` видит правдоподобный сайт-заглушку (выбранный встроенный шаблон или свой каталог) с валидным сертификатом домена ноды; запрос с чужим SNI или без SNI не раскрывает дефолтный сертификат/404 Traefik (`openssl s_client` в verify)
  3. После прогона в Panel существуют config profile, node и hosts для ноды из inventory, нода в состоянии connected; повторный прогон не создаёт дубликатов и не меняет Reality-ключи/shortIds (`changed=0`)
  4. Модули `remnawave_config_profile`, `remnawave_node`, `remnawave_host`, `remnawave_internal_squad` работают в `--check` и `--diff` и честно сообщают `changed`
  5. Порт 2222 ноды доступен только с IP Panel; нода с `state: absent` и явным флагом удаляется из Panel вместе с hosts, а её юниты останавливаются
**Plans:** 9 plans
Plans:
**Wave 1**
- [ ] 03-01-PLAN.md — Роль node (скелет, input-guards), self-steal маршрут на loopback-edge, playbooks/node.yml и site.yml, контейнерный сценарий node, QA-05 для node.yml (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 03-02-PLAN.md — Регрессионный гейт self-steal на продакшн-шаблонах: Reality -> Traefik 127.0.0.1:8443, валидный/чужой/пустой SNI, Vision-клиент, private-блок, xver, break-proof (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 03-03-PLAN.md — Четыре шаблона сайта-заглушки, выбор по хешу домена, свой каталог с prune, строгий 404 на ноде, Panel без дрейфа (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 03-04-PLAN.md — API-клиент module_utils + remnawave_node_secret, SECRET_KEY один раз, remnanode rootless Quadlet, двух-VM стенд Panel+Node, unit-тесты на fake Panel (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [ ] 03-05-PLAN.md — Сертификатный гейт STEAL-05 (443 только после пробы), rich rule 2222 только для Panel, матрица alma/rocky/oracle (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [ ] 03-06-PLAN.md — remnawave_config_profile: свой профиль ноды, ключи из Panel без ротации, нормализованный diff с redaction, override, дрейф из UI (wave 6)

**Wave 7** *(blocked on Wave 6 completion)*
- [ ] 03-07-PLAN.md — remnawave_internal_squad (union) и remnawave_node (ожидание connected с диагностикой) (wave 7)

**Wave 8** *(blocked on Wave 7 completion)*
- [ ] 03-08-PLAN.md — remnawave_host, реальный клиент из подписки выходит в интернет, private-негативы, SNI/decoy-матрица против ноды (wave 8)

**Wave 9** *(blocked on Wave 8 completion)*
- [ ] 03-09-PLAN.md — Decommission с флагом и повторная регистрация, честные --check/--diff на реальной Panel, README Node host (wave 9)
**Research flag**: HIGH RISK: Reality -> Traefik TLS на loopback (`127.0.0.1:8443`, `xver: 0`, ALPN, default cert при неизвестном SNI) не подтверждён; начать с ручного спайка, при провале пересмотреть выбор Traefik. REST-контракт Remnawave читать из OpenAPI закреплённой версии backend 3.4.11 до написания модулей. Проверить необходимость `NET_ADMIN` и SELinux-разрешений для `container_t`

### Phase 4: Доступ в LAN для доверенного squad'а
**Goal**: Оператор объявляет в inventory приватные подсети за нодой, и только клиенты LAN-squad'а получают к ним доступ; все остальные клиенты не могут достучаться ни до LAN, ни до самой ноды, что доказывают негативные e2e-тесты.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: LAN-01, LAN-02, LAN-03, LAN-04
**Success Criteria** (what must be TRUE):
  1. У ноды есть отдельный LAN-инбаунд на отдельном порту с собственными Reality-ключами и отдельный internal squad, созданные автоматически из inventory
  2. Клиент из LAN-squad'а достигает хоста в объявленной приватной подсети за нодой
  3. Обычный клиент не достигает приватных адресов, loopback, link-local, IP самой ноды (например, `127.0.0.1:22`) и доменов, резолвящихся в приватные IP
  4. Негативные e2e-тесты на утечки LAN для обычных клиентов входят в Molecule VM-тир и проходят
**Plans**: 1-2 plans (LAN-инбаунд + squad + routing-блок; e2e позитивные/негативные тесты)
**Research flag**: семантика routing Xray в версии образа ноды, покрытие `geoip:private` (link-local, ULA), DNS для LAN-имён

### Phase 5: Эксплуатация, hardening и готовность к публикации
**Goal**: Оператор может безопасно эксплуатировать инсталляцию долго: БД бэкапится и восстанавливается, компоненты обновляются сменой тега с автоматическим дампом и откатом, о проблемах с сертификатами приходит оповещение, хост ужесточён, а внешний пользователь по README и примерам поднимает Panel + 2 ноды и получает `changed=0` на повторном прогоне.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, HARD-01, HARD-02, HARD-03, HARD-04, QA-04, QA-06, DOC-01, DOC-02, DOC-03
**Success Criteria** (what must be TRUE):
  1. Systemd-таймер снимает дампы Postgres и хранит последние N успешных; restore-playbook восстанавливает Panel из дампа, и это проверено в VM-тире
  2. Смена закреплённого тега образа в переменных обновляет компонент, перед этим автоматически снимается дамп; playbook отката возвращает предыдущий тег; `latest` нигде не используется
  3. Оператор получает оповещение (systemd OnFailure или документированный механизм), если сертификат Panel/ноды скоро истечёт или продление не удалось
  4. SSH ужесточён через drop-in с проверкой `sshd -t` без потери доступа, fail2ban с firewalld-action защищает SSH, dnf-automatic ставит security-обновления; каждый компонент отключается своей переменной
  5. По README (EN + ключевые гайды RU) и примеру inventory (Panel + 2 ноды, одна с LAN, пример vault) полный playbook разворачивается, повторный прогон даёт `changed=0` в CI-матрице ansible-core 2.21/2.22; справочник переменных сгенерирован из `argument_specs`
**Plans**: 3 plans (бэкапы/restore/обновления/откат + алерты по сертификатам; hardening; CI-матрица + full-playbook идемпотентность + документация и примеры)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Rootless-фундамент и тестовый стенд | 12/12 | Complete    | 2026-11-25 |
| 2. Panel за Traefik с защищённым входом | 12/12 | Complete    | 2026-11-28 |
| 3. Нода с Reality self-steal и авто-регистрацией | 0/3 | Not started | - |
| 4. Доступ в LAN для доверенного squad'а | 0/2 | Not started | - |
| 5. Эксплуатация, hardening и готовность к публикации | 0/3 | Not started | - |
