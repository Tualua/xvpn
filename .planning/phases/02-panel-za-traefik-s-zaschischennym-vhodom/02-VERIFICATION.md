---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
verified: 2026-11-26T14:00:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files: [".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-01-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-01-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-02-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-02-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-03-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-03-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-04-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-04-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-05-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-05-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-06-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-06-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-07-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-07-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-08-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-08-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-09-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-09-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-10-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-10-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-11-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-11-SUMMARY.md", "playbooks/panel.yml", "roles/edge/tasks/main.yml", "roles/edge/templates/traefik.yml.j2", "roles/panel/tasks/bootstrap.yml", "roles/panel/tasks/main.yml", "roles/panel/tasks/secrets.yml", "roles/panel/tasks/stack.yml", "roles/panel/tasks/subpage.yml", "roles/panel/templates/panel-routes.yml.j2", "roles/podman_rootless/tasks/restart_stale.yml", "scripts/check_no_log.py", "scripts/ci_watch.sh"]
covered_digest: "v4:sha256:fc9f2faefc4fa3c337f7aff242490c0df54dea4b158b84d4764878e11fcc13e6"
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
**Повторная верификация:** Да, после коммитов code review 60dbb9e..HEAD (WR-03, WR-04, WR-05, IN-02..IN-05); регрессий нет

## Достижение цели

### Наблюдаемые истины (ROADMAP Success Criteria)

| # | Истина | Статус | Свидетельство |
|---|--------|--------|---------------|
| 1 | HTTPS на домене Panel с валидным сертификатом (в CI Pebble/staging), в access log реальный IP клиента | VERIFIED | `roles/edge/templates/traefik.yml.j2`: HTTP-01 resolver `le`, caServer по переключателю production/staging/custom; `verify_edge.yml` проверяет реальный client address; `scripts/check.sh` (QA-05) запрещает production CA в Molecule-сценариях. Новые assert'ы в `edge/tasks/main.yml` (порт <= 65535, строже regex email) только сужают допустимый ввод |
| 2 | Без cookie админка отдаёт decoy (200); секретный URL ставит cookie; /api (кроме /api/auth) и подписки доступны без cookie | VERIFIED | `panel-routes.yml.j2`: роутеры gate / cookie / api / decoy по приоритетам; `verify_gate*.yml`, `scripts/gate/run.sh`; файлы не менялись после последнего зелёного CI |
| 3 | Админ и долгоживущий токен (0600) созданы; повторный прогон логинится, секреты не меняются, changed=0 | VERIFIED | `bootstrap.yml` не менялся; `secrets.yml` изменён только текстом `fail_msg` (IN-02), логика generate-once и immutable-ключей сохранена; `converge.yml`/`side_effect.yml` сверяют sha256 |
| 4 | Subscription page на отдельном домене по HTTPS получает данные от Panel по API-токену без ручных шагов | VERIFIED | `subpage.yml`, `subscription-routes.yml.j2`, assert `xvpn_subscription_domain != xvpn_panel_domain` сохранён в `panel/tasks/main.yml` (изменён только TLD-regex для punycode) |
| 5 | Секреты не в выводе (no_log), placeholder'ы отвергаются assert'ом | VERIFIED | `secrets.yml`: weak-words и форматные assert'ы на месте; `check_no_log.py` расширен (slurp/fetch и доп. writer-модули); rescue в `stack.yml` не печатает `ansible_failed_result.msg` и логи, они уходят в root-only файл 0600 |

**Оценка:** 5/5 истин подтверждено.

### Проверка правок с 60dbb9e (регрессии)

| Файл | Изменение | Итог |
|------|-----------|------|
| `roles/edge/tasks/main.yml` | порт <= 65535 для http/https entrypoint, regex email требует домен с точкой | Без регрессий, только ужесточение валидации |
| `roles/panel/tasks/main.yml` | punycode-TLD `xn--` без дефиса на краях | Без регрессий; требования к FQDN и различию доменов сохранены |
| `roles/panel/tasks/secrets.yml` | `fail_msg` уточнён (vault-переопределения не заменяют immutable-ключи) | Только сообщение, логика не затронута |
| `roles/panel/tasks/stack.yml` | rescue: no_log на сборе логов, root-only `/var/log/xvpn` 0700, файл 0600, очистка старого лога после успешного старта | Секреты не попадают в вывод; успешный путь только удаляет устаревший файл (`state: absent`, идемпотентно, play имеет `become: true`) |
| `scripts/check_no_log.py` | расширено покрытие slurp/fetch и writer-модулей | `check.sh: OK` (lint, syntax-check, no_log guard, сборка коллекции) |
| `scripts/ci_watch.sh` | ошибка чтения baseline run прерывает скрипт | Инструмент CI, на артефакты фазы не влияет |

