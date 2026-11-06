"""Portable Windows asset-mod manager. No bundled game or mod assets."""

import argparse
import contextlib
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import drybowser as base
import arc_backend
import arc_import
import catalog
import moveset_support

APP = "OpenSmash-Asset-Modmanager-v1"
LOCAL = "opensmash_mods"
LOCK_DEPTH = {}
ROOTS = {
    "fighter",
    "effect",
    "ui",
    "sound",
    "stage",
    "item",
    "param",
    "common",
    "camera",
    "system",
    "stream",
    "stream;",
    "standard",
    "flags",
}
CODE = {
    ".nro",
    ".dll",
    ".exe",
    ".com",
    ".bat",
    ".cmd",
    ".ps1",
    ".psm1",
    ".py",
    ".pyd",
    ".vbs",
    ".js",
    ".lnk",
    ".scr",
    ".asi",
    ".msi",
    ".reg",
}
TOOLS = [
    "Localization.ps1",
    "locales.json",
    "BrandLogo.png",
    "BrandIcon.png",
    "BrandIcon.ico",
    "modmanager.py",
    "drybowser.py",
    "Start.ps1",
    "arc_backend.py",
    "arc_import.py",
    "arc_simd.py",
    "arc_fs_support.h",
    "batch_import.py",
    "catalog.py",
    "gamebanana.py",
    "downloads.py",
    "network.py",
    "manager_links.py",
    "ImageViewer.ps1",
    "Discover.ps1",
    "Discover.xaml",
    "Downloads.xaml",
    "deployment.py",
    "runtime_cache.py",
    "playback.py",
    "rar_support.py",
    "sevenzip_support.py",
    "7za.exe",
    "7ZIP_LICENSE.txt",
    "7ZIP_LGPL.txt",
    "7ZIP_DISTRIBUTION.json",
    "UnRAR64.dll",
    "UNRAR_LICENSE.txt",
    "setup_checks.py",
    "UiSupport.ps1",
    "Theme.ps1",
    "library_export.py",
    "mod_lists.py",
    "ModLists.ps1",
    "plugin_runtime.py",
    "plugin_dependencies.py",
    "moveset_support.py",
    "legacy_addresses.py",
    "library_media.py",
    "LibraryView.ps1",
    "LibraryViews.xaml",
    "ModManager.ps1",
    "ModManager.xaml",
    "ModManager.exe",
    "Mods verwalten.bat",
]


def root(repo):
    return base.contained(repo, repo / LOCAL)


def files(path):
    result = {}
    for p in sorted(path.rglob("*")):
        if p.is_symlink() or p.is_junction():
            raise ValueError("Verknuepfungen sind nicht erlaubt: " + str(p))
        if p.is_file():
            result[p.relative_to(path).as_posix()] = base.digest(p)
    return result


def idle():
    if sys.platform != "win32":
        return
    p = subprocess.run(
        ["tasklist.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        errors="replace",
        creationflags=0x08000000,
    )
    if p.returncode:
        raise ValueError(
            "Spielstatus konnte nicht geprueft werden. Bitte das Spiel schliessen und erneut versuchen."
        )
    for row in csv.reader(p.stdout.splitlines()):
        if (
            row
            and row[0].lower().startswith("ssbu_")
            and row[0].lower().endswith(".exe")
        ):
            raise ValueError(
                "OpenSmash laeuft noch. Bitte vor Installieren, Umschalten oder Rueckbau schliessen."
            )


def stamp():
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]


def load(repo):
    r = root(repo)
    if (r / "transaction.json").exists():
        import deployment
        from types import SimpleNamespace

        deployment.recover_pending(SimpleNamespace(**globals()), repo)
    if r.is_symlink() or r.is_junction():
        raise ValueError("Modmanager-Ordner darf keine Verknuepfung sein.")
    state = json.loads((r / "state.json").read_text(encoding="utf-8"))
    if state.get("app") != APP:
        raise ValueError(
            "Unbekannter Modmanager-Ordner; keine Aenderungen vorgenommen."
        )
    return state


