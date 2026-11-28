#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) xvpn.remnawave contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: remnawave_node
short_description: Register a Remnawave node in the Panel and wait until it is connected
version_added: "0.1.0"
description:
  - Creates, updates or deletes a node (key is O(name)) and binds it to a config profile and inbounds.
  - A node whose name is new but whose requested O(address) equals the Panel C(address) field of another node
    is refused before any write (the Panel keeps addresses unique). The comparison is a string comparison
    (stripped, case-insensitive); DNS is never resolved.
  - With O(wait_connected) the module polls the node until the Panel reports it connected, bounded by
    O(wait_retries) times O(wait_delay) seconds. Waiting never sets C(changed).
extends_documentation_fragment:
  - xvpn.remnawave.remnawave
options:
  name:
    description: Node name (3 to 30 characters).
    type: str
    required: true
  address:
    description: Address the Panel connects to. Required for V(present).
    type: str
  port:
    description: Node API port.
    type: int
    default: 2222
  country_code:
    description: Two-letter country code.
    type: str
    default: XX
  config_profile:
    description: Config profile name. Required for V(present).
    type: str
  inbound_tags:
    description: Inbound tags of the profile that the node serves.
    type: list
    elements: str
    default: []
  state:
    description: V(present) reconciles the node, V(absent) deletes it and waits until it is gone.
    type: str
    choices: [present, absent]
    default: present
  wait_connected:
    description: Wait until the node is connected. Ignored in check mode.
    type: bool
    default: false
  wait_retries:
    description: Maximum number of status polls.
    type: int
    default: 30
  wait_delay:
    description: Seconds between polls.
    type: int
    default: 5
author:
  - xvpn.remnawave contributors
"""

EXAMPLES = r"""
- name: Register the node
  xvpn.remnawave.remnawave_node:
    api_token_file: /home/remnawave/secrets/api_token
    name: node-1
    address: node1.example.com
    config_profile: node-1
    inbound_tags: [vless-reality-node-1]
    wait_connected: true
"""

RETURN = r"""
uuid:
  description: UUID of the node (empty when absent or would be created in check mode).
  returned: always
  type: str
is_connected:
  description: Connection state seen by the Panel at the last read.
  returned: always
  type: bool
changed:
  description: True exactly when a create, update or delete was sent (or would be, in check mode).
  returned: always
  type: bool
diff:
  description: Before and after text of the managed fields.
  returned: always
  type: dict
