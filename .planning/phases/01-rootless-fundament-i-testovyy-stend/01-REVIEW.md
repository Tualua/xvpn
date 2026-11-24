---
phase: 01-rootless-fundament-i-testovyy-stend
reviewed: 2026-11-24T00:00:00Z
depth: standard
files_reviewed: 54
files_reviewed_list:
  - .ansible-lint
  - .github/workflows/lint.yml
  - .github/workflows/molecule-container.yml
  - .github/workflows/molecule-vm.yml
  - .gitignore
  - .yamllint
  - LICENSE
  - README.md
  - ansible.cfg
  - changelogs/changelog.yaml
  - extensions/molecule/container/converge.yml
  - extensions/molecule/container/molecule.yml
  - extensions/molecule/container/prepare.yml
  - extensions/molecule/container/verify.yml
  - extensions/molecule/preflight/converge.yml
  - extensions/molecule/preflight/molecule.yml
  - extensions/molecule/preflight/prepare.yml
  - extensions/molecule/preflight/run_case.yml
  - extensions/molecule/preflight/verify.yml
  - extensions/molecule/shared/templates/xvpn-broken.container.j2
  - extensions/molecule/shared/templates/xvpn-fixture.container.j2
  - extensions/molecule/shared/verify_common.yml
  - extensions/molecule/shared/verify_rootless.yml
  - extensions/molecule/shared/verify_runtime.yml
  - extensions/molecule/vm/converge.yml
  - extensions/molecule/vm/molecule.yml
  - extensions/molecule/vm/prepare.yml
  - extensions/molecule/vm/side_effect.yml
  - extensions/molecule/vm/verify.yml
  - galaxy.yml
  - meta/runtime.yml
  - playbooks/foundation.yml
  - playbooks/preflight.yml
  - requirements-dev.txt
  - requirements.yml
  - roles/common/defaults/main.yml
  - roles/common/meta/argument_specs.yml
  - roles/common/meta/main.yml
  - roles/common/tasks/firewalld.yml
  - roles/common/tasks/main.yml
  - roles/podman_rootless/defaults/main.yml
  - roles/podman_rootless/meta/argument_specs.yml
  - roles/podman_rootless/meta/main.yml
  - roles/podman_rootless/tasks/main.yml
  - roles/podman_rootless/tasks/quadlet.yml
  - roles/podman_rootless/tasks/quadlet_validate.yml
  - roles/podman_rootless/tasks/user.yml
  - roles/preflight/defaults/main.yml
  - roles/preflight/meta/argument_specs.yml
  - roles/preflight/meta/main.yml
  - roles/preflight/tasks/check_dns.yml
  - roles/preflight/tasks/check_podman.yml
  - roles/preflight/tasks/check_ports.yml
  - roles/preflight/tasks/main.yml
  - scripts/check.sh
findings:
  critical: 0
  warning: 8
  info: 6
  total: 14
  necessity: 1
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-11-24
**Depth:** standard
**Files Reviewed:** 54
**Status:** issues_found

## Summary

Просмотрены роли `preflight`, `common`, `podman_rootless`, три сценария Molecule (container, preflight, vm), CI-воркфлоу и `scripts/check.sh`. Структурный пре-проход (fallow) не передавался. Файл `~/.claude/gsd-core/references/necessity-review.md` не читался; категория necessity оценена по месту, по доказательствам из репозитория (одна находка, IN-01).

Критических дефектов безопасности и потери данных не найдено. Основные риски: деструктивное «усыновление» существующей учётной записи (WR-01), слабая валидация `xvpn_podman_rootless_home_root` при рекурсивном `restorecon` (WR-02), дыра в идемпотентности релейблинга SELinux (WR-03), SELinux-гейт в `common` срабатывает после установки пакетов (WR-05), неагрегированные падения в DNS-проверке preflight (WR-07), отсутствие `timeout-minutes` в `lint.yml` (WR-04).

## Warnings

### WR-01: Роль «усыновляет» любую существующую учётную запись с uid >= 1000 и перезаписывает её shell, пароль и home

