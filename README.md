<p align="center">
  <img src="installer/BrandLogo.png" alt="OpenSmash Mod Manager" width="600">
</p>

# OpenSmash Mod Manager

A native Windows mod manager for an **existing, working OpenSmash installation**.
Browse GameBanana, import ZIP/RAR/7z archives or folders, review conflicts, manage
your active mods, and launch the game from one application.

**Current version: 3.7.0 · Windows x64 · Original application code: MIT**

This project does **not** include the game, Nintendo assets, keys, firmware,
third-party mods, or compiled game/plugin binaries. It is an independent
community tool and is not affiliated with or endorsed by Nintendo, GameBanana,
OpenAI, or the developers of OpenSmash or the supported mod frameworks.

## Download and install

1. Open this repository's **Releases** section.
2. Download `OpenSmash_Mod_Manager_Installer_v3.7.0.zip` and extract the whole ZIP.
   GitHub's automatically generated **Source code** archives are for developers;
   they are not the installer.
3. Run `Setup.exe`. Setup installs for your Windows account without administrator
   rights. The private Python runtime and archive decoders are included.
4. Connect your existing OpenSmash folder. Keep the application and game in
   separate directories. You can also choose the game folder after installation.

The release provides a `.zip.sha256` file. In PowerShell, run
`Get-FileHash .\OpenSmash_Mod_Manager_Installer_v3.7.0.zip -Algorithm SHA256`
and compare the result with that file. A matching hash checks file integrity;
it does not establish who published the file. The current builds are unsigned.

### Requirements

- Windows 11 x64, or Windows 10 x64 version 2004+ on a supported servicing channel.
- Windows PowerShell 5.1 and .NET Framework 4.8 or later.
- An existing compatible OpenSmash **13.0.5** installation, your own game data,
  and sufficient free disk space for imported mods and backups.
- Internet for GameBanana and first-time framework/tool downloads.
- For local mod-loader/plugin builds: a complete supported OpenSmash build,
  LLVM/Clang, Microsoft C++ Build Tools and the Windows SDK. A standalone
  prebuilt game executable may not contain the required build inputs.

You do not need to install Python separately to use a release. The first loader
or plugin build can take several minutes. Setup explains missing prerequisites;
it does not download game data or bypass access restrictions.

## Main workflow

1. **Add mods:** drop ZIP, RAR, 7z archives or mod folders onto the library, or
   select them with **Files… / Folder…**. Multiple files and nested bundles are
   supported.
2. **Review:** inspect detected mods, duplicates and conflicts. Nothing is
   installed merely because it was dropped or downloaded.
3. **Install:** explicitly confirm the preview. Conflicts can be installed
   paused or replace conflicting active mods.
4. **Choose your setup:** enable/pause mods in the library, search, and switch
   between list and tile views. Covers come from local images or recorded
   GameBanana origins; unknown artwork is not guessed from titles.
5. **Play:** use **Play with mods** or **Play vanilla**. **Undo** restores the
   previous managed change. Changes apply at the next game launch.

Updates keep the mod library, activation, profiles, preferences, saves and game
configuration. Existing DLC, online and volume settings remain the game's own
settings. Back up valuable data before making changes to your mod setup.

## Discover and download

**Discover** browses the public GameBanana catalog with categories, skin character
filters, update checks and full-screen screenshots. Choose a file variant
explicitly. Search is separate from category browsing because the provider's
search API does not apply category filters.

**Downloads** is a persistent queue. Completed supported archives need a separate
installation confirmation. You can remove individual finished jobs or choose
**Clear all downloads…** to cancel active transfers and remove current entries
and cached archives. Installed mods are preserved. Other public formats appear
as **Download only** and can be saved explicitly; they are never executed or
automatically installed. Restricted, unavailable or unsafe provider files stay
blocked.

`opensmashmm:` is this application's own link protocol. The MOSAIC/FightPlanner
protocol belongs to a different manager and is not registered or replaced here.
A dedicated GameBanana website button for this manager has **not** been published.

## Share a mod list without sending mod files

Use **More > Share mod list…** to create a small `*.opensmash-list.json` file.
Another user imports or drops that list into the manager, reviews it, and confirms
**Install missing mods**. The manager downloads the recorded provider files and
installs only missing requested content. Existing activation is preserved; new
conflicts install paused. Several requested members of one archive share a download.