### Замечания свежего code review (02-REVIEW.md, 810ad39)

0 critical, 2 warning, 2 info; это advisory, на must-have не влияют.

- **WR-01/WR-02** (`stack.yml`, `failed_when: false` делает проверки `is succeeded` всегда истинными): затрагивает только диагностику в rescue-ветке уже упавшего запуска. Если запись `/var/log/xvpn/panel-start-failure.log` не удалась, сообщение об ошибке всё равно сошлётся на файл. Секреты при этом не раскрываются, успешный путь, идемпотентность и сами истины 1-5 не затронуты. Статус: предупреждение (качество диагностики), рекомендуемое исправление: `ignore_errors: true` вместо `failed_when: false` на двух задачах.
- **IN-01, IN-02**: захардкоженный путь лога и не покрытые `check_no_log.py` способы чтения секретного файла (`command cat`, `include_vars`); текущие роли таких конструкций не содержат. Дальний запас прочности.

### Покрытие требований

| Требование | Статус | Свидетельство |
|-----------|--------|---------------|
| EDGE-01 | SATISFIED | traefik.container.j2: Network=host, file provider, без сокета Podman |
| EDGE-02 | SATISFIED | httpChallenge, переключатель staging/production, `/acme/acme.json` на томе, 0600 проверяется |
| EDGE-03 | SATISFIED | verify_edge: реальный IP клиента в access log |
| PANEL-01 | SATISFIED | remnawave*.container.j2, network/volume, Notify=healthy |
| PANEL-02 | SATISFIED | secrets.yml generate-once, sha256 стабилен в VM-тесте |
| PANEL-03 | SATISFIED | bootstrap.yml на 127.0.0.1:3000 до записи route-файла |
| PANEL-04 | SATISFIED | api-token 0600, проба и пересоздание |
| PANEL-05 | SATISFIED | panel-routes.yml.j2, TLS через resolver le |
| PANEL-06 | SATISFIED | см. истину 2 |
| SUB-01 / SUB-02 | SATISFIED | см. истину 4 |
| QA-05 | SATISFIED | check.sh guard + Pebble в VM-тире |
| DOC-04 | SATISFIED | no_log gate, assert плейсхолдеров |

Все 13 ID из PLAN frontmatter присутствуют в REQUIREMENTS.md и привязаны к Phase 2; осиротевших требований нет.

### Anti-patterns

TBD/FIXME/XXX в `roles`, `playbooks`, `scripts` не найдено. Блокеров нет.

### Автоматические проверки

| Проверка | Результат |
|----------|-----------|
| `scripts/check.sh` локально (на HEAD 1242e98) | `check.sh: OK` |
| CI на 64e5d9c: lint, gate, molecule-container, molecule-vm (alma10 и rocky10, SELinux enforcing, идемпотентность) | success |
| CI на коммитах после 64e5d9c (WR-03/04/05, IN-02..IN-05) | Запусков нет; правки сводятся к сообщениям, валидации, rescue-ветке и dev-скриптам, поэтому риск низкий. Рекомендуется зелёный прогон перед релизом |

## Требуется проверка человеком

1. **Живой браузерный вход через гейт.** Открыть секретный URL из admin-url файла, убедиться, что cookie ставится и логин работает; без cookie виден decoy.
2. **Production Let's Encrypt на реальном домене.** Один прогон с `xvpn_edge_acme_ca: production`.

## Итог

Цель фазы достигнута по всем пяти критериям и тринадцати требованиям. Правки code review после 60dbb9e регрессий не вносят. WR-01/WR-02 из свежего ревью затрагивают только качество диагностики в rescue-ветке и не блокируют. Остаются два ручных пункта и один рекомендуемый прогон CI на актуальном HEAD.

---

_Проверено: 2026-11-26_
_Верификатор: Claude (gsd-verifier)_
