# OpenSmash Mod Manager

A native Windows desktop manager for an existing OpenSmash installation. Import
ZIP/RAR/7z archives or folders, review conflicts, choose active mods, and start the
game. GameBanana browsing and downloads are built in. Downloading a mod never
installs it automatically.

This repository contains the manager, not the game, Nintendo data, keys, firmware,
or third-party mod assets. Original manager code is MIT licensed. The supplied
wordmark and third-party components retain their separate rights; see
`LICENSE.txt` and `THIRD_PARTY_NOTICES.txt`.

## Using the manager

1. Extract a release and run `Setup.exe`. Installation is per user.
2. Select your configured OpenSmash folder, or connect it when first opening the
   manager. Keep the application and game in separate folders.
3. Drop mod archives/folders onto **Add mods**, or find a mod in **Discover** and
   explicitly choose a file to download.
4. Review the import list. Conflicting mods are not silently overwritten. Choose
   whether to install paused or replace conflicting active mods, then install.
5. Check mods to enable them. Selection changes apply on the next game launch.
   **Undo** restores the previous selection. **Play vanilla** starts without the
   manager's active mod profile.

Export, full verification, update checks, logs and manager links live in **More**.
Screenshots open full screen; use Left/Right and Escape. Imported mods are
classified by structure, not by title. A valid structure does not guarantee a mod
will work in the game. Plugin translation and first-time loader builds may take
several minutes and require the game's supported C++ toolchain.

The library offers **List / Tiles**, with one shared search, selection and
activation model. The chosen view is remembered. Covers come from local
`preview.png`, `thumbnail.png`, `cover.png` (also JPG/WebP) or the recorded
GameBanana origin. **More > Choose cover…** sets a custom image. Unknown origins
use a neutral placeholder. Artwork is never guessed from a mod's title.

**Downloads > Remove download** deletes selected finished/failed/cancelled jobs
and their cached archives. Cancel active transfers first. Installed mods and
prepared import snapshots remain available.

**Clear all downloads…** cancels current transfers and removes all current jobs
and cached archives after confirmation. Transfer workers close their files before
removing them. Installed mods and prepared import snapshots are preserved. Jobs
queued afterwards are outside this clear request. Provider-public files in other
formats can be downloaded as **Download only**, then exported using **Save file…**;
they are never executed or automatically installed. Provider access/AV restrictions
still apply. Opening another Discover item resets its detail scroll position.

Keyboard: Ctrl+O archives, Ctrl+Shift+O folder, Ctrl+F search, Ctrl+I install,
Ctrl+Z undo, Ctrl+R verify, Ctrl+L logs, F5 play with mods, F6 play vanilla.

## Language and accessibility

The manager and setup use the Windows **display language** (`CurrentUICulture`),
not the regional date/number setting. Language families: German, English,
Spanish, French, Italian, Portuguese, Dutch, Polish, Turkish, Russian, Ukrainian,
Japanese, Korean, simplified Chinese, traditional Chinese and Arabic. Regional
variants fall back to their language family; unknown languages fall back to
English. Arabic uses right-to-left window layout.

The primary workflow is translated in these families. The current catalog has
English fallbacks for supplementary explanations and technical diagnostics;
some legacy backend diagnostics remain German. Mod names, author descriptions,
character names, file paths, and upstream errors remain in their original language.
This is not a claim of complete translation or native-speaker review of every
message. Contributions to extend translation coverage are welcome.

Language files are local. The application never sends text to a translation
service. Developers can set `OPENSMASH_UI_LANGUAGE` to test a display language
without changing Windows. There is no extra language-selection step for users.

Windows high contrast, text scaling, reduced animation, native keyboard access,
hover/pressed feedback and visible focus are supported. Existing light/dark/system
preferences survive upgrades. New preferences follow Windows by default.

## Sharing a download list

Use **More > Share mod list…** to export `*.opensmash-list.json`. The recipient
uses **Import mod list…** or drops the file into the library, reviews the summary
and confirms **Install missing mods**. This explicit action downloads and installs
the missing items. Ordinary GameBanana links/downloads still need their separate
installation confirmation.

Existing content is detected by a SHA-256 fingerprint of effective paths/module
names and file hashes; current activation is preserved. New conflicts install
paused. Bundled files download once, and only requested members are installed.
Failed or removed provider versions are reported without substituting a newer
file. Manual-source mods are listed with an explanation and need the original
files. Download lists reproduce recorded original downloads, not unpublished
local edits; use the asset ZIP export when those files must be transferred.

