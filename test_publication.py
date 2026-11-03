"""Publication guard regressions use tiny owned bytes, not a user's work tree."""

import hashlib
import json
import unittest

import audit_publication as audit
from export_source import check_build_inputs


def fixture():
    files = {name: b"Own fixture\n" for name in audit.REQUIRED}
    for name in ("LICENSE.txt", "THIRD_PARTY_NOTICES.txt", "BRANDING.md"):
        files["installer/" + name] = files[name]
    files["installer/7ZIP_DISTRIBUTION.json"] = json.dumps(
        dict(
            binary_sha256=hashlib.sha256(files["installer/7za.exe"]).hexdigest(),
            source_sha256=hashlib.sha256(
                files["third_party/7zip/7z2605-src.tar.xz"]
            ).hexdigest(),
        )
    ).encode()
    files["installer/UNRAR_DISTRIBUTION.json"] = json.dumps(
        dict(
            sha256=hashlib.sha256(files["installer/UnRAR64.dll"]).hexdigest(),
        )
    ).encode()
    files["installer/test_data/rar/fixtures.json"] = b"{}"
    return files


class PublicationTests(unittest.TestCase):
    def test_publication_includes_build_documents(self):
        files = {
            "build_release.py": b"names = ['README.md', 'ModManager.exe', 'Uninstall.exe']"
        }
        with self.assertRaisesRegex(ValueError, "Build inputs missing"):
            check_build_inputs(files)
        files["installer/README.md"] = b"Own public documentation"
        check_build_inputs(files)

    def test_required_notices_and_matching_source(self):
        self.assertTrue(audit.validate(fixture())["corresponding_7zip_source"])

    def test_missing_license_fails(self):
        files = fixture()
        del files["installer/7ZIP_LGPL.txt"]
        with self.assertRaisesRegex(ValueError, "Missing"):
            audit.validate(files)

    def test_private_generated_and_game_files_fail(self):
        for name in (
            "installer/runtime/private.txt",
            "settings.json",
            "gameplay-qa/result.txt",
            "installer/ssbu_game.dll",
            "game/main.elf",
            "installer/BERICHT_3.0_DE.md",
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                audit.validate(dict(fixture(), **{name: b"own"}))

    def test_modified_pinned_decoder_or_source_fails(self):
        for name in (
            "installer/7za.exe",
            "installer/UnRAR64.dll",
            "third_party/7zip/7z2605-src.tar.xz",
        ):
            files = fixture()
            files[name] = b"modified own bytes"
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Pinned"):
                audit.validate(files)

    def test_secret_rejection_does_not_echo_value(self):
        value = b"ghp_" + b"A" * 40
        files = fixture()
        files["example.py"] = value
        with self.assertRaises(ValueError) as caught:
            audit.validate(files)
        self.assertNotIn(value.decode(), str(caught.exception))

    def test_unsafe_names_and_wrong_powershell_encoding_fail(self):
        for name, data in (
            ("../outside.txt", b"own"),
            ("C:/outside.txt", b"own"),
            ("bad.ps1", "Write-Host 'ä'".encode()),
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                audit.validate(dict(fixture(), **{name: data}))


if __name__ == "__main__":
    unittest.main()
