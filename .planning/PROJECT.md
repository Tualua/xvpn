# xvpn.remnawave — Ansible-коллекция для Remnawave

## What This Is

Публичная Ansible-коллекция `xvpn.remnawave` с ролями для развёртывания Remnawave Panel и Remnawave Node на Rocky/Alma/Oracle Linux 10 (SELinux enforcing, rootless Podman + Quadlet). Ноды используют VLESS Reality в режиме self-steal: Reality указывает на собственный домен ноды, за ним стоит правдоподобный сайт-заглушка. Отдельная группа клиентов может через ноду выходить во внутреннюю сеть (LAN), в которой стоит нода. Коллекция предназначена для сообщества (open source) и для любого, кто поднимает Remnawave на RHEL-совместимых хостах.

## Core Value

Из inventory одной командой получается рабочая, защищённая и идемпотентная инсталляция Remnawave: Panel за прокси с защищённым входом, ноды автоматически зарегистрированы через API, Reality self-steal без внешних «чужих» доменов, и всё это работает на RHEL 10 с SELinux enforcing без ослабления безопасности.

## Requirements

### Validated

- ✓ Rootless-фундамент: preflight (ОС, SELinux enforcing, Podman >= 5.4, порты, DNS), выделенный пользователь с linger/subuid, порты 80/443 через sysctl, Quadlet переживает перезагрузку без AVC — Phase 1
- ✓ Каркас коллекции `xvpn.remnawave` (galaxy.yml, argument_specs) и тестовый стенд: ansible-lint/yamllint, Molecule container-тир и VM-тир (Alma/Rocky 10, SELinux enforcing) в CI — Phase 1
- ✓ Роль Panel: Remnawave backend 3.4.11 + Postgres 18.4 + Valkey 9 в rootless Podman (Quadlet), первый админ и API-токен через API — Phase 2
- ✓ Panel за Traefik v3.7.20 с TLS Let's Encrypt (HTTP-01), отдельное хранилище ACME на каждый CA; проверено на production-хосте — Phase 2
- ✓ Защита входа в админку: cookie/secret-path гейт на Traefik — Phase 2
- ✓ Subscription page 8.0.1 на отдельном домене за Traefik, включается и выключается переменной — Phase 2

### Active

- [ ] Бэкапы Postgres панели по расписанию с ротацией
- [ ] Роль Node: remnanode (Xray) в rootless Podman + Quadlet
- [ ] Автоматическая регистрация ноды в Panel через API: создание ноды, получение секрета, inbound'ов и конфиг-профиля
- [ ] Self-steal: Reality `dest` указывает на локальный Traefik ноды с настоящим сертификатом своего домена; сайт-заглушка и fallback для неавторизованных подключений
- [ ] Выпуск сертификата ноды через HTTP-01 на 80 порту (443 занят Xray)
- [ ] Доступ в LAN: отдельный inbound/internal squad, пользователи которого маршрутизируются в объявленные приватные подсети; остальные пользователи в LAN не попадают
- [ ] Firewalld и SELinux настраиваются ролями (порты, контексты, правила), SELinux остаётся enforcing
- [ ] Hardening хоста: SSH, fail2ban, автоматические обновления безопасности
- [ ] Идемпотентность: повторный прогон даёт `changed=0`
- [ ] Обновление версий компонентов через переменные (теги образов) без ручных действий
- [ ] Molecule-сценарии и CI (lint + тесты) для всех ролей

### Out of Scope

- Ubuntu/Debian и RHEL 8/9 — целевая платформа только EL10; расширение позже при запросе сообщества
- Rootful Docker / Docker CE — выбран rootless Podman + Quadlet как нативный для RHEL
- DNS-01 и другие ACME-челленджи — в v1 только HTTP-01
- Туннели до LAN (WireGuard, reverse tunnel) — нода физически стоит внутри LAN
- Panel и Node на одном хосте — поддерживаемая топология: Panel отдельно, N нод на других хостах
- Публикация в Ansible Galaxy как критерий готовности v1 — коллекция публичная, но релиз в Galaxy не входит в definition of done v1

## Context

- Remnawave — панель управления прокси на базе Xray-core (VLESS/Reality и др.). Официально поставляется как docker compose (Panel: backend + Postgres + Redis; Node: контейнер remnanode, обычно `network_mode: host`). Для rootless Podman + Quadlet compose нужно адаптировать.
- Self-steal: Reality маскируется под собственный сайт на том же хосте, а не под сторонний домен. Требуется настоящий сертификат на домен ноды и локальный TLS-терминатор (здесь Traefik), куда Xray проксирует неавторизованный трафик.
- Rootless Podman и порты ниже 1024 (80/443): нужен `net.ipv4.ip_unprivileged_port_start` или иной механизм; сеть контейнера ноды (host/pasta) влияет на сохранение IP клиента и доступ в LAN.
- Traefik выбран, потому что он привычнее пользователю. Его пригодность для self-steal (TLS-терминация за Xray, HTTP-01 при занятом 443) нужно подтвердить на этапе исследования.
- Изначально в рабочей директории есть только `.devcontainer/`.

