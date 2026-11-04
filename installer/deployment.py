"""Incremental directory deployment, durable move journal and lightweight rollback states."""

import json, os, re, shutil, time, uuid
from pathlib import Path
import catalog, plugin_runtime, runtime_cache

BUSY = set()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def journal_write(m, path, value):
    temporary = path.with_name(path.name + ".new-" + uuid.uuid4().hex)
    try:
        with temporary.open("wb") as out:
            out.write(json.dumps(value, ensure_ascii=False).encode("utf-8"))
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def checkpoint(cancel):
    if cancel and cancel():
        from batch_import import Cancelled

        raise Cancelled("Vorgang vor dem Profilwechsel sicher abgebrochen.")


def grouped(manifest):
    out = {}
    for name, sha in manifest.get("files", {}).items():
        key, sep, path = name.partition("/")
        if not sep:
            raise ValueError("Ungueltiger Profilpfad.")
        out.setdefault(key, {})[path] = sha
    return out


def runtime_signature(records, manifest=None, repo=None):
    values = []
    for key, record in records.items():
        if not any(
            e.get("kind") == "plugin" or e["path"].startswith("flags/")
            for e in record["entries"]
        ):
            continue
        for e in record["entries"]:
            if e.get("kind") not in ("plugin", "plugin-config") and not e[
                "path"
            ].startswith("flags/"):
                continue
            sha = (
                manifest["files"].get(key + "/" + e["path"])
                if manifest
                else e["sha256"]
            )
            if sha:
                values.append((key, e["path"], sha, e.get("module", "")))
    if repo is not None and values:
        import plugin_dependencies

        extra = plugin_dependencies.required_records(repo, records)
        if extra:
            values.append(
                ("framework-dependencies", plugin_dependencies.fingerprint(extra))
            )
    return catalog.fingerprint(sorted(values)) if values else None


def notify(callback, phase, name=""):
    if callback:
        callback(dict(event="progress", phase=phase, name=name, current=0, total=0))


def preserve_training_data(m, source_profile, pending):
    """Keep plugin-owned settings/state outside the immutable mod asset trees."""
    source = source_profile / 'ultimate/TrainingModpack'
    if not source.exists():
        return
    if source.is_symlink() or source.is_junction() or not source.is_dir():
        raise ValueError('Unsicherer Trainingsdaten-Ordner; nichts ersetzt.')
    entries = m.files(source)  # rejects links throughout the tree
    if len(entries) > 4096 or sum((source / name).stat().st_size for name in entries) > 64 * 1024**2:
        raise ValueError('Trainingsdaten zu gross fuer einen sicheren Profilwechsel.')
    target = pending / 'ultimate/TrainingModpack'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)


def recover_pending(m, repo):
    root = m.root(repo)
    journal = root / "transaction.json"
    if not journal.exists() or str(root) in BUSY:
        return
    with m.locked(repo):
        recover(m, repo)


def recover(m, repo):
    root = m.root(repo)
    journal = root / "transaction.json"
    if not journal.exists():
        return
    job = read(journal)
    if job.get("app") != "OpenSmash-Deployment-v1":
        raise ValueError("Fremdes Transaktionsjournal; Wiederherstellung gestoppt.")
    if (
        not re.fullmatch("[0-9a-f]{32}", str(job.get("id", "")))
        or job.get("pending") != "profile.pending-" + job["id"]
        or job.get("state_temp") != "state-" + job["id"] + ".tmp"
        or not re.fullmatch(
            r"backups/\d{8}-\d{6}-[0-9a-f]{8}", str(job.get("backup", ""))
        )
    ):
        raise ValueError("Ungueltige Pfade im Profiljournal; nichts entfernt.")
    path = lambda name: m.base.contained(root, root / job[name])
    active = root / "profile"
    pending = path("pending")
    backup = path("backup")
    old = backup / "profile"
    state = m.base.digest(root / "state.json")
    committed = (
        state == job["new_state_sha"]
        and (active / "profile.json").exists()
        and read(active / "profile.json").get("generation") == job["id"]
    )
    if committed:
        finalize(m, repo, job)
        return
    if (active / "profile.json").exists() and read(active / "profile.json").get(
        "generation"
    ) == job["id"]:
        if pending.exists():
            raise ValueError(
                "Widerspruechliches Profiljournal; Dateien bleiben erhalten."
            )
        active.rename(pending)
    old_root = old if old.exists() else active
    for action in reversed(job["moves"]):
        src = m.base.contained(root, root / action["source"])
        dst = m.base.contained(root, root / action["destination"])
        if action["source"].startswith("profile/") and old_root == old:
            src = old / action["source"][len("profile/") :]
        if dst.exists():
            if src.exists():
                raise ValueError(
                    "Zwei Kopien im Wiederherstellungsjournal; nichts ueberschrieben."
                )
            src.parent.mkdir(parents=True, exist_ok=True)
            dst.rename(src)
        if action.get("library_id"):
            catalog.relocate(repo, action["library_id"], src)
    if old.exists():
        if active.exists():
            raise ValueError(
                "Altes und aktives Profil vorhanden; Wiederherstellung gestoppt."
            )
        old.rename(active)
    if state != job["old_state_sha"]:
        raise ValueError("Mod-Auswahl extern geaendert; Wiederherstellung gestoppt.")
    if pending.exists():
        shutil.rmtree(pending)
    temp = path("state_temp")
    temp.unlink(missing_ok=True)
    journal.unlink()
    # The backup holds a recoverable previous state, even when preparation failed.


