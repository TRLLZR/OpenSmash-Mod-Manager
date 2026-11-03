# Publication and license review

Review date: 2026-11-03. Application version: 3.7.0.

This is a technical inventory and packaging review, not a legal opinion or a
guarantee of non-infringement. Copyrighted material is not automatically unlawful
to distribute: the relevant permission and license conditions matter. Deleting
someone else's copyright or license notice does not remove their rights.

## Scope and findings

The review inspected the application source, dependency manifests, bundled notices,
test-fixture generator and contents, asset provenance, build allowlist and exported
publication inventory. It did not perform a comprehensive external source-code
similarity search, patent review, trademark clearance or analysis of every future
user-supplied mod or locally built third-party integration.

- **Original source:** the existing MIT license and contributor copyright notice
  are retained. No additional unauthorized copied implementation was identified
  by this inspection. This is not proof of authorship or an exhaustive similarity
  finding. Historical internal names/identifiers are interoperability state, not
  a reason to remove notices or break users' existing libraries.
- **Native compatibility glue:** shipped files implement local integration.
  Required game build sources/objects are read from the user's installation or
  copied only into that user's private build area. Those local generated sources,
  game objects, plugin binaries and hook lists are not exported or shipped here.
  External ABI references in `arc_fs_support.h` remain identified; no complete
  external SDK header is included. The three loader signature sources were not
  changed for publication.
- **Archive components:** the unmodified UnRAR DLL and 7-Zip executable have
  their own terms. They are not relabeled as MIT. Their original notices and
  pinned provenance remain supplied. RAR support is extraction only; no RAR
  compressor is shipped. The included UnRAR DLL permission permits handling RAR
  archives in software, but is a freeware component, not a claim of wholly
  MIT-licensed or fully open-source native dependencies.
- **7-Zip source:** the matching official source archive is part of the manager
  source package. Release instructions require publishing that source ZIP beside
  the installer. This makes corresponding source available from the same release
  location instead of merely assuming a link to an upstream project is sufficient.
- **Private Python runtime:** official distributions retain their PSF, BSD, HPND
  and other component notices. NumPy's wheel includes OpenBLAS and additional
  runtime notices; its entire license directory is preserved. The review does
  not incorrectly treat all bundled native components as one MIT license.
- **Fixtures:** the RAR generator writes original short strings and synthetic
  patterns, including files with game-like extensions. The extensions do not
  make those bytes game assets. Bad-path, link, encrypted, corrupt and multipart
  fixtures exist to test rejection. A proprietary RAR encoder used to create
  fixtures is not needed for tests and is not distributed.
- **Branding:** the old wordmark/icon are replaced by the maintainer-supplied
  ChatGPT-generated design. AI origin and the tool-prepared transparent assets
  are recorded in BRANDING.md and BRAND_ASSETS.json. No exclusive rights or
  legal safety are inferred from the prompt.
- **Publication boundary:** only the dedicated source inventory is exported.
  Game data, keys, firmware, real mods, saves, personal preferences, test downloads,
  local logs, historical case reports and unrelated workspace utilities such as
  SoundVolumeView are outside the publishing folder. There are no bundled
  Windows font files. No source replacement was justified solely because it
  contained an ordinary copyright notice.

## What maintainers must preserve

| Component | Permission/terms | Supplied evidence |
| --- | --- | --- |
| Original manager and setup source | MIT | LICENSE.txt, original notice retained |
| UnRAR64.dll 7.23.0 | Original freeware DLL terms | UNRAR_LICENSE.txt, UNRAR_DISTRIBUTION.json |
| 7za.exe 26.05 | LGPL 2.1-or-later and included BSD notices | 7ZIP_LICENSE.txt, 7ZIP_LGPL.txt, 7ZIP_DISTRIBUTION.json, matching source archive |
| CPython and Python packages | Their upstream/component licenses | runtime/LICENSE.txt, runtime/DISTRIBUTION.json, package notice directories in releases |
| New artwork | Maintainer-supplied AI output; separately documented | BRANDING.md, BRAND_ASSETS.json |
| External game/mod frameworks | Separate projects and author terms | Local downloads/builds only; no game/plugin binaries in the source publication |

Keep upstream notices verbatim. If replacing a dependency, first verify the
replacement's provenance, license, compatibility and functionality; renaming it
or deleting its copyright line is not a substitute. Mod-list sharing does not
grant redistribution rights to mod assets. The name, artwork and future public
use still need the maintainer's own rights assessment if legal certainty is needed.

## Primary references

- [MIT license conditions](https://choosealicense.com/licenses/mit/)
- [GNU LGPL 2.1, including executable/source distribution](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html)
- [Official 7-Zip licensing information](https://www.7-zip.org/license.txt);
  the precise Extra 26.05 notices shipped with this executable take precedence
  over a different upstream package's summary.
- [RARLAB developer downloads](https://www.rarlab.com/rar_add.htm);
  the exact DLL permission text is supplied in UNRAR_LICENSE.txt.
- [OpenAI Europe terms](https://openai.com/policies/eu-terms-of-use/), including
  the distinction between service output terms and other people's rights.

The repository and release checks reduce accidental disclosure and missing
notices. They do not decide legal ownership or certify all possible uses.
