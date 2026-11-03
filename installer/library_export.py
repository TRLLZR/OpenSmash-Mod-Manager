"""Portable mod libraries: assets/configuration/NROs only, never game or save files."""

import hashlib, json, os, tempfile, zipfile
from pathlib import Path

APP = "OpenSmash-ModPack-v1"
MANIFEST = "opensmash-pack.json"


def export(m, repo, destination):
    from batch_import import safe_name, MAX_ITEMS, MAX_FILES, MAX_BYTES

    destination = Path(destination).resolve()
    if destination.suffix.lower() != ".zip":
        raise ValueError("Bitte eine ZIP-Datei als Exportziel waehlen.")
    root = m.root(repo)
    if destination.is_relative_to(root) or destination.is_relative_to(repo / "build"):
        raise ValueError(
            "Export bitte ausserhalb der verwalteten Spiel-/Moddateien speichern."
        )
    if not destination.parent.is_dir():
        raise ValueError("Export-Zielordner fehlt.")
    state = m.load(repo)
    records = {key: m.metadata(repo, key) for key in state["mods"]}
    if not records:
        raise ValueError("Keine installierten Mods zum Exportieren vorhanden.")
    if len(records) > MAX_ITEMS:
        raise ValueError("Die Bibliothek ueberschreitet die Paketgrenze von 1024 Mods.")
    count = 1
    size = 0
    for key, record in records.items():
        for entry in record["entries"]:
            count += 1
            size += (
                (root / "library" / key / "assets" / safe_name(entry["path"]))
                .stat()
                .st_size
            )
        if not any(e["path"] == "info.toml" for e in record["entries"]):
            count += 1
            size += 4096
    if count > MAX_FILES or size + 16 * 1024**2 > MAX_BYTES:
        raise ValueError(
            "Die Bibliothek ueberschreitet die Paketgrenze von 64000 Dateien / 8 GiB."
        )
    document = dict(app=APP, version=1, mods=[])
    fd, temp = tempfile.mkstemp(
        prefix=".opensmash-export-", suffix=".zip", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temp)
    try:
        with zipfile.ZipFile(
            temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True
        ) as z:
            for key, record in records.items():
                relative = "mods/" + key
                hashes = {}
                for entry in record["entries"]:
                    name = safe_name(entry["path"])
                    src = m.base.contained(
                        root / "library" / key / "assets",
                        root / "library" / key / "assets" / name,
                    )
                    digest = hashlib.sha256()
                    with src.open("rb") as source, z.open(
                        relative + "/" + name, "w", force_zip64=True
                    ) as out:
                        while True:
                            block = source.read(1024 * 1024)
                            if not block:
                                break
                            digest.update(block)
                            out.write(block)
                    if digest.hexdigest() != entry["sha256"]:
                        raise ValueError(
                            "Mod-Datei hat sich waehrend des Exports geaendert: "
                            + record["name"]
                        )
                    hashes[name] = digest.hexdigest()
                if "info.toml" not in hashes:
                    data = (
                        "display_name = "
                        + json.dumps(state["mods"][key]["name"], ensure_ascii=True)
                        + "\n"
                    ).encode()
                    z.writestr(relative + "/info.toml", data)
                    hashes["info.toml"] = hashlib.sha256(data).hexdigest()
                document["mods"].append(
                    dict(
                        folder=relative,
                        name=state["mods"][key]["name"],
                        enabled=state["mods"][key]["enabled"],
                        files=hashes,
                    )
                )
            metadata = json.dumps(document, ensure_ascii=False, indent=2).encode(
                "utf-8"
            )
            if len(metadata) > 16 * 1024**2:
                raise ValueError("Das Paketverzeichnis ueberschreitet 16 MiB.")
            z.writestr(MANIFEST, metadata)
        # Streaming hashes validate copied bytes; central-directory CRC also detects archive faults.
        with zipfile.ZipFile(temporary) as z:
            if z.testzip() is not None:
                raise ValueError(
                    "Export-ZIP konnte nicht fehlerfrei verifiziert werden."
                )
        os.replace(temporary, destination)
        return dict(
            path=str(destination),
            mods=len(records),
            bytes=destination.stat().st_size,
            message="Alle installierten Mods wurden exportiert, einschliesslich pausierter Mods und ihrer Konfiguration.",
        )
    finally:
        temporary.unlink(missing_ok=True)


def manifest(folder):
    """Return validated path-to-options mapping; no trusted actions from pack metadata."""
    from batch_import import safe_name, MAX_ITEMS

    file = folder / MANIFEST
    if not file.is_file():
        return {}
    if file.stat().st_size > 16 * 1024**2:
        raise ValueError("Modpaket-Verzeichnis ist zu gross.")
    data = json.loads(file.read_text(encoding="utf-8-sig"))
    if (
        data.get("app") != APP
        or data.get("version") != 1
        or not isinstance(data.get("mods"), list)
        or len(data["mods"]) > MAX_ITEMS
    ):
        raise ValueError("Ungueltiges OpenSmash-Modpaket.")
    out = {}
    for item in data["mods"]:
        name = safe_name(item["folder"])
        if (
            name in out
            or type(item.get("enabled")) is not bool
            or not isinstance(item.get("files"), dict)
        ):
            raise ValueError("Ungueltiger Mod-Eintrag im Paket.")
        files = {safe_name(p): sha for p, sha in item["files"].items()}
        if not all(
            isinstance(sha, str)
            and len(sha) == 64
            and all(c in "0123456789abcdef" for c in sha)
            for sha in files.values()
        ):
            raise ValueError("Ungueltige Mod-Pruefsummen im Paket.")
        path = (folder / name).resolve()
        if not path.is_relative_to(folder.resolve()):
            raise ValueError("Unsicherer Modpaket-Pfad.")
        out[path] = dict(enabled=item["enabled"], files=files)
    return out
