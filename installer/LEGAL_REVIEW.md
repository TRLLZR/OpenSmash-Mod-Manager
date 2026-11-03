# Licenses and redistribution

The application code uses the MIT license in `LICENSE.txt`. Bundled components
retain their own licenses and copyright notices in `THIRD_PARTY_NOTICES.txt`.

| Component | License information |
| --- | --- |
| Manager, setup and UI source | `LICENSE.txt` (MIT) |
| 7-Zip Extra | `installer/7ZIP_LICENSE.txt`, `installer/7ZIP_LGPL.txt` |
| UnRAR DLL | `installer/UNRAR_LICENSE.txt` (original freeware library terms) |
| CPython and Python packages | Component notices retained in the release runtime |
| Wordmark and icon | `BRANDING.md`, AI-generated artwork |

Native decoder versions, upstream URLs and checksums are recorded in the
`installer/*_DISTRIBUTION.json` manifests. Matching 7-Zip source is included at
`third_party/7zip/7z2605-src.tar.xz`; publish the source package alongside installer
releases. Keep the upstream license and notice files when redistributing binaries.

Game data and mod assets belong to their respective authors. Installing a mod
does not grant permission to redistribute its contents. Optional gameplay
frameworks are obtained separately and retain their upstream terms.