def finalize(m, repo, job):
    root = m.root(repo)
    backup = m.base.contained(root, root / job["backup"])
    active = root / "profile"
    manifest = read(active / "profile.json")
    for action in job["moves"]:
        if action.get("library_id"):
            catalog.relocate(repo, action["library_id"], root / action["destination"])
        destination = action["destination"]
        if destination.startswith(job["pending"] + "/"):
            destination = "profile/" + destination[len(job["pending"]) + 1 :]
        if action["source"] != destination:
            catalog.moved(repo, root / action["source"], root / destination)
    # Keep removed source data by an atomic same-volume rename, available to Undo.
    for key in job.get("removed", []):
        source = root / "library" / key
        destination = root / "rollback" / (key + "-" + job["id"])
        if source.exists():
            destination.parent.mkdir(exist_ok=True)
            source.rename(destination)
            catalog.moved(repo, source, destination)
        if destination.exists():
            catalog.relocate(repo, key, destination)
    old = backup / "profile"
    old_manifest = read(old / "profile.json") if (old / "profile.json").exists() else {}
    old_groups = grouped(old_manifest)
    for key, expected in old_groups.items():
        folder = old / old_manifest.get("asset_dir", "assets") / key
        if folder.exists():
            catalog.moved(
                repo,
                root / "profile" / old_manifest.get("asset_dir", "assets") / key,
                folder,
            )
            catalog.deployment(
                repo,
                catalog.fingerprint([old_manifest.get("backend"), key, expected]),
                folder,
            )
    for key, expected in grouped(manifest).items():
        folder = active / manifest["asset_dir"] / key
        if key in job.get("copied_groups", []):
            catalog.seed(repo, folder, expected)
        catalog.deployment(
            repo, catalog.fingerprint([manifest["backend"], key, expected]), folder
        )
    for name, expected in manifest.get("support_files", {}).items():
        catalog.seed(repo, active / name, expected)
    (root / "transaction.json").unlink(missing_ok=True)


