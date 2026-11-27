# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## flaky-panel-secrets-ci — set_fact + until never re-draws random passwords, rare CI failures
- **Date:** 2026-11-27
- **Error patterns:** draw passwords, attempts 50, exhausted retries, FAILED - RETRYING, flaky, intermittent, negative case not recorded, xvpn_negative_rejected, panel-divergent-secret, lookup password, until, set_fact
- **Root cause(s):** roles/panel/tasks/secrets.yml drew passwords with set_fact + loop + until/retries; set_fact templates its arguments once per item, so every retry re-checked the first draw. A first draw missing a character class (~0.8% per role run) exhausted all retries; in the container verify this pre-empted the D-10 assert, so the rescue of panel-divergent-secret (keyed on 'app_secret' + 'rotation') correctly did not record it
- **Fix:** rejection sampling inside one template (Jinja loop over up to 64 fresh lookup('password') candidates, first with lower+upper+digit wins), failed_when on the class regex instead of until/retries
- **Files changed:** roles/panel/tasks/secrets.yml, scripts/check_until_set_fact.py, scripts/check.sh
- **Why not caught:** no gate existed for this class; review accepted until/retries as a re-draw loop, and the ~0.8% per-run failure rate is below what single CI runs expose
- **Recurrence guard:** scripts/check_until_set_fact.py (run by scripts/check.sh) fails on any role task combining set_fact with until; KB pattern: "retries exhaust in well under a second" means the retried value is frozen
---

