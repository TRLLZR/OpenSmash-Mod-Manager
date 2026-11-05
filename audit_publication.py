"""Check a clean publication tree without reading a real game or user library.

This catches accidental private/generated files and missing notices. It cannot
establish copyright ownership, trademark clearance or the absence of secrets.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
ALLOWED_NATIVE = {"installer/7za.exe", "installer/UnRAR64.dll"}
FORBIDDEN_PARTS = {
    "runtime",
    "runtime-downloads",
    "dev-tools",
    "test-scratch",
    "saves",
    "downloads",
    "logs",
    "library",
    "profile",
    "opensmash_mods",
    "drybowser_local",
    "build",
    "gameplay-qa",
    "performance-qa",
}
FORBIDDEN_SUFFIXES = {
    ".exe",
    ".dll",
    ".obj",
    ".pdb",
    ".elf",
    ".nro",
    ".nsp",
    ".xci",
    ".nca",
    ".arc",
    ".db",
    ".sqlite",
    ".pem",
    ".key",
    ".pyc",
    ".pyo",
}
TEXT_SUFFIXES = {
    ".patch",
    ".py",
    ".ps1",
    ".cs",
    ".h",
    ".xaml",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".bat",
    ".manifest",
}
SECRET_PATTERNS = (
    re.compile(rb"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}"),
    re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
REQUIRED = {
    "README.md",
    "installer/README.md",
    "docs/MODS.md",
    "LICENSE.txt",
    "THIRD_PARTY_NOTICES.txt",
    "installer/LICENSE.txt",
    "installer/THIRD_PARTY_NOTICES.txt",
    ".gitignore",
    ".gitattributes",
    ".github/workflows/validate.yml",
    "installer/BrandLogo.png",
    "installer/BrandIcon.png",
    "installer/BrandIcon.ico",
    "installer/BRAND_ASSETS.json",
    "installer/7ZIP_LICENSE.txt",
    "installer/7ZIP_LGPL.txt",
    "installer/UNRAR_LICENSE.txt",
    "installer/7ZIP_DISTRIBUTION.json",
    "installer/UNRAR_DISTRIBUTION.json",
    "installer/test_data/rar/README.md",
    "third_party/7zip/7z2605-src.tar.xz",
    *ALLOWED_NATIVE,
}


def validate(files):
    """Validate named publication bytes; never echo suspected secret contents."""
    if len({name.casefold() for name in files}) != len(files):
        raise ValueError("Case-colliding publication paths")
    missing = REQUIRED - files.keys()
    if missing:
        raise ValueError("Missing public files: " + ", ".join(sorted(missing)))
    for name, data in files.items():
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
            raise ValueError("Unsafe publication path: " + name)
        if any(
            part.lower() in FORBIDDEN_PARTS or part.startswith("checkpoint-")
            for part in path.parts
        ):
            raise ValueError("Private/generated directory in publication: " + name)
        if path.suffix.lower() in FORBIDDEN_SUFFIXES and name not in ALLOWED_NATIVE:
            raise ValueError("Unexpected native/private file: " + name)
        if path.name.startswith(".env") or path.name in {
            "settings.json",
            "install-state.json",
        }:
            raise ValueError("Personal configuration in publication: " + name)
        if name.endswith("-result.json") or name.startswith("installer/BERICHT_"):
            raise ValueError("Internal case report in publication: " + name)
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = data.decode("utf-8-sig")
            if (
                path.suffix.lower() == ".ps1"
                and any(ord(c) > 127 for c in text)
                and not data.startswith(b"\xef\xbb\xbf")
            ):
                raise ValueError("PowerShell needs a UTF-8 BOM: " + name)
            if any(pattern.search(data) for pattern in SECRET_PATTERNS):
                raise ValueError("Possible credential material in: " + name)
    seven = json.loads(files["installer/7ZIP_DISTRIBUTION.json"])
    unrar = json.loads(files["installer/UNRAR_DISTRIBUTION.json"])
    for name, digest in {
        "installer/7za.exe": seven["binary_sha256"],
        "third_party/7zip/7z2605-src.tar.xz": seven["source_sha256"],
        "installer/UnRAR64.dll": unrar["sha256"],
    }.items():
        if hashlib.sha256(files[name]).hexdigest() != digest:
            raise ValueError("Pinned dependency changed: " + name)
    for suffix in ("LICENSE.txt", "THIRD_PARTY_NOTICES.txt"):
        if files[suffix] != files["installer/" + suffix]:
            raise ValueError("Root/application notice mismatch: " + suffix)
    fixtures = json.loads(files["installer/test_data/rar/fixtures.json"])
    for name, digest in fixtures.items():
        if (
            hashlib.sha256(files["installer/test_data/rar/" + name]).hexdigest()
            != digest
        ):
            raise ValueError("Fixture changed: " + name)
    return dict(
        ok=True,
        checked_files=len(files),
        pinned_native_files=2,
        notices_present=True,
        corresponding_7zip_source=True,
        limitation="Publication hygiene only; no legal clearance or exhaustive secret detection.",
    )


def read_tree(root):
    files = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        if path.is_symlink() or path.is_junction():
            raise ValueError("Links are not publication files: " + str(relative))
        if path.is_file():
            files[relative.as_posix()] = path.read_bytes()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(validate(read_tree(args.root.resolve(strict=True))), indent=2))


if __name__ == "__main__":
    main()
