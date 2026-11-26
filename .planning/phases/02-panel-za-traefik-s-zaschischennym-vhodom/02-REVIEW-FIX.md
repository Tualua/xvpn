---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
fixed_at: 2026-11-26T00:00:00Z
review_path: /workspaces/xvpn/.planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 2: отчёт об исправлениях по code review

**Исправлено:** 2026-11-26
**Исходный отчёт:** 02-REVIEW.md
**Итерация:** 1

**Итого:**
- Находок в области: 2 (WR-01, WR-02; Info вне области)
- Исправлено: 2
- Пропущено: 0

## Fixed Issues

### WR-01: Сообщение об ошибке запуска стека фильтрует логи чёрным списком по строкам

**Изменённые файлы:** `roles/panel/tasks/stack.yml`
**Коммит:** bb95cbc
**Что сделано:** журналы юнитов и логи контейнеров больше не попадают в вывод Ansible. В rescue они пишутся в root-only файл `/var/tmp/xvpn-panel-start-failure.log` (0600, `no_log: true`, `diff: false`). В сообщении `fail` остались только статус контейнеров (`podman ps -a`: имя и статус), путь к файлу и `ansible_failed_result.msg`, прогнанный через `regex_replace` по ключевым словам секретов (дополнительная защита, а не основная). Подстановку проверил отдельным плейбуком: `token=abc` и `password: x` маскируются.
**Статус:** fixed (логика сообщения проверена вручную, но стоит проверить на реальном падении старта).

### WR-02: `check_no_log.py` пропускает задачи с free-form аргументами

**Изменённые файлы:** `scripts/check_no_log.py`
**Коммит:** 1e31c28
**Что сделано:** добавлена функция `targets_secret_file`, разбирающая как dict-форму, так и строковую `src=... dest=... path=...`. Набор модулей расширен до `template`, `copy`, `lineinfile`, `blockinfile`, `ini_file`; проверяются ключи `src`, `dest`, `path`. `ansible.builtin.file` сознательно не включён: он меняет только права и владельца и не пишет содержимое, поэтому не может вывести секрет. В `self_test` добавлены 4 декоя (free-form template, lineinfile, free-form blockinfile, ini_file).
**Статус:** fixed: requires human verification (изменена логика проверки; решение не включать `file` стоит подтвердить).

## Проверка

- Место запуска: изолированный git worktree; затем fast-forward в `main`, worktree удалён.
- `ansible-lint` (профиль production, весь проект): 0 failures, 0 warnings, профиль production пройден. Одно информационное предупреждение окружения о второй установленной копии коллекции `xvpn.remnawave` в `~/.ansible/collections` не относится к правилам линтера.
- `scripts/check_no_log.py`: в системном `python3` PyYAML нет, поэтому запускал интерпретатором из venv ansible-lint (`/opt/uv-tools/ansible-lint/bin/python`), где PyYAML есть. Самотест и проход по `roles/*/tasks/*.yml` прошли: `check_no_log: OK`.
- `scripts/check.sh` целиком не запускался: он требует `python3` с PyYAML и падает на системном интерпретаторе. Утверждать, что он проходит, я не могу.

---

_Fixed: 2026-11-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
