---
phase: 02
review: 02-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Частичный `panel-secrets.yml` проходит проверку целостности, недостающие секреты генерируются заново"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Rescue-ветка стека печатает логи контейнеров и journal в `fail_msg` без фильтрации"
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
  - id: IN-01
    severity: info
    disposition: fixed
    title: "Лишние рестарты при первой установке"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "Канарейка AVC для Pebble считает любую ошибку `ausearch` чистым результатом"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "`shuffle` использует не криптографический ГСЧ при сборке паролей"
  - id: IN-04
    severity: info
    disposition: fixed
    title: "Якорь `$` в regex-форматах секретов допускает хвостовой перевод строки"
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
open: 0
total: 12
recorded: 2026-11-26T07:18:52.355Z
---

# Phase 02: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 02-REVIEW-FIX.md |
| WR-02 | warning | fixed | 02-REVIEW-FIX.md |
| WR-03 | warning | fixed | 02-REVIEW-FIX.md |
| WR-04 | warning | fixed | 02-REVIEW-FIX.md |
| WR-05 | warning | fixed | 02-REVIEW-FIX.md |
| IN-01 | info | fixed | 02-REVIEW-FIX.md |
| IN-02 | info | fixed | 02-REVIEW-FIX.md |
| IN-03 | info | fixed | 02-REVIEW-FIX.md |
| IN-04 | info | fixed | 02-REVIEW-FIX.md |
| IN-05 | info | fixed | 02-REVIEW-FIX.md |
| IN-06 | info | fixed | 02-REVIEW-FIX.md |
| IN-07 | info | fixed | 02-REVIEW-FIX.md |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
