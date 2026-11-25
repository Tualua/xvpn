---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
verified: 2026-11-25T19:30:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files: [roles/panel/tasks/secrets.yml, roles/panel/tasks/bootstrap.yml, roles/panel/tasks/subpage.yml, roles/panel/templates/panel-routes.yml.j2, roles/edge/templates/traefik.yml.j2, playbooks/panel.yml]
covered_digest: "v4:sha256:4e1f3cbfd229c421deb909a4884eb90b25370d27047c8b40250b4b423b2133f1"
behavior_unverified: 0
overrides_applied: 0
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
**Проверено:** 2026-11-25
**Статус:** human_needed (автоматические проверки пройдены, остались два ручных пункта)
**Повторная верификация:** Нет, первичная

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

### Anti-patterns и замечания code review (все warning, открыты)

TBD/FIXME/XXX в файлах фазы не найдено. Блокеров (critical) нет. 02-SECURITY.md: threats_open 0.

| ID | Влияние на цель | Оценка |
|----|-----------------|--------|
| WR-01 частичный `panel-secrets.yml` пополняется свежими секретами | Затрагивает "не меняет секреты" только при ручной порче файла; штатный прогон и guard при полной потере файла работают | WARNING, рекомендуется исправить (assert неизменяемых ключей) |
| WR-05 потеря сигнала "changed" при сбое между рендером и рестартом | Нарушает сходимость только после сбойного прогона; штатный сценарий покрыт | WARNING, рекомендуется исправить |
| WR-02, WR-03, WR-04, IN-01..07 | Не затрагивают must-have | Информационно |

### Автоматические проверки

| Проверка | Результат |
|----------|-----------|
| `scripts/check.sh` локально | OK |
| CI на 5d29527: lint, gate, molecule-container (push), molecule-vm (dispatch) | все success (`gh run list`); более ранний сбой molecule-container на ef0a8b9 исправлен 5d29527 |

## Требуется проверка человеком

1. **Живой браузерный вход через гейт.** Открыть секретный URL из admin-url файла, убедиться, что cookie ставится и логин работает; без cookie виден decoy.
2. **Production Let's Encrypt на реальном домене.** Один прогон с `xvpn_edge_acme_ca: production`.

## Итог

Цель фазы достигнута по всем пяти критериям и тринадцати требованиям, подтверждена кодом и CI (включая VM-тир с SELinux enforcing). Блокирующих пробелов нет. Остаются два ручных пункта и два рекомендуемых исправления (WR-01, WR-05).

---

_Проверено: 2026-11-25_
_Верификатор: Claude (gsd-verifier)_
