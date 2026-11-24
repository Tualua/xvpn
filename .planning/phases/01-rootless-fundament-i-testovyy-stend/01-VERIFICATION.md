---
phase: 01-rootless-fundament-i-testovyy-stend
verified: 2026-11-24T10:00:00Z
status: human_needed
score: 4/4 must-haves verified
covered_files:
  - .github/workflows/molecule-vm.yml
  - extensions/molecule/preflight/converge.yml
  - extensions/molecule/vm/side_effect.yml
  - galaxy.yml
  - roles/common/tasks/firewalld.yml
  - roles/podman_rootless/tasks/main.yml
  - roles/preflight/tasks/main.yml
covered_digest: "v4:sha256:be11fd73d0da86e300ae0ee2d9471a6eb387da8044585fad371966a9d52e2c14"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Решить, делать ли molecule-vm обязательной проверкой слияния (branch protection)"
    expected: "После пяти подряд зелёных прогонов molecule-vm добавить в required checks; сейчас зелёный прогон один (45360051173)"
    why_human: "Решение о политике репозитория; в 01-12 SUMMARY зафиксировано как отложенное"
  - test: "Принять отклонение: бокс alma10 берётся из каталога Vagrant Cloud с закреплённой версией, без sha256-пина из репозитория"
    expected: "Оператор подтверждает приемлемость или требует sha256-пин"
    why_human: "Компромисс по цепочке поставок, решает человек"
  - test: "Решить судьбу 8 открытых предупреждений 01-REVIEW.md (WR-01..WR-08, все open)"
    expected: "Исправить в Phase 1 или явно перенести"
    why_human: "Приоритизация; на достижение цели фазы не влияют, но WR-01/WR-02/WR-03/WR-05 касаются безопасности и надёжности роли"
---

# Phase 1: Rootless-фундамент и тестовый стенд. Отчёт верификации

**Цель фазы:** Оператор запускает playbook на чистом Rocky/Alma 10 и получает проверенный rootless-хост: preflight отсекает неподходящие хосты, выделенный пользователь с linger запускает тестовый Quadlet-сервис на порту 80, который переживает перезагрузку при SELinux enforcing без AVC; всё проверяется в Molecule и CI-линтерах.
**Проверено:** 2026-11-24
**Статус:** human_needed (цель достигнута; остаются решения человека)
**Повторная верификация:** нет, первичная

## Достижение цели

### Наблюдаемые истины (ROADMAP Success Criteria)

| # | Истина | Статус | Доказательство |
|---|--------|--------|----------------|
| 1 | Preflight падает с понятным сообщением на не-EL10, SELinux не Enforcing, Podman < 5.4, занятых 80/443, неверной A-записи, ничего не изменив | VERIFIED | `roles/preflight/tasks/main.yml` собирает ошибки и один раз вызывает `fail`; чеки ОС, getenforce, `check_podman.yml`, `check_ports.yml`, `check_dns.yml`. `playbooks/foundation.yml`: первый play это preflight с `any_errors_fatal`. Сценарий `extensions/molecule/preflight` имеет кейсы os/selinux/podman-floor/port-foreign/port-unmanaged/dns-mismatch/dns-unresolvable/dns-disabled; verify проверяет read-only allow-list модулей и отсутствие изменений на хосте. Сценарий в матрице molecule-container (зелёный) |
| 2 | Тестовый Quadlet-сервис под rootless-пользователем слушает :80, управляется через `systemctl --user` из Ansible, поднимается после reboot | VERIFIED | `side_effect.yml`: `systemd_service scope: user state: restarted` с проверкой нового InvocationID; `reboot` и ожидание `is-active` до 60x10 с. VM-прогон 45360051173: converge, идемпотентный прогон (changed=0), reboot, verify (ok=83 changed=0) на alma10 |
| 3 | VM-тир Alma10 и Rocky10 (SELinux enforcing): converge, idempotence changed=0, reboot, ноль AVC; firewalld открывает только нужные порты | VERIFIED | Run 45360051173, job `vm (alma10)` и `vm (rocky10)` оба success; в логе "Assert zero AVC denials since the marker" до и после reboot, dontaudit отключён и проверен, контрольная сумма бинарной политики сверяется после reboot. `verify_common.yml` проверяет точное совпадение портов зоны, список сервисов, отсутствие внутренних портов 3000/3010/8443/2222, SSH остаётся доступным |
| 4 | Контейнерный тир, ansible-lint и yamllint проходят в CI; коллекция собирается из `galaxy.yml`; у ролей есть `argument_specs` | VERIFIED | На HEAD-коммите a73aa2a `lint` (45364037493) и `molecule-container` (45364037508) success. `ansible-galaxy collection build` собрал `xvpn-remnawave-0.1.0.tar.gz`. `argument_specs.yml` есть у common, podman_rootless, preflight |

