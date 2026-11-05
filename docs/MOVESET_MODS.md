# Movesets, visual patches and costume selection

Downloading and importing a package verifies its archive structure, not that it
adds a playable character. Three different things are commonly called a mod:

- A normal costume replaces one of a fighter's existing costumes. For example,
  a file under `fighter/luigi/model/body/c01` is Luigi's **second costume**.
  Select Luigi and cycle the costume. It does not add a CSS portrait or moveset.
- A custom-moveset skin supplies models, sounds or UI for another author's
  moveset. Marker files and extended slots such as `c32` or `c120` do not create
  that moveset themselves. The base gameplay plugin must be installed and active.
- A moveset base supplies gameplay NRO code and typically also assets, UI/slot
  definitions and framework requirements. All parts must match the game version.

The library details and import warnings now show costume/extended-slot hints.
Before **Play with mods**, marker-based packages are checked against the active
gameplay plugins. Missing matching code is reported by package and marker name;
the manager does not silently launch a partial moveset as though it were ready.
Marker matches are dependency evidence, not proof of full compatibility.

## Install a base together with its visual patch

Read the original author's instructions and obtain the original packages from
their official pages. The manager does not bundle character mods or invent a
compatible moveset from a skin.

1. Import the complete moveset base, including its NRO and asset directories.
2. Import its matching visual patch. When identical asset paths have different
   contents, select **Als Skin/Patch ueberlagern** in the conflict preview.
   Confirm only if the packages are intended to work together.
3. If the visual patch was installed first, import the missing base and choose
   **Als Basis ergaenzen**. Existing visual files take priority, while the base's
   remaining assets and gameplay code are retained.
4. Keep both entries enabled and choose **Play with mods**. The manager builds a
   private runtime and checks the selected plugins. The first build takes minutes.

These two choices are explicit per-file priorities. **Konfliktpartner ersetzen**
still pauses the conflicting entry, so it should not be used to replace a
required moveset base with a cosmetic patch. Pausing a higher-priority skin
restores the base's files; Undo restores the previous selection and priorities.
The stored library copies are never edited to merge assets. Different versions
of the same plugin cannot be hidden by an asset priority. Unrelated conflicts
still require a separate decision. Exported libraries must have their overlay
decisions reviewed again on import; priorities are not silently trusted from
an external package manifest.

The selected patch's root `config.json` replaces its permitted base's root
configuration, as a folder installation would. Explicit `share-to-added` and
`share-to-vanilla` destinations also take priority over physical copies from
those bases: an old physical model must not unshare a model that the new patch
defines as an archive alias. Only the generated profile hides those files;
disabling the patch restores them. Unrelated owners remain conflicts.

Independent `.xmsbt` text patches are retained in their individual mod folders
so ARCropolis's native handler can merge their labels. Different text for the
same label remains a conflict requiring an explicit priority. UTF-8/UTF-16
input is supported; malformed XML, entities and changed source bytes are
rejected before composition. This prevents a common character-name patch from
pausing an otherwise independent skin or moveset.

## Framework resolution and runtime fix

