# Requirements: xvpn.remnawave

**Defined:** 2026-11-23
**Core Value:** Из inventory одной командой получается рабочая, защищённая и идемпотентная инсталляция Remnawave на RHEL 10 с SELinux enforcing: Panel за прокси с защищённым входом, ноды автоматически зарегистрированы через API, Reality self-steal.

"Оператор" — пользователь коллекции (тот, кто запускает playbook). "Клиент" — конечный пользователь VPN.

## v1 Requirements

### Foundation (FND)

- [x] **FND-01**: Оператор получает понятную ошибку preflight, если хост не Rocky/Alma 10, SELinux не enforcing, Podman ниже 5.4 или порты 80/443 заняты
- [x] **FND-02**: Каждый сервис работает под выделенным rootless-пользователем с linger, subuid/subgid и доступным `systemctl --user` из Ansible
- [x] **FND-03**: Rootless-контейнеры могут слушать порты 80/443 (persistent sysctl `ip_unprivileged_port_start`), что проверяется в verify
- [x] **FND-04**: Quadlet-юниты рендерятся из шаблонов, проходят dry-run генератора, переживают перезагрузку хоста
- [x] **FND-05**: Роли настраивают firewalld и SELinux (контексты томов, booleans/порты только по доказанной необходимости) без перевода SELinux в permissive и без AVC-denial'ов
- [x] **FND-06**: Коллекция имеет `galaxy.yml` (`xvpn.remnawave`), `argument_specs` для всех ролей и Galaxy-ready структуру
- [x] **FND-07**: Preflight проверяет, что A-запись каждого домена указывает на IP внешнего интерфейса хоста (жёсткий fail, отключаемый флагом; детекция Cloudflare не делается — DNS в ответственности оператора)

### Edge / Traefik (EDGE)

- [x] **EDGE-01**: Traefik v3 работает как rootless Quadlet-сервис (host network, file provider, без Podman socket) на Panel- и Node-хостах
- [x] **EDGE-02**: Traefik получает сертификаты Let's Encrypt через HTTP-01 на порту 80 с переключателем staging/production и персистентным `acme.json`
- [x] **EDGE-03**: Traefik видит реальный IP клиента (проверяется по access log)

### Panel (PANEL)

- [x] **PANEL-01**: Оператор разворачивает Remnawave backend + Postgres + Valkey как Quadlet-юниты на приватной Podman-сети с healthcheck'ами и правильным порядком запуска
- [x] **PANEL-02**: Секреты панели (app/JWT-секреты, пароль Postgres, metrics-креды) генерируются один раз и не меняются при повторных прогонах
- [x] **PANEL-03**: Первый администратор создаётся на loopback до публикации роутера Traefik; повторный прогон логинится, а не регистрирует
- [x] **PANEL-04**: Коллекция создаёт долгоживущий API-токен для автоматизации и хранит его с правами 0600 на Panel-хосте
- [x] **PANEL-05**: Panel доступна через Traefik по HTTPS на собственном домене
- [x] **PANEL-06**: Админка закрыта cookie/secret-path гейтом: вход по секретному URL ставит cookie, без неё отдаётся сайт-заглушка (HTTP 200), UI и логин недоступны; подписки и API остаются доступными

### Subscription page (SUB)

- [x] **SUB-01**: Клиент открывает subscription page на отдельном домене через Traefik по HTTPS
- [x] **SUB-02**: Subscription page подключена к Panel через API-токен без ручных шагов

### Node (NODE)

- [ ] **NODE-01**: Оператор разворачивает remnanode (Xray) как rootless Quadlet-сервис с host network
- [ ] **NODE-02**: Порт API ноды (2222) доступен только с IP Panel (firewalld rich rule)
- [x] **NODE-03**: Клиент подключается к ноде по VLESS Reality (xtls-rprx-vision) на 443 и выходит в интернет

### Self-steal (STEAL)

- [x] **STEAL-01**: Reality `dest` указывает на loopback-entrypoint Traefik ноды с настоящим LE-сертификатом на домен ноды
- [x] **STEAL-02**: Неавторизованный посетитель (браузер, сканер) на 443 видит правдоподобный сайт-заглушку с валидным сертификатом домена ноды
- [x] **STEAL-03**: Запрос с чужим SNI или без SNI не раскрывает дефолтный сертификат/404 Traefik (проверяется `openssl s_client` в verify)
- [x] **STEAL-04**: Оператор выбирает сайт-заглушку из нескольких встроенных шаблонов или подставляет свой каталог
- [ ] **STEAL-05**: Reality-инбаунд включается только после того, как сертификат ноды выпущен и проверен

