# Copyright (c) xvpn.remnawave contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Stdlib fake Remnawave Panel for the module unit tests."""
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakePanel(object):
    def __init__(self):
        self.resources = {"nodes": []}
        self.requests = []
        self.meta_requests = []
        self.panel_version = "3.4.11"
        self._errors = []
        self.hang = False
        self.server = None
        self.thread = None

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
                if self.command == "GET" and self.path == "/api/nodes":
                    return self._send(200, {"response": list(panel.resources["nodes"])})
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
