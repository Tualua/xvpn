---
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
reviewed: 2026-11-25T00:00:00Z
depth: standard
files_reviewed: 64
files_reviewed_list:
  - .github/workflows/gate.yml
  - .github/workflows/lint.yml
  - .gitleaks.toml
  - README.md
  - extensions/molecule/container/converge.yml
  - extensions/molecule/container/molecule.yml
  - extensions/molecule/container/verify.yml
  - extensions/molecule/shared/verify_common.yml
  - extensions/molecule/shared/verify_edge.yml
  - extensions/molecule/shared/verify_gate.yml
  - extensions/molecule/shared/verify_gate_log.yml
  - extensions/molecule/shared/verify_gate_requests.yml
  - extensions/molecule/shared/verify_panel.yml
  - extensions/molecule/shared/verify_rootless.yml
  - extensions/molecule/shared/verify_runtime.yml
  - extensions/molecule/shared/verify_subpage.yml
  - extensions/molecule/vm/converge.yml
  - extensions/molecule/vm/molecule.yml
  - extensions/molecule/vm/prepare.yml
  - extensions/molecule/vm/side_effect.yml
  - extensions/molecule/vm/tasks/pebble.yml
  - extensions/molecule/vm/vars/panel.yml
  - extensions/molecule/vm/verify.yml
  - galaxy.yml
  - playbooks/panel.yml
  - playbooks/site.yml
  - roles/edge/defaults/main.yml
  - roles/edge/files/decoy/index.html
  - roles/edge/meta/argument_specs.yml
  - roles/edge/meta/main.yml
  - roles/edge/tasks/main.yml
  - roles/edge/tasks/route.yml
  - roles/edge/templates/00-edge.yml.j2
  - roles/edge/templates/decoy-nginx.conf.j2
  - roles/edge/templates/traefik.container.j2
  - roles/edge/templates/traefik.yml.j2
  - roles/edge/templates/xvpn-decoy.container.j2
  - roles/panel/defaults/main.yml
  - roles/panel/meta/argument_specs.yml
  - roles/panel/meta/main.yml
  - roles/panel/tasks/bootstrap.yml
  - roles/panel/tasks/main.yml
  - roles/panel/tasks/routes.yml
  - roles/panel/tasks/secrets.yml
  - roles/panel/tasks/stack.yml
  - roles/panel/tasks/subpage.yml
  - roles/panel/templates/backend.env.j2
  - roles/panel/templates/panel-routes.yml.j2
  - roles/panel/templates/postgres.env.j2
  - roles/panel/templates/remnawave-db.container.j2
  - roles/panel/templates/remnawave-db.volume.j2
  - roles/panel/templates/remnawave-redis.container.j2
  - roles/panel/templates/remnawave-subscription-page.container.j2
  - roles/panel/templates/remnawave-valkey.volume.j2
  - roles/panel/templates/remnawave.container.j2
  - roles/panel/templates/remnawave.network.j2
  - roles/panel/templates/subpage.env.j2
  - roles/panel/templates/subscription-routes.yml.j2
  - roles/podman_rootless/defaults/main.yml
  - scripts/check.sh
  - scripts/check_no_log.py
  - scripts/ci_watch.sh
  - scripts/gate/render.yml
  - scripts/gate/run.sh
findings:
  critical: 0
  warning: 5
  info: 7
  total: 12
  necessity: 1
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-11-25
**Depth:** standard
**Files Reviewed:** 64
**Status:** issues_found

## Summary

Просмотрены роли `edge` и `panel`, шаблоны Quadlet и Traefik, плейбуки, скрипты `scripts/*` (check, check_no_log, ci_watch, gate) и Molecule-харнесс (container и VM-уровни). Файл `references/necessity-review.md` прочитан.

Общая оценка: фаза выполнена добротно. Матрица gate (регистр, двойные слэши, dot-сегменты, percent-encoding, якоря cookie-regex) покрывает реальные обходы. Секреты нигде не печатаются, а аудит no_log/diff:false последователен. Блокирующих дефектов (утечка секрета, обход gate, потеря данных) не найдено. Миттигации из 02-SECURITY.md проверены выборочно (gate-маршруты, `accessLogs: false`, `RequestPath: drop`, режимы файлов) и не сломаны.

