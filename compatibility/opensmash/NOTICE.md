# Companion OpenSmash source patch

Upstream: OpenSmash-Ultimate, https://github.com/Denkishi/ssbu-recomp

The companion patch modifies OpenSmash runtime and translator sources and adds
regression tests and documentation for optional Ultimate Training Modpack v7.1.1
compatibility. The source changes were prepared on 2026-11-04 with Codex.
Existing upstream authors retain their copyrights. This patch is supplied under
the GNU General Public License version 3; see [LICENSE.txt](LICENSE.txt).
It is separate from the MIT-licensed manager application.

This is the preferred source form of these changes, not a compiled game/plugin
distribution. The base was a local extracted OpenSmash source archive; the
exact affected source content is identified in `base-hashes.json` (normalized
UTF-8 text, without BOM, with LF line endings). Review conflicts against newer
upstream revisions rather than forcing the patch.

The patch includes seven modified runtime/lifter files, one standalone SIMD
test and one documentation file. It includes no Ultimate Training Modpack NRO,
release ZIP, generated game source, game data, keys, personal settings or saves.
Obtain the optional mod separately from its official release. Its own license
and authors' rights remain separate; it is not redistributed here.