The version-1 schema uses `app: OpenSmash-ModList-v1`, `version: 1`, and `mods`.
Each entry contains `name`, a 64-character `signature`, a boolean `enabled` and
either `source: null` or a GameBanana source with `provider`, `model` (Mod/Sound),
positive integer `submission_id`/`file_id` and a 64-character archive `sha256`.
No arbitrary URLs or local paths are accepted. Limits: 2 MiB JSON, 1024 unique
content identities. A review token detects changes before installation. Archives
still use the ordinary bounded, hash-checked download/import pipeline; imported
metadata never grants filesystem or execution authority.

`mod_lists.py` owns recipes and orchestration; `ModLists.ps1` adds the existing
file-dialog/review workflow. `DownloadRow` keeps WPF row identity stable and raises
property notifications only for changes. Polling uses 1 s during transfers and
5 s while idle. Asset-only commits reuse verified unchanged plugin inputs;
framework flags invalidate that reuse. Known incompatible supplied NRO hashes
fail in preview before compilation, avoiding a repeated known-incompatible build.

## Architecture (implementation)

| Layer | Files | Responsibility |
| --- | --- | --- |
| C# / .NET Framework | `ModManagerLauncher.cs` | GUI host, WPF runspace, DPI, observable rows, user-scoped link IPC |
| PowerShell 5.1 / WPF | `ModManager.ps1`, `UiSupport.ps1`, `Theme.ps1`, XAML | Presentation, file dialogs, async worker results, shared button tokens |
| Discovery | `Discover.ps1`, `ImageViewer.ps1`, `network.py`, `gamebanana.py` | Public API, filters, validated image cache, full-screen viewing |
| Downloads | `downloads.py`, `Downloads.xaml` | Persistent two-transfer queue, integrity checks, explicit import handoff |
| Import | `modmanager.py`, `batch_import.py`, `rar_support.py`, `sevenzip_support.py`, `arc_import.py` | Archive limits, structure classification, snapshots, conflict decisions |
| Deployment | `catalog.py`, `deployment.py`, `runtime_cache.py` | Hash/stat index, transactional profile switching, recovery and undo |
| Library views | `LibraryView.ps1`, `LibraryViews.xaml`, `library_media.py` | Shared list/tile bindings and bounded optional cover cache outside mod identity |
| Game integration | `arc_backend.py`, `arc_simd.py`, `arc_fs_support.h`, `plugin_runtime.py`, `playback.py` | Existing compatible loader/toolchain integration and original game settings |
| Installation | `Setup.cs`, `AeroButton.cs` | Staged per-user install, rollback, owned-file uninstall, own protocol |
| Localization | `Localization.cs`, `Localization.ps1`, `locales.json` | Embedded setup/launcher vocabulary, translated UI, invariant protocol values |

Python workers return newline-delimited JSON over redirected UTF-8 pipes. UI and
network workers do not share the deployment busy lane. Translations are applied
only to presentation text, never to operation keys or mod identities. The browser
renders provider HTML as plain text and converts images locally before WPF sees
them. There is no Electron, Node.js runtime, browser/WebView or cloud account.

Skin character filtering uses actual subcategories. Free-text search is separate
because the upstream search API does not apply those category filters.

`plugin_dependencies.py` resolves a small explicit registry of shared frameworks
from NRO library references and extended effect-slot paths. It never uses mod
titles or executes author tools from dependency archives. Artifacts are pinned
by SHA-256, extracted members are explicit, and known game-version mismatches
fail before compilation. A supplied framework NRO follows the ordinary plugin
validation/build path. The runtime cache includes framework pins; unrelated
plugin sets retain their existing keys. Missing-library messages, host crashes,
guest traps and inactive required hooks cannot pass the ready check.

Moveset integration now selects CSK 6.0.0 for 13.0.5 and retains 5.0.6 for
13.0.4. Marker-based skins report missing base gameplay code before play; the
private runtime exposes real Skyline boot files in its read-only RomFS view.
Explicit asset overlay/underlay choices keep base gameplay plugins enabled.
See [the moveset guide](../docs/MOVESET_MODS.md). Native fighter.json/Windows-DLL
packages remain outside the supported import formats. Structure recognition
does not guarantee gameplay compatibility.

## 7z implementation and redistribution

The unmodified official portable x64 `7za.exe` 26.05 is pinned by SHA-256. It
is a child process, not a system installation. `sevenzip_support.py` parses a
bounded `l -slt` listing and rejects unsafe paths, links, encrypted/special entries
and ambiguous metadata before creating output. Extraction uses `x -so`, which
writes only to stdout. The manager creates its own contained files, checks exact
lengths and CRC32, and shares the ordinary batch expansion quotas. Solid archives
use one decode pass, not one decompression per member. A bounded pipe queue,
768 MiB Windows Job Object, cancellation and timeouts constrain the decoder.
The 7-Zip source's `ArchiveExtractCallback.cpp` uses `CStdOutFileStream` in stdout
mode rather than its filesystem extraction path. Native decoder defects remain
an upstream dependency risk; keep the pin current when updating this component.

