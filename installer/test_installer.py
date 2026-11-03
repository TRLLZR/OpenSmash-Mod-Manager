"""Offline transaction tests with synthetic files; contains no game data."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import zipfile

spec = importlib.util.spec_from_file_location(
    "installer_under_test", Path(__file__).with_name("drybowser.py")
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / "test-scratch"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="Dry Bowser tests ", dir=scratch)
        assert Path(self.temp.name).resolve().is_relative_to(scratch.resolve())
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "Game with spaces"
        self.repo.mkdir()

        def put(path, content):
            p = self.repo / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)

        put(
            "build/state.json",
            json.dumps(
                dict(
                    game_version="13.0.5",
                    dump=dict(romfs=str(self.repo / "build/dump/romfs")),
                )
            ),
        )
        put("scripts/run.py", "# --env --log --userdata")
        put("runtime/loose_host.c", "SSBU_LOOSE_FILES SSBU_LOOSE_FILES=0")
        put("runtime/loose_files.c", "SSBU_CHARACTERS SSBU_LOOSE_RAW lf_rawcopy")
        put(
            "build/work/ssbu_native.exe",
            "SYNTHETIC SSBU_LOOSE_FILES SSBU_LOOSE_RAW [loose] served",
        )
        for p in [
            "build/work/ssbu_game_eh_o1.dll",
            "build/work/SDL3.dll",
            "build/work/ssbu_glslang.dll",
            "build/binaries/13.0.5/main.elf",
            "build/dump/romfs/data.arc",
        ]:
            put(p, "SYNTHETIC FIXTURE")
        put("Play SSBU.bat", "original vanilla starter")
        put("Play SSBU Modded.bat", "preexisting custom starter")
        put("build/saves/save.bin", "untouched user save")
        put(
            "tools/nro/arc_extract.py",
            """
def hash40(s): return s
class Arc:
 def __init__(self,p): self.f=open(p,'rb'); self.n_path=0
 def path_index_from_hash(self,h): return h
 def file_record(self,i): return dict(decomp_size=1,info_flags=16,info_index=i,data_flags=1)
