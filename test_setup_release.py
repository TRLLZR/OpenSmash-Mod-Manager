"""Exercise setup against an isolated app root and namespaced HKCU test registration."""

import hashlib, json, os, shutil, subprocess, sys, tempfile, winreg
from pathlib import Path

work = Path(__file__).resolve().parent
sys.path.insert(0, str(work / "installer"))
import test_modmanager as fixture

case = fixture.ManagerTests()
case.setUp()
m = fixture.m
repo = case.repo
test = Path(tempfile.mkdtemp(prefix="Setup lifecycle ", dir=work / "test-scratch"))
(test / "installer-test.json").write_text(
    json.dumps(dict(app="OpenSmash.Mods.Desktop"))
)
app = test / "App with spaces"
setup = work / "release-3.7.1/Setup.exe"
checks = []
reg = (
    "Software\\OpenSmashModsInstallerTests\\"
    + hashlib.sha256(str(test).encode()).hexdigest()[:16]
)
protocol = reg + "\\Protocols\\opensmashmm"


def protocol_snapshot(path):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            values = {
                winreg.EnumValue(key, i)[0]: winreg.EnumValue(key, i)[1:]
                for i in range(winreg.QueryInfoKey(key)[1])
            }
            children = {
                winreg.EnumKey(key, i): protocol_snapshot(
                    path + "\\" + winreg.EnumKey(key, i)
                )
                for i in range(winreg.QueryInfoKey(key)[0])
            }
            return values, children
    except FileNotFoundError:
        return None


foreign_before = protocol_snapshot(r"Software\Classes\fightplanner")


def check_protocol():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, protocol) as key:
        assert winreg.QueryValueEx(key, "URL Protocol")[0] == ""
        assert winreg.QueryValueEx(key, "OpenSmashOwner")[0] == "OpenSmash.Mods.Desktop"
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, protocol + "\\shell\\open\\command"
    ) as key:
        assert (
            winreg.QueryValueEx(key, "")[0]
            == f'"{app / "ModManager.exe"}" --gamebanana-link "%1"'
        )
    assert protocol_snapshot(r"Software\Classes\fightplanner") == foreign_before


def run(*args, ok=True):
    result = subprocess.run(
        [str(setup), *args, "--dir", str(app), "--test-root", str(test), "--quiet"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=65,
    )
    assert (result.returncode == 0) == ok, (
        result.returncode,
        result.stdout,
        result.stderr,
        args,
    )
    return result


def stage_update():
    """Feed the real updater an offline GitHub response and the built release ZIP."""
    release = work / "OpenSmash_Mod_Manager_Installer_v3.7.1.zip"
    metadata = test / "latest-release.json"
    metadata.write_text(json.dumps(dict(tag_name="v3.7.1", draft=False, prerelease=False, assets=[
        dict(name=release.name, state="uploaded", size=release.stat().st_size,
             digest="sha256:" + hashlib.sha256(release.read_bytes()).hexdigest(),
             browser_download_url="https://github.com/TRLLZR/OpenSmash-Mod-Manager/releases/download/v3.7.1/" + release.name)
    ])), encoding="utf-8")
    src = work / "installer"
    tester = test / "StageUpdate.exe"
    compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    subprocess.run([
        str(compiler), "/nologo", f"/out:{tester}",
        "/reference:System.Windows.Forms.dll", "/reference:System.Drawing.dll",
        "/reference:System.Web.Extensions.dll", "/reference:System.IO.Compression.dll",
        "/reference:System.IO.Compression.FileSystem.dll",
        str(src / "StartupUpdate.cs"), str(src / "test_data/update/StageUpdate.cs"),
    ], check=True, timeout=30)
    staged = test / "Downloaded Setup.exe"
    subprocess.run([str(tester), str(metadata), str(release), str(staged)], check=True, timeout=30)
    return staged


def snapshot():
    return {
        str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
        for name in ("opensmash_mods/state.json", "build/saves", "Play SSBU.bat")
        for p in (
            [repo / name] if (repo / name).is_file() else (repo / name).rglob("*")
        )
        if p.is_file()
    }


def shortcut(file, seed=False):
    script = """[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$link=(New-Object -ComObject WScript.Shell).CreateShortcut($env:OPENSMASH_TEST_LINK)
if($env:OPENSMASH_TEST_SEED -eq '1'){$link.Arguments='-Repo "C:\\OldGame"';$link.IconLocation='shell32.dll,0';$link.Save()}
@{target=$link.TargetPath;icon=$link.IconLocation;working=$link.WorkingDirectory;arguments=$link.Arguments}|ConvertTo-Json -Compress"""
    p = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ],
        env=dict(
            os.environ,
            OPENSMASH_TEST_LINK=str(file),
            OPENSMASH_TEST_SEED="1" if seed else "0",
        ),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        timeout=15,
    )
    return json.loads(p.stdout)


