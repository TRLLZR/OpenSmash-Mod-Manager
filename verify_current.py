"""Verify the retained current source, installed manager and active game integration."""

import json, sys, winreg
from pathlib import Path
from release_context import configured_repo, installed_app

w = Path(__file__).resolve().parent
sys.path.insert(0, str(w / "installer"))
import modmanager as m

r = configured_repo()
app = installed_app()
installation = json.loads((app / "install-state.json").read_text(encoding="utf-8"))
assert installation["version"] == "3.7.2"
with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\opensmashmm") as key:
    assert winreg.QueryValueEx(key, "URL Protocol")[0] == ""
    assert winreg.QueryValueEx(key, "OpenSmashOwner")[0] == "OpenSmash.Mods.Desktop"
with winreg.OpenKey(
    winreg.HKEY_CURRENT_USER, r"Software\Classes\opensmashmm\shell\open\command"
) as key:
    assert (
        winreg.QueryValueEx(key, "")[0]
        == f'"{app / "ModManager.exe"}" --gamebanana-link "%1"'
    )
for name, sha in installation["files"].items():
    assert m.base.digest(app / name) == sha, name
tools = json.loads((m.root(r) / "tools.json").read_text(encoding="utf-8"))
for name, sha in tools.items():
    assert (
        m.base.digest(w / "installer" / name)
        == m.base.digest(app / name)
        == m.base.digest(m.root(r) / "tools" / name)
        == sha
    ), name
m.profile_valid(r)
m.arc_backend.valid(r, True)
m.base.verify_managed(r / "drybowser_local")
state = m.load(r)
for key in state["mods"]:
    m.metadata(r, key)
profile = json.loads((m.root(r) / "profile/profile.json").read_text(encoding="utf-8"))
if profile.get("plugin_runtime"):
    import plugin_runtime

    plugin_runtime.valid(r, profile["plugin_runtime"])
archive = r.parent / "OpenSmash_Mod_Manager_Installer_v3.7.2.zip"
assert (
    m.base.digest(archive) == archive.with_suffix(".zip.sha256").read_text().split()[0]
)
result = dict(
    ok=True,
    version="3.7.2",
    mods=len(state["mods"]),
    active=sum(v["enabled"] for v in state["mods"].values()),
    app_files_verified=len(installation["files"]),
    game_integration_valid=True,
    own_url_handler=True,
    zip=str(archive),
)
print(json.dumps(result, indent=2))
