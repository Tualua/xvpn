---
phase: 02
review: 02-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "`$` in the regex accepts a trailing newline"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "The allowlist admits existing system directories, so \"dedicated\" is not enforced"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "Negative tests for the failure log dir assert are still missing"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "The accepted character set is undocumented"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "Маскирование в `fail` через `regex_replace` не скрывает значения и, вероятно, портит обратную ссылку"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Файл с логами в `/var/tmp` лежит бессрочно, под предсказуемым именем, а сообщение обещает его наличие безусловно"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "Задачи сбора журналов и логов контейнеров не имеют `no_log`"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "Регулярные выражения валидации допускают некорректные значения"
  - id: IN-04
    severity: info
    disposition: fixed
    title: "`ci_watch.sh` завершается без сообщения при сбое базовой выборки"
  - id: IN-05
    severity: info
    disposition: fixed
    title: "`check_no_log.py` проверяет только модули записи и не видит чтение секретных файлов"
  - id: IN-06
    severity: info
    disposition: fixed
    title: "`ci_watch.sh` сравнивает `createdAt` запуска с локальными часами"
  - id: IN-07
    severity: info
    disposition: fixed
    title: "Переменная `xvpn_panel_bootstrap_password_key` (necessity: generality without instantiation)"
open: 0
total: 12
recorded: 2026-11-27T02:24:38.144Z
---

# Phase 02: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 02-REVIEW-FIX.md |
| WR-02 | warning | fixed | 02-REVIEW-FIX.md |
| IN-01 | info | fixed | 02-REVIEW-FIX.md |
| IN-02 | info | fixed | 02-REVIEW-FIX.md |
| WR-03 | warning | fixed | 02-REVIEW-FIX.md (not in the current review) |
| WR-04 | warning | fixed | 02-REVIEW-FIX.md (not in the current review) |
| WR-05 | warning | fixed | 02-REVIEW-FIX.md (not in the current review) |
| IN-03 | info | fixed | 02-REVIEW-FIX.md (not in the current review) |
| IN-04 | info | fixed | 02-REVIEW-FIX.md (not in the current review) |
| IN-05 | info | fixed | 02-REVIEW-FIX.md (not in the current review) |
| IN-06 | info | fixed | 02-REVIEW-FIX.md (not in the current review) |
| IN-07 | info | fixed | 02-REVIEW-FIX.md (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
