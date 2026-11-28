# -*- coding: utf-8 -*-
# Copyright (c) xvpn.remnawave contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
options:
  api_url:
    description:
      - Base URL of the Remnawave Panel API.
      - Plain C(http) is accepted only for a loopback host; the API token is never sent over http to another host.
    type: str
    default: http://127.0.0.1:3000
  api_token_file:
    description:
      - Path of a file holding the Panel API token. The file is read on the host the module runs on.
      - The token itself is never a module argument.
    type: path
    required: true
  timeout:
    description:
      - Timeout of one API request in seconds.
    type: int
    default: 30
  panel_version_check:
    description:
      - Before the first write request the client reads C(/api/system/metadata) and refuses a Panel outside the supported 3.4.x series.
      - Set to V(false) to override the check at your own risk.
    type: bool
    default: true
"""
