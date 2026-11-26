---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
fixed_at: 2026-11-26T00:00:00Z
review_path: /workspaces/xvpn/.planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 7
skipped: 1
status: partial
---

# Phase 2: отчёт об исправлениях по code review

**Fixed at:** 2026-11-26
**Source review:** /workspaces/xvpn/.planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8
- Fixed: 7
- Skipped: 1

Проверки после правок (запускались в основном каталоге, worktree не создавался: изменения небольшие, а ансибл-линт в worktree без окружения ненадёжен):
- `ansible-lint` (профиль production): 0 failure(s), 0 warning(s), "Profile 'production' was required, and it passed".
- `/opt/uv-tools/ansible-lint/bin/python scripts/check_no_log.py` (включая self-test): `check_no_log: OK`. Мутационная проверка: при `no_log: false` на `slurp` секретов скрипт падает, как и ожидается.
- Регулярные выражения IN-03 проверены отдельным маленьким playbook на localhost (`a@b`, `xn--`, `xn--abc-`, порт 99999 отклоняются, `xn--p1ai`, `a@b.co`, `:8443` проходят).
- Molecule/VM-прогон не выполнялся.

## Fixed Issues

### WR-05: Задачи сбора журналов и логов контейнеров не имеют `no_log`

**Files modified:** `roles/panel/tasks/stack.yml`
**Commit:** 399d4e5
**Applied fix:** `no_log: true` добавлен в задачи `journalctl` и `podman logs`/`inspect`. Зарегистрированные переменные остаются доступны для записи в файл.

### WR-03: Маскирование в `fail` через `regex_replace` не скрывает значения и, вероятно, портит обратную ссылку

**Files modified:** `roles/panel/tasks/stack.yml`
**Commit:** 381a3cd
**Applied fix:** Выбран упрощённый дизайн: `ansible_failed_result.msg` больше не выводится совсем, маскирующий `regex_replace` (с неработающей обратной ссылкой) удалён. Сообщение содержит имя упавшей задачи (`ansible_failed_task.name`) и статус контейнеров. Поскольку фильтра больше нет, проверять обратную ссылку на localhost не потребовалось.

### WR-04: Файл с логами в `/var/tmp` лежит бессрочно, под предсказуемым именем, а сообщение обещает его наличие безусловно

**Files modified:** `roles/panel/tasks/stack.yml`
**Commit:** 3dc0d3f
**Applied fix:** Логи пишутся в `/var/log/xvpn/panel-start-failure.log` (каталог `root:root 0700`, файл `0600`). Путь указывается в сообщении только если запись удалась (`register` + `is succeeded`), иначе сообщение отправляет к `journalctl`. После успешного старта стека старый файл удаляется отдельной задачей. WR-03, WR-04, WR-05 закоммичены отдельными коммитами.

### IN-02: Проверка неизменяемых ключей игнорирует значения из vault

**Files modified:** `roles/panel/tasks/secrets.yml`
**Commit:** 46873cb
**Applied fix:** Вычитать ключи overrides нельзя: `xvpn_panel_secrets_overrides` формируется позже по ходу файла. Поэтому дополнен `fail_msg`: поясняет, что vault-переопределения применяются после проверки и не заменяют недостающие immutable-ключи, файл нужно восстановить.

### IN-03: Регулярные выражения валидации допускают некорректные значения

**Files modified:** `roles/panel/tasks/main.yml`, `roles/edge/tasks/main.yml`
**Commit:** 91d62f3
**Applied fix:** Punycode-TLD теперь `xn--[a-z0-9]([a-z0-9-]{0,57}[a-z0-9])?`; добавлена проверка порта адресов точек входа `<= 65535`; email требует точку в доменной части. Пустой хост в адресе (`:80`) оставлен намеренно: для Traefik это допустимая запись.

### IN-04: `ci_watch.sh` завершается без сообщения при сбое базовой выборки

**Files modified:** `scripts/ci_watch.sh`
**Commit:** 9334529
**Applied fix:** `BASE="$(select_run max)" || { echo "ci-watch: cannot read the baseline of runs" >&2; exit 1; }`. Синтаксис проверен `bash -n`.

### IN-05: `check_no_log.py` проверяет только модули записи и не видит чтение секретных файлов

**Files modified:** `scripts/check_no_log.py`
**Commit:** 97ade02
**Applied fix:** Добавлены `READER_MODULES` (`slurp`, `fetch`) с проверкой только `no_log`, модули записи расширены (`replace`, `assemble`, `get_url`), пути секретных файлов распознаются и по переменным `xvpn_*secrets_file` / `xvpn_*api_token_file`. В self-test добавлены три декоя. Текущие задачи `slurp` проходят проверку.

## Skipped Issues

### IN-01: `restart_stale` сравнивает mtime и старт юнита с точностью до секунды

**File:** `roles/podman_rootless/tasks/restart_stale.yml:55-56`
**Reason:** skipped: замена `gt` на `ge` или различение `rc` `systemctl show` меняет баланс между пропуском рестарта и лишним рестартом Postgres сразу после initdb, а проверить это можно только на VM-уровне (SELinux, `systemd --user`), который в этой сессии недоступен. Риск регрессии выше пользы для узкого окна в одну секунду; оставлено на отдельное решение.
**Original issue:** Сравнение mtime и `ExecMainStartTimestamp` идёт с секундной точностью, а падение `systemctl show` приравнивается к «юнит не запускался».

---

_Fixed: 2026-11-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
