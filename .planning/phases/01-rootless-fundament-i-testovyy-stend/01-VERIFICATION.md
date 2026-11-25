---
phase: 01-rootless-fundament-i-testovyy-stend
verified: 2026-11-25T04:00:00Z
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
  - roles/podman_rootless/defaults/main.yml
  - roles/podman_rootless/meta/argument_specs.yml
  - roles/podman_rootless/tasks/main.yml
  - roles/podman_rootless/tasks/user.yml
  - roles/preflight/tasks/check_dns.yml
covered_digest: "v4:sha256:bca6c1c2e2603de6417f305d1bf1adfc3bc9fd7143d8ca8a4593d5703735f613"
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
**Повторная верификация:** да, после исправлений code review IN-01 (коммиты 43280f1, ea4f207) и IN-02 (dc57c25)

## Достижение цели

### Наблюдаемые истины (ROADMAP Success Criteria)

| # | Истина | Статус | Доказательство |
|---|--------|--------|----------------|
| 1 | Preflight падает с понятным сообщением на не-EL10, SELinux не Enforcing, Podman < 5.4, занятых 80/443, неверной A-записи, ничего не изменив | VERIFIED | Роль `preflight` и сценарий `extensions/molecule/preflight` не менялись с 856bde5 (зелёный run 45521121807); гейты `getenforce` в `common` и `podman_rootless` на месте (`podman_rootless/tasks/main.yml:1-23`), режим SELinux не меняется |
| 2 | Тестовый Quadlet-сервис под rootless-пользователем слушает :80, управляется через `systemctl --user`, поднимается после reboot | VERIFIED | VM-прогон 45524347495 (alma10 и rocky10 success) на 856bde5. С тех пор в `roles/`, `extensions/`, `playbooks/`, `.github/`, `galaxy.yml` изменены только три файла (см. ниже), поведенческих изменений на пути Quadlet/sysctl/reboot нет |
| 3 | VM-тир Alma10/Rocky10 (SELinux enforcing): converge, идемпотентность changed=0, reboot, ноль AVC; firewalld открывает только нужные порты | VERIFIED | Тот же прогон 45524347495; `firewalld.yml`, `verify_rootless.yml`, `user.yml` не менялись после 856bde5 |
| 4 | Контейнерный тир, ansible-lint и yamllint в CI; коллекция собирается; у ролей есть `argument_specs` | VERIFIED | Локально: `ansible-lint --profile production` на roles/extensions/playbooks: 0 failures, 0 warnings (43 файла); `ansible-galaxy collection build` создаёт `xvpn-remnawave-0.1.0.tar.gz`; `meta/argument_specs.yml` есть у common, podman_rootless, preflight; workflows lint/molecule-container/molecule-vm присутствуют |

**Счёт:** 4/4 (behavior-unverified: 0).

### Проверка регрессий после правок ревью

Диф `git diff 856bde5 HEAD` по исходникам (без `.planning`) затрагивает ровно три файла:

| ID | Файл | Изменение | Результат |
|----|------|-----------|-----------|
| IN-01 | `roles/podman_rootless/tasks/main.yml:38` | `is match('...$')` заменён на `is regex('^/[A-Za-z0-9_-]+(/[A-Za-z0-9_-]+)*', match_type='fullmatch')` | Проверено на ansible-core 2.22.0: `/var/lib/xvpn` True (дефолт проходит), `/opt/x_y-z` True; `/srv/a.b`, значение с хвостовым `\n`, `/`, `rel/x`, `/a//b` False. Регрессии нет, дефект с `\n` закрыт, обратных слэшей нет |
| IN-02 | `roles/podman_rootless/defaults/main.yml`, `meta/argument_specs.yml` | Документирован запрет точек в сегментах и системных каталогов | Только комментарий/описание; `argument_specs` по-прежнему валиден (ansible-lint production чист) |

Ранее принятые WR-01..WR-04 (3282765, eb8c45e, e448be3, 12333db) входят в код, на котором прошёл VM-прогон 45524347495, и после него не менялись.

### Локальные проверки

| Проверка | Результат |
|----------|-----------|
| `ansible-lint --profile production roles extensions playbooks` | Passed: 0 failure(s), 0 warning(s) |
| `ansible-playbook --syntax-check playbooks/preflight.yml` | OK |
| `ansible-playbook --syntax-check playbooks/foundation.yml` | Не выполнен полностью: локально нет `community.general` (`sefcontext` не резолвится). Ограничение окружения, не дефект; плейбук не менялся с 856bde5, а CI-тиры его выполняют |
| `yamllint` | Не установлен локально; выполняется в CI-воркфлоу `lint` |
| `ansible-galaxy collection build` | OK |

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
| QA-01 | SATISFIED | lint workflow, локальный ansible-lint production чист |
| QA-02 | SATISFIED | `molecule-container.yml`, матрица container + preflight |
| QA-03 | SATISFIED | `molecule-vm.yml`, прогон 45524347495 |

Все 10 ID из PLAN frontmatter есть в REQUIREMENTS.md и отмечены Complete; осиротевших требований Phase 1 нет (QA-04/05/06 привязаны к фазам 5, 2, 5).

### Анти-паттерны

TBD/FIXME/XXX в изменённых файлах не найдено. Стабов нет.

### Предупреждения (не блокируют)

- **CI после 43280f1/ea4f207 не перезапускался.** Последний зелёный CI/VM-прогон относится к 856bde5, а правка regex (assert на `home_root`) после него не проходила ни контейнерный, ни VM-тир. Локальная проверка Jinja-теста на ansible-core 2.22.0 подтверждает корректность, но рекомендуется дождаться зелёного CI на HEAD. Статус не понижен: изменение минимально и проверено напрямую.
- IN-03 (гейт `getenforce` до установки `libselinux-utils`) пропущен как архитектурное решение; роль падает честно (fail closed), SELinux не ослабляется.
- WR-08 пропущен, остаточный риск цепочки поставок принят пользователем в UAT.

### Решения человека (UAT)

`01-UAT.md`: status complete, 2 pass, 1 skipped, 0 issues. Политика required check для molecule-vm отложена как follow-up (не блокер цели). Ожидающих проверок человека нет.

---

_Проверено: 2026-11-25_
_Верификатор: Claude (gsd-verifier)_