""",
        )
        self.mod = self.repo / "mods/custom/DryBowserFullReplacement"
        put(
            "mods/custom/DryBowserFullReplacement/info.toml",
            "Dry Bowser Full Replacement Release 4",
        )
        for fighter in ["koopa", "koopag"]:
            for slot in range(8):
                put(
                    f"mods/custom/DryBowserFullReplacement/fighter/{fighter}/model/body/c{slot:02}/model.numdlb",
                    "synthetic model",
                )
        for i in range(600):
            put(
                f"mods/custom/DryBowserFullReplacement/fighter/koopa/texture/f{i}.nutexb",
                "synthetic texture",
            )

    def invoke(self, fn, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*args)

    def test_native_starters_preserve_online_configuration(self):
        self.invoke(m.install, self.repo, self.mod)
        config = self.repo / "build/config/graphics.ini"
        config.parent.mkdir()
        config.write_text(
            "online_mode = lobby\nonline_server = test.invalid:12345\nrollback = on\n"
        )
        before = config.read_bytes()
        with patch.object(m.subprocess, "call", return_value=0) as launch:
            for mode in ("modded", "vanilla"):
                self.invoke(m.play, self.repo, mode)
                args = launch.call_args.args[0]
                self.assertFalse(any(arg.startswith("SSBU_ONLINE") for arg in args))
                self.assertEqual(before, config.read_bytes())

    def test_launch_helper_update_does_not_require_mod_source(self):
        self.invoke(m.install, self.repo, self.mod)
        initial = m.verify_managed(self.repo / m.LOCAL)
        self.mod.rename(self.repo / "download no longer at original location")
        incoming = Path(self.temp.name) / "updated tools"
        incoming.mkdir()
        for name in ("drybowser.py", "Start.ps1"):
            source = Path(__file__).with_name(name)
            (incoming / name).write_bytes(
                source.read_bytes() + b"\n# synthetic tool update\n"
            )
        m.update_launch_tools(self.repo, incoming)
        updated = m.verify_managed(self.repo / m.LOCAL)
        self.assertEqual(initial["source_sha256"], updated["source_sha256"])
        self.assertEqual(
            {
                k: v
                for k, v in initial["owned_files"].items()
                if k.startswith("assets/")
            },
            {
                k: v
                for k, v in updated["owned_files"].items()
                if k.startswith("assets/")
            },
        )
        self.assertEqual(
            m.digest(incoming / "drybowser.py"),
            updated["owned_files"]["tools/drybowser.py"],
        )
        before = (self.repo / m.LOCAL / "installation.json").read_bytes()
        m.update_launch_tools(self.repo, incoming)
        self.assertEqual(
            before, (self.repo / m.LOCAL / "installation.json").read_bytes()
        )

    def test_install_repeat_uninstall_restore(self):
        self.invoke(m.install, self.repo, self.mod)
        local = self.repo / m.LOCAL
        before = (local / "installation.json").read_bytes()
        self.invoke(m.install, self.repo, self.mod)
        self.assertEqual(before, (local / "installation.json").read_bytes())
        self.assertEqual(
            "untouched user save", (self.repo / "build/saves/save.bin").read_text()
        )
        self.invoke(m.uninstall, self.repo)
        self.assertFalse(local.exists())
        self.assertEqual(
            "preexisting custom starter",
            (self.repo / "Play SSBU Modded.bat").read_text(),
        )
        self.assertFalse((self.repo / "Play SSBU Vanilla.bat").exists())
        self.assertEqual(
            "original vanilla starter", (self.repo / "Play SSBU.bat").read_text()
        )
        self.invoke(m.uninstall, self.repo)
        self.invoke(m.install, self.repo, self.mod)

    def test_tampered_assets_refuse_uninstall(self):
        self.invoke(m.install, self.repo, self.mod)
        p = next((self.repo / m.LOCAL / "assets").rglob("*.numdlb"))
        p.write_text("user modification")
        with self.assertRaises(ValueError):
            self.invoke(m.uninstall, self.repo)
        self.assertEqual("user modification", p.read_text())

    def test_tampered_launcher_refuse_uninstall(self):
        self.invoke(m.install, self.repo, self.mod)
        (self.repo / "Play SSBU Modded.bat").write_text("user modification")
        with self.assertRaises(ValueError):
            self.invoke(m.uninstall, self.repo)
        self.assertTrue((self.repo / m.LOCAL).exists())

    def test_updated_mod_backup_preserves_originals(self):
        self.invoke(m.install, self.repo, self.mod)
        (self.mod / "fighter/koopa/texture/f0.nutexb").write_text("updated texture")
        self.invoke(m.install, self.repo, self.mod)
        self.assertEqual(
            "updated texture",
            (
                self.repo / m.LOCAL / "assets/DryBowser/fighter/koopa/texture/f0.nutexb"
            ).read_text(),
        )
        self.invoke(m.uninstall, self.repo)
        self.assertEqual(
            "preexisting custom starter",
            (self.repo / "Play SSBU Modded.bat").read_text(),
        )

    def test_check_has_no_install_side_effects(self):
        self.invoke(m.install, self.repo, self.mod, True)
        self.assertFalse((self.repo / m.LOCAL).exists())
        self.assertFalse((self.repo / "drybowser_backups").exists())

    def test_missing_loader_refuses_install(self):
        (self.repo / "build/work/ssbu_native.exe").write_text("unrelated exe")
        with self.assertRaises(ValueError):
            self.invoke(m.install, self.repo, self.mod)
        self.assertFalse((self.repo / m.LOCAL).exists())

    def test_external_archive_alias_keeps_original(self):
        build, state, arc, h40 = m.preflight(self.repo)
        self.addCleanup(arc.f.close)
        original_record = arc.file_record
        arc.n_path = 1
        arc.file_path = lambda index: ((123456789, 0), None, None, None)
        arc.file_record = lambda index: original_record(
            "fighter/koopa/texture/f0.nutexb" if index == 0 else index
        )
        report = m.analyze(self.mod, arc, h40)
        self.assertNotIn("fighter/koopa/texture/f0.nutexb", report["install_files"])
        self.assertEqual(1, len(report["protected_shared_entries"]))

    def test_zip_traversal_rejected(self):
        archive = Path(self.temp.name) / "bad.zip"
        target = Path(self.temp.name) / "unzip"
        target.mkdir()
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("../escape.txt", "unsafe")
        with self.assertRaises(ValueError):
            m.unpack_zip(archive, target)
        self.assertFalse((target.parent / "escape.txt").exists())

    def test_zip_input(self):
        archive = Path(self.temp.name) / "mod.zip"
        target = Path(self.temp.name) / "unzip"
        target.mkdir()
        with zipfile.ZipFile(archive, "w") as z:
            for p in self.mod.rglob("*"):
                if p.is_file():
                    z.write(
                        p,
                        "wrapper/DryBowserFullReplacement/"
                        + p.relative_to(self.mod).as_posix(),
                    )
        m.unpack_zip(archive, target)
        found = m.find_mod(target)
        self.invoke(m.install, self.repo, found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