def check_links():
    for folder in ("Start Menu", "Desktop"):
        link = shortcut(test / folder / "OpenSmash Mod Manager.lnk")
        assert (
            Path(link["target"]) == app / "ModManager.exe"
            and Path(link["working"]) == app
        )
        assert (
            link["icon"].endswith(",0")
            and Path(link["icon"].rsplit(",", 1)[0]) == app / "BrandIcon.ico"
        )
        assert link["arguments"] == "", link


def check_packaged_launch_paths():
    private = repo / "build/work/modmanager_plugins/0123456789abcdef0123"
    private.mkdir(parents=True, exist_ok=True)
    (private / "ssbu_modmanager.exe").write_text("QA private executable")
    profile = m.root(repo) / "profile/profile.json"
    old = profile.read_bytes()
    value = json.loads(old)
    value.update(
        backend="arcropolis",
        plugin_runtime=dict(
            exe="modmanager_plugins/0123456789abcdef0123/ssbu_modmanager.exe",
            plugin_bin="plugin_bin",
            nro_bin="../../nro_bin_eh_o2",
        ),
    )
    profile.write_text(json.dumps(value), encoding="utf-8")
    code = """import os,sys,json
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,os.getcwd())
import modmanager as m,runtime_cache
m.idle=lambda:None
m.arc_backend.valid=lambda *args,**kwargs:{}
# This fixture checks packaged launch routing with an owned synthetic EXE.
# Runtime compatibility is exercised by the separate backend/build tests.
runtime_cache.plugin=lambda *args,**kwargs:{}
seen=[]
def launch(args,**kwargs):seen.append(args);return SimpleNamespace(pid=1)
m.subprocess.Popen=launch
m.play(Path(os.environ['OPENSMASH_TEST_REPO']))
print(json.dumps(seen[0]))"""
    try:
        result = subprocess.run(
            [str(app / "runtime/python.exe"), "-B", "-c", code],
            cwd=app,
            env=dict(os.environ, OPENSMASH_TEST_REPO=str(repo)),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=True,
            timeout=15,
        )
        args = json.loads(result.stdout)
        env = dict(
            args[i + 1].split("=", 1) for i, v in enumerate(args) if v == "--env"
        )
        for key, name in [
            ("SSBU_GRAPHICS_CONFIG", "graphics.ini"),
            ("SSBU_CONFIG", "controllers.ini"),
            ("SSBU_DLC_LIST", "dlc.txt"),
        ]:
            assert env[key] == str(repo / "build/config" / name)
        assert (
            args[args.index("--userdata") + 1] == str(repo / "build/saves")
            and "modmanager_plugins/" in args[args.index("--exe") + 1]
        )
        assert "SSBU_VOLUME" not in env and "SSBU_ONLINE" not in env
    finally:
        profile.write_bytes(old)


try:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, protocol) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Foreign protocol")
    run("--install", ok=False)
    assert (
        not app.exists() and protocol_snapshot(protocol)[0][""][0] == "Foreign protocol"
    )
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, protocol)
    checks += ["foreign opensmashmm association rejected before app mutation"]
    # Genuine previous-release -> new-release upgrade in isolated registration.
    import zipfile

    previous_package = Path(os.environ["OPENSMASH_PREVIOUS_INSTALLER"])
    with zipfile.ZipFile(previous_package) as archive:
        old_setup = test / "Previous Setup.exe"
        old_setup.write_bytes(
            archive.read("OpenSmash_Mod_Manager_Installer_v3.7.0/Setup.exe")
        )
    new_setup = setup
    setup = old_setup
    run("--install")
    setup = new_setup
    assert json.loads((app / "install-state.json").read_text())["version"] == "3.7.0"
    prefs = json.loads((test / "settings.json").read_text())
    prefs.update(glass="Frosted", theme="Dark", repo=str(repo))
    (test / "settings.json").write_text(json.dumps(prefs))
    old_snapshot = snapshot()
    setup = stage_update()
    run("--install", "--update", "--wait-pid", "2147483647", "--expected-version", "3.7.1")
    setup = new_setup
    assert snapshot() == old_snapshot
    assert json.loads((app / "install-state.json").read_text())["version"] == "3.7.1"
    check_protocol()
    assert json.loads((test / "settings.json").read_text())["theme"] == "Dark"
    check_links()
    checks += [
        "verified release ZIP upgrades 3.7.0 to 3.7.1 and preserves game data, preferences and shortcuts"
    ]
    installed = (app / "install-state.json").read_bytes()
    run("--install", "--update", "--wait-pid", "2147483647", "--expected-version", "3.7.1", ok=False)
    assert (app / "install-state.json").read_bytes() == installed
    checks += ["automatic reinstall of the same version is rejected"]
    run("--uninstall")
    run("--install", "--no-desktop")
    assert not (test / "Desktop/OpenSmash Mod Manager.lnk").exists()
    run("--uninstall")
    checks += ["desktop opt-out works on a fresh installation"]
    run("--install")
    assert (app / "ModManager.exe").is_file() and (app / "runtime/python.exe").is_file()
    assert (test / "Start Menu/OpenSmash Mod Manager.lnk").is_file() and (
        test / "Desktop/OpenSmash Mod Manager.lnk"
    ).is_file()
    check_links()
    checks += [
        "default fresh install creates both shortcuts with logo, correct target and no fixed game arguments"
    ]
    result = subprocess.run(
        [
            str(app / "runtime/python.exe"),
            "-B",
            str(app / "modmanager.py"),
            "--repo",
            str(repo),
            "inspect",
            "--source",
            str(work / "installer/test_data/rar/rar5-compressed.rar"),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    assert json.loads(result.stdout)["result"]["count"] == 1
    checks += ["installed private runtime decodes RAR without external WinRAR"]
    own_seven = test / "Own 7z import"
    (own_seven / "ui/replace").mkdir(parents=True)
    (own_seven / "ui/replace/own.bntx").write_bytes(b"Own installed decoder fixture")
    seven_archive = test / "Own.7z"
    subprocess.run(
        [
            str(work / "installer/7za.exe"),
            "a",
            "-t7z",
            str(seven_archive),
            own_seven.name,
        ],
        cwd=test,
        check=True,
        capture_output=True,
    )
    seven_result = subprocess.run(
        [
            str(app / "runtime/python.exe"),
            "-B",
            str(app / "modmanager.py"),
            "--repo",
            str(repo),
            "inspect",
            "--source",
            str(seven_archive),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        timeout=20,
    )
    assert json.loads(seven_result.stdout)["result"]["count"] == 1
    checks += ["installed private runtime decodes 7z without system 7-Zip"]
    check_packaged_launch_paths()
    checks += [
        "packaged plugin launch retains original graphics, controller, DLC and save paths without forced volume or offline mode"
    ]
    prefs = json.loads((test / "settings.json").read_text())
    prefs.update(glass="Frosted", theme="Dark", repo=str(repo))
    (test / "settings.json").write_text(json.dumps(prefs))
    source = case.mod()
    m.install(repo, source)
    key = next(iter(m.load(repo)["mods"]))
    m.change(repo, key, "enable", False)
    shortcut(test / "Desktop/OpenSmash Mod Manager.lnk", seed=True)
    for folder in ("Start Menu", "Desktop"):
        (test / folder / "OpenSmash Mod Manager.lnk").rename(
            test / folder / "OpenSmash Mods.lnk"
        )
    before = snapshot()
    run("--install", "--repo", str(repo))
    assert snapshot() == before
    assert all(
        (test / f / "OpenSmash Mod Manager.lnk").exists()
        and not (test / f / "OpenSmash Mods.lnk").exists()
        for f in ("Start Menu", "Desktop")
    )
    check_links()
    check_protocol()
    checks += [
        "upgrade refreshes own shortcut logo and removes stale game-path arguments"
    ]
    prefs = json.loads((test / "settings.json").read_text())
    assert (
        prefs["glass"] == "Frosted"
        and prefs["theme"] == "Dark"
        and prefs["repo"] == str(repo)
    )
    assert list(test.glob("App with spaces.backup-*"))
    checks += [
        "upgrade preserves paused mod, saves, starter and appearance; backup retained"
    ]
    installed = (app / "install-state.json").read_bytes()
    run("--install", "--repo", str(test / "Not a game"), ok=False)
    assert (
        app / "install-state.json"
    ).read_bytes() == installed and snapshot() == before
    assert not list(test.glob("*.staging-*"))
    checks += ["invalid game rolls back without staging remnants"]
    result = subprocess.run(
        [
            str(app / "runtime/python.exe"),
            "-B",
            str(app / "modmanager.py"),
            "--repo",
            str(repo),
            "check",
        ],
        capture_output=True,
        encoding="utf-8",
        check=True,
    )
    data = json.loads(result.stdout)["result"]
    assert data["manager_ready"] and not data["skin_ready"] and data["warnings"]
    checks += ["missing local skin-build dependencies give guidance"]
    foreign = test / "Foreign folder"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("keep")
    old = app
    app = foreign
    run("--install", ok=False)
    assert (foreign / "keep.txt").read_text() == "keep"
    app = old
    checks += ["foreign nonempty directory rejected"]
    reg = (
        "Software\\OpenSmashModsInstallerTests\\"
        + hashlib.sha256(str(test).encode()).hexdigest()[:16]
    )
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg) as k:
        assert winreg.QueryValueEx(k, "DisplayVersion")[0] == "3.7.1"
        assert winreg.QueryValueEx(k, "DisplayName")[0] == "OpenSmash Mod Manager"
        uninstall = winreg.QueryValueEx(k, "UninstallString")[0]
        assert "--test-root" in uninstall and str(app) in uninstall
    run("--uninstall")
    assert (
        not app.exists() and (test / "settings.json").exists() and snapshot() == before
    )
    assert (
        protocol_snapshot(protocol) is None
        and protocol_snapshot(r"Software\Classes\fightplanner") == foreign_before
    )
    checks += [
        "own quoted URL handler installed, upgraded and removed without changing MOSAIC association"
    ]
    assert (
        not (test / "Start Menu/OpenSmash Mod Manager.lnk").exists()
        and not (test / "Desktop/OpenSmash Mod Manager.lnk").exists()
    )
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg)
        raise AssertionError("Registration remained")
    except FileNotFoundError:
        pass
    checks += [
        "registered uninstall removes own app and shortcuts, preserves settings and game data"
    ]
    run("--install")
    assert json.loads((test / "settings.json").read_text())["glass"] == "Frosted"
    assert snapshot() == before
    (app / "My file.txt").write_text("preserve")
    (app / "README.md").write_text("manually edited")
    run("--uninstall")
    assert (app / "My file.txt").read_text() == "preserve" and (
        app / "README.md"
    ).read_text() == "manually edited"
    assert not (app / "ModManager.exe").exists()
    checks += [
        "reinstall preserves preferences; uninstall preserves foreign/changed files"
    ]
    report = dict(ok=True, checks=checks, test_root=str(test), game_unchanged=True)
    (work / "setup-release-result.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
finally:
    case.doCleanups()
    if "report" in globals() and report.get("ok"):
        assert (
            test.resolve().is_relative_to((work / "test-scratch").resolve())
            and (test / "installer-test.json").is_file()
        )
        shutil.rmtree(test)
