---
phase: 01
review: 01-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "Роль «усыновляет» любую существующую учётную запись с uid >= 1000 и перезаписывает её shell, пароль и home"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Валидация `xvpn_podman_rootless_home_root` допускает `..` и системные каталоги, затем идут chmod/chown и рекурсивный restorecon"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "`restorecon` запускается только если `sefcontext` изменился, поэтому прерванный первый прогон оставляет неверные метки навсегда"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Задача `lint` в `lint.yml` не имеет `timeout-minutes`"
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
  - id: IN-01
    severity: info
    disposition: fixed
    title: "Повторная SSH-проверка «after» в `firewalld.yml` недостижима для падения"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "Проверка конфликта портов в preflight учитывает только TCP"
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
open: 0
total: 14
recorded: 2026-11-24T10:23:51.526Z
---

# Phase 01: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | 01-REVIEW-FIX.md |
| WR-02 | warning | fixed | 01-REVIEW-FIX.md |
| WR-03 | warning | fixed | 01-REVIEW-FIX.md |
| WR-04 | warning | fixed | 01-REVIEW-FIX.md |
| WR-05 | warning | fixed | 01-REVIEW-FIX.md |
| WR-06 | warning | fixed | 01-REVIEW-FIX.md |
| WR-07 | warning | fixed | 01-REVIEW-FIX.md |
| WR-08 | warning | skipped | 01-REVIEW-FIX.md |
| IN-01 | info | fixed | 01-REVIEW-FIX.md |
| IN-02 | info | fixed | 01-REVIEW-FIX.md |
| IN-03 | info | fixed | 01-REVIEW-FIX.md |
| IN-04 | info | fixed | 01-REVIEW-FIX.md |
| IN-05 | info | fixed | 01-REVIEW-FIX.md |
| IN-06 | info | fixed | 01-REVIEW-FIX.md |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
