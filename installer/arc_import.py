"""Read standard ARCropolis asset mods, without changing author configuration."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import tomllib
import drybowser as base


def known_package_name(entries):
    # Official v7.1.1 release: name only exact original contents, never a guess
    # based on an archive/folder name or a different training plugin build.
    training = {
        'libnro_hook.nro': 'ca7aec03aee49fea539dcb92569fea5bc5389f77377ba2a30e4d0b7ebd0255e6',
        'libparam_hook.nro': '3ed7a2945084176cbb7742d99878f1e8d3a0992feb0fef74be2cfbc68ac8fb88',
        'libtraining_modpack.nro': '38260daeb8f917c99ea3443b7d533ce2bffd8bae4890fc4baca9b317d9fcf829',
    }
    actual = {e['path']: e['sha256'] for e in entries}
    return 'Ultimate Training Modpack v7.1.1' if actual == training else None

CONFIG_FIELDS = {
    "unshare-blacklist": "list",
    "unshare_blacklist": "list",
    "keep-shared": "list",
    "keep_shared": "list",
    "preprocess-reshare": "map",
    "preprocess_reshare": "map",
    "share-to-vanilla": "map",
    "share_to_vanilla": "map",
    "share-to-added": "map",
    "share_to_added": "map",
    "new-shared-files": "map",
    "new_shared_files": "map",
    "new-dir-files": "files",
    "new_dir_files": "files",
    "new-dir-infos": "list",
    "new_dir_infos": "list",
    "new-dir-infos-base": "map",
    "new_dir_infos_base": "map",
}


def config(path):
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("config.json ist zu gross.")
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Ungueltige config.json: " + str(exc)) from exc
    if not isinstance(value, dict):
        raise ValueError("config.json muss ein JSON-Objekt enthalten.")
    for key, data in value.items():
        kind = CONFIG_FIELDS.get(key)
        if kind is None:
            raise ValueError("Unbekanntes ARCropolis-Konfigurationsfeld: " + key)
        if not isinstance(data, list if kind == "list" else dict):
            raise ValueError("Ungueltiger Wert in config.json: " + key)
        if kind == "files" and any(not isinstance(v, list) for v in data.values()):
            raise ValueError(
                "new-dir-files muss Verzeichnisse auf Dateilisten abbilden."
            )

    # Config contains only virtual archive references, never filesystem actions.
    def references(item):
        if isinstance(item, str):
            if (
                "\x00" in item
                or "\\" in item
                or any(p == ".." for p in PurePosixPath(item).parts)
            ):
                raise ValueError("Ungueltiger Archivpfad in config.json: " + item)
        elif isinstance(item, list):
            for child in item:
                references(child)
        elif isinstance(item, dict):
            for key, child in item.items():
                references(key)
                references(child)
        elif type(item) is not int or not 0 <= item < 2**40:
            raise ValueError("Ungueltige Archiv-Referenz in config.json.")

    for item in value.values():
        references(item)
    return value


def analyze(repo, asset_root, roots):
    build, game, arc, h40 = base.preflight(repo)
    try:
        entries, ignored, known = [], [], set()
        plugin_files = list(asset_root.glob("*.nro"))
        import plugin_runtime

        plugin_info = {p.name: plugin_runtime.inspect_nro(p) for p in plugin_files}
        new_files = 0
        for source in sorted(asset_root.rglob("*")):
            if not source.is_file():
                continue
            rel = source.relative_to(asset_root).as_posix()
            path = rel.lower()
            top = "/" not in path
            is_plugin = top and source.suffix.lower() == ".nro"
            is_plugin_config = (
                top
                and bool(plugin_files)
                and source.suffix.lower() in {".toml", ".ini", ".json"}
                and path not in {"config.json", "info.toml"}
            )
            metadata = top and (
                path in {"config.json", "info.toml"} or is_plugin or is_plugin_config
            )
            if top and path in {"config.ini", "fighter.json"} and not is_plugin_config:
                raise ValueError(path + " ist kein Standard-ARCropolis-Skin-Format.")
            if not top and source.suffix.lower() == ".nro":
                raise ValueError("Skyline-NROs bitte im Mod-Hauptordner ablegen.")
            if top and not metadata:
                continue
            if not top and path.split("/")[0] not in roots:
                ignored.append(
                    dict(path=path, reason="Begleitdatei ausserhalb der Spiel-Assets")
                )
                continue
            if path in known:
                raise ValueError(
                    "Doppelter Asset-Pfad (Gross-/Kleinschreibung): " + path
                )
            known.add(path)
            if path == "config.json":
                config(source)
            if is_plugin_config:
                if source.stat().st_size > 16 * 1024**2:
                    raise ValueError("Plugin-Konfiguration ist zu gross.")
                if source.suffix.lower() == ".toml":
                    tomllib.loads(source.read_text(encoding="utf-8-sig"))
                if source.suffix.lower() == ".json":
                    json.loads(source.read_text(encoding="utf-8-sig"))
            if source.stat().st_size >= 2**32:
                raise ValueError("Mod-Einzeldatei ist zu gross: " + path)
            if not metadata and arc.path_index_from_hash(h40(path)) is None:
                new_files += 1
            entry = dict(
                path=path,
                source_path=rel,
                sha256=base.digest(source),
                info="path:" + path,
                metadata=metadata,
            )
            if is_plugin:
                entry.update(kind="plugin", module=plugin_info[source.name]["module"])
            if is_plugin_config:
                entry.update(kind="plugin-config")
            entries.append(entry)
        assets = [e for e in entries if not e["metadata"]]
        if not assets and not plugin_files:
            raise ValueError(
                "Keine unterstuetzten Spiel-Assets oder Skyline-Plugins gefunden."
            )
        if len(entries) > 16000:
            raise ValueError("Mehr als 16000 Mod-Dateien.")
        name = known_package_name(entries) or asset_root.name
        info = asset_root / "info.toml"
        if info.is_file():
            try:
                name = str(
                    tomllib.loads(info.read_text(encoding="utf-8-sig")).get(
                        "display_name", name
                    )
                )[:140]
            except ValueError as exc:
                raise ValueError("Ungueltige info.toml: " + str(exc)) from exc
        warnings = [
            "ARCropolis: Kostuemdateien werden getrennt; config.json und Merge-Dateien bleiben vollstaendig erhalten."
        ]
        if plugin_files:
            warnings.append(
                "Skyline-Plugin: benoetigt eine lokal uebersetzte Plugin-Laufzeit; NRO und Begleitkonfiguration werden gemeinsam verwaltet."
            )
        if new_files:
            warnings.append(
                str(new_files)
                + " neue oder zusammenzufuehrende Archivdateien werden an ARCropolis uebergeben."
            )
        token = hashlib.sha256(
            json.dumps(
                dict(entries=entries, ignored=ignored, backend="arcropolis"),
                sort_keys=True,
            ).encode()
        ).hexdigest()
        return dict(
            id="mod-" + token[:16],
            name=name,
            token=token,
            backend="arcropolis",
            entries=entries,
            warnings=warnings,
            ignored=ignored,
            assets_root=str(asset_root),
            count=len(assets) + len(plugin_files),
            bytes=sum((asset_root / e["source_path"]).stat().st_size for e in entries),
        )
    finally:
        arc.f.close()