**File:** `roles/podman_rootless/tasks/user.yml:17-34`
**Issue:** Защита отсекает только системные аккаунты (uid < 1000). Если в `xvpn_podman_rootless_users` указано имя реального человека-пользователя (uid >= 1000), модуль `user` выставит ему `shell: /sbin/nologin`, `password_lock: true` и новый `home`. Затем `file` сменит владельца и права на 0700. Это блокирует вход живому пользователю. Опечатка в имени или совпадение с существующим именем приводят к локауту.
**Fix:** Усыновлять только аккаунт, который уже выглядит как управляемый: ожидаемый home под `xvpn_podman_rootless_home_root` и shell `/sbin/nologin`. Иначе падать.
```yaml
- name: Refuse to adopt an account that this collection did not create
  ansible.builtin.assert:
    that:
      - ansible_facts['getent_passwd'][xvpn_podman_rootless_user.name][1] | int >= 1000
      - ansible_facts['getent_passwd'][xvpn_podman_rootless_user.name][4]
        == xvpn_podman_rootless_home_root ~ '/' ~ xvpn_podman_rootless_user.name
      - ansible_facts['getent_passwd'][xvpn_podman_rootless_user.name][5] in ['/sbin/nologin', '/usr/sbin/nologin']
  when: ansible_facts['getent_passwd'][xvpn_podman_rootless_user.name] is not none
```

### WR-02: Валидация `xvpn_podman_rootless_home_root` допускает `..` и системные каталоги, затем идут chmod/chown и рекурсивный restorecon

**File:** `roles/podman_rootless/tasks/main.yml:13-18, 54-79`
**Issue:** Регулярное выражение `^/[A-Za-z0-9_./-]+$` пропускает `/usr`, `/etc`, `/var/lib` и `/../etc`. Для такого значения роль выставит владельца root и права 0755, создаст эквивалентность `sefcontext` (`target -> /home`) и выполнит `restorecon -R`. Это рекурсивный релейбл системного дерева. Источник значения — инвентарь, но роль заявляет входную валидацию (T-01-07), и она неполна.
**Fix:** Запретить `..` и ограничить допустимые родители. Для SELinux-эквивалентности нужен выделенный каталог.
```yaml
that:
  - xvpn_podman_rootless_home_root is match('^/[A-Za-z0-9_-]+(/[A-Za-z0-9_.-]+)*$')
  - "'..' not in xvpn_podman_rootless_home_root"
  - xvpn_podman_rootless_home_root not in ['/usr', '/etc', '/var', '/var/lib', '/opt', '/srv', '/home', '/root']
```

### WR-03: `restorecon` запускается только если `sefcontext` изменился, поэтому прерванный первый прогон оставляет неверные метки навсегда

**File:** `roles/podman_rootless/tasks/main.yml:62-79`
**Issue:** Задача `restorecon -R` условна по `xvpn_podman_rootless_sefcontext is changed`. Если первый прогон упал между `sefcontext` и `restorecon` (или `restorecon` сам завершился ошибкой), повторный прогон видит эквивалентность уже установленной, пропускает `restorecon`, и метки `var_lib_t` остаются. Домашние каталоги, созданные ранее, не релейблятся. Идемпотентные модули не должны зависеть от того, что предыдущая итерация дошла до конца. Верификация VM поймает это только на чистом стенде.
**Fix:** Проверять фактическую метку и релейблить по результату проверки.
```yaml
- name: Check that the home root already carries the /home-equivalent label
  ansible.builtin.command: restorecon -nvR {{ xvpn_podman_rootless_home_root | quote }}
  register: xvpn_podman_rootless_relabel_probe
  changed_when: xvpn_podman_rootless_relabel_probe.stdout | length > 0
  check_mode: false
  when: xvpn_podman_rootless_selinux.rc == 0
# then run `restorecon -R` when xvpn_podman_rootless_relabel_probe is changed
```

### WR-04: Задача `lint` в `lint.yml` не имеет `timeout-minutes`

**File:** `.github/workflows/lint.yml:17-18`
**Issue:** Остальные воркфлоу ограничены (`45`/`120` минут), у `lint` лимита нет, действует дефолт GitHub 360 минут. Зависание `ansible-galaxy collection install` (сеть Galaxy) блокирует runner на шесть часов. Это нарушает проектное требование о CI-дисциплине.
**Fix:**
```yaml
jobs:
  lint:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
```

### WR-05: SELinux-гейт в роли `common` стоит после установки пакетов и не защищает `podman_rootless` при отдельном запуске

