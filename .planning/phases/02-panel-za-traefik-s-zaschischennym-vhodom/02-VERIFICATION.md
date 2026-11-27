---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
verified: 2026-11-27T15:00:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files: [".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-01-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-01-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-02-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-02-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-03-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-03-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-04-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-04-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-05-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-05-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-06-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-06-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-07-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-07-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-08-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-08-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-09-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-09-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-10-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-10-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-11-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-11-SUMMARY.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-12-PLAN.md", ".planning/phases/02-panel-za-traefik-s-zaschischennym-vhodom/02-12-SUMMARY.md", "README.md", "extensions/molecule/container/verify.yml", "extensions/molecule/shared/verify_edge.yml", "extensions/molecule/vm/side_effect.yml", "playbooks/panel.yml", "roles/edge/tasks/main.yml", "roles/edge/templates/traefik.yml.j2", "roles/edge/vars/main.yml", "roles/panel/tasks/bootstrap.yml", "roles/panel/tasks/secrets.yml", "roles/panel/tasks/stack.yml", "roles/panel/tasks/subpage.yml", "roles/panel/templates/panel-routes.yml.j2", "roles/preflight/meta/argument_specs.yml", "scripts/check_no_log.py"]
covered_digest: "v4:sha256:e3c0047acd2d2d5447e1a28c5426ee7e79bd4592422cfa896bc03ac73d92009e"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  gaps_closed:
    - "02-UAT-G1: переключение xvpn_edge_acme_ca staging -> production не меняло сертификат (общий acme.json); закрыто планом 02-12 (хранилище ACME по CA)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Повторить UAT-тест 2 на реальном Panel-хосте: переключить xvpn_edge_acme_ca с staging на production и перезапустить playbooks/panel.yml"
    expected: "Прогон перерисовывает traefik.yml и перезапускает Traefik; через 1-2 минуты Panel и subscription page отдают доверенный сертификат production Let's Encrypt (хранилище acme-production.json создано Traefik'ом с 0600). Ручной перезапуск и вход под rw-edge не требуются"
    why_human: "CI по QA-05 никогда не обращается к production LE (только Pebble); исправление доказано в CI подменой идентичности CA на Pebble, но реальный выпуск проверить автоматически нельзя"
  - test: "Живой браузерный вход через гейт (UAT-тест 1 пройден пользователем: pass)"
    expected: "Секретный URL ставит cookie и ведёт на логин; без cookie отдаётся decoy"
    why_human: "Закрыто пользователем в UAT; остаётся только для production-сертификата после переключения CA (повторная проверка вместе с пунктом выше)"
---

# Phase 2: Panel за Traefik с защищённым входом — отчёт верификации

**Цель фазы:** Оператор разворачивает Panel-хост одной командой: Panel по HTTPS на собственном домене, вход в админку закрыт cookie/secret-path гейтом, первый админ и API-токен создаются автоматически, subscription page на отдельном домене, повторный прогон ничего не ломает и не меняет секреты.
**Проверено:** 2026-11-27
**Статус:** human_needed (автоматические проверки пройдены; осталась проверка production-сертификата на реальном хосте)
**Повторная верификация:** Да, после UAT (16 passed, 2 skipped, 1 issue), плана закрытия разрыва 02-12 и изменений: OL10 (quick 261127-ej4), tar в VM prepare (2d08b00), rejection sampling паролей (93967d3), argument_specs preflight (a7d502a), инкрементальное code review (02-REVIEW.md, 02-REVIEW-DISPOSITION.md).

## Достижение цели

### Наблюдаемые истины (ROADMAP Success Criteria)

| # | Истина | Статус | Свидетельство |
|---|--------|--------|---------------|
| 1 | HTTPS на домене Panel с валидным сертификатом (в CI Pebble/staging), в access log реальный IP клиента | VERIFIED | `roles/edge/templates/traefik.yml.j2` (resolver `le`, httpChallenge, переключатель CA); `verify_edge.yml` проверяет ClientHost при подделанном X-Forwarded-For; VM-тир: Pebble, идемпотентность, reboot, 0 AVC (CI зелёный). Production-выпуск: см. human_verification |
| 2 | Без cookie админка отдаёт decoy; секретный URL ставит cookie; /api (кроме /api/auth) и подписки без cookie | VERIFIED | `panel-routes.yml.j2`; UAT-тест 1 (живой браузер) pass; автотесты gate в container/VM тирах |
| 3 | Админ и токен (0600) созданы автоматически; повторный прогон логинится, секреты не меняются, changed=0 | VERIFIED | `bootstrap.yml`, `secrets.yml` (генерация один раз, rejection sampling в одном шаблоне после 93967d3); UAT-тест 3 pass; `side_effect.yml` проверяет отказ ротации |
| 4 | Subscription page на отдельном домене по HTTPS получает данные от Panel по API-токену | VERIFIED | `subpage.yml`; assert различия доменов (container-кейс panel-same-domains); UAT-тест 4 pass; автотест panel-subpage-toggle |
| 5 | Секреты не в выводе (no_log), placeholder'ы отвергаются assert'ом | VERIFIED | `scripts/check_no_log.py` в `check.sh`; UAT-тесты 5, 6 pass |

