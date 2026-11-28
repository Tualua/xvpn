# Copyright (c) xvpn.remnawave contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
import os
import pathlib
import secrets
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".ansible" / "collections"))

from ansible_collections.xvpn.remnawave.plugins.module_utils import remnawave as rw  # noqa: E402
from tests.unit.fake_panel import FakePanel  # noqa: E402


class Failed(Exception):
    pass


class FakeModule(object):
    check_mode = False

    def __init__(self, **params):
        self.params = params

    def fail_json(self, **kwargs):
        raise Failed(kwargs.get("msg", ""))


class ClientTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.token = secrets.token_hex(16)
        self.token_file = os.path.join(self.tmp.name, "tok")
        with open(self.token_file, "w") as handle:
            handle.write(self.token + "\n")

    def client(self, url, **extra):
        params = {"api_url": url, "api_token_file": self.token_file, "timeout": 30, "panel_version_check": True}
        params.update(extra)
        return rw.RemnawaveClient(FakeModule(**params))

    def test_plain_http_non_loopback_refused(self):
        with self.assertRaises(Failed) as ctx:
            self.client("http://10.0.0.5:3000")
        self.assertIn("refusing to send the API token over plain http", str(ctx.exception))

    def test_loopback_and_https_accepted(self):
        for url in ("http://127.0.0.1:3000", "http://[::1]:3000", "http://localhost:3000", "https://panel.example.net"):
            self.client(url)

    def test_refusal_precedes_token_read(self):
        os.unlink(self.token_file)
        with self.assertRaises(Failed) as ctx:
            self.client("http://10.0.0.5:3000")
        self.assertIn("refusing", str(ctx.exception))

    def test_headers_on_every_request(self):
        with FakePanel() as fake:
            c = self.client(fake.url)
            c.get("/api/nodes")
            c.post("/api/nodes", {"a": 1})
            self.assertEqual(len(fake.requests), 2)
            for req in fake.requests:
                h = {k.lower(): v for k, v in req["headers"].items()}
                self.assertEqual(h["authorization"], "Bearer " + self.token)
                self.assertEqual(h["x-forwarded-for"], "127.0.0.1")
                self.assertEqual(h["x-forwarded-proto"], "https")  # X-Forwarded-Proto

    def test_panel_error_text(self):
        with FakePanel() as fake:
            fake.fail_next(400, "A034", "bad request")
            c = self.client(fake.url)
            with self.assertRaises(Failed) as ctx:
                c.get("/api/nodes")
            text = str(ctx.exception)
            self.assertIn("400", text)
            self.assertIn("A034", text)
            self.assertNotIn(self.token, text)

    def test_redact_and_normalize(self):
        out = rw.redact({"privateKey": "k", "a": {"secretKey": "s"}, "port": 443, "l": [{"apiToken": "t"}]})
        self.assertEqual(out["privateKey"], "<redacted>")
        self.assertEqual(out["a"]["secretKey"], "<redacted>")
        self.assertEqual(out["l"][0]["apiToken"], "<redacted>")
        self.assertEqual(out["port"], 443)
        self.assertEqual(rw.normalize({"a": 1, "b": {"c": 2, "d": 3}}), rw.normalize({"b": {"d": 3, "c": 2}, "a": 1}))

    def test_version_pin_refuses_unsupported_panel(self):
        with FakePanel() as fake:
            fake.panel_version = "3.5.0"
            c = self.client(fake.url)
            with self.assertRaises(Failed) as ctx:
                c.post("/api/x", {})
            self.assertIn("3.5.0", str(ctx.exception))
            self.assertIn("3.4", str(ctx.exception))
            self.assertEqual(fake.requests, [])

    def test_version_pin_once_per_client(self):
        with FakePanel() as fake:
            c = self.client(fake.url)
            c.post("/api/x", {})
            c.patch("/api/y", {})
            self.assertEqual(len(fake.meta_requests), 1)
            self.assertEqual([r["method"] for r in fake.requests], ["POST", "PATCH"])

    def test_panel_version_check_false(self):
        with FakePanel() as fake:
            fake.panel_version = "9.9.9"
            c = self.client(fake.url, panel_version_check=False)
            c.post("/api/x", {})
            self.assertEqual(fake.meta_requests, [])
            self.assertEqual(len(fake.requests), 1)

    def test_reads_send_no_metadata_request(self):
        with FakePanel() as fake:
            c = self.client(fake.url)
            c.get("/api/nodes")
            self.assertEqual(fake.meta_requests, [])

    def test_timeout_fails_fast_without_token(self):
        with FakePanel() as fake:
            fake.hang = True
            c = self.client(fake.url, timeout=2)
            start = time.time()
            with self.assertRaises(Failed) as ctx:
                c.get("/api/nodes")
            self.assertLess(time.time() - start, 10)
            text = str(ctx.exception)
            self.assertIn(fake.url, text)
            self.assertIn("2", text)
            self.assertNotIn(self.token, text)


if __name__ == "__main__":
    unittest.main()
