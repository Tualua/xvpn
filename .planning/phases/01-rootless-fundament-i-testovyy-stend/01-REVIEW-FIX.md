---
phase: 01-rootless-fundament-i-testovyy-stend
fixed_at: 2026-11-24T00:00:00Z
review_path: .planning/phases/01-rootless-fundament-i-testovyy-stend/01-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 1: Отчёт об исправлениях по code review

**Fixed at:** 2026-11-24
**Source review:** .planning/phases/01-rootless-fundament-i-testovyy-stend/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (fix_scope: critical_warning; IN-01 и IN-02 вне области)
- Fixed: 4
- Skipped: 0

Проверка: после каждого исправления выполнялся `bash scripts/check.sh` (lint, yamllint, syntax-check, сборка) в основном checkout, без worktree (запуск на ветке main). Результат: `check.sh: OK` для всех четырёх. Molecule локально недоступен (нет podman/VM), его прогонит CI.

## Fixed Issues

### WR-01: Валидация `xvpn_podman_rootless_home_root` обходится сегментом `.` и неполным denylist (недоработка WR-02 прошлого ревью)

**Files modified:** `roles/podman_rootless/tasks/main.yml`
**Commit:** 3282765
**Applied fix:** regex сегментов сужен до `[A-Za-z0-9_-]+` (точки запрещены целиком, проверка `'..'` стала лишней и убрана); denylist расширен (`/var/log`, `/var/cache`, `/var/tmp`, `/var/run`, `/var/spool`, `/usr/local`, `/usr/bin`, `/usr/sbin`, `/usr/lib`, `/usr/lib64`, `/usr/share`, `/var/lib/containers`, `/var/lib/systemd`, `/var/lib/selinux`). Выбран вариант «убрать `.`», а не allowlist, чтобы не ограничивать допустимые корни. Подкаталоги других системных каталогов (например `/etc/ssh`) по-прежнему проходят; полный allowlist остаётся решением владельца.
Статус: fixed: requires human verification (логика валидации).

### WR-02: SELinux-гейт теперь стоит до установки `libselinux-utils`, при отсутствии `getenforce` ошибка вводит в заблуждение

**Files modified:** `roles/common/tasks/main.yml`, `roles/podman_rootless/tasks/main.yml`
**Commit:** eb8c45e
**Applied fix:** перед проверкой Enforcing добавлена отдельная задача `fail`, срабатывающая при `getenforce.rc != 0`, с сообщением «getenforce is unavailable or failed; install libselinux-utils ...». Теперь отсутствие бинаря отличается от режима не-Enforcing.
Статус: fixed: requires human verification (логика гейта).

### WR-03: Защита от «усыновления» аккаунта не сверяет явно заданный `uid`

**Files modified:** `roles/podman_rootless/tasks/user.yml`
**Commit:** e448be3
**Applied fix:** в assert добавлено условие, что заданный `uid` совпадает с текущим uid существующей учётной записи; текст `fail_msg` обновлён.
Статус: fixed: requires human verification (логика условия).

### WR-04: Негативный контроль «порт 79 привилегирован» ломается при допустимых значениях sysctl

**Files modified:** `extensions/molecule/shared/verify_rootless.yml`
**Commit:** 12333db
**Applied fix:** порт для негативной проверки берётся как `xvpn_verify_sysctl_value - 1`; проба и assert пропускаются при значении 1 (порта ниже нет). Имена задач и сообщение обновлены.
Статус: fixed: requires human verification (проверяется только Molecule в CI).

---

_Fixed: 2026-11-24_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
