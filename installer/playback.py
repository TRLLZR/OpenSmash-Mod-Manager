"""Use OpenSmash's normal playable EXE designation, preserving saved audio policy."""

import json, os, shutil, uuid
from pathlib import Path
import drybowser as base, arc_backend, catalog

APP = "OpenSmash-Playable-v1"


def alias(repo, source, directory):
    source = source.resolve()
    directory = base.contained(base.build_dir(repo) / "work", directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "ssbu_user.exe"
    marker = directory / "playable.json"
    sha = catalog.digest(repo, source)
    old = json.loads(marker.read_text(encoding="utf-8")) if marker.exists() else None
    if old and old.get("app") != APP:
        raise ValueError("Fremde spielbare Laufzeit; nichts ersetzt.")
    if target.exists():
        existing = catalog.digest(repo, target)
        if existing != sha and (not old or existing != old.get("sha256")):
            raise ValueError(
                "Spielbarer Starter wurde extern geaendert. Nichts ueberschrieben."
            )
        if existing == sha:
            if not old:
                base.write_json(marker, dict(app=APP, sha256=sha))
            return target
    temporary = directory / ("ssbu_user.exe.pending-" + uuid.uuid4().hex)
    try:
        shutil.copy2(source, temporary)
        if base.digest(temporary) != sha:
            raise ValueError("Spielbarer Starter konnte nicht geprueft werden.")
        os.replace(temporary, target)
        base.write_json(marker, dict(app=APP, sha256=sha))
    finally:
        temporary.unlink(missing_ok=True)
    return target


def prepare(repo, profile):
    work = base.build_dir(repo) / "work"
    record = profile.get("plugin_runtime")
    if record:
        source = base.contained(work, work / record["exe"])
        target = alias(repo, source, source.parent)
        return target.relative_to(work).as_posix(), dict(
            SSBU_PLUGIN_BIN=record["plugin_bin"], SSBU_NRO_BIN=record["nro_bin"]
        )
    source = work / arc_backend.EXE
    key = catalog.fingerprint(
        [catalog.digest(repo, source), catalog.digest(repo, work / arc_backend.DLL)]
    )[:20]
    directory = work / "modmanager_play" / ("arc-" + key)
    target = alias(repo, source, directory)
    for file in work.glob("*.dll"):
        if file.name.lower().startswith("ssbu_game") and file.name != arc_backend.DLL:
            continue
        destination = directory / file.name
        if destination.exists():
            # Both paths are owned runtime inputs. Never replace a foreign file.
            if destination.stat().st_ino == file.stat().st_ino:
                continue
            if catalog.digest(repo, destination) == catalog.digest(repo, file):
                continue
            raise ValueError(
                "Private Laufzeit-DLL wurde extern geaendert: " + file.name
            )
        try:
            os.link(file, destination)
        except OSError:
            shutil.copy2(file, destination)
    return target.relative_to(work).as_posix(), dict(
        SSBU_PLUGIN_BIN="../../" + arc_backend.BIN, SSBU_NRO_BIN="../../nro_bin_eh_o2"
    )