`7ZIP_LICENSE.txt` contains the upstream notices and `7ZIP_LGPL.txt` the LGPL 2.1
text. Corresponding unmodified upstream source is included in the **manager source
ZIP** at `third_party/7zip/7z2605-src.tar.xz`; artifact and source hashes/URLs are
recorded in `7ZIP_DISTRIBUTION.json`. Publish this source ZIP alongside the installer
when sharing releases. The source snapshot's ignore rules retain the pinned
`installer/7za.exe`; use the recorded upstream package when replacing it.

Public 7z variants use the same structural import path as ZIP/RAR files. A valid
archive does not assert gameplay compatibility. CSK 6.0.0 for 13.0.5 was still
absent from the official public listing at the last compatibility review; older
incompatible packages are not installed as substitutes.

## Publication resources (3.7)

The root README is written for GitHub users. `export_source.py` creates an explicit
public inventory and a separate fresh `github-ready/` directory, with contribution
instructions, issue templates, a Windows CI workflow, notices, artwork provenance
and corresponding 7-Zip source. `audit_publication.py` checks that clean inventory
before generated build/runtime files exist. `test_publication.py` checks its guards.
Internal case reports and local work-area artifacts are excluded. New branding is
loaded as a whole transparent asset, without the previous image crop rectangle.
The independent Windows ICO uses the separate symbol. See BRANDING.md and
LEGAL_REVIEW.md for the rights review and its limits. No legal safety is inferred
from a generated logo or from removing a copyright notice.

## Build from source

Use Windows x64 with Windows PowerShell 5.1 and .NET Framework 4.8 or later.
The compiler is Windows' Framework `csc.exe`; a separate modern .NET SDK is not
required. The source archive has the same `installer/` layout as this project.

```powershell
# Use a separate, trusted Python 3.14+ for development.
python prepare_runtime.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File installer/BuildLauncher.ps1
python build_release.py
```

`prepare_runtime.py` downloads the official SHA-256-pinned CPython 3.14.10 x64
embedded runtime and compatible NumPy 2.5.4, zstandard 0.25.0, Pillow 13.0.0,
and Capstone 5.0.9 wheels. It stages and probes the result before replacing the
source runtime. The previous source runtime is retained for rollback. It installs
neither pip nor system packages. Supply the official `UnRAR64.dll` 7.23.0 described
in `UNRAR_DISTRIBUTION.json`; preserve its license. The clean source archive
includes that unmodified redistributable decoder and the supplied brand assets.

The build uses an explicit payload allowlist and includes original license files
and `runtime/DISTRIBUTION.json`. Output: `release-3.7.0/Setup.exe` and
`OpenSmash_Mod_Manager_Installer_v3.7.0.zip`, with hashes. Build timestamps mean
byte-identical EXEs are not promised. Hashes detect corruption; they do not replace
a trusted download origin or publisher signature.

## Validation and maintenance

```powershell
installer/runtime/python.exe -B -m unittest discover -s installer -p 'test_*.py'
installer/runtime/python.exe -B test_batch_ui.py
installer/runtime/python.exe -B test_setup_release.py
python audit_dependencies.py
```

The tests use synthetic game folders and self-authored archives. Downloads for
testing belong in disposable fixtures, never a user's real mod library. Installer
tests use a namespaced HKCU registration and `--test-root`; set
`OPENSMASH_PREVIOUS_INSTALLER` to a retained previous release to exercise upgrades.
Real-installation checks require an explicitly configured game path.

For translations edit `author_locales.py` / `author_workflow_translations.py`,
then regenerate the checked-in catalogs. Preserve placeholders and access keys.
PowerShell text files containing non-ASCII characters must use UTF-8 with BOM;
Python, JSON, XAML and Markdown use explicit UTF-8.

Do not casually reformat or edit `arc_backend.py`, `arc_simd.py`, or
`arc_fs_support.h`: their byte hashes identify the loader build and changes force
an expensive runtime rebuild. Keep mod classification structural. Never run a
downloaded mod script or installer to determine its type. See `SECURITY.md` for
the security review and its limits.

Do not commit user libraries, downloads, saves, settings, generated game DLLs,
local test reports or caches. `export_source.py` creates a clean source ZIP from
an explicit allowlist; review that artifact before uploading it to GitHub.
