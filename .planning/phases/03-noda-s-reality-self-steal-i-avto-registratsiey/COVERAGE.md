# API Coverage — Remnawave Panel REST API (backend 3.4.11), Phase 03

> Full coverage by default. Opt-outs are explicit, reasoned decisions.

Phase 03 calls the Panel API only through the collection's own modules (`plugins/modules/remnawave_*.py`,
shared client `plugins/module_utils/remnawave.py`), executed on the Panel host (`delegate_to`) against
`http://127.0.0.1:3000` with the token file written in Phase 02 (D-09). The Molecule two-VM scenario
additionally calls a few endpoints from verify tasks to build a real client (test fixture only).
Let's Encrypt / Pebble ACME is spoken by Traefik, not by the collection.

| capability | decision | reason |
|---|---|---|
| config-profiles.list (GET /api/config-profiles) | INTEGRATE | |
| config-profiles.create (POST /api/config-profiles) | INTEGRATE | |
| config-profiles.update (PATCH /api/config-profiles) | INTEGRATE | |
| config-profiles.delete (DELETE /api/config-profiles/{uuid}) | INTEGRATE | |
| internal-squads.list (GET /api/internal-squads) | INTEGRATE | |
| internal-squads.create (POST /api/internal-squads) | INTEGRATE | |
| internal-squads.update (PATCH /api/internal-squads, union of inbounds) | INTEGRATE | |
| internal-squads.delete (DELETE /api/internal-squads/{uuid}) | OPT-OUT | not needed: D-06 only adds the node inbound to named squads and never deletes squads; inbound membership disappears by cascade when the profile is deleted (RESEARCH Pitfall 5) |
| nodes.list (GET /api/nodes) | INTEGRATE | |
| nodes.get (GET /api/nodes/{uuid}) | INTEGRATE | |
| nodes.create (POST /api/nodes) | INTEGRATE | |
| nodes.update (PATCH /api/nodes) | INTEGRATE | |
| nodes.delete (DELETE /api/nodes/{uuid}, async, polled) | INTEGRATE | |
| nodes.enable / disable / restart / reorder | OPT-OUT | not needed yet: lifecycle beyond present/absent is operated in the Panel UI; a profile PATCH already restarts the nodes it touches |
| hosts.list (GET /api/hosts) | INTEGRATE | |
| hosts.create (POST /api/hosts) | INTEGRATE | |
| hosts.update (PATCH /api/hosts) | INTEGRATE | |
| hosts.delete (DELETE /api/hosts/{uuid}) | INTEGRATE | |
| hosts bulk actions / reorder | OPT-OUT | not needed: one host per node in v1 (D-07); several hosts per node are deferred |
| keygen (GET /api/keygen, SECRET_KEY, generate-once) | INTEGRATE | |
| system.tools.x25519.generate (GET /api/system/tools/x25519/generate) | INTEGRATE | |
| system.metadata (GET /api/system/metadata, version pin check) | INTEGRATE | |
| users.create + users.get-by-username (probe user `xvpn-molecule-client`) | INTEGRATE | test fixture only: called by the two-VM verify to obtain a real client subscription (Plan 03-13); the roles never create users (REQUIREMENTS Out of Scope) |
| subscription /api/sub/{shortUuid} (raw links) | INTEGRATE | test fixture only: the two-VM verify reads the issued vless:// link to configure the Xray client (Plan 03-13) |
| users / subscriptions management in roles | OPT-OUT | explicitly out of scope for v1: VPN users are managed by the operator in the Panel UI |
| config-profiles computed config / inbounds-by-profile endpoints | OPT-OUT | not needed: the list response already carries `config` and `inbounds[]` with uuids and tags |
| Reality key rotation (any endpoint) | OPT-OUT | explicitly out of scope: D-03, API-V2-01 (v2) |
| nodes usage / traffic / bandwidth statistics | OPT-OUT | explicitly out of scope: monitoring is operated in the Panel UI |
| auth / api-tokens endpoints | OPT-OUT | not needed: covered by Phase 02 (bootstrap); Phase 03 only reads the token file on the Panel host |
| infra-billing, snippets, HWID, settings, other admin | OPT-OUT | explicitly out of scope: not part of node registration |