@contextlib.contextmanager
def locked(repo):
    r = root(repo)
    path = r / "operation.lock"
    handle = None
    stream = None
    acquired = False
    registered = False
    if sys.platform == "win32":
        import ctypes as c

        kernel = c.WinDLL("kernel32", use_last_error=True)
        kernel.CreateMutexW.argtypes = [c.c_void_p, c.c_int, c.c_wchar_p]
        kernel.CreateMutexW.restype = c.c_void_p
        kernel.WaitForSingleObject.argtypes = [c.c_void_p, c.c_uint32]
        kernel.WaitForSingleObject.restype = c.c_uint32
        kernel.ReleaseMutex.argtypes = [c.c_void_p]
        kernel.CloseHandle.argtypes = [c.c_void_p]
        handle = kernel.CreateMutexW(
            None,
            False,
            "Local\\OpenSmash.ModManager."
            + hashlib.sha256(str(r.resolve()).lower().encode()).hexdigest()[:32],
        )
        if not handle:
            raise OSError(
                c.get_last_error(), "Modmanager-Mutex konnte nicht angelegt werden."
            )
    try:
        if handle:
            result = kernel.WaitForSingleObject(handle, 0)
            if result not in (0, 128):
                raise ValueError("Ein Mod-Vorgang laeuft bereits.")
            acquired = True
            # Older releases used only a PID file. Honour a still-running worker
            # during upgrades, but recover stale files after process termination.
            if path.exists():
                try:
                    pid = int(path.read_text(encoding="ascii"))
                except (OSError, ValueError):
                    pid = 0
                if pid and pid != os.getpid():
                    kernel.OpenProcess.argtypes = [c.c_uint32, c.c_int, c.c_uint32]
                    kernel.OpenProcess.restype = c.c_void_p
                    process = kernel.OpenProcess(0x100000, False, pid)
                    if process:
                        try:
                            alive = kernel.WaitForSingleObject(process, 0) == 258
                        finally:
                            kernel.CloseHandle(process)
                    else:
                        alive = c.get_last_error() == 5
                    if alive:
                        acquired = False
                        kernel.ReleaseMutex(handle)
                        raise ValueError(
                            "Ein Mod-Vorgang der bisherigen Version laeuft bereits."
                        )
        else:
            import fcntl

            stream = path.open("a+b")
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError as exc:
                raise ValueError("Ein Mod-Vorgang laeuft bereits.") from exc
        LOCK_DEPTH[str(r)] = LOCK_DEPTH.get(str(r), 0) + 1
        registered = True
        path.write_text(str(os.getpid()), encoding="ascii")
        yield
    finally:
        if registered:
            LOCK_DEPTH[str(r)] -= 1
        if acquired and not LOCK_DEPTH.get(str(r), 0):
            try:
                path.unlink(missing_ok=True)
            except PermissionError:
                pass
        if stream:
            stream.close()
        if handle:
            if acquired:
                kernel.ReleaseMutex(handle)
            kernel.CloseHandle(handle)


@contextlib.contextmanager
def pending_directory(parent, prefix):
    parent = parent.resolve()
    path = base.contained(parent, parent / (prefix + uuid.uuid4().hex))
    path.mkdir()
    try:
        yield path
    finally:
        if path.exists():
            if (
                path.resolve().parent != parent
                or path.is_symlink()
                or path.is_junction()
            ):
                raise ValueError("Unerwarteter temporaerer Pfad; Bereinigung gestoppt.")
            shutil.rmtree(path)


def metadata(repo, mod_id, verify=True, force=False):
    if not mod_id or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in mod_id
    ):
        raise ValueError("Ungueltige Mod-ID.")
    folder = catalog.location(repo, mod_id)
    record = catalog.record(repo, mod_id)
    if record.get("id") != mod_id:
        raise ValueError("Mod-Metadaten stimmen nicht ueberein.")
    if (
        not isinstance(record.get("name"), str)
        or not isinstance(record.get("entries"), list)
        or len(record["entries"]) > 16000
    ):
        raise ValueError("Ungueltige Mod-Metadaten: " + mod_id)
    if verify:
        expected = {entry["path"]: entry["sha256"] for entry in record["entries"]}
        try:
            catalog.validate(repo, folder / "assets", expected, force)
        except ValueError as exc:
            raise ValueError(
                "Gespeicherte Mod wurde ausserhalb des Managers veraendert: "
                + record["name"]
            ) from exc
    return record


def profile_valid(repo, force=False):
    p = root(repo) / "profile"
    if not p.exists():
        return
    manifest = json.loads((p / "profile.json").read_text(encoding="utf-8"))
    try:
        catalog.validate(
            repo, p / manifest.get("asset_dir", "assets"), manifest["files"], force
        )
    except ValueError as exc:
        raise ValueError(
            "Das aktive Mod-Profil wurde ausserhalb des Managers geaendert. Nichts ueberschrieben."
        ) from exc
    for folder, expected in manifest.get("support_files", {}).items():
        try:
            catalog.validate(repo, p / folder, expected, force)
        except ValueError as exc:
            raise ValueError(
                "Die Mod-Loader-Dateien im Profil wurden ausserhalb des Managers geaendert."
            ) from exc


def commit(
    repo, desired, record_history=True, cancel=None, callback=None, force_runtime=False
):
    import deployment
    from types import SimpleNamespace

    return deployment.commit(
        SimpleNamespace(**globals()),
        repo,
        desired,
        record_history,
        cancel,
        callback,
        force_runtime,
    )