**File:** `roles/common/tasks/main.yml:20-38`, `roles/podman_rootless/tasks/main.yml:20-67`
**Issue:** Комментарий называет блок «defence in depth», но `dnf install` идёт раньше проверки `getenforce`. При Permissive/Disabled хост уже изменён, хотя ограничение проекта запрещает работу без Enforcing. Роль `podman_rootless` вообще не имеет гейта и сама допускает отключённый SELinux (`ignore_selinux_state` и `when: selinux.rc == 0`). Если её вызвать без `foundation.yml` (в том числе через `tasks_from: quadlet`), роль молча создаст пользователей, выставит sysctl и продолжит.
**Fix:** Поставить проверку `getenforce` первой задачей в `common` (до `dnf`) и добавить такой же короткий гейт в начало `podman_rootless/tasks/main.yml`. В `podman_rootless` убрать ветки «SELinux выключен» либо превратить их в `fail`.

### WR-06: Валидация Quadlet изолирует спеки одного вызова, поэтому юниты со ссылками на `.network`/`.volume` из другого вызова будут ложно отклонены; проверка «ожидаемый сервис» подстрочная

**File:** `roles/podman_rootless/tasks/quadlet_validate.yml:36-73`
**Issue:** Генератор запускается с `QUADLET_UNIT_DIRS` на scratch-каталог, в который попадают только спеки текущего вызова. Для `.container` с `Network=panel.network` или `Volume=pg.volume`, объявленными отдельным вызовом `tasks_from: quadlet`, генератор вернёт ошибку «not found», и деплой упадёт, хотя юнит корректен. Из плана Panel/Node (фазы 2-4) это неизбежный сценарий. Также `expected_service in stdout` — подстрочное совпадение: `foo.service` найдётся внутри `xfoo.service` или в строках `Wants=`/`After=` чужого юнита, и safety net даёт ложный успех. Код возврата генератора помечен в комментарии как предположение (RESEARCH A5).
**Fix:** Подкладывать в scratch-каталог уже установленные юниты из Quadlet-каталога пользователя (symlink или копия), а проверку делать по заголовку блока, например `regex_search('(?m)^---' ~ expected ~ '---$')`.

### WR-07: Проверка DNS в preflight падает необработанной ошибкой шаблона, если факты выбранного интерфейса отсутствуют

**File:** `roles/preflight/tasks/check_dns.yml:20-26, 83-95`
**Issue:** `ansible_facts[xvpn_preflight_dns_iface | replace('-', '_')]['ipv4']['address']` обращается к словарю, которого может не быть: интерфейс без IPv4 (только IPv6), имя из `xvpn_public_interface`, которого нет на хосте, либо ключ факта с `.`/`:`. Валидатор имён допускает `.` и `:`. Результат — «dict object has no attribute» и аварийное завершение, а не сообщение в агрегированном списке ошибок. Это ломает главный контракт preflight «один отчёт со всеми проблемами». Блок AAAA прикрыт `rescue`, блок A — нет.
**Fix:** Добавить явную проверку существования интерфейса и записывать ошибку в `xvpn_preflight_errors`.
```yaml
- name: Preflight dns | interface facts are missing
  ansible.builtin.set_fact:
    xvpn_preflight_errors: "{{ xvpn_preflight_errors + ['No IPv4 facts for interface ' ~ xvpn_preflight_dns_iface ~ '; set xvpn_public_ip'] }}"
  when:
    - xvpn_public_ip == ''
    - (ansible_facts[xvpn_preflight_dns_iface | replace('-', '_')]['ipv4']['address'] | default('')) == ''
```
И обернуть расчёт `xvpn_preflight_dns_ips` в этот `when`.

### WR-08: Воркфлоу `molecule-vm` ставит vagrant-libvirt и ключ HashiCorp без проверки отпечатка и запускается на каждом PR

**File:** `.github/workflows/molecule-vm.yml:49-55`
**Issue:** GPG-ключ скачивается через `curl` и сразу доверяется (`gpg --dearmor`), отпечаток не сверяется. Плагин ставится из RubyGems по версии без хеша. Остальной CI аккуратно пин-ит действия по SHA и боксы по checksum, поэтому здесь цепочка поставки слабее. Воркфлоу работает на PR из форков с правами `contents: read` и привилегированным `sudo` на runner'е.
**Fix:** Сверять отпечаток ключа (`gpg --show-keys --with-fingerprint` и сравнение с зафиксированным значением) перед `tee` в `sources.list.d`. Либо отказаться от ветки с HashiCorp и жёстко опираться на пакеты Ubuntu. Рассмотреть ограничение запуска на PR из форков (`if: github.event.pull_request.head.repo.full_name == github.repository`).

