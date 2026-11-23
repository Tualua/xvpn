# Phase 1: Rootless-фундамент и тестовый стенд - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-23
**Phase:** 01-rootless-fundament-i-testovyy-stend
**Areas discussed:** Preflight: DNS и NAT, Пользователи и роли, Тестовый сервис и firewalld, Galaxy-роли для Podman, Molecule и CI

---

## Preflight: DNS и NAT

| Option | Description | Selected |
|--------|-------------|----------|
| Внешний IP (auto) / override | Определять внешний IP через сервис, override переменной | |
| Только явно в inventory | Оператор указывает публичный IP | |
| IP интерфейса хоста | ansible_default_ipv4 | |

**User's choice:** (free text) Нода имеет 2 интерфейса — внутренний и внешний.

| Option | Description | Selected |
|--------|-------------|----------|
| Default route + override | ansible_default_ipv4, override `xvpn_public_interface`/`xvpn_public_ip` | ✓ |
| Явно в inventory | Без автоопределения | |
| Любой IP хоста | Совпадение с любым адресом | |

| Option | Description | Selected |
|--------|-------------|----------|
| Публичный резолвер + диапазоны CF | | |
| Системный резолвер | | |
| С controller | | |

**User's choice:** (free text) Не нужно определять проксирование. Настройка DNS — задача оператора.

| Option | Description | Selected |
|--------|-------------|----------|
| Warning | | |
| Жёсткий fail с отключением | `xvpn_preflight_dns_check: false` | ✓ |
| Убрать полностью | | |

| Option | Description | Selected |
|--------|-------------|----------|
| По владельцу процесса | ss -ltnp, rw-* — ок | ✓ |
| Только при первом прогоне | Маркер-файл | |

---

## Пользователи и роли

| Option | Description | Selected |
|--------|-------------|----------|
| По домену доверия (rw-edge/rw-panel/rw-node) | | ✓ |
| Один пользователь на хост | | |
| По одному на контейнер | | |

| Option | Description | Selected |
|--------|-------------|----------|
| preflight + common + podman_rootless | | ✓ |
| common (включая preflight) + podman_rootless | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Обычные UID, nologin, /var/lib/xvpn | | ✓ |
| Обычные UID, home в /home | | |
| На усмотрение Claude | | |

---

## Тестовый сервис и firewalld

| Option | Description | Selected |
|--------|-------------|----------|
| Фикстура только в Molecule | | ✓ |
| Плейбук smoke-test в коллекции | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Только добавляет своё | | ✓ |
| Авторитарно | | |
| Авторитарно опцией | | |

| Option | Description | Selected |
|--------|-------------|----------|
| SSH не трогаем, LAN в фазе 4 | | ✓ |
| Настраиваемый SSH-порт уже сейчас | | |

---

## Galaxy-роли для Podman (вопрос пользователя)

**User's question:** Возможно, в Galaxy есть роли по установке и настройке podman — стоит ли их использовать, чтобы не изобретать велосипед?
**Findings:** `fedora.linux_system_roles.podman` (Red Hat, Quadlet, rootless, linger); мелкие community-роли (safeaim, voidquark) отвергнуты.

| Option | Description | Selected |
|--------|-------------|----------|
| LSR podman, если research подтвердит | Иначе свой тонкий хелпер с обоснованием | ✓ |
| Всегда LSR podman | | |
| Свой хелпер | | |

---

## Molecule и CI

**User's question:** Обязательно ли нужен KVM? dind нельзя обойтись?
**Answer:** Нет — SELinux/AVC/booleans/reboot требуют собственного ядра; контейнерный тир остаётся для быстрых проверок.

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub-hosted KVM + локально | | ✓ |
| Облачные VM (delegated) | | |
| Только локально | | |

| Option | Description | Selected |
|--------|-------------|----------|
| На усмотрение Claude | | ✓ |
| Vagrant + libvirt | | |
| Delegated + cloud-образы | | |

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub + GitHub Actions | | ✓ |
| GitLab CI | | |

## Claude's Discretion

- Драйвер VM для Molecule
- Резолвер для проверки A-записи
- LSR firewall/selinux vs ansible.posix
- Формат сообщений preflight, структура переменных

## Deferred Ideas

- LAN-интерфейс и firewalld-зона — Phase 4
- Управление SSH — Phase 5
