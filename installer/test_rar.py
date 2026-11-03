"""Actual portable UnRAR decoding; no WinRAR executable or network is needed."""

import shutil, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import batch_import as b, rar_support
import test_modmanager as fixture

m = fixture.m
DATA = Path(__file__).with_name("test_data") / "rar"


class RarTests(unittest.TestCase):
    setUp = fixture.ManagerTests.setUp
    mod = fixture.ManagerTests.mod

    def archive(self, name):
        target = Path(self.tmp.name) / name
        shutil.copy2(DATA / name, target)
        return target

    def test_rar4_single_import_and_original_unchanged(self):
        source = self.archive("rar4-stored.rar")
        before = source.read_bytes()
        plan = m.inspect(self.repo, source)
        result = m.install(self.repo, source, plan["token"])
        self.assertEqual(1, len(result["state"]["mods"]))
        self.assertEqual(before, source.read_bytes())
        self.assertEqual(
            b"own RAR fixture",
            next(
                (m.root(self.repo) / "library").glob("*/assets/ui/replace/a.bntx")
            ).read_bytes(),
        )

    def test_rar5_uppercase_extension(self):
        source = self.archive("rar5-compressed.rar")
        upper = source.with_suffix(".RAR")
        source.rename(upper)
        p = m.batch_preview(self.repo, [upper])
        self.assertEqual(1, p["ready"])
        self.assertEqual(
            1, m.batch_install(self.repo, p["job_id"], p["token"])["installed"]
        )

    def test_rar5_solid_bundle_multiple_mods(self):
        source = self.archive("rar5-solid.rar")
        p = m.batch_preview(self.repo, [source])
        self.assertEqual(2, p["ready"])
        result = m.batch_install(self.repo, p["job_id"], p["token"])
        self.assertEqual(2, result["installed"])
        self.assertEqual(
            {b"first content" * 6000, b"second content" * 6000},
            {
                p.read_bytes()
                for p in (m.root(self.repo) / "library").glob(
                    "*/assets/ui/replace/*.bntx"
                )
            },
        )

    def test_rar5_unicode_wrapper(self):
        source = self.archive("rar5-unicode.rar")
        p = m.batch_preview(self.repo, [source])
        self.assertEqual(1, p["ready"])
        self.assertEqual(
            1, m.batch_install(self.repo, p["job_id"], p["token"])["installed"]
        )

    def test_mixed_zip_rar_skips_existing_and_batch_duplicate(self):
        old = self.archive("rar4-stored.rar")
        m.install(self.repo, old)
        new = self.mod("New sound", "sound/bank/test.nus3audio", "new audio")
        zip_path = Path(self.tmp.name) / "new.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            for p in new.rglob("*"):
                if p.is_file():
                    z.write(p, "New/" + p.relative_to(new).as_posix())
        plan = m.batch_preview(
            self.repo, [self.archive("rar5-compressed.rar"), zip_path, new]
        )
        self.assertEqual(
            ["duplicate", "existing", "ready"],
            sorted(i["status"] for i in plan["items"]),
        )
        self.assertEqual(
            1, m.batch_install(self.repo, plan["job_id"], plan["token"])["installed"]
        )

    def test_rar_nested_in_zip(self):
        source = self.archive("rar5-compressed.rar")
        outer = Path(self.tmp.name) / "bundle.zip"
        with zipfile.ZipFile(outer, "w") as z:
            z.write(source, "Package/mod.rar")
        plan = m.batch_preview(self.repo, [outer])
        self.assertEqual(1, plan["ready"])
        self.assertEqual(
            1, m.batch_install(self.repo, plan["job_id"], plan["token"])["installed"]
        )

    def test_rar_from_selected_folder_is_snapshotted(self):
        folder = Path(self.tmp.name) / "Downloaded bundle"
        folder.mkdir()
        shutil.copy2(DATA / "rar5-compressed.rar", folder / "pack.rar")
        plan = m.batch_preview(self.repo, [folder])
        shutil.rmtree(folder)
        self.assertEqual(1, plan["ready"])
        self.assertEqual(
            1, m.batch_install(self.repo, plan["job_id"], plan["token"])["installed"]
        )

    def test_bad_rar_does_not_block_good_zip(self):
        bad = Path(self.tmp.name) / "bad.rar"
        bad.write_bytes(b"not RAR")
        good = self.mod()
        plan = m.batch_preview(self.repo, [bad, good])
        self.assertEqual(1, plan["ready"])
        self.assertEqual(
            1, m.batch_install(self.repo, plan["job_id"], plan["token"])["installed"]
        )

    def test_unsafe_rar_paths_rejected_before_any_output(self):
        for name in (
            "traversal.rar",
            "duplicate.rar",
            "collision.rar",
            "reserved.rar",
            "symlink.rar",
        ):
            with self.subTest(name=name):
                self.assertTrue((DATA / name).is_file())
                target = Path(self.tmp.name) / ("unpack-" + name)
                with self.assertRaises(ValueError):
                    b.extract(m, DATA / name, target, None)
                self.assertFalse(target.exists())
        self.assertFalse((Path(self.tmp.name) / "outside.txt").exists())

    def test_rar_dll_normalized_colon_cannot_create_ntfs_stream(self):
        target = Path(self.tmp.name) / "normalized"
        b.extract(m, DATA / "ads.rar", target, None)
        self.assertEqual(
            ["Mod/ui/a_stream"],
            [
                p.relative_to(target).as_posix()
                for p in target.rglob("*")
                if p.is_file()
            ],
        )

    def test_zip_and_rar_nested_inside_rar(self):
        for name in ("rar5-nested-zip.rar", "rar5-nested-rar.rar"):
            with self.subTest(name=name):
                self.assertEqual(1, m.batch_preview(self.repo, [DATA / name])["ready"])

    def test_encrypted_and_multivolume_have_clear_errors(self):
        for name, word in [
            ("encrypted.rar", "Passwort"),
            ("encrypted-headers.rar", "Passwort"),
            ("volumes.part1.rar", "Mehrteilige"),
        ]:
            with self.subTest(name=name):
                p = m.batch_preview(self.repo, [DATA / name])
                self.assertEqual(0, p["ready"])
                self.assertIn(word, p["items"][0]["message"])
        self.assertEqual({}, m.load(self.repo)["mods"])

    def test_crc_damage_rejected_without_profile_change(self):
        state = (m.root(self.repo) / "state.json").read_bytes()
        p = m.batch_preview(self.repo, [DATA / "corrupt-data.rar"])
        self.assertEqual(0, p["ready"])
        self.assertIn("Pruefsumme", p["items"][0]["message"])
        self.assertEqual(state, (m.root(self.repo) / "state.json").read_bytes())

    def test_aggregate_zip_rar_size_budget(self):
        budget = dict(files=0, bytes=b.MAX_BYTES - 1)
        target = Path(self.tmp.name) / "over-budget"
        with self.assertRaisesRegex(ValueError, "Stapel"):
            b.extract(m, DATA / "rar5-compressed.rar", target, None, budget)
        self.assertFalse(target.exists())

    def test_cancel_during_rar_stream_stops_before_commit(self):
        original = rar_support.Archive.receive

        def receive(archive, msg, *args):
            if msg == 1:
                (m.root(self.repo) / "cancel-rar").touch()
            return original(archive, msg, *args)

        with patch.object(rar_support.Archive, "receive", receive):
            plan = m.batch_preview(
                self.repo,
                [DATA / "rar5-solid.rar"],
                cancel=lambda: (m.root(self.repo) / "cancel-rar").exists(),
            )
        self.assertTrue(plan["cancelled"])
        self.assertEqual(0, plan["ready"])
        self.assertEqual({}, m.load(self.repo)["mods"])

    def test_imported_rar_exports_as_standard_zip(self):
        import library_export

        m.install(self.repo, DATA / "rar5-compressed.rar")
        target = Path(self.tmp.name) / "all.zip"
        library_export.export(m, self.repo, target)
        plan = m.batch_preview(self.repo, [target])
        self.assertEqual(0, plan["ready"])
        self.assertEqual("existing", plan["items"][0]["status"])


if __name__ == "__main__":
    unittest.main()