These lists contain content fingerprints and recorded GameBanana file IDs, not
mod assets, saves or arbitrary download URLs. They cannot reproduce unpublished
local edits or download mods whose original source was never recorded. Removed
or changed provider versions are reported rather than silently substituted.
An asset ZIP export is also available; only share assets you have rights to share.

## Compatibility and limits

- Support follows the **structure and type** of a mod, not its name. Common
  ARCropolis assets, skins, sounds, UI, effects, configurations and compatible
  Skyline NRO plugins use the existing OpenSmash integration.
- Successful import means the files passed structural checks. It is **not** a
  guarantee of in-game, online or arbitrary gameplay-plugin compatibility.
- Gameplay and additional-character mods may require compatible frameworks,
  supported lifter instructions and hooks. Native `fighter.json`/Windows DLL
  packages are outside the supported import formats. Downloaded author scripts
  and executables are not run as part of import.
- CSK-dependent gameplay remains limited: the public CSK 5.0.6 targets Smash
  13.0.4 and is blocked for 13.0.5 after a failed isolated compatibility probe.
  The author documents CSK 6.0.0 for 13.0.5; it was not available in the official
  public file listing at the last compatibility review. Do not substitute the old
  package. See [known limitations](installer/BEKANNTE_EINSCHRAENKUNGEN.md).
- Maximum import batch: 1,024 mods, 64,000 archive entries and 8 GiB expanded
  content; up to two nested archive levels. Public downloads are limited to
  2 GiB per file with two simultaneous transfers. Password-protected and
  multi-volume archives must be handled separately. Decoder resource limits
  can also reject unusually large archives.

## Language and accessibility

The application follows the Windows **display language** automatically. The core
workflow supports German, English, Spanish, French, Italian, Portuguese, Dutch,
Polish, Turkish, Russian, Ukrainian, Japanese, Korean, simplified/traditional
Chinese, and Arabic. Arabic uses right-to-left layout. Unknown languages fall
back to English. Supplementary explanations may use English; some older backend
diagnostics remain German. Mod descriptions and author content remain unchanged.

Light, dark and system themes, opaque surfaces, high contrast, text scaling,
keyboard navigation and reduced animation are supported. Translation happens
locally; no text is sent to a translation service.

## Development

The stack is **C#/.NET Framework**, **Windows PowerShell/WPF** and a bundled
**CPython** backend. There is no Electron, WebView or Node.js runtime.

From the repository root, using a separate trusted Python 3.14+ on Windows x64:

```powershell
python prepare_runtime.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File installer/BuildLauncher.ps1
installer/runtime/python.exe -B -m unittest discover -s installer -p 'test_*.py'
installer/runtime/python.exe -B build_release.py
```

The preparation script downloads SHA-256-pinned official runtime artifacts; the
portable archive decoders and their notices are already included. Build output
is `release-3.7.0/Setup.exe` and the versioned installer ZIP. No game is needed
to run the synthetic backend suite. Native visual and real-game integration
checks are separate, require an appropriate local environment, and are not
claimed to run in the hosted CI job.

Read the [developer guide](installer/README.md),
[contribution guide](CONTRIBUTING.md), [security notes](SECURITY.md), and
[release checklist](docs/RELEASING.md). The workflow in `.github/workflows/validate.yml`
checks publication hygiene, builds the host, and runs the synthetic backend suite
on Windows. It does not publish releases or access a real mod library.

## Licenses and artwork

The original application source is MIT licensed; see [LICENSE.txt](LICENSE.txt).
Third-party components keep their own licenses, including the freeware UnRAR DLL
and LGPL/BSD 7-Zip executable. **The entire download is not solely MIT licensed.**
Keep [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt) and all supplied license
files. The matching unmodified 7-Zip source is included at
`third_party/7zip/7z2605-src.tar.xz`; publish the manager source ZIP alongside each
installer release so recipients have corresponding source from the same place.

The new wordmark and icon were supplied as ChatGPT-generated artwork and prepared
as separate transparent assets. See [BRANDING.md](BRANDING.md) for provenance and
scope. AI generation and this code review do not establish trademark clearance
or guarantee that no third-party rights apply. The
[publication review](docs/LEGAL_REVIEW.md) records what was checked and its limits.

## Help and contributions

Use this repository's Issues for reproducible bugs or focused feature requests.
Include the manager version, Windows version, mod type and a short reproduction.
Redact personal paths and identifiers from logs. Do not upload game files, keys,
saves, private mod collections or third-party assets without permission. This
project does not provide those files or advice for obtaining unauthorized copies.
