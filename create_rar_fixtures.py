"""Generate owned archives once; tests never need a system WinRAR installation."""

import hashlib, io, json, shutil, struct, subprocess, tempfile, zipfile, zlib
from pathlib import Path

w = Path(__file__).resolve().parent
out = w / "installer/test_data/rar"
out.mkdir(parents=True, exist_ok=True)
(w / "test-scratch").mkdir(exist_ok=True)
rar = Path(r"C:\Program Files\WinRAR\Rar.exe")


def pack(name, files, *options):
    if name == "volumes.rar":
        for old in out.glob("volumes*.rar"):
            assert old.resolve().parent == out.resolve()
            old.unlink()
    with tempfile.TemporaryDirectory(dir=w / "test-scratch") as tmp:
        tmp = Path(tmp)
        for name_, data in files.items():
            p = tmp / name_
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        subprocess.run(
            [
                str(rar),
                "a",
                "-ma5",
                "-m3",
                "-idq",
                "-r",
                "-ep1",
                "-o+",
                *options,
                str(out / name),
                "*",
            ],
            cwd=tmp,
            check=True,
            timeout=30,
        )


def rar4(name, files, host=2, attributes=0x20):
    def block(kind, flags, body):
        value = struct.pack("<BHH", kind, flags, 7 + len(body)) + body
        return struct.pack("<H", zlib.crc32(value) & 0xFFFF) + value

    data = b"Rar!\x1a\x07\x00" + block(0x73, 0, b"\0" * 6)
    for path, content in files.items():
        filename = path.encode("ascii")
        body = (
            struct.pack(
                "<IIBIIBBHI",
                len(content),
                len(content),
                host,
                zlib.crc32(content),
                0,
                20,
                0x30,
                len(filename),
                attributes,
            )
            + filename
        )
        data += block(0x74, 0x8000, body) + content
    (out / name).write_bytes(data + block(0x7B, 0, b""))


single = {"Any Skin/ui/replace/a.bntx": b"own RAR fixture"}
rar4("rar4-stored.rar", single)
pack("rar5-compressed.rar", single)
pack("ui-skin-b.rar", {"Skin B/ui/replace/b.bntx": b"B"})
pack(
    "rar5-solid.rar",
    {
        "Bundle/ultimate/mods/First/ui/replace/a.bntx": b"first content" * 6000,
        "Bundle/ultimate/mods/Second/ui/replace/b.bntx": b"second content" * 6000,
    },
    "-s",
)
pack(
    "rar5-unicode.rar",
    {"Package/ultimate/mods/Uebung ü/sound/bank/test.nus3audio": b"own audio"},
)
stream = io.BytesIO()
with zipfile.ZipFile(stream, "w") as z:
    z.writestr("Audio/sound/bank/new.nus3audio", b"new audio")
pack("rar5-nested-zip.rar", {"Package/inner.zip": stream.getvalue()})
pack(
    "rar5-nested-rar.rar",
    {"Package/inner.rar": (out / "rar5-compressed.rar").read_bytes()},
)
pack("encrypted.rar", single, "-pOwnTestPassword")
pack("encrypted-headers.rar", single, "-hpOwnTestPassword")
pack(
    "volumes.rar",
    {"Any Skin/ui/replace/a.bntx": bytes(range(256)) * 200},
    "-m0",
    "-v10k",
)
rar4("traversal.rar", {"../outside.txt": b"unsafe"})
rar4("duplicate.rar", {"Mod/ui/A": b"1", "Mod/ui/a": b"2"})
rar4("collision.rar", {"Mod/ui/a": b"1", "Mod/ui/a/file": b"2"})
rar4("ads.rar", {"Mod/ui/a:stream": b"unsafe"})
rar4("reserved.rar", {"Mod/ui/CON.txt": b"unsafe"})
rar4("symlink.rar", {"Mod/ui/link": b"../../outside"}, host=3, attributes=0o120777)
rar4("corrupt-data.rar", single)
p = out / "corrupt-data.rar"
data = p.read_bytes()
p.write_bytes(data.replace(b"own RAR fixture", b"bad RAR fixture"))
manifest = {
    p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("*.rar")
}
(out / "fixtures.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest, indent=2))
