# Release checklist

1. Update the application version, user documentation, source exporter and
   previous-version installer test. Preserve the existing copyright notices.
2. Run publication checks in a clean checkout. Prepare the pinned runtime, build
   the host, and run the synthetic backend suite. Perform native UI/layout and
   isolated installer tests on Windows; do not imply a hosted CI run tested real
   gameplay or another person's installation.
3. Review `THIRD_PARTY_NOTICES.txt`, the runtime's component notices and the codec
   distribution manifests. Keep the matching 7-Zip source archive and LGPL/BSD
   notices. Document any changed upstream component or artwork provenance.
4. Build the installer with `build_release.py`. Run `export_source.py` to create
   the source ZIP and a fresh, isolated `github-ready/OpenSmash-Mod-Manager-*`
   directory. It does not include the local work area's history or private files.
5. Rebuild from the source ZIP with the pinned preparation tools. Compare source
   manifests and non-EXE payload contents; compiler timestamps can change EXEs.
6. Make a local version commit in your publishing repository. On GitHub, create
   a draft release against that exact commit and tag (for example `v3.7.0`).
7. Attach all four assets from the same validated build:
   - `OpenSmash_Mod_Manager_Installer_v3.7.0.zip`
   - `OpenSmash_Mod_Manager_Installer_v3.7.0.zip.sha256`
   - `OpenSmash_Mod_Manager_Source_v3.7.0.zip`
   - `OpenSmash_Mod_Manager_Source_v3.7.0.zip.sha256`
8. Read the release notes and publish when ready. Corresponding 7-Zip source is
   inside the attached manager source ZIP. Do not offer only the installer or
   assume GitHub's auto-generated source archive contains local release assets.

Do not attach game files, local generated DLLs/objects, copyrighted mod packs,
test downloads, personal logs, credentials or Windows font files. The installer
already contains its required private runtime and licenses. Do not replace it
with the entire game directory.

This process does not publish automatically or sign Windows binaries. Configure
signing separately if you have a legitimate signing identity; do not present
checksums as a publisher signature.

GitHub's [release documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
describes draft releases and attaching binary assets.