Найдены пять предупреждений и семь замечаний. Главное из них: сигнал "env/static изменился" живёт только внутри одного прогона, и сбой между рендером и рестартом навсегда оставляет контейнер на старой конфигурации. Второе: проверка целостности `panel-secrets.yml` принимает файл с частью ключей и молча генерирует недостающие секреты рядом с живой БД.

## Warnings

### WR-01: Частичный `panel-secrets.yml` проходит проверку целостности, недостающие секреты генерируются заново

**File:** `roles/panel/tasks/secrets.yml:49-66` (merge: `:123-133`)
**Issue:** Проверка `xvpn_panel_secrets_file_ok` требует только, чтобы файл был непустым mapping без чужих ключей. Файл с подмножеством ключей (например, после ручной правки или обрезки, оставшийся только с `gate_path`) проходит проверку. `combine(generated, stored, overrides)` тогда подставляет свежесгенерированные `postgres_password`, `app_secret`, `admin_password`, `metrics_*`. Это ровно тот сценарий, который комментарий на строках 46-48 и guard на строках 18-32 призваны исключить: новые секреты поверх инициализированной БД. Пароль Postgres в `postgres.env` изменится, а в БД останется старый. Бэкенд не подключится, bootstrap зависнет в логине с подставленным новым `admin_password`, и причина будет не очевидна. Файл при этом будет перезаписан (строка 196), и исходные значения потеряны.
**Fix:** Когда файл существует, требовать наличие неизменяемых ключей:
```yaml
- name: Panel secrets | assert the stored file holds every immutable key
  ansible.builtin.assert:
    that:
      - ['app_secret', 'postgres_password', 'metrics_user', 'metrics_password', 'admin_password']
        | difference(xvpn_panel_secrets_stored.keys() | list) | length == 0
    fail_msg: "panel-secrets.yml misses immutable keys; restore it from backup (Phase 5)"
    quiet: true
  when: xvpn_panel_secrets_stat.stat.exists
```
Ключи gate (`gate_path`, `gate_cookie_*`) можно докомплектовывать генерацией, они ротируемые.

### WR-02: Rescue-ветка стека печатает логи контейнеров и journal в `fail_msg` без фильтрации

**File:** `roles/panel/tasks/stack.yml:78-102`
**Issue:** При сбое старта `fail` выводит `xvpn_panel_start_journal.stdout` и `xvpn_panel_start_logs.stdout` (по 20 строк логов `remnawave-db`, `remnawave-redis`, `remnawave`, плюс journal пользователя) в открытом виде в вывод плейбука и CI-лог. Логи бэкенда и Prisma при ошибках конфигурации и подключения могут содержать фрагменты DATABASE_URL, значения env или заголовки. Проектный DOC-04 требует, чтобы запуск не печатал секретов. Сам харнесс в `verify_subpage.yml:~103-106` фильтрует строки по `token|bearer|authorization|jwt`, а роль нет. Поверхность невелика, но это единственное место роли, где неконтролируемый вывод контейнера попадает в сообщение об ошибке.
**Fix:** Фильтровать строки и ограничивать объём:
```yaml
msg: >-
  Panel stack start failed: {{ ansible_failed_result.msg | default('') }}
  {{ ((xvpn_panel_start_journal.stdout_lines | default([])) + (xvpn_panel_start_logs.stdout_lines | default([])))
     | reject('search', '(?i)token|bearer|authorization|jwt|password|secret|DATABASE_URL|APP_SECRET|METRICS_PASS')
     | join(' | ') }}
```

### WR-03: Регулярка FQDN отвергает punycode-TLD (`xn--p1ai` и т. п.), вопреки README

**File:** `roles/panel/tasks/main.yml:6` и `:15`
**Issue:** `^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?[.])+[a-z]{2,63}$` требует, чтобы TLD состоял только из букв. Реальные IDN-TLD в punycode (`.xn--p1ai` для `.рф`, `.xn--80asehdb` и др.) содержат цифры и дефис, поэтому валидные домены отвергаются с сообщением "must be a real lowercase FQDN". README (строка 45) при этом прямо предписывает вводить IDN в punycode-форме. Проверка на шаге Panel host происходит уже после preflight, так что оператор получает отказ посреди прогона.
**Fix:** Разрешить punycode-TLD:
```yaml
- xvpn_panel_domain is regex('^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?[.])+([a-z]{2,63}|xn--[a-z0-9-]{1,59})$')
```
То же для `xvpn_subscription_domain`. Вынести в общую переменную, чтобы не дублировать регулярку.

