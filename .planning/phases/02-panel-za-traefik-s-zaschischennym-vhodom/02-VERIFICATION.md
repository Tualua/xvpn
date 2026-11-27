---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
verified: 2026-11-27T06:00:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files: [".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-01-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-01-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-02-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-02-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-03-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-03-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-04-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-04-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-05-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-05-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-06-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-06-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-07-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-07-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-08-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-08-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-09-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-09-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-10-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-10-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-11-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-11-SUMMARY.md", "README.md", "extensions/molecule/container/verify.yml", "playbooks/panel.yml", "roles/edge/tasks/main.yml", "roles/edge/templates/traefik.yml.j2", "roles/panel/defaults/main.yml", "roles/panel/meta/argument_specs.yml", "roles/panel/tasks/bootstrap.yml", "roles/panel/tasks/main.yml", "roles/panel/tasks/secrets.yml", "roles/panel/tasks/stack.yml", "roles/panel/tasks/subpage.yml", "roles/panel/templates/panel-routes.yml.j2", "roles/panel/vars/main.yml", "roles/podman_rootless/tasks/restart_stale.yml", "scripts/check_no_log.py", "scripts/ci_watch.sh"]
covered_digest: "v4:sha256:11c34cc2894b4efc0278cd706b3876ee86e86c008f51fd05b5eed32d08800528"
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
**Проверено:** 2026-11-27
**Статус:** human_needed (автоматические проверки пройдены, остались два ручных пункта)
**Повторная верификация:** Да, после quick-задачи 261127-40g (коммиты 7c897d7, c4eadea): пользовательская переменная `xvpn_panel_failure_log_dir` удалена, путь стал внутренней константой. Регрессий нет. Code review намеренно не перезапускался (все находки в 02-REVIEW-DISPOSITION.md закрыты, open: 0).

## Достижение цели

### Наблюдаемые истины (ROADMAP Success Criteria)

| # | Истина | Статус | Свидетельство |
|---|--------|--------|---------------|
| 1 | HTTPS на домене Panel с валидным сертификатом (в CI Pebble/staging), в access log реальный IP клиента | VERIFIED | `roles/edge/*` не менялись в quick-задаче; resolver HTTP-01, переключатель CA и проверка client address на месте |
| 2 | Без cookie админка отдаёт decoy; секретный URL ставит cookie; /api (кроме /api/auth) и подписки без cookie | VERIFIED | `panel-routes.yml.j2` не менялся |
| 3 | Админ и токен (0600) созданы; повторный прогон логинится, секреты не меняются, changed=0 | VERIFIED | `bootstrap.yml`, `secrets.yml` не менялись |
| 4 | Subscription page на отдельном домене по HTTPS получает данные от Panel по API-токену | VERIFIED | `subpage.yml` и assert различия доменов не менялись |
| 5 | Секреты не в выводе (no_log), placeholder'ы отвергаются assert'ом | VERIFIED | `secrets.yml`, `check_no_log.py` не менялись; `no_log: true` сохранён на задачах сбора и записи логов |

**Оценка:** 5/5 истин подтверждено.

### Проверка изменений quick-задачи 261127-40g

| Проверка | Результат |
|----------|-----------|
| Константа | `roles/panel/vars/main.yml`: `xvpn_panel_start_failure_log_dir: /var/log/xvpn`; vars/main.yml имеет высокий приоритет, inventory её не переопределит |
| Каталог логов | `stack.yml`: `file state=directory owner=root group=root mode=0700` (play-level `become: true` в `playbooks/panel.yml`) |
| Файл лога | `copy ... dest={{ dir }}/panel-start-failure.log mode=0600 owner=root`, `no_log: true`, `diff: false`; внутри вложенного block с rescue, флаг `xvpn_panel_start_log_saved` ставится только после записи |
| Очистка при успехе | `file state=absent` на `panel-start-failure.log` после успешного старта |
| Условный путь в сообщении | `fail.msg` называет путь лога только если `xvpn_panel_start_log_saved`, иначе рекомендует `journalctl` |
| Удалённая валидация | В `stack.yml` не осталось regex/stat/assert по пути; задачи удалены |
| Остаточные ссылки | `grep -rn "failure_log_dir\|panel_failure_log_dir_case"` вне `.planning/` находит только внутреннюю константу `xvpn_panel_start_failure_log_dir` (stack.yml, vars/main.yml); публичной переменной и файла `extensions/molecule/shared/panel_failure_log_dir_case.yml` нет |
| README | Строка таблицы файлов описывает фиксированный (не настраиваемый) `/var/log/xvpn` |
| `scripts/check.sh` | `check.sh: OK` (ansible-lint, syntax-check, сборка коллекции, гейты) |

Поведение при сбое старта не изменилось. Удаление пути как параметра закрывает также прежние WR-01/WR-02 ревью (guard «чужого каталога» больше не нужен: путь не задаётся оператором).

### Покрытие требований

| Требование | Статус | Свидетельство |
|-----------|--------|---------------|
| EDGE-01 | SATISFIED | Traefik Network=host, file provider, без сокета Podman |
| EDGE-02 | SATISFIED | httpChallenge, переключатель staging/production, `acme.json` на томе, 0600 |
| EDGE-03 | SATISFIED | verify_edge: реальный IP клиента в access log |
| PANEL-01 | SATISFIED | remnawave*.container.j2, network/volume, Notify=healthy |
| PANEL-02 | SATISFIED | secrets.yml generate-once |
| PANEL-03 | SATISFIED | bootstrap.yml на 127.0.0.1:3000 |
| PANEL-04 | SATISFIED | api-token 0600, проба и пересоздание |
| PANEL-05 | SATISFIED | panel-routes.yml.j2, TLS через resolver le |
| PANEL-06 | SATISFIED | см. истину 2 |
| SUB-01 / SUB-02 | SATISFIED | см. истину 4 |
| QA-05 | SATISFIED | check.sh guard + Pebble в VM-тире |
| DOC-04 | SATISFIED | no_log gate, assert плейсхолдеров |

Все 13 ID из PLAN frontmatter есть в REQUIREMENTS.md; осиротевших требований нет.

### Автоматические проверки

| Проверка | Результат |
|----------|-----------|
| `scripts/check.sh` на текущем рабочем дереве | `check.sh: OK` |
| CI на коммитах после quick-задачи | Не проверялось; Molecule/VM-тир не запускался в этой верификации |

### Антипаттерны

TBD/FIXME/XXX в изменённых файлах не обнаружено.

## Требуется проверка человеком

1. **Живой браузерный вход через гейт.** Открыть https://<panel-domain>/<gate_path> (путь из admin-url файла на Panel-хосте), войти логином admin. Ожидается: cookie ставится, логин проходит; без cookie виден decoy. Почему вручную: автотесты не проверяют живой браузерный поток и SameSite.
2. **Production Let's Encrypt на реальном домене.** Прогон `playbooks/panel.yml` с `xvpn_edge_acme_ca: production`. Ожидается: выпуск сертификата, Panel и subscription page открываются по HTTPS. Почему вручную: CI по QA-05 использует только Pebble.

## Итог

Цель фазы достигнута по всем пяти критериям и тринадцати требованиям. Поведение журнала сбоя старта стека не изменилось, ссылок на удалённую переменную и файл нет. Остаются два ручных пункта.

---

_Проверено: 2026-11-27_
_Верификатор: Claude (gsd-verifier)_
