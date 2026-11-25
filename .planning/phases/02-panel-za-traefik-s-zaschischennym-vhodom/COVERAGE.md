# API Coverage — Remnawave Panel REST API (backend 3.4.11), Phase 02

> Full coverage by default. Opt-outs are explicit, reasoned decisions.

Phase 02 calls the Panel API only from Ansible on the Panel host over loopback (`http://127.0.0.1:3000`,
forwarded headers set by hand, RESEARCH Pitfall 1) to bootstrap the first admin and the automation token
(PANEL-03, PANEL-04). The subscription page talks to the API itself with the token (SUB-02); the collection
does not call those endpoints. Let's Encrypt / Pebble ACME is spoken by Traefik, not by the collection, so it
is not an integration surface of this phase.

| capability | decision | reason |
|---|---|---|
| auth.status (GET /api/auth/status) | INTEGRATE | |
| auth.register (POST /api/auth/register) | INTEGRATE | |
| auth.login (POST /api/auth/login) | INTEGRATE | |
| api-tokens.create (POST /api/tokens) | INTEGRATE | |
| api-tokens.list (GET /api/tokens) | INTEGRATE | |
| api-tokens.delete (DELETE /api/tokens/{uuid}) | INTEGRATE | |
| nodes.list (GET /api/nodes, read-only token validity probe) | INTEGRATE | |
| api-tokens.scopes (GET /api/tokens/scopes) | OPT-OUT | not needed yet: v1 uses the single scopes ["*"] token (D-17, RESEARCH Open Question 3); least-privilege sub-page token is a v2 hardening item |
| auth.oauth2 / telegram / passkey login | OPT-OUT | explicitly out of scope: v1 supports password login only behind the SameSite=Strict gate cookie (D-04, RESEARCH Pitfall 10) |
| system.metadata (GET /api/system/metadata) | OPT-OUT | not needed: called by the subscription page itself at start-up, not by the collection |
| subscription public endpoints (/api/sub/*) | OPT-OUT | not needed: consumed by clients and the subscription page; the collection only keeps /api/* reachable without the cookie (D-03) |
| nodes create/update/delete/enable/disable/restart | OPT-OUT | not needed yet: node registration is Phase 3 (REG-*), with its own matrix |
| keygen (GET /api/keygen) | OPT-OUT | not needed yet: node secret key retrieval is Phase 3 |
| config-profiles | OPT-OUT | not needed yet: Reality inbound profiles are Phase 3 |
| hosts | OPT-OUT | not needed yet: client-facing hosts are Phase 3 |
| internal-squads | OPT-OUT | not needed yet: trusted LAN squad is Phase 4 |
| users / user subscriptions management | OPT-OUT | explicitly out of scope for v1: VPN users are managed by the operator in the Panel UI |
| users.create + users.get-by-username (probe user `xvpn-molecule-probe`) | INTEGRATE | test fixture only: called by `extensions/molecule/shared/verify_subpage.yml` in the Molecule VM to prove SUB-02 with an authenticated lookup (Plan 02-10); the roles never create users |
| subscription /api/sub/* without cookie on the Panel domain | INTEGRATE | verify-only reachability probe `sub-public-no-cookie` (Plans 02-07, 02-08); the collection itself still does not consume subscriptions |
| system stats, bandwidth, HWID, settings, infra-billing, snippets and other admin surfaces | OPT-OUT | explicitly out of scope: operated through the Panel UI, not automated by the collection |
