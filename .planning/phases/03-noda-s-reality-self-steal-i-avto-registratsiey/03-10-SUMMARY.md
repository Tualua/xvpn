---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 10
subsystem: node-config-profile
status: complete
tags: [config-profile, reality, x25519, idempotency, selfsteal-gate, unit-tests]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: module_utils/remnawave.py, fake Panel (03-05), selfsteal harness (03-02), node-vm matrix (03-09)
provides:
  - module xvpn.remnawave.remnawave_config_profile (create, update, delete, key preservation, enforced BLOCK rule and managed Reality fields)
  - module_utils apply_panel_mutations, find_by, diff_paths
  - roles/node/templates/config-profile.json.j2 (declared profile, no keys)
  - extensions/molecule/shared/templates/test-sink-override.json.j2
affects: [03-11, 03-15, 03-16, phase-04]
actuals:
  tokens: 36000
  tasks: 2
  commits: 4
plan_head_before: 96b247166b9bd9db831291d44424a5ee68ac814a
plan_head_after: c03b7c7a8bcbb9409e49efbcd6f3a8e564cc6316
key-files:
  created:
    - plugins/modules/remnawave_config_profile.py
    - roles/node/templates/config-profile.json.j2
    - extensions/molecule/shared/templates/test-sink-override.json.j2
    - tests/unit/test_config_profile.py
  modified:
    - plugins/module_utils/remnawave.py
    - tests/unit/fake_panel.py
    - roles/node/vars/main.yml
    - scripts/selfsteal/render.yml
    - scripts/selfsteal/run.sh
key-decisions:
  - "Keys never come from the declaration: privateKey/publicKey/shortIds of managed tags are deleted from the desired config, then stored values are copied back or one x25519 batch is used (first unused keypair per new inbound)"
  - "module.params['config'] is replaced by redact(config) right after reading, so the invocation echo never carries key material from an override"
  - "IPv4-mapped ::ffff:0:0/96 is NOT in xvpn_node_blocked_cidrs: Xray 26.11.9 rejects it in routing ip"
requirements-completed: [API-01, API-03]
---

# Phase 3 Plan 10: declared Reality profile and remnawave_config_profile Summary

The selfsteal gate now builds its Xray server config from the production profile template (plus the shared test sink override) and still passes 11 cases; `remnawave_config_profile` reconciles a profile with the Panel without rotating, leaking or accepting Reality keys, covered by 23 unit tests.

## CI evidence

Final HEAD c03b7c7: lint run 46162577422 success (unit tests run inside check.sh); selfsteal run 46162577493 success, log line `selfsteal: OK (11 cases)`.
Earlier selfsteal runs 46162006914 and 46162351039 failed for the two issues listed under deviations.
Local: `bash scripts/check.sh` OK; `xray run -test` on the rendered gate profile: Configuration OK.

## Upstream contract (remnawave/backend 3.4.11)

- Routes: `GET /api/config-profiles` -> `{total, configProfiles[]}` (each with `uuid, name, config, inbounds[{uuid, profileUuid, tag, ...}], nodes`); `POST /api/config-profiles {name, config}`; `PATCH /api/config-profiles {uuid, name?, config?}`; `DELETE /api/config-profiles/{uuid}`; `GET /api/system/tools/x25519/generate` -> `{keypairs: [{publicKey, privateKey}]}`.
- x25519 returns **30 keypairs per call** (system.service.ts, generateAmount = 30); the module uses the first unused one per new inbound and calls the tool at most once per run.
- Errors: duplicate tag A113 (409, INBOUNDS_WITH_SAME_TAG_ALREADY_EXISTS), duplicate name A114 (409), reserved name `Default-Profile` A145 (400), config validation A061 (500, e.g. update without outbounds).
- Name rule `^[A-Za-z0-9_\s-]+$`, 2..30 characters (create/update command schemas).

## Pitfall 4: transformations in the create/update paths (file:line)

Paths relative to `src/`, tag 3.4.11.

