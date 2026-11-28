---
status: diagnosed
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md, 02-04-SUMMARY.md, 02-05-SUMMARY.md, 02-06-SUMMARY.md, 02-07-SUMMARY.md, 02-08-SUMMARY.md, 02-09-SUMMARY.md, 02-10-SUMMARY.md, 02-11-SUMMARY.md]
started: 2026-11-27T03:29:21Z
updated: 2026-11-27T13:56:58.183Z
---

## Current Test

[testing complete]

## Tests

### 1. Вход через гейт в реальном браузере
expected: Открыть https://<panel-domain>/ без cookie: отдаётся сайт-заглушка. Открыть секретный URL из /var/lib/xvpn/rw-panel/secrets/admin-url: ставится cookie и происходит переход на форму логина Remnawave. Вход логином rwoperator (или значением xvpn_panel_admin_username; пароль — admin_password из /var/lib/xvpn/rw-panel/secrets/panel-secrets.yml) проходит, админка работает. При xvpn_edge_acme_ca: staging браузер предупредит о недоверенном сертификате — это ожидаемо, предупреждение нужно принять.
result: pass

### 2. Production Let's Encrypt на реальном домене
expected: Прогон playbooks/panel.yml на реальном публичном домене с xvpn_edge_acme_ca: production выпускает сертификат production Let's Encrypt; Panel и subscription page открываются по HTTPS без предупреждений браузера.
result: issue
reported: "PLAY RECAP panel1 : ok=574 changed=2 unreachable=0 failed=0 skipped=420. Сертификат остался staging. Подозреваю, что нужно перезапустить контейнер с traefik. Сделать я это не смог, у юзера /sbin/nologin"
severity: major

### 3. Повторный прогон идемпотентен и не меняет секреты
expected: Второй запуск ansible-playbook playbooks/panel.yml на том же хосте завершается с changed=0; panel-secrets.yml, api-token и admin-url не меняются (sha256 до и после совпадает), вход в админку работает с прежним паролем.
result: pass

### 4. Subscription page на отдельном домене
expected: https://<sub-domain>/<shortUuid> существующего пользователя открывается по HTTPS без cookie гейта и показывает страницу подписки с данными пользователя из Panel; на домене Panel этот путь не открывает админку.
result: pass

### 5. Секреты не попадают в вывод
expected: В выводе ansible-playbook (в том числе с -v и --diff) нет паролей, JWT, API-токена и cookie-значения гейта; из admin-url печатается только путь к файлу. Файлы секретов имеют права 0600, каталог 0700.
result: pass

### 6. Защитные проверки входных данных
expected: Placeholder-домен (panel.example.com) или одинаковые домены Panel и subscription отклоняются до каких-либо изменений с понятным сообщением, где названа переменная; попытка задать через vault другой секрет на уже развёрнутом хосте отклоняется (ротация не выполняется молча).
result: pass
source: automated
note: по просьбе пользователя переведён в автотест; placeholder-домен, одинаковые домены (panel-same-domains, f111d61) и расхождение секрета с vault (panel-divergent-secret) проверяет container tier, отказ ротации admin_password проверяет VM tier (side_effect.yml); CI run 46009584443 success

### 7. Отключение subscription page
expected: С xvpn_panel_subscription_enabled: false повторный прогон останавливает юнит subscription page, затем удаляет юнит, subpage.env и файл маршрута; Panel продолжает работать. Возврат в true восстанавливает страницу подписки.
result: skipped
reason: пользователь не видит смысла в ручной проверке; удаление и восстановление юнита, subpage.env и маршрута покрыты автотестом panel-subpage-toggle (container tier)

### 8. README, раздел «Panel host»
expected: По разделу «Panel host» в README внешний пользователь понимает, какие переменные задать в inventory, как запустить playbooks/panel.yml, где найти admin-url, токен и логи, и какие есть известные ограничения.
result: pass

### 9. ci_watch.sh: ветки cancelled-run и dispatch
expected: scripts/ci_watch.sh ждёт именно запуск для текущего HEAD; если запуск был отменён (cancelled), выбирает новый запуск для того же HEAD, а не завершается с ложным результатом.
result: skipped
reason: внутренний dev-скрипт, не для оператора; ветку cancelled вручную не воспроизвести, скрипт работает в CI-потоке каждой фазы

