"""Deterministic API/security/streaming tests. All archives contain own fixture bytes."""

import contextlib, hashlib, io, json, socket, threading, time, unittest, zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError, URLError
import gamebanana as gb, downloads as dl
import test_modmanager as fixture
import batch_import as batch

m = fixture.m


class Response(io.BytesIO):
    def __init__(self, body, headers=None):
        super().__init__(body)
        self.headers = headers or {}


def row(number=10):
    return dict(
        _idRow=number,
        _sModelName="Mod",
        _sName="Own QA skin",
        _aGame={"_idRow": 6498},
        _aSubmitter={"_sName": "QA"},
        _aCategory={"_sName": "UI"},
        _tsDateModified=123,
        _sText="<p>Own text</p><script>evil()</script>",
        _aFiles=[],
    )


class ApiTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        scratch = Path(__file__).resolve().parent.parent / "test-scratch"
        scratch.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.calls = []

        def transport(url, *args):
            self.calls.append(url)
            return Response(json.dumps(self.response).encode())

        self.client = gb.Client(Path(self.tmp.name), transport, rate=0)

    def test_schema_plain_text_and_cache(self):
        self.response = row()
        a = self.client.detail("Mod", 10)
        b = self.client.detail("Mod", 10)
        self.assertEqual(1, len(self.calls))
        self.assertEqual("Own text", a["description"])
        self.assertEqual("Unknown", b["compatibility"])

    def test_search_scope_pagination_and_empty(self):
        self.response = {
            "_aMetadata": {"_nRecordCount": 32, "_nPerpage": 15},
            "_aRecords": [row()],
        }
        result = self.client.browse("Dry Bowser", page=2)
        self.assertTrue(result["has_next"])
        self.assertEqual("relevance", result["ordering"])
        self.assertIn("_idGameRow=6498", self.calls[-1])
        self.assertIn("_nPage=2", self.calls[-1])
        self.response = {"_aMetadata": {"_nRecordCount": 0}, "_aRecords": []}
        self.assertEqual([], self.client.browse("no matches")["items"])

    def test_categories_sorts_and_filter_parameters(self):
        config = {
            "categories": [{"id": 3330, "name": "Skins", "model": "Mod"}],
            "sorts": {"Mod": ["likes"], "Sound": ["newest"]},
        }
        self.response = {"_aMetadata": {"_nRecordCount": 1}, "_aRecords": [row()]}
        with patch.object(self.client, "config", return_value=config):
            self.client.browse(category=3330, sort="likes")
            self.assertIn("Generic_Category%5D=3330", self.calls[-1])
            self.assertIn("Generic_MostLiked", self.calls[-1])
            with self.assertRaises(ValueError):
                self.client.browse(category=123, sort="likes")
            with self.assertRaises(ValueError):
                self.client.browse(sort="downloads")

    def test_wrong_game_never_accepted(self):
        self.response = row()
        self.response["_aGame"]["_idRow"] = 1
        with self.assertRaises(ValueError):
            self.client.detail("Mod", 10)

    def test_file_variants_not_implicitly_selected_and_download_only(self):
        self.response = row()
        self.response["_aFiles"] = [
            dict(_idRow=i, _sFile=n, _nFilesize=30, _sMd5Checksum="a" * 32)
            for i, n in [
                (1, "one.zip"),
                (2, "other.rar"),
                (3, "direct.7z"),
                (4, "data.tar"),
            ]
        ]
        result = self.client.detail("Mod", 10)
        self.assertEqual(4, len(result["files"]))
        self.assertNotIn("selected_file", result)
        self.assertTrue(result["files"][2]["supported"])
        self.assertTrue(result["files"][1]["supported"])
        self.assertFalse(result["files"][3]["supported"])
        self.assertTrue(result["files"][3]["downloadable"])

    def test_permission_and_av_restrictions(self):
        self.response = row()
        self.response["_bIsWithheld"] = True
        self.response["_aFiles"] = [dict(_idRow=1, _sFile="a.zip", _nFilesize=10)]
        self.assertFalse(self.client.detail("Mod", 10)["files"][0]["downloadable"])
        self.response = row()
        self.response["_aFiles"] = [
            dict(_idRow=2, _sFile="b.zip", _nFilesize=10, _sAvResult="infected")
        ]
        self.assertFalse(self.client.detail("Mod", 11)["files"][0]["downloadable"])

    def test_timeout_retries_and_rate_limit(self):
        with patch.object(
            self.client, "transport", side_effect=URLError("timeout")
        ), patch.object(gb, "pause"):
            with self.assertRaises(gb.ServiceError):
                self.client.detail("Mod", 10)
            self.assertEqual(3, self.client.transport.call_count)
        with patch.object(
            self.client,
            "transport",
            side_effect=HTTPError(gb.API, 429, "limited", {"Retry-After": "120"}, None),
        ), patch.object(gb, "pause"):
            with self.assertRaisesRegex(gb.ServiceError, "120"):
                self.client.detail("Mod", 10)

    def test_403_no_bypass(self):
        with patch.object(
            self.client,
            "transport",
            side_effect=HTTPError(gb.API, 403, "forbidden", {}, None),
        ):
            with self.assertRaisesRegex(ValueError, "Anmeldung"):
                self.client.detail("Mod", 10)

    def test_malformed_response(self):
        with patch.object(
            self.client, "transport", return_value=Response(b"<html>no json</html>")
        ):
            with self.assertRaisesRegex(ValueError, "API-Antwort"):
                self.client.detail("Mod", 10)

    def test_redirect_url_security(self):
        for url in (
            "http://files.gamebanana.com/a.zip",
            "https://evil.test/a.zip",
            "https://gamebanana.com@evil.test/a.zip",
            "https://files.gamebanana.com:444/a.zip",
            "https://files.gamebanana.com/a\n.zip",
            "https://files.gamebanana.com.evil.test/a.zip",
        ):
            with self.assertRaises(ValueError):
                gb.safe_url(url, "download", False)
        gb.safe_url("https://filecache54.gamebanana.com/mods/a.zip", "download", False)
        with patch.object(
            socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]
        ):
            with self.assertRaisesRegex(ValueError, "oeffentlich"):
                gb.safe_url("https://files.gamebanana.com/a.zip", "download")

    def test_thumbnail_cache_and_invalid_image(self):
        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (100, 60), "aqua").save(buffer, format="PNG")
        calls = []

        def image(url, *args):
            calls.append(url)
            return Response(buffer.getvalue())

        with patch.object(self.client, "transport", side_effect=image):
            a = self.client.thumbnail("https://images.gamebanana.com/img/a.png")
            b = self.client.thumbnail("https://images.gamebanana.com/img/a.png")
            self.assertEqual(a, b)
            self.assertEqual(1, len(calls))
            self.assertTrue(Path(a).exists())
        with patch.object(
            self.client, "transport", return_value=Response(b"<svg><script/></svg>")
        ):
            with self.assertRaises(Exception):
                self.client.thumbnail("https://images.gamebanana.com/img/b.svg")

    def test_character_categories_are_provider_ids(self):
        game = {"_aModRootCategories": [{"_idRow": 3330, "_sName": "Skins"}]}
        children = [
            {
                "_sName": "Sora",
                "_sUrl": "https://gamebanana.com/mods/cats/14759",
                "_nItemCount": 214,
            },
            {"_sName": "Fake", "_sUrl": "https://evil.test/cats/123"},
        ]
        filters = {"_aSorts": [{"_sAlias": "Generic_Newest"}]}

        def endpoint(path, *args, **kwargs):
            return (
                game
                if path.startswith("Game/")
                else (
                    {"_aRecords": children}
                    if path.endswith("SubCategories")
                    else filters
                )
            )

        with patch.object(self.client, "json", side_effect=endpoint):
            config = self.client.config()
        self.assertEqual(
            [{"id": 14759, "name": "Sora", "count": 214}], config["characters"]
        )
        self.assertEqual(3330, config["skin_category"])

    def test_character_filter_is_server_side_with_paging(self):
        config = {
            "skin_category": 3330,
            "characters": [{"id": 14759, "name": "Sora"}],
            "sorts": {"Mod": ["newest"]},
        }
        self.response = {
            "_aMetadata": {"_nRecordCount": 214, "_nPerpage": 15},
            "_aRecords": [row()],
        }
        with patch.object(self.client, "config", return_value=config):
            result = self.client.browse(character=14759, category=3330, page=2)
            self.assertIn("Generic_Category%5D=14759", self.calls[-1])
            self.assertIn("_nPage=2", self.calls[-1])
            self.assertEqual(214, result["total"])
            with self.assertRaisesRegex(ValueError, "getrennte"):
                self.client.browse(query="Mario", character=14759)
            with self.assertRaises(ValueError):
                self.client.browse(character=123)
            with self.assertRaises(ValueError):
                self.client.browse(character=14759, model="Sound")

    def test_array_subcategories_schema_and_cache(self):
        self.response = [
            {"_sName": "Sora", "_sUrl": "https://gamebanana.com/mods/cats/14759"}
        ]
        a = self.client.json("ModCategory/3330/SubCategories")
        b = self.client.json("ModCategory/3330/SubCategories")
        self.assertEqual(a, b)
        self.assertEqual(1, len(self.calls))
        self.assertEqual("Sora", a["_aRecords"][0]["_sName"])

    def test_fullscreen_uses_original_and_preserves_resolution(self):
        from PIL import Image

        data = row()
        data["_aPreviewMedia"] = {
            "_aImages": [
                {
                    "_sBaseUrl": "https://images.gamebanana.com/img/ss/mods",
                    "_sFile": "original.png",
                    "_sFile220": "220-original.png",
                }
            ]
        }
        result = gb.summary(data, "Mod")
        self.assertTrue(result["thumbnail"].endswith("220-original.png"))
        self.assertTrue(result["images"][0].endswith("/original.png"))
        stream = io.BytesIO()
        Image.new("RGB", (1600, 900), "aqua").save(stream, format="PNG")
        with patch.object(
            self.client, "transport", side_effect=lambda *a: Response(stream.getvalue())
        ):
            small = self.client.thumbnail(result["images"][0])
            full = self.client.thumbnail(result["images"][0], full=True)
        with Image.open(small) as im:
            self.assertEqual(720, im.width)
        with Image.open(full) as im:
            self.assertEqual(1600, im.width)
        self.assertNotEqual(small, full)


