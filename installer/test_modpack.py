import hashlib, json, struct, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import test_modmanager as fixture
import library_export, plugin_runtime

m = fixture.m


def nro(name="sample"):
    data = bytearray(256)
    data[16:20] = b"NRO0"
    struct.pack_into("<I", data, 24, 256)
    for off, start, size in ((32, 0, 128), (40, 128, 64), (48, 192, 64)):
        struct.pack_into("<II", data, off, start, size)
    text = (name + ".nro").encode()
    struct.pack_into("<Ii", data, 128, 0, len(text))
    data[136 : 136 + len(text)] = text
    return bytes(data)


class ModpackTests(unittest.TestCase):
    setUp = fixture.ManagerTests.setUp
    mod = fixture.ManagerTests.mod

    def export(self):
        target = Path(self.tmp.name) / "All mods.zip"
        library_export.export(m, self.repo, target)
        return target

    def test_generic_ui_and_narration_sd_wrappers(self):
        z = Path(self.tmp.name) / "sound-ui.zip"
        with zipfile.ZipFile(z, "w") as a:
            a.writestr(
                "Package/ultimate/mods/Any name/sound/bank/narration/a.nus3audio",
                b"audio",
            )
            a.writestr(
                "Package/ultimate/mods/Any name/ui/layout/screen/layout.arc", b"layout"
            )
        p = m.batch_preview(self.repo, [z])
        self.assertEqual(1, p["ready"])
        self.assertEqual(
            1, m.batch_install(self.repo, p["job_id"], p["token"])["installed"]
        )

    def test_streaming_and_credits_survive_install_pause_reenable_remove(self):
        assets = {
            "stream;/sound/bgm/example.nus3audio": b"own music",
            "standard/staffroll/texture/example.nutexb": b"own credits",
        }
        archive = Path(self.tmp.name) / "Wrapped assets.zip"
        with zipfile.ZipFile(archive, "w") as output:
            for name, data in assets.items():
                output.writestr("bundle/ultimate/mods/Example/" + name, data)
        plan = m.batch_preview(self.repo, [archive])
        result = m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertEqual(1, result["installed"])
        key = result["state"]["mods"][0]["id"]
        profile = m.root(self.repo) / "profile/ultimate/mods" / key
        for name, data in assets.items():
            self.assertEqual(data, (profile / name).read_bytes())
        m.change(self.repo, key, "enable", False)
        self.assertFalse(profile.exists())
        m.change(self.repo, key, "enable", True)
        for name, data in assets.items():
            self.assertEqual(data, (profile / name).read_bytes())
        m.change(self.repo, key, "remove")
        self.assertFalse(profile.exists())
        self.assertEqual([], m.listing(self.repo)["mods"])

    def test_plugin_and_arbitrary_named_configuration_preserved(self):
        source = self.mod("Generic effect", "effect/system/common/a.eff")
        (source / "plugin.nro").write_bytes(nro())
        (source / "arbitrary_settings.toml").write_text("[character]\nvalue=3\n")
        record = m.analyze(self.repo, source)
        self.assertEqual(
            {"plugin.nro", "arbitrary_settings.toml"},
            {e["path"] for e in record["entries"] if e.get("kind")},
        )
        self.assertEqual(
            "sky_sample",
            next(e["module"] for e in record["entries"] if e.get("kind") == "plugin"),
        )

    def test_plugin_only_mod(self):
        source = Path(self.tmp.name) / "Plugin only"
        source.mkdir()
        (source / "plugin.nro").write_bytes(nro("different_plugin"))
        self.assertEqual(1, m.batch_preview(self.repo, [source])["ready"])

    def test_windows_program_still_rejected(self):
        source = self.mod()
        (source / "installer.exe").write_bytes(b"MZ")
        with self.assertRaises(ValueError):
            m.analyze(self.repo, source)

    def test_failed_plugin_does_not_block_plain_asset_mod(self):
        plugin = self.mod("Plugin", "effect/a.eff")
        (plugin / "plugin.nro").write_bytes(nro())
        plain = self.mod("Audio Pack", "sound/a.nus3audio")

        def prepare(repo, profile, requirements=None):
            if plugin_runtime.plugins(profile):
                raise ValueError("Unsupported synthetic plugin")
            return None

        plan = m.batch_preview(self.repo, [plugin, plain])
        with patch.object(plugin_runtime, "ensure", side_effect=prepare):
            result = m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertEqual(1, result["installed"])
        self.assertEqual(1, result["failed"])
        self.assertEqual("Audio Pack", result["state"]["mods"][0]["name"])

    def test_cancel_during_plugin_preparation_keeps_previous_profile(self):
        source = self.mod("Plugin", "effect/a.eff")
        (source / "plugin.nro").write_bytes(nro())
        plan = m.batch_preview(self.repo, [source])
        before = (m.root(self.repo) / "state.json").read_bytes()
        import batch_import

        def prepare(repo, profile, requirements=None):
            (batch_import.path(m, repo, plan["job_id"]) / "cancel.request").write_text(
                "cancel"
            )
            return None

        with patch.object(plugin_runtime, "ensure", side_effect=prepare):
            result = m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertTrue(result["cancelled"])
        self.assertEqual(0, result["installed"])
        self.assertEqual(before, (m.root(self.repo) / "state.json").read_bytes())

    def test_only_documented_smashline_sdk_exemptions_allowed(self):
        text = "[skyline] sky_smashline: main\n[skyline] inline hook at sdk+0x1: NOT ACTIVE\n[skyline] hook at sdk+0x2 -> sky_smashline+0x3: NOT ACTIVE\n[skyline] sky_smashline: main returned"
        self.assertEqual(2, len(plugin_runtime.validate_log(text, True)))
        with self.assertRaises(ValueError):
            plugin_runtime.validate_log(text, False)
        with self.assertRaises(ValueError):
            plugin_runtime.validate_log(
                "[skyline] inline hook at main+0x1: NOT ACTIVE", True
            )

    def test_unmanaged_executable_cannot_be_selected_by_runtime_metadata(self):
        with self.assertRaises(ValueError):
            plugin_runtime.valid(
                self.repo,
                dict(
                    app=plugin_runtime.APP, key="0" * 20, exe="C:/other.exe", files={}
                ),
            )

    def test_invalid_nro_header_rejected(self):
        source = self.mod()
        (source / "plugin.nro").write_bytes(b"not NRO")
        with self.assertRaises(ValueError):
            m.analyze(self.repo, source)

    def test_export_includes_paused_mods_and_omits_private_game_paths(self):
        first = m.install(self.repo, self.mod("First"))["state"]["mods"][0]["id"]
        m.change(self.repo, first, "enable", False)
        m.install(self.repo, self.mod("Second", "ui/replace/b.bntx"))
        target = self.export()
        with zipfile.ZipFile(target) as z:
            d = json.loads(z.read(library_export.MANIFEST))
            self.assertEqual(2, len(d["mods"]))
            self.assertEqual([False, True], sorted(x["enabled"] for x in d["mods"]))
            self.assertFalse(
                any(
                    s in n.lower()
                    for n in z.namelist()
                    for s in ("userdata", "save.bin", "graphics.ini", "state.json")
                )
            )
            self.assertNotIn(str(self.repo), json.dumps(d))
        plan = m.batch_preview(self.repo, [target])
        self.assertEqual(0, plan["ready"])
        self.assertTrue(all(i["status"] == "existing" for i in plan["items"]))
        self.assertFalse(m.load(self.repo)["mods"][first]["enabled"])

    def test_export_roundtrip_preserves_enabled_state(self):
        key = m.install(self.repo, self.mod())["state"]["mods"][0]["id"]
        m.change(self.repo, key, "enable", False)
        archive = self.export()
        m.change(self.repo, key, "remove")
        plan = m.batch_preview(self.repo, [archive])
        self.assertEqual(1, plan["ready"])
        result = m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertEqual(1, result["installed"])
        self.assertFalse(result["state"]["mods"][0]["enabled"])

    def test_pack_existing_plus_new_only_installs_new(self):
        one = self.mod("Existing")
        two = self.mod("New", "ui/replace/b.bntx")
        m.install(self.repo, one)
        z = Path(self.tmp.name) / "mixed.zip"
        with zipfile.ZipFile(z, "w") as out:
            for source in (one, two):
                for p in source.rglob("*"):
                    if p.is_file():
                        out.write(
                            p, source.name + "/" + p.relative_to(source).as_posix()
                        )
        plan = m.batch_preview(self.repo, [z, one])
        self.assertEqual(1, plan["ready"])
        self.assertEqual(
            1, m.batch_install(self.repo, plan["job_id"], plan["token"])["installed"]
        )

    def test_nested_zip_bundle(self):
        a = Path(self.tmp.name) / "one.zip"
        b = Path(self.tmp.name) / "bundle.zip"
        with zipfile.ZipFile(a, "w") as z:
            z.writestr("Any root/sound/bank/a.nus3audio", b"sound")
        with zipfile.ZipFile(b, "w") as z:
            z.write(a, "mods/one.zip")
        p = m.batch_preview(self.repo, [b])
        self.assertEqual(1, p["ready"])
        self.assertEqual(
            1, m.batch_install(self.repo, p["job_id"], p["token"])["installed"]
        )

    def test_bundle_larger_than_old_64_mod_limit(self):
        archive = Path(self.tmp.name) / "large-library.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for i in range(65):
                z.writestr("mods/pack%d/sound/%d.nus3audio" % (i, i), bytes([i]))
        plan = m.batch_preview(self.repo, [archive])
        self.assertEqual(65, plan["ready"])

    def test_info_label_changes_do_not_duplicate_assets(self):
        source = self.mod("Original")
        m.install(self.repo, source)
        (source / "info.toml").write_text('display_name="New label"')
        self.assertEqual(
            "existing", m.batch_preview(self.repo, [source])["items"][0]["status"]
        )

    def test_export_detects_change_during_copy_and_preserves_old_target(self):
        source = self.mod()
        key = m.install(self.repo, source)["state"]["mods"][0]["id"]
        target = Path(self.tmp.name) / "protected.zip"
        target.write_bytes(b"previous export")
        original = m.metadata

        def changed(repo, mod_id):
            record = original(repo, mod_id)
            (m.root(repo) / "library" / key / "assets/ui/replace/a.bntx").write_text(
                "changed"
            )
            return record

        with patch.object(m, "metadata", side_effect=changed):
            with self.assertRaises(ValueError):
                library_export.export(m, self.repo, target)
        self.assertEqual(b"previous export", target.read_bytes())
        self.assertFalse(list(target.parent.glob(".opensmash-export-*")))

    def test_tampered_pack_is_rejected_per_mod(self):
        m.install(self.repo, self.mod())
        archive = self.export()
        with zipfile.ZipFile(archive) as z:
            content = {i.filename: z.read(i) for i in z.infolist()}
        name = next(n for n in content if n.endswith(".bntx"))
        content[name] = b"tampered"
        with zipfile.ZipFile(archive, "w") as z:
            for n, d in content.items():
                z.writestr(n, d)
        plan = m.batch_preview(self.repo, [archive])
        self.assertEqual("invalid", plan["items"][0]["status"])