### Panel API (API)

- [x] **API-01**: Коллекция предоставляет Ansible-модули (`remnawave_config_profile`, `remnawave_node`, `remnawave_host`, `remnawave_internal_squad`) с поддержкой `check_mode`, `--diff` и честным `changed`
- [x] **API-02**: Нода из inventory автоматически регистрируется в Panel: config profile, node, SECRET_KEY, hosts — без ручных действий в UI
- [ ] **API-03**: Повторный прогон не создаёт дубликатов и не меняет Reality-ключи/shortIds (`changed=0`)
- [ ] **API-04**: Playbook ждёт, пока зарегистрированная нода перейдёт в состояние connected, с ограниченным числом попыток
- [ ] **API-05**: Оператор выводит ноду из эксплуатации (`state: absent` + явный флаг): нода и её hosts удаляются из Panel, юниты на хосте останавливаются

### LAN access (LAN)

- [ ] **LAN-01**: Нода имеет отдельный LAN-инбаунд на отдельном порту с собственными Reality-ключами и отдельный internal squad
- [ ] **LAN-02**: Клиент из LAN-squad'а получает доступ к объявленным в inventory приватным подсетям за нодой
- [ ] **LAN-03**: Клиент без LAN-доступа не может достучаться до приватных адресов, loopback, link-local и IP самой ноды (включая через домены, резолвящиеся в приватные IP)
- [ ] **LAN-04**: Негативные e2e-тесты подтверждают отсутствие LAN-утечек для обычных клиентов

### Operations (OPS)

- [ ] **OPS-01**: Postgres панели бэкапится по systemd-таймеру с ротацией (хранятся последние N успешных дампов)
- [ ] **OPS-02**: Отдельный restore-playbook восстанавливает Panel из дампа и проверен в тестах
- [ ] **OPS-03**: Оператор обновляет компоненты сменой закреплённых тегов образов в переменных; `latest` не используется
- [ ] **OPS-04**: Перед сменой тега образа автоматически снимается дамп БД; есть playbook отката на предыдущий тег
- [ ] **OPS-05**: Оператор получает оповещение (systemd OnFailure или документированный механизм), если сертификат ноды/Panel скоро истечёт или продление не удалось

### Hardening (HARD)

- [ ] **HARD-01**: SSH ужесточается через drop-in с валидацией `sshd -t` без риска потерять доступ
- [ ] **HARD-02**: fail2ban (EPEL) защищает SSH с firewalld-action
- [ ] **HARD-03**: dnf-automatic применяет security-обновления автоматически
- [ ] **HARD-04**: Каждый под-компонент hardening включается/выключается отдельной переменной

### Quality (QA)

- [x] **QA-01**: Каждая роль проходит ansible-lint и yamllint в CI
- [x] **QA-02**: Molecule: быстрый контейнерный тир (синтаксис, шаблоны, идемпотентность) для каждой роли
- [x] **QA-03**: Molecule: VM-тир на Alma/Rocky 10 с SELinux enforcing, проверкой нуля AVC, идемпотентности и перезагрузки
- [ ] **QA-04**: Повторный прогон полного playbook даёт `changed=0`
- [x] **QA-05**: CI использует Pebble (или LE staging), никогда не обращаясь к production Let's Encrypt
- [ ] **QA-06**: CI-матрица покрывает ansible-core 2.21 и 2.22

### Documentation (DOC)

- [ ] **DOC-01**: README на английском с quickstart; ключевые гайды продублированы на русском
- [ ] **DOC-02**: Примеры inventory/playbook (Panel + 2 ноды, одна с LAN) и пример vault-файла
- [ ] **DOC-03**: Справочник переменных генерируется из `argument_specs`
- [x] **DOC-04**: Токены и ключи не выводятся в логи (`no_log`); реальные секреты не хранятся в репозитории, placeholder'ы отвергаются assert'ом

## v2 Requirements

### Panel

- **PANEL-V2-01**: IP allowlist для админки как дополнительный/альтернативный гейт
- **PANEL-V2-02**: Интеграция с внешним forward-auth (tinyauth/Authelia)
- **PANEL-V2-03**: Экспозиция метрик Panel для Prometheus с basic auth

