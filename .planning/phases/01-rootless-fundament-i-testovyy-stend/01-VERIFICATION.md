---
phase: 01-rootless-fundament-i-testovyy-stend
verified: 2026-11-25T02:00:00Z
status: passed
score: 4/4 must-haves verified
covered_files:
  - .github/workflows/lint.yml
  - .github/workflows/molecule-vm.yml
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-01-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-01-SUMMARY.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-02-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-02-SUMMARY.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-03-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-03-SUMMARY.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-04-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-04-SUMMARY.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-05-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-05-SUMMARY.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-06-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-06-SUMMARY.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-07-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-07-SUMMARY.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-08-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-08-SUMMARY.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-09-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-09-SUMMARY.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-10-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-10-SUMMARY.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-11-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-11-SUMMARY.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-12-PLAN.md
  - .planning/phases/01-rootless-fundament-i-testovyy-stend/01-12-SUMMARY.md
  - extensions/molecule/shared/verify_rootless.yml
  - galaxy.yml
  - roles/common/tasks/firewalld.yml
  - roles/common/tasks/main.yml
  - roles/podman_rootless/tasks/main.yml
  - roles/podman_rootless/tasks/user.yml
  - roles/preflight/tasks/check_dns.yml
covered_digest: "v4:sha256:85451520afe88b5118052d95f8fbd705abcfe9646ed357d419a11b3e339e6d91"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 4/4
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 1: Rootless-фундамент и тестовый стенд. Отчёт верификации

**Цель фазы:** Оператор запускает playbook на чистом Rocky/Alma 10 и получает проверенный rootless-хост: preflight отсекает неподходящие хосты, выделенный пользователь с linger запускает тестовый Quadlet-сервис (fixture из Molecule, D-12) на порту 80, который переживает перезагрузку при SELinux enforcing без AVC; всё автоматически проверяется в Molecule и CI-линтерах.
**Проверено:** 2026-11-25
**Статус:** passed
**Повторная верификация:** да, после исправлений WR-01..WR-04 из повторного ревью (изменены `verify_rootless.yml`, `common/tasks/main.yml`, `podman_rootless/tasks/main.yml`, `podman_rootless/tasks/user.yml`)

## Достижение цели

### Наблюдаемые истины (ROADMAP Success Criteria)

| # | Истина | Статус | Доказательство |
|---|--------|--------|----------------|
| 1 | Preflight падает с понятным сообщением на не-EL10, SELinux не Enforcing, Podman < 5.4, занятых 80/443, неверной A-записи, ничего не изменив | VERIFIED | Роль `preflight` (`main`, `check_podman`, `check_ports`, `check_dns`) и сценарий `extensions/molecule/preflight`; `container (preflight)` зелёный в run 45521121807 на 856bde5. Новый гейт `getenforce rc != 0` в `common` и `podman_rootless` падает с понятным сообщением и не меняет режим SELinux |
| 2 | Тестовый Quadlet-сервис под rootless-пользователем слушает :80, управляется через `systemctl --user`, поднимается после reboot | VERIFIED | VM-прогон 45524347495 (alma10 и rocky10 success) на 856bde5, который содержит все исправления WR-01..WR-04; `git diff 12333db HEAD` по roles/extensions/playbooks/.github/galaxy.yml пуст |
| 3 | VM-тир Alma10/Rocky10 (SELinux enforcing): converge, идемпотентность changed=0, reboot, ноль AVC; firewalld открывает только нужные порты | VERIFIED | Тот же прогон 45524347495, оба job success, уже на коде после правок ревью (в том числе `verify_rootless.yml` с вычисляемым негативным портом) |
| 4 | Контейнерный тир, ansible-lint и yamllint в CI; коллекция собирается; у ролей есть `argument_specs` | VERIFIED | `lint` 45521121714 и `molecule-container` 45521121807 success на 856bde5; локально `ansible-lint --profile production`: 0 failures, 0 warnings; `ansible-galaxy collection build` создаёт `xvpn-remnawave-0.1.0.tar.gz`; `meta/argument_specs.yml` есть у common, podman_rootless, preflight |

**Счёт:** 4/4 (behavior-unverified: 0).

### Проверка исправлений ревью (регрессии)

| ID | Что изменено | Результат |
|----|--------------|-----------|
| WR-01 | Регэксп `home_root` без точек в сегментах, расширенный denylist (`podman_rootless/tasks/main.yml`) | Реализовано, дефолт `/var/lib/xvpn` проходит; VM зелёный |
| WR-02 | Отдельный `fail` при `getenforce rc != 0` в обеих ролях | Реализовано; режим SELinux не меняется |
| WR-03 | `user.yml`: явный `uid` сверяется с uid существующего аккаунта | Реализовано; защита D-08 дополнена |
| WR-04 | Негативный bind-порт = `sysctl - 1`, проба пропускается при пороге <= 1 | Реализовано; VM зелёный |

### Требования

| Требование | Статус | Доказательство |
|------------|--------|----------------|
| FND-01 | SATISFIED | роль preflight + сценарий preflight |
| FND-02 | SATISFIED | `podman_rootless/tasks/user.yml` (защита от усыновления аккаунта, сверка uid, linger), VM-verify |
| FND-03 | SATISFIED | sysctl drop-in, bind-проба на :80 и негативная проба в `verify_rootless.yml` |
| FND-04 | SATISFIED | `quadlet_validate.yml`, переживание reboot в VM-тире |
| FND-05 | SATISFIED | `firewalld.yml`, sefcontext, AVC=0 в VM-тире, SELinux-гейт в common и podman_rootless |
| FND-06 | SATISFIED | `galaxy.yml` (`xvpn.remnawave`), 3 `argument_specs`, сборка проходит |
| FND-07 | SATISFIED | `check_dns.yml`, флаг отключения; реальный внешний IP не проверялся (ограничение стенда) |
| QA-01 | SATISFIED | lint workflow зелёный, локальный ansible-lint production чист |
| QA-02 | SATISFIED | `molecule-container.yml`, матрица container + preflight |
| QA-03 | SATISFIED | `molecule-vm.yml`, прогон 45524347495 |

Все 10 ID из PLAN frontmatter есть в REQUIREMENTS.md и отмечены Complete; осиротевших требований Phase 1 нет (QA-04/05/06 привязаны к фазам 5, 2, 5).

### Анти-паттерны

TBD/FIXME/XXX в roles, extensions, playbooks, .github, scripts, galaxy.yml не найдено. Стабов нет.

### Открытые замечания ревью (информационные, не блокируют)

- IN-01: `$` в регэкспе `home_root` пропускает завершающий `\n`; рекомендуется `\Z`.
- IN-02: запрет точки в сегментах `home_root` не задокументирован в описании переменной/README.
- IN-03: гейт `getenforce` стоит до установки `libselinux-utils`; при отсутствии бинаря роль честно падает (fail closed).

WR-08 пропущен, остаточный риск цепочки поставок принят пользователем в UAT.

### Решения человека (UAT)

`01-UAT.md`: status complete, 2 pass, 1 skipped, 0 issues. Политика required check для molecule-vm отложена как follow-up (не блокер цели). Ожидающих проверок человека нет.

---

_Проверено: 2026-11-25_
_Верификатор: Claude (gsd-verifier)_