The dependency resolver now chooses the pinned CSK Collection **6.0.0 for Smash
13.0.5**, retaining **5.0.6 for 13.0.4**. Unknown game versions and known
incompatible supplied binaries are rejected. Source:
[The CSK Collection](https://gamebanana.com/mods/499008).
The 6.0.0 archive SHA-256 is
`5ebf9d1426494e901da3fe2c1a291de1d2e5258efe77d4eefeb100ea3762d3ab`;
the extracted NRO SHA-256 is
`5c4e39ef3cbc6f03792483a23542e34a4ce9212b77a9cf265380339d39787efc`.
The provider's MD5 was also checked during local investigation. Only the pinned
NRO is used, excluding unrelated example mods and optional flags from the archive.

Extended body/effect slots request the relevant shared frameworks even when a
skin itself contains no NRO. Framework definitions are part of normal and fast
runtime-cache validity. Shared libraries retain their real boot filenames;
different bytes under the same boot filename cause an error.

The automatic Smashline pin is **1.6.8**, SHA-256
`a83636e565be0729271aa7c21817da9aa3b8b3e9b3abed7499c1eeae4cb57d5c`,
verified against the official GitHub asset digest. The
[2.0.0 release](https://github.com/HDR-Development/smashline/releases/tag/v2.0.0)
explicitly warns that existing movesets may be incompatible: its C-linkage
`smashline_clone_weapon` and `smashline_update_weapon_count` signatures changed
without changing the symbol names. Automatically providing 2.0.0 to older
movesets can therefore crash even when all imports resolve. A local probe
reproduced that crash while registering Bandana Dee. 1.6.8 retains their ABI and
includes the upstream fixes for Smash 13.0.5. No mod is patched to fake the API.

Plugins referencing recognized 2.0-only APIs require the matching framework to
be explicitly imported; an explicitly supplied framework is not silently
replaced by the automatic one. The complete selected set still has to pass the
normal runtime probe. A version cannot be proved from an unversioned C symbol
alone, and mixing incompatible plugin ABI generations is not supported.

The private runtime now exposes the selected SD profile's actual
`atmosphere/contents/01006A800016E000/romfs/skyline/plugins` directory through
read-only `rom:/skyline/plugins` filesystem operations. Previously, plugins
could be loaded but dependency existence checks in guest code still saw the
original unmodified RomFS and reported every library missing. Existence,
opening and directory lookup now use the same actual files; missing files
still fail. Other RomFS paths, mount rules and write denial remain intact.
This requires rebuilding the private runtime, not modifying the game dump.

Some original plugins still call a fixed 13.0.4 main address on 13.0.5. The
private builder can derive conservative callable aliases from the user's own
`build/binaries/13.0.4/main.elf` and `13.0.5/main.elf` (using the configured build
directory). Both local files are required for this compatibility pass. It
compares unique complete function bodies, PC-relative references, callees and
external import identities, retaining existing OpenSmash verified ABI boundaries
only when their normalized bodies also match. Ambiguous targets and existing
13.0.5 function entries are not remapped. The fallback applies only to unresolved
calls originating in the plugin address range. Missing or changed functions
still trap; it does not port arbitrary hooks, data pointers or changed APIs.
No game bytes or generated address table are distributed. Both ELF fingerprints
and runtime/builder sources participate in cache validity.

The Cuphead build investigated here needs that pass on 13.0.5. A successful
plugin initialization alone does not establish compatibility: its fixed call
was first reached after entering the training battle.

## Investigated packages

- [LAPIS' CUPHEAD (Moveset Patch)](https://gamebanana.com/mods/639357) is a visual
  patch for the [Cuphead moveset](https://gamebanana.com/mods/633920).
- [Kirby Air Riders Bandana Dee](https://gamebanana.com/mods/659713) is a skin
  for [Bandana Dee Moveset](https://gamebanana.com/mods/580288). Follow its README
  for the Dynamic/Simple/Spring Breeze lineup differences.
- [Luigi Streetwear Hoodie](https://gamebanana.com/mods/735744) replaces `c01`.

No package titles or these character names are used to decide dependency or
overlay behavior. Tests use synthetic future names, marker files and plugin
references. Support for arbitrary future instructions, hook offsets, plugin
APIs or incompatible mod combinations is not guaranteed; concrete build/runtime
errors remain blocking and require their own investigation.

## Local validation and limits

With copied saves and a separate test profile on Smash 13.0.5, the original
Cuphead base plus LAPIS patch and Bandana Dee base plus Dynamic Lineup both
reached training battles and rendered their custom fighters. Basic attack,
special and jump input sequences ran without the previous guest traps. Luigi
Streetwear Hoodie rendered after selecting Luigi's second costume. The normal
Vanilla executable also started successfully with Skyline and asset mods off.
These short runs do not cover every move, costume, stage or multiplayer pairing.

Synthetic regression tests cover missing-base evidence, game-version pins,
framework-cache invalidation, library filename collisions, explicit priorities,
alias destinations, independent/conflicting text labels, profile restoration
after disabling a skin, Undo, read-only RomFS visibility and conservative
cross-version function matching. Full compatibility with all future mods cannot
be inferred from those tests or a successful build.
