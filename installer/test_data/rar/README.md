# RAR test fixtures

These archives contain original synthetic bytes, not game or mod assets.
`fixtures.json` records their SHA-256 hashes; `create_rar_fixtures.py` explains
their creation. Regenerating RAR5 fixtures needs a separately licensed RAR encoder,
which is not bundled or required to run tests.

Some fixtures intentionally contain unsafe paths, links, encryption or corruption
to test rejection. Do not extract them into a real game or personal folder.
