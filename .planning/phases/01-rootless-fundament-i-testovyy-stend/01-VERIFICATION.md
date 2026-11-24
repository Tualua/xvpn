---
phase: 01-rootless-fundament-i-testovyy-stend
verified: 2026-11-24T12:10:00Z
status: passed
score: 4/4 must-haves verified
covered_files:
  - .github/workflows/lint.yml
  - .github/workflows/molecule-vm.yml
  - extensions/molecule/shared/verify_rootless.yml
  - galaxy.yml
  - roles/common/tasks/firewalld.yml
  - roles/common/tasks/main.yml
  - roles/podman_rootless/tasks/main.yml
  - roles/podman_rootless/tasks/user.yml
  - roles/preflight/tasks/check_dns.yml
covered_digest: "v4:sha256:16caafa760e8ebbfdfe140a80e1562b84e7474575dc5953d2d5ffd85ad149bfc"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 4/4
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 1: Rootless-фундамент и тестовый стенд. Отчёт верификации

**Цель фазы:** Оператор запускает playbook на чистом Rocky/Alma 10 и получает проверенный rootless-хост: preflight отсекает неподходящие хосты, выделенный пользователь с linger запускает тестовый Quadlet-сервис (fixture из Molecule, D-12) на порту 80, который переживает перезагрузку при SELinux enforcing без AVC; всё автоматически проверяется в Molecule и CI-линтерах.
**Проверено:** 2026-11-24
**Статус:** passed (с предупреждениями ревью, см. ниже)
**Повторная верификация:** да, после review-fix (WR-01..07, IN-01..06) и UAT

## Достижение цели

### Наблюдаемые истины (ROADMAP Success Criteria)

| # | Истина | Статус | Доказательство |
|---|--------|--------|----------------|
| 1 | Preflight падает с понятным сообщением на не-EL10, SELinux не Enforcing, Podman < 5.4, занятых 80/443, неверной A-записи, ничего не изменив | VERIFIED | `roles/preflight/tasks/{main,check_podman,check_ports,check_dns}.yml` на месте; `check_dns.yml` после WR-07 защищён rescue-блоком; сценарий `extensions/molecule/preflight` покрывает кейсы os/selinux/podman/port/dns. `molecule-container` зелёный на HEAD (45385042482) |
| 2 | Тестовый Quadlet-сервис под rootless-пользователем слушает :80, управляется через `systemctl --user`, поднимается после reboot | VERIFIED | VM-прогон 45374658629 (alma10 и rocky10 success) на коммите f63864f, содержащем все review-fix; с тех пор в roles/extensions/playbooks/.github/galaxy.yml изменений нет (`git diff f63864f HEAD` пуст) |
| 3 | VM-тир Alma10/Rocky10 (SELinux enforcing): converge, идемпотентность changed=0, reboot, ноль AVC; firewalld открывает только нужные порты | VERIFIED | Тот же прогон 45374658629 (оба job success), то есть доказательство относится к коду после правок `firewalld.yml` и `podman_rootless/tasks/main.yml`, а не только к состоянию до ревью |
| 4 | Контейнерный тир, ansible-lint и yamllint в CI; коллекция собирается; у ролей есть `argument_specs` | VERIFIED | `lint` 45385042412 и `molecule-container` 45385042482 success на HEAD-1; локально `ansible-lint --profile production`: 0 failures, 0 warnings; `ansible-galaxy collection build` создаёт `xvpn-remnawave-0.1.0.tar.gz`; `argument_specs.yml` у common, podman_rootless, preflight |

**Счёт:** 4/4.

### Требования

