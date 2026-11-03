# Security review and reporting

Review date: 2026-11-03. Release: 3.7.0.

3.7 separates the public source inventory from local work, adds notice/source
checks and records the new AI-supplied artwork provenance. Existing runtime and
archive-decoder versions are unchanged from the preceding dependency lookup.
Publication checks are not legal clearance or exhaustive secret detection.

3.6 adds 7z through the pinned unmodified official portable 7-Zip 26.05 decoder.
Only decoded stdout bytes enter manager-created destinations; the child cannot
choose extraction paths. Listing size, ambiguous metadata, links, encryption,
entry names, exact sizes, CRC32, batch expansion, time and decoder memory are
bounded. A Windows Job Object limits memory to 768 MiB and kills the child on
parent exit. Download-only public formats are cached under a neutral `.file`
suffix and can be explicitly saved, never executed or automatically installed.
Clear-all deletion derives owned UUID paths and waits for active transfers to
close files. The dependency lookup was repeated on the review date; no published
PyPI/OSV advisories were returned for the shipped Python package versions.
This does not certify third-party plugin internals or eliminate unknown native
decoder risks. Binary provenance and matching source are documented in README.md.

3.5 adds bounded, versioned download-list JSON containing provider IDs and hashes.
Imported recipes cannot supply arbitrary URLs; normal game/file ownership,
download integrity and archive safety checks remain mandatory. Review detects
list changes. Existing activation is preserved, conflicts install paused and
unrequested archive members are skipped. Known incompatible supplied framework
binaries are rejected before compilation, including renamed copies. Reusing a
verified unchanged plugin set for asset-only edits does not approve missing
dependencies for a game launch.

3.4 adds optional image conversion capped at 8 MiB, 20 million decoded pixels
and a 480×270 cached output. Covers never enter gameplay profiles or mod hashes.
Download removal accepts terminal jobs only, validates owned UUID paths and
uses a database transaction plus reversible file moves; persisted arbitrary
paths are never deletion targets. Shared gameplay libraries use explicit pinned
artifacts/members and game-version gates. Known incompatible CSK 5.0.6 is not
automatically loaded into a 13.0.5 game. These changes do not extend the previous
dependency audit into a security audit of third-party gameplay plugin internals.

Report a suspected vulnerability privately to the repository maintainer using
GitHub's private vulnerability reporting if enabled. Do not attach copyrighted
game assets, personal settings, credentials or saves. Include the manager version,
Windows version, a minimal self-authored reproducer and expected/actual behavior.
There is no published security inbox or response-time guarantee at this stage.

## Changes in 3.3

CPython 3.13.16 was replaced with 3.14.10, including the expedited TLS trust-store
mitigation for compromised eMudhra intermediates (CVE-2026-115557). This release
also contains the upstream tarfile link-filter correction (CVE-2026-114583);
the manager does not import TAR archives. The official
[Python release notes](https://www.python.org/downloads/release/python-31410/)
describe the patches. Python 3.15.2 is the newest feature line; 3.14.10 is the
supported patched line chosen here because zstandard 0.25.0 has a matching Windows
wheel. Mixing CPython ABIs or shipping a release candidate is deliberately avoided.

ZIP/RAR/7z import rejects Windows reserved superscript device names (`COM¹`,
`LPT²`, etc.), control characters and invalid filename characters before creating
output files. This closes a Win32 device-name validation gap shared by all archive
types. See Microsoft's
[Windows filename rules](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file).

## Dependency inventory

| Component | Shipped/required | Audit result |
| --- | --- | --- |
| CPython | 3.14.10 x64 embedded | Updated, official archive and pinned SHA-256 |
| NumPy | 2.5.4 | Current PyPI stable; no PyPI/OSV advisory for this version on review date |
| zstandard | 0.25.0 | Current PyPI stable; no PyPI/OSV advisory for this version on review date |
| Pillow | 13.0.0 | Current PyPI stable; no PyPI/OSV advisory for this version on review date |
| Capstone | 5.0.9 | Current PyPI stable; no PyPI/OSV advisory for this version on review date |
| 7-Zip Extra | 26.05 x64 portable | Current official stable; pinned binary, notices and matching source supplied |
| UnRAR DLL | 7.23.0 | Current stable DLL retained; upstream offers 7.30 beta 2, not adopted |
| Windows PowerShell | 5.1 | Latest Windows PowerShell line, serviced with Windows |
| .NET Framework / WPF / WinForms | 4.8 minimum, compatible with 4.8.1 | Windows-serviced; modern .NET/PowerShell 7 are different hosting stacks |
| ARCropolis / Smashline / nro-hook | 4.1.1 / 2.0.0 / 0.4.0 | Current stable upstream releases; separate local downloads, not redistributed |
| LLVM, C++ tools, SDK, SDL/Vulkan/ImGui | Supplied/selected by the existing game | External compatibility dependencies; not silently replaced by the manager |

PyPI versions/advisories and [OSV](https://osv.dev/) are recorded by
`audit_dependencies.py`. Official artifact URLs, checksums and licenses are in
`runtime/DISTRIBUTION.json` and `UNRAR_DISTRIBUTION.json`. The runtime probe reports
OpenSSL 3.5.9 and SQLite 3.50.4. These are the components in the official Python
distribution; they are not separately replaced with ABI-incompatible DLLs.

Windows and its .NET/PowerShell security updates remain the user's OS maintenance
responsibility. Windows 10 users need an edition/channel still receiving security
updates (for example, applicable ESU or LTSC). A minimum runtime version alone
does not establish that the operating system is fully patched. See Microsoft's
[Framework servicing documentation](https://learn.microsoft.com/en-us/dotnet/framework/install/versions-and-dependencies)
and [Windows PowerShell lifecycle explanation](https://learn.microsoft.com/en-us/powershell/scripting/what-is-windows-powershell).

## Trust boundaries checked

Archive traversal, duplicate/case-folded paths, alternate streams, links/junctions,
file/directory collisions, encrypted entries and extraction quotas are validated.
UnRAR supplies decoded bytes to manager-created files rather than choosing output
paths. Nested archives share the import budget. ZIP/RAR/7z CRC and download byte
counts are checked. Provider MD5 is used for integrity when present; downloaded
files also receive a local SHA-256. MD5 is not claimed to authenticate a publisher.

GameBanana traffic is HTTPS with hostname checks, restricted provider hosts,
redirect limits, public-address validation, response-size bounds and ordinary
certificate verification. Remote HTML is converted to text. Image downloads and
decoded pixel counts are bounded. There is no evaluation of downloaded code.
Own one-click links are parsed strictly and ownership is checked through the API;
installation requires a separate user action. User-scoped named pipes restrict
link forwarding to that Windows account.

Setup stages and verifies its bundled payload before switching the application
directory; failures roll back. Uninstall uses ownership markers and file hashes,
and preserves foreign/modified files. The game, mod library, activation state,
profiles, saves, DLC configuration, online settings and volume are outside the
application upgrade payload.

## Limits

This is a source/dependency review and regression test run, not a penetration
test or a guarantee that no vulnerabilities exist. Advisory databases can lag.
The review did not audit the full game, external toolchains, all transitive native
codecs or every third-party mod. Plugins are executable code once deliberately
translated and launched by the game; install only mods you trust. Same-user local
malware can modify a per-user application and is outside this application's
security boundary. The current first-party EXEs are not Authenticode signed.
