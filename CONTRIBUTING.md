# Contributing

Small, focused fixes and improved translations are welcome. Explain the concrete
problem, resulting behavior and validation in your pull request.

## Build and test

Use Windows x64, Windows PowerShell 5.1, .NET Framework 4.8+ and a separate trusted
Python 3.14+. From the repository root:

```powershell
python audit_publication.py
python prepare_runtime.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File installer/BuildLauncher.ps1
installer/runtime/python.exe -B -m unittest discover -s installer -p 'test_*.py'
installer/runtime/python.exe -B build_release.py
```

`audit_publication.py` runs before preparing generated runtime files. The backend
suite uses synthetic game folders and self-authored asset bytes. No real game or
downloads from a personal mod collection belong in tests. Native UI tests require
an interactive Windows session. Installer lifecycle tests use isolated app roots
and namespaced HKCU registrations; read `test_setup_release.py` before running
them and set `OPENSMASH_PREVIOUS_INSTALLER` to the previous retained release.

## Implementation conventions

- Keep code and useful comments in English. Keep the German UI source phrases
  stable and maintain the local translation catalogs. Do not translate provider
  content, protocol keys, file paths or mod identities.
- Use explicit UTF-8. PowerShell files containing non-ASCII text need a UTF-8 BOM.
- Preserve user libraries, settings, activation, saves and original game options.
  Use ordinary previews, transactions, cancellation checkpoints and undo.
- Identify support by file structure/type, never individual mod titles.
- Do not casually edit or reformat `arc_backend.py`, `arc_simd.py` or
  `arc_fs_support.h`: their byte hashes identify loader builds. A change forces
  expensive local recompilation and requires integration validation.
- Do not execute downloaded mod scripts/installers, bypass provider restrictions,
  register another manager's protocol, or silently install downloaded mods.
- Keep native dependencies pinned, preserve notices and review corresponding
  source obligations before updating them.

## Rights and privacy

Only contribute material you have the right to submit. Original project-code
contributions are under the existing MIT license. Preserve existing notices;
identify external code and its license in the PR. Do not assume a copyright notice
is a problem to remove. AI-assisted contributions need the same review as others.

The RAR fixtures contain original synthetic bytes, not game assets. Creating new
RAR5 fixtures may require a separately licensed RAR encoder; it is not bundled
or needed to run tests. Keep fixture hashes and provenance documented.

Never commit credentials, personal settings/logs, mod libraries, game data,
generated game code/binaries or build caches. Run publication checks in a clean
checkout before submitting. Use private vulnerability reporting when the
repository owner has enabled it; see SECURITY.md.
