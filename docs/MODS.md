# Mod setup

## Costumes and movesets

- A costume replaces an existing slot: `c00` is the first costume, `c01` the second.
  Select the fighter and cycle costumes; a skin does not add a character portrait.
- A moveset skin changes the appearance of another mod. Install its complete base
  moveset, including the gameplay NRO and assets, and follow the author's instructions.
- Import the base and then the skin. In the conflict preview, choose the skin/patch
  overlay option. If the skin was installed first, use the option to add the base
  underneath it. Keep both entries enabled. Replacing a conflict partner pauses it.

Overlay priorities affect the generated profile; original library files are kept.
Disabling a skin restores the base files, and Undo restores the previous selection.
Compatible XMSBT text patches can coexist; different text for the same label needs
an explicit priority. Different versions of the same plugin remain a conflict.

Examples: [LAPIS' Cuphead patch](https://gamebanana.com/mods/639357) needs the
[Cuphead moveset](https://gamebanana.com/mods/633920);
[Kirby Air Riders Bandana Dee](https://gamebanana.com/mods/659713) needs
[Bandana Dee Moveset](https://gamebanana.com/mods/580288).
Luigi Streetwear Hoodie uses Luigi's second costume.

## Plugin requirements

The manager currently targets OpenSmash 13.0.5. Its automatic dependencies use
Smashline 1.6.8 and nro-hook 0.4.0; CSK 6.0.0 is selected for 13.0.5. CSK 5.0.6 is
reserved for 13.0.4. URLs and checksums are kept in `installer/plugin_runtime.py`
and `installer/plugin_dependencies.py`.

Smashline 2.0 changed its API and can break older movesets. Plugins using its new
APIs need a matching explicitly imported framework. Do not mix incompatible versions.

Older Cuphead binaries also call fixed 13.0.4 game addresses. On 13.0.5, the
manager's conservative compatibility pass requires your own `main.elf` files in
both `binaries/13.0.4/` and `binaries/13.0.5/` under the configured OpenSmash build
directory. It derives only verified function aliases locally; no game code or
address table is distributed. Missing functions, changed APIs and arbitrary old
hook/data offsets are not automatically supported.

If a build or launch fails, check the reported missing dependency/symbol and the
mod author's game-version requirements. Short local tests covered Cuphead, Bandana
Dee and Luigi in training; they do not cover every move, stage or future mod.

## Ultimate Training Modpack v7.1.1

Use a complete OpenSmash 13.0.5 source/build installation and the current manager
source. The companion runtime/lifter patch must be applied before importing the mod.
Back up your OpenSmash sources. From this manager checkout in PowerShell:

```powershell
$Patch = (Resolve-Path 'compatibility/opensmash/training-modpack-v7.1.1.patch').Path
$OpenSmash = 'C:\Path\To\OpenSmash'
git -C $OpenSmash apply --check $Patch
if ($LASTEXITCODE -ne 0) { throw 'Source mismatch: review the patch first.' }
git -C $OpenSmash apply $Patch
```

The affected source versions are recorded in
[`base-hashes.json`](../compatibility/opensmash/base-hashes.json); do not force a
conflicting patch. Obtain the unchanged ZIP from the
[official release](https://github.com/jugeeya/UltimateTrainingModpack/releases/tag/v7.1.1),
import it and enable its library entry. The validated ZIP SHA-256 is
`edf1ca8fdf479feb801e6afacc3abf440e05263af9f5d872d0d16978fb6590d9`.

Play with mods rebuilds stale private runtimes. Open the training menu using the
mod's configured shortcut. Settings and positional states in
`ultimate/TrainingModpack` are preserved when switching profiles or pausing the mod.
Menu use, CPU options, hitboxes and positional save/load were tested locally;
online play and arbitrary mod combinations are not guaranteed.
