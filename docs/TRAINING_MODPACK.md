# Training Modpack compatibility change

Requires the companion OpenSmash runtime/lifter changes, tested locally with
Smash 13.0.5 and the original
[Ultimate Training Modpack v7.1.1 ZIP](https://github.com/jugeeya/UltimateTrainingModpack/releases/tag/v7.1.1).

## Optional setup from source

This repository includes the manager changes and the companion source patch at
[`compatibility/opensmash/training-modpack-v7.1.1.patch`](../compatibility/opensmash/training-modpack-v7.1.1.patch).
It includes the runtime changes, both lifters, a standalone SIMD regression test
and OpenSmash-specific documentation. It contains no mod binaries or game data.
Nothing downloads or activates the Training Modpack automatically.

1. Build/install the manager from this repository following the root README.
   Existing older installer releases do not acquire these changes just by
   downloading this patch.
2. Use your own complete OpenSmash 13.0.5 source/build installation with LLVM,
   Microsoft C++ Build Tools and Windows SDK. Back up your sources first.
3. From this manager checkout, apply the companion patch to OpenSmash. In
   PowerShell, replace the example OpenSmash path:

   ```powershell
   $Patch = (Resolve-Path "compatibility/opensmash/training-modpack-v7.1.1.patch").Path
   $OpenSmash = "C:\Path\To\OpenSmash"
   git -C $OpenSmash apply --check $Patch
   if ($LASTEXITCODE -ne 0) { throw "Source mismatch: inspect the patch before continuing." }
   git -C $OpenSmash apply $Patch
   if ($LASTEXITCODE -ne 0) { throw "Patch application failed." }
   ```

   The original installation was an extracted source archive without a Git
   revision. [`base-hashes.json`](../compatibility/opensmash/base-hashes.json)
   records SHA-256 hashes of the affected base and result files after UTF-8 BOM
   removal and CRLF-to-LF normalization. A patch conflict on another source
   revision requires review; do not force it or copy hook offsets from elsewhere.
4. Connect the updated manager to that OpenSmash folder. Its normal private
   runtime build stages the patched runtime/lifter sources and invalidates old
   ARC/plugin caches. The original vanilla executable is retained.
5. Download `TrainingModpack.zip` yourself from the official release linked
   above. The release ZIP used in validation has SHA-256
   `edf1ca8fdf479feb801e6afacc3abf440e05263af9f5d872d0d16978fb6590d9`.
   For example, verify it with `Get-FileHash .\TrainingModpack.zip -Algorithm SHA256`.
6. Import the unchanged ZIP and enable its library entry as described below.

OpenSmash source modifications are supplied separately under GPL-3.0; see the
[companion notice and license](../compatibility/opensmash/NOTICE.md). The manager
application's own code retains its existing MIT license.

## Using the mod

Import the original ZIP using **Mods hinzufügen**, review the preview and enable
**Ultimate Training Modpack v7.1.1**. **Mit Mods spielen** builds the private
plugin runtime before starting. Special + Up Taunt opens the training menu
(default keyboard X + I). Pause the library entry to start with the other mods;
**Vanilla spielen** uses the original native executable.

The release name is recognized only when all three original NRO hashes match.
An author's info.toml still takes precedence. The NROs are not patched or bundled
with the manager.

## Changes and verification

Private ARC/plugin builds now stage current OpenSmash runtime and lifter sources
and include their content hashes in both normal and fast cache validation.
The plugin builder itself is also part of cache identity. Stale runtimes are
rebuilt before play; source changes during a build prevent publishing its cache
marker. The original native executable and generated base game objects are not
replaced by source staging.

Training settings and positional save states under `ultimate/TrainingModpack`
are copied to the next profile, including when the mod is paused and re-enabled.
Links and oversized data trees are rejected before the profile switch. These
writable settings are kept separate from immutable mod asset checksums.

Missing plugin functions now report the concrete missing symbol. Existing
trap, inactive-hook and mount checks remain mandatory. A successful build alone
does not claim full gameplay compatibility.

Local validation includes the core manager regression suite, source cache
invalidation through the fast path, exact package naming, and settings/state
preservation over disable/enable. Real training checks cover menu use, settings
reload, CPU Jump/Always, visible hitboxes and positional save/load. All fighters,
stages, online behavior and arbitrary combinations remain outside this test.

Validation before publication: 868 SIMD cases against Unicorn, SDK self-tests
with zero failures, 102 selected manager regression tests, and publication
guards. The final manager-selected runtime also reached training after a real
disable/enable cycle. Vanilla reached the main menu with its executable
unchanged; the other nine local mod selections, original saves and game
configuration were preserved. These are local checks, not a compatibility
guarantee for every system or mod combination.

Run the manager regression tests from this checkout, using a prepared Python
runtime, with:

```powershell
installer/runtime/python.exe -B -m unittest discover -s installer -p 'test_*.py'
python -B -m unittest test_publication
```

After applying the OpenSmash patch, its `tests/simd_immediate_test.py --clang
<clang.exe>` test requires Unicorn and a Windows C compiler. Its new
`docs/TRAINING_MODPACK.md` documents remaining unused or unsupported imports;
general HTTPS/updater support is not added. Existing missing-import, trap,
inactive-hook and version compatibility checks remain in force.