"""

import json
import time

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.xvpn.remnawave.plugins.module_utils.remnawave import (
    RemnawaveClient,
    common_argument_spec,
    find_by,
    resolve_profile,
)


def _same_address(a, b):
    return (a or "").strip().lower() == (b or "").strip().lower()


def _managed(node):
    cfg = node.get("configProfile") or {}
    return {
        "address": node.get("address"),
        "port": node.get("port"),
        "countryCode": node.get("countryCode"),
        "activeConfigProfileUuid": cfg.get("activeConfigProfileUuid"),
        "activeInbounds": sorted(i.get("uuid") if isinstance(i, dict) else i for i in cfg.get("activeInbounds") or []),
    }


def _text(obj):
    return json.dumps(obj, indent=2, sort_keys=True) if obj else ""


def wait_connected(module, client, node):
    p = module.params
    retries, delay = max(p["wait_retries"], 1), max(p["wait_delay"], 0)
    last = node
    for attempt in range(retries):
        last = client.get("/api/nodes/%s" % node["uuid"]) or {}
        if last.get("isConnected"):
            return last
        if attempt < retries - 1:
            time.sleep(delay)
    module.fail_json(
        msg="node %s not connected after %s x %s s (isConnecting=%s, isDisabled=%s, lastStatusMessage=%s): "
        "check the rich rule for the Panel IP on port %s (it admits only xvpn_node_panel_sources, IPv4 only; "
        "when the Panel is behind NAT set xvpn_node_panel_sources to the address it connects from), "
        "remnanode.service on the node and node.env (a lost key is re-issued only with -e xvpn_node_rekey=true)"
        % (p["name"], retries, delay, last.get("isConnecting"), last.get("isDisabled"), last.get("lastStatusMessage"), p["port"]),
        uuid=node["uuid"],
        is_connected=False,
    )


def wait_gone(module, client, uuid):
    p = module.params
    retries, delay = max(p["wait_retries"], 1), max(p["wait_delay"], 0)
    for attempt in range(retries):
        nodes = client.get("/api/nodes") or []
        left = find_by(nodes, "uuid", uuid)
        if left is None:
            return
        if attempt < retries - 1:
            time.sleep(delay)
    module.fail_json(
        msg="node %s still listed by the Panel after %s x %s s (isNeedToBeDeleted=%s, isConnected=%s)"
        % (p["name"], retries, delay, left.get("isNeedToBeDeleted"), left.get("isConnected"))
    )


def main():
    spec = common_argument_spec()
    spec.update(
        name=dict(type="str", required=True),
        address=dict(type="str"),
        port=dict(type="int", default=2222),
        country_code=dict(type="str", default="XX"),
        config_profile=dict(type="str"),
        inbound_tags=dict(type="list", elements="str", default=[]),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        wait_connected=dict(type="bool", default=False),
        wait_retries=dict(type="int", default=30),
        wait_delay=dict(type="int", default=5),
    )
    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        required_if=[("state", "present", ["address", "config_profile"])],
    )
    p = module.params
    client = RemnawaveClient(module)
    nodes = client.get("/api/nodes") or []
    node = find_by(nodes, "name", p["name"])

    if p["state"] == "absent":
        if node is None:
            module.exit_json(changed=False, uuid="", is_connected=False, diff={"before": "", "after": ""})
        diff = {"before": _text(_managed(node)), "after": ""}
        if not module.check_mode:
            client.delete("/api/nodes/%s" % node["uuid"])
            wait_gone(module, client, node["uuid"])
        module.exit_json(changed=True, uuid=node["uuid"], is_connected=False, diff=diff)

    profile_uuid, tag_map = resolve_profile(client, p["config_profile"])
    if profile_uuid is None and not module.check_mode:
        module.fail_json(msg="config profile %s does not exist" % p["config_profile"])
    unknown = [t for t in p["inbound_tags"] if t not in tag_map]
    if profile_uuid is not None and unknown:
        module.fail_json(msg="config profile %s has no inbound(s) %s" % (p["config_profile"], ", ".join(unknown)))
    desired = {
        "address": p["address"].strip(),
        "port": p["port"],
        "countryCode": p["country_code"].upper(),
        "activeConfigProfileUuid": profile_uuid,
        "activeInbounds": sorted(tag_map[t] for t in p["inbound_tags"] if t in tag_map),
    }
    if profile_uuid is None:
        desired["activeConfigProfileUuid"] = "<created on apply>"
    diff = {"before": _text(_managed(node)) if node else "", "after": _text(desired)}

    if node is None:
        for other in nodes:
            if _same_address(other.get("address"), p["address"]):
                module.fail_json(
                    msg="another Panel node already uses address %s; set xvpn_node_address or remove that node"
                    % p["address"].strip()
                )
        if module.check_mode:
            module.exit_json(changed=True, uuid="", is_connected=False, diff=diff)
        body = {
            "name": p["name"],
            "address": desired["address"],
            "port": desired["port"],
            "countryCode": desired["countryCode"],
            "configProfile": {
                "activeConfigProfileUuid": profile_uuid,
                "activeInbounds": desired["activeInbounds"],
            },
        }
        node = client.post("/api/nodes", body) or {}
        changed = True
    else:
        current = _managed(node)
        changed = current != desired
        if changed and not module.check_mode:
            body = {"uuid": node["uuid"]}
            for key in ("address", "port", "countryCode"):
                if current[key] != desired[key]:
                    body[key] = desired[key]
            if (current["activeConfigProfileUuid"], current["activeInbounds"]) != (
                desired["activeConfigProfileUuid"],
                desired["activeInbounds"],
            ):
                body["configProfile"] = {
                    "activeConfigProfileUuid": profile_uuid,
                    "activeInbounds": desired["activeInbounds"],
                }
            client.patch("/api/nodes", body)

    connected = bool(node.get("isConnected"))
    if p["wait_connected"] and not module.check_mode:
        node = wait_connected(module, client, node)
        connected = True
    module.exit_json(changed=changed, uuid=node.get("uuid", ""), is_connected=connected, diff=diff)


if __name__ == "__main__":
    main()