def deploy(repo):
    r = root(repo)
    tools = r / "tools"
    tools.mkdir(exist_ok=True)
    manifest_file = r / "tools.json"
    previous = json.loads(manifest_file.read_text()) if manifest_file.exists() else {}
    incoming = {name: base.digest(Path(__file__).parent / name) for name in TOOLS}
    for name, expected in previous.items():
        if not (tools / name).is_file() or base.digest(tools / name) != expected:
            raise ValueError("Modmanager-Werkzeug wurde manuell geaendert: " + name)
    if previous != incoming:
        backup = r / "backups" / ("tools-" + stamp())
        backup.mkdir(parents=True)
        for name in previous:
            shutil.copy2(tools / name, backup / name)
        for name in TOOLS:
            target = tools / name
            if not target.is_file() or base.digest(target) != incoming[name]:
                shutil.copy2(Path(__file__).parent / name, target)
        base.write_json(manifest_file, incoming)
    launcher = repo / "Mods verwalten.bat"
    data = (
        "@echo off\r\nsetlocal DisableDelayedExpansion\r\n"
        '"%~dp0opensmash_mods\\tools\\ModManager.exe" -Repo "%~dp0."\r\n'
        "if errorlevel 1 pause\r\n"
    ).encode("ascii")
    saved = r / "launcher.json"
    if saved.exists():
        old = json.loads(saved.read_text())
        if not launcher.is_file() or base.digest(launcher) != old["sha256"]:
            raise ValueError("Modmanager-Startdatei wurde manuell geaendert.")
    elif launcher.exists():
        raise ValueError(
            "Mods verwalten.bat existiert bereits und gehoert nicht diesem Manager."
        )
    launcher.write_bytes(data)
    base.write_json(saved, dict(sha256=hashlib.sha256(data).hexdigest()))


