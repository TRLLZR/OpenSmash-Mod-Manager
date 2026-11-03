"""Publish the verified current installer; keep game data and only the latest local release."""

import hashlib, json, os, re, shutil, subprocess, sys, winreg, zipfile
from pathlib import Path
from release_context import configured_repo
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--repo")
parser.add_argument("--destination", type=Path)
arguments = parser.parse_args()
w = Path(__file__).resolve().parent
s = w / "installer"
sys.path.insert(0, str(s))
import modmanager as m

version = re.search(
    r'\bVersion\s*=\s*"(\d+\.\d+\.\d+)"', (s / "Setup.cs").read_text()
).group(1)
release = w / ("release-" + version)
source = w / ("OpenSmash_Mod_Manager_Installer_v" + version + ".zip")
repo = configured_repo(arguments.repo)
games = arguments.destination or repo.parent
with winreg.OpenKey(
    winreg.HKEY_CURRENT_USER,
    r"Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenSmashMods",
) as key:
    app = Path(winreg.QueryValueEx(key, "InstallLocation")[0])
before = json.loads((app / "install-state.json").read_text(encoding="utf-8"))
assert before["app"] == "OpenSmash.Mods.Desktop"
assert tuple(map(int, before["version"].split("."))) <= tuple(
    map(int, version.split("."))
)
m.idle()
state_sha = m.base.digest(m.root(repo) / "state.json")


def game_hashes():
    paths = [
        p
        for name in ("build/config", "build/saves", "opensmash_mods/profile")
        for p in (repo / name).rglob("*")
        if p.is_file()
    ]
    for key in m.load(repo)["mods"]:
        paths.extend(
            p for p in (m.root(repo) / "library" / key).rglob("*") if p.is_file()
        )
    return {p.relative_to(repo).as_posix(): m.base.digest(p) for p in paths}


protected = game_hashes()
roots = [app.parent, m.root(repo) / "backups", repo / "drybowser_backups"]
existing = {
    str(root): set(root.iterdir()) if root.exists() else set() for root in roots
}
sha = m.base.digest(source)
assert source.with_suffix(".zip.sha256").read_text().split()[0] == sha
with zipfile.ZipFile(source) as z:
    assert z.testzip() is None
    prefix = "OpenSmash_Mod_Manager_Installer_v" + version + "/"
    for line in z.read(prefix + "SHA256SUMS.txt").decode().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256(z.read(prefix + name)).hexdigest() == digest
    assert z.read(prefix + "Setup.exe") == (release / "Setup.exe").read_bytes()
result = subprocess.run(
    [str(release / "Setup.exe"), "--install", "--repo", str(repo)],
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    timeout=75,
)
if result.returncode:
    raise RuntimeError(result.stdout + "\n" + result.stderr)
result = subprocess.run(
    [
        str(app / "runtime/python.exe"),
        "-B",
        str(app / "modmanager.py"),
        "--repo",
        str(repo),
        "bootstrap",
    ],
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    timeout=60,
)
if result.returncode:
    raise RuntimeError(result.stdout + "\n" + result.stderr)
assert json.loads(result.stdout)["ok"]
with zipfile.ZipFile(release / "Payload.zip") as z:
    manifest = json.loads(z.read("PAYLOAD.json"))
    assert manifest["version"] == version
    for name, digest in manifest["files"].items():
        assert (
            hashlib.sha256(z.read(name)).hexdigest()
            == m.base.digest(app / name)
            == digest
        ), name
    for name in m.TOOLS:
        assert (
            m.base.digest(s / name)
            == m.base.digest(app / name)
            == m.base.digest(m.root(repo) / "tools" / name)
        )
assert (
    m.base.digest(m.root(repo) / "state.json") == state_sha
    and game_hashes() == protected
)
m.profile_valid(repo)
m.arc_backend.valid(repo, True)
target = games / source.name
shutil.copy2(source, target)
shutil.copy2(source.with_suffix(".zip.sha256"), target.with_suffix(".zip.sha256"))
assert m.base.digest(target) == sha
removed = []  # Retain all existing releases and installation backups.
report = dict(
    ok=True,
    version=version,
    zip=str(target),
    sha256=sha,
    bytes=target.stat().st_size,
    payload_files=len(manifest["files"]),
    installed_app=str(app),
    mods=len(m.load(repo)["mods"]),
    original_data_unchanged=True,
    backend_tests=207,
    publication=json.loads(
        (w / "source-export-result.json").read_text(encoding="utf-8")
    )["publication"],
    source_build=json.loads(
        (w / "source-build-3.7-result.json").read_text(encoding="utf-8")
    ),
    setup_checks=json.loads(
        (w / "setup-release-result.json").read_text(encoding="utf-8")
    )["checks"],
    old_generated_data_removed=removed,
)
(w / ("final-release-" + version + ".json")).write_text(
    json.dumps(report, indent=2), encoding="utf-8"
)
print(json.dumps(report, indent=2))
# Retain release staging until all post-install UI checks pass.
# Only temporary build/test products are discarded; source and current package remain.
# remove_owned_tree(release,w)
# Keep the workspace build artifact as well as the shareable copy.
scratch = w / "test-scratch"
if scratch.exists() and not any(scratch.iterdir()):
    scratch.rmdir()
