---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
reviewed: 2026-11-26T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - extensions/molecule/vm/tasks/pebble.yml
  - roles/edge/tasks/main.yml
  - roles/panel/defaults/main.yml
  - roles/panel/meta/argument_specs.yml
  - roles/panel/tasks/bootstrap.yml
  - roles/panel/tasks/main.yml
  - roles/panel/tasks/secrets.yml
  - roles/panel/tasks/stack.yml
  - roles/panel/tasks/subpage.yml
  - roles/podman_rootless/meta/argument_specs.yml
  - roles/podman_rootless/tasks/restart_stale.yml
  - scripts/check_no_log.py
  - scripts/ci_watch.sh
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
  necessity: 0
status: issues_found
---

# Phase 2: Code Review Report (инкрементальный повторный обзор)

**Reviewed:** 2026-11-26
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Просмотрены изменённые хунки fix-коммитов WR-01..WR-05 и IN-01..IN-07 и контекст файлов целиком. Критических дефектов и регрессий, ломающих сценарии первой установки или идемпотентность, не найдено. Новый механизм `restart_stale` логически корректен: на первой установке файл рендерится до старта юнита, поэтому повторного рестарта нет. Для уже запущенного юнита решение принимается по mtime. Для юнита, который не запускался, действует запасной вариант по флагу `changed`. Ссылки на удалённую переменную `xvpn_panel_bootstrap_password_key` в репозитории отсутствуют. Пути в `xvpn_podman_rootless_restart_files` совпадают с путями рендера.

Остались два предупреждения: фильтр секретов в сообщении об ошибке и слепая зона `check_no_log.py`. Остальное носит информационный характер.

Ограничение: `scripts/check_no_log.py` не удалось выполнить локально, потому что в окружении нет PyYAML (и pip). Корректность проверена чтением кода. Grep по `template` и `copy` с `.env` и `/secrets/` показал, что все такие задачи в `roles/panel/tasks` имеют `no_log: true` и `diff: false`, поэтому ложных срабатываний новой проверки по пути не ожидается.

## Warnings

### WR-01: Сообщение об ошибке запуска стека фильтрует логи чёрным списком по строкам

**File:** `roles/panel/tasks/stack.yml:101-107`
**Issue:** `fail` выводит журнал и логи контейнеров, отфильтрованные по ключевым словам (`reject('search', 'token|password|...')`). Это denylist. Строки логов Postgres и backend, которые содержат значение секрета без этих слов, пройдут фильтр. Пример: эхо строки подключения без `DATABASE_URL`, значение `POSTGRES_USER` или дамп env `podman inspect`. Вывод попадает в stdout Ansible и в CI-логи публичной коллекции. Кроме того, `ansible_failed_result.msg` подставляется без фильтра. Задача без `no_log` выводит всё вместе с `msg`.
**Fix:** Выводить из логов только то, что нужно для диагностики. Например, последние N строк со статусом юнита (`systemctl status` без env), без `podman logs` и `podman inspect`. Либо хранить полный вывод в файле `0600` на хосте и показывать в сообщении только путь к нему. Фильтр оставить как дополнительную защиту, а не как основную.

### WR-02: `check_no_log.py` пропускает задачи с free-form аргументами

**File:** `scripts/check_no_log.py:65-69`
**Issue:** Проверка по пути работает, только если `args = task.get(module)` является `dict`. Free-form форма `ansible.builtin.template: src=x.env.j2 dest=.../a.env` (строка) даёт `by_path = False`, поэтому задача проходит без `no_log`. Самотест декоя этого варианта не покрывает. Проверка также не ловит `ansible.builtin.file`, `lineinfile` и `blockinfile` над env-файлами и `secrets/`, то есть другие пути записи секретов.
**Fix:** Обработать строковую форму: если `args` является `str`, искать `SECRET_FILE` в значениях `src=`/`dest=`. Добавить декой со строковыми аргументами в `self_test`. Расширить множество модулей на `lineinfile`, `blockinfile`, `ini_file`.

## Info

### IN-01: `restart_stale` сравнивает mtime и старт юнита с точностью до секунды

**File:** `roles/podman_rootless/tasks/restart_stale.yml:55-56`
**Issue:** `stat.mtime` (float) приводится к `int`, а `ExecMainStartTimestamp` с `--timestamp=unix` имеет секундную точность. Файл, изменённый в ту же секунду, но после старта юнита, не считается новее (`select('gt', ...)`). Окно узкое, но именно оно и должно «лечиться» этим механизмом. Если `systemctl show` падает (`failed_when: false`), `started` становится 0 и решает флаг `changed`. Тогда юнит, запущенный в этом же прогоне, получит лишний рестарт, от которого IN-01 как раз избавлял.
**Fix:** Использовать `select('ge', started)` для запущенного юнита. Либо брать `ExecMainStartTimestampMonotonic` или микросекундный `--timestamp=us` и сравнивать с дробным mtime. Ненулевой `rc` команды стоит различать: падение `systemctl show` не должно приравниваться к «юнит не запускался».

### IN-02: Проверка неизменяемых ключей игнорирует значения из vault

**File:** `roles/panel/tasks/secrets.yml:77-97`
**Issue:** Если на хосте частично повреждённый или ручной `panel-secrets.yml`, а недостающие immutable-ключи заданы vault-переопределениями, assert всё равно падает, хотя в слияние попадут заданные значения. Поведение консервативное и безопасное, но сообщение предлагает только восстановление из бэкапа.
**Fix:** Вычитать из списка отсутствующих ключей ключи из `xvpn_panel_secrets_overrides`, либо дополнить `fail_msg` подсказкой, что ключ можно задать через vault.

### IN-03: Регулярные выражения валидации допускают некорректные значения

**File:** `roles/panel/tasks/main.yml:6,15`, `roles/edge/tasks/main.yml:12-14`
**Issue:** (1) Ветка `xn--[a-z0-9-]{1,59}` принимает метки с завершающим дефисом (`xn--abc-`) и значение `xn--` без содержимого; такой TLD недействителен. (2) Адрес точки входа принимает порт больше 65535 (`:99999`) и пустой хост. (3) Регулярка email допускает `a@b` без точки и метки вроде `..`. Ошибка проявится только на стороне Traefik или ACME, а не в понятном assert.
**Fix:** Для punycode: `xn--[a-z0-9]([a-z0-9-]{0,57}[a-z0-9])?`. Для адреса дополнительно проверять `(address.split(':')[-1] | int) <= 65535`. Для email требовать точку в доменной части.

### IN-04: `ci_watch.sh` завершается без сообщения при сбое базовой выборки

**File:** `scripts/ci_watch.sh:25-28`
**Issue:** При `set -euo pipefail` падение `gh run list` внутри `BASE="$(select_run max)"` (сеть, лимиты API) завершает скрипт с кодом без пояснения. До правки такая же выборка была отложена до цикла ожидания и повторялась. Теперь диспатч не выполнится, но причина останется неочевидной.
**Fix:** `BASE="$(select_run max)" || { echo "ci-watch: cannot read the baseline of runs" >&2; exit 1; }`.

---

_Reviewed: 2026-11-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
