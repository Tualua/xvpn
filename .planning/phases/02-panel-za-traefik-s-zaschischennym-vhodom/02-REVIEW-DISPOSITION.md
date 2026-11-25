---
phase: 02
review: 02-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Частичный `panel-secrets.yml` проходит проверку целостности, недостающие секреты генерируются заново"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Rescue-ветка стека печатает логи контейнеров и journal в `fail_msg` без фильтрации"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Регулярка FQDN отвергает punycode-TLD (`xn--p1ai` и т. п.), вопреки README"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Проверка DOC-04 (`check_no_log.py`) не видит секреты, которые приходят только через `.j2`-шаблон"
  - id: WR-05
    severity: warning
    disposition: open
    title: "Сигнал \"конфигурация изменилась\" теряется при сбое между рендером и рестартом"
  - id: IN-01
    severity: info
    disposition: open
    title: "Лишние рестарты при первой установке"
  - id: IN-02
    severity: info
    disposition: open
    title: "Канарейка AVC для Pebble считает любую ошибку `ausearch` чистым результатом"
  - id: IN-03
    severity: info
    disposition: open
    title: "`shuffle` использует не криптографический ГСЧ при сборке паролей"
  - id: IN-04
    severity: info
    disposition: open
    title: "Якорь `$` в regex-форматах секретов допускает хвостовой перевод строки"
  - id: IN-05
    severity: info
    disposition: open
    title: "Часть операторских значений интерполируется в YAML Traefik без валидации"
  - id: IN-06
    severity: info
    disposition: open
    title: "`ci_watch.sh` сравнивает `createdAt` запуска с локальными часами"
  - id: IN-07
    severity: info
    disposition: open
    title: "Переменная `xvpn_panel_bootstrap_password_key` (necessity: generality without instantiation)"
open: 12
total: 12
recorded: 2026-11-25T18:37:39.166Z
---

# Phase 02: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
