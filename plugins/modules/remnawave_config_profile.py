#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) xvpn.remnawave contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: remnawave_config_profile
short_description: Reconcile a Remnawave config profile without rotating Reality keys
version_added: "0.1.0"
description:
  - Creates, updates or deletes a Remnawave config profile (an Xray config) through the Panel API.
  - Reality keys are never taken from the declaration. For every inbound listed in O(reality_inbounds) the keys
    C(privateKey), C(publicKey) and C(shortIds) are removed from O(config); an existing profile keeps its stored keys,
    a new inbound gets a key from the Panel x25519 tool and generated shortIds, once.
  - The Panel x25519 tool returns a batch of keypairs; the module uses the first unused one per new inbound.
  - The Panel transforms a stored config (empty C(settings.clients), split C(serverNames), key order). The module
    pre-applies those transformations and compares normalized JSON, so a converged profile is never patched
    (every config PATCH restarts all nodes of the profile).
  - The private keys are never returned, printed in C(--diff) or echoed in the invocation.
extends_documentation_fragment:
  - xvpn.remnawave.remnawave
options:
  name:
    description:
      - Profile name, 2 to 30 characters of letters, digits, underscore, dash and space (Panel rule, no dots).
    type: str
    required: true
  state:
    description: V(present) reconciles the profile, V(absent) deletes it.
    type: str
    choices: [present, absent]
    default: present
  config:
    description: The declared Xray config. Required for V(present).
    type: dict
  reality_inbounds:
    description: Inbounds (by tag) whose Reality keys the module manages.
    type: list
    elements: dict
    default: []
    suboptions:
      tag:
        description: Inbound tag.
        type: str
        required: true
      short_ids:
        description: Number of shortIds generated for a new inbound.
        type: int
        default: 2
      short_id_length:
        description: Hex characters per generated shortId (even, 2 to 16).
        type: int
        default: 16
      target:
        description: When set, C(realitySettings.target) (and C(dest) when present) of the inbound must equal it.
        type: str
      server_names:
        description: When set, C(realitySettings.serverNames) of the inbound must equal it.
        type: list
        elements: str
  required_block_cidrs:
    description:
      - When not empty, the config must contain a routing rule with C(outboundTag) O(block_outbound_tag) whose C(ip)
        list covers every entry. Guards against an override that replaces C(routing.rules).
    type: list
    elements: str
    default: []
  block_outbound_tag:
    description: Outbound tag of the blocking rule.
    type: str
    default: BLOCK
notes:
  - "Check mode sends no write and no x25519 call; a profile or inbound that would get new keys shows
    C(<generated on apply>) in the diff."
author:
  - xvpn.remnawave contributors
"""

EXAMPLES = r"""
- name: Reconcile the node profile
  xvpn.remnawave.remnawave_config_profile:
    api_token_file: /home/remnawave/secrets/api_token
    name: node-1
    config: "{{ lookup('ansible.builtin.template', 'config-profile.json.j2') | from_json }}"
    reality_inbounds:
      - tag: vless-reality-node-1
        target: 127.0.0.1:8443
        server_names: [node.example.com]
    required_block_cidrs: [10.0.0.0/8, 192.168.0.0/16]
  register: profile
"""

RETURN = r"""
uuid:
  description: UUID of the profile (empty when it does not exist or would be created in check mode).
  returned: always
  type: str
inbounds:
  description: Mapping of inbound tag to inbound UUID.
  returned: always
  type: dict
changed:
  description: True exactly when a create, update or delete was sent (or would be, in check mode).
  returned: always
  type: bool
diff:
  description: Before and after text of the profile with secret values redacted.
  returned: always
  type: dict
warnings:
  description: A warning names the JSON paths where the Panel stored something different from what was sent.
  returned: when the read-back differs
  type: list
