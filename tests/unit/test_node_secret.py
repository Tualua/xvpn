# Copyright (c) xvpn.remnawave contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
import json
import os
import pathlib
import secrets
import subprocess
import sys
import tempfile
import unittest

from tests.unit.fake_panel import FakePanel

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / "plugins" / "modules" / "remnawave_node_secret.py"


def run_module(args, check_mode=False):
    params = dict(args)
    if check_mode:
        params["_ansible_check_mode"] = True
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / ".ansible" / "collections") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(MODULE)],
        input=json.dumps({"ANSIBLE_MODULE_ARGS": params}),
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    return json.loads(proc.stdout)


class NodeSecretTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.token = secrets.token_hex(16)
        self.token_file = os.path.join(self.tmp.name, "tok")
        with open(self.token_file, "w") as handle:
            handle.write(self.token + "\n")

    def args(self, fake, **extra):
        out = {"api_url": fake.url, "api_token_file": self.token_file}
        out.update(extra)
        return out

    def test_normal_mode_one_keygen(self):
        with FakePanel() as fake:
            res = run_module(self.args(fake))
            self.assertFalse(res.get("failed"), res)
            self.assertTrue(res["changed"])
            self.assertTrue(res["secret_key"])
            self.assertFalse(res["node_exists"])
            self.assertEqual([(r["method"], r["path"]) for r in fake.requests], [("GET", "/api/keygen")])

    def test_check_mode_sends_no_request(self):
        with FakePanel() as fake:
            res = run_module(self.args(fake), check_mode=True)
            self.assertTrue(res["changed"])
            self.assertEqual(fake.requests, [])

    def test_empty_token_file_fails_without_request(self):
        with open(self.token_file, "w") as handle:
            handle.write("\n")
        with FakePanel() as fake:
            res = run_module(self.args(fake))
            self.assertTrue(res.get("failed"))
            self.assertIn("empty or unreadable", res["msg"])
            self.assertEqual(fake.requests, [])

    def test_guard_node_exists(self):
        with FakePanel() as fake:
            fake.resources["nodes"] = [{"name": "n1"}]
            res = run_module(self.args(fake, guard_node_name="n1"))
            self.assertTrue(res["node_exists"])
            self.assertFalse(res["changed"])
            self.assertEqual(res["secret_key"], "")
            self.assertEqual([r["path"] for r in fake.requests], ["/api/nodes"])

    def test_guard_no_such_node(self):
        with FakePanel() as fake:
            res = run_module(self.args(fake, guard_node_name="n1"))
            self.assertFalse(res["node_exists"])
            self.assertTrue(res["changed"])
            self.assertTrue(res["secret_key"])
            self.assertEqual([r["path"] for r in fake.requests], ["/api/nodes", "/api/keygen"])

    def test_check_mode_guard_node_exists(self):
        with FakePanel() as fake:
            fake.resources["nodes"] = [{"name": "n1"}]
            res = run_module(self.args(fake, guard_node_name="n1"), check_mode=True)
            self.assertTrue(res["node_exists"])
            self.assertFalse(res["changed"])
            self.assertEqual([r["path"] for r in fake.requests], ["/api/nodes"])

    def test_check_mode_guard_no_node(self):
        with FakePanel() as fake:
            res = run_module(self.args(fake, guard_node_name="n1"), check_mode=True)
            self.assertFalse(res["node_exists"])
            self.assertTrue(res["changed"])
            self.assertEqual([r["path"] for r in fake.requests], ["/api/nodes"])


if __name__ == "__main__":
    unittest.main()
