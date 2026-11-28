---
phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
plan: 04
subsystem: edge-decoy
status: complete
tags: [decoy, self-steal, templates, gate, molecule]
requires:
  - phase: 03-noda-s-reality-self-steal-i-avto-registratsiey
    provides: decoy.yml with rendezvous selection, studio template, self-steal gate (plans 03-02, 03-03)
provides:
  - selfsteal gate cases decoy-template and decoy-404 (verdict "selfsteal: OK (11 cases)")
  - bundled decoy templates blog, business, maintenance (with studio: four, pairwise distinct stylesheets)
  - final xvpn_edge_decoy_templates list and argument_specs choices
  - node verify cases for order independence, every template, explicit choice, operator directory, brand escape, unknown template
affects: [03-05]
actuals:
  tokens: 45000
  tasks: 2
  commits: 2
plan_head_before: d92dab887307f47b3e052a9cb0e971bb02969a45
plan_head_after: ae4a85727d530d799c31e2cd3d545ff0731aa7d1
tech-stack:
  added: []
  patterns: [gate renders through the production decoy.yml, shared task helpers for node verify variants]
key-files:
  created:
    - roles/edge/files/decoy-templates/blog/
    - roles/edge/files/decoy-templates/business/
    - roles/edge/files/decoy-templates/maintenance/
    - extensions/molecule/shared/node_decoy_variant.yml
    - extensions/molecule/shared/node_decoy_each.yml
  modified:
    - scripts/selfsteal/render.yml
    - scripts/selfsteal/run.sh
    - .github/workflows/selfsteal.yml
    - roles/edge/vars/main.yml
    - roles/edge/meta/argument_specs.yml
    - roles/edge/tasks/decoy.yml
    - extensions/molecule/node/verify.yml
key-decisions:
  - "The gate installs the site by including the production roles/edge/tasks/decoy.yml, so the scanner sees exactly what a node serves"
  - "Node verify helpers live in extensions/molecule/shared (matched by the ansible-lint tasks kind), not in the scenario directory"
requirements-completed: [STEAL-02, STEAL-04]
---

# Phase 3 Plan 04: Decoy gate and remaining templates Summary

The selfsteal gate now proves through Reality that a scanner gets the node's own rendered site and its own 404, and the edge role ships four distinct bundled templates (blog, business, maintenance, studio) with node verify cases for selection, operator directory and brand escaping.

## What was done

**Task 1 (tracer), commit 123a75c.** `scripts/selfsteal/render.yml` includes the production `roles/edge/tasks/decoy.yml` (home under the work dir, `xvpn_edge_decoy_select_key: node.test`, strict true) instead of copying the neutral page. `run.sh` mounts `edge-home/decoy/site` into the decoy container and adds `decoy-template` (200, body byte-equal to the rendered index.html) and `decoy-404` (404, body byte-equal to the rendered 404.html, neither "404 page not found" nor "nginx"). The workflow links the collection and installs dependencies before the gate (filetree needs community.general).

**Task 2, commit ae4a857.** Three new templates, each with its own layout, wording, colour scheme, class names and a distinct generated favicon: blog (journal with sidebar, 2 posts), business (landing, services table, contact), maintenance (dark single box, 2 pages). `xvpn_edge_decoy_templates` is `[blog, business, maintenance, studio]` (order irrelevant), argument_specs choices extended. Node verify gained: reversed list selects the same template; a loop proves all four templates (index, 404, strict conf, own stylesheet, four distinct checksums); explicit `blog` wins over the hash pick (`maintenance` for node.xvpn.test); operator directory leaves exactly the two operator files and switching back restores the template; brand `<b>Acme</b>` is escaped; unknown template is rejected (negative case `decoy-template-unknown`, 10 markers). The scenario ends with the default selection restored.

## CI results (pushed to origin/main)

| Commit | lint | selfsteal | molecule-container |
|--------|------|-----------|--------------------|
| 123a75c | success, run 46140047690 | success, run 46140047662, "selfsteal: OK (11 cases)" with ok decoy-template and ok decoy-404 | not required for this commit |
| ae4a857 | success, run 46140762000 | success, run 46140761977, "selfsteal: OK (11 cases)" | success, run 46140761992 (container, node, preflight legs all success) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale selection reported as template for an operator directory**
- **Found during:** Task 2 (operator directory case)
- **Issue:** `xvpn_edge_decoy_source_kind` used the `xvpn_edge_decoy_selected_template` fact left over from an earlier role run, so the debug label said "template" although the operator directory was used (selection itself was correct).
- **Fix:** the label considers the selected template only when no operator directory is set.
- **Files modified:** roles/edge/tasks/decoy.yml
- **Commit:** ae4a857

**2. [Rule 3 - Blocking] Existing node verify asserted studio-only files**
- **Found during:** Task 2
- **Issue:** the install check listed work.html and contact.html, which maintenance (hash pick for node.xvpn.test) does not have.
- **Fix:** the list is now the files common to all templates (style.css, 404.html, index.html, favicon.ico, robots.txt).
- **Files modified:** extensions/molecule/node/verify.yml
- **Commit:** ae4a857

**3. [Rule 3 - Blocking] Helper task files in the scenario directory failed ansible-lint**
- **Issue:** lint treated them as plays. They live in extensions/molecule/shared (matched by the lint `tasks` kind) as node_decoy_variant.yml and node_decoy_each.yml; not listed in the plan's files.
- **Commit:** ae4a857

**4. Plan acceptance inconsistency (documented, not changed):** `grep -rli xvpn roles/edge/files/decoy-templates` == 0 cannot hold, because every template (including studio from 03-03) references the variable `xvpn_edge_decoy_brand_resolved`. The only matches are that variable name (37 hits); rendered output contains no "xvpn" (the node verify asserts this for index.html and 404.html). The other grep guards hold: no http(s):// (0 files), four 404.html.j2, four favicons, four distinct style.css hashes.

**5. Explicit-choice case uses `blog`** instead of `maintenance`, because maintenance is the hash pick for node.xvpn.test and would not prove that the choice beats the hash.

## Known Stubs

None.

## Threat Flags

None. Mitigations T-03-07 (four distinct templates, no marker), T-03-09 (brand escape executed) and T-03-32 (operator directory file set asserted exactly) are covered by the verify cases above.

## Notes

- `state update-progress` skips because STATE.md milestone is "v3.7.20" with no ROADMAP milestone headings (known pre-existing issue, not touched).
- Residual accepted by the plan: subtle cross-template fingerprinting is checked structurally only; a human look at a rendered template is deferred to end of phase.

## Self-Check: PASSED
