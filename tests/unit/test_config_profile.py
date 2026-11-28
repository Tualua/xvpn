# Copyright (c) xvpn.remnawave contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
import copy
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys
import tempfile
import unittest

from tests.unit.fake_panel import FakePanel

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / "plugins" / "modules" / "remnawave_config_profile.py"
TAG = "vless-reality-n1"
BLOCK = ["10.0.0.0/8", "192.168.0.0/16"]


def base_config(**changes):
    cfg = {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "tag": TAG,
                "port": 443,
                "protocol": "vless",
                "settings": {"clients": [], "decryption": "none"},
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {"show": False, "target": "127.0.0.1:8443", "xver": 0, "serverNames": ["n1.test"]},
                },
            }
        ],
        "outbounds": [
            {"tag": "DIRECT", "protocol": "freedom", "settings": {}},
            {"tag": "BLOCK", "protocol": "blackhole"},
        ],
        "routing": {"rules": [{"type": "field", "ip": list(BLOCK), "outboundTag": "BLOCK"}]},
    }
    cfg.update(changes)
    return cfg


def managed(**extra):
    entry = {"tag": TAG, "target": "127.0.0.1:8443", "server_names": ["n1.test"]}
    entry.update(extra)
    return [entry]


def run_module(args, check_mode=False, diff=False):
    params = dict(args)
    if check_mode:
        params["_ansible_check_mode"] = True
    if diff:
        params["_ansible_diff"] = True
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
    res = json.loads(proc.stdout)
    res["_raw"] = proc.stdout
    return res


class ConfigProfileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.token_file = os.path.join(self.tmp.name, "tok")
        with open(self.token_file, "w") as handle:
            handle.write(secrets.token_hex(16) + "\n")

    def args(self, fake, **extra):
        out = {
            "api_url": fake.url,
            "api_token_file": self.token_file,
            "name": "node-1",
            "config": base_config(),
            "reality_inbounds": managed(),
            "required_block_cidrs": list(BLOCK),
        }
        out.update(extra)
        return out

    def writes(self, fake):
        return [r for r in fake.requests if r["method"] in ("POST", "PATCH", "DELETE")]

    def count(self, fake, method, path):
        return len([r for r in fake.requests if r["method"] == method and r["path"] == path])

    def stored(self, fake):
        return fake.resources["config_profiles"][0]["config"]

    def stored_real(self, fake):
        return self.stored(fake)["inbounds"][0]["streamSettings"]["realitySettings"]

    def assert_no_secret(self, fake, res):
        for profile in fake.resources["config_profiles"]:
            for inbound in profile["config"].get("inbounds") or []:
                key = (inbound.get("streamSettings") or {}).get("realitySettings", {}).get("privateKey")
                if key:
                    self.assertNotIn(key, res["_raw"])

    # --- tracer: create once, converged re-run is silent ---

    def test_create_generates_keys_once(self):
        with FakePanel() as fake:
            res = run_module(self.args(fake))
            self.assertFalse(res.get("failed"), res)
            self.assertTrue(res["changed"])
            self.assertEqual(self.count(fake, "GET", "/api/system/tools/x25519/generate"), 1)
            post = [r for r in fake.requests if r["method"] == "POST" and r["path"] == "/api/config-profiles"]
            self.assertEqual(len(post), 1)
            real = post[0]["json"]["config"]["inbounds"][0]["streamSettings"]["realitySettings"]
            self.assertTrue(real["privateKey"].startswith("key"))
            self.assertEqual(len(real["shortIds"]), 2)
            for sid in real["shortIds"]:
                self.assertRegex(sid, r"^[0-9a-f]{16}$")
            self.assertNotIn("publicKey", real)
            self.assertIn(TAG, res["inbounds"])
            self.assertTrue(res["uuid"])
            self.assert_no_secret(fake, res)
            self.assertNotIn(real["privateKey"], res["_raw"])

    def test_rerun_on_stored_profile_is_a_noop(self):
        with FakePanel() as fake:
            run_module(self.args(fake))
            fake.requests.clear()
            res = run_module(self.args(fake))
            self.assertFalse(res["changed"], res)
            self.assertEqual(self.writes(fake), [])
            self.assertEqual(self.count(fake, "GET", "/api/system/tools/x25519/generate"), 0)
            self.assertNotIn("warnings", res)

    # --- drift and redaction ---

    def test_drift_one_patch_keeps_keys_and_redacts_diff(self):
        with FakePanel() as fake:
            run_module(self.args(fake))
            keys_before = copy.deepcopy(self.stored_real(fake))
            fake.requests.clear()
            res = run_module(self.args(fake, config=base_config(log={"loglevel": "debug"})), diff=True)
            self.assertTrue(res["changed"], res)
            patches = [r for r in fake.requests if r["method"] == "PATCH"]
            self.assertEqual(len(patches), 1)
            sent = patches[0]["json"]["config"]["inbounds"][0]["streamSettings"]["realitySettings"]
            self.assertEqual(sent["privateKey"], keys_before["privateKey"])
            self.assertEqual(sent["shortIds"], keys_before["shortIds"])
            self.assertEqual(self.count(fake, "GET", "/api/system/tools/x25519/generate"), 0)
            self.assertIn("<redacted>", res["diff"]["before"])
            self.assertIn("<redacted>", res["diff"]["after"])
            self.assertNotIn(keys_before["privateKey"], res["_raw"])

    # --- D-03: keys from an override never reach the Panel ---

    def override_config(self):
        cfg = base_config()
        real = cfg["inbounds"][0]["streamSettings"]["realitySettings"]
        real["privateKey"] = "from-override"
        real["publicKey"] = "from-override-pub"
        real["shortIds"] = ["ab12"]
        return cfg

    def test_override_keys_discarded_on_create(self):
        with FakePanel() as fake:
            res = run_module(self.args(fake, config=self.override_config()))
            self.assertFalse(res.get("failed"), res)
            blob = json.dumps(fake.requests)
            self.assertNotIn("from-override", blob)
            self.assertNotIn("ab12", blob)
            real = self.stored_real(fake)
            self.assertTrue(real["privateKey"].startswith("key"))
            self.assertEqual(len(real["shortIds"]), 2)
            self.assertNotIn("from-override", res["_raw"])

    def test_override_keys_discarded_on_update(self):
        with FakePanel() as fake:
            run_module(self.args(fake))
            fake.requests.clear()
            res = run_module(self.args(fake, config=self.override_config()))
            self.assertFalse(res["changed"], res)
            self.assertEqual(self.writes(fake), [])
            self.assertNotIn("from-override", json.dumps(fake.requests))
            self.assertNotIn("from-override", res["_raw"])

    # --- convergence against Panel-side mutations ---

    def test_server_names_comma_list_converges(self):
        cfg = base_config()
        cfg["inbounds"][0]["streamSettings"]["realitySettings"]["serverNames"] = ["a.test,b.test"]
        with FakePanel() as fake:
            run_module(self.args(fake, config=cfg, reality_inbounds=[{"tag": TAG}]))
            self.assertEqual(self.stored_real(fake)["serverNames"], ["a.test", "b.test"])
            fake.requests.clear()
            res = run_module(self.args(fake, config=cfg, reality_inbounds=[{"tag": TAG}]))
            self.assertFalse(res["changed"], res)
            self.assertEqual(self.writes(fake), [])

    def complex_config(self):
        cfg = base_config()
        first = cfg["inbounds"][0]
        first["settings"]["clients"] = [{"id": "00000000-0000-0000-0000-000000000001"}]
        first["streamSettings"]["realitySettings"]["serverNames"] = ["a.test,b.test", "a.test"]
        second = copy.deepcopy(first)
        second["tag"] = "vless-reality-second"
        second["port"] = 8443
        cfg["inbounds"].append(second)
        return cfg

    def test_second_apply_of_complex_config_is_a_noop(self):
        entries = [{"tag": TAG}, {"tag": "vless-reality-second"}]
        with FakePanel() as fake:
            seed = base_config(log={"loglevel": "debug"})
            seed["inbounds"][0]["streamSettings"]["realitySettings"]["privateKey"] = "stored-key-value"
            seed["inbounds"][0]["streamSettings"]["realitySettings"]["shortIds"] = ["0123456789abcdef"]
            fake.seed_profile("node-1", seed)
            first = run_module(self.args(fake, config=self.complex_config(), reality_inbounds=entries))
            self.assertFalse(first.get("failed"), first)
            self.assertNotIn("warnings", first)
            fake.requests.clear()
            res = run_module(self.args(fake, config=self.complex_config(), reality_inbounds=entries))
            self.assertFalse(res["changed"], res)
            self.assertEqual(self.writes(fake), [])
            self.assertEqual(self.count(fake, "GET", "/api/system/tools/x25519/generate"), 0)

    def converge_after_mutation(self, mutation, config):
        """Seed a profile as the UI would store it, apply a config the Panel will transform on update, converge."""
        with FakePanel() as fake:
            fake.mutations = {mutation}
            seed = base_config(log={"loglevel": "debug"})
            seed["inbounds"][0]["streamSettings"]["realitySettings"]["privateKey"] = "stored-key-value"
            seed["inbounds"][0]["streamSettings"]["realitySettings"]["shortIds"] = ["0123456789abcdef"]
            fake.seed_profile("node-1", seed)
            first = run_module(self.args(fake, config=config(), reality_inbounds=[{"tag": TAG}]))
            self.assertFalse(first.get("failed"), first)
            self.assertTrue(first["changed"])
            self.assertEqual([r["method"] for r in fake.requests if r["method"] == "PATCH"], ["PATCH"])
            self.assertNotIn("warnings", first, "read-back mismatch: apply_panel_mutations lacks %s" % mutation)
            fake.requests.clear()
            second = run_module(self.args(fake, config=config(), reality_inbounds=[{"tag": TAG}]))
            self.assertFalse(second["changed"], second)
            self.assertEqual(self.writes(fake), [])
            return fake

    def test_panel_mutation_clients_cleanup(self):
        def config():
            cfg = base_config()
            cfg["inbounds"][0]["settings"]["clients"] = [{"id": "00000000-0000-0000-0000-000000000001"}]
            return cfg

        fake = self.converge_after_mutation("clients_cleanup", config)
        self.assertEqual(self.stored(fake)["inbounds"][0]["settings"]["clients"], [])

    def test_panel_mutation_clients_cleanup_creates_settings(self):
        def config():
            cfg = base_config()
            del cfg["inbounds"][0]["settings"]
            return cfg

        fake = self.converge_after_mutation("clients_cleanup", config)
        self.assertEqual(self.stored(fake)["inbounds"][0]["settings"], {"clients": []})

    def test_panel_mutation_server_names(self):
        def config():
            cfg = base_config()
            cfg["inbounds"][0]["streamSettings"]["realitySettings"]["serverNames"] = ["a.test, b.test", "b.test"]
            return cfg

        fake = self.converge_after_mutation("server_names", config)
        self.assertEqual(self.stored_real(fake)["serverNames"], ["a.test", "b.test"])

    def test_panel_mutation_sorted_keys(self):
        fake = self.converge_after_mutation("sorted_keys", base_config)
        self.assertEqual(list(self.stored(fake))[0], "log")

    def test_panel_mutation_outbounds_required(self):
        with FakePanel() as fake:
            fake.mutations = {"outbounds_required"}
            fake.seed_profile("node-1", base_config(log={"loglevel": "debug"}))
            cfg = base_config()
            del cfg["outbounds"]
            res = run_module(self.args(fake, config=cfg, reality_inbounds=[]))
            self.assertTrue(res.get("failed"))
            self.assertIn("outbounds", res["msg"])
            self.assertEqual(self.writes(fake), [])

    def test_read_back_mismatch_warns_with_path_and_no_key(self):
        with FakePanel() as fake:
            fake.extra_transform = True
            res = run_module(self.args(fake))
            self.assertFalse(res.get("failed"), res)
            self.assertTrue(res["changed"])
            text = json.dumps(res.get("warnings") or [])
            self.assertIn("inbounds[0].sniffing", text)
            self.assertIn("will PATCH again", text)
            self.assertNotIn(self.stored_real(fake)["privateKey"], res["_raw"])

    # --- enforcement before any write ---

    def test_override_dropping_block_rule_fails(self):
        cfg = base_config()
        cfg["routing"]["rules"] = [{"type": "field", "ip": ["10.0.0.0/8"], "outboundTag": "BLOCK"}]
        with FakePanel() as fake:
            res = run_module(self.args(fake, config=cfg))
            self.assertTrue(res.get("failed"))
            self.assertIn("xvpn_node_profile_override", res["msg"])
            self.assertIn("BLOCK", res["msg"])
            self.assertEqual(self.writes(fake), [])

    def test_override_changing_server_names_fails(self):
        cfg = base_config()
        cfg["inbounds"][0]["streamSettings"]["realitySettings"]["serverNames"] = ["evil.test"]
        with FakePanel() as fake:
            res = run_module(self.args(fake, config=cfg))
            self.assertTrue(res.get("failed"))
            self.assertIn("xvpn_node_profile_override", res["msg"])
            self.assertIn("serverNames", res["msg"])
            self.assertEqual(self.writes(fake), [])

    def test_override_changing_target_fails(self):
        cfg = base_config()
        cfg["inbounds"][0]["streamSettings"]["realitySettings"]["target"] = "1.2.3.4:443"
        with FakePanel() as fake:
            res = run_module(self.args(fake, config=cfg))
            self.assertTrue(res.get("failed"))
            self.assertIn("xvpn_node_profile_override", res["msg"])
            self.assertIn("target", res["msg"])
            self.assertEqual(self.writes(fake), [])

    def test_profile_name_rule(self):
        with FakePanel() as fake:
            res = run_module(self.args(fake, name="a.b"))
            self.assertTrue(res.get("failed"))
            self.assertIn("^[A-Za-z0-9_ -]{2,30}$", res["msg"])
            self.assertEqual(fake.requests, [])

    # --- key loss ---

    def test_stored_inbound_without_private_key_fails(self):
        with FakePanel() as fake:
            run_module(self.args(fake))
            fake.strip_private_key = True
            fake.requests.clear()
            res = run_module(self.args(fake))
            self.assertTrue(res.get("failed"))
            self.assertIn("delete the profile in the Panel to re-key", res["msg"])
            self.assertEqual(self.writes(fake), [])

    # --- check mode and absent ---

    def test_check_mode_on_missing_profile(self):
        with FakePanel() as fake:
            res = run_module(self.args(fake), check_mode=True, diff=True)
            self.assertTrue(res["changed"], res)
            self.assertEqual(self.writes(fake), [])
            self.assertEqual(self.count(fake, "GET", "/api/system/tools/x25519/generate"), 0)
            self.assertIn("<generated on apply>", res["diff"]["after"])

    def test_check_mode_on_drift_sends_nothing(self):
        with FakePanel() as fake:
            run_module(self.args(fake))
            fake.requests.clear()
            res = run_module(self.args(fake, config=base_config(log={"loglevel": "debug"})), check_mode=True)
            self.assertTrue(res["changed"])
            self.assertEqual(self.writes(fake), [])

    def test_state_absent_deletes_once(self):
        with FakePanel() as fake:
            run_module(self.args(fake))
            fake.requests.clear()
            res = run_module(self.args(fake, state="absent", config=None))
            self.assertTrue(res["changed"], res)
            self.assertEqual([r["method"] for r in self.writes(fake)], ["DELETE"])
            self.assertEqual(fake.resources["config_profiles"], [])

    def test_state_absent_on_missing_profile(self):
        with FakePanel() as fake:
            res = run_module(self.args(fake, state="absent", config=None))
            self.assertFalse(res["changed"])
            self.assertEqual(self.writes(fake), [])

    def test_new_inbound_in_existing_profile_generates_only_its_keys(self):
        entries = [{"tag": TAG}, {"tag": "vless-reality-second"}]
        with FakePanel() as fake:
            run_module(self.args(fake, reality_inbounds=[{"tag": TAG}]))
            keys_before = copy.deepcopy(self.stored_real(fake))
            second = copy.deepcopy(base_config()["inbounds"][0])
            second["tag"] = "vless-reality-second"
            second["port"] = 8443
            cfg = base_config()
            cfg["inbounds"].append(second)
            fake.requests.clear()
            res = run_module(self.args(fake, config=cfg, reality_inbounds=entries))
            self.assertTrue(res["changed"], res)
            self.assertEqual(self.count(fake, "GET", "/api/system/tools/x25519/generate"), 1)
            inbounds = self.stored(fake)["inbounds"]
            self.assertEqual(inbounds[0]["streamSettings"]["realitySettings"]["privateKey"], keys_before["privateKey"])
            self.assertNotEqual(inbounds[1]["streamSettings"]["realitySettings"]["privateKey"], keys_before["privateKey"])
            self.assertTrue(re.match(r"^[0-9a-f]{16}$", inbounds[1]["streamSettings"]["realitySettings"]["shortIds"][0]))


if __name__ == "__main__":
    unittest.main()
