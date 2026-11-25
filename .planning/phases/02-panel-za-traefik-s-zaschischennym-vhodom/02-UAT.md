---
status: testing
phase: 02-panel-za-traefik-s-zaschischennym-vhodom
source: [02-VERIFICATION.md]
started: 2026-11-25T00:00:00Z
updated: 2026-11-25T00:00:00Z
---

## Current Test

number: 1
name: Вход через гейт в реальном браузере (секретный URL из admin-url файла, затем логин admin)
expected: |
  Секретный URL ставит cookie и ведёт на форму логина; без cookie отдаётся сайт-заглушка; логин проходит
awaiting: user response

## Tests

### 1. Вход через гейт в реальном браузере (секретный URL из admin-url файла, затем логин admin)
expected: Секретный URL ставит cookie и ведёт на форму логина; без cookie отдаётся сайт-заглушка; логин проходит
result: [pending]

### 2. Прогон playbooks/panel.yml на реальном публичном домене с xvpn_edge_acme_ca: production
expected: Выпускается сертификат production Let's Encrypt, Panel и subscription page открываются по HTTPS
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
