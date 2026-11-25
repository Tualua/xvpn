---
phase: 01-rootless-fundament-i-testovyy-stend
reviewed: 2026-11-25T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - extensions/molecule/shared/verify_rootless.yml
  - roles/common/tasks/main.yml
  - roles/podman_rootless/tasks/main.yml
  - roles/podman_rootless/tasks/user.yml
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
  necessity: 0
status: issues_found
---

# Phase 1: Отчёт о code review (повторная проверка исправлений WR-01..WR-04)

**Reviewed:** 2026-11-25
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Проверен diff от `36b24f5` до HEAD по четырём файлам. Все четыре исправления (WR-01..WR-04 прошлого ревью) реализованы корректно, новых багов уровня Warning/Critical не найдено.

- WR-01 (home_root): регэксп сегментов `[A-Za-z0-9_-]+` полностью запрещает точки, поэтому проверка `'..'` действительно стала избыточной. Расширенный denylist покрывает типовые системные каталоги. Дефолт `/var/lib/xvpn` проходит валидацию.
- WR-02 (getenforce): отдельный `fail` при `rc != 0` различает «бинарь недоступен» и «режим не Enforcing». Приоритет операторов в `rc | default(0) != 0` верный (фильтр привязан сильнее сравнения). Режим SELinux по-прежнему не меняется.
- WR-03 (uid): условие `uid is not defined or ... == uid | int` корректно. Assert выполняется только при существующем аккаунте (`when ... is not none`), поэтому обращение к `getent_passwd[...]` безопасно. Многострочный plain-scalar с `or` валиден в YAML.
- WR-04 (негативный пробный порт): порт `sysctl - 1` вычисляется корректно, при значении `<= 1` проба и assert пропускаются; `xvpn_verify_sysctl_value` определён выше по файлу (строка 103) со значением по умолчанию 80. Проверка прав на привилегированный порт в ядре идёт раньше проверки занятости адреса, поэтому `EADDRINUSE` не подменит ожидаемый `rc == 13`.

Остались мелкие замечания информационного уровня.

## Info

### IN-01: Регэксп `home_root` пропускает завершающий перевод строки

**File:** `roles/podman_rootless/tasks/main.yml:38`
**Issue:** Тест `match` использует `re.match`, а `$` в Python совпадает и перед завершающим `\n`. Значение вида `"/var/lib/xvpn\n"` (например, из YAML block scalar `|`) пройдёт валидацию и попадёт в `home:` модуля `user` и в сравнение с `getent` в `user.yml`.
**Fix:** заменить `$` на `\Z`: `is match('^/[A-Za-z0-9_-]+(/[A-Za-z0-9_-]+)*\Z')`.

### IN-02: Ужесточение регэкспа ломает корни с точкой в имени

**File:** `roles/podman_rootless/tasks/main.yml:38`
**Issue:** Раньше допускались сегменты вида `/srv/xvpn.d`; теперь точка запрещена целиком. Это осознанный выбор, но поведение изменилось и не отражено в документации переменной.
**Fix:** упомянуть ограничение (`[A-Za-z0-9_-]` в каждом сегменте) в комментарии к `xvpn_podman_rootless_home_root` в `roles/podman_rootless/defaults/main.yml` и в README.

### IN-03: Гейт `getenforce` стоит до установки `libselinux-utils`

**File:** `roles/common/tasks/main.yml:28-34`, `roles/podman_rootless/tasks/main.yml:10-16`
**Issue:** `libselinux-utils` входит в `xvpn_common_packages` и в пакеты `podman_rootless`, но устанавливается после гейта. На хосте без `getenforce` роль завершится ошибкой и попросит поставить пакет вручную, хотя могла бы поставить его сама. Это не регрессия (раньше падала проверка Enforcing с менее понятным сообщением), а известное ограничение порядка задач.
**Fix:** при желании установить `libselinux-utils` отдельной ранней задачей `dnf` до чтения режима (изменение режима SELinux при этом не происходит), либо зафиксировать в README, что пакет должен быть на хосте заранее.

---

_Reviewed: 2026-11-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