### WR-04: Проверка DOC-04 (`check_no_log.py`) не видит секреты, которые приходят только через `.j2`-шаблон

**File:** `scripts/check_no_log.py:14-30` и `:60-61`
**Issue:** Сканер ищет чувствительные имена только в ключах задачи (`json.dumps(keys)`). Задачи, которые рендерят секретные файлы, не содержат этих имён в самой задаче. В `stack.yml:20-40` это `src: postgres.env.j2` и `src: backend.env.j2`, а в `subpage.yml:168-178` это `src: subpage.env.j2`, где значение берёт `xvpn_panel_sp_token`. Паттерн `xvpn_panel_api_token\b` не совпадает с `xvpn_panel_sp_token`. Сегодня `no_log` и `diff: false` на этих задачах стоят, но стоят они вручную: guard ничего не проверяет и даёт ложную уверенность. Задача, добавленная в Phase 3 (node env, token-файлы), с шаблоном `*.env.j2` без `no_log` пройдёт `check.sh`.
**Fix:** Добавить правило по имени/пути: любая задача `template`/`copy` с `src` или `dest`, оканчивающимся на `.env.j2`, `.env` или `secrets/*`, обязана иметь `no_log` и `diff: false`. Добавить в `SENSITIVE` `xvpn_panel_sp_token`. Покрыть самотестом (задача-приманка).

### WR-05: Сигнал "конфигурация изменилась" теряется при сбое между рендером и рестартом

**File:** `roles/panel/tasks/stack.yml:31-40` и `:105-131`; `roles/panel/tasks/subpage.yml:168-208`; `roles/edge/tasks/main.yml:49-56` и `:141-153`
**Issue:** Рестарт зависит от `register: ... is changed` в том же прогоне. Порядок такой: рендер env или `traefik.yml`, затем `include_role` Quadlet-деплоя (с dry-run генератором и запуском юнитов), затем рестарт. Если деплой упадёт (ошибка генератора, таймаут старта, сбой rescue), то файл на диске уже новый. В следующем прогоне шаблон `ok`, рестарт не срабатывает, а контейнер продолжает работать со старой конфигурацией, потому что env и `traefik.yml` читаются только при старте. Для Traefik это означает, что новый caServer, адреса entrypoint или CA-файл не применятся до ближайшего перезапуска хоста. Для sub-page новый токен не попадёт в контейнер, и страница перестанет проходить авторизацию. Нарушается идемпотентность "сходимости": повторный запуск не исправляет состояние.
**Fix:** Не полагаться на состояние внутри прогона. Варианты: (a) сравнивать время старта юнита (`systemctl --user show -p ActiveEnterTimestampMonotonic`) с mtime файла и рестартовать, если файл новее; (b) записывать маркер-файл "applied" с checksum после успешного рестарта и сравнивать с checksum env; (c) как минимум вынести рестарт в `block/always` вокруг деплоя, чтобы он выполнялся даже при сбое соседних задач.

## Info

### IN-01: Лишние рестарты при первой установке

**File:** `roles/panel/tasks/stack.yml:105-131`, `roles/panel/tasks/subpage.yml:196-208`, `roles/edge/tasks/main.yml:141-167`
**Issue:** При создании файла с нуля задача env/static всегда `changed`, поэтому сразу после первого старта юниты рестартуются повторно. Postgres перезапускается сразу после initdb, а `Requires=` тянет за ним рестарт бэкенда. Это безвредно (юниты `Notify=healthy` ждут готовности), но удлиняет первый запуск и делает вывод шумным.
**Fix:** Рестартовать только если юнит уже был активен до деплоя (`systemctl --user is-active` до `include_role`) либо если файл существовал (`stat` до рендера).

### IN-02: Канарейка AVC для Pebble считает любую ошибку `ausearch` чистым результатом

**File:** `extensions/molecule/vm/tasks/pebble.yml:177-185`
**Issue:** `assert: item.rc != 0`. `ausearch` возвращает 1 при "no matches", но и другие коды (ошибка разбора `-ts`, нет прав, отсутствие аудит-лога) тоже `!= 0`. Канарейка тогда молча проходит, хотя ничего не проверила. Итоговый ворота в `verify_runtime.yml:~340-345` сделаны правильно (`rc == 1` и `<no matches>`), и здесь нужно то же.
**Fix:**
```yaml
that:
  - item.rc == 1
  - item.stderr is search('<no matches>')
```

