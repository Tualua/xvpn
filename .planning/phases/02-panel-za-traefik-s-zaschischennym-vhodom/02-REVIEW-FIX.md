---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
fixed_at: 2026-11-26T12:00:00Z
review_path: /workspaces/xvpn/.planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-REVIEW.md
iteration: 2
findings_in_scope: 12
fixed: 12
skipped: 0
status: all_fixed
---

# Phase 2: отчёт об исправлении замечаний code review

**Исправлено:** 2026-11-26
**Исходный отчёт:** 02-REVIEW.md
**Итерация:** 2

**Итог:**
- В области: 12 (WR-01..WR-05 из итерации 1, IN-01..IN-07 из итерации 2)
- Исправлено: 12
- Пропущено: 0

Проверка: `scripts/check.sh` пройден (`check.sh: OK`) в основном рабочем дереве (worktree не создавался), после всех исправлений итерации 2. gitleaks локально не установлен, проверяется только в CI. Molecule локально не запускался.

## Fixed Issues

### WR-01: Частичный `panel-secrets.yml` проходит проверку целостности, недостающие секреты генерируются заново

**Файлы:** `roles/panel/tasks/secrets.yml`
**Коммиты:** 9032e4a, 312a6d1 (доработка: в тексте сообщения assert не должно быть имён секретов, иначе `check_no_log.py` требует `no_log`, а он скрыл бы сообщение)
**Что сделано:** если файл существует, он обязан содержать все неизменяемые ключи (`app_secret`, `postgres_password`, `metrics_user`, `metrics_password`, `admin_password`). Вердикт считается булевым `set_fact` с `no_log`, затем assert без секретов. Ключи gate можно докомплектовывать генерацией.
**Статус:** fixed: requires human verification (логика условия; в Molecule нет негативного кейса на частичный файл).

### WR-02: Rescue-ветка стека печатает логи контейнеров и journal в `fail_msg` без фильтрации

**Файлы:** `roles/panel/tasks/stack.yml`
**Коммит:** 89bc1b4
**Что сделано:** journal и логи контейнеров идут через `stdout_lines | reject('search', '(?i)token|bearer|authorization|jwt|password|secret|DATABASE_URL|APP_SECRET|METRICS_PASS')`. Выражение проверено на тестовом плейбуке.

### WR-03: Регулярка FQDN отвергает punycode-TLD (`xn--p1ai` и т. п.), вопреки README

**Файлы:** `roles/panel/tasks/main.yml`
**Коммит:** 1af7039
**Что сделано:** TLD теперь `([a-z]{2,63}|xn--[a-z0-9-]{1,59})` для `xvpn_panel_domain` и `xvpn_subscription_domain`. Проверено на `a.xn--p1ai`, `a.b-.com`. Вынос в общую переменную не делался (две строки, пересечения с preflight нет).

### WR-04: Проверка DOC-04 (`check_no_log.py`) не видит секреты, которые приходят только через `.j2`-шаблон

**Файлы:** `scripts/check_no_log.py`
**Коммит:** 6aae78b
**Что сделано:** добавлен `xvpn_panel_sp_token` в `SENSITIVE`; любая задача `template`/`copy`, у которой `src`/`dest` оканчивается на `.env` / `.env.j2` или лежит в `/secrets/`, обязана иметь `no_log` и `diff: false`. Добавлен самотест с задачами-приманками, выполняется перед сканом; если приманка не поймана, проверка падает. Существующие роли проходят без правок.

### WR-05: Сигнал "конфигурация изменилась" теряется при сбое между рендером и рестартом

**Файлы:** `roles/podman_rootless/tasks/restart_stale.yml` (новый), `roles/podman_rootless/meta/argument_specs.yml`, `roles/panel/tasks/stack.yml`, `roles/panel/tasks/subpage.yml`, `roles/edge/tasks/main.yml`
**Коммит:** c389b83
**Что сделано (вариант (a) из ревью):** общий `tasks_from: restart_stale` сравнивает mtime файлов конфигурации с временем старта главного процесса юнита (`systemctl --user show --property=ExecMainStartTimestamp --timestamp=unix`). Устаревший юнит перезапускается, повторный прогон даёт `changed=0`. Охвачены `postgres.env`, `backend.env`, `subpage.env`, `traefik.yml` + `ca.pem`, `decoy default.conf`.
**Статус:** fixed: requires human verification. Реальное поведение `systemctl --timestamp=unix` на EL10 и идемпотентность подтверждает только Molecule VM.

### IN-01: Лишние рестарты при первой установке

