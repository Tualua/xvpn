# Phase 2: Panel за Traefik с защищённым входом - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-25
**Phase:** 02-panel-za-traefik-s-zaschischennym-vhodom
**Areas discussed:** Админ-гейт, Секреты и креды админа, Домены/ACME/CI, Раскладка ролей/playbook

---

## Админ-гейт

| Вопрос | Варианты | Выбрано |
|--------|----------|---------|
| Точка входа | Секретный путь / Query-параметр / Выбирает оператор | Секретный путь |
| Ответ без cookie | Голый 404 Traefik / Нейтральная заглушка | Нейтральная заглушка |
| Статус заглушки | 200 + статичный сайт / Страница 404 / Выбирает оператор | 200 + статичный сайт |
| Пути без cookie | /api/* открыт, /api/auth/* закрыт / Закрыто всё / /api/* открыт целиком | /api/* открыт, /api/auth/* закрыт |
| Срок жизни cookie | Переменная, 30 дней / Сессионная / На усмотрение Claude | Переменная, 30 дней |
| Fallback при провале спайка | Set-Cookie отдаёт decoy-nginx / Только эскалация / Traefik-плагин | decoy-nginx |
| Источник секрета | Generate-once, переопределяется / Обязательно из vault | Generate-once |

**Notes:** заглушка вместо 404 означает, что PANEL-06 и критерий успеха 2 нужно переформулировать.

## Секреты и креды админа

| Вопрос | Варианты | Выбрано |
|--------|----------|---------|
| Хранилище секретов | Panel-хост 0600 / Контроллер (lookup password) / Только vault | Panel-хост 0600 |
| Креды админа | Логин из переменной + пароль generate-once / Оба из vault | Логин из переменной + generate-once |
| Доступ к токену в фазе 3 | Чтение с Panel-хоста во время прогона / Плюс экспорт на контроллер | Чтение во время прогона |
| Изменение применённого секрета | Fail / Применить (ротация) / На усмотрение Claude | Fail (секрет гейта — исключение) |

## Домены, ACME и CI

| Вопрос | Варианты | Выбрано |
|--------|----------|---------|
| Домены | Два FQDN / Базовый домен + префиксы | Два FQDN |
| ACME по умолчанию | Production, email необязателен / Staging / Production, email обязателен | Production, email необязателен |
| Где e2e с Pebble | VM-тир / Оба тира | VM-тир |
| Неизвестный SNI | Сброс TLS (sniStrict) / Отдать заглушку | sniStrict |

## Раскладка ролей/playbook

| Вопрос | Варианты | Выбрано |
|--------|----------|---------|
| Traefik | Отдельная роль `edge` / Внутри `panel` | Отдельная роль `edge` |
| Subscription page | Часть `panel` / Отдельная роль | Часть `panel` |
| Playbook | `panel.yml` + `site.yml` / Только `site.yml` | `panel.yml` + `site.yml` |

## Claude's Discretion

- `Network=host` или pasta для Traefik (разночтение CLAUDE.md и EDGE-01)
- Podman `Secret=` или env-файл; формат файла секретов
- Контент заглушки, имена переменных, маскирование секретного пути в логе

## Deferred Ideas

- Бэкап файла секретов — фаза 5
- Ротация секретов — вне v1
- Sub-page на отдельном хосте — вне v1
