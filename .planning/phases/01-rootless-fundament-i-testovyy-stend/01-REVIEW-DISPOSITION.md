---
phase: 01
review: 01-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Валидация `xvpn_podman_rootless_home_root` обходится сегментом `.` и неполным denylist (недоработка WR-02 прошлого ревью)"
  - id: WR-02
    severity: warning
    disposition: open
    title: "SELinux-гейт теперь стоит до установки `libselinux-utils`, при отсутствии `getenforce` ошибка вводит в заблуждение"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Защита от «усыновления» аккаунта не сверяет явно заданный `uid`"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Негативный контроль «порт 79 привилегирован» ломается при допустимых значениях sysctl"
  - id: IN-01
    severity: info
    disposition: open
    title: "Ветка AAAA в `check_dns.yml` не получила того же укрепления, что A-ветка (WR-07)"
  - id: IN-02
    severity: info
    disposition: open
    title: "В verify зашиты пользователь и домашний путь при параметризованном sysctl"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "SELinux-гейт в роли `common` стоит после установки пакетов и не защищает `podman_rootless` при отдельном запуске"
  - id: WR-06
    severity: warning
    disposition: fixed
    title: "Валидация Quadlet изолирует спеки одного вызова, поэтому юниты со ссылками на `.network`/`.volume` из другого вызова будут ложно отклонены; проверка «ожидаемый сервис» подстрочная"
  - id: WR-07
    severity: warning
    disposition: fixed
    title: "Проверка DNS в preflight падает необработанной ошибкой шаблона, если факты выбранного интерфейса отсутствуют"
  - id: WR-08
    severity: warning
    disposition: skipped
    title: "Воркфлоу `molecule-vm` ставит vagrant-libvirt и ключ HashiCorp без проверки отпечатка и запускается на каждом PR"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "SSH-гейт использует `ansible_port` контроллера, а не порт sshd на целевом хосте"
  - id: IN-04
    severity: info
    disposition: fixed
    title: "Слабые проверки в `verify_rootless.yml` для sysctl"
  - id: IN-05
    severity: info
    disposition: fixed
    title: "`xvpn_podman_rootless_unprivileged_port_start` не ограничен"
  - id: IN-06
    severity: info
    disposition: fixed
    title: "Дублирование запусков CI и строгие `suboptions` спецификации"
open: 5
total: 14
recorded: 2026-11-24T11:57:19.508Z
---

# Phase 01: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | fixed | 01-REVIEW-FIX.md |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| WR-05 | warning | fixed | 01-REVIEW-FIX.md (not in the current review) |
| WR-06 | warning | fixed | 01-REVIEW-FIX.md (not in the current review) |
| WR-07 | warning | fixed | 01-REVIEW-FIX.md (not in the current review) |
| WR-08 | warning | skipped | 01-REVIEW-FIX.md (not in the current review) |
| IN-03 | info | fixed | 01-REVIEW-FIX.md (not in the current review) |
| IN-04 | info | fixed | 01-REVIEW-FIX.md (not in the current review) |
| IN-05 | info | fixed | 01-REVIEW-FIX.md (not in the current review) |
| IN-06 | info | fixed | 01-REVIEW-FIX.md (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
