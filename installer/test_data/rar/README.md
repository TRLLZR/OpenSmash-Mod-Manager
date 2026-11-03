# RAR test fixtures

These archives contain original synthetic strings/patterns written for this
project. They do not contain Nintendo assets, real mod contents or a RAR encoder.
Game-like extensions are used only to exercise the manager's structural importer.

`fixtures.json` records SHA-256 hashes. `create_rar_fixtures.py` at the repository
root documents how the bytes were created. Stored RAR4 fixtures use a small
original header writer; RAR5 fixtures were encoded using a separately installed
RAR tool. That encoder is not bundled and is not needed to run tests. Regenerating
RAR5 fixtures requires obtaining an encoder under its own applicable terms.

Some fixtures intentionally contain unsafe paths, links, collisions, encryption,
corruption or multiple volumes. They test safe rejection. Do not extract them
with an arbitrary system tool into a real game or personal directory.
