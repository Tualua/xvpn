---
phase: 01-rootless-fundament-i-testovyy-stend
reviewed: 2026-11-24T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - .github/workflows/lint.yml
  - extensions/molecule/shared/verify_rootless.yml
  - roles/common/defaults/main.yml
  - roles/common/meta/argument_specs.yml
  - roles/common/tasks/firewalld.yml
  - roles/common/tasks/main.yml
  - roles/podman_rootless/meta/argument_specs.yml
  - roles/podman_rootless/tasks/main.yml
  - roles/podman_rootless/tasks/quadlet_validate.yml
  - roles/podman_rootless/tasks/user.yml
  - roles/preflight/defaults/main.yml
  - roles/preflight/meta/argument_specs.yml
  - roles/preflight/tasks/check_dns.yml
findings:
  critical: 0
  warning: 4
  info: 2
  total: 6
  necessity: 0
status: issues_found
---

# Phase 1: Отчёт о code review (повторный, инкрементальный)

**Reviewed:** 2026-11-24
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Проверены исправления WR-01..WR-07 и IN-01..IN-06 (WR-08 вне области). Большинство исправлений корректно: `timeout-minutes`, перенос SELinux-гейта, `xvpn_common_ssh_port`, диапазон 1..80 для `unprivileged_port_start`, безопасное выражение набора IPv4 в `check_dns.yml`, построчная проверка sysctl в `verify_rootless.yml`, поиск заголовка `---<service>---` в `quadlet_validate.yml` (формат совпадает с выводом dry-run Podman). Критичных проблем нет. Найдены остаточные дефекты самих исправлений: валидация `home_root` всё ещё обходится, гейт SELinux в новом месте даёт вводящую в заблуждение ошибку, защита от «усыновления» аккаунта не сверяет явный `uid`, негативный контроль в verify ломается при допустимых значениях sysctl.

## Warnings

### WR-01: Валидация `xvpn_podman_rootless_home_root` обходится сегментом `.` и неполным denylist (недоработка WR-02 прошлого ревью)

**File:** `roles/podman_rootless/tasks/main.yml:28-37`
**Issue:** Regex `^/[A-Za-z0-9_-]+(/[A-Za-z0-9_.-]+)*$` допускает сегмент `.`, а проверка `'..' not in` его не ловит. Значения `/var/./lib` или `/var/lib/.` проходят и не равны ни одному элементу denylist, хотя указывают на `/var/lib`. Затем идут `file` (owner root, mode 0755), `sefcontext` с substitute `/home` и рекурсивный `restorecon -R` по системному каталогу, то есть исходный риск WR-02 остаётся. Denylist также не содержит `/var/log`, `/var/cache`, `/usr/local`, `/etc/ssh`, `/var/lib/containers` и т.п.; любой подкаталог системных каталогов проходит.
**Fix:** Перейти на allowlist и запретить сегменты `.`/`..`:
```yaml
- "xvpn_podman_rootless_home_root is match('^/(var/lib|srv|opt)/[A-Za-z0-9_-]+(/[A-Za-z0-9_-]+)*$')"
```
либо оставить denylist, но убрать `.` из допустимых символов сегмента, если точки в имени каталога не нужны (`[A-Za-z0-9_-]+`), и добавить `/var/log`, `/usr/local`, `/var/cache`.

### WR-02: SELinux-гейт теперь стоит до установки `libselinux-utils`, при отсутствии `getenforce` ошибка вводит в заблуждение