### 10. Edge role renders hardened rootless Traefik unit, static config and 00-edge route file, passing the Quadlet generator dry-run
expected: Edge role renders hardened rootless Traefik unit, static config and 00-edge route file, passing the Quadlet generator dry-run
result: pass
source: automated
coverage_id: 02-01-D1

### 11. CI points the edge at the staging ACME CA only
expected: CI points the edge at the staging ACME CA only
result: pass
source: automated
coverage_id: 02-01-D2

### 12. Invalid edge inputs fail before any change (custom CA without server, bad route name)
expected: Invalid edge inputs fail before any change (custom CA without server, bad route name)
result: pass
source: automated
coverage_id: 02-01-D3

### 13. One-command panel.yml installs edge and the Panel-domain decoy route; the container tier runs it
expected: One-command panel.yml installs edge and the Panel-domain decoy route; the container tier runs it
result: pass
source: automated
coverage_id: 02-02-D1

### 14. check_acme_ca fails on a production CA pin in an edge converge (mutation-tested) and prints OK otherwise
expected: check_acme_ca fails on a production CA pin in an edge converge (mutation-tested) and prints OK otherwise
result: pass
source: automated
coverage_id: 02-02-D2

### 15. Placeholder Panel domain panel.example.com is rejected naming xvpn_panel_domain
expected: Placeholder Panel domain panel.example.com is rejected naming xvpn_panel_domain
result: pass
source: automated
coverage_id: 02-02-D3

### 16. VM converge of panel.yml serves the decoy through a Pebble-issued certificate
expected: After the VM converge of panel.yml, https://panel.xvpn.test/ serves the decoy through a Pebble-issued certificate (HTTP-01 on :80); idempotence changed=0, reboot, zero AVC
result: pass
source: automated
coverage_id: 02-03-D1

### 17. Strict SNI, :80 redirect/404, encoded-slash 400, acme.json 0600, listeners owned by rw-edge
expected: Strict SNI (no certificate for unknown or absent SNI), :80 redirect/404, /a%2Fb gives 400, acme.json 0600 owned by rw-edge, 80/443 listeners owned by the rw-edge uid
result: pass
source: automated
coverage_id: 02-03-D2

### 18. Traefik logs the real client address despite a forged X-Forwarded-For
expected: Traefik logs the controller address as ClientHost despite a forged X-Forwarded-For; cookie and path absent from the log
result: pass
source: automated
coverage_id: 02-03-D3

### 19. No scenario talks to production Let's Encrypt
expected: No scenario talks to production Let's Encrypt: the VM tier pins the ACME CA to Pebble on 127.0.0.1:14000
result: pass
source: automated
coverage_id: 02-03-D4

## Summary

total: 19
passed: 16
issues: 1
pending: 0
skipped: 2
blocked: 0

## Gaps

- truth: "Переключение xvpn_edge_acme_ca со staging на production и повторный прогон panel.yml дают production-сертификат Let's Encrypt"
  status: resolved
  resolved_by: 02-12-PLAN.md
  resolved_at: 2026-11-28
  reason: "User reported: PLAY RECAP panel1 : ok=574 changed=2 unreachable=0 failed=0 skipped=420. Сертификат остался staging. Подозреваю, что нужно перезапустить контейнер с traefik. Сделать я это не смог, у юзера /sbin/nologin"
  severity: major
  test: 2
  gap_id: 02-UAT-G1
  root_cause: "Traefik restarted correctly (changed=2 = traefik.yml re-render + restart_stale restart), but the le resolver keeps one storage file /acme/acme.json for every CA. Traefik reuses a stored certificate for a domain until it is within 30 days of expiry and never compares it with the configured caServer, so the staging certificate (valid ~90 days) keeps being served after switching xvpn_edge_acme_ca to production."
  artifacts:
    - path: "roles/edge/templates/traefik.yml.j2"
      issue: "storage: /acme/acme.json is the same file whatever xvpn_edge_acme_ca selects"
    - path: "roles/edge/tasks/main.yml"
      issue: "acme.json lookup/permission tasks hard-code the single file name"
  missing:
    - "Key the ACME storage file by the selected CA (e.g. acme-production.json, acme-staging.json, acme-custom-<hash of server>.json) so a CA switch starts from an empty store and issues new certificates, while switching back reuses the earlier store"
    - "Keep the 0600 permission task and the VM/container verifiers (acme.json 0600 check) pointed at the active file"
    - "Automated check that changing xvpn_edge_acme_ca changes the rendered storage path and restarts Traefik"
    - "README note on switching staging -> production"
  debug_session: ""
