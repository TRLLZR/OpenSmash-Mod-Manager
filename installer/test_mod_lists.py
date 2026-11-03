"""Share/import recipes use only synthetic assets and an in-memory provider."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch, Mock
import unittest

import mod_lists as lists
import test_modmanager as fixture
import test_gamebanana as download_fixture

m = fixture.m


class ModListTests(unittest.TestCase):
    setUp = fixture.ManagerTests.setUp
    mod = fixture.ManagerTests.mod
    queue = download_fixture.DownloadTests.queue

    def recipe(self, entries=None, enabled=True):
        self.queue()
        folder = self.mod("Own QA", "ui/replace/test.bntx", "Own QA asset")
        record = m.inspect(self.repo, folder)
        source = dict(
            provider="GameBanana",
            model="Mod",
            submission_id=10,
            file_id=20,
            sha256=hashlib.sha256(self.data).hexdigest(),
        )
        rows = entries or [
            dict(
                name="Own QA",
                signature=lists.identity(record),
                enabled=enabled,
                source=source,
            )
        ]
        path = Path(self.tmp.name) / "own.opensmash-list.json"
        path.write_text(
            json.dumps(dict(app=lists.APP, version=1, mods=rows)), encoding="utf-8"
        )
        return path

    def test_missing_mod_downloads_and_installs_with_origin(self):
        path = self.recipe()
        preview = lists.preview(m, self.repo, path)
        self.assertEqual(1, preview["ready"])
        result = lists.install(m, self.repo, path, preview["token"], client=self.client)
        self.assertEqual((1, 0), (result["installed"], result["failed"]))
        key = next(iter(m.load(self.repo)["mods"]))
        self.assertEqual(20, m.metadata(self.repo, key)["origin"]["file_id"])

    def test_existing_paused_mod_is_not_downloaded_or_reactivated(self):
        path = self.recipe()
        m.install(self.repo, Path(self.tmp.name) / "Own QA")
        key = next(iter(m.load(self.repo)["mods"]))
        m.change(self.repo, key, "enable", False)
        before = (m.root(self.repo) / "state.json").read_bytes()
        client = Mock()
        result = lists.install(
            m,
            self.repo,
            path,
            lists.preview(m, self.repo, path)["token"],
            client=client,
        )
        self.assertEqual(0, result["installed"])
        client.detail.assert_not_called()
        self.assertEqual(before, (m.root(self.repo) / "state.json").read_bytes())

    def test_conflict_installs_paused_without_changing_existing_selection(self):
        path = self.recipe()
        m.install(self.repo, self.mod("Prior", "ui/replace/test.bntx", "different"))
        prior = next(iter(m.load(self.repo)["mods"]))
        result = lists.install(
            m,
            self.repo,
            path,
            lists.preview(m, self.repo, path)["token"],
            client=self.client,
        )
        self.assertEqual(1, result["installed"])
        state = m.load(self.repo)
        self.assertTrue(state["mods"][prior]["enabled"])
        self.assertFalse(
            next(v["enabled"] for k, v in state["mods"].items() if k != prior)
        )

    def test_changed_archive_hash_never_installs_another_version(self):
        path = self.recipe()
        data = json.loads(path.read_text())
        data["mods"][0]["source"]["sha256"] = "f" * 64
        path.write_text(json.dumps(data), encoding="utf-8")
        result = lists.install(
            m,
            self.repo,
            path,
            lists.preview(m, self.repo, path)["token"],
            client=self.client,
        )
        self.assertEqual((0, 1), (result["installed"], result["failed"]))
        self.assertFalse(m.load(self.repo)["mods"])

    def test_review_token_rejects_changed_list_before_download(self):
        path = self.recipe()
        preview = lists.preview(m, self.repo, path)
        path.write_text(path.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Vorschau"):
            lists.install(m, self.repo, path, preview["token"], client=Mock())

    def test_export_contains_no_local_paths_or_assets_and_marks_manual_sources(self):
        self.recipe()
        m.install(self.repo, Path(self.tmp.name) / "Own QA")
        output = Path(self.tmp.name) / "share.json"
        report = lists.export(m, self.repo, output)
        self.assertEqual(1, report["manual"])
        self.assertNotIn(str(self.repo), output.read_text())
        rows, _ = lists.read(output)
        self.assertIsNone(rows[0]["source"])

    def test_arbitrary_url_cannot_become_a_download(self):
        path = self.recipe()
        doc = json.loads(path.read_text())
        doc["mods"][0]["source"]["url"] = "http://127.0.0.1/secret"
        path.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Download-URLs"):
            lists.preview(m, self.repo, path)

    def test_unrequested_bundle_members_are_not_installed(self):
        path = self.recipe()
        self.queue(
            {
                "Bundle A/ui/replace/test.bntx": b"Own QA asset",
                "Bundle B/ui/replace/b.bntx": b"extra",
            }
        )
        doc = json.loads(path.read_text())
        doc["mods"][0]["source"]["sha256"] = hashlib.sha256(self.data).hexdigest()
        path.write_text(json.dumps(doc), encoding="utf-8")
        result = lists.install(
            m,
            self.repo,
            path,
            lists.preview(m, self.repo, path)["token"],
            client=self.client,
        )
        self.assertEqual((1, 0), (result["installed"], result["failed"]))
        self.assertEqual(1, len(m.load(self.repo)["mods"]))

    def test_paused_recipe_stays_paused(self):
        path = self.recipe(enabled=False)
        result = lists.install(
            m,
            self.repo,
            path,
            lists.preview(m, self.repo, path)["token"],
            client=self.client,
        )
        self.assertEqual(1, result["installed"])
        self.assertFalse(next(iter(m.load(self.repo)["mods"].values()))["enabled"])

    def test_cancel_before_download_leaves_library_untouched(self):
        path = self.recipe()
        before = (m.root(self.repo) / "state.json").read_bytes()
        with self.assertRaises(lists.batch.Cancelled):
            lists.install(
                m,
                self.repo,
                path,
                lists.preview(m, self.repo, path)["token"],
                client=self.client,
                cancel=lambda: True,
            )
        self.assertEqual(before, (m.root(self.repo) / "state.json").read_bytes())

    def test_two_requested_mods_share_one_download_and_one_undo(self):
        path = self.recipe()
        self.queue(
            {"A/ui/replace/test.bntx": b"Own QA asset", "B/ui/replace/b.bntx": b"B"}
        )
        doc = json.loads(path.read_text())
        doc["mods"][0]["source"]["sha256"] = hashlib.sha256(self.data).hexdigest()
        b = m.inspect(self.repo, self.mod("B", "ui/replace/b.bntx", "B"))
        doc["mods"].append(
            dict(
                name="B",
                signature=lists.identity(b),
                enabled=True,
                source=doc["mods"][0]["source"],
            )
        )
        path.write_text(json.dumps(doc), encoding="utf-8")
        self.client.transport = Mock(wraps=self.client.transport)
        result = lists.install(
            m,
            self.repo,
            path,
            lists.preview(m, self.repo, path)["token"],
            client=self.client,
        )
        self.assertEqual(2, result["installed"])
        self.assertEqual(1, self.client.transport.call_count)
        m.undo(self.repo)
        self.assertFalse(m.load(self.repo)["mods"])

    def test_missing_cached_archive_is_redownloaded(self):
        import downloads

        path = self.recipe()
        queue = downloads.Queue(self.repo, self.client)
        job = queue.enqueue("Mod", 10, 20)
        queue.run()
        queue.paths(job["id"], "qa.zip")[1].unlink()
        result = lists.install(
            m,
            self.repo,
            path,
            lists.preview(m, self.repo, path)["token"],
            client=self.client,
        )
        self.assertEqual(1, result["installed"])

    def test_cancel_during_download_removes_partial_and_never_installs(self):
        import downloads

        path = self.recipe()
        cancelled = False

        class Response(download_fixture.Response):
            def read(response, n=-1):
                nonlocal cancelled
                data = super().read(n)
                cancelled = True
                return data

        self.client.transport = lambda *a, **k: Response(
            self.data, {"Content-Length": str(len(self.data))}
        )
        with self.assertRaises(lists.batch.Cancelled):
            lists.install(
                m,
                self.repo,
                path,
                lists.preview(m, self.repo, path)["token"],
                client=self.client,
                cancel=lambda: cancelled,
            )
        self.assertFalse(m.load(self.repo)["mods"])
        queue = downloads.Queue(self.repo, self.client)
        for job in queue.jobs():
            self.assertEqual("cancelled", job["status"])
            self.assertFalse(any(p.exists() for p in queue.paths(job["id"], "qa.zip")))
