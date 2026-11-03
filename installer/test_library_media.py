"""Cover conversion is bounded, optional, and independent of playable mod data."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import Mock
from PIL import Image

import library_media as media
import test_modmanager as fixture


class LibraryMediaTests(unittest.TestCase):
    setUp = fixture.ManagerTests.setUp
    mod = fixture.ManagerTests.mod

    def test_imported_cover_has_no_effect_on_mod_identity_or_profile(self):
        folder = self.mod()
        before = fixture.m.inspect(self.repo, folder)
        Image.new("RGB", (1000, 700), (40, 130, 180)).save(folder / "preview.png")
        with_cover = fixture.m.inspect(self.repo, folder)
        self.assertEqual(before["token"], with_cover["token"])
        fixture.m.install(self.repo, folder)
        key = before["id"]
        cover = media.cached(self.repo, key)
        self.assertTrue(cover)
        with Image.open(cover) as image:
            self.assertLessEqual(image.width, 480)
            self.assertLessEqual(image.height, 270)
        profile = json.loads(
            (fixture.m.root(self.repo) / "profile/profile.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(any("preview.png" in name for name in profile["files"]))

    def test_bad_optional_cover_does_not_block_installation(self):
        folder = self.mod()
        (folder / "cover.png").write_text("not an image", encoding="utf-8")
        fixture.m.install(self.repo, folder)
        self.assertEqual(len(fixture.m.load(self.repo)["mods"]), 1)

    def test_manual_cover_does_not_change_activation_profile_or_settings(self):
        fixture.m.install(self.repo, self.mod())
        key = next(iter(fixture.m.load(self.repo)["mods"]))
        before = (fixture.m.root(self.repo) / "state.json").read_bytes()
        profile = (fixture.m.root(self.repo) / "profile/profile.json").read_bytes()
        source = Path(self.tmp.name) / "own.png"
        Image.new("RGB", (320, 180), (20, 90, 160)).save(source)
        media.set_cover(self.repo, key, source)
        self.assertEqual(
            before, (fixture.m.root(self.repo) / "state.json").read_bytes()
        )
        self.assertEqual(
            profile, (fixture.m.root(self.repo) / "profile/profile.json").read_bytes()
        )

    def test_invalid_id_cannot_choose_cache_path(self):
        with self.assertRaises(ValueError):
            media.cover_path(self.repo, "../../outside")

    def test_existing_cover_is_not_replaced_by_optional_import_art(self):
        key = "mod-0123456789abcdef"
        source = self.mod()
        Image.new("RGB", (20, 20), (20, 30, 40)).save(source / "cover.png")
        target = Path(media.set_cover(self.repo, key, source / "cover.png"))
        before = target.read_bytes()
        Image.new("RGB", (20, 20), (120, 130, 140)).save(source / "cover.png")
        media.capture(self.repo, key, source)
        self.assertEqual(before, target.read_bytes())

    def test_cover_uses_saved_provider_identity_without_guessing_titles(self):
        import modmanager

        fixture.m.install(self.repo, self.mod())
        key = next(iter(fixture.m.load(self.repo)["mods"]))
        record = fixture.m.metadata(self.repo, key)
        record["origin"] = dict(provider="GameBanana", model="Mod", submission_id=123)
        source = Path(self.tmp.name) / "own-provider-image.png"
        Image.new("RGB", (400, 200), (20, 40, 80)).save(source)
        client = Mock()
        client.detail.return_value = dict(
            thumbnail="https://images.gamebanana.com/img/ss/mods/own.png"
        )
        client.thumbnail.return_value = source
        with patch.object(modmanager, "metadata", return_value=record):
            result = media.populate(self.repo, client, [key])
        self.assertTrue(result["items"][0]["path"])
        client.detail.assert_called_once_with("Mod", 123)

    def test_legacy_import_without_provider_does_not_search_by_name(self):
        fixture.m.install(self.repo, self.mod())
        key = next(iter(fixture.m.load(self.repo)["mods"]))
        client = Mock()
        result = media.populate(self.repo, client, [key])
        self.assertIsNone(result["items"][0]["path"])
        client.detail.assert_not_called()
        client.thumbnail.assert_not_called()


if __name__ == "__main__":
    unittest.main()
