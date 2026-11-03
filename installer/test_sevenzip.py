"""Real portable 7z solid/Unicode/CRC decoding and bounded hostile metadata."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
import batch_import as b
import sevenzip_support as seven
import test_modmanager as fixture

m = fixture.m


class SevenZipTests(unittest.TestCase):
    setUp = fixture.ManagerTests.setUp
    mod = fixture.ManagerTests.mod

    def archive(self, encrypted=False):
        folder = self.mod("Öwn 7z", "ui/replace/a.bntx", "own first asset")
        (folder / "info.toml").write_text('display_name="Öwn 7z"', encoding="utf-8")
        (folder / "ui/replace/second.bntx").write_bytes(b"own second asset")
        (folder / "hinweise_ä.txt").write_text(
            "Own ignored Unicode document", encoding="utf-8"
        )
        output = Path(self.tmp.name) / "own.7z"
        args = [str(seven.binary()), "a", "-t7z", "-ms=on", str(output), folder.name]
        if encrypted:
            args += ["-pown-password", "-mhe=on"]
        subprocess.run(
            args, cwd=folder.parent, capture_output=True, check=True, timeout=15
        )
        return output

    def test_solid_unicode_import_duplicate_and_undo(self):
        source = self.archive()
        before = source.read_bytes()
        preview = m.batch_preview(self.repo, [source])
        self.assertEqual(1, preview["ready"])
        result = m.batch_install(self.repo, preview["job_id"], preview["token"])
        self.assertEqual(1, result["installed"])
        self.assertEqual(0, m.batch_preview(self.repo, [source])["ready"])
        key = next(iter(m.load(self.repo)["mods"]))
        self.assertEqual(
            b"own second asset",
            (
                m.root(self.repo) / "library" / key / "assets/ui/replace/second.bntx"
            ).read_bytes(),
        )
        self.assertEqual(before, source.read_bytes())
        m.undo(self.repo)
        self.assertFalse(m.load(self.repo)["mods"])

    def test_empty_files_and_directories(self):
        folder = Path(self.tmp.name) / "Own empty archive"
        (folder / "ui/empty").mkdir(parents=True)
        (folder / "ui/empty.bntx").write_bytes(b"")
        archive = Path(self.tmp.name) / "empty.7z"
        subprocess.run(
            [str(seven.binary()), "a", "-t7z", str(archive), folder.name],
            cwd=folder.parent,
            check=True,
            capture_output=True,
        )
        output = Path(self.tmp.name) / "empty output"
        seven.extract(m, archive, output, None)
        self.assertEqual(b"", (output / folder.name / "ui/empty.bntx").read_bytes())
        self.assertTrue((output / folder.name / "ui/empty").is_dir())

    def test_uppercase_extension_and_mixed_zip_7z_batch(self):
        import zipfile

        source = self.archive()
        upper = source.with_suffix(".7Z")
        source.rename(upper)
        z = Path(self.tmp.name) / "other.zip"
        with zipfile.ZipFile(z, "w") as a:
            a.writestr("Other/ui/replace/b.bntx", b"own third asset")
        self.assertEqual(2, m.batch_preview(self.repo, [upper, z])["ready"])

    def test_nested_7z_in_zip(self):
        import zipfile

        source = self.archive()
        outer = Path(self.tmp.name) / "outer.zip"
        with zipfile.ZipFile(outer, "w") as z:
            z.write(source, "wrapper/inner.7z")
        self.assertEqual(1, m.batch_preview(self.repo, [outer])["ready"])

    def test_encrypted_archive_rejected_without_password_prompt(self):
        plan = m.batch_preview(self.repo, [self.archive(encrypted=True)])
        self.assertEqual(0, plan["ready"])
        self.assertEqual("invalid", plan["items"][0]["status"])

    def test_corrupt_archive_is_not_importable(self):
        source = self.archive()
        data = bytearray(source.read_bytes())
        data[33] ^= 0xFF
        source.write_bytes(data)
        self.assertEqual(0, m.batch_preview(self.repo, [source])["ready"])

    def metadata(
        self, path="Own/ui/replace/a.bntx", size="1", attributes="A", extra=""
    ):
        source = Path(self.tmp.name) / "header.7z"
        source.write_bytes(b"7z\xbc\xaf\x27\x1c")
        data = f"Path = {path}\nSize = {size}\nAttributes = {attributes}\nCRC = 00000000\nEncrypted = -\n{extra}\n".encode(
            "utf-8"
        )
        return source, data

    def test_unsafe_paths_are_rejected_before_output_files(self):
        for path in [
            "../escape",
            "C:/outside",
            "Own/CON.txt",
            "Own/thing:stream",
            "Own/a\x00b",
        ]:
            source, data = self.metadata(path)
            with self.subTest(path=path), patch.object(
                seven, "chunks", return_value=iter([data])
            ), self.assertRaises(ValueError):
                seven.entries(source, None)

    def test_links_and_special_files_are_rejected(self):
        for attributes, extra in [
            ("A_ lrwxrwxrwx", ""),
            ("A", "Symbolic Link = ../outside"),
            ("A", "Hard Link = ../outside"),
            ("A", "Anti = +"),
            ("A_ prw-r--r--", ""),
        ]:
            source, data = self.metadata(attributes=attributes, extra=extra)
            with self.subTest(attributes=attributes, extra=extra), patch.object(
                seven, "chunks", return_value=iter([data])
            ), self.assertRaises(ValueError):
                seven.entries(source, None)

    def test_ambiguous_newline_metadata_is_rejected(self):
        source, data = self.metadata("Own/file\nSize = 999")
        with patch.object(
            seven, "chunks", return_value=iter([data])
        ), self.assertRaises(ValueError):
            seven.entries(source, None)

    def test_shared_expansion_quota_is_checked_before_decode(self):
        source = self.archive()
        target = Path(self.tmp.name) / "out"
        with self.assertRaises(ValueError):
            seven.extract(m, source, target, None, dict(files=0, bytes=b.MAX_BYTES))
        self.assertFalse(target.exists())

    def test_cancel_cannot_change_library(self):
        source = self.archive()
        before = (m.root(self.repo) / "state.json").read_bytes()
        plan = m.batch_preview(self.repo, [source], cancel=lambda: True)
        self.assertTrue(plan["cancelled"])
        self.assertEqual(before, (m.root(self.repo) / "state.json").read_bytes())

    def test_native_memory_limit_fails_closed(self):
        with patch.object(seven, "MEMORY_LIMIT", 1024 * 1024), self.assertRaises(
            ValueError
        ):
            seven.entries(self.archive(), None)