"""

import copy
import json
import re
import secrets

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.xvpn.remnawave.plugins.module_utils.remnawave import (
    RemnawaveClient,
    apply_panel_mutations,
    common_argument_spec,
    diff_paths,
    find_by,
    normalize,
    redact,
)

NAME_RULE = re.compile(r"^[A-Za-z0-9_ -]{2,30}$")
PLACEHOLDER = "<generated on apply>"
OVERRIDE = "xvpn_node_profile_override"


def _reality(inbound):
    stream = inbound.setdefault("streamSettings", {})
    return stream.setdefault("realitySettings", {})


def _find_inbound(config, tag):
    return find_by((config or {}).get("inbounds"), "tag", tag)


def _split_names(names):
    out = []
    for name in names or []:
        for part in str(name).split(","):
            part = part.strip()
            if part not in out:
                out.append(part)
    return out


def enforce_declared(module, desired, managed, required_cidrs, block_tag):
    inbounds = desired.get("inbounds")
    if not isinstance(inbounds, list) or not inbounds:
        module.fail_json(msg="config has no inbounds (the Panel rejects it)")
    tags = [i.get("tag") for i in inbounds if isinstance(i, dict)]
    if len(tags) != len(set(tags)) or not all(tags):
        module.fail_json(msg="every inbound needs a unique tag")
    for entry in managed:
        inbound = _find_inbound(desired, entry["tag"])
        if inbound is None:
            module.fail_json(msg="reality_inbounds tag %s is not an inbound of config" % entry["tag"])
        reality = (inbound.get("streamSettings") or {}).get("realitySettings") or {}
        if entry.get("target"):
            for field in ("target", "dest"):
                if field in reality or field == "target":
                    if reality.get(field) != entry["target"]:
                        module.fail_json(
                            msg="realitySettings.%s of managed inbound %s is managed by the collection "
                            "(xvpn_edge_https_address / xvpn_node_domain); remove it from %s"
                            % (field, entry["tag"], OVERRIDE)
                        )
        if entry.get("server_names"):
            if _split_names(reality.get("serverNames")) != _split_names(entry["server_names"]):
                module.fail_json(
                    msg="realitySettings.serverNames of managed inbound %s is managed by the collection "
                    "(xvpn_edge_https_address / xvpn_node_domain); remove it from %s" % (entry["tag"], OVERRIDE)
                )
    if required_cidrs:
        rules = (desired.get("routing") or {}).get("rules") or []
        ok = any(
            isinstance(r, dict)
            and r.get("outboundTag") == block_tag
            and set(required_cidrs) <= set(r.get("ip") or [])
            for r in rules
        )
        if not ok:
            module.fail_json(
                msg="the private-destination %s rule over xvpn_node_blocked_cidrs is missing from the profile; "
                "%s replaces lists such as routing.rules instead of merging them, so an override of "
                "routing.rules must keep that rule (a LAN allow may precede it)" % (block_tag, OVERRIDE)
            )


class Keys(object):
    """Lazy source of one x25519 batch per run (the Panel returns 30 keypairs per call)."""

    def __init__(self, client):
        self.client = client
        self.batch = None
        self.used = 0

    def next_private(self):
        if self.batch is None:
            data = self.client.get("/api/system/tools/x25519/generate") or {}
            self.batch = [k for k in data.get("keypairs") or [] if k.get("privateKey")]
        if self.used >= len(self.batch):
            self.client.module.fail_json(msg="the Panel x25519 tool returned no usable keypair")
        key = self.batch[self.used]["privateKey"]
        self.used += 1
        return key


def inject_keys(module, desired, stored_config, managed, keys, name):
    """D-03: drop any declared key material, then fill stored keys or generate new ones once."""
    for entry in managed:
        tag = entry["tag"]
        reality = _reality(_find_inbound(desired, tag))
        for key in ("privateKey", "publicKey", "shortIds"):
            reality.pop(key, None)
        stored = _find_inbound(stored_config, tag)
        if stored is not None:
            sreal = (stored.get("streamSettings") or {}).get("realitySettings") or {}
            if not sreal.get("privateKey") or not sreal.get("shortIds"):
                module.fail_json(
                    msg="stored profile %s inbound %s has no privateKey/shortIds; delete the profile in the Panel "
                    "to re-key (clients must be re-issued)" % (name, tag)
                )
            reality["privateKey"] = sreal["privateKey"]
            reality["shortIds"] = copy.deepcopy(sreal["shortIds"])
        elif module.check_mode:
            reality["privateKey"] = PLACEHOLDER
            reality["shortIds"] = [PLACEHOLDER]
        else:
            length = entry["short_id_length"]
            reality["privateKey"] = keys.next_private()
            reality["shortIds"] = [secrets.token_hex(length // 2) for _ in range(entry["short_ids"])]


def read_profiles(client):
    data = client.get("/api/config-profiles") or {}
    return data.get("configProfiles") or []


def inbound_map(profile):
    return dict((i.get("tag"), i.get("uuid")) for i in (profile or {}).get("inbounds") or [])


def main():
    spec = common_argument_spec()
    spec.update(
        name=dict(type="str", required=True),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        config=dict(type="dict"),
        reality_inbounds=dict(
            type="list",
            elements="dict",
            default=[],
            options=dict(
                tag=dict(type="str", required=True),
                short_ids=dict(type="int", default=2),
                short_id_length=dict(type="int", default=16),
                target=dict(type="str"),
                server_names=dict(type="list", elements="str"),
            ),
        ),
        required_block_cidrs=dict(type="list", elements="str", default=[]),
        block_outbound_tag=dict(type="str", default="BLOCK"),
    )
    module = AnsibleModule(
        argument_spec=spec,
        supports_check_mode=True,
        required_if=[("state", "present", ["config"])],
    )
    p = module.params
    name = p["name"]
    declared = p.get("config")
    # the invocation echoes module.params: keep key material out of it
    if declared is not None:
        module.params["config"] = redact(declared)

    if not NAME_RULE.match(name):
        module.fail_json(msg="name %r violates the Panel rule ^[A-Za-z0-9_ -]{2,30}$ (no dots)" % name)
    if name == "Default-Profile":
        module.fail_json(msg="Default-Profile is reserved by the Panel")
    for entry in p["reality_inbounds"]:
        length = entry["short_id_length"]
        if length < 2 or length > 16 or length % 2:
            module.fail_json(msg="short_id_length must be an even number from 2 to 16")
        if entry["short_ids"] < 1:
            module.fail_json(msg="short_ids must be at least 1")

    desired = None
    if p["state"] == "present":
        desired = copy.deepcopy(declared)
        enforce_declared(module, desired, p["reality_inbounds"], p["required_block_cidrs"], p["block_outbound_tag"])
        try:
            apply_panel_mutations(desired)
        except ValueError as exc:
            module.fail_json(msg=str(exc))

    client = RemnawaveClient(module)
    stored = find_by(read_profiles(client), "name", name)

    if p["state"] == "absent":
        if stored is None:
            module.exit_json(changed=False, uuid="", inbounds={}, diff={"before": "", "after": ""})
        diff = {"before": json.dumps(redact(stored.get("config")), indent=2, sort_keys=True), "after": ""}
        if not module.check_mode:
            client.delete("/api/config-profiles/%s" % stored["uuid"])
        module.exit_json(changed=True, uuid=stored["uuid"], inbounds=inbound_map(stored), diff=diff)

    stored_config = stored.get("config") if stored else None
    inject_keys(module, desired, stored_config, p["reality_inbounds"], Keys(client), name)

    before = redact(stored_config) if stored else {}
    diff = {
        "before": json.dumps(before, indent=2, sort_keys=True) if stored else "",
        "after": json.dumps(redact(desired), indent=2, sort_keys=True),
    }
    differs = stored is None or normalize(stored_config) != normalize(desired)
    if not differs:
        module.exit_json(changed=False, uuid=stored["uuid"], inbounds=inbound_map(stored), diff=diff)
    if module.check_mode:
        module.exit_json(
            changed=True,
            uuid=stored["uuid"] if stored else "",
            inbounds=inbound_map(stored) if stored else {},
            diff=diff,
        )

    if stored is None:
        client.post("/api/config-profiles", {"name": name, "config": desired})
    else:
        client.patch("/api/config-profiles", {"uuid": stored["uuid"], "config": desired})

    after = find_by(read_profiles(client), "name", name)
    warnings = []
    if after is None:
        module.fail_json(msg="profile %s is not listed by the Panel after the write" % name)
    if normalize(after.get("config")) != normalize(desired):
        paths = diff_paths(after.get("config"), desired)
        warnings.append(
            "Panel transformed profile %s at %s; the next run will PATCH again - report this mutation"
            % (name, ", ".join(paths) or "$")
        )
    for text in warnings:
        module.warn(text)
    module.exit_json(changed=True, uuid=after["uuid"], inbounds=inbound_map(after), diff=diff)


if __name__ == "__main__":
    main()