## Info

### IN-01: Повторная SSH-проверка «after» в `firewalld.yml` недостижима для падения

**File:** `roles/common/tasks/firewalld.yml:89-118`
**Issue:** **Category:** necessity. Между проверками «before» и «after» выполняется единственная задача `ansible.posix.firewalld` с `state: enabled` и циклом по портам. Она только добавляет порты и не может убрать сервис `ssh` или порт SSH из зоны (это закреплено и `defaults/main.yml:10`: «Never removes anything», и описанием argument_specs). Состояние «before ok, after fail» невозможно, пока роль add-only, поэтому четыре задачи (два `command`, `fail`) — мёртвая защита. Оценка доказана по коду репозитория.
**Fix:** Удалить блок «after» либо оставить только как одну проверку, если планируется добавить режим удаления портов.

### IN-02: Проверка конфликта портов в preflight учитывает только TCP

**File:** `roles/preflight/tasks/check_ports.yml:8-15`
**Issue:** `ss -ltn` не видит UDP-слушателей. Планируется QUIC/Hysteria на 443/udp (в `xvpn_common_firewall_ports` допускается `/udp`), и занятый 443/udp пройдёт preflight.
**Fix:** Либо документировать ограничение рядом с `xvpn_preflight_ports`, либо добавить второй вызов с `-lun` и расширить формат `xvpn_preflight_ports` до `<port>/<proto>`.

### IN-03: SSH-гейт использует `ansible_port` контроллера, а не порт sshd на целевом хосте

**File:** `roles/common/tasks/firewalld.yml:59-68`
**Issue:** `ansible_port` — порт, к которому подключается Ansible. За NAT/bastion/port-forward он не совпадает с портом sshd. Гейт либо ложно блокирует (зона разрешает 22, а подключение через 2222), либо ложно пропускает. Хост без `ssh` в зоне, но с rich-правилом для SSH, также будет отвергнут.
**Fix:** Ввести явную переменную `xvpn_common_ssh_port` (по умолчанию `ansible_port | default(22)`) и описать её в `argument_specs`.

### IN-04: Слабые проверки в `verify_rootless.yml` для sysctl

**File:** `extensions/molecule/shared/verify_rootless.yml:105-127`
**Issue:** `is search('80')` совпадёт и с `800`, `1080` и т. п. Путь к drop-in и значение `80` захардкожены и игнорируют `xvpn_podman_rootless_sysctl_file` и `xvpn_podman_rootless_unprivileged_port_start`. Проверка перестанет соответствовать роли при смене переменных.
**Fix:** Сравнивать построчно: `is match('(?m)^net\.ipv4\.ip_unprivileged_port_start\s*=\s*80\s*$')`, а путь и значение брать из переменных с теми же дефолтами.

### IN-05: `xvpn_podman_rootless_unprivileged_port_start` не ограничен

**File:** `roles/podman_rootless/meta/argument_specs.yml:34-37`, `roles/podman_rootless/tasks/main.yml:89-96`
**Issue:** Тип `int` без границ. Значение выше 80 молча ломает привязку 80/443 пользователем `rw-edge`, а значение 0 открывает все порты локальным пользователям. Ошибка проявится только на стадии Traefik.
**Fix:** Добавить `assert: 1 <= value <= 80` (или 443) в `tasks/main.yml` рядом с валидацией `home_root`.

### IN-06: Дублирование запусков CI и строгие `suboptions` спецификации

**File:** `.github/workflows/lint.yml:4-7`, `.github/workflows/molecule-container.yml:4-7`, `roles/podman_rootless/meta/argument_specs.yml:58-68`
**Issue:** (1) Триггеры `push:` без фильтра ветки и `pull_request` запускают одну и ту же работу дважды на каждый коммит PR-ветки внутри репозитория. (2) `options` элементов `xvpn_podman_rootless_quadlet_specs` описывают только `template_src` и `state`. Валидатор Ansible отвергает неописанные ключи подопций, поэтому передать дальше в LSR-роль `name`, `activate_systemd_unit` и подобное нельзя, хотя `quadlet.yml` добавляет `run_as_user` уже после валидации.
**Fix:** (1) Ограничить `push` ветками `main` либо оставить только `pull_request`. (2) Добавить необходимые поля в спецификацию заранее (до фаз 2-4) или документировать, что набор ключей закрыт.

---

_Reviewed: 2026-11-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
