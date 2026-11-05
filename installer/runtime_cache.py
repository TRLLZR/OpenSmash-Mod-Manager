"""Validate immutable generated outputs using persistent file fingerprints."""

import json, re
from pathlib import Path
import arc_backend, plugin_runtime, catalog


def arc(repo, required=True):
    marker = arc_backend.location(repo) / "runtime.json"
    if not marker.exists():
        return arc_backend.valid(repo, required)
    try:
        record = json.loads(marker.read_text(encoding="utf-8-sig"))
        if (
            record["app"] != arc_backend.APP
            or record["builder"] != arc_backend.signature()
        ):
            raise ValueError("Loader-Buildversion geaendert.")
        if record.get('source_inputs') != arc_backend.source_inputs(repo):
            raise ValueError('OpenSmash-Buildquellen geaendert.')
        if (
            catalog.digest(
                repo, arc_backend.base.build_dir(repo) / "work/ssbu_native.exe"
            )
            != record["native_sha256"]
        ):
            raise ValueError("OpenSmash-Version geaendert.")
        for name, sha in record["files"].items():
            if catalog.digest(repo, arc_backend.resolve_file(repo, name)) != sha:
                raise ValueError("Laufzeitdatei geaendert: " + name)
        return record
    except (OSError, ValueError, KeyError):
        if required:
            raise
        return None


def plugin(repo, record):
    if record.get('legacy_alias_inputs', {}) != plugin_runtime.legacy_addresses.inputs(repo):
        raise ValueError('Spielabbilder fuer gepruefte Versions-Aliase geaendert; Laufzeit neu erstellen.')
    if record.get('dependency_fingerprint', {}) != plugin_runtime.dependency_hashes(repo, record.get('dependencies', [])):
        raise ValueError('Gameplay-Bibliotheken oder Spielversion geaendert; Plugin-Laufzeit neu erstellen.')
    if record.get('source_inputs') != arc_backend.source_inputs(repo):
        raise ValueError('OpenSmash-Buildquellen geaendert; Plugin-Laufzeit neu erstellen.')
    if record.get('plugin_builder') != plugin_runtime.base.digest(Path(plugin_runtime.__file__)):
        raise ValueError('Plugin-Builder geaendert; Plugin-Laufzeit neu erstellen.')
    if record.get("app") != plugin_runtime.APP:
        return plugin_runtime.valid(repo, record)
    key = record.get("key", "")
    if record.get("app") != plugin_runtime.APP or not re.fullmatch("[0-9a-f]{20}", key):
        raise ValueError("Ungueltige Plugin-Laufzeit.")
    if (
        record.get("exe") != "modmanager_plugins/" + key + "/" + arc_backend.EXE
        or record.get("plugin_bin") != "plugin_bin"
        or record.get("nro_bin") != "../../nro_bin_eh_o2"
    ):
        raise ValueError("Ungueltige Plugin-Laufzeitpfade.")
    if not record.get("files") or "@build/work/" + record["exe"] not in record["files"]:
        raise ValueError("Unvollstaendige Plugin-Laufzeit.")
    for name, sha in record["files"].items():
        if catalog.digest(repo, arc_backend.resolve_file(repo, name)) != sha:
            raise ValueError("Plugin-Laufzeit geaendert: " + name)
    return record
