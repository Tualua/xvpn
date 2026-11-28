#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) xvpn.remnawave contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: remnawave_internal_squad
short_description: Add or remove inbounds of a Remnawave internal squad without touching other inbounds
version_added: "0.1.0"
description:
  - The Panel replaces the whole inbound set of a squad on update. The module therefore sends the union of the
    current inbounds and the requested ones (V(present)), or the current inbounds minus the requested ones
    (V(absent)), and only when that changes something. Inbounds of other profiles are never removed and a squad
    is never deleted.
  - The squad C(Default-Squad) is seeded by the Panel, always exists and cannot be created by the module.
extends_documentation_fragment:
  - xvpn.remnawave.remnawave
options:
  name:
    description: Squad name.
    type: str
    required: true
  config_profile:
    description: Name of the config profile that owns the inbounds.
    type: str
    required: true
  inbound_tags:
    description: Inbound tags (of O(config_profile)) to add or remove.
    type: list
    elements: str
    required: true
  state:
    description: V(present) adds the inbounds, V(absent) removes only the listed ones.
    type: str
    choices: [present, absent]
    default: present
  create:
    description: Create a missing squad (never the reserved C(Default-Squad)).
    type: bool
    default: true
notes:
  - "Check mode sends no write; a config profile that does not exist yet counts as an addition."
author:
  - xvpn.remnawave contributors
"""

EXAMPLES = r"""
- name: Put the node inbound into the default squad
  xvpn.remnawave.remnawave_internal_squad:
    api_token_file: /home/remnawave/secrets/api_token
    name: Default-Squad
    config_profile: node-1
    inbound_tags: [vless-reality-node-1]
"""

RETURN = r"""
uuid:
  description: UUID of the squad (empty when it would be created in check mode).
  returned: always
  type: str
changed:
  description: True exactly when a create or update was sent (or would be, in check mode).
  returned: always
  type: bool
diff:
  description: Before and after list of inbound tags/uuids of the squad.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.xvpn.remnawave.plugins.module_utils.remnawave import (
    RemnawaveClient,
    common_argument_spec,
    find_by,
    resolve_profile,
)

RESERVED_SQUAD = "Default-Squad"


def main():
    spec = common_argument_spec()
    spec.update(
        name=dict(type="str", required=True),
        config_profile=dict(type="str", required=True),
        inbound_tags=dict(type="list", elements="str", required=True),
        state=dict(type="str", default="present", choices=["present", "absent"]),
        create=dict(type="bool", default=True),
    )
    module = AnsibleModule(argument_spec=spec, supports_check_mode=True)
    p = module.params
    name = p["name"]
    client = RemnawaveClient(module)

    data = client.get("/api/internal-squads") or {}
    squad = find_by(data.get("internalSquads"), "name", name)
    profile_uuid, tag_map = resolve_profile(client, p["config_profile"])

    wanted = []
    missing_tags = []
    for tag in p["inbound_tags"]:
        if tag in tag_map:
            wanted.append(tag_map[tag])
        else:
            missing_tags.append(tag)
    if profile_uuid is not None and missing_tags:
        module.fail_json(msg="config profile %s has no inbound(s) %s" % (p["config_profile"], ", ".join(missing_tags)))
    if profile_uuid is None and not module.check_mode:
        module.fail_json(msg="config profile %s does not exist" % p["config_profile"])

    current = [i.get("uuid") for i in (squad or {}).get("inbounds") or []]
    label = dict((v, k) for k, v in tag_map.items())

    def names(uuids):
        return sorted(label.get(u, u) for u in uuids)

    if p["state"] == "present":
        desired = sorted(set(current) | set(wanted))
        adds = profile_uuid is None or desired != sorted(set(current))
    else:
        desired = sorted(set(current) - set(wanted))
        adds = desired != sorted(set(current))
    diff = {"before": "\n".join(names(current)), "after": "\n".join(names(desired)) if profile_uuid else "<new inbounds>"}

    if squad is None:
        if p["state"] == "absent":
            module.exit_json(changed=False, uuid="", diff={"before": "", "after": ""})
        if name == RESERVED_SQUAD or not p["create"]:
            module.fail_json(msg="squad %s does not exist" % name)
        if module.check_mode:
            module.exit_json(changed=True, uuid="", diff=diff)
        created = client.post("/api/internal-squads", {"name": name, "inbounds": desired}) or {}
        module.exit_json(changed=True, uuid=created.get("uuid", ""), diff=diff)

    if not adds:
        module.exit_json(changed=False, uuid=squad["uuid"], diff=diff)
    if not module.check_mode:
        client.patch("/api/internal-squads", {"uuid": squad["uuid"], "inbounds": desired})
    module.exit_json(changed=True, uuid=squad["uuid"], diff=diff)


if __name__ == "__main__":
    main()
