---
phase: 02
review: 02-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "`paths-ignore` skips the secret scan and the gate on planning-only and Markdown-only changes"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "preflight `argument_specs` default contradicts `defaults/main.yml`"
  - id: IN-01
    severity: info
    disposition: open
    title: "`check_until_set_fact.py` scans only `roles/*/tasks/*.yml`"
  - id: IN-02
    severity: info
    disposition: open
    title: "the ACME CA-switch test hard-codes the derived store hashes"
  - id: IN-03
    severity: info
    disposition: deferred
    title: "old ACME stores are kept forever and the legacy `acme.json` is orphaned"
  - id: IN-04
    severity: info
    disposition: open
    title: "`xvpn_panel_failure_log_dir` was removed without a deprecation notice"
---

# Phase 02 — code review disposition (incremental review, diff base 75d71a4)

Previous ledger (full phase review) is in git history before this commit; all its findings were fixed or skipped.

| id | severity | disposition | source |
|----|----------|-------------|--------|
| WR-01 | warning | fixed | gate (gitleaks) runs on every push and PR; lint and Molecule keep the skip (user decision) |
| WR-02 | warning | fixed | a7d502a |
| IN-01 | info | open | |
| IN-02 | info | open | |
| IN-03 | info | deferred | documented in README (CA switch section); cleanup is an operator action |
| IN-04 | info | open | |
