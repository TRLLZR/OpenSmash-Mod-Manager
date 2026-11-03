"""Resolve shared gameplay libraries by NRO references and extended-slot assets.

These are framework dependencies, never rules for a particular mod title. Only
the listed, hashed NRO is used from an upstream archive; optional flags, example
mods and authoring scripts are deliberately left out.
"""

import hashlib
import json
import os
import re
import urllib.request
import uuid
import zipfile
from pathlib import Path

REGISTRY = {
    "param_config": {
        "filename": "libparam_config.nro",
        "version": "6.5",
        "url": "https://github.com/CSharpM7/lib_paramconfig/releases/download/6.5/libparam_config.nro",
        "sha256": "f014f3143ca8ff0b9b2dcbacdb07acc598c2a76cacd7f754097ea2a8f896889a",
    },
    "csk": {
        "filename": "libthe_csk_collection.nro",
        "version": "5.0.6",
        "game_versions": ["13.0.4"],
        "nro_sha256": "4d91c3d771b5c846a58ba31e123ff2aca5847614493235e754930a621c19c892",
        "unavailable": "The CSK Collection 6.0.0 fuer Smash 13.0.5 fehlt. Die oeffentliche Version 5.0.6 ist inkompatibel. Bitte die passende Bibliothek vom Autor beziehen und als Mod importieren: https://gamebanana.com/mods/499008",
        "url": "https://gamebanana.com/dl/1745532",
        "sha256": "6a4c07f206d4b42945d08d86f1d5959c39d0c6f784b04236ee7f5e006b1cd64f",
        "member": "atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libthe_csk_collection.nro",
    },
    "one_slot_effects": {
        "filename": "libone_slot_eff.nro",
        "version": "13.0.5",
        "game_versions": ["13.0.5"],
        "url": "https://gamebanana.com/dl/1806494",
        "sha256": "2116f2c20070ea2050bf220717526927ed82786fad801c66a790e4d65729f9be",
        "member": "one_slot_eff_13-0-5/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libone_slot_eff.nro",
    },
}
MAX_ARTIFACT = 16 * 1024**2


def required(plugins, asset_paths=()):
    result = set()
    provided = {Path(p).name.casefold() for p in plugins}
    for plugin in plugins:
        data = Path(plugin).read_bytes()
        for key, record in REGISTRY.items():
            if (
                record["filename"].encode("ascii") in data
                and record["filename"].casefold() not in provided
            ):
                result.add(key)
    # Slotted effects need a shared effect loader even when the gameplay NRO
    # does not import that library directly. Standard slots remain untouched.
    if plugins and any(
        re.search(r"(?:^|/)effect/.*(?:[/_]c)(\d{2,})(?:[/. _]|$)", p, re.I)
        and any(int(n) > 7 for n in re.findall(r"(?:[/_]c)(\d{2,})", p, re.I))
        for p in asset_paths
    ):
        if REGISTRY["one_slot_effects"]["filename"].casefold() not in provided:
            result.add("one_slot_effects")
    return sorted(result)


def fingerprint(keys):
    return {key: REGISTRY[key]["sha256"] for key in sorted(keys)}


def preflight(repo, keys):
    """Reject known game-version mismatches before downloading or compiling."""
    if not any(REGISTRY[key].get("game_versions") for key in keys):
        return
    import drybowser as base

    state = json.loads(
        (base.build_dir(Path(repo)) / "state.json").read_text(encoding="utf-8")
    )
    version = state.get("game_version")
    for key in keys:
        record = REGISTRY[key]
        if record.get("game_versions") and version not in record["game_versions"]:
            raise ValueError(
                record.get("unavailable")
                or (
                    record["filename"]
                    + " ist nicht fuer Spielversion "
                    + str(version)
                    + " freigegeben."
                )
            )


def check_provided(repo, plugins):
    """Recognize incompatible upstream binaries even when supplied or renamed."""
    by_hash = {
        r["nro_sha256"]: key for key, r in REGISTRY.items() if r.get("nro_sha256")
    }
    found = set()
    for path in plugins:
        path = Path(path)
        if (
            not path.is_file()
            or path.is_symlink()
            or path.is_junction()
            or path.stat().st_size > 128 * 1024**2
        ):
            continue
        with path.open("rb") as stream:
            key = by_hash.get(hashlib.file_digest(stream, "sha256").hexdigest())
        if key:
            found.add(key)
    preflight(repo, found)


def _download(record):
    if record["url"].startswith("https://gamebanana.com/"):
        import gamebanana

        response = gamebanana.open_url(record["url"], "download", timeout=40)
    else:
        response = urllib.request.urlopen(
            urllib.request.Request(
                record["url"], headers={"User-Agent": "OpenSmashModManager/3.5"}
            ),
            timeout=40,
        )
    with response:
        data = response.read(MAX_ARTIFACT + 1)
    if len(data) > MAX_ARTIFACT or hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ValueError(
            "Pruefsumme der Gameplay-Abhaengigkeit stimmt nicht. Download verworfen."
        )
    return data


def obtain(repo, key):
    preflight(repo, [key])
    record = REGISTRY[key]
    folder = Path(repo) / "opensmash_mods/plugin-dependencies"
    folder.mkdir(exist_ok=True)
    if folder.is_symlink() or folder.is_junction():
        raise ValueError("Plugin-Abhaengigkeiten duerfen keine Verknuepfung sein.")
    artifact = folder / (record["sha256"] + (".zip" if "member" in record else ".nro"))
    if artifact.is_symlink() or artifact.is_junction():
        raise ValueError("Verknuepfung im Abhaengigkeitscache.")
    if (
        not artifact.exists()
        or hashlib.sha256(artifact.read_bytes()).hexdigest() != record["sha256"]
    ):
        data = _download(record)
        temporary = folder / (uuid.uuid4().hex + ".download")
        try:
            temporary.write_bytes(data)
            os.replace(temporary, artifact)
        finally:
            temporary.unlink(missing_ok=True)
    if "member" not in record:
        return artifact
    with zipfile.ZipFile(artifact) as archive:
        entry = archive.getinfo(record["member"])
        if entry.file_size > MAX_ARTIFACT:
            raise ValueError("Gameplay-Bibliothek ist zu gross.")
        data = archive.read(entry)
    target = folder / (record["sha256"] + "-" + record["filename"])
    if target.is_symlink() or target.is_junction():
        raise ValueError("Verknuepfung im Abhaengigkeitscache.")
    if not target.exists() or target.read_bytes() != data:
        temporary = folder / (uuid.uuid4().hex + ".nro.tmp")
        try:
            temporary.write_bytes(data)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return target


def required_records(repo, records):
    import catalog

    plugins, paths = [], []
    for key, record in records.items():
        for entry in record["entries"]:
            paths.append(entry["path"])
            if entry.get("kind") == "plugin":
                plugins.append(catalog.location(repo, key) / "assets" / entry["path"])
    return required(plugins, paths)
