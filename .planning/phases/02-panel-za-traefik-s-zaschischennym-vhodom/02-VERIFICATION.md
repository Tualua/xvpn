---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
verified: 2026-11-26T07:00:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files: [".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-01-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-01-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-02-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-02-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-03-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-03-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-04-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-04-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-05-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-05-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-06-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-06-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-07-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-07-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-08-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-08-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-09-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-09-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-10-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-10-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-11-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-11-SUMMARY.md", "playbooks/panel.yml", "roles/edge/tasks/main.yml", "roles/edge/templates/traefik.yml.j2", "roles/panel/tasks/bootstrap.yml", "roles/panel/tasks/main.yml", "roles/panel/tasks/secrets.yml", "roles/panel/tasks/stack.yml", "roles/panel/tasks/subpage.yml", "roles/panel/templates/panel-routes.yml.j2", "roles/podman_rootless/tasks/restart_stale.yml", "scripts/check_no_log.py"]
covered_digest: "v4:sha256:7b69b08653188a541f1f4eea500afbe7968e5c96cb158bbb3cb86e6d9d8bcc11"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Открыть в реальном браузере https://<panel-domain>/<gate_path> (путь из admin-url файла на Panel-хосте), затем войти логином admin"
    expected: "Секретный URL ставит cookie и ведёт на форму логина; без cookie отдаётся сайт-заглушка; логин проходит"
    why_human: "Автотесты (curl из Molecule VM) проверяют cookie/redirect/decoy, но не живой браузерный поток и SameSite-поведение"
  - test: "Прогнать playbooks/panel.yml на реальном публичном домене с xvpn_edge_acme_ca: production"
    expected: "Выпускается сертификат production Let's Encrypt, Panel и subscription page открываются по HTTPS"
    why_human: "CI по требованию QA-05 никогда не обращается к production LE (Pebble), реальный выпуск проверить автоматически нельзя"
---

# Phase 2: Panel за Traefik с защищённым входом — отчёт верификации

**Цель фазы:** Оператор разворачивает Panel-хост одной командой: HTTPS на собственном домене, вход в админку закрыт cookie/secret-path гейтом, первый админ и API-токен создаются автоматически, subscription page на отдельном домене, повторный прогон ничего не ломает и не меняет секреты.
**Проверено:** 2026-11-26
**Статус:** human_needed (автоматические проверки пройдены, остались два ручных пункта)
**Повторная верификация:** Да, после правок code review (WR-01..WR-05); регрессий нет

## Достижение цели

### Наблюдаемые истины (ROADMAP Success Criteria)

| # | Истина | Статус | Свидетельство |
|---|--------|--------|---------------|
| 1 | HTTPS на домене Panel с валидным сертификатом (в CI Pebble/staging), в access log реальный IP клиента | VERIFIED | `roles/edge/templates/traefik.yml.j2`: HTTP-01 resolver `le`, caServer по переключателю production/staging/custom; `verify_edge.yml:344` проверяет реальный client address; `scripts/check.sh` (QA-05) запрещает production CA в Molecule-сценариях; CI molecule-vm (alma10+rocky10) на 5d29527 success |
| 2 | Без cookie админка отдаёт decoy (200); секретный URL ставит cookie; /api (кроме /api/auth) и подписки доступны без cookie | VERIFIED | `panel-routes.yml.j2`: роутеры gate (prio 1000, Set-Cookie + redirect), cookie (500), api (400, исключает /api/auth), decoy (1); `verify_gate*.yml` — матрица запросов, ротация gate, отсутствие gate path в логах; `scripts/gate/run.sh` — регрессия на реальном Traefik образе (CI gate success) |
| 3 | Админ и долгоживущий токен (0600) созданы; повторный прогон логинится, секреты не меняются, changed=0 | VERIFIED | `bootstrap.yml`: status -> register только если isRegisterAllowed и не isLoginAllowed, иначе login; токен проверяется пробой, пересоздаётся только при невалидности; файл 0600; `converge.yml` фиксирует sha256 секретов и токена, `side_effect.yml` сверяет после idempotence и reboot; CI VM success |
| 4 | Subscription page на отдельном домене по HTTPS получает данные от Panel по API-токену без ручных шагов | VERIFIED | `subpage.yml` + `subpage.env.j2` (REMNAWAVE_API_TOKEN из bootstrap), `subscription-routes.yml.j2` (Host(sub-домен)), assert `xvpn_subscription_domain != xvpn_panel_domain`; `verify_subpage.yml` сверяет токен контейнера, запрашивает страницу пробного пользователя, негативный контроль неверного токена |
| 5 | Секреты не в выводе (no_log), placeholder'ы отвергаются assert'ом | VERIFIED | `secrets.yml`: форматные regex + weak-words assert; `scripts/check_no_log.py` в `check.sh` (локально `check.sh: OK`); gitleaks в CI |

