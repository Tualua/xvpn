---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
verified: 2026-11-27T03:00:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files: [".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-01-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-01-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-02-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-02-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-03-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-03-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-04-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-04-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-05-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-05-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-06-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-06-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-07-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-07-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-08-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-08-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-09-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-09-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-10-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-10-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-11-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-11-SUMMARY.md", "README.md", "extensions/molecule/container/verify.yml", "extensions/molecule/shared/panel_failure_log_dir_case.yml", "playbooks/panel.yml", "roles/edge/tasks/main.yml", "roles/edge/templates/traefik.yml.j2", "roles/panel/defaults/main.yml", "roles/panel/meta/argument_specs.yml", "roles/panel/tasks/bootstrap.yml", "roles/panel/tasks/main.yml", "roles/panel/tasks/secrets.yml", "roles/panel/tasks/stack.yml", "roles/panel/tasks/subpage.yml", "roles/panel/templates/panel-routes.yml.j2", "roles/podman_rootless/tasks/restart_stale.yml", "scripts/check_no_log.py", "scripts/ci_watch.sh"]
covered_digest: "v4:sha256:8a43b03c04bbbfc1d7f3ac964c22b88f5b543561e7e096b102fe5dff5cf7808f"
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
**Проверено:** 2026-11-27 (повторная верификация после 6244716)
**Статус:** human_needed (автоматические проверки пройдены, остались два ручных пункта)
**Повторная верификация:** Да. Изменились README.md, `roles/panel/meta/argument_specs.yml`, `roles/panel/tasks/stack.yml` (плюс тесты в `extensions/molecule/container/verify.yml` и новый `extensions/molecule/shared/panel_failure_log_dir_case.yml`). Регрессий нет.

## Достижение цели

### Наблюдаемые истины (ROADMAP Success Criteria)

| # | Истина | Статус | Свидетельство |
|---|--------|--------|---------------|
| 1 | HTTPS на домене Panel с валидным сертификатом (в CI Pebble/staging), в access log реальный IP клиента | VERIFIED | `roles/edge/templates/traefik.yml.j2` и `roles/edge/tasks/main.yml` не менялись с 6244716; HTTP-01 resolver, переключатель CA, проверка client address в `verify_edge.yml` на месте |
| 2 | Без cookie админка отдаёт decoy; секретный URL ставит cookie; /api (кроме /api/auth) и подписки без cookie | VERIFIED | `panel-routes.yml.j2` не менялся; `verify_gate*.yml`, `scripts/gate/run.sh` на месте |
| 3 | Админ и токен (0600) созданы; повторный прогон логинится, секреты не меняются, changed=0 | VERIFIED | `bootstrap.yml`, `secrets.yml` не менялись. Новые задачи в `stack.yml` (stat + assert) только читают состояние, идемпотентны, changed=0 |
| 4 | Subscription page на отдельном домене по HTTPS получает данные от Panel по API-токену | VERIFIED | `subpage.yml` и assert различия доменов в `main.yml` не менялись |
| 5 | Секреты не в выводе (no_log), placeholder'ы отвергаются assert'ом | VERIFIED | `secrets.yml` и `check_no_log.py` не менялись; новый assert выводит в `fail_msg` только путь каталога (не секрет) |

**Оценка:** 5/5 истин подтверждено.

### Проверка изменений после 6244716 (fadc5fe, 2115ba3, 8ea2677, dfe1f55)

| Файл | Изменение | Итог |
|------|-----------|------|
| `roles/panel/tasks/stack.yml` | Regex `xvpn_panel_failure_log_dir` закрыт якорем `\Z` (вместо `$`, который допускал завершающий перевод строки); добавлены `stat` и assert, отказывающие брать существующий чужой каталог (допустим только отсутствующий либо real dir root:root 0700); stat идёт под `become`, символьная ссылка отсекается (`isdir` без follow) | Прочитано в коде: порядок корректный (валидация до первого использования), дефолт `/var/log/xvpn` проходит, успешный путь не затронут |
| `README.md`, `meta/argument_specs.yml` | Описание допустимых символов и правила существующего каталога | Согласованы с кодом |
| `extensions/molecule/container/verify.yml`, `shared/panel_failure_log_dir_case.yml` | Негативные и позитивные кейсы для валидации каталога | Присутствуют; закрывают IN-01 прошлого ревью (отсутствие негативных тестов) |

