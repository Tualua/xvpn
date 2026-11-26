---
phase: 02
review: 02-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Сообщение об ошибке запуска стека фильтрует логи чёрным списком по строкам"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "`check_no_log.py` пропускает задачи с free-form аргументами"
  - id: IN-01
    severity: info
    disposition: open
    title: "`restart_stale` сравнивает mtime и старт юнита с точностью до секунды"
  - id: IN-02
    severity: info
    disposition: open
    title: "Проверка неизменяемых ключей игнорирует значения из vault"
  - id: IN-03
    severity: info
    disposition: open
    title: "Регулярные выражения валидации допускают некорректные значения"
  - id: IN-04
    severity: info
    disposition: open
    title: "`ci_watch.sh` завершается без сообщения при сбое базовой выборки"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "Регулярка FQDN отвергает punycode-TLD (`xn--p1ai` и т. п.), вопреки README"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Проверка DOC-04 (`check_no_log.py`) не видит секреты, которые приходят только через `.j2`-шаблон"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "Сигнал \"конфигурация изменилась\" теряется при сбое между рендером и рестартом"
  - id: IN-05
    severity: info
    disposition: fixed
    title: "Часть операторских значений интерполируется в YAML Traefik без валидации"
  - id: IN-06
    severity: info
    disposition: fixed
    title: "`ci_watch.sh` сравнивает `createdAt` запуска с локальными часами"
  - id: IN-07
    severity: info
    disposition: fixed
    title: "Переменная `xvpn_panel_bootstrap_password_key` (necessity: generality without instantiation)"
open: 4
total: 12
recorded: 2026-11-26T11:58:32.234Z
---

# Phase 02: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 02-REVIEW-FIX.md |
| WR-02 | warning | fixed | 02-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| WR-03 | warning | fixed | 02-REVIEW-FIX.md (not in the current review) |
| WR-04 | warning | fixed | 02-REVIEW-FIX.md (not in the current review) |
| WR-05 | warning | fixed | 02-REVIEW-FIX.md (not in the current review) |
| IN-05 | info | fixed | 02-REVIEW-FIX.md (not in the current review) |
| IN-06 | info | fixed | 02-REVIEW-FIX.md (not in the current review) |
| IN-07 | info | fixed | 02-REVIEW-FIX.md (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