**Счёт:** 4/4 истин подтверждено.

### Требования

| Требование | Статус | Доказательство |
|------------|--------|----------------|
| FND-01 | SATISFIED | Роль preflight, сценарий preflight (кейсы выше) |
| FND-02 | SATISFIED | `podman_rootless/tasks/user.yml`: пользователь uid>=1000, nologin, home 0700, subuid check; linger и `systemctl --user` подтверждены в VM-verify |
| FND-03 | SATISFIED | sysctl drop-in `ip_unprivileged_port_start`; `verify_rootless.yml` биндует :443 под rw-edge и отрицательный контроль :79 (EACCES), до и после reboot |
| FND-04 | SATISFIED | `quadlet_validate.yml` (dry-run генератора) до LSR podman; VM-тир подтверждает переживание reboot |
| FND-05 | SATISFIED | `common/tasks/firewalld.yml`, sefcontext для home root; AVC=0 в VM-прогоне, SELinux Enforcing |
| FND-06 | SATISFIED | `galaxy.yml` (`xvpn.remnawave`), `argument_specs` для 3 ролей, сборка проходит |
| FND-07 | SATISFIED | `check_dns.yml` сравнивает A-записи с IP интерфейса или `xvpn_public_ip`, отключается `xvpn_preflight_dns_check`; CDN-детекции нет. Проверено в контейнерном сценарии с подменой резолвинга; на реальном внешнем IP не проверялось |
| QA-01 | SATISFIED | `lint.yml` зелёный на HEAD (после правки двух line-length ошибок в a73aa2a) |
| QA-02 | SATISFIED | `molecule-container.yml`, матрица container + preflight, зелёная |
| QA-03 | SATISFIED | `molecule-vm.yml`, run 45360051173 |

Все 10 ID из PLAN frontmatter найдены в REQUIREMENTS.md и отмечены Complete; осиротевших требований Phase 1 нет (QA-04/05/06 привязаны к фазам 2 и 5).

### Анти-паттерны

TBD/FIXME/XXX в roles, extensions, playbooks, .github, scripts: не найдено. Стабов нет.

### Замечания

- Lint был красным на коммитах 5017478..2314474 и docs(01-12) 45361546115, исправлен a73aa2a; на HEAD зелёный. Последующие коммиты только документация.
- Прогон molecule-vm единственный зелёный (до него три красных/отменённых при отладке); устойчивость не доказана статистикой.
- Открытые ревью-предупреждения WR-01..WR-08 (0 critical) не блокируют цель, но WR-01 (усыновление существующего аккаунта), WR-02 (`..` в home_root), WR-03 (restorecon только при изменении sefcontext), WR-05 (SELinux-гейт после установки пакетов при автономном запуске роли), WR-07 (необработанная ошибка DNS-шаблона при отсутствии фактов интерфейса) стоит решить до публикации.

### Требуется решение человека

1. Политика required check для molecule-vm (после пяти зелёных прогонов).
2. Приемлемость бокса alma10 без sha256-пина репозитория.
3. Распределение 8 открытых предупреждений ревью.

---

_Проверено: 2026-11-24_
_Верификатор: Claude (gsd-verifier)_
