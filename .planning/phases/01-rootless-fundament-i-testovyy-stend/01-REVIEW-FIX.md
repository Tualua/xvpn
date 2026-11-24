---
phase: 01-rootless-fundament-i-testovyy-stend
fixed_at: 2026-11-24T00:00:00Z
review_path: /workspaces/xvpn/.planning/phases/01-rootless-fundament-i-testovyy-stend/01-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 7
skipped: 1
status: partial
---

# Phase 1: Отчёт об исправлениях по code review

**Исправлено:** 2026-11-24
**Исходный отчёт:** `/workspaces/xvpn/.planning/phases/01-rootless-fundament-i-testovyy-stend/01-REVIEW.md`
**Итерация:** 1

**Итого:**
- Находок в области: 8 (WR-01..WR-08; Info не входят в `critical_warning`)
- Исправлено: 7
- Пропущено: 1

Работа велась прямо в ветке `main` в основном checkout, без worktree (по указанию оркестратора). Проверки (`bash scripts/check.sh`, включая ansible-lint production, argument_specs, syntax-check, build и `yamllint -s .` yamllint 1.38.0) запускались в основном checkout после каждого исправления и проходили (кроме WR-04, где запускался только `yamllint -s` на изменённом файле). Molecule-сценарии локально не запускались: в окружении нет podman и VM, их прогонит CI.

## Fixed Issues

### WR-01: Роль «усыновляет» любую существующую учётную запись с uid >= 1000 и перезаписывает её shell, пароль и home
**Файлы:** `roles/podman_rootless/tasks/user.yml`
**Коммит:** ed1515b
**Исправление:** проверка перед `ansible.builtin.user` теперь требует от уже существующего аккаунта uid >= 1000, home `<home_root>/<name>` и shell `nologin`. Иначе роль падает, не меняя shell, пароль и home чужой учётной записи.
**Статус:** fixed: requires human verification (логика условия).

### WR-02: Валидация `xvpn_podman_rootless_home_root` допускает `..` и системные каталоги, затем идут chmod/chown и рекурсивный restorecon
**Файлы:** `roles/podman_rootless/tasks/main.yml`
**Коммит:** 52820b2
**Исправление:** новый regex не допускает `..` и ведущие/пустые сегменты, добавлены явная проверка на `..` и denylist системных каталогов (`/usr`, `/etc`, `/var`, `/var/lib`, `/home` и др.). Значение по умолчанию `/var/lib/xvpn` проходит.
**Статус:** fixed.

### WR-03: `restorecon` запускается только если `sefcontext` изменился, поэтому прерванный первый прогон оставляет неверные метки навсегда
**Файлы:** `roles/podman_rootless/tasks/main.yml`
**Коммит:** 16aed53
**Исправление:** добавлен read-only probe `restorecon -n -v <home_root>` (`changed_when` по строке `Would relabel`). Рекурсивный `restorecon -R` выполняется, если изменился `sefcontext` или probe показал неверную метку. Probe намеренно нерекурсивный (отличие от предложения в REVIEW.md): рекурсивный probe постоянно находил бы файлы хранилища контейнеров с метками `container_file_t` и ломал бы идемпотентность, а `restorecon -R` мог бы их сбросить.
**Статус:** fixed: requires human verification (поведение проверяется только в VM-тире с SELinux enforcing).

### WR-04: Задача `lint` в `lint.yml` не имеет `timeout-minutes`
**Файлы:** `.github/workflows/lint.yml`
**Коммит:** 0277145
**Исправление:** добавлен `timeout-minutes: 20`.
**Статус:** fixed.

### WR-05: SELinux-гейт в роли `common` стоит после установки пакетов и не защищает `podman_rootless` при отдельном запуске
**Файлы:** `roles/common/tasks/main.yml`, `roles/podman_rootless/tasks/main.yml`
**Коммит:** d33f6b6
**Исправление:** в `common` проверка `getenforce` перенесена перед `dnf install`. В `podman_rootless/tasks/main.yml` добавлен такой же гейт первым действием роли. Ветки «SELinux выключен» (`ignore_selinux_state`, `when: selinux.rc == 0`) в `podman_rootless` сохранены: контейнерный Molecule-тир использует тестовый двойник `getenforce` на ядре без SELinux, и без этих веток он перестал бы работать. Гейт при этом по-прежнему требует, чтобы `getenforce` сообщал `Enforcing`.
**Статус:** fixed.

### WR-06: Валидация Quadlet изолирует спеки одного вызова, поэтому юниты со ссылками на `.network`/`.volume` из другого вызова будут ложно отклонены; проверка «ожидаемый сервис» подстрочная
**Файлы:** `roles/podman_rootless/tasks/quadlet_validate.yml`
**Коммит:** 1294083
**Исправление:** scratch-каталог перед рендером кандидатов заполняется уже установленными юнитами из `~/.config/containers/systemd` пользователя (если каталог есть), так что ссылки на `.network`/`.volume` из прежних вызовов разрешаются. Проверка ожидаемого сервиса теперь ищет строку-заголовок `---<service>---` (с допуском префикса пути) вместо подстроки.
**Статус:** fixed: requires human verification. Точный формат заголовка dry-run (`---name.service---`) не удалось проверить локально (нет podman); если Podman печатает иной формат, проверка «ожидаемый сервис» упадёт в container/VM-тире, это нужно подтвердить прогоном CI.

### WR-07: Проверка DNS в preflight падает необработанной ошибкой шаблона, если факты выбранного интерфейса отсутствуют
**Файлы:** `roles/preflight/tasks/check_dns.yml`
**Коммит:** af4a89a
**Исправление:** выражение для набора IPv4-адресов теперь безопасно к отсутствующему интерфейсу/ключу `ipv4`. Если адресов нет, в агрегированный список `xvpn_preflight_errors` добавляется сообщение, а сравнение A/AAAA пропускается (вложенный блок с `when`). Выражение проверено отдельным ad-hoc плейбуком на отсутствующем и присутствующем интерфейсе.
**Статус:** fixed.

## Skipped Issues

### WR-08: Воркфлоу `molecule-vm` ставит vagrant-libvirt и ключ HashiCorp без проверки отпечатка и запускается на каждом PR
**Файл:** `.github/workflows/molecule-vm.yml:49-55`
**Причина:** пропущено, нет проверяемого авторитетного значения. Ключ с `https://apt.releases.hashicorp.com/gpg` сейчас отдаёт отпечаток `D55C0D1AC78A8D8126CB631CFC9CA96ACA026560`, но подтвердить его по независимому источнику не удалось (страницы безопасности HashiCorp отвечают 429/404). Пинить значение, полученное из того же канала, который нужно проверять, бессмысленно, а отпечаток по памяти (старый ключ) заведомо расходится с текущим. Хеш плагина vagrant-libvirt 0.12.2 также не подтверждён. Ограничение запуска для PR из форков не применялось: это изменение политики CI, его решает человек (форки и так получают только `contents: read`).
**Исходная проблема:** цепочка поставки HashiCorp/RubyGems слабее остальной (действия пинятся по SHA, боксы по checksum).
**Что нужно:** взять отпечаток текущего ключа подписи пакетов с официального ресурса HashiCorp, добавить сверку через `gpg --show-keys --with-colons` перед установкой ключа, при желании добавить `if` для fork-PR.

---

_Fixed: 2026-11-24_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
