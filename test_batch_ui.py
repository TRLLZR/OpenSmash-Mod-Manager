"""Real UI/worker/filesystem batch lifecycle, synthetic game and ARC builder substitute."""

import json, shutil, subprocess, sys, zipfile, hashlib
from pathlib import Path

work = Path(__file__).resolve().parent
sys.path.insert(0, str(work / "installer"))
import test_modmanager as fixture

case = fixture.ManagerTests()
case.setUp()
m = fixture.m
try:
    src = Path(case.tmp.name) / "Application with spaces"
    src.mkdir()
    for name in {*m.TOOLS, "UiSupport.ps1"}:
        shutil.copy2(work / "installer" / name, src / name)
    controller = src / "modmanager.py"
    text = controller.read_text(encoding="utf-8")
    start = text.index("def idle():")
    end = text.index("\n\n", start)
    # This synthetic game has no executable process. Other real-game tests may
    # run concurrently; skip only the global process check in this owned copy.
    text = text[:start] + "def idle():\n    return None" + text[end:]
    controller.write_text(text, encoding="utf-8")
    # Replace only the ARC integration module in this owned test copy, never production.
    (src / "arc_backend.py").write_text("""from pathlib import Path
EXE='synthetic.exe';DLL='synthetic.dll';BIN='synthetic'
def location(repo):return repo/'build/work/modmanager_arc'
def ensure(repo):return {}
def valid(*args):return {}
def make_sd(repo,destination):
 (destination/'atmosphere').mkdir(parents=True)
 (destination/'ultimate/arcropolis/resources').mkdir(parents=True)
""")
    a = case.mod("Skin A", "ui/replace/a.bntx", "A")
    from PIL import Image

    Image.new("RGB", (600, 340), (35, 145, 195)).save(a / "preview.png")
    b = case.mod("Skin B", "ui/replace/b.bntx", "B")
    z = Path(case.tmp.name) / "Skin A.zip"
    with zipfile.ZipFile(z, "w") as archive:
        for p in a.rglob("*"):
            if p.is_file():
                archive.write(p, "Skin A/" + p.relative_to(a).as_posix())
    bad = Path(case.tmp.name) / "Broken.zip"
    bad.write_text("invalid ZIP")
    rar = Path(case.tmp.name) / "Skin B.rar"
    shutil.copy2(work / "installer/test_data/rar/ui-skin-b.rar", rar)
    seven = Path(case.tmp.name) / "Skin A.7z"
    subprocess.run(
        [str(work / "installer/7za.exe"), "a", "-t7z", str(seven), a.name],
        cwd=a.parent,
        check=True,
        capture_output=True,
    )
    sources = Path(case.tmp.name) / "sources.json"
    sources.write_text(json.dumps([str(z), str(rar), str(seven), str(a), str(bad)]))
    from PIL import Image

    for i, width in [(1, 1600), (2, 1200)]:
        url = f"https://images.gamebanana.com/img/ss/mods/own-qa-{i}.png"
        for folder in ("images", "full-images"):
            cache = case.repo / "opensmash_mods/network-cache" / folder
            cache.mkdir(parents=True, exist_ok=True)
            Image.new(
                "RGB",
                (min(width, 720) if folder == "images" else width, 700),
                (35, 120 + i * 30, 160),
            ).save(cache / (hashlib.sha256(url.encode()).hexdigest() + ".png"))
    report = work / "native-ui-3.7-result.json"
    Path(str(report) + ".settings.json").write_text(
        json.dumps(
            dict(
                app="OpenSmashModsPreferences-v1",
                install_dir=str(work / "installer"),
                theme="Light",
                library_view="List",
            )
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-STA",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(work / "BatchUiTest.ps1"),
            "-Source",
            str(src),
            "-Repo",
            str(case.repo),
            "-Sources",
            str(sources),
            "-Report",
            str(report),
        ],
        check=True,
        timeout=95,
    )
    assert m.load(case.repo)["mods"] == {}
finally:
    case.doCleanups()