### IN-03: `shuffle` использует не криптографический ГСЧ при сборке паролей

**File:** `roles/panel/tasks/secrets.yml:83-101`
**Issue:** Символы берутся из `lookup('password')` (secrets/SystemRandom), но порядок перемешивания даёт фильтр `shuffle` (Mersenne Twister из `random`). Энтропия самих символов достаточна, но порядок классов символов предсказуем при знании состояния MT. Практический риск мал, однако для генератора паролей лучше не смешивать источники.
**Fix:** Не перемешивать вовсе: один вызов `lookup('password', ..., chars=['ascii_letters','digits'], length=N)` повторять, пока результат не содержит все три класса (цикл `until`), либо сгенерировать класс-гарантии и перемешать на SystemRandom (например, `community.general.random_string` / собственный фильтр).

### IN-04: Якорь `$` в regex-форматах секретов допускает хвостовой перевод строки

**File:** `roles/panel/tasks/secrets.yml:152-160`
**Issue:** Тест `regex` в Jinja использует `re.search`, а `$` в Python совпадает и перед завершающим `\n`. Значение из vault, заданное блочным скаляром (`|`), с хвостовым переводом строки пройдёт проверки `app_secret`, `postgres_password`, `gate_path` и попадёт в env-файл и в regex Traefik (`Path`) с переводом строки внутри.
**Fix:** Заменить `$` на `\Z` в `xvpn_panel_secret_formats` либо `| trim` значения и сравнивать с исходным.

### IN-05: Часть операторских значений интерполируется в YAML Traefik без валидации

**File:** `roles/edge/tasks/main.yml:12`; `roles/edge/templates/traefik.yml.j2:24,35,57,62`
**Issue:** `xvpn_edge_acme_email` проверяется регуляркой `^[^@ ]+@[^@ ]+$`, которая допускает кавычки и переводы строк. `xvpn_edge_http_address`, `xvpn_edge_https_address` не проверяются вообще. Значения подставляются в YAML в двойных кавычках, так что `"` или `\n` ломает или расширяет статический конфиг Traefik. Источник значений оператор, поэтому это вопрос устойчивости, а не эксплуатации извне.
**Fix:** Ужесточить регулярки: email `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+$`, адреса `^[0-9.\[\]:a-z]*:[0-9]{1,5}$`. Либо рендерить через `| to_json`.

### IN-06: `ci_watch.sh` сравнивает `createdAt` запуска с локальными часами

**File:** `scripts/ci_watch.sh:106-110`, `:121-122`
**Issue:** В режиме `--dispatch` отбираются запуски с `createdAt >= START`, где `START` взят из локального `date -u`. Если локальные часы опережают GitHub хотя бы на несколько секунд, только что запущенный run отсеивается. Скрипт ждёт 600 с и завершается ошибкой "no run", хотя запуск был успешен.
**Fix:** Не сравнивать с часами: до `gh workflow run` запомнить `databaseId` последнего запуска и после диспетчеризации ждать запуск с большим id; либо вычесть запас (`START - 60 s`) и фильтровать по `headSha` и `event`.

### IN-07: Переменная `xvpn_panel_bootstrap_password_key` (necessity: generality without instantiation)

**File:** `roles/panel/defaults/main.yml:59-60`, `roles/panel/meta/argument_specs.yml:130-133`, `roles/panel/tasks/bootstrap.yml:111`
**Category:** necessity
**Issue:** Переменная существует только затем, чтобы подставить имя ключа в сообщение об ошибке, и во всём репозитории имеет единственное значение `admin_password`. Ключ жёстко зашит в самой логике (`xvpn_panel_secrets.admin_password` на строках 54 и 88 `bootstrap.yml`), поэтому изменение переменной ничего не перенастроит и лишь приведёт к неверному сообщению. Абстракция имеет один экземпляр и вынесена в публичный интерфейс роли (argument_specs). Суждение, а не доказанный дефект, поэтому Info.
**Fix:** Удалить переменную и спецификацию, написать `admin_password` прямо в тексте сообщения. То же рассмотреть для `xvpn_panel_api_token_probe_route`, если у него нет второго потребителя кроме верификаторов.

---

_Reviewed: 2026-11-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
