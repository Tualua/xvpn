#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) xvpn.remnawave contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: remnawave_node_secret
short_description: Fetch a Remnawave Node SECRET_KEY from the Panel
version_added: "0.1.0"
description:
  - Calls C(GET /api/keygen) of the Panel and returns the SECRET_KEY a Remnawave Node needs.
  - Every call yields a new key (a new node certificate), so fetch it once and keep it.
extends_documentation_fragment:
  - xvpn.remnawave.remnawave
options:
  guard_node_name:
    description:
      - When set, the Panel nodes are listed first (read-only, also in check mode).
      - If a node with this name exists, no key is requested and V(node_exists=true) is returned.
    type: str
notes:
  - "Check mode and guard_node_name: normal and no guard, keygen, changed; normal and guard and node exists, nodes GET only, unchanged, node_exists;
    normal and guard and no node, nodes GET then keygen, changed; check and no guard, no request, changed;
    check and guard and node exists, nodes GET only, unchanged, node_exists; check and guard and no node, nodes GET only, changed."
author:
  - xvpn.remnawave contributors
"""

EXAMPLES = r"""
- name: Fetch the node SECRET_KEY unless the node is already registered
  xvpn.remnawave.remnawave_node_secret:
    api_token_file: /home/remnawave/secrets/api_token
    guard_node_name: node-1
  register: node_secret
  no_log: true
"""

RETURN = r"""
secret_key:
  description: The node SECRET_KEY (sensitive, use no_log). Empty when not fetched.
  returned: always
  type: str
node_exists:
  description: Whether the guard found a node with the given name.
  returned: always
  type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.xvpn.remnawave.plugins.module_utils.remnawave import (
    RemnawaveClient,
    common_argument_spec,
)


def main():
    spec = common_argument_spec()
    spec.update(guard_node_name=dict(type="str"))
    module = AnsibleModule(argument_spec=spec, supports_check_mode=True)
    client = RemnawaveClient(module)
    guard = module.params.get("guard_node_name")

    exists = False
    if guard:
        nodes = client.get("/api/nodes") or []
        exists = any(isinstance(n, dict) and n.get("name") == guard for n in nodes)
        if exists:
            module.exit_json(changed=False, node_exists=True, secret_key="")
    if module.check_mode:
        module.exit_json(changed=True, node_exists=False, secret_key="")
    data = client.get("/api/keygen") or {}
    module.exit_json(changed=True, node_exists=False, secret_key=data.get("secretKey", ""))


if __name__ == "__main__":
    main()
