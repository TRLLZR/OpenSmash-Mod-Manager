"""Framework resolution uses binary/asset structure, never user-visible titles."""

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import plugin_dependencies as dependencies
import plugin_runtime
import catalog


class GameplayDependencies(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / "test-scratch"
        scratch.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.plugin = self.folder / "plugin.nro"
        self.plugin.write_bytes(
            b"own fixture libparam_config.nro\0libthe_csk_collection.nro\0"
        )

    def test_resolves_binary_references_and_extended_effect_slots(self):
        self.assertEqual(
            dependencies.required(
                [self.plugin], ["effect/fighter/example/example_c120.eff"]
            ),
            ["csk", "one_slot_effects", "param_config"],
        )

    def test_standard_skin_effects_do_not_request_slot_framework(self):
        self.plugin.write_bytes(b"own ordinary plugin")
        self.assertEqual(
            dependencies.required(
                [self.plugin], ["effect/fighter/example/example_c00.eff"]
            ),
            [],
        )
        self.assertEqual(
            dependencies.required([], ["effect/fighter/example/example_c120.eff"]), ['one_slot_effects']
        )

    def test_explicitly_provided_framework_is_not_duplicated(self):
        supplied = self.folder / "libparam_config.nro"
        supplied.write_bytes(b"own supplied framework")
        self.assertEqual(dependencies.required([self.plugin, supplied]), ["csk"])

    def test_extended_costumes_are_reported_without_truncation(self):
        record = {
            "entries": [
                {"path": "fighter/example/model/body/c120/model.numdlb"},
                {"path": "fighter/example/model/body/c127/model.numdlb"},
            ]
        }
        self.assertEqual(
            catalog.costume_slots(record), ["example/c120", "example/c127"]
        )

    def test_runtime_cannot_pass_when_required_library_is_missing(self):
        with self.assertRaisesRegex(ValueError, "libgeneric_library.nro"):
            plugin_runtime.validate_log(
                "Finished mounting mods:/\nlibgeneric_library.nro not found! This installation is incomplete."
            )

    def test_host_crash_cannot_pass_as_ready(self):
        with self.assertRaises(ValueError):
            plugin_runtime.validate_log(
                "Finished mounting mods:/\nHOST EXCEPTION 0xc0000005"
            )

    def test_imported_framework_keeps_required_boot_filename(self):
        self.assertEqual(
            plugin_runtime.boot_name(
                dict(
                    path="ultimate/mods/own/libthe_csk_collection.nro",
                    module="sky_the_csk_collection",
                )
            ),
            "libthe_csk_collection.nro",
        )

    def test_renamed_incompatible_binary_rejected_before_builder(self):
        state = self.folder / "build/state.json"
        state.parent.mkdir()
        state.write_text(json.dumps(dict(game_version="13.0.5")), encoding="utf-8")
        self.plugin.write_bytes(b"own incompatible framework fixture")
        definition = dict(
            dependencies.REGISTRY["csk"],
            nro_sha256=hashlib.sha256(self.plugin.read_bytes()).hexdigest(),
            game_versions=['13.0.4'], version='5.0.6',
        )
        with patch.dict(dependencies.REGISTRY, {"csk": definition}):
            with self.assertRaisesRegex(ValueError, "13.0.5"):
                dependencies.check_provided(self.folder, [self.plugin])

    def test_early_probe_crash_is_identified_in_message(self):
        with self.assertRaisesRegex(ValueError, "HOST EXCEPTION"):
            plugin_runtime.validate_log("HOST EXCEPTION 0xc0000005")
        self.assertEqual(
            plugin_runtime.boot_name(
                dict(path="ultimate/mods/own/ordinary.nro", module="sky_ordinary")
            ),
            "ordinary.nro",
        )

    def test_incompatible_framework_fails_before_network_or_build(self):
        state = self.folder / "build/state.json"
        state.parent.mkdir()
        state.write_text(json.dumps(dict(game_version="13.0.3")), encoding="utf-8")
        with patch.object(dependencies, "_download") as download:
            with self.assertRaisesRegex(ValueError, "13.0.3"):
                dependencies.obtain(self.folder, "csk")
            download.assert_not_called()

    def test_dependency_archive_extracts_only_the_pinned_library(self):
        (self.folder / "opensmash_mods").mkdir()
        archive = self.folder / "own.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("plugins/library.nro", b"own NRO bytes")
            z.writestr("optional/unlock.flag", b"not selected")
            z.writestr("author-tools.py", b"never executed")
        data = archive.read_bytes()
        definition = dict(
            filename="library.nro",
            member="plugins/library.nro",
            sha256=hashlib.sha256(data).hexdigest(),
            url="https://gamebanana.com/dl/1",
        )
        with patch.dict(dependencies.REGISTRY, {"own": definition}), patch.object(
            dependencies, "_download", return_value=data
        ):
            path = dependencies.obtain(self.folder, "own")
            self.assertEqual(path.read_bytes(), b"own NRO bytes")
            self.assertFalse(list((self.folder / "opensmash_mods").rglob("*.flag")))
            self.assertFalse(list((self.folder / "opensmash_mods").rglob("*.py")))


if __name__ == "__main__":
    unittest.main()
