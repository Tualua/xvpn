---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 08
subsystem: node-role
status: complete
tags: [cert-gate, firewalld, rich-rule, steal-05, node-02, molecule-node-vm]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: remnanode and SECRET_KEY (03-07), two-VM stand (03-06), loopback cert on 127.0.0.1:8443 (03-02/03-04)
provides:
  - roles/node/tasks/gate.yml (openssl s_client probe of the loopback entrypoint, STEAL-05)
  - roles/node/tasks/firewall.yml (443/tcp after the gate, Panel-only IPv4 rich rule for 2222)
  - variables xvpn_node_panel_sources, xvpn_node_cert_gate_retries, xvpn_node_cert_gate_delay, xvpn_node_cert_gate_ca_file
  - verify_common.yml input xvpn_verify_expected_rich_rules (exact set)
affects: [03-09, 03-11, 03-16]
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: 056d63198e60552b390f5948391d283158ec4d33
plan_head_after: 9c0e9ad30bf922a8b07ce86917c2da191e702977
key-files:
  created:
    - roles/node/tasks/gate.yml
    - roles/node/tasks/firewall.yml
  modified:
    - roles/node/defaults/main.yml
    - roles/node/meta/argument_specs.yml
    - roles/node/tasks/main.yml
    - roles/node/tasks/present.yml
    - extensions/molecule/shared/verify_common.yml
    - extensions/molecule/shared/verify_node.yml
    - extensions/molecule/node/converge.yml
    - extensions/molecule/node/verify.yml
    - extensions/molecule/node-vm/vars/node-vm.yml
key-decisions:
  - "443/tcp opens only after the loopback certificate probe; activate false with register true is rejected for state present"
  - "Panel sources: explicit variable, then inventory xvpn_public_ip (guarded with default), then delegated network facts of the Panel host; IPv4/CIDR regex before the rule is rendered"
requirements-completed: [NODE-02, STEAL-05]
---

# Phase 3 Plan 08: Certificate gate and Panel-only node API Summary

443/tcp на ноде открывается только после проверки сертификата домена ноды на loopback (openssl s_client с SNI и verify_hostname), а порт 2222 отвечает только адресам Панели через одно IPv4 rich rule на источник.

## Что сделано

- `gate.yml`: probe `127.0.0.1:8443`, повтор 60 x 5 с, цепочка проверяется для production CA или при заданном `xvpn_node_cert_gate_ca_file` (Pebble в CI), для остальных CA проверяется только домен в subject. Сообщение об ошибке называет ACME staging/rate limits, DNS и порт 80.
- `firewall.yml`: 443/tcp за `xvpn_node_gate_passed`, rich rule для каждого Panel source, 8443 нигде не открывается.
- `main.yml`: assert `activate false` + `register true` (первым в блоке валидации), разрешение Panel sources с проверкой регулярным выражением и подсказкой про NAT.
- Verify: точное множество rich rules, 13 негативных кейсов в контейнерном verify (добавлены `node-activate-register-mismatch`, `panel-source-injection`, `panel-source-missing`), на VM порт 2222 доступен с Panel VM и недоступен с контроллера (`api-port-from-controller`), 443 закрыт в контейнерном уровне.

## CI

- lint: 46153520942 success
- gate / selfsteal: success
- molecule-container: 46153520887 success (leg node: ports ровно 80/tcp, одно rich rule)
- molecule-node-vm (dispatch на HEAD 9c0e9ad): 46155071561 success

## Deviations from Plan

**1. [Rule 3 - Blocking] delegate_to с пустым Panel host**
- **Found during:** Task 2, первый прогон molecule-container (run 46152083586, leg node)
- **Issue:** `delegate_to: "{{ xvpn_node_panel_host }}"` в пропущенной задаче `setup` ломало шаблонизацию при пустом Panel host (контейнерный уровень).
- **Fix:** `xvpn_node_panel_host | default(omit, true)`, как в secret.yml.
- **Commit:** 9c0e9ad

**2. [Rule 3 - Blocking] Зона firewalld в verify-прогоне**
- Позитивный кейс `node-name-space` запускает роль целиком, а факт `xvpn_common_fw_zone` в отдельном verify-прогоне отсутствует. Перед кейсом подключается `common` `tasks_from: firewalld` (offline, портов нет, add-only), кейсу передан `xvpn_common_firewalld_offline: true`; verify play получил `xvpn_node_panel_sources`.

**3. Организация коммитов:** задачи 1 и 2 зафиксированы одним коммитом (8658fcc), поскольку правки пересекаются в одних файлах (verify, main.yml, defaults); промежуточный счётчик 11 маркеров не фиксировался отдельно.

## Known Stubs

None.

## Threat Flags

None beyond the plan threat model.

## Self-Check: PASSED

Файлы gate.yml и firewall.yml существуют; коммиты 8658fcc и 9c0e9ad в истории main.