## Constraints

- **Платформа**: Rocky Linux 10 / AlmaLinux 10 / Oracle Linux 10 (ядро UEK по умолчанию) — целевые ОС v1
- **Безопасность**: SELinux enforcing обязателен, permissive не допускается
- **Рантайм**: rootless Podman + Quadlet (systemd user units), без Docker
- **Прокси**: Traefik, если технически подходит для self-steal и Panel; иначе решение пересматривается с обоснованием
- **TLS**: Let's Encrypt через HTTP-01 на порту 80
- **Топология**: Panel на отдельном хосте, ноды на других хостах
- **Качество**: идемпотентность, Molecule + CI, ansible-lint
- **Публичность**: коллекция open source и должна быть понятна внешним пользователям (README, примеры inventory)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Только EL10 (Rocky/Alma/Oracle) | Фокус на одной современной платформе | — Pending |
| Rootless Podman + Quadlet вместо Docker | Нативно для RHEL, systemd-интеграция, меньше привилегий | ✓ Good — Phase 1: тестовый Quadlet на порту 80 переживает reboot на VM-тире |
| SELinux enforcing | Не ослаблять безопасность хоста | ✓ Good — Phase 1: ноль AVC на VM-тире, гейт Enforcing до изменений хоста |
| Traefik как reverse proxy | Привычен пользователю | ✓ Good для Panel — Phase 2 (гейт, LE, sub-page); для self-steal проверяется в Phase 3 |
| HTTP-01 для сертификатов | Не нужны ключи DNS-провайдера | ✓ Good — Phase 2: production LE на реальном хосте, Pebble в CI |
| Авто-регистрация нод через Panel API | Минимум ручных шагов | — Pending |
| Доступ в LAN через отдельный inbound/squad | Изоляция: в LAN попадают только доверенные пользователи | — Pending |
| Panel на отдельном хосте | Типичная топология пользователя | ✓ Good — Phase 2: playbooks/panel.yml разворачивает Panel-хост одной командой |
| Имя коллекции `xvpn.remnawave` (временное) | Сменить перед публикацией | — Pending |
| Отдельный файл ACME-хранилища на каждый CA (acme-production/staging/custom-<hash>.json) | Traefik не перевыпускает сертификат при смене caServer, пока старый не близок к истечению (UAT G1); legacy acme.json не мигрируется | ✓ Good — Phase 2, план 02-12 |
| Gate (gitleaks) запускается на каждый пуш; lint и Molecule пропускают пуши только с .planning/Markdown | Экономия CI без потери проверки секретов (review WR-01, решение пользователя 2026-11-28) | ✓ Принято |
| Общение GSD/Claude с пользователем на русском (`response_language: ru`) | Предпочтение пользователя; код и технические термины на английском | ✓ Good |
| Rocky 10 в VM-тире Molecule — официальный libvirt Vagrant box с dl.rockylinux.org (версионированный, sha256 из CHECKSUM), а не nightly cloud-image job из CLAUDE.md | D-18 требует Alma и Rocky в самом VM-тире; box `rockylinux/10` в Vagrant Cloud устарел. Принято пользователем 2026-11-23 (Phase 1, планы 01-11/01-12) | ✓ Принято |
| CI Phase 1 только на ansible-core 2.21; нога 2.22 отложена до QA-06 (Phase 5), а не матрица {2.21, 2.22} из CLAUDE.md | Сознательное отступление от CLAUDE.md: фокус Phase 1 на фундаменте и VM-тире; `check.sh` локально уже идёт на 2.22. Решение пользователя 2026-11-24, D-23 (Phase 1, план 01-09) | ✓ Принято |
| Traefik на Panel-хосте в `Network=host` (а не pasta, как в таблице стека CLAUDE.md) и образ `traefik:v3.7.20` вместо пина v3.7.19 | `Network=host` нужен для EDGE-01 (реальный IP клиента, бинд 80/443, доступ к сервисам на 127.0.0.1) и входит в зону усмотрения Claude по CONTEXT фазы 2. В v3.7.20 закрыты три advisory (02-RESEARCH). При AVC-отказе нужна эскалация через `checkpoint:decision`, а не тихий boolean (планы 02-01, 02-03) | ✓ Good — Phase 2: ноль AVC на VM-тире, реальный IP клиента в логах |
| Oracle Linux 10 добавлен как целевая ОС | Реальный деплой упал в preflight на OL10. Покрытие: container-тир на docker.io/library/oraclelinux:10, VM-тир на официальном libvirt box yum.oracle.com b710 (пин sha256) | ✓ Good — container- и VM-тир OL10 зелёные; production-деплой на OL10 работает |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-11-28 after Phase 2*
