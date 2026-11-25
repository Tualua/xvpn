---
phase: "02"
slug: "panel-za-traefik-s-zaschischennym-vhodom"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-25"
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Internet -> Traefik :80/:443 | untrusted clients, scanners, forged headers | HTTP requests, X-Forwarded-*, SNI |
| Internet -> Panel domain :443 | attackers probe UI, login and API paths | gate path, gate cookie (secret) |
| Internet -> subscription domain :443 | public, unauthenticated clients | subscription short UUIDs |
| Internet -> registration endpoint | must not exist before the admin is registered | first-admin credentials |
| Traefik -> loopback services | decoy, backend, sub-page trust Traefik's X-Forwarded-* | forwarded headers |
| Traefik logs and Ansible output | must not reveal the gate path, cookies or tokens | request paths, headers |
| Ansible (root) -> rw-edge / rw-panel home | root writes configs read by rootless containers | configs, env files (secret) |
| controller/vault -> Panel host | override values and generated secrets cross once, in memory | DB password, APP_SECRET, admin password, gate path/cookie (secret) |
| Ansible on Panel host -> backend loopback | bootstrap of first admin and API token | admin password, admin JWT, API token (secret) |
| Panel host filesystem | secrets, token, env files readable by service users only | secrets file, token file, env files (secret) |
| Podman network remnawave | backend, db, redis, sub-page talk privately | DB credentials, API token |
| operator inventory -> panel role | domains and toggles are operator input | FQDNs, booleans |
| CI -> ACME CA | test runs must never reach production Let's Encrypt | ACME requests |
| CI runner / VM -> downloads | Pebble, gitleaks, Traefik image fetched in CI | binaries, images (integrity) |
| Executor -> GitHub Actions | ci_watch.sh dispatches and reads workflow runs | run ids, conclusions |
| developer working tree / README -> public repository | committed content becomes public | any accidental secret |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Information Disclosure | TLS :443 default certificate | medium | mitigate | `sniStrict: true` (roles/edge/templates/00-edge.yml.j2); verify_edge unknown/no-SNI cases; gate run.sh | closed |
| T-02-02 | Spoofing | client X-Forwarded-* | high | mitigate | no forwardedHeaders/trustedIPs/insecure in roles/edge; verify_edge forged XFF -> ClientHost = real peer | closed |
| T-02-03 | Elevation of Privilege | Traefik container | high | mitigate | no Podman socket mount, file provider only, no api/dashboard (traefik.container.j2, traefik.yml.j2) | closed |
| T-02-04 | Denial of Service | LE prod rate limits from CI | medium | mitigate | `check_acme_ca` in scripts/check.sh; staging in container tier; Pebble in VM tier | closed |
| T-02-05 | Information Disclosure | private keys in acme.json | high | mitigate | dirs 0700, file 0600 rw-edge, never read/printed (roles/edge/tasks/main.yml); verify_edge asserts 0600 | closed |
| T-02-06 | Tampering | encoded path characters | medium | mitigate | all `allowEncoded*: false` on both entrypoints; `%2F` -> 400 asserted | closed |
| T-02-07 | Tampering | Pebble binaries in VM prepare | medium | mitigate | `get_url` with sha256 checksums (extensions/molecule/vm/tasks/pebble.yml) | closed |
| T-02-08 | Information Disclosure | Cookie/Authorization in access log | medium | mitigate | `headers.defaultMode: drop`, only User-Agent kept; verify_edge asserts absence | closed |
| T-02-09 | Information Disclosure | secrets in output, --diff, labels | high | mitigate | `no_log` + `diff: false` on all secret tasks; static gate scripts/check_no_log.py | closed |
| T-02-10 | Spoofing | placeholder / weak secrets | high | mitigate | format, weak-word and `<...>` asserts (roles/panel/tasks/secrets.yml); negative container cases | closed |
| T-02-11 | Denial of Service | silent rotation / regeneration | high | mitigate | refuse on lost secrets with surviving DB volume, corrupt file, vault mismatch; negative cases | closed |
| T-02-12 | Information Disclosure | backend/metrics/PG/Valkey exposure | high | mitigate | only `PublishPort=127.0.0.1:3000`; DB/Redis unpublished, Valkey `--port 0`; firewalld 80/443 only | closed |
| T-02-13 | Information Disclosure | secrets file on disk | medium | mitigate | dir 0700, file 0600 rw-panel; asserted in container and VM verify | closed |
| T-02-14 | Tampering | controller-side state of secrets | low | accept | see Accepted Risks AR-02-01 | closed |
| T-02-15 | Elevation of Privilege | first-admin registration race | high | mitigate | bootstrap before routes are published; backend loopback-only; `/api/auth` excluded from public API router | closed |
| T-02-16 | Information Disclosure | API token on controller or in logs | high | mitigate | no delegate_to/fetch/cacheable; no_log on token tasks; token file 0600; debug prints paths only | closed |
| T-02-17 | Elevation of Privilege | second admin on rerun | medium | mitigate | register only when `isRegisterAllowed && !isLoginAllowed`; hard fail on contradictory state | closed |
| T-02-18 | Spoofing | hand-set X-Forwarded-* on loopback requests | low | accept | see Accepted Risks AR-02-02 | closed |
| T-02-19 | Repudiation/Tampering | stale token stays valid | medium | mitigate | delete-by-name before create; VM asserts old token 401/403, exactly one token | closed |
| T-02-20 | Elevation of Privilege | gate bypass via normalization/encoding | high | mitigate | `(?i)^/+api/+auth(/|$)`, sanitizePath intact, allowEncoded* false; gate matrix in CI and VM | closed |
| T-02-21 | Information Disclosure | secret path in logs / Ansible output | high | mitigate | `RequestPath: drop`, `accessLogs: false` on gate routers, sensitive route no_log; verify_gate cases | closed |
| T-02-22 | Spoofing | stolen/forged gate cookie | medium | mitigate | 48-char cookie regenerated on path change; `Secure; HttpOnly; SameSite`; anchored regex | closed |
| T-02-23 | Spoofing | brute force of secret path | low | accept | see Accepted Risks AR-02-03 | closed |
| T-02-24 | Tampering | Pebble and Traefik image in gate workflow | medium | mitigate | `sha256sum -c`; image from role defaults; actions pinned by SHA, `contents: read` | closed |
| T-02-25 | Information Disclosure | API token in subpage.env / output | high | mitigate | subpage.env 0600 + no_log + diff:false; check_no_log covers `REMNAWAVE_API_TOKEN` | closed |
| T-02-26 | Elevation of Privilege | full-scope token in internet-facing container | medium | accept | see Accepted Risks AR-02-04 | closed |
| T-02-27 | Information Disclosure | sub-page reachable bypassing Traefik | medium | mitigate | `PublishPort=127.0.0.1:3010`; verify_subpage / verify_common port checks | closed |
| T-02-28 | Denial of Service | sub-page crash loop | low | mitigate | `Requires=/After=remnawave.service`, `Restart=always`; bootstrap ordered before subpage | closed |
| T-02-29 | Tampering | ci_watch accepts another commit's run | low | mitigate | origin/main == HEAD check, `--commit`, headSha re-check, conclusion check (scripts/ci_watch.sh) | closed |
| T-02-30 | Tampering | probe user / wrong-token swap in test VM | low | accept | see Accepted Risks AR-02-05 | closed |
| T-02-31 | Spoofing | placeholder / invalid Panel domain | low | mitigate | FQDN regex, `example.*` refused; `panel-placeholder-domain` case | closed |
| T-02-32 | Elevation of Privilege | SELinux weakened to get VM tier green | high | mitigate | Enforcing asserted, zero AVC since marker, no booleans; no setenforce/SecurityLabelDisable/privileged | closed |
| T-02-33 | Information Disclosure | env files with DB password, APP_SECRET, metrics | medium | mitigate | dir 0700, files 0600, no_log, diff:false (roles/panel/tasks/stack.yml); verify_panel | closed |
| T-02-34 | Elevation of Privilege | router regression exposes UI without cookie | high | mitigate | gate workflow on push/PR, break hook proves failure; ci_watch accepts push runs only | closed |
| T-02-35 | Information Disclosure | real secret in public repository | high | mitigate | gitleaks 8.30.1 (sha256) over all tracked files, xvpn rules, self-test 16 cases, CI hard fail; residuals in AR-02-06 | closed |
| T-02-36 | Information Disclosure | stale subpage.env / running page after disable | medium | mitigate | stop, then remove unit/env/route (roles/panel/tasks/subpage.yml); container + VM toggle cases | closed |
| T-02-37 | Information Disclosure | secret in README | medium | mitigate | placeholders only; README covered by gitleaks scan | closed |
| T-02-38 | Information Disclosure | gate path logged via :80 | high | mitigate | `xvpn-panel-http` with `accessLogs: false`; run.sh and verify_gate cases | closed |
| T-02-39 | Information Disclosure | request paths in access log | high | mitigate | access-log field config; rendered-config and live-log assertions | closed |
| T-02-40 | Information Disclosure | path of logged decoy request | high | mitigate | random-path probe, no path/`RequestPath` in live log (verify_edge) | closed |
| T-02-41 | Denial of Service | LE prod rate limits from gate workflow | medium | mitigate | Pebble URL pinned in scripts/gate/render.yml; check_acme_ca scans scripts/gate/*.yml | closed |
| T-02-SC | Tampering | supply chain (images, binaries, actions) | high | mitigate | images pinned via role defaults, `:latest` refused, no AutoUpdate=, sha256 on Pebble/gitleaks, actions pinned by SHA | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-14 | D-07: no controller-side state; secrets exist in controller memory only during the run (`lookup('password','/dev/null')`, no fetch/delegate_to) | plan 02-04 (user-approved plan) | 2026-11-25 |
| AR-02-02 | T-02-18 | Loopback-only calls from root on the host; the backend proxy check is a deployment sanity check, not an auth boundary | plan 02-06 (user-approved plan) | 2026-11-25 |
| AR-02-03 | T-02-23 | Secret path is 32 alnum chars (~190 bits); unknown paths return the same 200 decoy, no oracle | plan 02-07 (user-approved plan) | 2026-11-25 |
| AR-02-04 | T-02-26 | D-17: single full-scope API token (`scopes: ["*"]`) for v1; least-privilege sub-page token is v2 hardening (COVERAGE.md opt-out, README) | plan 02-10 (user-approved plan) | 2026-11-25 |
| AR-02-05 | T-02-30 | Test-only fixture in the Molecule VM; wrong token is random, role rerun restores subpage.env; roles never create users | plan 02-10 (user-approved plan) | 2026-11-25 |
| AR-02-06 | T-02-35 (residual) | Gitleaks residual bypasses: upstream stopwords pulled in by `useDefault = true` can suppress a finding; secret-named keys with suffixes other than `_file/_dir/_path` (e.g. `_file_v2`) are not scanned | user (plan-checker override, STATE.md) | 2026-11-25 |

*Accepted risks do not resurface in future audit runs.*

Non-blocking note from the audit: `valkey/valkey:9-alpine` and `nginx-unprivileged:1.31-alpine` float at patch/minor level as planned; candidate for digest pinning in a later phase.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-25 | 42 | 42 | 0 | gsd-security-auditor (ASVS L1, block_on high) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-25
