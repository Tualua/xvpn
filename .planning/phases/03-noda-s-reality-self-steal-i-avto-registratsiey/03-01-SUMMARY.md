---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 01
subsystem: infra
tags: [ansible, traefik, reality, self-steal, molecule, node]
requires:
  - phase: 02-panel-za-traefik-s-zaschischennym-vhodom
    provides: edge role with route.yml drop-in interface and the xvpn-decoy / xvpn-to-https / le contract
provides:
  - role xvpn.remnawave.node skeleton (inputs, validation, self-steal route)
  - playbooks/node.yml with websecure pinned to 127.0.0.1:8443
  - Molecule container scenario node with nine negative cases and one positive case
affects: [03-02, 03-03, 03-04, 03-08, 03-16]
actuals:
  tokens: 7850
  tasks: 2
  commits: 2
plan_head_before: 3322daf24f8116df9062e1ba2bbec5858db86b60
plan_head_after: 2d2c92bab6c4521a6785222311e9e0ff2bbed12c
tech-stack:
  added: []
  patterns: [edge route drop-in reuse without a fork, lazily templated defaults over vars/main.yml sanitizers]
key-files:
  created:
    - roles/node/defaults/main.yml
    - roles/node/vars/main.yml
    - roles/node/meta/main.yml
    - roles/node/meta/argument_specs.yml
    - roles/node/tasks/main.yml
    - roles/node/tasks/present.yml
    - roles/node/templates/node-selfsteal.yml.j2
    - playbooks/node.yml
    - extensions/molecule/node/molecule.yml
    - extensions/molecule/node/prepare.yml
    - extensions/molecule/node/converge.yml
    - extensions/molecule/node/verify.yml
  modified:
    - .github/workflows/molecule-container.yml
    - scripts/check.sh
key-decisions:
  - "Edge is reused as is: node differences are xvpn_edge_https_address 127.0.0.1:8443 in play vars and one drop-in route"
  - "Default inbound tag uses a separate sanitizer (xvpn_node_tag_sanitized) that also replaces spaces"
status: complete
---

# Phase 3 Plan 01: Node role skeleton Summary

Роль `node` с валидацией входов и self-steal маршрутом поверх неизменённого edge, плейбук `playbooks/node.yml` с websecure на 127.0.0.1:8443 и Molecule-сценарий `node` (container tier).

## Что сделано

- Task 1 (tracer, b865b65): роль `node` (defaults, vars, meta, argument_specs, tasks, шаблон `node-selfsteal.yml.j2`), `playbooks/node.yml`, сценарий `extensions/molecule/node`, матрица `molecule-container` расширена на `node`, regex QA-05 в `scripts/check.sh` учитывает `playbooks/node.yml`. Firewalld получает только 80/tcp.
- Task 2 (2d2c92b): девять негативных кейсов (`# xvpn_negative_case:`) и позитивный кейс `node-name-space` в `verify.yml`; итоговый assert сравнивает список отклонённых id с `xvpn_negative_expected`; каталог dynamic проверяется по контрольным суммам до и после.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `bash scripts/check.sh` -> `check.sh: OK`, `check_acme_ca: OK` (локально; yamllint и gitleaks не установлены локально, их проверяет CI).
- Предусловие (маркеры spike в 03-RESEARCH.md) выполнено: все шесть счётчиков >= 1.
- Регулярные выражения домена, образа и дефолтного тега проверены отдельным запуском ansible (`node one` -> `node-one`).
- Не выполнено: запуск `molecule test -s node` и CI (`lint`, `molecule-container`) для HEAD. В окружении нет molecule/podman, а push не выполнялся. Нужно запушить и дождаться `scripts/ci_watch.sh lint molecule-container`; пока идемпотентность (changed=0) и негативные кейсы подтверждены только синтаксисом и линтом.

## Known Stubs

None. Ветка `xvpn_node_state: absent` намеренно падает с сообщением "decommission is not implemented yet" (реализация в Plan 03-16).

## Threat Flags

None.

## Self-Check: PASSED

- Файлы roles/node/**, playbooks/node.yml, extensions/molecule/node/* существуют.
- Коммиты b865b65 и 2d2c92b присутствуют в истории.