| Требование | Статус | Доказательство |
|------------|--------|----------------|
| FND-01 | SATISFIED | роль preflight + сценарий preflight |
| FND-02 | SATISFIED | `podman_rootless/tasks/user.yml` (защита от усыновления аккаунта, linger), VM-verify |
| FND-03 | SATISFIED | sysctl drop-in, диапазон 1..80 проверяется в роли, bind-проба в `verify_rootless.yml` |
| FND-04 | SATISFIED | `quadlet_validate.yml` + переживание reboot в VM-тире |
| FND-05 | SATISFIED | `firewalld.yml`, sefcontext, AVC=0 в VM-тире, SELinux-гейт в common и podman_rootless |
| FND-06 | SATISFIED | `galaxy.yml`, 3 `argument_specs`, сборка проходит |
| FND-07 | SATISFIED | `check_dns.yml`, флаг отключения; реальный внешний IP не проверялся (ограничение стенда) |
| QA-01 | SATISFIED | lint workflow зелёный, локальный ansible-lint production чист |
| QA-02 | SATISFIED | `molecule-container.yml`, матрица container + preflight |
| QA-03 | SATISFIED | `molecule-vm.yml`, прогон 45374658629 |

Все 10 ID из PLAN frontmatter присутствуют в REQUIREMENTS.md и отмечены Complete. Осиротевших требований Phase 1 нет (QA-04/05/06 привязаны к фазам 2 и 5).

### Анти-паттерны

TBD/FIXME/XXX в roles, extensions, playbooks, .github, scripts, galaxy.yml: не найдено. Стабов нет.

### Открытые замечания свежего ревью (01-REVIEW.md), оценка влияния на цель

Критичных нет. Все четыре предупреждения подтверждены в коде, но касаются граничных, нестандартных входных значений и не нарушают ни одну из 4 истин при значениях по умолчанию (VM-тир зелёный на этом коде). Блокерами не являются, рекомендуется закрыть до публикации коллекции.

| ID | Подтверждено в коде | Влияние |
|----|---------------------|---------|
| WR-01 | `podman_rootless/tasks/main.yml:30`: regex допускает сегмент `.`, `'..' not in` его не ловит; denylist неполный | Только при ошибочном нестандартном `home_root`; риск к системному каталогу через chown/restorecon. Предупреждение безопасности |
| WR-02 | `common/tasks/main.yml:21-33` и `podman_rootless/tasks/main.yml:3-15`: `getenforce` вызывается до установки `libselinux-utils`; при отсутствии бинаря ошибка вводит в заблуждение | Ложный отказ (fail closed), небезопасного прохождения нет; на стандартных образах EL10 `libselinux-utils` обычно уже есть |
| WR-03 | `user.yml:17-34`: явно заданный `uid` не сверяется с uid существующего аккаунта | Только для заранее существующего аккаунта с заданным `uid`; неполная защита D-08 |
| WR-04 | `verify_rootless.yml:186-213`: порт 79 зашит, ложный провал при `unprivileged_port_start` <= 79 | Только в тесте и только при нестандартном значении; роль не затронута |
| IN-01, IN-02 | ветка AAAA в `check_dns.yml`; зашитые `rw-edge` и путь в verify | Шум/гибкость, функциональность не затронута |

Диспозиция в `01-REVIEW-DISPOSITION.md`: 6 open, WR-05..07 и IN-03..06 fixed, WR-08 skipped (риск принят пользователем в UAT).

### Решения человека (UAT учтён)

`01-UAT.md` status complete: 2 pass, 1 skipped, 0 issues, pending 0.

- Бокс alma10 без sha256-пина: принято (pass).
- Судьба предупреждений ревью: принята (WR-01..07 исправлены, WR-08 принят как остаточный риск).
- Политика required check для molecule-vm: осознанно отложена как follow-up (не блокер цели; прогонов molecule-vm теперь три успешных: 45360051173, 45369636668, 45374658629).

Ожидающих проверок человека нет, поэтому статус `passed`, а не `human_needed`.

### Рекомендации (не блокируют)

1. Закрыть WR-01..WR-04 до публикации (`/gsd-code-review-fix 1`) или явно перенести в backlog; WR-01 и WR-03 касаются безопасности входных данных.
2. Вернуться к политике required check для molecule-vm.

---

_Проверено: 2026-11-24_
_Верификатор: Claude (gsd-verifier)_