def save_library(repo, record, source):
    r = root(repo)
    key = record["id"]
    folder = r / "library" / key
    existing = catalog.location(repo, key)
    if existing.exists():
        metadata(repo, key)
        return
    with pending_directory(r / "library", "pending-") as pending:
        (pending / "assets").mkdir()
        for entry in record["entries"]:
            dst = base.contained(pending, pending / "assets" / entry["path"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / entry.get("source_path", entry["path"]), dst)
            if base.digest(dst) != entry["sha256"]:
                raise ValueError(
                    "Mod-Quelle hat sich waehrend der Installation geaendert."
                )
        import library_media

        library_media.capture(repo, key, source)
        base.write_json(pending / "mod.json", record)
        pending.rename(folder)
        catalog.record(repo, key)
        catalog.seed(
            repo, folder / "assets", {e["path"]: e["sha256"] for e in record["entries"]}
        )


def setup(repo, legacy_source=None):
    idle()
    build, game, arc, h40 = base.preflight(repo)
    arc.f.close()
    r = root(repo)
    if r.exists() and not (r / "state.json").is_file():
        raise ValueError(
            "opensmash_mods existiert ohne gueltigen Eigentumsnachweis. Nichts ueberschrieben."
        )
    if not r.exists():
        r.mkdir()
        for name in ("library", "backups", "incoming", "empty", "logs"):
            (r / name).mkdir()
        base.write_json(
            r / "state.json",
            dict(
                app=APP,
                mods={},
                history=[],
                runtime_sha256=base.digest(build / "work/ssbu_native.exe"),
            ),
        )
    with locked(repo):
        state = load(repo)
        if legacy_source:
            state["legacy_source"] = str(legacy_source.resolve())
        deploy(repo)
        base.update_launch_tools(repo)
        # Import the already verified private Dry Bowser installation only once.
        legacy = repo / base.LOCAL
        if not state.get("legacy_imported") and legacy.exists():
            legacy_state = base.verify_managed(legacy)
            report = json.loads(
                (legacy / "asset-report.json").read_text(encoding="utf-8")
            )
            build, game, arc, h40 = base.preflight(repo)
            try:
                entries = []
                for path in report["install_files"]:
                    index = arc.path_index_from_hash(h40(path))
                    if index is None:
                        raise ValueError(
                            "Dry-Bowser-Archiv hat sich geaendert; den bisherigen Installer erneut ausfuehren."
                        )
                    entries.append(
                        dict(
                            path=path,
                            sha256=base.digest(legacy / "assets/DryBowser" / path),
                            info=str(arc.file_record(index)["info_index"]),
                        )
                    )
                record = dict(
                    id="dry-bowser",
                    name="Dry Bowser",
                    entries=entries,
                    warnings=report["limitations"],
                    legacy=True,
                )
                save_library(repo, record, legacy / "assets/DryBowser")
                state["mods"]["dry-bowser"] = dict(name="Dry Bowser", enabled=True)
                state["legacy_imported"] = True
                commit(repo, state)
            finally:
                arc.f.close()
        elif not (r / "profile").exists() or legacy_source:
            commit(repo, state)
    return listing(repo)


def bootstrap(repo):
    """Warm start reads metadata only; all mutations and launches still verify asset hashes."""
    r = root(repo)
    if (
        (r / "state.json").is_file()
        and (r / "profile/profile.json").is_file()
        and (r / "tools.json").is_file()
    ):
        incoming = {name: base.digest(Path(__file__).parent / name) for name in TOOLS}
        previous = json.loads((r / "tools.json").read_text())
        if previous == incoming and all(
            (r / "tools" / name).is_file() and base.digest(r / "tools" / name) == sha
            for name, sha in previous.items()
        ):
            return listing(repo)
    return setup(repo)


@contextlib.contextmanager
def source_folder(repo, source):
    if source.is_symlink() or source.is_junction():
        raise ValueError(
            "Bitte einen echten Mod-Ordner oder ZIP/RAR/7z waehlen, keine Verknuepfung."
        )
    source = source.resolve(strict=True)
    if source.is_dir():
        yield source
        return
    import batch_import
    from types import SimpleNamespace

    if source.suffix.lower() not in batch_import.ARCHIVES:
        raise ValueError("Unterstuetzt werden Mod-Ordner und ZIP-/RAR-/7z-Dateien.")
    incoming = root(repo) / "incoming"
    with tempfile.TemporaryDirectory(prefix="import-", dir=incoming) as tmp:
        target = Path(tmp) / "unpacked"
        assert target.resolve().is_relative_to(incoming.resolve())
        batch_import.extract(SimpleNamespace(**globals()), source, target, None)
        yield target


def find_assets(source):
    if source.name.lower() in ROOTS:
        raise ValueError(
            "Bitte den Mod-Ordner ueber fighter/, ui/ usw. ablegen, nicht den Asset-Unterordner selbst."
        )
    candidates = []
    all_files = list(source.rglob("*"))
    if len(all_files) > 16000:
        raise ValueError(
            "Zu viele Dateien/Ordner. Bitte nur einen einzelnen Mod ablegen."
        )
    for p in [source, *all_files]:
        if p.is_symlink() or p.is_junction():
            raise ValueError("Verknuepfung in der Mod nicht erlaubt: " + str(p))
        if p.is_file() and p.suffix.lower() == ".nro":
            import plugin_runtime

            try:
                plugin_runtime.inspect_nro(p)
            except ValueError as exc:
                raise ValueError(
                    "Plugin-/Programmcode ist kein gueltiges Skyline-NRO: " + str(exc)
                ) from exc
            candidates.append(p.parent)
        elif p.is_file() and p.suffix.lower() in CODE:
            raise ValueError(
                "Diese Mod enthaelt nicht unterstuetzten Programmcode ("
                + p.name
                + "). Windows-DLLs und Installationsskripte sind keine Skyline-NROs."
            )
        if p.is_dir() and p.name.lower() in ROOTS:
            candidates.append(p.parent)
    candidates = sorted(set(candidates), key=str)
    # asset subtrees may contain a directory also called common/item; take only outer roots.
    candidates = [
        p
        for p in candidates
        if not any(p != other and p.is_relative_to(other) for other in candidates)
    ]
    if len(candidates) != 1:
        raise ValueError(
            "Genau einen Mod mit fighter/, ui/, effect/, sound/ usw. ablegen. Gefundene Mod-Wurzeln: "
            + str(len(candidates))
        )
    return candidates[0]


def analyze(repo, source):
    return arc_import.analyze(repo, find_assets(source), ROOTS)


def inspect(repo, source):
    with source_folder(repo, source) as folder:
        record = analyze(repo, folder)
        record.pop("assets_root")
        return record


def prepare_legacy(repo, state):
    # Preserve full legacy replacements when changing loaders: the old
    # native library deliberately kept only one file per shared ARC entry.
    for key, status in list(state["mods"].items()):
        old = metadata(repo, key, verify=False)
        if status["enabled"] and old.get("legacy") and not old.get("backend"):
            metadata(repo, key)
            legacy = base.verify_managed(repo / base.LOCAL)
            original = Path(state.get("legacy_source", repo / "mods/custom"))
            with source_folder(repo, original) as full:
                full = base.find_mod(full)
                if any(
                    not (full / rel).is_file() or base.digest(full / rel) != sha
                    for rel, sha in legacy["source_sha256"].items()
                ):
                    raise ValueError(
                        "Vollstaendige urspruengliche Dry-Bowser-Quelle fehlt oder wurde geaendert. Zuerst die alte Dry-Bowser-Mod deaktivieren oder Originalquelle erneut installieren."
                    )
                replacement = analyze(repo, full)
                replacement["name"] = status["name"]
                replacement.pop("assets_root")
                save_library(repo, replacement, full)
            del state["mods"][key]
            state["mods"][replacement["id"]] = status


def install(repo, source, expected=None):
    idle()
    with locked(repo), source_folder(repo, source) as folder:
        record = analyze(repo, folder)
        if expected and record["token"] != expected:
            raise ValueError(
                "Die Mod hat sich seit der Vorschau geaendert. Bitte erneut pruefen."
            )
        assets = Path(record.pop("assets_root"))
        state = load(repo)
        if record["id"] in state["mods"]:
            return dict(
                message="Diese Mod ist bereits installiert.", state=listing(repo)
            )
        signature = {(e["path"], e["sha256"]) for e in record["entries"]}
        for key in state["mods"]:
            existing = metadata(repo, key)
            if signature == {(e["path"], e["sha256"]) for e in existing["entries"]}:
                return dict(
                    message='Diese Dateien sind bereits als "'
                    + existing["name"]
                    + '" installiert.',
                    state=listing(repo),
                )
        prepare_legacy(repo, state)
        save_library(repo, record, assets)
        state["mods"][record["id"]] = dict(name=record["name"], enabled=True)
        result = commit(repo, state)
        return dict(
            message="Installiert und aktiviert. Wirksam beim naechsten Spielstart.",
            state=listing(repo),
            result=result,
        )


def listing(repo, verify=False):
    state = load(repo)
    mods = []
    records = {}
    owners = {}
    slots = {}
    for key, status in state["mods"].items():
        record = metadata(repo, key, verify=verify)
        records[key] = record
        if status["enabled"]:
            for entry in record["entries"]:
                if entry.get("metadata"):
                    continue
                owners.setdefault(entry["path"], []).append((key, entry["sha256"]))
            for slot in catalog.costume_slots(record):
                slots.setdefault(slot, []).append(key)
        mods.append(
            dict(
                id=key,
                name=status["name"],
                enabled=status["enabled"],
                files=sum(not e.get("metadata", False) for e in record["entries"]),
                warnings=record.get("warnings", []),
                origin=record.get("origin", {}),
                location=str(catalog.location(repo, key)),
                compatibility=record.get("compatibility", "Experimental"),
                preview=__import__("library_media").cached(repo, key),
                validation="Metadaten im lokalen Index; betroffene Dateien werden vor Aenderungen geprueft.",
            )
        )
    active = {key: record for key, record in records.items() if state['mods'][key]['enabled']}
    try:
        effective = moveset_support.overlay_groups(active, state['mods'], repo=repo)
    except (ValueError, OSError):
        effective = None
    for row in mods:
        key = row["id"]
        record = records[key]
        row["known_conflicts"] = [
            dict(path=entry["path"], mod_id=other, name=state["mods"][other]["name"])
            for entry in record["entries"]
            if not entry.get("metadata")
            for other, sha in owners.get(entry["path"], [])
            if other != key and sha != entry["sha256"]
            and effective is None
        ][:100]
        row["costume_overlaps"] = [
            dict(slot=slot, mod_id=other, name=state["mods"][other]["name"])
            for slot in catalog.costume_slots(record)
            for other in slots.get(slot, [])
            if other != key
        ][:100]
        warnings = list(row["warnings"])
        hint = moveset_support.selection_hint(record)
        if hint:
            warnings.append(hint)
        row['selection_hint'] = hint
        row['overlays'] = state['mods'][key].get('overlays', [])
        if row['overlays']:
            warnings.append('Ausdrueckliche Asset-Ueberlagerung: ' + ', '.join(state['mods'].get(k, {}).get('name', k) for k in row['overlays'])
                            + '. Bei Pause werden die Basisdateien wiederhergestellt.')
        if row["known_conflicts"]:
            warnings.append(
                "Konflikte mit aktiven Zielpfaden: "
                + ", ".join(sorted({i["name"] for i in row["known_conflicts"]}))
            )
        if row["costume_overlaps"]:
            warnings.append(
                "Gleiche Kostuemslots: "
                + ", ".join(
                    sorted(
                        {
                            i["slot"] + " (" + i["name"] + ")"
                            for i in row["costume_overlaps"]
                        }
                    )
                )
                + ". Verschiedene Dateien koennen kombinierbar sein; Spielverhalten pruefen."
            )
        row["warnings"] = warnings
    issues = moveset_support.diagnostics(repo, active)
    for row in mods:
        if row['id'] in issues:
            row['compatibility'] = 'NeedsDependencies'
            row['warnings'].append(issues[row['id']])
        row['dependency_issue'] = issues.get(row['id'], '')
    catalog.summaries(repo, mods)
    return dict(mods=mods, can_undo=bool(state.get("history")), root=str(root(repo)))


def change(repo, key, action, enabled=False, callback=None, cancel=None):
    idle()
    with locked(repo):
        state = load(repo)
        if key not in state["mods"]:
            raise ValueError("Mod ist nicht mehr installiert.")
        metadata(repo, key)
        manifest = json.loads(
            (root(repo) / "profile/profile.json").read_text(encoding="utf-8")
        )
        if key in manifest.get("mods", []):
            expected = {
                name[len(key) + 1 :]: sha
                for name, sha in manifest["files"].items()
                if name.startswith(key + "/")
            }
            try:
                catalog.validate(
                    repo,
                    root(repo) / "profile" / manifest.get("asset_dir", "assets") / key,
                    expected,
                )
            except ValueError as exc:
                raise ValueError(
                    "Das Mod-Profil wurde ausserhalb des Managers veraendert."
                ) from exc
        if action == "remove":
            del state["mods"][key]
        else:
            if state["mods"][key]["enabled"] == enabled:
                return listing(repo)
            state["mods"][key]["enabled"] = enabled
        commit(repo, state, callback=callback, cancel=cancel)
    return listing(repo)


def undo(repo):
    idle()
    with locked(repo):
        state = load(repo)
        if not state.get("history"):
            raise ValueError("Keine vorherige Aenderung vorhanden.")
        backup = base.contained(
            root(repo) / "backups", root(repo) / state["history"][-1]
        )
        previous = json.loads((backup / "state.json").read_text(encoding="utf-8"))
        if previous.get("app") != APP:
            raise ValueError("Ungueltige Sicherung.")
        commit(repo, previous, record_history=False)
    return listing(repo)


def change_many(repo, values, callback=None, cancel=None):
    if (
        not isinstance(values, dict)
        or not values
        or len(values) > 1024
        or any(type(v) is not bool for v in values.values())
    ):
        raise ValueError("Ungueltige Mod-Auswahl.")
    idle()
    with locked(repo):
        state = load(repo)
        manifest = json.loads(
            (root(repo) / "profile/profile.json").read_text(encoding="utf-8")
        )
        changed = False
        for key, value in values.items():
            if key not in state["mods"]:
                raise ValueError("Eine ausgewaehlte Mod ist nicht mehr installiert.")
            metadata(repo, key)
            if key in manifest.get("mods", []):
                expected = {
                    name[len(key) + 1 :]: sha
                    for name, sha in manifest["files"].items()
                    if name.startswith(key + "/")
                }
                try:
                    catalog.validate(
                        repo,
                        root(repo)
                        / "profile"
                        / manifest.get("asset_dir", "assets")
                        / key,
                        expected,
                    )
                except ValueError as exc:
                    raise ValueError(
                        "Das Mod-Profil wurde ausserhalb des Managers geaendert."
                    ) from exc
            changed |= state["mods"][key]["enabled"] != value
            state["mods"][key]["enabled"] = value
        if changed:
            commit(repo, state, callback=callback, cancel=cancel)
    return listing(repo)


def refresh(repo, callback=None, cancel=None):
    idle()
    errors = {}
    start = time.perf_counter()
    with locked(repo):
        state = load(repo)
        for index, key in enumerate(state["mods"]):
            if cancel and cancel():
                from batch_import import Cancelled

                raise Cancelled("Vollstaendige Pruefung abgebrochen.")
            if callback:
                callback(
                    dict(
                        event="progress",
                        phase="refresh",
                        current=index,
                        total=len(state["mods"]),
                        name=state["mods"][key]["name"],
                    )
                )
            try:
                metadata(repo, key, force=True)
            except ValueError as exc:
                errors[key] = str(exc)
        try:
            profile_valid(repo, force=True)
        except ValueError as exc:
            errors["profile"] = str(exc)
    result = listing(repo)
    result.update(validation_errors=errors, refresh_seconds=time.perf_counter() - start)
    return result


def uninstall(repo):
    idle()
    r = root(repo)
    if not r.exists():
        return dict(message="Modmanager ist nicht installiert.")
    with locked(repo):
        listing(repo)
        profile_valid(repo)
        for name, expected in json.loads((r / "tools.json").read_text()).items():
            if base.digest(r / "tools" / name) != expected:
                raise ValueError(
                    "Modmanager-Werkzeuge wurden manuell geaendert. Rueckbau gestoppt."
                )
        launcher = repo / "Mods verwalten.bat"
        expected = json.loads((r / "launcher.json").read_text())["sha256"]
        if not launcher.is_file() or base.digest(launcher) != expected:
            raise ValueError(
                "Modmanager-Startdatei wurde manuell geaendert. Rueckbau gestoppt."
            )
        backup = base.contained(
            repo, repo / "modmanager_backups" / ("uninstall-" + stamp())
        )
        backup.parent.mkdir(exist_ok=True)
        r.rename(backup)
        (backup / "operation.lock").unlink()
        launcher.unlink()
    return dict(
        message="Modmanager entfernt. Alle Mod-Kopien und Rueckbaustaende gesichert.",
        backup=str(backup),
    )


def prepare_gameplay(repo, callback=None, cancel=None):
    """Repair missing shared gameplay libraries without changing mod selection."""
    import plugin_dependencies

    idle()
    with locked(repo):
        state = load(repo)
        profile_valid(repo)
        profile = json.loads(
            (root(repo) / "profile/profile.json").read_text(encoding="utf-8")
        )
        records = {
            key: metadata(repo, key, verify=False)
            for key, value in state["mods"].items()
            if value["enabled"]
        }
        needed = plugin_dependencies.required_records(repo, records)
        moveset_support.preflight(repo, records)
        plugin_dependencies.preflight(repo, needed)
        present = (profile.get("plugin_runtime") or {}).get("dependencies", [])
        runtime_changed = False
        if profile.get('backend') == 'arcropolis':
            import runtime_cache
            try:
                runtime_cache.arc(repo, True)
                if profile.get('plugin_runtime'):
                    runtime_cache.plugin(repo, profile['plugin_runtime'])
            except (ValueError, OSError):
                runtime_changed = True
        if runtime_changed or set(needed) - set(present):
            arc_backend.ensure(repo)
            commit(
                repo,
                state,
                record_history=False,
                callback=callback,
                cancel=cancel,
                force_runtime=True,
            )
    return listing(repo)


def play(repo, vanilla=False, callback=None, cancel=None):
    if not vanilla:
        prepare_gameplay(repo, callback, cancel)
    state = load(repo)
    build = base.build_dir(repo)
    if base.digest(build / "work/ssbu_native.exe") != state["runtime_sha256"]:
        raise ValueError(
            "OpenSmash wurde aktualisiert. Modmanager neu einrichten und Mods erneut pruefen."
        )
    profile_valid(repo)
    listing(repo)
    logs = build / "logs"
    logs.mkdir(exist_ok=True)
    log = logs / ("mods-" + ("vanilla-" if vanilla else "") + stamp() + ".log")
    args = [
        sys.executable,
        str(repo / "scripts/run.py"),
        "--play",
        "--userdata",
        str(build / "saves"),
        "--seconds",
        "0",
        "--log",
        str(log),
    ]
    profile = json.loads((root(repo) / "profile/profile.json").read_text())
    arc = not vanilla and profile.get("backend") == "arcropolis"
    if arc:
        import runtime_cache

        runtime_cache.arc(repo, True)
        if profile.get("plugin_runtime"):
            import plugin_runtime

            runtime_cache.plugin(repo, profile["plugin_runtime"])
        import playback

        playable, playable_env = playback.prepare(repo, profile)
        args.extend(["--exe", playable])
    env = dict(
        SSBU_LOOSE_FILES="0" if vanilla or arc else "1",
        SSBU_LOOSE_RAW="1",
        SSBU_CHARACTERS=str(
            root(repo)
            / (
                "empty"
                if vanilla or arc
                else "profile/" + profile.get("asset_dir", "assets")
            )
        ),
        SSBU_MODS=str(root(repo) / "empty"),
        SSBU_SKYLINE="0",
        SSBU_FIGHTER_SRC="0",
        SSBU_SHOW="1",
    )
    # OpenSmash defaults these paths relative to the EXE. Plugin EXEs live
    # deeper in work/, so bind every normal route to the user's original files.
    env.update(
        SSBU_GRAPHICS_CONFIG=str(build / "config/graphics.ini"),
        SSBU_CONFIG=str(build / "config/controllers.ini"),
        SSBU_DLC_LIST=str(build / "config/dlc.txt"),
    )
    if arc:
        env.update(
            SSBU_SKYLINE="1",
            SSBU_SD=str(root(repo) / "profile"),
            SSBU_PLUGIN_BIN=arc_backend.BIN,
        )
    if arc and profile.get("plugin_runtime"):
        env.update(
            SSBU_PLUGIN_BIN=profile["plugin_runtime"]["plugin_bin"],
            SSBU_NRO_BIN=profile["plugin_runtime"]["nro_bin"],
        )
    if arc:
        env.update(playable_env)
    if arc:
        env.update(base.alternate_launch_env(build))
    for k, v in env.items():
        args.extend(["--env", k + "=" + v])
    proc = subprocess.Popen(
        args, cwd=repo, creationflags=0x08000000 if sys.platform == "win32" else 0
    )
    return dict(
        message="Spiel gestartet. Mod-Aenderungen erfordern einen Neustart.",
        pid=proc.pid,
        log=str(log),
    )


def batch_preview(repo, sources, callback=None, cancel=None, previous_job=None):
    import batch_import
    from types import SimpleNamespace

    return batch_import.preview(
        SimpleNamespace(**globals()), repo, sources, callback, cancel, previous_job
    )


def batch_install(repo, job_id, expected=None, callback=None, cancel=None):
    import batch_import
    from types import SimpleNamespace

    return batch_import.install(
        SimpleNamespace(**globals()), repo, job_id, expected, callback, cancel
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument(
        "action",
        choices=[
            "setup",
            "bootstrap",
            "check",
            "list",
            "inspect",
            "install",
            "enable",
            "remove",
            "change-set",
            "refresh",
            "repair-plugins",
            "undo",
            "play",
            "uninstall",
            "batch-preview",
            "download-preview",
            "batch-install",
            "batch-configure",
            "batch-discard",
            "export",
            "export-list",
            "list-preview",
            "list-install",
        ],
    )
    ap.add_argument("--source", type=Path)
    ap.add_argument("--expected")
    ap.add_argument("--id")
    ap.add_argument("--value", choices=["0", "1"], default="1")
    ap.add_argument("--vanilla", action="store_true")
    ap.add_argument("--job")
    ap.add_argument("--token")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--cancel-token")
    ap.add_argument("--destination", type=Path)
    a = ap.parse_args()
    repo = a.repo.resolve(strict=True)
    callback = lambda event: print(json.dumps(event, ensure_ascii=False), flush=True)
    cancel = None
    if a.cancel_token:
        import re

        if not re.fullmatch("[0-9a-f]{32}", a.cancel_token):
            raise ValueError("Ungueltiger Abbruchauftrag.")
        cancel = lambda: (
            root(repo) / "incoming" / ("operation-" + a.cancel_token + ".cancel")
        ).exists()
    if a.action == "setup":
        result = setup(repo, a.source)
    elif a.action in ("export-list", "list-preview", "list-install"):
        import mod_lists
        from types import SimpleNamespace

        api = SimpleNamespace(**globals())
        if a.action == "export-list":
            result = mod_lists.export(api, repo, a.destination)
        elif a.action == "list-preview":
            result = mod_lists.preview(api, repo, a.source)
        else:
            result = mod_lists.install(api, repo, a.source, a.token, callback, cancel)
    elif a.action == "export":
        import library_export
        from types import SimpleNamespace

        if not a.destination:
            raise ValueError("ZIP-Exportziel fehlt.")
        result = library_export.export(
            SimpleNamespace(**globals()), repo, a.destination
        )
    elif a.action == "check":
        import setup_checks

        result = setup_checks.check(repo)
    elif a.action == "bootstrap":
        result = bootstrap(repo)
    elif a.action == "download-preview":
        import downloads

        raw = sys.stdin.read(262145)
        if len(raw) > 262144:
            raise ValueError("Download-Auswahl zu gross.")
        result = downloads.Queue(repo).preview(json.loads(raw).get("ids"), callback)
    elif a.action == "batch-preview":
        raw = sys.stdin.read(262145) if a.stdin else "{}"
        if len(raw) > 262144:
            raise ValueError("Zu viele Importpfade.")
        payload = json.loads(raw)
        result = batch_preview(
            repo,
            payload.get("sources", []),
            lambda event: print(json.dumps(event, ensure_ascii=False), flush=True),
            previous_job=payload.get("previous_job"),
        )
    elif a.action == "batch-install":
        result = batch_install(repo, a.job, a.token, callback, cancel)
    elif a.action == "batch-configure":
        import batch_import
        from types import SimpleNamespace

        raw = sys.stdin.read(262145)
        if len(raw) > 262144:
            raise ValueError("Importauswahl zu gross.")
        result = batch_import.configure(
            SimpleNamespace(**globals()),
            repo,
            a.job,
            a.token,
            json.loads(raw).get("choices", {}),
        )
    elif a.action == "batch-discard":
        import batch_import
        from types import SimpleNamespace

        batch_import.discard(SimpleNamespace(**globals()), repo, a.job)
        result = dict(discarded=True)
    elif a.action == "list":
        result = listing(repo)
    elif a.action == "inspect":
        result = inspect(repo, a.source)
    elif a.action == "install":
        result = install(repo, a.source, a.expected)
    elif a.action in ("enable", "remove"):
        result = change(repo, a.id, a.action, a.value == "1", callback, cancel)
    elif a.action == "change-set":
        raw = sys.stdin.read(262145)
        if len(raw) > 262144:
            raise ValueError("Mod-Auswahl zu gross.")
        result = change_many(repo, json.loads(raw).get("values"), callback, cancel)
    elif a.action == "repair-plugins":
        result = prepare_gameplay(repo, callback, cancel)
    elif a.action == "refresh":
        result = refresh(repo, callback, cancel)
    elif a.action == "undo":
        result = undo(repo)
    elif a.action == "uninstall":
        result = uninstall(repo)
    else:
        result = play(repo, a.vanilla, callback, cancel)
    return result


if __name__ == "__main__":
    try:
        print(json.dumps(dict(ok=True, result=main()), ensure_ascii=False))
    except __import__("batch_import").Cancelled as exc:
        print(
            json.dumps(
                dict(ok=True, result=dict(cancelled=True, message=str(exc))),
                ensure_ascii=False,
            )
        )
    except Exception as exc:
        detail = None
        try:
            import traceback, uuid

            repo = Path(sys.argv[sys.argv.index("--repo") + 1]).resolve(strict=True)
            logs = base.contained(root(repo), root(repo) / "logs")
            if logs.is_dir():
                detail = logs / (
                    "error-" + stamp() + "-" + uuid.uuid4().hex[:6] + ".log"
                )
                detail.write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        message = str(exc) + (("\nDetails: " + str(detail)) if detail else "")
        print(json.dumps(dict(ok=False, error=message), ensure_ascii=False))
        sys.exit(1)
