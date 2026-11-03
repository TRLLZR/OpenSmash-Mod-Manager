import unittest
from types import SimpleNamespace
from unittest.mock import Mock
import manager_links as links


class LinkTests(unittest.TestCase):
    def test_provider_format_roundtrip(self):
        value = links.make("Sound", 45225, 1040406, "sound.rar")
        self.assertEqual(
            dict(model="Sound", id=45225, file_id=1040406, extension="rar"),
            links.parse(value),
        )
        self.assertEqual("opensmashmm", value.split(":", 1)[0])
        self.assertEqual(
            "7z", links.parse(links.make("Mod", 10, 20, "own.7z"))["extension"]
        )

    def test_own_alternative_link(self):
        self.assertEqual(
            dict(model="Mod", id=174180, file_id=123),
            links.parse("opensmashmm://gamebanana/Mod/174180?file=123"),
        )

    def test_pasted_mosaic_link_does_not_require_hijacking(self):
        parsed = links.parse(
            "fightplanner:https://gamebanana.com/mmdl/1040406,Sound,45225,zip"
        )
        self.assertEqual(1040406, parsed["file_id"])
        self.assertEqual("Sound", parsed["model"])

    def test_mod_page_opens_details_without_picking_file(self):
        q = SimpleNamespace(
            enqueue=Mock(side_effect=AssertionError("must choose variant"))
        )
        self.assertEqual(
            dict(mode="detail", model="Mod", id=174180),
            links.accept(q, "https://gamebanana.com/mods/174180"),
        )

    def test_rejects_command_injection_and_unrelated_hosts(self):
        for value in [
            "opensmashmm:https://evil.test/dl/1,Mod,2,zip",
            "opensmashmm:https://gamebanana.com/dl/1,Mod,2,exe",
            "opensmashmm:https://gamebanana.com/dl/1,Tool,2,zip",
            'opensmashmm:https://gamebanana.com/dl/1,Mod,2,zip" -Repo C:\\evil',
            "https://gamebanana.com@evil.test/mods/123",
            "https://gamebanana.com:444/mods/1",
            "https://gamebanana.com/mods/../1",
            "file:///C:/test.zip",
            "https://gamebanana.com/mods/1\n",
            "x" * 2049,
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                links.parse(value)

    def test_file_must_belong_to_submission(self):
        q = SimpleNamespace(
            client=SimpleNamespace(
                detail=Mock(return_value={"files": [{"id": 2, "name": "own.zip"}]})
            ),
            enqueue=Mock(),
        )
        with self.assertRaisesRegex(ValueError, "gehoert"):
            links.accept(q, "opensmashmm:https://gamebanana.com/dl/1,Mod,10,zip")
        q.enqueue.assert_not_called()

    def test_extension_checked_then_same_queue(self):
        q = SimpleNamespace(
            client=SimpleNamespace(
                detail=Mock(return_value={"files": [{"id": 2, "name": "own.rar"}]})
            ),
            enqueue=Mock(return_value={"id": "job"}),
        )
        with self.assertRaisesRegex(ValueError, "Archivformat"):
            links.accept(q, "opensmashmm:https://gamebanana.com/dl/2,Mod,10,zip")
        self.assertEqual(
            dict(mode="queued", job={"id": "job"}),
            links.accept(q, "opensmashmm:https://gamebanana.com/dl/2,Mod,10,rar"),
        )
        q.enqueue.assert_called_once_with("Mod", 10, 2)


if __name__ == "__main__":
    unittest.main()