class DownloadTests(unittest.TestCase):
    setUp = fixture.ManagerTests.setUp
    mod = fixture.ManagerTests.mod

    def test_clear_completed_queued_failed_and_abandoned_downloads_preserves_mods(self):
        q = self.queue()
        first = q.enqueue("Mod", 10, 20)
        q.run()
        plan = q.preview([first["id"]])
        m.batch_install(self.repo, plan["job_id"], plan["token"])
        before = (m.root(self.repo) / "state.json").read_bytes()
        profile = (m.root(self.repo) / "profile/profile.json").read_bytes()
        for fileid, status in [(21, "queued"), (22, "failed"), (23, "downloading")]:
            self.file["id"] = fileid
            job = q.enqueue("Mod", 10, fileid)
            q.update(job["id"], status=status)
            q.paths(job["id"], "qa.zip")[0].write_bytes(b"own partial")
        result = q.clear()
        self.assertEqual(0, result["pending"])
        self.assertEqual(4, result["removed"])
        self.assertFalse(q.jobs())
        self.assertEqual(before, (m.root(self.repo) / "state.json").read_bytes())
        self.assertEqual(
            profile, (m.root(self.repo) / "profile/profile.json").read_bytes()
        )

    def test_clear_during_transfer_finishes_after_cancel_closes_stream(self):
        q = self.queue()
        job = q.enqueue("Mod", 10, 20)
        observed = []

        class ClearResponse(Response):
            def read(response, n=-1):
                value = super().read(n)
                observed.append(q.clear())
                return value

        with patch.object(
            self.client, "transport", return_value=ClearResponse(self.data)
        ):
            q.run()
        self.assertTrue(observed)
        self.assertFalse(q.jobs())
        self.assertFalse(any(p.exists() for p in q.paths(job["id"], "qa.zip")))

    def test_clear_empty_is_harmless(self):
        self.assertEqual(dict(items=[], removed=0, pending=0), self.queue().clear())

    def test_download_only_file_can_be_saved_but_not_installed(self):
        q = self.queue()
        self.file.update(name="own.tar", supported=False, downloadable=True)
        job = q.enqueue("Mod", 10, 20)
        q.run()
        job = q.get(job["id"])
        self.assertEqual("downloaded", job["status"])
        self.assertEqual("DownloadOnly", job["compatibility"])
        with self.assertRaises(ValueError):
            q.preview([job["id"]])
        target = Path(self.tmp.name) / "own saved.tar"
        q.save(job["id"], target)
        self.assertEqual(self.data, target.read_bytes())
        with self.assertRaises(ValueError):
            q.save(job["id"], self.repo / "build/saves/should-not-exist.bin")

    def test_7z_download_uses_same_import_and_provenance(self):
        import subprocess, sevenzip_support

        q = self.queue()
        folder = self.mod("Own Seven", "ui/replace/test.bntx", "own 7z download")
        archive = Path(self.tmp.name) / "own.7z"
        subprocess.run(
            [str(sevenzip_support.binary()), "a", "-t7z", str(archive), folder.name],
            cwd=folder.parent,
            check=True,
            capture_output=True,
        )
        self.data = archive.read_bytes()
        self.file.update(
            name="own.7z", size=len(self.data), md5=hashlib.md5(self.data).hexdigest()
        )
        job = q.enqueue("Mod", 10, 20)
        q.run()
        self.assertEqual("downloaded", q.get(job["id"])["status"])
        plan = q.preview([job["id"]])
        result = m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertEqual(1, result["installed"])

    def queue(self, contents=None):
        raw = io.BytesIO()
        with zipfile.ZipFile(raw, "w") as z:
            for name, value in (
                contents or {"Own QA/ui/replace/test.bntx": b"Own QA asset"}
            ).items():
                z.writestr(name, value)
        self.data = raw.getvalue()
        self.file = dict(
            id=20,
            name="qa.zip",
            size=len(self.data),
            md5=hashlib.md5(self.data).hexdigest(),
            date=123,
            version="1",
            supported=True,
            description="",
            archived=False,
            download_url="https://gamebanana.com/dl/20",
        )
        self.detail = dict(
            title="Own QA",
            author="QA",
            source_url="https://gamebanana.com/mods/10",
            files=[self.file],
        )
        self.client = SimpleNamespace(
            detail=lambda *a, **k: self.detail,
            transport=lambda *a, **k: Response(
                self.data, {"Content-Length": str(len(self.data))}
            ),
        )
        return dl.Queue(self.repo, self.client)

    def test_explicit_variant_download_preview_install_origin_and_duplicate(self):
        q = self.queue()
        with self.assertRaises(ValueError):
            q.enqueue("Mod", 10, None)
        job = q.enqueue("Mod", 10, 20)
        self.assertEqual(job["id"], q.enqueue("Mod", 10, 20)["id"])
        q.run()
        job = q.get(job["id"])
        self.assertEqual("downloaded", job["status"], job["message"])
        self.assertEqual("Experimental", job["compatibility"])
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), job["sha256"])
        plan = q.preview([job["id"]])
        result = m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertEqual(1, result["installed"])
        origin = m.listing(self.repo)["mods"][0]["origin"]
        self.assertEqual(20, origin["file_id"])
        self.assertEqual("QA", origin["author"])
        again = q.preview([job["id"]])
        self.assertEqual(0, again["ready"])
        self.assertEqual("existing", again["items"][0]["status"])

    def test_remove_finished_download_preserves_installed_mod_and_selection(self):
        q = self.queue()
        job = q.enqueue("Mod", 10, 20)
        q.run()
        plan = q.preview([job["id"]])
        m.batch_install(self.repo, plan["job_id"], plan["token"])
        before = m.files(m.root(self.repo) / "library")
        state = (m.root(self.repo) / "state.json").read_bytes()
        result = q.remove([job["id"]])
        self.assertEqual(result["removed"], 1)
        self.assertEqual(result["items"], [])
        self.assertFalse(q.paths(job["id"], "qa.zip")[1].exists())
        self.assertEqual(before, m.files(m.root(self.repo) / "library"))
        self.assertEqual(state, (m.root(self.repo) / "state.json").read_bytes())

    def test_remove_active_or_mixed_selection_is_atomic(self):
        q = self.queue()
        first = q.enqueue("Mod", 10, 20)
        q.run()
        second = q.enqueue("Mod", 11, 20)
        with self.assertRaises(ValueError):
            q.remove([first["id"], second["id"]])
        self.assertEqual(len(q.jobs()), 2)
        self.assertTrue(q.paths(first["id"], "qa.zip")[1].exists())

    def test_remove_ignores_saved_external_path(self):
        q = self.queue()
        job = q.enqueue("Mod", 10, 20)
        q.run()
        external = Path(self.tmp.name) / "keep.zip"
        external.write_bytes(b"own external file")
        q.update(job["id"], path=str(external))
        q.remove([job["id"]])
        self.assertEqual(external.read_bytes(), b"own external file")

    def test_md5_failure_cleans_partial_and_final(self):
        q = self.queue()
        self.file["md5"] = "0" * 32
        job = q.enqueue("Mod", 10, 20)
        q.run()
        result = q.get(job["id"])
        self.assertEqual("failed", result["status"])
        self.assertIn("Pruefsumme", result["message"])
        self.assertFalse(any(p.exists() for p in q.paths(job["id"], "qa.zip")))

    def test_cancel_and_retry(self):
        q = self.queue()
        job = q.enqueue("Mod", 10, 20)
        q.control(job["id"], "cancel")
        q.run()
        self.assertEqual("cancelled", q.get(job["id"])["status"])
        q.control(job["id"], "retry")
        q.run()
        self.assertEqual("downloaded", q.get(job["id"])["status"])

    def test_interruption_recovery_and_transient_retry(self):
        q = self.queue()
        job = q.enqueue("Mod", 10, 20)
        q.update(job["id"], status="downloading")
        part, _ = q.paths(job["id"], "qa.zip")
        part.write_bytes(b"partial")
        q.run()
        self.assertEqual("interrupted", q.get(job["id"])["status"])
        self.assertFalse(part.exists())
        q.control(job["id"], "retry")
        with patch.object(
            self.client,
            "transport",
            side_effect=[URLError("interrupted"), Response(self.data)],
        ), patch.object(gb, "pause"):
            q.run()
        self.assertEqual("downloaded", q.get(job["id"])["status"])

    def test_traversal_and_archive_bomb_not_installable(self):
        q = self.queue({"../escape": b"bad"})
        job = q.enqueue("Mod", 10, 20)
        q.run()
        self.assertEqual("failed", q.get(job["id"])["status"])
        self.assertFalse((q.folder.parent / "escape").exists())
        q = self.queue()
        job = q.enqueue("Mod", 11, 20)
        with patch.object(batch, "MAX_BYTES", 1):
            q.run()
        self.assertEqual("failed", q.get(job["id"])["status"])

    def test_corrupt_archive_and_wrong_size(self):
        q = self.queue()
        self.data = b"not zip"
        self.file.update(size=len(self.data), md5=hashlib.md5(self.data).hexdigest())
        job = q.enqueue("Mod", 10, 20)
        q.run()
        self.assertEqual("failed", q.get(job["id"])["status"])

    def test_two_stream_limit_and_independent_failure(self):
        q = self.queue()
        jobs = [q.enqueue("Mod", n, 20) for n in range(10, 15)]
        active = 0
        peak = 0
        lock = threading.Lock()

        def transfer(key):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.03)
            q.update(key, status="failed" if key == jobs[0]["id"] else "downloaded")
            with lock:
                active -= 1

        with patch.object(q, "transfer", side_effect=transfer):
            q.run()
        self.assertEqual(2, peak)
        self.assertEqual(4, sum(j["status"] == "downloaded" for j in q.jobs()))

    def test_local_download_modified_before_review_rejected(self):
        q = self.queue()
        job = q.enqueue("Mod", 10, 20)
        q.run()
        _, path = q.paths(job["id"], "qa.zip")
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "extern"):
            q.preview([job["id"]])

    def test_cancel_during_stream_removes_partial(self):
        q = self.queue()
        job = q.enqueue("Mod", 10, 20)

        class CancelResponse(Response):
            def read(response, n=-1):
                value = super().read(n)
                q.control(job["id"], "cancel")
                return value

        with patch.object(
            self.client, "transport", return_value=CancelResponse(self.data)
        ):
            q.run()
        self.assertEqual("cancelled", q.get(job["id"])["status"])
        self.assertFalse(any(p.exists() for p in q.paths(job["id"], "qa.zip")))

    def test_midstream_failure_retries_from_zero(self):
        q = self.queue()
        job = q.enqueue("Mod", 10, 20)

        class Interrupted(Response):
            count = 0

            def read(response, n=-1):
                response.count += 1
                if response.count > 1:
                    raise URLError("connection lost during transfer")
                return super().read(20)

        with patch.object(
            self.client,
            "transport",
            side_effect=[Interrupted(self.data), Response(self.data)],
        ), patch.object(gb, "pause"):
            q.run()
        self.assertEqual("downloaded", q.get(job["id"])["status"])
        self.assertEqual(2, q.get(job["id"])["attempt"])

    def test_existing_worker_not_reclassified_as_interrupted(self):
        q = self.queue()
        job = q.enqueue("Mod", 10, 20)
        q.update(job["id"], status="downloading")
        with q.worker_lock() as held:
            self.assertTrue(held)
            self.assertTrue(q.run()["running"])
        self.assertEqual("downloading", q.get(job["id"])["status"])

    def test_rar_uses_same_validator_and_provenance(self):
        q = self.queue()
        self.data = (
            Path(__file__)
            .with_name("test_data")
            .joinpath("rar/ui-skin-b.rar")
            .read_bytes()
        )
        self.file.update(
            name="qa.rar", size=len(self.data), md5=hashlib.md5(self.data).hexdigest()
        )
        job = q.enqueue("Mod", 10, 20)
        q.run()
        self.assertEqual(
            "downloaded", q.get(job["id"])["status"], q.get(job["id"])["message"]
        )
        self.assertEqual(1, q.preview([job["id"]])["ready"])

    def test_update_check_uses_files_and_hashes(self):
        q = self.queue()
        job = q.enqueue("Mod", 10, 20)
        q.run()
        plan = q.preview([job["id"]])
        m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertEqual(
            "Keine neuere Anbieterdatei",
            dl.updates(self.repo, self.client)["items"][0]["status"],
        )
        candidate = dict(self.file, id=21, date=124, version="2")
        self.detail["files"] = [self.file, candidate]
        result = dl.updates(self.repo, self.client)["items"][0]
        self.assertEqual(21, result["candidates"][0]["id"])
        self.assertFalse(result["changed"])
        self.detail["files"] = [dict(self.file, md5="f" * 32)]
        self.assertTrue(dl.updates(self.repo, self.client)["items"][0]["changed"])


if __name__ == "__main__":
    unittest.main()
