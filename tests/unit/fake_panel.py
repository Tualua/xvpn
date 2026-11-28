# Copyright (c) xvpn.remnawave contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Stdlib fake Remnawave Panel for the module unit tests."""
import copy
import json
import secrets
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ALL_MUTATIONS = ("clients_cleanup", "server_names", "outbounds_required", "sorted_keys")


def _reorder(obj):
    """Postgres JSONB and sortXrayConfig return keys in another order: reverse them recursively."""
    if isinstance(obj, dict):
        return dict((k, _reorder(obj[k])) for k in reversed(list(obj)))
    if isinstance(obj, list):
        return [_reorder(v) for v in obj]
    return obj


class FakePanel(object):
    def __init__(self):
        self.resources = {"nodes": [], "config_profiles": [], "internal_squads": []}
        # node status: isConnected turns true on the Nth GET /api/nodes/{uuid} (None: never)
        self.connect_after = 1
        self.node_status_message = "connection refused"
        self.node_gets = {}
        self.delete_polls = 1
        self._delete_seen = {}
        # Server-side transformations of config profiles, switchable per test. Faithful to 3.4.11: create only
        # sorts (config-profile.service.ts:146), update additionally cleans clients, splits serverNames and
        # requires outbounds (config-profile.service.ts:274-276).
        self.mutations = set(ALL_MUTATIONS)
        # an extra transformation the module does not know (read-back warning test)
        self.extra_transform = False
        # drops privateKey from stored inbounds (profile edited in the UI)
        self.strip_private_key = False
        self.requests = []
        self.meta_requests = []
        self.panel_version = "3.4.11"
        self._errors = []
        self.hang = False
        self.server = None
        self.thread = None

    def seed_profile(self, name, config):
        """Store a profile as the UI would: no mutation at all."""
        profile = {"uuid": str(uuid.uuid4()), "name": name, "config": copy.deepcopy(config)}
        self.resources["config_profiles"].append(profile)
        return profile

    def _public_profile(self, profile):
        config = copy.deepcopy(profile["config"])
        if self.strip_private_key:
            for inbound in config.get("inbounds") or []:
                ((inbound.get("streamSettings") or {}).get("realitySettings") or {}).pop("privateKey", None)
        if "sorted_keys" in self.mutations:
            config = _reorder(config)
        inbounds = [
            {"uuid": uuid.uuid5(uuid.UUID(profile["uuid"]), i["tag"]).hex, "profileUuid": profile["uuid"], "tag": i["tag"]}
            for i in profile["config"].get("inbounds") or []
        ]
        return {"uuid": profile["uuid"], "name": profile["name"], "config": config, "inbounds": inbounds, "nodes": []}

    def _update_mutations(self, config):
        config = copy.deepcopy(config)
        for inbound in config.get("inbounds") or []:
            if "clients_cleanup" in self.mutations and inbound.get("protocol") in ("vless", "trojan", "shadowsocks", "hysteria"):
                inbound.setdefault("settings", {})["clients"] = []
            names = ((inbound.get("streamSettings") or {}).get("realitySettings") or {}).get("serverNames")
            if "server_names" in self.mutations and inbound.get("protocol") == "vless" and names:
                out = []
                for name in names:
                    for part in name.split(","):
                        if part.strip() not in out:
                            out.append(part.strip())
                inbound["streamSettings"]["realitySettings"]["serverNames"] = out
            if self.extra_transform:
                inbound.setdefault("sniffing", {})["metadataOnly"] = False
        return config

    def _profiles_request(self, command, path, body):
        profiles = self.resources["config_profiles"]
        if command == "GET" and path == "/api/config-profiles":
            return 200, {"response": {"total": len(profiles), "configProfiles": [self._public_profile(p) for p in profiles]}}
        if command == "POST" and path == "/api/config-profiles":
            if any(p["name"] == body["name"] for p in profiles):
                return 409, {"errorCode": "A114", "message": "Config profile name already exists"}
            profile = self.seed_profile(body["name"], body["config"])
            if self.extra_transform:
                profile["config"] = self._update_mutations(profile["config"])
            return 200, {"response": self._public_profile(profile)}
        if command == "PATCH" and path == "/api/config-profiles":
            profile = next((p for p in profiles if p["uuid"] == body["uuid"]), None)
            if profile is None:
                return 404, {"errorCode": "A062", "message": "Config profile not found"}
            if "outbounds_required" in self.mutations and not body["config"].get("outbounds"):
                return 500, {"errorCode": "A061", "message": "Config validation error"}
            profile["config"] = self._update_mutations(body["config"])
            return 200, {"response": self._public_profile(profile)}
        if command == "DELETE" and path.startswith("/api/config-profiles/"):
            key = path.rsplit("/", 1)[1]
            self.resources["config_profiles"] = [p for p in profiles if p["uuid"] != key]
            return 200, {"response": True}
        return None

    def seed_squad(self, name, inbound_uuids=(), squad_uuid=None):
        squad = {"uuid": squad_uuid or str(uuid.uuid4()), "name": name, "inbounds": [{"uuid": u} for u in inbound_uuids]}
        self.resources["internal_squads"].append(squad)
        return squad

    def seed_node(self, name, address, profile_uuid, inbound_uuids, port=2222, country="XX"):
        node = {
            "uuid": str(uuid.uuid4()), "name": name, "address": address, "port": port, "countryCode": country,
            "isConnected": False, "isConnecting": False, "isDisabled": False, "lastStatusMessage": None,
            "configProfile": {"activeConfigProfileUuid": profile_uuid, "activeInbounds": [{"uuid": u} for u in inbound_uuids]},
        }
        self.resources["nodes"].append(node)
        return node

    def inbound_uuid(self, profile_name, tag):
        profile = next(p for p in self.resources["config_profiles"] if p["name"] == profile_name)
        return uuid.uuid5(uuid.UUID(profile["uuid"]), tag).hex

    def _squads_request(self, command, path, body):
        squads = self.resources["internal_squads"]
        if path != "/api/internal-squads":
            return None
        if command == "GET":
            return 200, {"response": {"total": len(squads), "internalSquads": copy.deepcopy(squads)}}
        if command == "POST":
            if any(s["name"] == body["name"] for s in squads):
                return 409, {"errorCode": "A100", "message": "Internal squad name already exists"}
            squad = self.seed_squad(body["name"], body["inbounds"])
            return 200, {"response": copy.deepcopy(squad)}
        if command == "PATCH":
            squad = next((s for s in squads if s["uuid"] == body["uuid"]), None)
            if squad is None:
                return 404, {"errorCode": "A099", "message": "Internal squad not found"}
            if "inbounds" in body:  # cleanInbounds + createInbounds: full replace
                squad["inbounds"] = [{"uuid": u} for u in body["inbounds"]]
            return 200, {"response": copy.deepcopy(squad)}
        return None

    def _nodes_request(self, command, path, body):
        nodes = self.resources["nodes"]
        if path == "/api/nodes" and command == "GET":
            out = []
            for n in nodes:
                if n.get("isNeedToBeDeleted"):
                    seen = self._delete_seen.get(n["uuid"], 0) + 1
                    self._delete_seen[n["uuid"]] = seen
                    if seen > self.delete_polls:
                        continue
                out.append(copy.deepcopy(n))
            self.resources["nodes"] = [n for n in nodes if not (n.get("isNeedToBeDeleted") and self._delete_seen.get(n["uuid"], 0) > self.delete_polls)]
            return 200, {"response": out}
        if path == "/api/nodes" and command == "POST" and "configProfile" not in (body or {}):
            return 200, {"response": {}}  # client tests post arbitrary bodies
        if path == "/api/nodes" and command == "POST":
            if any(n["address"] == body["address"] for n in nodes):
                return 409, {"errorCode": "A034", "message": "Node address already exists"}
            node = self.seed_node(
                body["name"], body["address"], body["configProfile"]["activeConfigProfileUuid"],
                body["configProfile"]["activeInbounds"], body.get("port") or 2222, body.get("countryCode", "XX"),
            )
            return 200, {"response": copy.deepcopy(node)}
        if path == "/api/nodes" and command == "PATCH":
            node = next((n for n in nodes if n["uuid"] == body["uuid"]), None)
            if node is None:
                return 404, {"errorCode": "A011", "message": "Node not found"}
            for key in ("address", "port", "countryCode"):
                if key in body:
                    node[key] = body[key]
            if "configProfile" in body:
                cp = body["configProfile"]
                node["configProfile"] = {
                    "activeConfigProfileUuid": cp["activeConfigProfileUuid"],
                    "activeInbounds": [{"uuid": u} for u in cp["activeInbounds"]],
                }
            return 200, {"response": copy.deepcopy(node)}
        if path.startswith("/api/nodes/"):
            key = path.rsplit("/", 1)[1]
            node = next((n for n in nodes if n["uuid"] == key), None)
            if node is None:
                return 404, {"errorCode": "A011", "message": "Node not found"}
            if command == "DELETE":
                node["isNeedToBeDeleted"] = True
                return 200, {"response": True}
            if command == "GET":
                count = self.node_gets.get(key, 0) + 1
                self.node_gets[key] = count
                if self.connect_after is not None and count >= self.connect_after:
                    node["isConnected"] = True
                else:
                    node["lastStatusMessage"] = self.node_status_message
                return 200, {"response": copy.deepcopy(node)}
        return None

    def fail_next(self, status, code, message):
        self._errors.append((status, code, message))

    @property
    def url(self):
        return "http://127.0.0.1:%d" % self.server.server_address[1]

    def __enter__(self):
        panel = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status, payload):
                raw = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _handle(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                if panel.hang:
                    threading.Event().wait(8)
                    return
                entry = {"method": self.command, "path": self.path, "headers": dict(self.headers), "json": body}
                if self.path == "/api/system/metadata":
                    panel.meta_requests.append(entry)
                    return self._send(200, {"response": {"version": panel.panel_version}})
                panel.requests.append(entry)
                if panel._errors:
                    status, code, message = panel._errors.pop(0)
                    return self._send(status, {"errorCode": code, "message": message})
                if self.command == "GET" and self.path == "/api/keygen":
                    return self._send(200, {"response": {"secretKey": secrets.token_hex(24)}})
                if self.command == "GET" and self.path == "/api/system/tools/x25519/generate":
                    return self._send(200, {"response": {"keypairs": [
                        {"publicKey": "pub" + secrets.token_hex(8), "privateKey": "key" + secrets.token_hex(20)}
                        for _ in range(30)]}})
                handled = panel._profiles_request(self.command, self.path, body)
                if handled:
                    return self._send(*handled)
                for extra in (panel._squads_request, panel._nodes_request):
                    handled = extra(self.command, self.path, body)
                    if handled:
                        return self._send(*handled)
                return self._send(200, {"response": {}})

            do_GET = do_POST = do_PATCH = do_DELETE = _handle

        # bound (and listening) before the serving thread starts: no readiness race
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
