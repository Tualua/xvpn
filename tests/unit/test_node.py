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
from tests.unit.test_config_profile import base_config, TAG

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / "plugins" / "modules" / "remnawave_node.py"


def run_module(args, check_mode=False):
    params = dict(args)
    if check_mode:
        params["_ansible_check_mode"] = True
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / ".ansible" / "collections") + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(MODULE)], input=json.dumps({"ANSIBLE_MODULE_ARGS": params}),
        capture_output=True, text=True, env=env, timeout=60,
    )
    return json.loads(proc.stdout)


class NodeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.token_file = os.path.join(self.tmp.name, "tok")
        with open(self.token_file, "w") as handle:
            handle.write(secrets.token_hex(16) + "\n")

    def args(self, fake, **extra):
        out = {"api_url": fake.url, "api_token_file": self.token_file, "name": "node-1",
               "address": "n1.test", "config_profile": "node-1", "inbound_tags": [TAG],
               "wait_delay": 0, "wait_retries": 3}
        out.update(extra)
        return out

    def writes(self, fake):
        return [r for r in fake.requests if r["method"] != "GET"]

    def status_gets(self, fake):
        return [r for r in fake.requests if r["method"] == "GET" and r["path"].startswith("/api/nodes/")]

    def profile(self, fake):
        profile = fake.seed_profile("node-1", base_config())
        return profile["uuid"], fake.inbound_uuid("node-1", TAG)

    def test_create_posts_once_and_rerun_is_idempotent(self):
        with FakePanel() as fake:
            puuid, inb = self.profile(fake)
            res = run_module(self.args(fake, wait_connected=True))
            self.assertTrue(res["changed"], res)
            self.assertTrue(res["is_connected"], res)
            posts = [r for r in self.writes(fake) if r["method"] == "POST"]
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0]["json"], {
                "name": "node-1", "address": "n1.test", "port": 2222, "countryCode": "XX",
                "configProfile": {"activeConfigProfileUuid": puuid, "activeInbounds": [inb]}})
            fake.requests.clear()
            res = run_module(self.args(fake))
            self.assertFalse(res["changed"], res)
            self.assertEqual(self.writes(fake), [])

    def test_address_change_sends_one_patch(self):
        with FakePanel() as fake:
            self.profile(fake)
            run_module(self.args(fake))
            fake.requests.clear()
            res = run_module(self.args(fake, address="n2.test"))
            self.assertTrue(res["changed"], res)
            patch = self.writes(fake)
            self.assertEqual(len(patch), 1)
            self.assertEqual(patch[0]["method"], "PATCH")
            self.assertEqual(patch[0]["json"]["address"], "n2.test")
            self.assertEqual(set(patch[0]["json"]), {"uuid", "address"})

    def test_wait_succeeds_after_two_false_polls(self):
        with FakePanel() as fake:
            self.profile(fake)
            fake.connect_after = 3
            res = run_module(self.args(fake, wait_connected=True, wait_retries=5))
            self.assertFalse(res.get("failed"), res)
            self.assertEqual(len(self.status_gets(fake)), 3)

    def test_wait_timeout_message_pins_diagnostics(self):
        with FakePanel() as fake:
            self.profile(fake)
            fake.connect_after = None
            res = run_module(self.args(fake, wait_connected=True, wait_retries=3))
            self.assertTrue(res.get("failed"), res)
            self.assertEqual(len(self.status_gets(fake)), 3)
            for needle in ("not connected after", "lastStatusMessage=", "xvpn_node_panel_sources",
                           "remnanode.service", "xvpn_node_rekey"):
                self.assertIn(needle, res["msg"], needle)
            self.assertNotIn("delete", res["msg"])
            self.assertIn("connection refused", res["msg"])

    def test_duplicate_address_fails_before_post(self):
        with FakePanel() as fake:
            puuid, inb = self.profile(fake)
            fake.seed_node("other-node", "N1.Test", puuid, [inb])
            res = run_module(self.args(fake))
            self.assertTrue(res.get("failed"), res)
            self.assertIn("xvpn_node_address", res["msg"])
            self.assertEqual(self.writes(fake), [])

    def test_different_address_on_same_host_is_not_a_duplicate(self):
        with FakePanel() as fake:
            puuid, inb = self.profile(fake)
            fake.seed_node("other-node", "n9.test", puuid, [inb])
            res = run_module(self.args(fake))
            self.assertFalse(res.get("failed"), res)
            self.assertTrue(res["changed"])

    def test_check_mode_without_profile_would_create_and_never_polls(self):
        with FakePanel() as fake:
            res = run_module(self.args(fake, wait_connected=True), check_mode=True)
            self.assertTrue(res["changed"], res)
            self.assertEqual(self.writes(fake), [])
            self.assertEqual(self.status_gets(fake), [])

    def test_check_mode_existing_node_reports_drift_without_write(self):
        with FakePanel() as fake:
            self.profile(fake)
            run_module(self.args(fake))
            fake.requests.clear()
            res = run_module(self.args(fake, address="n3.test", wait_connected=True), check_mode=True)
            self.assertTrue(res["changed"], res)
            self.assertIn("n3.test", res["diff"]["after"])
            self.assertEqual(self.writes(fake), [])
            self.assertEqual(self.status_gets(fake), [])

    def test_absent_deletes_and_polls_until_gone(self):
        with FakePanel() as fake:
            self.profile(fake)
            run_module(self.args(fake))
            fake.requests.clear()
            res = run_module(self.args(fake, state="absent"))
            self.assertTrue(res["changed"], res)
            self.assertEqual([r["method"] for r in self.writes(fake)], ["DELETE"])
            lists = [r for r in fake.requests if r["method"] == "GET" and r["path"] == "/api/nodes"]
            self.assertGreaterEqual(len(lists), 3)
            self.assertEqual(fake.resources["nodes"], [])
            self.assertFalse(run_module(self.args(fake, state="absent"))["changed"])


if __name__ == "__main__":
    unittest.main()
