---
phase: 01-rootless-fundament-i-testovyy-stend
fixed_at: 2026-11-25T00:00:00Z
review_path: /workspaces/xvpn/.planning/phases/01-rootless-fundament-i-testovyy-stend/01-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 2
skipped: 1
status: partial
---

# Phase 1: Отчёт об исправлениях по code review

**Fixed at:** 2026-11-25
**Source review:** 01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 2
- Skipped: 1

Проверка: Tier 1 (повторное чтение diff). `ansible-lint` в окружении завис по таймауту (вероятно, из-за сетевых запросов), Python-модули `yaml`/`ansible` и `yamllint` недоступны, поэтому синтаксический чек не выполнялся. Правки выполнялись в изолированном worktree, затем fast-forward в `main`; worktree и временная ветка удалены.

## Fixed Issues

### IN-01: Регэксп `home_root` пропускает завершающий перевод строки

**Files modified:** `roles/podman_rootless/tasks/main.yml`
**Commit:** 43280f1, ea4f207
**Applied fix:** проверка переписана на `is regex('^/[A-Za-z0-9_-]+(/[A-Za-z0-9_-]+)*', match_type='fullmatch')`, так что значение с хвостовым `\n` больше не проходит валидацию. Первый вариант (`\Z` в 43280f1) заменён: обратный слэш в Jinja-литерале держится на устаревшем поведении `unicode-escape`, а проект избегает обратных слэшей в regex.

### IN-02: Ужесточение регэкспа ломает корни с точкой в имени

**Files modified:** `roles/podman_rootless/defaults/main.yml`, `roles/podman_rootless/meta/argument_specs.yml`
**Commit:** dc57c25
**Applied fix:** ограничение (сегменты только `[A-Za-z0-9_-]`, без точек, системные каталоги запрещены) добавлено в комментарий defaults и в `description` переменной `xvpn_podman_rootless_home_root` в `argument_specs.yml`. В README переменная не упоминается, поэтому он не менялся.

## Skipped Issues

### IN-03: Гейт `getenforce` стоит до установки `libselinux-utils`

**File:** `roles/common/tasks/main.yml:28-34`, `roles/podman_rootless/tasks/main.yml:10-16`
**Reason:** skipped: архитектурное решение, а не дефект. Ревьюер назвал это известным ограничением порядка задач и не регрессией. Ранняя установка пакета до гейта меняет порядок действий роли («до любых изменений хоста»), а в README нет раздела с предварительными требованиями, куда можно было бы вписать замечание. Сообщение об ошибке уже указывает установить `libselinux-utils`. Решение оставлено человеку.
**Original issue:** `libselinux-utils` ставится после проверки `getenforce`, поэтому на хосте без бинаря роль падает вместо того, чтобы поставить пакет.

---

_Fixed: 2026-11-25_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
