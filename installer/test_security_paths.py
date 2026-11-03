"""Regression tests for Win32 names before ZIP/RAR output creation."""

import unittest

from batch_import import safe_name, validate_entries


class WindowsArchiveNames(unittest.TestCase):
    def test_superscript_devices_are_rejected_at_any_depth(self):
        for prefix in ("COM", "LPT", "com", "lpt"):
            for digit in "¹²³":
                with self.subTest(prefix=prefix, digit=digit):
                    with self.assertRaises(ValueError):
                        validate_entries([(f"skin/ui/{prefix}{digit}.bntx", 3, False)])

    def test_invalid_windows_characters_are_rejected(self):
        for character in '<>"|?*\x01\x1f':
            with self.subTest(character=character):
                with self.assertRaises(ValueError):
                    safe_name("skin/ui/a" + character + ".bntx")

    def test_unicode_mod_paths_remain_valid(self):
        self.assertEqual(safe_name("肌肤/ui/étoile.bntx"), "肌肤/ui/étoile.bntx")
        self.assertEqual(safe_name("ui/COMPONENT1.bntx"), "ui/COMPONENT1.bntx")


if __name__ == "__main__":
    unittest.main()
