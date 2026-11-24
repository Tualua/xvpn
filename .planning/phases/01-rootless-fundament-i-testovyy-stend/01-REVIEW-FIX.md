---
phase: 01-rootless-fundament-i-testovyy-stend
fixed_at: 2026-11-24T00:00:00Z
review_path: /workspaces/xvpn/.planning/phases/01-rootless-fundament-i-testovyy-stend/01-REVIEW.md
iteration: 2
findings_in_scope: 14
fixed: 13
skipped: 1
status: partial
---

# Phase 1: Отчёт об исправлениях по code review

**Исправлено:** 2026-11-24
**Исходный отчёт:** `/workspaces/xvpn/.planning/phases/01-rootless-fundament-i-testovyy-stend/01-REVIEW.md`
**Итерация:** 2

**Итого:**
- Находок в области: 14 (WR-01..WR-08 в итерации 1; IN-01..IN-06 в итерации 2, `fix_scope: all`)
- Исправлено: 13
- Пропущено: 1

Итерация 2 (IN-01..IN-06) выполнена так же, в `main`, без worktree; `bash scripts/check.sh` со строгим yamllint проходил после каждого исправления. Molecule локально не запускался.

Итерация 1: работа велась прямо в ветке `main` в основном checkout, без worktree (по указанию оркестратора). Проверки (`bash scripts/check.sh`, включая ansible-lint production, argument_specs, syntax-check, build и `yamllint -s .` yamllint 1.38.0) запускались в основном checkout после каждого исправления и проходили (кроме WR-04, где запускался только `yamllint -s` на изменённом файле). Molecule-сценарии локально не запускались: в окружении нет podman и VM, их прогонит CI.

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

### IN-01: Повторная SSH-проверка «after» в `firewalld.yml` недостижима для падения
**Файлы:** `roles/common/tasks/firewalld.yml`
**Коммит:** c2e22af
**Исправление:** удалён блок «after» (два `command` и `fail`). Вместо него оставлен комментарий: задача `ansible.posix.firewalld` только добавляет порты. Проверка «before» сохранена.
**Статус:** fixed: requires human verification (необходимость удаляет код).

### IN-02: Проверка конфликта портов в preflight учитывает только TCP
**Файлы:** `roles/preflight/defaults/main.yml`, `roles/preflight/meta/argument_specs.yml`
**Коммит:** 9832c5a
**Исправление:** выбран вариант с документацией: ограничение «только TCP» описано в комментарии defaults и в описании `xvpn_preflight_ports`. Поведение не менялось, формат `<port>/<proto>` не вводился.
**Статус:** fixed.

### IN-03: SSH-гейт использует `ansible_port` контроллера, а не порт sshd на целевом хосте
**Файлы:** `roles/common/tasks/firewalld.yml`, `roles/common/defaults/main.yml`, `roles/common/meta/argument_specs.yml`
**Коммит:** 3a68500
**Исправление:** добавлена переменная `xvpn_common_ssh_port` (по умолчанию `ansible_port | default(22)`, тип `int` в `argument_specs`); гейт использует её. Поведение по умолчанию прежнее. Проверка `verify_common.yml` по-прежнему берёт `ansible_port`, что совпадает с дефолтом.
**Статус:** fixed.

### IN-04: Слабые проверки в `verify_rootless.yml` для sysctl
**Файлы:** `extensions/molecule/shared/verify_rootless.yml`
**Коммит:** 5cc4c5c
**Исправление:** путь drop-in и значение берутся из `xvpn_podman_rootless_sysctl_file` и `xvpn_podman_rootless_unprivileged_port_start` с теми же дефолтами. Содержимое проверяется построчно через `is search('(?m)^net\.ipv4\.ip_unprivileged_port_start\s*=\s*<value>\s*$')` (`search`, а не `match`, потому что `match` якорится только в начале строки и не видит строку после комментария). Выражение проверено ad-hoc плейбуком: `80` проходит, `800` отвергается. Формат строки `ansible.posix.sysctl` (`name=value`) подходит под шаблон.
**Статус:** fixed.

### IN-05: `xvpn_podman_rootless_unprivileged_port_start` не ограничен
**Файлы:** `roles/podman_rootless/tasks/main.yml`, `roles/podman_rootless/meta/argument_specs.yml`
**Коммит:** 5194dad
**Исправление:** перед установкой пакетов добавлен `assert` 1 <= значение <= 80 с понятным сообщением; диапазон описан в `argument_specs`. Значение по умолчанию 80 проходит.
**Статус:** fixed.

### IN-06: Дублирование запусков CI и строгие `suboptions` спецификации
**Файлы:** `roles/podman_rootless/meta/argument_specs.yml`
**Коммит:** cf16378
**Исправление:** выполнена только часть (2): в описание `xvpn_podman_rootless_quadlet_specs` добавлено, что набор ключей закрыт (`template_src`, `state`) и что спецификацию нужно расширить до передачи других ключей в LSR-роль. Часть (1), триггеры CI в `.github/workflows/lint.yml` и `molecule-container.yml`, намеренно не менялась: раскладка `push` и `pull_request` выбрана планами сознательно, смена затрагивает политику CI и остаётся за человеком.
**Статус:** fixed (частично, см. примечание).

## Skipped Issues

### WR-08: Воркфлоу `molecule-vm` ставит vagrant-libvirt и ключ HashiCorp без проверки отпечатка и запускается на каждом PR
**Файл:** `.github/workflows/molecule-vm.yml:49-55`
**Причина:** пропущено, нет проверяемого авторитетного значения. Ключ с `https://apt.releases.hashicorp.com/gpg` сейчас отдаёт отпечаток `D55C0D1AC78A8D8126CB631CFC9CA96ACA026560`, но подтвердить его по независимому источнику не удалось (страницы безопасности HashiCorp отвечают 429/404). Пинить значение, полученное из того же канала, который нужно проверять, бессмысленно, а отпечаток по памяти (старый ключ) заведомо расходится с текущим. Хеш плагина vagrant-libvirt 0.12.2 также не подтверждён. Ограничение запуска для PR из форков не применялось: это изменение политики CI, его решает человек (форки и так получают только `contents: read`).
**Исходная проблема:** цепочка поставки HashiCorp/RubyGems слабее остальной (действия пинятся по SHA, боксы по checksum).
**Что нужно:** взять отпечаток текущего ключа подписи пакетов с официального ресурса HashiCorp, добавить сверку через `gpg --show-keys --with-colons` перед установкой ключа, при желании добавить `if` для fork-PR.

---

_Fixed: 2026-11-24_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
