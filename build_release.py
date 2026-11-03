"""Build the v3.7 installer from an explicit application allowlist and verified runtime."""

import hashlib, json, subprocess, zipfile, os
from pathlib import Path

work = Path(__file__).resolve().parent
src = work / "installer"
out = work / "release-3.7.0"
out.mkdir(exist_ok=True)
compiler = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
manifest = src / "Setup.manifest"
manifest.write_text(
    (src / "ModManager.manifest")
    .read_text()
    .replace("OpenSmash.ModManager", "OpenSmash.Mods.Setup"),
    encoding="utf-8",
)
common = [
    str(compiler),
    "/nologo",
    "/target:winexe",
    "/platform:x64",
    "/optimize+",
    "/debug-",
    f"/win32manifest:{manifest}",
    f'/win32icon:{src / "BrandIcon.ico"}',
    "/reference:System.Windows.Forms.dll",
    "/reference:System.Drawing.dll",
    "/reference:System.Web.Extensions.dll",
    "/reference:System.IO.Compression.dll",
    "/reference:System.Core.dll",
    "/reference:Microsoft.CSharp.dll",
]
subprocess.run(
    [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(src / "BuildLauncher.ps1"),
    ],
    check=True,
)
subprocess.run(
    [
        *common,
        "/define:UNINSTALL",
        f'/out:{src / "Uninstall.exe"}',
        str(src / "Setup.cs"),
        str(src / "Localization.cs"),
        str(src / "AeroButton.cs"),
        f'/resource:{src / "locales.json"},OpenSmash.Locales.json',
    ],
    check=True,
)
names = [
    "Localization.ps1",
    "locales.json",
    "README.md",
    "BRANDING.md",
    "LEGAL_REVIEW.md",
    "SECURITY.md",
    "BrandLogo.png",
    "BrandIcon.png",
    "BRAND_ASSETS.json",
    "BrandIcon.ico",
    "ModManager.exe",
    "ModManager.ps1",
    "ModManager.xaml",
    "UiSupport.ps1",
    "modmanager.py",
    "batch_import.py",
    "catalog.py",
    "deployment.py",
    "runtime_cache.py",
    "playback.py",
    "gamebanana.py",
    "manager_links.py",
    "ImageViewer.ps1",
    "downloads.py",
    "network.py",
    "Discover.ps1",
    "Discover.xaml",
    "Downloads.xaml",
    "setup_checks.py",
    "Theme.ps1",
    "library_export.py",
    "mod_lists.py",
    "ModLists.ps1",
    "plugin_runtime.py",
    "plugin_dependencies.py",
    "library_media.py",
    "LibraryView.ps1",
    "LibraryViews.xaml",
    "rar_support.py",
    "sevenzip_support.py",
    "7za.exe",
    "7ZIP_LICENSE.txt",
    "7ZIP_LGPL.txt",
    "7ZIP_DISTRIBUTION.json",
    "UnRAR64.dll",
    "UNRAR_LICENSE.txt",
    "UNRAR_DISTRIBUTION.json",
    "drybowser.py",
    "arc_backend.py",
    "arc_import.py",
    "arc_simd.py",
    "arc_fs_support.h",
    "Install.ps1",
    "Install.bat",
    "Start.ps1",
    "Mods verwalten.bat",
    "Mod installieren.bat",
    "Uninstall.bat",
    "Uninstall.exe",
    "ANLEITUNG.txt",
    "README_DE.md",
    "MODMANAGER_DE.md",
    "ABHAENGIGKEITEN.md",
    "BEKANNTE_EINSCHRAENKUNGEN.md",
    "CHANGELOG_DE.md",
    "DESIGN_DE.md",
    "LICENSE.txt",
    "THIRD_PARTY_NOTICES.txt",
]
files = {name: src / name for name in names}
for p in sorted((src / "runtime").rglob("*")):
    if (
        p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix not in (".pyc", ".pyo")
    ):
        files[p.relative_to(src).as_posix()] = p
assert len(files) > 100 and all(p.is_file() for p in files.values())
sums = {n: hashlib.sha256(p.read_bytes()).hexdigest() for n, p in files.items()}
for n in names:
    if files[n].suffix in (".ps1", ".py", ".xaml", ".md", ".txt", ".bat"):
        data = files[n].read_bytes()
        if (
            n.endswith(".ps1")
            and any(b >= 128 for b in data)
            and not data.startswith(b"\xef\xbb\xbf")
        ):
            raise ValueError("PowerShell BOM required: " + n)
        decoded = data.decode("utf-8-sig")
        if any(
            token in decoded
            for token in (
                "\u00c3\u00a4",
                "\u00c3\u00bc",
                "\u00c3\u00b6",
                "\u00e2\u20ac",
                "\u00c2\u00b7",
                "\u00c3\u0192",
            )
        ):
            raise ValueError("Text encoding corruption in " + n)
        if any(
            token in data
            for token in (
                os.environ.get("USERNAME", "__unset_user__").encode("utf-8"),
                b"D:\\Games\\",
                b"D:\\Downloads\\",
            )
        ):
            raise ValueError("Private path in " + n)
payload = out / "Payload.zip"
with zipfile.ZipFile(payload, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for n, p in files.items():
        z.write(p, n)
    z.writestr(
        "PAYLOAD.json",
        json.dumps(
            dict(app="OpenSmash.Mods.Desktop", version="3.7.0", files=sums), indent=2
        ),
    )
with zipfile.ZipFile(payload) as z:
    assert z.testzip() is None
subprocess.run(
    [
        *common,
        f"/resource:{payload},OpenSmash.Payload.zip",
        f'/out:{out / "Setup.exe"}',
        str(src / "Setup.cs"),
        str(src / "Localization.cs"),
        str(src / "AeroButton.cs"),
        f'/resource:{src / "locales.json"},OpenSmash.Locales.json',
    ],
    check=True,
)
for name in (
    "ANLEITUNG.txt",
    "README.md",
    "SECURITY.md",
    "BRANDING.md",
    "LEGAL_REVIEW.md",
    "THIRD_PARTY_NOTICES.txt",
    "LICENSE.txt",
):
    (out / name).write_bytes((src / name).read_bytes())
release_files = [
    "Setup.exe",
    "ANLEITUNG.txt",
    "README.md",
    "SECURITY.md",
    "BRANDING.md",
    "LEGAL_REVIEW.md",
    "THIRD_PARTY_NOTICES.txt",
    "LICENSE.txt",
]
(out / "SHA256SUMS.txt").write_text(
    "".join(
        hashlib.sha256((out / n).read_bytes()).hexdigest() + "  " + n + "\n"
        for n in release_files
    ),
    encoding="ascii",
)
target = work / "OpenSmash_Mod_Manager_Installer_v3.7.0.zip"
with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for n in release_files + ["SHA256SUMS.txt"]:
        z.write(out / n, "OpenSmash_Mod_Manager_Installer_v3.7.0/" + n)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
sha = hashlib.sha256(target.read_bytes()).hexdigest()
target.with_suffix(".zip.sha256").write_text(
    sha + "  " + target.name + "\n", encoding="ascii"
)
print(
    json.dumps(
        dict(
            zip=str(target),
            sha256=sha,
            bytes=target.stat().st_size,
            payload_files=len(files),
        ),
        indent=2,
    )
)