| # | Where | What it changes | Counterpart |
|---|-------|-----------------|-------------|
| 1 | modules/config-profiles/config-profile.service.ts:274 -> common/helpers/xray-config/xray-config.validator.ts:161-174 (`cleanInboundClients(false)`), MANAGED_CLIENT_PROTOCOLS at :28 | update only: `settings.clients = []` on every hysteria/shadowsocks/trojan/vless inbound; does not inject flow (false) | `_mutation_clients_cleanup`, fake switch `clients_cleanup`, `test_panel_mutation_clients_cleanup` |
| 2 | xray-config.validator.ts:296-298 (`ensureSettings`, called from :166) | update only: a missing `settings` object becomes `{}` before clients is set | same function, `test_panel_mutation_clients_cleanup_creates_settings` |
| 3 | config-profile.service.ts:275 -> xray-config.validator.ts:300-315 (`fixIncorrectServerNames`) | update only, vless: `realitySettings.serverNames` split on commas, trimmed, de-duplicated | `_mutation_server_names`, fake switch `server_names`, `test_panel_mutation_server_names` |
| 4 | config-profile.service.ts:276 -> xray-config.validator.ts:335-339 (`validateOutbounds`) | update only: rejects a config without outbounds (no mutation, an error) | `_mutation_outbounds_required` raises before any write; fake switch `outbounds_required`, `test_panel_mutation_outbounds_required` |
| 5 | config-profile.service.ts:146 (create), :278 (update), :44 and :66 (reads) -> xray-config.validator.ts:83-85 (`getSortedConfig` = `sortXrayConfig`) | key reordering only (also Postgres JSONB order) | neutralised by `normalize()`; fake switch `sorted_keys`, `test_panel_mutation_sorted_keys` |
| 6 | xray-config.validator.ts:73-77, 409-421, 443-456 (`validate`, `validateTag`) | create and update: needs non-empty inbounds, unique tag, no comma in a tag; no mutation | module checks inbounds and unique tags before any request |

Note for create: items 1-4 are not applied on create (only sort), so a profile created with `clients` present stays that way until the first update. The module sends the already transformed config on create and update, so both paths store the same shape and the second run is a no-op.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] IPv4-mapped range rejected by Xray**
- **Found during:** Task 1 (selfsteal run 46162006914, `FAIL xray-server`)
- **Issue:** Xray 26.11.9: `illegal ip rule: ::ffff:0:0/96 ... CIDR prefix length 96 exceeds max 32`; the review round 1 addition makes the whole config unloadable.
- **Fix:** removed `::ffff:0:0/96` from `xvpn_node_blocked_cidrs` (reason kept in the vars comment, so the acceptance grep still finds the string); `::/128` is accepted by Xray (`xray run -test` OK). A mapped destination is folded to IPv4 by Xray and covered by the IPv4 entries. Plan 03-15 negative cases `client-private-*` should confirm on the real node.
- **Files modified:** roles/node/vars/main.yml
- **Commit:** 6b4e7a9

**2. [Rule 1 - Bug] Gate case client-private-blocked expected the freedom finalRules log**
- **Found during:** Task 1 (run 46162351039)
- **Issue:** with the production explicit BLOCK routing rule, a private destination is blackholed by routing before the freedom finalRules apply, so the old log probe (`finalrule`) no longer matched.
- **Fix:** the case now asserts no leak plus the access log line `tcp:127.0.0.1:18091 [... -> BLOCK]`, which proves the production rule.
- **Files modified:** scripts/selfsteal/run.sh
- **Commit:** c03b7c7

### Plan structure

- Task 1 (tracer) and Task 2 were committed as two commits by file group (gate/template files; module, utils, fake Panel, tests) instead of one commit per task, because the module and its 23 tests were written together.
- The sink override uses `"ip": ["127.0.0.1"]` in `finalRules` (the form the gate already proved on Xray 26.11.9) and `127.0.0.1/32` in the routing rule.

## Decisions Made

- `module.params["config"]` is replaced by its redacted copy so `invocation` carries no key even if an override contained one.
- check mode puts `<generated on apply>` into `shortIds`/`privateKey` of the diff (privateKey is shown as `<redacted>` by `redact()`).
- Read-back warning lists JSON paths only, never values.

## Known Stubs

None.

## Threat Flags

None beyond the plan threat model (T-03-18, T-03-20, T-03-37, T-03-40 mitigated and unit-tested).

## Self-Check: PASSED

Files and commits verified: 2e24d33, c39371d, 6b4e7a9, c03b7c7 on origin/main; lint and selfsteal green for c03b7c7.
