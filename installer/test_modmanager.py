"""Synthetic transaction and import tests; no game data and no game launches."""

import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location(
    "manager_under_test", Path(__file__).with_name("modmanager.py")
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ManagerTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / "test-scratch"
        scratch.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="Manager tests ", dir=scratch)
        assert Path(self.tmp.name).resolve().is_relative_to(scratch.resolve())
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "Game with spaces"
        self.repo.mkdir()
        self.idle = patch.object(m, "idle", return_value=None)
        self.idle.start()
        self.addCleanup(self.idle.stop)

        def make_sd(repo, destination):
            (destination / "atmosphere").mkdir(parents=True)
            (destination / "ultimate/arcropolis/resources").mkdir(parents=True)

        for attr, value in [
            ("ensure", lambda repo: {}),
            ("valid", lambda *args: {}),
            ("make_sd", make_sd),
        ]:
            stub = patch.object(m.arc_backend, attr, side_effect=value)
            stub.start()
            self.addCleanup(stub.stop)

        def put(path, text):
            p = self.repo / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)

        put("scripts/run.py", "# --env --log --userdata")
        put("runtime/loose_host.c", "SSBU_LOOSE_FILES SSBU_LOOSE_FILES=0")
        put("runtime/loose_files.c", "SSBU_CHARACTERS SSBU_LOOSE_RAW lf_rawcopy")
        put(
            "build/state.json",
            json.dumps(
                dict(
                    game_version="13.0.5",
                    dump=dict(romfs=str(self.repo / "build/dump/romfs")),
                )
            ),
        )
        put(
            "build/work/ssbu_native.exe",
            "SYNTHETIC SSBU_LOOSE_FILES SSBU_LOOSE_RAW [loose] served",
        )
        put("build/work/ssbu_modmanager.exe", "SYNTHETIC PRIVATE LOADER HOST")
        put("build/work/ssbu_game_modmanager.dll", "SYNTHETIC PRIVATE LOADER DLL")
        for path in [
            "build/work/ssbu_game_eh_o1.dll",
            "build/work/SDL3.dll",
            "build/work/ssbu_glslang.dll",
            "build/binaries/13.0.5/main.elf",
        ]:
            put(path, "SYNTHETIC fixture")
        put("build/saves/save.bin", "original save")
        put("Play SSBU.bat", "original starter")
        self.arc = self.repo / "build/dump/romfs/data.arc"
        put(
            "build/dump/romfs/data.arc",
            json.dumps(
                {
                    "ui/replace/a.bntx": dict(info_index=1),
                    "ui/replace/b.bntx": dict(info_index=2),
                }
            ),
        )
        put(
            "tools/nro/arc_extract.py",
            """
import json,zlib
def hash40(s): return zlib.crc32(s.lower().encode())
class Arc:
 def __init__(self,p):
  self.f=open(p,'rb');self.data=json.load(self.f);self.names=list(self.data);self.n_path=len(self.names)
 def path_index_from_hash(self,h):
  return next((i for i,p in enumerate(self.names) if hash40(p)==h),None)
 def file_record(self,i):
  r=dict(decomp_size=100,info_flags=16,data_flags=1);r.update(self.data[self.names[i]]);return r
 def file_path(self,i): return ((hash40(self.names[i]),0),None,None,None)
""",
        )
        m.setup(self.repo)

    def mod(self, name="New skin", path="ui/replace/a.bntx", content="asset A"):
        folder = Path(self.tmp.name) / name
        file = folder / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)
        (folder / "info.toml").write_text('display_name="' + name + '"')
        return folder

    def test_folder_duplicate_disable_remove_and_undo(self):
        source = self.mod()
        plan = m.inspect(self.repo, source)
        result = m.install(self.repo, source, plan["token"])
        self.assertEqual(1, result["result"]["files"])
        key = plan["id"]
        self.assertEqual(1, len(m.install(self.repo, source)["state"]["mods"]))
        m.change(self.repo, key, "enable", False)
        self.assertFalse(m.listing(self.repo)["mods"][0]["enabled"])
        self.assertEqual({}, m.files(m.root(self.repo) / "profile/assets"))
        m.undo(self.repo)
        self.assertTrue(m.listing(self.repo)["mods"][0]["enabled"])
        m.change(self.repo, key, "remove")
        self.assertEqual([], m.listing(self.repo)["mods"])
        m.undo(self.repo)
        self.assertEqual(key, m.listing(self.repo)["mods"][0]["id"])
        self.assertEqual(
            "original save", (self.repo / "build/saves/save.bin").read_text()
        )
        self.assertEqual("original starter", (self.repo / "Play SSBU.bat").read_text())

    def test_zip_and_path_with_spaces(self):
        source = self.mod()
        archive = Path(self.tmp.name) / "My mod archive.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for f in source.rglob("*"):
                if f.is_file():
                    z.write(f, "wrapper/mod/" + f.relative_to(source).as_posix())
        plan = m.inspect(self.repo, archive)
        m.install(self.repo, archive, plan["token"])
        self.assertEqual(1, len(m.listing(self.repo)["mods"]))

    def test_conflict_refuses_activation_preserves_profile(self):
        first = self.mod("First")
        m.install(self.repo, first)
        before = m.files(m.root(self.repo) / "profile")
        second = self.mod("Second", content="different")
        with self.assertRaisesRegex(ValueError, "Konflikt"):
            m.install(self.repo, second)
        self.assertEqual(before, m.files(m.root(self.repo) / "profile"))
        self.assertEqual(1, len(m.listing(self.repo)["mods"]))

    def test_source_changed_after_review(self):
        source = self.mod()
        plan = m.inspect(self.repo, source)
        (source / "ui/replace/a.bntx").write_text("changed after preview")
        with self.assertRaisesRegex(ValueError, "seit der Vorschau"):
            m.install(self.repo, source, plan["token"])
        self.assertEqual([], m.listing(self.repo)["mods"])

    def test_plugin_outside_asset_root_rejected(self):
        source = self.mod()
        (source / "libplugin.nro").write_text("synthetic code")
        with self.assertRaisesRegex(ValueError, "Plugin-/Programmcode"):
            m.inspect(self.repo, source)

    def test_archive_traversal_rejected(self):
        source = Path(self.tmp.name) / "unsafe.zip"
        with zipfile.ZipFile(source, "w") as z:
            z.writestr("../escape.txt", "bad")
        with self.assertRaises(ValueError):
            m.inspect(self.repo, source)
        self.assertFalse((m.root(self.repo) / "incoming/escape.txt").exists())

    def test_windows_device_name_rejected(self):
        source = Path(self.tmp.name) / "unsafe.zip"
        with zipfile.ZipFile(source, "w") as z:
            z.writestr("CON.txt", "bad")
        with self.assertRaisesRegex(ValueError, "Windows-Pfad"):
            m.inspect(self.repo, source)

    def test_new_file_is_preserved_for_arcropolis(self):
        plan = m.inspect(
            self.repo, self.mod(path="fighter/foo/model/body/c03/new.nutexb")
        )
        self.assertEqual("arcropolis", plan["backend"])
        self.assertEqual(
            "fighter/foo/model/body/c03/new.nutexb", plan["entries"][0]["path"]
        )

    def test_shared_mesh_uses_path_not_canonical_entry(self):
        self.arc.write_text(
            json.dumps(
                {
                    "fighter/foo/model/body/c00/model.numshb": dict(info_index=7),
                    "fighter/bar/model/body/c00/model.numshb": dict(info_index=7),
                }
            )
        )
        source = self.mod(path="fighter/foo/model/body/c00/model.numshb")
        plan = m.inspect(self.repo, source)
        self.assertEqual(
            "path:fighter/foo/model/body/c00/model.numshb", plan["entries"][0]["info"]
        )
        self.assertEqual([], plan["ignored"])

    def test_profile_tampering_preserved(self):
        source = self.mod()
        key = m.inspect(self.repo, source)["id"]
        m.install(self.repo, source)
        file = next((m.root(self.repo) / "profile/ultimate/mods").rglob("*.bntx"))
        file.write_text("manual change")
        with self.assertRaisesRegex(ValueError, "ausserhalb"):
            m.change(self.repo, key, "enable", False)
        self.assertEqual("manual change", file.read_text())

    def test_commit_failure_restores_previous_state(self):
        source = self.mod()
        key = m.inspect(self.repo, source)["id"]
        m.install(self.repo, source)
        before = m.files(m.root(self.repo) / "profile")
        state = (m.root(self.repo) / "state.json").read_bytes()
        with patch.object(
            m.os, "replace", side_effect=OSError("simulated commit failure")
        ):
            with self.assertRaises(OSError):
                m.change(self.repo, key, "enable", False)
        self.assertEqual(before, m.files(m.root(self.repo) / "profile"))
        self.assertEqual(state, (m.root(self.repo) / "state.json").read_bytes())

    def test_busy_game_blocks_import(self):
        source = self.mod()
        with patch.object(m, "idle", side_effect=ValueError("OpenSmash laeuft noch")):
            with self.assertRaisesRegex(ValueError, "laeuft noch"):
                m.install(self.repo, source)
        self.assertEqual([], m.listing(self.repo)["mods"])

    def test_child_asset_directory_refused(self):
        source = self.mod()
        with self.assertRaisesRegex(ValueError, "Mod-Ordner ueber"):
            m.inspect(self.repo, source / "ui")

    def test_full_uninstall_preserves_backup_and_originals(self):
        source = self.mod()
        m.install(self.repo, source)
        result = m.uninstall(self.repo)
        self.assertFalse(m.root(self.repo).exists())
        self.assertFalse((self.repo / "Mods verwalten.bat").exists())
        self.assertTrue((Path(result["backup"]) / "state.json").is_file())
        self.assertFalse((Path(result["backup"]) / "operation.lock").exists())
        self.assertEqual(
            "original save", (self.repo / "build/saves/save.bin").read_text()
        )
        self.assertEqual("original starter", (self.repo / "Play SSBU.bat").read_text())

    def test_play_uses_combined_profile_and_vanilla_disables_it(self):
        with patch.object(
            m.subprocess, "Popen", return_value=SimpleNamespace(pid=123)
        ) as process:
            m.play(self.repo)
            args = process.call_args.args[0]
            self.assertIn(
                "SSBU_CHARACTERS=" + str(m.root(self.repo) / "profile/assets"), args
            )
            self.assertIn("SSBU_LOOSE_FILES=1", args)
            self.assertIn("SSBU_SKYLINE=0", args)
            m.play(self.repo, True)
            args = process.call_args.args[0]
            self.assertIn("SSBU_LOOSE_FILES=0", args)
            self.assertIn("SSBU_CHARACTERS=" + str(m.root(self.repo) / "empty"), args)

    def test_existing_modded_starter_routes_to_manager(self):
        with patch.object(m.base.subprocess, "call", return_value=0) as process:
            m.base.play(self.repo, "modded")
            args = process.call_args.args[0]
            self.assertIn(str(m.root(self.repo) / "tools/modmanager.py"), args)
            self.assertEqual("play", args[-1])
            m.base.play(self.repo, "vanilla")
            self.assertEqual("--vanilla", process.call_args.args[0][-1])

    def test_launch_preserves_online_settings_for_both_modes(self):
        config = self.repo / "build/config/graphics.ini"
        config.parent.mkdir()
        for mode in ("lobby", "host", "off"):
            config.write_text(
                "online_mode = "
                + mode
                + "\nonline_server = test.invalid:12345\nonline_code = example\n"
            )
            before = config.read_bytes()
            with patch.object(
                m.subprocess, "Popen", return_value=SimpleNamespace(pid=123)
            ) as process:
                for vanilla in (False, True):
                    m.play(self.repo, vanilla)
                    args = process.call_args.args[0]
                    self.assertFalse(any(arg.startswith("SSBU_ONLINE") for arg in args))
                    self.assertEqual(before, config.read_bytes())

    def test_arc_launch_honors_configured_rollback(self):
        m.install(self.repo, self.mod())
        config = self.repo / "build/config/graphics.ini"
        config.parent.mkdir()
        for setting, enabled in [
            ("on # enabled", True),
            (" YES ; enabled", True),
            ("off", False),
            ("0", False),
        ]:
            config.write_text(
                "\ufeffonline_mode = lobby\nrollback = " + setting + "\n",
                encoding="utf-8",
            )
            before = config.read_bytes()
            with patch.object(
                m.subprocess, "Popen", return_value=SimpleNamespace(pid=123)
            ) as process:
                m.play(self.repo)
                args = process.call_args.args[0]
                self.assertEqual(enabled, "SSBU_RB_NET=net" in args)
                self.assertFalse(any(arg.startswith("SSBU_ONLINE") for arg in args))
            self.assertEqual(before, config.read_bytes())

    def test_config_is_preserved_and_folder_zip_identical(self):
        source = self.mod(path="fighter/foo/model/body/c03/new.nutexb")
        raw = '{"new-dir-files":{"fighter/foo/c03":["fighter/foo/model/body/c03/new.nutexb"]}}'
        (source / "config.json").write_text(raw)
        archive = Path(self.tmp.name) / "config skin.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for file in source.rglob("*"):
                if file.is_file():
                    z.write(file, "wrapper/" + file.relative_to(source).as_posix())
        first = m.inspect(self.repo, source)
        second = m.inspect(self.repo, archive)
        self.assertEqual(first["token"], second["token"])
        m.install(self.repo, archive, second["token"])
        self.assertEqual(
            raw,
            next(
                (m.root(self.repo) / "profile/ultimate/mods").rglob("config.json")
            ).read_text(),
        )

    def test_configs_of_two_mods_do_not_conflict(self):
        for i, path in enumerate(("ui/replace/a.bntx", "ui/replace/b.bntx")):
            source = self.mod("Skin " + str(i), path)
            (source / "config.json").write_text(
                json.dumps({"unshare-blacklist": ["fighter/foo/" + str(i)]})
            )
            m.install(self.repo, source)
        self.assertEqual(
            2,
            len(
                list((m.root(self.repo) / "profile/ultimate/mods").rglob("config.json"))
            ),
        )

    def test_bad_config_type_rejected(self):
        source = self.mod()
        (source / "config.json").write_text('{"new-dir-files":[]}')
        with self.assertRaisesRegex(ValueError, "Ungueltiger Wert"):
            m.inspect(self.repo, source)

    def test_backend_failure_keeps_existing_profile(self):
        before = m.files(m.root(self.repo) / "profile")
        state = m.load(self.repo)
        with patch.object(
            m.arc_backend, "ensure", side_effect=ValueError("build failed")
        ):
            with self.assertRaisesRegex(ValueError, "build failed"):
                m.install(self.repo, self.mod())
        self.assertEqual(before, m.files(m.root(self.repo) / "profile"))
        self.assertEqual(state, m.load(self.repo))

    def test_loader_profile_tampering_is_detected(self):
        source = self.mod()
        m.install(self.repo, source)
        file = m.root(self.repo) / "profile/atmosphere/injected.nro"
        file.write_text("unmanaged")
        with self.assertRaisesRegex(ValueError, "Mod-Loader-Dateien"):
            m.play(self.repo)

    def test_arc_play_selects_dedicated_executable(self):
        m.install(self.repo, self.mod())
        with patch.object(
            m.subprocess, "Popen", return_value=SimpleNamespace(pid=123)
        ) as process:
            m.play(self.repo)
            args = process.call_args.args[0]
            self.assertTrue(args[args.index("--exe") + 1].endswith("/ssbu_user.exe"))
            self.assertIn("SSBU_SKYLINE=1", args)
            self.assertIn("SSBU_LOOSE_FILES=0", args)
            self.assertIn("SSBU_SD=" + str(m.root(self.repo) / "profile"), args)
            m.play(self.repo, True)
            self.assertNotIn(m.arc_backend.EXE, process.call_args.args[0])

    def test_runtime_manifest_supports_external_build_location(self):
        outside = Path(self.tmp.name) / "External build"
        path = outside / "work/runtime.dll"
        path.parent.mkdir(parents=True)
        path.write_text("synthetic")
        (self.repo / "build_location.txt").write_text(str(outside))
        key = m.arc_backend.file_key(self.repo, path)
        self.assertEqual("@build/work/runtime.dll", key)
        self.assertEqual(path.resolve(), m.arc_backend.resolve_file(self.repo, key))
        with self.assertRaises(ValueError):
            m.arc_backend.resolve_file(self.repo, "@build/../escape")


if __name__ == "__main__":
    unittest.main(verbosity=2)
