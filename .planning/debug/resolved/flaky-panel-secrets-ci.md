---
status: resolved
trigger: "Flaky panel secrets role in CI (two symptoms, likely one root cause): rocky10 container-tier negative case panel-divergent-secret not recorded once; alma10 VM-tier 'Panel secrets | draw passwords' exhausted retries once. Both passed on rerun."
created: 2026-11-27
updated: 2026-11-27
---

## Symptoms

DATA_START
- expected: Every CI run of the panel role is deterministic: the container-tier negative case panel-divergent-secret is always rejected for the expected reason, and "Panel secrets | draw passwords" always succeeds within its retries.
- actual: (1) molecule-container run 46023069471 attempt 1, host rocky10 only: final assert "Assert every negative case was rejected for the expected reason" failed because 'panel-divergent-secret' was missing from xvpn_negative_rejected (alma10/oracle10 in the same run passed; the rerun passed). (2) molecule-vm run 46023083143 attempt 1, host alma10: task "Panel secrets | draw passwords" exhausted its retries (rerun passed).
- errors: see `gh run view 46023069471 --attempt 1 --log` and `gh run view 46023083143 --attempt 1 --log` (alma10 job).
- timeline: observed 2026-11-27 during plan 02-12 CI; the plan did not touch roles/panel. Earlier green runs exist, so the failure is intermittent.
- repro: intermittent; CI only. Relevant code: roles/panel/tasks/secrets.yml (draw passwords, policy checks, divergent-override refusal), extensions/molecule/container/verify.yml (# xvpn_negative_case: panel-divergent-secret, rescue `when:` conditions).
DATA_END

Hypothesis seed (orchestrator, unverified): random password drawing can fail a strength/policy check with some probability, and/or the negative case's rescue condition depends on the failure message, which changes when a random draw fails first.

## Current Focus

bug_class: Bohrbug (deterministic given the first random draw; looks flaky only because the draw is random)
hypothesis: "set_fact + loop + until does not re-template the task args on retry, so the first lookup('password') value is reused for all 50 attempts. When that first draw lacks a character class (p~0.36% for 32 chars, ~0.09% for 40), the task deterministically exhausts its retries. In the container-tier negative case this failure happens before the D-10 rotation assert, so the rescue condition ('app_secret' and 'rotation' in the result) is false and the case is not recorded."
test: "local ansible-core 2.22 playbook: set_fact with a 1-digit lookup, until d=='0', retries 30, run 15x"
expecting: "re-templating => ~4% failures; frozen value => ~90% failures"
next_action: "none (resolved, archived). CI green on 93967d3; human verification waived by the orchestrator for this CI-only fix. Done: replace until/retries with rejection sampling inside one template (Jinja loop over fresh lookups), keep a failed_when on the class regex; add a static guard against until on set_fact"
reasoning_checkpoint:
  hypothesis: "The draw task's until/retries never re-draws: Ansible templates set_fact args once per item, so retries re-check the same value; ~0.8% of panel role runs fail at draw passwords."
  confirming_evidence:
    - "CI logs: both alma10 VM and rocky10 container failures show 'draw passwords' attempts=50 within ~0.2 s (retries without new draws)"
    - "Local repro: 13/15 runs failed with a 1/10 success condition and 30 retries (frozen value predicts ~90%, re-draw predicts ~4%)"
    - "Container rocky10 failure at 15:22:24 sits inside the negative-case section, matching panel-divergent-secret missing from xvpn_negative_rejected"
  falsification_test: "If a draw that lacks a class could be followed by a different draw on retry, the local test would fail ~4%, not ~87%."
  fix_rationale: "Rejection sampling inside a single template draws fresh CSPRNG values per candidate, so the class requirement is met with probability 1-1e-150 and no reliance on retry semantics."
  blind_spots: "Whether lookup results inside a Jinja for loop are cached in ansible-core 2.20/2.21 (verify on installed core and CI matrix)."
  candidate_causes:
    - "code: until/retries on set_fact reuse the templated value (confirmed)"
    - "environment: CI host entropy/regex engine differences (eliminated: same failure on two hosts/tiers, repro on local controller)"
  and_gate: "yes, for symptom 1 only: the draw failure (cause) AND the rescue condition keyed on the rotation message (amplifier) together turn the draw failure into a missing negative-case record; the rescue condition is correct as-is (it must not accept unrelated failures)."

## Evidence

- timestamp: 2026-11-27
  checked: gh run 46023083143 attempt 1 (alma10 VM) and 46023069471 attempt 1 (container rocky10) logs
  found: both fail at 'Panel secrets | draw passwords' with attempts=50 in ~0.16 s; the container failure (15:22:24) is inside the verify negative cases, right after the panel-* domain negatives, i.e. panel-divergent-secret
  implication: symptom 1 and 2 are the same failure; the negative case was rejected for the wrong reason (draw failure), so the rescue did not record it
- timestamp: 2026-11-27
  checked: local ansible-core 2.22.0, set_fact+loop+until with lookup('password', chars=digits, length=1), until d=='0', retries 30, 15 runs
  found: 13/15 runs failed
  implication: retries reuse the first templated value; the until/retries in secrets.yml never re-draws
- timestamp: 2026-11-27
  checked: probability that a draw misses a class (inclusion-exclusion over 62 alnum)
  found: 32 chars 0.36%, 40 chars 0.088%; per role run (2x32 + 1x40) 0.80%; the verify playbooks run the panel role many times per host per CI run
  implication: a few-percent flake rate per CI run, matching the intermittent observations

## Eliminated

- hypothesis: rescue condition of panel-divergent-secret is wrong / D-10 message changed
  evidence: the run failed before the D-10 assert (at draw passwords); the rescue correctly refused to record an unrelated failure
  timestamp: 2026-11-27

## Resolution

root_cause: "roles/panel/tasks/secrets.yml draws passwords with set_fact + loop + until/retries; Ansible templates set_fact args once per item, so retries re-check the same value. A first draw lacking a character class (~0.8% per role run) exhausts all 50 retries; in the container verify that failure pre-empts the D-10 assert, so panel-divergent-secret is not recorded."
fix: "secrets.yml draw task: rejection sampling inside one template (Jinja loop, up to 64 fresh lookup(password) candidates, first one with lower+upper+digit wins); until/retries replaced by failed_when on the class regex. New static guard scripts/check_until_set_fact.py (wired into scripts/check.sh) fails on any role task that combines set_fact with until."
verification:
  oracle_type: specified (every drawn password matches ^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9]) and has the requested length)
  repro_before: "local: set_fact+until frozen-draw test failed 13/15 (expected ~90% if frozen)"
  fix_stress: "the fixed task, extracted with lengths 3/4/5 (83%/~70%/~55% per-candidate rejection), 40/40 runs green, assert on classes and length; old shape fails most such runs"
  fresh_draw_check: "candidate counts per run 4,3,15,30,3,21,3,5,4,5,23,1 (geometric, mean ~10) -> lookups inside the Jinja loop are fresh"
  guard_mutation: "check_until_set_fact.py: OK on fix, rc=1 naming the draw task when secrets.yml is reverted"
  gate: "scripts/check.sh OK; ansible-lint production 0 failures 0 warnings"
  ci: "commit 93967d3: molecule-container run 46036846451 success (9 draw executions, 0 retries); molecule-vm run 46038967381 success"
  human_verification: "waived (CI-only fix); green lint/gate/molecule-container 46036846451 and molecule-vm 46038967381 (alma10/oracle10/rocky10) on 93967d3 accepted as verification"
  guardrail_verdict: accepted
  residual: "one green CI run cannot prove absence of a ~0.8%-per-run flake by itself; the proof is the frozen-retry repro + short-length stress test"
files_changed: [roles/panel/tasks/secrets.yml, scripts/check_until_set_fact.py, scripts/check.sh]

## Prevention

- why_not_caught: none (no gate existed for this class; until/retries on set_fact looked correct and the failure rate is ~0.8% per role run)
- guard: scripts/check_until_set_fact.py (wired into scripts/check.sh) rejects any role task combining set_fact with until
