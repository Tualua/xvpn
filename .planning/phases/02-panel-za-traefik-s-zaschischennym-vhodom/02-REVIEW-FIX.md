---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
fixed_at: 2026-11-26T00:00:00Z
review_path: /workspaces/xvpn/.planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 2: отчёт об исправлении замечаний code review

**Исправлено:** 2026-11-26
**Исходный отчёт:** 02-REVIEW.md
**Итерация:** 1

**Итог:**
- В области: 5 (WR-01..WR-05; Info не входили)
- Исправлено: 5
- Пропущено: 0

Проверка: `scripts/check.sh` пройден (`check.sh: OK`) в изолированном worktree; gitleaks локально не установлен, проверяется только в CI. Molecule локально не запускался.

## Исправленные замечания

### WR-01: частичный `panel-secrets.yml` проходил проверку целостности

**Файлы:** `roles/panel/tasks/secrets.yml`
**Коммиты:** 9032e4a, 312a6d1 (доработка: в тексте сообщения assert не должно быть имён секретов, иначе `check_no_log.py` требует `no_log`, а он скрыл бы сообщение)
**Что сделано:** если файл существует, он обязан содержать все неизменяемые ключи (`app_secret`, `postgres_password`, `metrics_user`, `metrics_password`, `admin_password`). Вердикт считается булевым `set_fact` с `no_log`, затем assert без секретов. Ключи gate можно докомплектовывать генерацией.
**Статус:** fixed: requires human verification (логика условия; в Molecule нет негативного кейса на частичный файл).

### WR-02: сырые логи в `fail_msg` rescue-ветки

**Файлы:** `roles/panel/tasks/stack.yml`
**Коммит:** 89bc1b4
**Что сделано:** journal и логи контейнеров идут через `stdout_lines | reject('search', '(?i)token|bearer|authorization|jwt|password|secret|DATABASE_URL|APP_SECRET|METRICS_PASS')`. Выражение проверено на тестовом плейбуке.

### WR-03: punycode-TLD отвергались

**Файлы:** `roles/panel/tasks/main.yml`
**Коммит:** 1af7039
**Что сделано:** TLD теперь `([a-z]{2,63}|xn--[a-z0-9-]{1,59})` для `xvpn_panel_domain` и `xvpn_subscription_domain`. Проверено на `a.xn--p1ai`, `a.b-.com`. Вынос в общую переменную не делался (две строки, пересечения с preflight нет).

### WR-04: `check_no_log.py` не видел секреты, приходящие через `.env`-шаблоны

**Файлы:** `scripts/check_no_log.py`
**Коммит:** 6aae78b
**Что сделано:** добавлен `xvpn_panel_sp_token` в `SENSITIVE`; любая задача `template`/`copy`, у которой `src`/`dest` оканчивается на `.env` / `.env.j2` или лежит в `/secrets/`, обязана иметь `no_log` и `diff: false`. Добавлен самотест с задачами-приманками, выполняется перед сканом; если приманка не поймана, проверка падает. Существующие роли проходят без правок.

### WR-05: сигнал "конфигурация изменилась" терялся при сбое между рендером и рестартом

**Файлы:** `roles/podman_rootless/tasks/restart_stale.yml` (новый), `roles/podman_rootless/meta/argument_specs.yml`, `roles/panel/tasks/stack.yml`, `roles/panel/tasks/subpage.yml`, `roles/edge/tasks/main.yml`
**Коммит:** c389b83
**Выбранный подход (вариант (a) из ревью, без маркер-файлов):** общий `tasks_from: restart_stale` читает `systemctl --user show --property=ExecMainStartTimestamp --timestamp=unix <unit>` и сравнивает целую часть mtime файлов конфигурации с временем старта главного процесса. Юнит перезапускается, если `changed` в этом прогоне ИЛИ какой-либо файл новее запущенного процесса. Юнит, который ни разу не стартовал (пустой timestamp), не считается устаревшим: первый старт за деплоем. После рестарта timestamp новее файла, повторный прогон даёт `changed=0`. Охвачены: `postgres.env`, `backend.env`, `subpage.env`, `traefik.yml` + `ca.pem`, `decoy default.conf`. Спецификация аргументов добавлена в `argument_specs` для `restart_stale`.
**Статус:** fixed: requires human verification. Логика выбора проверена на тестовом плейбуке (тест `gt`, разбор timestamp), но реальное поведение `systemctl --timestamp=unix` на EL10 и идемпотентность подтверждает только Molecule VM.
**Замечание:** IN-01 (лишний рестарт при первой установке) не затронут: при `changed` на первой установке рестарт по-прежнему происходит.

## Что проверяется только в CI

- WR-05: `molecule-vm` (rootless Podman + `systemd --user`; в container-уровне `activate` отключён, и рестарт не выполняется). Смотреть: второй converge `changed=0`, а также что принудительно старый unit (touch файла) перезапускается.
- WR-01: ни один сценарий не создаёт частичный секрет-файл; негативный кейс можно добавить в `container/verify.yml` по образцу `panel-secrets-lost-with-volume`.
- gitleaks: только CI.

---

_Fixed: 2026-11-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