**File:** `roles/common/tasks/main.yml:21-33`, `roles/podman_rootless/tasks/main.yml:3-15`
**Issue:** После переноса гейта перед `dnf install` бинарь `getenforce` (пакет `libselinux-utils`, который роль `common` сама ставит) может ещё отсутствовать на минимальном образе. Команда с `failed_when: false` вернёт rc=2 и пустой stdout, и роль упадёт сообщением `SELinux must be Enforcing (getenforce: )`, хотя SELinux может быть в Enforcing. Роль `podman_rootless` вообще не ставит `libselinux-utils` в своих пакетах (проверить `xvpn_podman_rootless_packages`), поэтому при отдельном запуске гейт и последующий `selinuxenabled` зависят от внешнего состояния.
**Fix:** Различать «нет бинаря» и «не Enforcing» (`when: getenforce.rc != 0` отдельным `fail` с сообщением «getenforce not found; install libselinux-utils»), либо читать режим без бинаря: `slurp` `/sys/fs/selinux/enforce` (`1` = Enforcing), либо ставить `libselinux-utils` отдельной задачей перед гейтом.

### WR-03: Защита от «усыновления» аккаунта не сверяет явно заданный `uid`

**File:** `roles/podman_rootless/tasks/user.yml:17-34`
**Issue:** Для существующей учётной записи проверяются uid >= 1000, home и shell, но если в спецификации задан `uid` и он отличается от текущего, `ansible.builtin.user` выполнит `usermod -u` над живым аккаунтом (смена владельца файлов/подчинённых id, рассинхрон с linger и `/run/user/<uid>`). Это обходит заявленный смысл WR-01 (не переписывать чужой аккаунт).
**Fix:** добавить в assert условие
```yaml
- xvpn_podman_rootless_user.uid is not defined or ansible_facts['getent_passwd'][xvpn_podman_rootless_user.name][1] | int == xvpn_podman_rootless_user.uid | int
```

### WR-04: Негативный контроль «порт 79 привилегирован» ломается при допустимых значениях sysctl

**File:** `extensions/molecule/shared/verify_rootless.yml:186-213`
**Issue:** После IN-05 `xvpn_podman_rootless_unprivileged_port_start` допустим в диапазоне 1..80, а verify параметризует sysctl, но порт 79 в негативном контроле зашит. При значении <= 79 (например 70) `rw-edge` легитимно привяжет 79, и assert «bind probe is vacuous» упадёт ложно. Рассогласование появилось из-за IN-04/IN-05.
**Fix:** брать порт из значения: `xvpn_verify_sysctl_value | int - 1` (проверять только если значение > 1), и пропускать контроль при значении 1; либо ограничить в verify допустимый набор значений явным assert с понятным сообщением.

## Info

### IN-01: Ветка AAAA в `check_dns.yml` не получила того же укрепления, что A-ветка (WR-07)

**File:** `roles/preflight/tasks/check_dns.yml:105-106`
**Issue:** `ansible_facts[xvpn_preflight_dns_iface | replace('-', '_')].ipv6 | default([])` разыменовывает `.ipv6` у возможно неопределённого факта интерфейса (например, при заданном `xvpn_public_ip` и пустом интерфейсе); `default` не защищает цепочку, возникает `UndefinedError`. Rescue превратит это в предупреждение «AAAA check could not be evaluated», так что функционально безопасно, но шумно и маскирует реальные AAAA-расхождения.
**Fix:** использовать тот же приём, что для IPv4: `(ansible_facts[iface | replace('-', '_')] | default({}))['ipv6'] | default([])`.

### IN-02: В verify зашиты пользователь и домашний путь при параметризованном sysctl

**File:** `extensions/molecule/shared/verify_rootless.yml:41-57, 136`
**Issue:** `rw-edge` и `/var/lib/xvpn/rw-edge` захардкожены, тогда как sysctl теперь берётся из переменных роли; смена `xvpn_podman_rootless_home_root` ломает verify без внятной причины. Также из-за `push` без `branches` в `lint.yml` CI запускается дважды на PR из той же репозитории (принято по IN-06, фиксируется для полноты).
**Fix:** строить пути из `xvpn_podman_rootless_home_root | default('/var/lib/xvpn')` и имени пользователя из переменной.

---

_Reviewed: 2026-11-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
