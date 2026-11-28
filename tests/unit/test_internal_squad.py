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
MODULE = ROOT / "plugins" / "modules" / "remnawave_internal_squad.py"


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


class SquadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.token_file = os.path.join(self.tmp.name, "tok")
        with open(self.token_file, "w") as handle:
            handle.write(secrets.token_hex(16) + "\n")

    def args(self, fake, **extra):
        out = {"api_url": fake.url, "api_token_file": self.token_file, "name": "Default-Squad",
               "config_profile": "node-1", "inbound_tags": [TAG]}
        out.update(extra)
        return out

    def writes(self, fake):
        return [r for r in fake.requests if r["method"] != "GET"]

    def seeded(self, fake):
        fake.seed_profile("node-1", base_config())
        ours = fake.inbound_uuid("node-1", TAG)
        fake.seed_profile("other", base_config(inbounds=[dict(base_config()["inbounds"][0], tag="foreign")]))
        foreign = fake.inbound_uuid("other", "foreign")
        return ours, foreign

    def test_union_keeps_foreign_inbound_and_is_idempotent(self):
        with FakePanel() as fake:
            ours, foreign = self.seeded(fake)
            squad = fake.seed_squad("Default-Squad", [foreign])
            res = run_module(self.args(fake))
            self.assertTrue(res["changed"], res)
            patch = [r for r in self.writes(fake) if r["method"] == "PATCH"]
            self.assertEqual(len(patch), 1)
            self.assertEqual(patch[0]["json"], {"uuid": squad["uuid"], "inbounds": sorted([foreign, ours])})
            fake.requests.clear()
            res = run_module(self.args(fake))
            self.assertFalse(res["changed"], res)
            self.assertEqual(self.writes(fake), [])

    def test_absent_removes_only_listed_inbound(self):
        with FakePanel() as fake:
            ours, foreign = self.seeded(fake)
            fake.seed_squad("Default-Squad", [foreign, ours])
            res = run_module(self.args(fake, state="absent"))
            self.assertTrue(res["changed"], res)
            patch = [r for r in self.writes(fake) if r["method"] == "PATCH"]
            self.assertEqual(patch[0]["json"]["inbounds"], [foreign])
            fake.requests.clear()
            self.assertFalse(run_module(self.args(fake, state="absent"))["changed"])
            self.assertEqual(self.writes(fake), [])

    def test_reserved_default_squad_is_never_created(self):
        with FakePanel() as fake:
            self.seeded(fake)
            res = run_module(self.args(fake))
            self.assertTrue(res.get("failed"), res)
            self.assertIn("does not exist", res["msg"])
            self.assertEqual(self.writes(fake), [])

    def test_missing_custom_squad_is_created(self):
        with FakePanel() as fake:
            ours, _ = self.seeded(fake)
            res = run_module(self.args(fake, name="lan-trusted"))
            self.assertTrue(res["changed"], res)
            post = [r for r in self.writes(fake) if r["method"] == "POST"]
            self.assertEqual(post[0]["json"], {"name": "lan-trusted", "inbounds": [ours]})
            fake.requests.clear()
            self.assertFalse(run_module(self.args(fake, name="lan-trusted"))["changed"])

    def test_check_mode_writes_nothing_and_missing_profile_would_add(self):
        with FakePanel() as fake:
            fake.seed_squad("Default-Squad", [])
            res = run_module(self.args(fake), check_mode=True)
            self.assertTrue(res["changed"], res)
            self.assertEqual(self.writes(fake), [])
            ours, foreign = self.seeded(fake)
            res = run_module(self.args(fake), check_mode=True)
            self.assertTrue(res["changed"], res)
            self.assertEqual(self.writes(fake), [])
            self.assertIn(TAG, res["diff"]["after"])


if __name__ == "__main__":
    unittest.main()