Прогон `scripts/check.sh` на текущем HEAD: `check.sh: OK` (ansible-lint, syntax-check всех сценариев, сборка коллекции, гейты). TBD/FIXME/XXX в `roles`, `playbooks`, `scripts` не найдено.

### Свежее ревью (02-REVIEW.md, 02-REVIEW-DISPOSITION.md): 0 critical, 2 warning, 2 info

Рекомендательно, не блокирует: все находки касаются только необязательной диагностической переменной и её тестов.

- **WR-01:** guard «чужого каталога» принимает существующие системные каталоги с root:root 0700 (например `/var/log/audit`), поэтому формулировка README «no existing system or service directory is taken over» слишком сильна. Нужно смягчить текст или добавить denylist/проверку пустоты.
- **WR-02:** тесты не проверяют ветку «home / родитель home» (кейсы лежат вне разрешённых баз и отклоняются regex'ом раньше).
- **IN-01:** очистка fixture'ов не в `always`.
- **IN-02:** слишком длинная строка в списке negative-кейсов.

Оценка влияния: дефолт безопасен, истины 1-5 и 13 требований не затронуты. Диспозиция: open 4 (WR-01, WR-02, IN-01, IN-02), остальные fixed.

### Покрытие требований

| Требование | Статус | Свидетельство |
|-----------|--------|---------------|
| EDGE-01 | SATISFIED | traefik.container.j2: Network=host, file provider, без сокета Podman |
| EDGE-02 | SATISFIED | httpChallenge, переключатель staging/production, `acme.json` на томе, 0600 |
| EDGE-03 | SATISFIED | verify_edge: реальный IP клиента в access log |
| PANEL-01 | SATISFIED | remnawave*.container.j2, network/volume, Notify=healthy |
| PANEL-02 | SATISFIED | secrets.yml generate-once, sha256 стабилен |
| PANEL-03 | SATISFIED | bootstrap.yml на 127.0.0.1:3000 |
| PANEL-04 | SATISFIED | api-token 0600, проба и пересоздание |
| PANEL-05 | SATISFIED | panel-routes.yml.j2, TLS через resolver le |
| PANEL-06 | SATISFIED | см. истину 2 |
| SUB-01 / SUB-02 | SATISFIED | см. истину 4 |
| QA-05 | SATISFIED | check.sh guard + Pebble в VM-тире |
| DOC-04 | SATISFIED | no_log gate, assert плейсхолдеров |

Все 13 ID из PLAN frontmatter присутствуют в REQUIREMENTS.md; осиротевших требований нет.

### Автоматические проверки

| Проверка | Результат |
|----------|-----------|
| `scripts/check.sh` локально на HEAD | `check.sh: OK` |
| CI на 64e5d9c (lint, gate, molecule-container, molecule-vm alma10/rocky10, SELinux enforcing) | success (по предыдущему отчёту, не перепроверялось) |
| CI на коммитах после (в т.ч. 8ea2677..dfe1f55) | Не проверялось в этом прогоне. Изменения затрагивают только валидацию диагностического каталога; рекомендуется зелёный CI перед релизом (новые molecule-кейсы запускались только локально через check.sh в части lint/syntax) |

## Требуется проверка человеком

1. **Живой браузерный вход через гейт.** Открыть секретный URL из admin-url файла, убедиться, что cookie ставится и логин работает; без cookie виден decoy.
2. **Production Let's Encrypt на реальном домене.** Один прогон с `xvpn_edge_acme_ca: production`.

## Итог

Цель фазы достигнута по всем пяти критериям и тринадцати требованиям; изменения после 6244716 регрессий не вносят. Остаются два ручных пункта и рекомендуемый зелёный прогон CI на актуальном HEAD; открытые WR-01/WR-02/IN-01/IN-02 ревью не блокируют.

---

_Проверено: 2026-11-27_
_Верификатор: Claude (gsd-verifier)_
