"""Export a reviewed source ZIP and a separate clean GitHub publishing folder."""

import ast
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from audit_publication import validate

WORK = Path(__file__).resolve().parent
SOURCE = WORK / "installer"


def checked_names(names):
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
            raise ValueError("Unsafe publication inventory entry")
        yield name


def check_build_inputs(files):
    # Build metadata and source publication must agree, including user documents.
    tree = ast.parse(files["build_release.py"].decode("utf-8-sig"))
    names = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "names" for t in node.targets)
    )
    generated = {"ModManager.exe", "Uninstall.exe"}
    missing = {
        "installer/" + name for name in names if name not in generated
    } - files.keys()
    if missing:
        raise ValueError(
            "Build inputs missing from source publication: "
            + ", ".join(sorted(missing))
        )


def collect():
    inventory_path = WORK / "publication_inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    # Templates live apart from local notes; exported checkouts use their root.
    public = (
        WORK / "publication" if (WORK / "publication/README.md").is_file() else WORK
    )
    paths = {"publication_inventory.json": inventory_path}
    for name in checked_names(inventory["installer"]):
        paths["installer/" + name] = SOURCE / name
    for path in (SOURCE / "test_data").rglob("*"):
        if path.is_file():
            paths["installer/" + path.relative_to(SOURCE).as_posix()] = path
    for name in checked_names(inventory["tools"]):
        paths[name] = WORK / name
    for name in checked_names(inventory["public_files"]):
        paths[name] = public / name
    paths["third_party/7zip/7z2605-src.tar.xz"] = (
        WORK / "third_party/7zip/7z2605-src.tar.xz"
    )
    files = {}
    for name, path in paths.items():
        if (
            not path.resolve(strict=True).is_relative_to(WORK.resolve())
            or path.is_symlink()
            or path.is_junction()
        ):
            raise ValueError("Linked publication source: " + name)
        data = path.read_bytes()
        if path.suffix.lower() in {
            ".patch",
            ".py",
            ".ps1",
            ".cs",
            ".h",
            ".md",
            ".txt",
            ".xaml",
            ".json",
            ".bat",
            ".yml",
        }:
            data.decode("utf-8-sig")
            if any(
                token in data.lower()
                for token in (
                    os.environ.get("USERNAME", "__unset_user__")
                    .lower()
                    .encode("utf-8"),
                    b"d:\\games\\",
                    b"d:\\downloads\\",
                )
            ):
                raise ValueError("Private development path in source artifact: " + name)
        files[name] = data
    check_build_inputs(files)
    validate(files)
    return inventory["version"], files


def main():
    version, files = collect()
    records = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    files["SOURCE_MANIFEST.json"] = (
        json.dumps(dict(version=version, files=records), indent=2) + "\n"
    ).encode("utf-8")
    destination = WORK / "github-ready"
    destination.mkdir(exist_ok=True)
    folder = Path(
        tempfile.mkdtemp(
            prefix="OpenSmash-Mod-Manager-v" + version + "-", dir=destination
        )
    )
    assert folder.resolve().is_relative_to(destination.resolve())
    for name, data in files.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    # Never replace an existing publishing checkout or copy local .git history.
    target = WORK / f"OpenSmash_Mod_Manager_Source_v{version}.zip"
    temporary = target.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(
            temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6
        ) as archive:
            for name, data in sorted(files.items()):
                archive.writestr(name, data)
        with zipfile.ZipFile(temporary) as archive:
            assert archive.testzip() is None
            for name, digest in records.items():
                assert hashlib.sha256(archive.read(name)).hexdigest() == digest
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(
        digest + "  " + target.name + "\n", encoding="ascii"
    )
    result = dict(
        source_zip=str(target),
        files=len(records),
        sha256=digest,
        bytes=target.stat().st_size,
        github_folder=str(folder),
        publication=validate(files),
    )
    (WORK / "source-export-result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
