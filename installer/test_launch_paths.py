"""Regression: a nested plugin EXE must retain the user's actual config/DLC/save paths."""

import json, unittest
from types import SimpleNamespace
from unittest.mock import patch
import plugin_runtime, test_modmanager as fixture
import runtime_cache

m = fixture.m


class LaunchPathTests(unittest.TestCase):
    setUp = fixture.ManagerTests.setUp

    def check_route(self, backend, vanilla=False, plugin=False):
        build = self.repo / "build"
        config = build / "config"
        config.mkdir(exist_ok=True)
        for name, data in [
            ("graphics.ini", "rollback = on\nvolume = 37"),
            ("controllers.ini", "[keyboard]\n"),
            ("dlc.txt", "19\n"),
        ]:
            (config / name).write_text(data)
        profile = m.root(self.repo) / "profile/profile.json"
        data = json.loads(profile.read_text())
        data["backend"] = backend
        if plugin:
            data["plugin_runtime"] = dict(
                exe="modmanager_plugins/0123456789abcdef0123/ssbu_modmanager.exe",
                plugin_bin="plugin_bin",
                nro_bin="../../nro_bin_eh_o2",
            )
            exe = build / "work" / data["plugin_runtime"]["exe"]
            exe.parent.mkdir(parents=True)
            exe.write_bytes(b"SYNTHETIC PRIVATE HOST")
        profile.write_text(json.dumps(data))
        before = {p.name: p.read_bytes() for p in config.iterdir()}
        with patch.object(
            m.subprocess, "Popen", return_value=SimpleNamespace(pid=123)
        ) as launch, patch.object(runtime_cache, "plugin", return_value={}):
            m.play(self.repo, vanilla)
        args = launch.call_args.args[0]
        env = dict(
            args[i + 1].split("=", 1) for i, v in enumerate(args) if v == "--env"
        )
        self.assertEqual(str(config / "graphics.ini"), env["SSBU_GRAPHICS_CONFIG"])
        self.assertEqual(str(config / "controllers.ini"), env["SSBU_CONFIG"])
        self.assertEqual(str(config / "dlc.txt"), env["SSBU_DLC_LIST"])
        self.assertEqual(str(build / "saves"), args[args.index("--userdata") + 1])
        self.assertNotIn("SSBU_VOLUME", env)
        self.assertNotIn("SSBU_ONLINE", env)
        if plugin and not vanilla:
            self.assertIn("modmanager_plugins/", args[args.index("--exe") + 1])
            self.assertTrue(args[args.index("--exe") + 1].endswith("/ssbu_user.exe"))
            self.assertEqual("net", env["SSBU_RB_NET"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in config.iterdir()})

    def test_native_route(self):
        self.check_route("native")

    def test_arc_route(self):
        self.check_route("arcropolis")

    def test_nested_plugin_route(self):
        self.check_route("arcropolis", plugin=True)

    def test_vanilla_from_plugin_profile(self):
        self.check_route("arcropolis", vanilla=True, plugin=True)


if __name__ == "__main__":
    unittest.main()