**Оценка:** 5/5 истин подтверждено.

### Покрытие требований

| Требование | Статус | Свидетельство |
|-----------|--------|---------------|
| EDGE-01 | SATISFIED | traefik.container.j2: Network=host, file provider, без сокета Podman |
| EDGE-02 | SATISFIED | httpChallenge, переключатель staging/production, `/acme/acme.json` на персистентном томе, проверка 0600 в verify_edge |
| EDGE-03 | SATISFIED | verify_edge: реальный IP клиента в access log |
| PANEL-01 | SATISFIED | remnawave*.container.j2 + network/volume, Notify=healthy, Requires/After |
| PANEL-02 | SATISFIED | secrets.yml generate-once, checksum стабилен в VM-тесте |
| PANEL-03 | SATISFIED | bootstrap.yml на 127.0.0.1:3000 до записи route-файла (порядок в main.yml) |
| PANEL-04 | SATISFIED | api-token 0600, проба и пересоздание |
| PANEL-05 | SATISFIED | panel-routes.yml.j2, TLS через resolver le |
| PANEL-06 | SATISFIED | см. истину 2 |
| SUB-01 / SUB-02 | SATISFIED | см. истину 4 |
| QA-05 | SATISFIED | check.sh guard + Pebble в VM-тире |
| DOC-04 | SATISFIED | no_log gate, assert плейсхолдеров |

Все 13 ID из PLAN frontmatter присутствуют в REQUIREMENTS.md и в ROADMAP фазы; осиротевших требований нет.

### Anti-patterns и замечания code review

TBD/FIXME/XXX в roles, playbooks, scripts, extensions не найдено. Блокеров нет. Все пять предупреждений WR-01..WR-05 исправлены и перепроверены по коду:

| ID | Коммиты | Проверка в коде |
|----|---------|-----------------|
| WR-01 | 9032e4a, 312a6d1 | `secrets.yml`: булев `secrets_immutable_ok` (no_log) + assert без имён секретов; неизменяемые ключи обязательны в существующем файле. Негативного Molecule-кейса нет (информационно) |
| WR-02 | 89bc1b4 | `stack.yml`: rescue фильтрует строки по token/password/secret/DATABASE_URL и т. п. |
| WR-03 | 1af7039 | `main.yml`: TLD допускает `xn--...` для обоих доменов |
| WR-04 | 6aae78b | `check_no_log.py`: самотест-приманки, правило для `.env`/`secrets`-шаблонов; `check.sh: OK` |
| WR-05 | c389b83 | `restart_stale.yml` сравнивает mtime файла с `ExecMainStartTimestamp`; подключён в stack, subpage, edge; пустой timestamp = не устарел. Идемпотентность подтверждена молекулой VM (см. ниже) |

02-SECURITY.md: threats_open 0.

### Автоматические проверки

| Проверка | Результат |
|----------|-----------|
| `scripts/check.sh` локально (повторно в этой верификации) | `check.sh: OK` |
| CI на HEAD 7c6a2d9: lint, gate, molecule-container (run 45762412668) | success |
| molecule-vm run 45763475691 (headSha 7c6a2d9, alma10 и rocky10, SELinux enforcing, idempotence) | success |

Молекулу локально запустить нельзя; поведение WR-05 на EL10 (`systemctl --timestamp=unix`) подтверждено только зелёным VM-прогоном с идемпотентностью.

## Требуется проверка человеком

1. **Живой браузерный вход через гейт.** Открыть секретный URL из admin-url файла, убедиться, что cookie ставится и логин работает; без cookie виден decoy.
2. **Production Let's Encrypt на реальном домене.** Один прогон с `xvpn_edge_acme_ca: production`.

## Итог

Цель фазы достигнута по всем пяти критериям и тринадцати требованиям, подтверждена кодом и CI (включая VM-тир с SELinux enforcing). Блокирующих пробелов нет. Остаются два ручных пункта и два рекомендуемых исправления (WR-01, WR-05).

---

_Проверено: 2026-11-25_
_Верификатор: Claude (gsd-verifier)_