def commit(
    m,
    repo,
    desired,
    record_history=True,
    cancel=None,
    callback=None,
    force_runtime=False,
):
    root = m.root(repo)
    start = time.perf_counter()
    metrics = {}
    current = m.load(repo)
    # Orphans from a killed preparation contain no moved live data: every move
    # is journalled first, and an existing journal is recovered by load().
    for orphan in root.glob("profile.pending-*"):
        marker = orphan / ".manager-owned.json"
        if marker.is_file() and not orphan.is_symlink() and not orphan.is_junction():
            owner = read(marker)
            if (
                owner.get("app") == "OpenSmash-Deployment-v1"
                and orphan.name == "profile.pending-" + owner.get("id", "")
                and re.fullmatch("[0-9a-f]{32}", owner.get("id", ""))
            ):
                shutil.rmtree(orphan)
    old = (
        read(root / "profile/profile.json")
        if (root / "profile/profile.json").exists()
        else {}
    )
    records = {
        key: m.metadata(repo, key, verify=False)
        for key, value in desired["mods"].items()
        if value["enabled"]
    }
    owners = {}
    groups = {}
    arc = any(r.get("backend") == "arcropolis" for r in records.values())
    for key, record in records.items():
        for e in record["entries"]:
            identity = (
                ("plugin", e["module"])
                if e.get("kind") == "plugin"
                else (
                    (key, e["path"])
                    if e.get("metadata")
                    else ("path:" + e["path"] if arc else e["info"])
                )
            )
            if identity in owners:
                if owners[identity][1] != e["sha256"]:
                    raise ValueError(
                        "Konflikt: "
                        + record["name"]
                        + " und "
                        + owners[identity][0]
                        + ". Zuerst eine der Mods deaktivieren."
                    )
                continue
            owners[identity] = (record["name"], e["sha256"])
            groups.setdefault(key, {})[e["path"]] = e["sha256"]
    if sum(map(len, groups.values())) > (16000 if arc else 4096):
        raise ValueError("Gemeinsames Profil enthaelt zu viele Dateien.")
    if arc and old.get("backend") != "arcropolis":
        notify(callback, "loader_prepare")
        m.arc_backend.ensure(repo)
    signature = runtime_signature(records)
    runtime = None
    if signature:
        old_records = {
            key: m.metadata(repo, key, verify=False)
            for key in old.get("mods", [])
            if key in current["mods"]
        }
        old_signature = runtime_signature(old_records, old)
        if old_signature and old.get("plugin_runtime"):
            catalog.runtime(repo, old_signature, old["plugin_runtime"])
        # Asset-only changes must not migrate/rebuild an unchanged plugin set.
        # Explicit gameplay preparation still resolves missing frameworks.
        same_inputs = old_signature == runtime_signature(records)
        if same_inputs and old.get("plugin_runtime") and not force_runtime:
            runtime = old["plugin_runtime"]
        else:
            signature = runtime_signature(records, repo=repo)
            runtime = catalog.runtime(repo, signature)
        if runtime:
            try:
                runtime_cache.plugin(repo, runtime)
            except (ValueError, OSError):
                runtime = None
        if runtime is None:
            notify(
                callback,
                "plugin_prepare",
                "Plugin-Laufzeit wird uebersetzt; Abbruch vor Profilwechsel moeglich.",
            )
            with m.pending_directory(root, "runtime-input-") as inputs:
                m.arc_backend.make_sd(repo, inputs)
                for key, record in records.items():
                    if not any(
                        e.get("kind") == "plugin" or e["path"].startswith("flags/")
                        for e in record["entries"]
                    ):
                        continue
                    m.metadata(repo, key)
                    shutil.copytree(
                        catalog.location(repo, key) / "assets",
                        inputs / "ultimate/mods" / key,
                    )
                try:
                    runtime = plugin_runtime.ensure(repo, inputs)
                except Exception as exc:
                    raise plugin_runtime.PluginBuildError(str(exc)) from exc
            if runtime:
                catalog.runtime(repo, signature, runtime)
    metrics["runtime_prepare_seconds"] = time.perf_counter() - start
    checkpoint(cancel)
    template = m.arc_backend.location(repo) / "template-sd"
    reuse_arc = (
        arc
        and old.get("backend") == "arcropolis"
        and (root / "profile/ultimate/arcropolis").is_dir()
        and template.exists()
    )
    tx = uuid.uuid4().hex
    pending = root / ("profile.pending-" + tx)
    pending.mkdir()
    m.base.write_json(
        pending / ".manager-owned.json", dict(app="OpenSmash-Deployment-v1", id=tx)
    )
    asset_dir = "ultimate/mods" if arc else "assets"
    if arc and not reuse_arc:
        m.arc_backend.make_sd(repo, pending)
    (pending / asset_dir).mkdir(parents=True, exist_ok=True)
    preserve_training_data(m, root / 'profile', pending)
    backup = root / "backups" / m.stamp()
    backup.mkdir(parents=True)
    shutil.copy2(root / "state.json", backup / "state.json")
    desired = json.loads(json.dumps(desired))
    desired["history"] = (
        (current.get("history", []) + [backup.relative_to(root).as_posix()])
        if record_history
        else desired.get("history", [])
    )
    state_temp = root / ("state-" + tx + ".tmp")
    m.base.write_json(state_temp, desired)
    job = dict(
        app="OpenSmash-Deployment-v1",
        id=tx,
        pending=pending.relative_to(root).as_posix(),
        backup=backup.relative_to(root).as_posix(),
        state_temp=state_temp.relative_to(root).as_posix(),
        old_state_sha=m.base.digest(root / "state.json"),
        new_state_sha=m.base.digest(state_temp),
        moves=[],
        copied_groups=[],
        removed=sorted(set(current["mods"]) - set(desired["mods"])),
    )
    BUSY.add(str(root))
    copied = 0
    reused = 0
    reusable = []
    old_groups = grouped(old)
    try:
        for key, expected in groups.items():
            checkpoint(cancel)
            notify(callback, "deploy_prepare", records[key]["name"])
            destination = pending / asset_dir / key
            source = root / "profile" / old.get("asset_dir", "assets") / key
            if old_groups.get(key) != expected or not source.is_dir():
                source = catalog.deployment(
                    repo,
                    catalog.fingerprint(
                        ["arcropolis" if arc else "native", key, expected]
                    ),
                )
            if source and source.is_dir():
                # Only this affected cached mod is checked. Unchanged active trees are
                # moved intact; an explicit refresh/start validates all external changes.
                if not source.is_relative_to(root / "profile"):
                    catalog.validate(repo, source, expected)
                reusable.append((source, destination, None))
                reused += 1
                continue
            m.metadata(repo, key)
            job["copied_groups"].append(key)
            for name, sha in expected.items():
                file = m.base.contained(
                    catalog.location(repo, key) / "assets",
                    catalog.location(repo, key) / "assets" / name,
                )
                out = m.base.contained(pending, destination / name)
                if len(
                    str(root / "profile" / asset_dir / key / name).encode("ascii")
                ) >= (255 if arc else 390):
                    raise ValueError("Mod-Pfad ist fuer den Loader zu lang.")
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, out)
                if m.base.digest(out) != sha:
                    raise ValueError("Datei hat sich beim Kopieren geaendert: " + name)
                copied += 1
        if arc:
            if reuse_arc:
                shutil.copytree(template / "atmosphere", pending / "atmosphere")
                reusable.append(
                    (
                        root / "profile/ultimate/arcropolis",
                        pending / "ultimate/arcropolis",
                        None,
                    )
                )
        for key in desired["mods"]:
            source = catalog.location(repo, key)
            destination = root / "library" / key
            if source != destination and source.exists():
                reusable.append((source, destination, key))
        checkpoint(cancel)
        journal_write(m, root / "transaction.json", job)
        for source, destination, library_id in reusable:
            action = dict(
                source=source.relative_to(root).as_posix(),
                destination=destination.relative_to(root).as_posix(),
            )
            if library_id:
                action["library_id"] = library_id
            job["moves"].append(action)
            journal_write(m, root / "transaction.json", job)
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
            if library_id:
                catalog.relocate(repo, library_id, destination)
        if arc:
            plugin_runtime.deploy_dependencies(repo, pending, runtime)
        support = (
            {
                name: m.files(pending / name)
                for name in ("atmosphere", "ultimate/arcropolis/resources")
            }
            if arc
            else {}
        )
        manifest = dict(
            generation=tx,
            files={
                key + "/" + p: sha
                for key, entries in groups.items()
                for p, sha in entries.items()
            },
            mods=list(records),
            backend="arcropolis" if arc else "native",
            asset_dir=asset_dir,
            support_files=support,
            plugin_runtime=runtime,
        )
        m.base.write_json(pending / "profile.json", manifest)
        checkpoint(cancel)
        active = root / "profile"
        if active.exists():
            active.rename(backup / "profile")
        pending.rename(active)
        os.replace(state_temp, root / "state.json")
        finalize(m, repo, job)
    except BaseException:
        if (root / "transaction.json").exists():
            recover(m, repo)
        elif pending.exists():
            shutil.rmtree(pending)
            state_temp.unlink(missing_ok=True)
        raise
    finally:
        BUSY.discard(str(root))
    metrics.update(
        total_seconds=time.perf_counter() - start,
        copied_files=copied,
        reused_mod_directories=reused,
    )
    m.base.write_json(root / "logs/last-operation.json", metrics)
    return dict(
        active=len(records),
        files=sum(
            not e.get("metadata", False) for r in records.values() for e in r["entries"]
        ),
        backup=str(backup),
        timings=metrics,
    )
