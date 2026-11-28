---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 03
subsystem: edge-decoy
tags: [decoy, nginx, self-steal, rendezvous, templates]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: edge role, node playbook, self-steal gate (plans 03-01, 03-02)
provides:
  - roles/edge/tasks/decoy.yml (selection chain, file-by-file install, prune)
  - bundled decoy template "studio" (index, work, contact, own 404, css, favicon, robots)
  - nginx strict-404 mode for nodes (xvpn_edge_decoy_strict)
affects: [03-04]
actuals:
  tokens: 30000
  tasks: 2
  commits: 3
plan_head_before: 69e32109b4c0876ba35a7fbc0a70cf8ff8463a61
plan_head_after: 1bf50b58b856535f3aaa5113d2e96eff752a6cfe
tech-stack:
  added: []
  patterns: [rendezvous (highest sha256 of key:name) template selection, single desired-set for install and prune]
key-files:
  created:
    - roles/edge/tasks/decoy.yml
    - roles/edge/files/decoy-templates/studio/
  modified:
    - roles/edge/tasks/main.yml
    - roles/edge/templates/decoy-nginx.conf.j2
    - roles/edge/defaults/main.yml
    - roles/edge/vars/main.yml
    - roles/edge/meta/argument_specs.yml
    - playbooks/node.yml
    - scripts/selfsteal/render.yml
    - extensions/molecule/node/verify.yml
    - extensions/molecule/container/verify.yml
key-decisions:
  - "Template choice by rendezvous rule over xvpn_edge_decoy_select_key; list order irrelevant, adding a template moves only nodes it wins"
  - "Panel keeps roles/edge/files/decoy/index.html (sha256 23058096...) and the catch-all; asserted in container verify"
requirements-completed: [STEAL-02, STEAL-04]
status: complete
---

# Phase 3 Plan 03: Decoy templates and strict 404 Summary

A node now serves the multi-page "studio" site with its own 404 page, picked deterministically from the node domain by a rendezvous rule, while Panels keep their neutral page byte for byte.

## Results

- Task 1 (tracer, 3a16920): decoy.yml, studio template, strict nginx mode, node playbook wiring, node verify with an independent python3 computation of the expected template. CI: lint 46137147130 success, molecule-container 46137147075 success (container, preflight, node), selfsteal 46137147094 failure (see deviation 1).
- Fix (selfsteal render): commit between tasks.
- Task 2 (test commit): Panel no-drift assertions (only index.html, pinned sha256, catch-all, no error_page) and stray file/directory prune in node verify. Final HEAD 1bf50b5: lint 46138447823, molecule-container 46138447897 (container, node, preflight all success, includes the idempotence leg), selfsteal 46138447856 all success.
- Local check: `bash scripts/check.sh` OK. decoy.yml also run locally: second run changed=0, strays pruned, Panel path leaves only index.html with the pinned sha256.
- favicon generator: Python `struct` script writing a 16x16 32-bit ICO (1150 bytes: ICONDIR + entry + BITMAPINFOHEADER 40 + 16x16 BGRA pixels + 64-byte AND mask), committed as a binary.

## Deviations from Plan

**1. [Rule 3 - Blocking] selfsteal gate rendered the nginx template without role defaults**
- Found during: Task 1 CI (selfsteal run 46137147094: `'xvpn_edge_decoy_strict' is undefined`)
- Fix: scripts/selfsteal/render.yml sets `xvpn_edge_decoy_strict: false` (gate keeps the catch-all; Plan 03-04 adds the strict cases)
- Verification: selfsteal run 46138447856 success

**2. [Plan conflict] "no xvpn string in studio sources" vs "404.html.j2 contains xvpn_edge_decoy_brand_resolved"**
- The two acceptance greps cannot both hold on the sources, because the variable name contains the substring. The intent (no marker in what is served) is enforced on the rendered pages: node verify asserts `xvpn` is absent from rendered index.html and 404.html, and the source check passes once the variable name is excluded (0 hits).

Total deviations: 2 (1 auto-fixed blocker, 1 plan-internal conflict resolved by checking rendered output).

## Known Stubs

None.

## Self-Check: PASSED

Files exist (decoy.yml, studio template, verify files); commits 3a16920 and 1bf50b5 are on origin/main; CI for HEAD green.
