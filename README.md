<p align="center">
  <img src="installer/BrandLogo.png" alt="OpenSmash Mod Manager" width="600">
</p>

# OpenSmash Mod Manager

A native Windows app for browsing, installing and organizing mods for OpenSmash.
Build your mod library, choose your active setup and launch the game from one place.

**Windows x64 · Version 3.7.0 · MIT-licensed application code**

**AI-assisted / vibe-coded:** this project was built with extensive help from
ChatGPT and Codex, through iterative development, testing and user feedback.

## Features

- **Import ZIP, RAR, 7z and folders** with drag-and-drop, batch installation and
  duplicate detection.
- **Review conflicts before installing**, activate or pause individual mods, and
  undo changes.
- **Browse GameBanana inside the app**, filter skins by character, choose file
  variants, check updates and open preview images full screen.
- **Manage downloads** with a persistent queue, progress, retry, cancellation and
  individual or bulk removal.
- **Choose list or tile view**, search your library and add cover images.
- **Share lightweight mod lists.** Recipients review the list and install missing
  mods from their recorded GameBanana sources. Full library ZIP export is available too.
- **Play with your selected mods or launch vanilla**, using your existing game settings.
- **Follow your Windows display language** across 16 language families, with light,
  dark, system and high-contrast appearances.

## Screenshots

The actual application, shown with illustrative demo mods and original sample artwork.

**Tile library and cover images**

![Mod library in the light theme with tile view](docs/images/library-tiles-light.png)

**List view in the dark theme**

![Mod library in the dark theme with list view](docs/images/library-list-dark.png)

**Download queue**

![Download queue with completed, active and queued demo entries](docs/images/downloads-light.png)

## Get started

You need Windows 11 x64 or a supported Windows 10 x64 installation (2004+),
.NET Framework 4.8+, Windows PowerShell 5.1 and an existing compatible
**OpenSmash 13.0.5** installation with your own game data.

1. Extract a versioned **Installer ZIP** and run `Setup.exe`. The private Python
   runtime and archive decoders are included.
2. Connect your OpenSmash folder.
3. Drop mod archives or folders into the library, or download a file through
   **Discover**.
4. Review the preview and confirm installation.
5. Enable your chosen mods and select **Play with mods** or **Play vanilla**.

Local loader/plugin builds use OpenSmash's build inputs, LLVM/Clang, Microsoft C++
Build Tools and the Windows SDK. Gameplay plugins may also need matching frameworks;
see the [compatibility guide](installer/BEKANNTE_EINSCHRAENKUNGEN.md).

Optional **Ultimate Training Modpack v7.1.1** support is available as source
changes and a companion OpenSmash patch. Follow the
[installation and compatibility guide](docs/TRAINING_MODPACK.md) before importing
the original release yourself. The mod is not bundled or automatically installed.

For new-character movesets, visual patches and costume selection, see the
[moveset setup guide](docs/MOVESET_MODS.md). It explains required base plugins,
versioned frameworks and explicit skin/base overlay choices.

## Build and contribute

The application uses **C#/.NET Framework**, **PowerShell/WPF** and **CPython**.
From the repository root, using a separate trusted Python 3.14+ on Windows:

```powershell
python prepare_runtime.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File installer/BuildLauncher.ps1
installer/runtime/python.exe -B -m unittest discover -s installer -p 'test_*.py'
installer/runtime/python.exe -B build_release.py
```

See the [developer guide](installer/README.md), [contribution guide](CONTRIBUTING.md)
and [release checklist](docs/RELEASING.md). Suggestions, reproducible bug reports,
translation improvements and code reviews are welcome in Issues and Pull Requests.

## License and credits

Original application code is covered by [LICENSE.txt](LICENSE.txt). Bundled
components retain their own licenses; see [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).
The source package includes the matching 7-Zip source under `third_party/7zip/`.
The wordmark and icon were created with AI assistance; details are in
[BRANDING.md](BRANDING.md). Security information is in [SECURITY.md](SECURITY.md).
