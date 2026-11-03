"""Observable I/O, crash boundaries and concurrent workers in isolated repositories."""

import json, os, shutil, subprocess, sys, time, unittest
from pathlib import Path
from unittest.mock import patch
import test_modmanager as fixture
import catalog, deployment, batch_import as batch

m = fixture.m


class IncrementalTests(unittest.TestCase):
    setUp = fixture.ManagerTests.setUp
    mod = fixture.ManagerTests.mod

    def installed(self):
        sources = [
            self.mod("QA A", "ui/replace/a.bntx", "A"),
            self.mod("QA B", "ui/replace/b.bntx", "B"),
        ]
        return [m.install(self.repo, s)["state"]["mods"][-1]["id"] for s in sources]

    def test_only_affected_assets_validate_and_directories_reused(self):
        a, b = self.installed()
        root = m.root(self.repo)
        manifest = json.loads((root / "profile/profile.json").read_text())
        path = root / "profile" / manifest["asset_dir"] / a / "ui/replace/a.bntx"
        inode = path.stat().st_ino
        with patch.object(
            m.base, "digest", wraps=m.base.digest
        ) as digest, patch.object(shutil, "copy2", wraps=shutil.copy2) as copy:
            m.change(self.repo, b, "enable", False)
            self.assertFalse(
                any(
                    a + "/assets" in str(c.args[0]).replace("\\", "/")
                    or ("/" + a + "/") in str(c.args[0]).replace("\\", "/")
                    for c in digest.call_args_list
                )
            )
            self.assertFalse(
                any(
                    "/ui/" in str(c.args[0]).replace("\\", "/")
                    for c in copy.call_args_list
                )
            )
        self.assertEqual(inode, path.stat().st_ino)
        m.change(self.repo, b, "enable", True)
        self.assertEqual(inode, path.stat().st_ino)
        m.profile_valid(self.repo, force=True)

    def test_noop_no_commit_and_bulk_one_history(self):
        a, b = self.installed()
        history = len(m.load(self.repo)["history"])
        with patch.object(
            m, "commit", side_effect=AssertionError("unnecessary commit")
        ):
            m.change(self.repo, a, "enable", True)
        m.change_many(self.repo, {a: False, b: False})
        self.assertEqual(history + 1, len(m.load(self.repo)["history"]))
        self.assertFalse(any(r["enabled"] for r in m.listing(self.repo)["mods"]))
        m.undo(self.repo)
        self.assertTrue(all(r["enabled"] for r in m.listing(self.repo)["mods"]))

    def test_removed_library_atomic_rollback_and_lost_cache(self):
        a, b = self.installed()
        root = m.root(self.repo)
        inode = (root / "library" / a).stat().st_ino
        m.change(self.repo, a, "remove")
        self.assertFalse((root / "library" / a).exists())
        self.assertEqual(inode, catalog.location(self.repo, a).stat().st_ino)
        (root / "index.sqlite").unlink()
        m.undo(self.repo)
        self.assertEqual(inode, (root / "library" / a).stat().st_ino)
        m.profile_valid(self.repo, force=True)

    def test_full_refresh_detects_changes_and_forces_hashes(self):
        a, b = self.installed()
        file = catalog.location(self.repo, a) / "assets/ui/replace/a.bntx"
        file.write_text("external")
        result = m.refresh(self.repo)
        self.assertIn(a, result["validation_errors"])
        with self.assertRaisesRegex(ValueError, "ausserhalb"):
            m.change(self.repo, a, "remove")
        file.write_text("A")
        with patch.object(m.base, "digest", wraps=m.base.digest) as digest:
            m.refresh(self.repo)
            self.assertIn(file, [c.args[0] for c in digest.call_args_list])

    def test_cancel_after_moves_recovers_exact_profile(self):
        a, b = self.installed()
        root = m.root(self.repo)
        before = (root / "state.json").read_bytes()
        assets = m.files(root / "profile")
        cancelled = False
        rename = Path.rename

        def move(path, destination):
            nonlocal cancelled
            result = rename(path, destination)
            if path == root / "profile/ultimate/mods" / a:
                cancelled = True
            return result

        with patch.object(Path, "rename", move):
            with self.assertRaises(batch.Cancelled):
                m.change(self.repo, b, "enable", False, cancel=lambda: cancelled)
        self.assertEqual(before, (root / "state.json").read_bytes())
        self.assertEqual(assets, m.files(root / "profile"))
        self.assertFalse((root / "transaction.json").exists())

    def crash(self, point, action="disable"):
        a, b = self.installed()
        root = m.root(self.repo)
        before = (root / "state.json").read_bytes()
        assets = m.files(root / "profile")
        code = r"""
import os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import modmanager as m
repo=Path(sys.argv[2]);key=sys.argv[3];point=sys.argv[4];action=sys.argv[5];root=m.root(repo)
m.idle=lambda:None
def make_sd(repo,p):
 (p/'atmosphere').mkdir(parents=True);(p/'ultimate/arcropolis/resources').mkdir(parents=True)
m.arc_backend.make_sd=make_sd
original=Path.rename
def rename(path,dst):
 result=original(path,dst)
 if point=='move' and 'profile.pending-' in str(dst) and '/mods/' in str(dst).replace('\\','/'):os._exit(88)
 if point=='old' and path==root/'profile':os._exit(88)
 if point=='swap' and path.name.startswith('profile.pending-') and Path(dst)==root/'profile':os._exit(88)
 if point=='removal' and path==root/'library'/key:os._exit(88)
 return result
Path.rename=rename
replace=os.replace
def save(src,dst):
 result=replace(src,dst)
 if point=='state' and Path(dst)==root/'state.json':os._exit(88)
 return result
os.replace=save
m.change(repo,key,'remove' if action=='remove' else 'enable',False)
"""
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                code,
                str(Path(__file__).parent),
                str(self.repo),
                b,
                point,
                action,
            ],
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(88, result.returncode, result.stderr.decode(errors="replace"))
        recovered = m.load(self.repo)
        m.profile_valid(self.repo, force=True)
        if point in ("state", "removal"):
            if action == "remove":
                self.assertNotIn(b, recovered["mods"])
                self.assertTrue(catalog.location(self.repo, b).exists())
            else:
                self.assertFalse(recovered["mods"][b]["enabled"])
            m.undo(self.repo)
            self.assertEqual(before, (root / "state.json").read_bytes())
        else:
            self.assertEqual(before, (root / "state.json").read_bytes())
            self.assertEqual(assets, m.files(root / "profile"))
        self.assertFalse((root / "transaction.json").exists())

    def test_forced_exit_after_mod_move(self):
        self.crash("move")

    def test_forced_exit_after_old_profile_rename(self):
        self.crash("old")

    def test_forced_exit_after_profile_swap(self):
        self.crash("swap")

    def test_forced_exit_after_state_commit(self):
        self.crash("state")

    def test_forced_exit_during_removal_finalize(self):
        self.crash("removal", "remove")

    def test_concurrent_and_abandoned_worker_lock(self):
        code = "import sys,time;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import modmanager as m\nwith m.locked(Path(sys.argv[2])):\n print('locked',flush=True);time.sleep(30)"
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-c",
                code,
                str(Path(__file__).parent),
                str(self.repo),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            self.assertEqual(b"locked", process.stdout.readline().strip())
            with self.assertRaisesRegex(ValueError, "laeuft bereits"):
                with m.locked(self.repo):
                    pass
        finally:
            process.terminate()
            process.communicate(timeout=5)
        with m.locked(self.repo):
            pass

    def test_runtime_key_ignores_unrelated_skin_config(self):
        plugin = dict(
            entries=[
                dict(kind="plugin", path="plugin.nro", sha256="one", module="qa"),
                dict(kind="plugin-config", path="settings.toml", sha256="cfg"),
            ]
        )
        one = deployment.runtime_signature(
            {
                "a": plugin,
                "skin": dict(entries=[dict(path="config.json", sha256="skin1")]),
            }
        )
        two = deployment.runtime_signature({"a": plugin})
        self.assertEqual(one, two)
        plugin["entries"][1]["sha256"] = "changed"
        self.assertNotEqual(one, deployment.runtime_signature({"a": plugin}))

    def test_framework_flags_change_runtime_inputs(self):
        plugin = dict(
            entries=[dict(kind="plugin", path="plugin.nro", sha256="one", module="qa")]
        )
        before = deployment.runtime_signature({"plugin": plugin})
        after = deployment.runtime_signature(
            {
                "plugin": plugin,
                "flags": dict(entries=[dict(path="flags/own.flag", sha256="two")]),
            }
        )
        self.assertNotEqual(before, after)

    def test_asset_import_reuses_unchanged_plugin_runtime_with_missing_framework(self):
        import plugin_runtime, plugin_dependencies, runtime_cache

        source = self.mod(
            "Own plugin", "plugin.nro", "own fixture libthe_csk_collection.nro"
        )
        runtime = dict(app="own test runtime", dependencies=[], files={})
        with patch.object(
            plugin_runtime,
            "inspect_nro",
            return_value=dict(module="sky_fixture", smashline=False),
        ), patch.object(plugin_runtime, "ensure", return_value=runtime), patch.object(
            plugin_runtime, "deploy_dependencies"
        ), patch.object(
            runtime_cache, "plugin", return_value=runtime
        ):
            m.install(self.repo, source)
            with patch.object(
                plugin_runtime,
                "ensure",
                side_effect=AssertionError("unchanged plugin set rebuilt"),
            ), patch.object(
                plugin_dependencies,
                "required_records",
                side_effect=AssertionError("unnecessary NRO scan"),
            ):
                m.install(
                    self.repo, self.mod("Independent skin", "ui/replace/b.bntx", "B")
                )
            self.assertEqual(2, len(m.load(self.repo)["mods"]))
            self.assertEqual(
                runtime,
                json.loads((m.root(self.repo) / "profile/profile.json").read_text())[
                    "plugin_runtime"
                ],
            )

    def test_conflict_install_disabled_replace_and_undo(self):
        a, b = self.installed()
        other = self.mod("Replacement", "ui/replace/a.bntx", "different")
        plan = m.batch_preview(self.repo, [other])
        self.assertEqual("conflict", plan["items"][0]["status"])
        configured = batch.configure(
            m, self.repo, plan["job_id"], plan["token"], {"0": "disabled"}
        )
        result = m.batch_install(self.repo, plan["job_id"], configured["token"])
        self.assertEqual(1, result["installed"])
        self.assertFalse(
            next(r for r in m.listing(self.repo)["mods"] if r["name"] == "Replacement")[
                "enabled"
            ]
        )
        m.undo(self.repo)
        plan = m.batch_preview(self.repo, [other])
        configured = batch.configure(
            m, self.repo, plan["job_id"], plan["token"], {"0": "replace"}
        )
        result = m.batch_install(self.repo, plan["job_id"], configured["token"])
        self.assertEqual(1, result["installed"])
        self.assertFalse(m.load(self.repo)["mods"][a]["enabled"])
        m.undo(self.repo)
        self.assertTrue(m.load(self.repo)["mods"][a]["enabled"])

    def test_failed_replacement_keeps_original_active(self):
        a, b = self.installed()
        other = self.mod("Replacement", "ui/replace/a.bntx", "different")
        plan = m.batch_preview(self.repo, [other])
        configured = batch.configure(
            m, self.repo, plan["job_id"], plan["token"], {"0": "replace"}
        )
        folder = batch.path(m, self.repo, plan["job_id"])
        document = json.loads((folder / "plan.json").read_text())
        (folder / document["items"][0]["assets_rel"] / "ui/replace/a.bntx").write_text(
            "tampered"
        )
        result = m.batch_install(self.repo, plan["job_id"], configured["token"])
        self.assertEqual(0, result["installed"])
        self.assertTrue(m.load(self.repo)["mods"][a]["enabled"])

    def test_slot_overlaps_are_evidence_not_false_file_conflicts(self):
        first = self.mod("Costume model", "fighter/foo/model/body/c03/a.nutexb", "A")
        second = self.mod("Costume texture", "fighter/foo/model/body/c03/b.nutexb", "B")
        m.install(self.repo, first)
        plan = m.batch_preview(self.repo, [second])
        self.assertEqual("ready", plan["items"][0]["status"])
        self.assertIn("foo/c03", plan["items"][0]["slot_overlaps"][0])
        m.batch_install(self.repo, plan["job_id"], plan["token"])
        rows = m.listing(self.repo)["mods"]
        self.assertTrue(all(r["costume_overlaps"] for r in rows))
        self.assertFalse(any(r["known_conflicts"] for r in rows))
        import sqlite3, contextlib

        with contextlib.closing(
            sqlite3.connect(m.root(self.repo) / "index.sqlite")
        ) as db:
            cached = json.loads(
                db.execute(
                    "SELECT body FROM summaries WHERE id=?", (rows[0]["id"],)
                ).fetchone()[0]
            )
            self.assertEqual(rows[0]["costume_overlaps"], cached["costume_overlaps"])
            self.assertIn("origin", cached)


if __name__ == "__main__":
    unittest.main()