**Файлы:** `roles/podman_rootless/tasks/restart_stale.yml`, `roles/podman_rootless/meta/argument_specs.yml`
**Коммит:** 56a1355
**Что сделано:** решение в `restart_stale` теперь опирается на времена файлов для уже стартовавшего юнита. Файл, отрендеренный до старта юнита (первая установка: деплой стартует юнит после рендера), не считается устаревшим, поэтому повторного рестарта сразу после initdb нет. Флаг `changed` из прогона учитывается только для юнита, который ещё ни разу не стартовал (пустой timestamp). Реальное обновление env у работающего юнита по-прежнему ведёт к рестарту (mtime новее старта). Одно общее изменение покрывает panel, sub-page и edge. Описание в `argument_specs` обновлено.
**Статус:** fixed: requires human verification (логика сравнения времён; подтверждается только Molecule VM: первый converge без второго рестарта БД, второй converge `changed=0`, `touch` файла вызывает рестарт).

### IN-02: Канарейка AVC для Pebble считает любую ошибку `ausearch` чистым результатом

**Файлы:** `extensions/molecule/vm/tasks/pebble.yml`
**Коммит:** 2232b12
**Что сделано:** assert требует `item.rc == 1` и `item.stderr is search('<no matches>')`, как итоговый gate в `verify_runtime.yml`.

### IN-03: `shuffle` использует не криптографический ГСЧ при сборке паролей

**Файлы:** `roles/panel/tasks/secrets.yml`
**Коммит:** 78fd357
**Что сделано:** `shuffle` убран. Пароли `postgres_password`, `metrics_password` (32 символа) и `admin_password` (40 символов) тянутся одним вызовом `lookup('password')` по `ascii_letters + digits`, с повтором (`until`, до 50 раз), пока в значении нет строчных, заглавных и цифр. Тест на локальном плейбуке: три значения сгенерированы, задачи с `no_log`. Форматы и длины соответствуют проверкам `xvpn_panel_secret_formats`.

### IN-04: Якорь `$` в regex-форматах секретов допускает хвостовой перевод строки

**Файлы:** `roles/panel/tasks/secrets.yml`
**Коммит:** 5caba09
**Что сделано:** во всех форматах `xvpn_panel_secret_formats` `$` заменён на `\Z`. Проверено: значение с хвостовым `\n` отвергается, без него принимается.

### IN-05: Часть операторских значений интерполируется в YAML Traefik без валидации

**Файлы:** `roles/edge/tasks/main.yml`
**Коммит:** 1d96510
**Что сделано:** email проверяется `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\Z`, адреса `xvpn_edge_http_address` / `xvpn_edge_https_address` проверяются `^[0-9A-Za-z.:\[\]-]*:[0-9]{1,5}\Z`. Допустимые значения по умолчанию и из `scripts/gate/render.yml` (`:80`, `:443`, `:8080`, `:8443`) проходят; кавычки и переводы строк отвергаются. Текст `fail_msg` обновлён.

### IN-06: `ci_watch.sh` сравнивает `createdAt` запуска с локальными часами

**Файлы:** `scripts/ci_watch.sh`
**Коммит:** cd36f19
**Что сделано:** запуски различаются по `databaseId`: перед `gh workflow run` запоминается максимальный id запусков для HEAD, после диспетчеризации выбирается запуск с большим id. Сравнение с локальными часами убрано. `bash -n` пройден; живой запуск не выполнялся (CI не диспетчеризовался).

### IN-07: Переменная `xvpn_panel_bootstrap_password_key` (necessity: generality without instantiation)

**Файлы:** `roles/panel/defaults/main.yml`, `roles/panel/meta/argument_specs.yml`, `roles/panel/tasks/bootstrap.yml`
**Коммит:** 8ba3739
**Что сделано:** переменная удалена из defaults и argument_specs (она была помечена как internal, публичный интерфейс не затронут), сообщение об ошибке логина теперь говорит "the stored admin credential" (текст без имени ключа, иначе `check_no_log.py` требует `no_log` на задаче `fail`). `xvpn_panel_api_token_probe_route` не трогалась: у неё потребители в bootstrap и она остаётся общей точкой для проверки токена.
**Статус:** fixed: requires human verification (удаление кода, решение о границах за человеком).

## Что проверяется только в CI

- IN-01 / WR-05: `molecule-vm` (rootless Podman + `systemd --user`). Смотреть: первый converge без второго рестарта Postgres, второй converge `changed=0`, `touch` env-файла перезапускает юнит.
- WR-01: ни один сценарий не создаёт частичный секрет-файл; негативный кейс можно добавить в `container/verify.yml`.
- IN-02: `molecule-vm` prepare (Pebble AVC канарейка).
- gitleaks: только CI.

---

_Fixed: 2026-11-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
