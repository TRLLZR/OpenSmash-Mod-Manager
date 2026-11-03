"""Batch safety tests use only temporary synthetic fixtures, no real mods."""

import json, stat, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import test_modmanager as fixture

m = fixture.m
import batch_import as b


class BatchTests(unittest.TestCase):
    setUp = fixture.ManagerTests.setUp
    mod = fixture.ManagerTests.mod

    def archive(self, folder, name=None):
        path = Path(self.tmp.name) / (name or folder.name + ".zip")
        with zipfile.ZipFile(path, "w") as z:
            for p in folder.rglob("*"):
                if p.is_file():
                    z.write(p, "wrapper/" + p.relative_to(folder).as_posix())
        return path

    def sources(self, n=3):
        return [
            self.mod("Skin " + str(i), f"ui/replace/{i}.bntx", "own data " + str(i))
            for i in range(n)
        ]

    def run_batch(self, sources):
        plan = m.batch_preview(self.repo, sources)
        return plan, m.batch_install(self.repo, plan["job_id"], plan["token"])

    def test_multiple_zips(self):
        plan, result = self.run_batch([self.archive(p) for p in self.sources()])
        self.assertEqual(3, plan["ready"])
        self.assertEqual(3, result["installed"])
        self.assertFalse(list((b.path(m, self.repo, plan["job_id"])).glob("input-*")))

    def test_multiple_folders_and_single_undo(self):
        before = (m.root(self.repo) / "state.json").read_bytes()
        _, result = self.run_batch(self.sources())
        self.assertEqual(3, result["installed"])
        m.undo(self.repo)
        self.assertEqual(before, (m.root(self.repo) / "state.json").read_bytes())

    def test_mixed_invalid_zip_partial_success(self):
        one, two = self.sources(2)
        bad = Path(self.tmp.name) / "bad.zip"
        bad.write_text("invalid")
        plan, result = self.run_batch([one, self.archive(two), bad])
        self.assertEqual(
            ["ready", "ready", "invalid"], [i["status"] for i in plan["items"]]
        )
        self.assertEqual(2, result["installed"])

    def test_one_zip_with_two_mods(self):
        paths = self.sources(2)
        archive = Path(self.tmp.name) / "pack.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("README.txt", "Own QA bundle")
            for folder in paths:
                for p in folder.rglob("*"):
                    if p.is_file():
                        z.write(p, folder.name + "/" + p.relative_to(folder).as_posix())
        _, result = self.run_batch([archive])
        self.assertEqual(2, result["installed"])

    def test_bundle_bad_config_does_not_block_other_mod(self):
        paths = self.sources(2)
        (paths[1] / "config.json").write_text("{bad")
        plan, result = self.run_batch(paths)
        self.assertEqual(1, result["installed"])
        self.assertEqual(1, sum(i["status"] == "invalid" for i in plan["items"]))

    def test_duplicate_sources_contents_and_existing_paused(self):
        one = self.sources(1)[0]
        key = m.install(self.repo, one)["state"]["mods"][0]["id"]
        m.change(self.repo, key, "enable", False)
        plan, result = self.run_batch([one, one, self.archive(one)])
        self.assertEqual(0, plan["ready"])
        self.assertEqual(0, result["installed"])
        self.assertFalse(m.listing(self.repo)["mods"][0]["enabled"])

    def test_conflicts_are_skipped_independent_mod_installs(self):
        one, two, three = self.sources()
        (two / "ui/replace/0.bntx").write_text("different")
        plan, result = self.run_batch([one, two, three])
        self.assertEqual(2, result["installed"])
        self.assertIn("conflict", [i["status"] for i in plan["items"]])

    def test_conflict_arrives_after_preview(self):
        one, two = self.sources(2)
        plan = m.batch_preview(self.repo, [one, two])
        other = self.mod("Arrived later", "ui/replace/0.bntx", "different")
        m.install(self.repo, other)
        result = m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertEqual(1, result["installed"])
        self.assertIn("conflict", [i["status"] for i in result["items"]])

    def test_display_name_collision_is_explicit(self):
        one, two = self.sources(2)
        (two / "info.toml").write_text('display_name="Skin 0"')
        plan, result = self.run_batch([one, two])
        self.assertEqual(2, result["installed"])
        self.assertEqual("Skin 0 (2)", plan["items"][1]["name"])

    def test_traversal_devices_ads_and_case_duplicates(self):
        for bad_names in [
            ("../escape.txt",),
            ("/absolute.txt",),
            ("C:/bad.txt",),
            ("CON.txt",),
            ("ui/a:stream",),
            ("ui/A", "ui/a"),
        ]:
            archive = Path(self.tmp.name) / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as z:
                for name in bad_names:
                    z.writestr(name, "own QA")
            plan = m.batch_preview(self.repo, [archive])
            self.assertEqual("invalid", plan["items"][0]["status"])
            self.assertEqual(0, plan["ready"])
        self.assertFalse((m.root(self.repo) / "incoming/escape.txt").exists())

    def test_symlink_zip_entry_rejected(self):
        archive = Path(self.tmp.name) / "link.zip"
        entry = zipfile.ZipInfo("mod/ui/link")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr(entry, "../../outside")
        plan = m.batch_preview(self.repo, [archive])
        self.assertEqual("invalid", plan["items"][0]["status"])

    def test_cancel_preview(self):
        plan = m.batch_preview(self.repo, self.sources(), cancel=lambda: True)
        self.assertTrue(plan["cancelled"])
        self.assertEqual(0, plan["ready"])
        self.assertEqual([], m.listing(self.repo)["mods"])

    def test_cancel_before_commit_cleans_uncommitted_copies(self):
        plan = m.batch_preview(self.repo, self.sources())
        before = (m.root(self.repo) / "state.json").read_bytes()

        def event(e):
            if e["phase"] == "install" and e["current"] == 1:
                (b.path(m, self.repo, plan["job_id"]) / "cancel.request").write_text(
                    "cancel"
                )

        result = m.batch_install(
            self.repo, plan["job_id"], plan["token"], callback=event
        )
        self.assertTrue(result["cancelled"])
        self.assertEqual(0, result["installed"])
        self.assertEqual(before, (m.root(self.repo) / "state.json").read_bytes())
        self.assertFalse(list((m.root(self.repo) / "library").iterdir()))

    def test_one_copy_failure_does_not_block_other_items(self):
        plan = m.batch_preview(self.repo, self.sources())
        original = m.save_library

        def save(repo, record, assets):
            if record["name"] == "Skin 1":
                raise PermissionError("Synthetic locked file")
            return original(repo, record, assets)

        with patch.object(m, "save_library", side_effect=save):
            result = m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertEqual(2, result["installed"])
        self.assertEqual(1, result["failed"])

    def test_modified_snapshot_is_rejected_individually(self):
        plan = m.batch_preview(self.repo, self.sources(2))
        folder = b.path(m, self.repo, plan["job_id"])
        raw = json.loads((folder / "plan.json").read_text())
        item = raw["items"][0]
        entry = item["record"]["entries"][0]
        (folder / item["assets_rel"] / entry["source_path"]).write_text("changed")
        result = m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertEqual(1, result["installed"])
        self.assertEqual(1, result["failed"])

    def test_changed_plan_rejected(self):
        plan = m.batch_preview(self.repo, self.sources(1))
        file = b.path(m, self.repo, plan["job_id"]) / "plan.json"
        file.write_text(file.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "veraendert"):
            m.batch_install(self.repo, plan["job_id"], plan["token"])

    def test_commit_failure_rolls_back_and_cleans_pending(self):
        plan = m.batch_preview(self.repo, self.sources(2))
        before = (m.root(self.repo) / "state.json").read_bytes()
        profile = m.files(m.root(self.repo) / "profile")
        with patch.object(
            m.os, "replace", side_effect=OSError("Synthetic commit failure")
        ):
            result = m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertEqual(0, result["installed"])
        self.assertEqual(before, (m.root(self.repo) / "state.json").read_bytes())
        self.assertEqual(profile, m.files(m.root(self.repo) / "profile"))
        self.assertFalse(list(m.root(self.repo).glob("profile.pending-*")))

    def test_same_job_cannot_install_twice(self):
        plan, result = self.run_batch(self.sources(1))
        self.assertEqual(1, result["installed"])
        with self.assertRaisesRegex(ValueError, "abgeschlossen"):
            m.batch_install(self.repo, plan["job_id"], plan["token"])

    def test_global_preparation_failure_reports_every_ready_item(self):
        plan = m.batch_preview(self.repo, self.sources(3))
        before = (m.root(self.repo) / "state.json").read_bytes()
        with patch.object(
            m, "prepare_legacy", side_effect=ValueError("Missing legacy source")
        ):
            result = m.batch_install(self.repo, plan["job_id"], plan["token"])
        self.assertEqual(3, result["failed"])
        self.assertEqual(3, len(result["items"]))
        self.assertEqual(before, (m.root(self.repo) / "state.json").read_bytes())

    def test_cancel_reports_ready_and_duplicate_with_same_name(self):
        source = self.sources(1)[0]
        plan = m.batch_preview(self.repo, [source, source])
        result = m.batch_install(
            self.repo, plan["job_id"], plan["token"], cancel=lambda: True
        )
        self.assertEqual(
            ["cancelled", "duplicate"], sorted(x["status"] for x in result["items"])
        )
        self.assertEqual(2, len({x["item_id"] for x in result["items"]}))

    def test_active_job_cannot_run_twice(self):
        plan = m.batch_preview(self.repo, self.sources(1))
        folder = b.path(m, self.repo, plan["job_id"])
        with b.active(folder):
            with self.assertRaisesRegex(ValueError, "bereits verarbeitet"):
                m.batch_install(self.repo, plan["job_id"], plan["token"])

    def test_read_only_listing_does_not_hash_assets_but_mutation_does(self):
        source = self.sources(1)[0]
        m.install(self.repo, source)
        key = m.listing(self.repo)["mods"][0]["id"]
        file = next((m.root(self.repo) / "library" / key / "assets/ui").rglob("*.bntx"))
        file.write_text("manual change")
        self.assertEqual(1, len(m.listing(self.repo)["mods"]))
        with self.assertRaisesRegex(ValueError, "ausserhalb"):
            m.change(self.repo, key, "enable", True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
