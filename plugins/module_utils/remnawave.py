# -*- coding: utf-8 -*-
# Copyright (c) xvpn.remnawave contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Shared Remnawave Panel API client (stdlib and ansible.module_utils only)."""
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy
import json
import re
import socket

from ansible.module_utils.common.text.converters import to_text
from ansible.module_utils.six.moves.urllib.error import HTTPError
from ansible.module_utils.six.moves.urllib.parse import urlparse
from ansible.module_utils.urls import open_url

SUPPORTED_PANEL_SERIES = "3.4"

_SENSITIVE_KEY = re.compile(r"(?i)(private|secret|password|seed|token)")
_LOOPBACK_HOSTS = ("localhost", "::1")


class RemnawaveError(Exception):
    """A Panel error; the text carries the HTTP status and the Panel error code, never headers or the token."""

    def __init__(self, status, code, message):
        self.status = status
        self.code = code
        self.message = message
        super(RemnawaveError, self).__init__(
            "Panel API error: HTTP %s, code %s: %s" % (status, code or "-", message or "-")
        )


def common_argument_spec():
    return dict(
        api_url=dict(type="str", default="http://127.0.0.1:3000"),
        api_token_file=dict(type="path", required=True),
        timeout=dict(type="int", default=30),
        panel_version_check=dict(type="bool", default=True),
    )


def normalize(obj):
    """Key-order independent canonical JSON text."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def redact(obj):
    """Deep copy of obj with the values of secret-looking keys replaced by a marker."""
    if isinstance(obj, dict):
        return dict(
            (k, "<redacted>" if _SENSITIVE_KEY.search(str(k)) else redact(v)) for k, v in obj.items()
        )
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return copy.deepcopy(obj)


def _is_loopback(host):
    host = (host or "").strip("[]").lower()
    if host in _LOOPBACK_HOSTS:
        return True
    parts = host.split(".")
    return len(parts) == 4 and parts[0] == "127" and all(p.isdigit() for p in parts)


class RemnawaveClient(object):
    def __init__(self, module):
        self.module = module
        params = module.params
        self.api_url = (params.get("api_url") or "http://127.0.0.1:3000").rstrip("/")
        self.timeout = params.get("timeout") or 30
        self.version_check = params.get("panel_version_check", True)
        self._version_checked = False
        parsed = urlparse(self.api_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            module.fail_json(msg="api_url %s is not a valid http(s) URL" % self.api_url)
        if parsed.scheme == "http" and not _is_loopback(parsed.hostname):
            module.fail_json(msg="refusing to send the API token over plain http to a non-loopback host")
        self.token = self._read_token(params["api_token_file"])

    def _read_token(self, path):
        try:
            with open(path, "r") as handle:
                token = handle.read().strip()
        except (IOError, OSError):
            token = ""
        if not token:
            self.module.fail_json(msg="api_token_file %s is empty or unreadable" % path)
        return token

    def _headers(self):
        return {
            "Authorization": "Bearer " + self.token,
            "X-Forwarded-For": "127.0.0.1",
            "X-Forwarded-Proto": "https",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _raw(self, method, path, body=None):
        data = None if body is None else json.dumps(body)
        try:
            resp = open_url(
                self.api_url + path,
                method=method,
                data=data,
                headers=self._headers(),
                timeout=self.timeout,
                validate_certs=True,
            )
            text = to_text(resp.read())
        except HTTPError as exc:
            code, message = None, None
            try:
                payload = json.loads(to_text(exc.read()))
                code = payload.get("errorCode")
                message = payload.get("message")
            except (ValueError, AttributeError):
                pass
            raise RemnawaveError(exc.code, code, message)
        except (socket.timeout, TimeoutError):
            raise RemnawaveError(0, "TIMEOUT", "no answer from %s within %s s" % (self.api_url, self.timeout))
        except Exception as exc:  # urllib URLError, ConnectionError, SSL errors: text without request headers
            reason = getattr(exc, "reason", None) or exc.__class__.__name__
            if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason):
                raise RemnawaveError(0, "TIMEOUT", "no answer from %s within %s s" % (self.api_url, self.timeout))
            raise RemnawaveError(0, "CONNECTION", "cannot reach %s: %s" % (self.api_url, reason))
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError:
            raise RemnawaveError(0, "BAD_RESPONSE", "Panel answered with non-JSON content")

    def _ensure_supported_version(self):
        if self._version_checked or not self.version_check:
            return
        payload = self._raw("GET", "/api/system/metadata") or {}
        version = str((payload.get("response") or {}).get("version", ""))
        if not version.startswith(SUPPORTED_PANEL_SERIES + "."):
            self.module.fail_json(
                msg="Panel version %s is not supported by this collection (supported: %s.x); "
                "set panel_version_check: false to override at your own risk" % (version or "unknown", SUPPORTED_PANEL_SERIES)
            )
        self._version_checked = True

    def request(self, method, path, body=None):
        if method.upper() != "GET":
            self._ensure_supported_version()
        try:
            payload = self._raw(method.upper(), path, body)
        except RemnawaveError as exc:
            self.module.fail_json(msg=str(exc), status=exc.status, error_code=exc.code)
        if isinstance(payload, dict) and "response" in payload:
            return payload["response"]
        return payload

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, body=None):
        return self.request("POST", path, body if body is not None else {})

    def patch(self, path, body=None):
        return self.request("PATCH", path, body if body is not None else {})

    def delete(self, path, body=None):
        return self.request("DELETE", path, body)