**Оценка:** 5/5 истин подтверждено.

### Закрытие разрыва 02-UAT-G1 (план 02-12)

| Проверка | Результат |
|----------|-----------|
| Первопричина | Единый `acme.json` для всех CA: Traefik не сверяет сохранённый сертификат с `caServer` до последних 30 дней срока |
| Реализация | `roles/edge/vars/main.yml`: `xvpn_edge_acme_storage_file` = `acme-production.json` / `acme-staging.json` / `acme-custom-<sha256[:12]>.json`; имя строится только из проверенного enum или hex, инъекция пути невозможна; шаблон `storage: /acme/{{ ... }}` использует эту переменную |
| Права | `roles/edge/tasks/main.yml`: stat активного и legacy-хранилища, `file mode 0600` owner rw-edge только для существующих; роль не создаёт, не читает и не печатает хранилище (T-02-05) |
| Верификаторы | `verify_edge.yml` читает активное хранилище из отрендеренного `traefik.yml` (regex на имя), проверяет 0600 и владельца rw-edge |
| Автотесты | container-кейс `edge-acme-storage-per-ca` (verify.yml); VM-блок «ACME CA switch» (side_effect.yml: рестарт по InvocationID, новое хранилище, sha256 исходного хранилища не меняется, возврат переиспользует прежнее и тот же leaf) |
| README | Подраздел «Switching the ACME CA» и строка таблицы файлов обновлены |
| Ограничение | Legacy `acme.json` не мигрируется (активный CA выпустит сертификат заново один раз), документировано |

Код-часть разрыва закрыта и подтверждена CI; сценарий пользователя на production-хосте не перепроверен (human).

### Покрытие требований

| Требование | Статус | Свидетельство |
|-----------|--------|---------------|
| EDGE-01 | SATISFIED | Traefik rootless Quadlet, Network=host, file provider, без сокета Podman |
| EDGE-02 | SATISFIED | httpChallenge, переключатель staging/production/custom, персистентное хранилище на томе (теперь по CA, 0600); production-выпуск ожидает ручной проверки |
| EDGE-03 | SATISFIED | verify_edge: реальный IP клиента в access log |
| PANEL-01 | SATISFIED | Quadlet-юниты backend/Postgres/Valkey, сеть, Notify=healthy |
| PANEL-02 | SATISFIED | `secrets.yml` generate-once |
| PANEL-03 | SATISFIED | `bootstrap.yml` на loopback до публикации роутера |
| PANEL-04 | SATISFIED | api-token 0600 |
| PANEL-05 | SATISFIED | `panel-routes.yml.j2`, TLS через resolver le |
| PANEL-06 | SATISFIED | см. истину 2 |
| SUB-01 / SUB-02 | SATISFIED | см. истину 4 |
| QA-05 | SATISFIED | check.sh guard на production CA + Pebble в VM-тире; CI не обращается к production LE |
| DOC-04 | SATISFIED | no_log gate, assert placeholder'ов |

Все 13 ID из PLAN frontmatter (DOC-04, EDGE-01..03, PANEL-01..06, QA-05, SUB-01, SUB-02) присутствуют в REQUIREMENTS.md, отмечены Complete; осиротевших требований нет.

### Автоматические проверки

| Проверка | Результат |
|----------|-----------|
| `scripts/check.sh` на текущем дереве (HEAD 0c0cd75) | `check.sh: OK` (ansible-lint, syntax-check, сборка коллекции, гейты) |
| CI на 93967d3: lint 46036846460, gate 46036846450, molecule-container 46036846451, molecule-vm 46038967381 (alma10, oracle10, rocky10) | все success (подтверждено `gh run view`) |
| Изменения кода после 93967d3 | только `roles/preflight/meta/argument_specs.yml` (+1 строка: `OracleLinux` в default); `check.sh` на этом дереве зелёный; отдельный CI-прогон на HEAD не проверялся |
| Известные flaky (secrets draw, panel-divergent-secret) | устранены 93967d3 (отладочная сессия flaky-panel-secrets-ci), CI после него зелёный |

### Антипаттерны

TBD/FIXME/XXX в файлах, изменённых после 75d71a4, не найдено. Замечания code review закрыты в 02-REVIEW-DISPOSITION.md.

## Требуется проверка человеком

1. **Production Let's Encrypt после переключения CA (UAT-тест 2, повтор).** На реальном Panel-хосте с `xvpn_edge_acme_ca: production` прогнать `playbooks/panel.yml`. Ожидается: Traefik перезапущен, создан `acme-production.json` (0600), Panel и subscription page отдают доверенный сертификат без предупреждений. Почему вручную: CI по QA-05 использует только Pebble.

## Итог

Цель фазы достигнута по всем пяти критериям и тринадцати требованиям; разрыв 02-UAT-G1 закрыт в коде, тестах и документации, CI зелёный. Единственный остаток: подтверждение реального production-сертификата на хосте пользователя.

---

_Проверено: 2026-11-27_
_Верификатор: Claude (gsd-verifier)_
