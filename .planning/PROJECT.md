# xvpn.remnawave — Ansible-коллекция для Remnawave

## What This Is

Публичная Ansible-коллекция `xvpn.remnawave` с ролями для развёртывания Remnawave Panel и Remnawave Node на Rocky/Alma Linux 10 (SELinux enforcing, rootless Podman + Quadlet). Ноды используют VLESS Reality в режиме self-steal: Reality указывает на собственный домен ноды, за ним стоит правдоподобный сайт-заглушка. Отдельная группа клиентов может через ноду выходить во внутреннюю сеть (LAN), в которой стоит нода. Коллекция предназначена для сообщества (open source) и для любого, кто поднимает Remnawave на RHEL-совместимых хостах.

## Core Value

Из inventory одной командой получается рабочая, защищённая и идемпотентная инсталляция Remnawave: Panel за прокси с защищённым входом, ноды автоматически зарегистрированы через API, Reality self-steal без внешних «чужих» доменов, и всё это работает на RHEL 10 с SELinux enforcing без ослабления безопасности.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Роль Panel: Remnawave backend + Postgres + Redis в rootless Podman (Quadlet-юниты systemd)
- [ ] Panel опубликована через Traefik с TLS (Let's Encrypt, HTTP-01) на собственном домене
- [ ] Защита входа в админку: скрытый путь, cookie-auth или IP allowlist
- [ ] Subscription page на отдельном домене за Traefik
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

- **Платформа**: Rocky Linux 10 / AlmaLinux 10 — единственная целевая ОС v1
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
| Только EL10 (Rocky/Alma) | Фокус на одной современной платформе | — Pending |
| Rootless Podman + Quadlet вместо Docker | Нативно для RHEL, systemd-интеграция, меньше привилегий | — Pending |
| SELinux enforcing | Не ослаблять безопасность хоста | — Pending |
| Traefik как reverse proxy | Привычен пользователю | — Pending (проверить для self-steal) |
| HTTP-01 для сертификатов | Не нужны ключи DNS-провайдера | — Pending |
| Авто-регистрация нод через Panel API | Минимум ручных шагов | — Pending |
| Доступ в LAN через отдельный inbound/squad | Изоляция: в LAN попадают только доверенные пользователи | — Pending |
| Panel на отдельном хосте | Типичная топология пользователя | — Pending |
| Имя коллекции `xvpn.remnawave` (временное) | Сменить перед публикацией | — Pending |
| Общение GSD/Claude с пользователем на русском (`response_language: ru`) | Предпочтение пользователя; код и технические термины на английском | ✓ Good |
| Rocky 10 в VM-тире Molecule — официальный libvirt Vagrant box с dl.rockylinux.org (версионированный, sha256 из CHECKSUM), а не nightly cloud-image job из CLAUDE.md | D-18 требует Alma и Rocky в самом VM-тире; box `rockylinux/10` в Vagrant Cloud устарел. Принято пользователем 2026-11-23 (Phase 1, планы 01-11/01-12) | ✓ Принято |
| CI Phase 1 только на ansible-core 2.21; нога 2.22 отложена до QA-06 (Phase 5), а не матрица {2.21, 2.22} из CLAUDE.md | Сознательное отступление от CLAUDE.md: фокус Phase 1 на фундаменте и VM-тире; `check.sh` локально уже идёт на 2.22. Решение пользователя 2026-11-24, D-23 (Phase 1, план 01-09) | ✓ Принято |

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
*Last updated: 2026-11-23 after Phase 1 planning (Rocky VM box decision)*