### API

- **API-V2-01**: Playbook ротации Reality-ключей/shortIds

### Operations

- **OPS-V2-01**: Offsite-бэкапы (S3/SFTP) с шифрованием age

## Out of Scope

| Feature | Reason |
|---------|--------|
| Ubuntu/Debian, EL8/EL9 | Фокус на EL10; Quadlet-возможности зависят от версии Podman |
| Docker / rootful compose | Выбран rootless Podman + Quadlet |
| DNS-01 / Cloudflare-токены | В v1 только HTTP-01 |
| Panel и Node на одном хосте | Конфликты 80/443 и Traefik; поддерживается только раздельная топология |
| Туннели до LAN (WireGuard и т.п.) | Нода физически стоит внутри LAN |
| SELinux permissive как «исправление» | Нарушает ключевое ограничение |
| Создание конечных пользователей/подписок, биллинг, Telegram-бот | Бизнес-данные оператора, не инфраструктура |
| Миграция с Marzban/3x-ui | Вне core value |
| Интерактивные мастера/bash-меню | Коллекция декларативная, управляется inventory |
| Обязательная публикация в Galaxy как критерий v1 | Метаданные Galaxy-ready, но релиз не входит в DoD v1 |
| Произвольный DSL маршрутизации Xray | Слишком большая поверхность; доступен override JSON профиля + LAN/private-блокировки |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | Phase 1 | Complete |
| FND-02 | Phase 1 | Complete |
| FND-03 | Phase 1 | Complete |
| FND-04 | Phase 1 | Complete |
| FND-05 | Phase 1 | Complete |
| FND-06 | Phase 1 | Complete |
| FND-07 | Phase 1 | Complete |
| EDGE-01 | Phase 2 | Complete |
| EDGE-02 | Phase 2 | Complete |
| EDGE-03 | Phase 2 | Complete |
| PANEL-01 | Phase 2 | Complete |
| PANEL-02 | Phase 2 | Complete |
| PANEL-03 | Phase 2 | Complete |
| PANEL-04 | Phase 2 | Complete |
| PANEL-05 | Phase 2 | Complete |
| PANEL-06 | Phase 2 | Complete |
| SUB-01 | Phase 2 | Complete |
| SUB-02 | Phase 2 | Complete |
| NODE-01 | Phase 3 | Pending |
| NODE-02 | Phase 3 | Pending |
| NODE-03 | Phase 3 | Complete |
| STEAL-01 | Phase 3 | Complete |
| STEAL-02 | Phase 3 | Complete |
| STEAL-03 | Phase 3 | Complete |
| STEAL-04 | Phase 3 | Complete |
| STEAL-05 | Phase 3 | Pending |
| API-01 | Phase 3 | Complete |
| API-02 | Phase 3 | Complete |
| API-03 | Phase 3 | Pending |
| API-04 | Phase 3 | Pending |
| API-05 | Phase 3 | Pending |
| LAN-01 | Phase 4 | Pending |
| LAN-02 | Phase 4 | Pending |
| LAN-03 | Phase 4 | Pending |
| LAN-04 | Phase 4 | Pending |
| OPS-01 | Phase 5 | Pending |
| OPS-02 | Phase 5 | Pending |
| OPS-03 | Phase 5 | Pending |
| OPS-04 | Phase 5 | Pending |
| OPS-05 | Phase 5 | Pending |
| HARD-01 | Phase 5 | Pending |
| HARD-02 | Phase 5 | Pending |
| HARD-03 | Phase 5 | Pending |
| HARD-04 | Phase 5 | Pending |
| QA-01 | Phase 1 | Complete |
| QA-02 | Phase 1 | Complete |
| QA-03 | Phase 1 | Complete |
| QA-04 | Phase 5 | Pending |
| QA-05 | Phase 2 | Complete |
| QA-06 | Phase 5 | Pending |
| DOC-01 | Phase 5 | Pending |
| DOC-02 | Phase 5 | Pending |
| DOC-03 | Phase 5 | Pending |
| DOC-04 | Phase 2 | Complete |

**Coverage:**
- v1 requirements: 54 total
- Mapped to phases: 54
- Unmapped: 0 ✓

---
*Requirements defined: 2026-11-23*
*Last updated: 2026-11-23 after roadmap creation*
