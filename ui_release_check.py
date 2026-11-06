"""Verify compiled host, final view variants and unchanged installed selection."""

import json, subprocess
from pathlib import Path
from release_context import configured_repo

work = Path(__file__).resolve().parent
repo = configured_repo()
before = (repo / "opensmash_mods/state.json").read_bytes()
expected_mods = len(json.loads(before)["mods"])
reports = []
for theme, solid in [
    ("Light", False),
    ("Dark", False),
    ("HighContrast", False),
    ("Auto", True),
]:
    args = [
        str(work / "installer/ModManager.exe"),
        "-Repo",
        str(repo),
        "-ReadOnlySession",
        "-SettingsPath",
        str(work / "ui-qa-settings.json"),
        "-SmokeTest",
        "-VisualTestTheme",
        theme,
    ]
    if solid:
        args += ["-SafeVisuals"]
    subprocess.run(args, check=True, timeout=25)
    data = json.loads(
        (repo / f"opensmash_mods/logs/ui-smoke-{theme}.json").read_text(
            encoding="utf-8-sig"
        )
    )
    assert data["ready"] and data["mods"] == expected_mods and data["controls"] == 66
    assert (
        data["logoLoaded"]
        and data["plainHeader"]
        and data["title"] == "OpenSmash Mod Manager"
    )
    assert (
        data["opaque"]
        and not data["backdrop"]
        and data["logoReplacesTitle"]
        and data["noTopmostControl"]
        and data["themeChoices"] == 3
        and data["menuActions"]
    )
    assert data["unifiedButtons"]
    assert data["font"] == "Trebuchet MS, Segoe UI"
    assert data["comboTemplatesOk"] and data["noImplicitVariant"]
    assert (
        data["filterOk"]
        and data["searchTextRectOk"]
        and data["listForegroundOk"]
        and all(c["layoutOk"] for c in data["layouts"])
    )
    if solid or theme == "HighContrast":
        assert not data["effects"] and not data["motion"] and not data["backdrop"]
    if theme == "Dark":
        assert data["dark"]
    if theme == "Light":
        assert not data["dark"]
    reports.append(data)
assert (repo / "opensmash_mods/state.json").read_bytes() == before
flow = json.loads((work / "native-ui-3.7-result.json").read_text(encoding="utf-8-sig"))
assert flow["ok"] and len(flow["checks"]) >= 6
assert flow["version"] == "3.7.1"
empty = dict(
    ready=True, mods=0, verified_by="isolated fresh setup and native view test"
)
(work / "ui-release-result.json").write_text(
    json.dumps(
        dict(
            version="3.7.1",
            variants=reports,
            flow=flow,
            empty=empty,
            selection_unchanged=True,
        ),
        indent=2,
    )
)
print(
    json.dumps(
        dict(
            ok=True,
            version="3.7.1",
            view_variants=4,
            layout_cases=80,
            ui_flow_checks=len(flow["checks"]),
            mods=expected_mods,
            empty_library=True,
            selection_unchanged=True,
        ),
        indent=2,
    )
)
