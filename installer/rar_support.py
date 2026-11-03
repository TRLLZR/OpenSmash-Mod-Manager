"""Stream official UnRAR into manager-owned files; never delegate path extraction."""

import contextlib, ctypes as c, hashlib, stat
from pathlib import Path

DLL_SHA256 = "894b7d2db8d6363eb12f30c7b89f48eab9e71963b8b438675bdd64c12dd59bcc"
MAX_DICT_KIB = 512 * 1024
U = c.c_uint32
P = c.c_void_p
W = c.c_wchar_p
Callback = getattr(c, "WINFUNCTYPE", c.CFUNCTYPE)(
    c.c_int, U, c.c_ssize_t, c.c_ssize_t, c.c_ssize_t
)


class OpenData(c.Structure):
    _pack_ = 1
    _fields_ = [
        ("ArcName", c.c_char_p),
        ("ArcNameW", W),
        ("OpenMode", U),
        ("OpenResult", U),
        ("CmtBuf", c.c_char_p),
        ("CmtBufSize", U),
        ("CmtSize", U),
        ("CmtState", U),
        ("Flags", U),
        ("Callback", Callback),
        ("UserData", c.c_ssize_t),
        ("OpFlags", U),
        ("CmtBufW", W),
        ("MarkOfTheWeb", W),
        ("Reserved", U * 23),
    ]


class Header(c.Structure):
    _pack_ = 1
    _fields_ = [
        ("ArcName", c.c_char * 1024),
        ("ArcNameW", c.c_wchar * 1024),
        ("FileName", c.c_char * 1024),
        ("FileNameW", c.c_wchar * 1024),
        *[
            (n, U)
            for n in (
                "Flags",
                "PackSize",
                "PackSizeHigh",
                "UnpSize",
                "UnpSizeHigh",
                "HostOS",
                "FileCRC",
                "FileTime",
                "UnpVer",
                "Method",
                "FileAttr",
            )
        ],
        ("CmtBuf", c.c_char_p),
        *[
            (n, U)
            for n in ("CmtBufSize", "CmtSize", "CmtState", "DictSize", "HashType")
        ],
        ("Hash", c.c_ubyte * 32),
        ("RedirType", U),
        ("RedirName", W),
        *[
            (n, U)
            for n in (
                "RedirNameSize",
                "DirTarget",
                "MtimeLow",
                "MtimeHigh",
                "CtimeLow",
                "CtimeHigh",
                "AtimeLow",
                "AtimeHigh",
            )
        ],
        ("ArcNameEx", W),
        ("ArcNameExSize", U),
        ("FileNameEx", W),
        ("FileNameExSize", U),
        ("Reserved", U * 982),
    ]


_dll = None


def library():
    global _dll
    if _dll is None:
        path = Path(__file__).with_name("UnRAR64.dll")
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != DLL_SHA256
        ):
            raise ValueError(
                "Die mitgelieferte RAR-Laufzeit fehlt oder wurde veraendert. Manager bitte neu installieren."
            )
        dll = c.WinDLL(str(path.resolve()), winmode=0x1100)
        for name, args, result in [
            ("RAROpenArchiveEx", [c.POINTER(OpenData)], P),
            ("RARReadHeaderEx", [P, c.POINTER(Header)], c.c_int),
            ("RARProcessFileW", [P, c.c_int, W, W], c.c_int),
            ("RARCloseArchive", [P], c.c_int),
        ]:
            function = getattr(dll, name)
            function.argtypes = args
            function.restype = result
        _dll = dll
    return _dll


def error(code):
    messages = {
        11: "Nicht genug Arbeitsspeicher fuer RAR.",
        12: "RAR-Datei beschaedigt oder Pruefsumme falsch.",
        13: "Keine gueltige RAR-Datei.",
        14: "RAR-Format nicht unterstuetzt.",
        15: "RAR-Datei kann nicht geoeffnet werden.",
        18: "RAR-Datei kann nicht vollstaendig gelesen werden.",
        22: "Passwortgeschuetzte RAR-Dateien bitte vorher entpacken.",
        24: "Passwortgeschuetzte RAR-Dateien bitte vorher entpacken.",
        25: "RAR-Kompressionswoerterbuch ist zu gross (maximal 512 MiB).",
    }
    return ValueError(
        messages.get(code, "RAR konnte nicht gelesen werden (Code %d)." % code)
    )


class Archive:
    def __init__(self, source, mode, cancel):
        self.dll = library()
        self.handle = None
        self.writer = None
        self.remaining = 0
        self.failure = None
        self.cancel = cancel
        self.callback = Callback(self.receive)
        data = OpenData()
        data.ArcNameW = str(source)
        data.OpenMode = mode
        data.Callback = self.callback
        self.handle = self.dll.RAROpenArchiveEx(c.byref(data))
        try:
            self.check(data.OpenResult)
            if not self.handle:
                raise error(13)
            if data.Flags & 1:
                raise ValueError(
                    "Mehrteilige RAR-Dateien bitte zuerst vollstaendig entpacken."
                )
            if data.Flags & 128:
                raise error(22)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.handle:
            self.dll.RARCloseArchive(self.handle)
            self.handle = None

    def check(self, code):
        if self.failure:
            raise self.failure
        if code:
            raise error(code)

    def receive(self, msg, user, pointer, length):
        try:
            from batch_import import checkpoint

            checkpoint(self.cancel)
            if msg in (0, 3):
                raise ValueError(
                    "Mehrteilige RAR-Dateien bitte zuerst vollstaendig entpacken."
                )
            if msg in (2, 4):
                raise error(22)
            if msg == 5:
                return 1 if 0 < pointer <= MAX_DICT_KIB else -1
            if msg == 1:
                if self.writer is None or length < 0 or length > self.remaining:
                    raise ValueError(
                        "RAR-Dateigroesse stimmt nicht mit dem Verzeichnis ueberein."
                    )
                self.remaining -= length
                for offset in range(0, length, 1024 * 1024):
                    checkpoint(self.cancel)
                    self.writer.write(
                        c.string_at(pointer + offset, min(1024 * 1024, length - offset))
                    )
            return 1
        except Exception as exc:
            self.failure = exc
            return -1

    def read(self):
        from batch_import import checkpoint, safe_name

        checkpoint(self.cancel)
        header = Header()
        buffer = c.create_unicode_buffer(32768)
        header.FileNameEx = c.cast(buffer, W)
        header.FileNameExSize = len(buffer)
        result = self.dll.RARReadHeaderEx(self.handle, c.byref(header))
        if result == 10:
            return None
        self.check(result)
        if header.Flags & 3:
            raise ValueError(
                "Mehrteilige RAR-Dateien bitte zuerst vollstaendig entpacken."
            )
        if header.Flags & 4:
            raise error(22)
        if (
            header.RedirType
            or (header.HostOS == 2 and header.FileAttr & 0x400)
            or (
                header.HostOS == 3
                and stat.S_IFMT(header.FileAttr) not in (0, stat.S_IFREG, stat.S_IFDIR)
            )
        ):
            raise ValueError(
                "Verknuepfungen und Spezialdateien im RAR werden nicht importiert."
            )
        if header.DictSize > MAX_DICT_KIB:
            raise error(25)
        return dict(
            name=safe_name(buffer.value or header.FileNameW),
            size=header.UnpSize + (header.UnpSizeHigh << 32),
            directory=bool(header.Flags & 32),
            crc=header.FileCRC,
            hash_type=header.HashType,
            hash=bytes(header.Hash),
        )

    def process(self, operation):
        self.check(self.dll.RARProcessFileW(self.handle, operation, None, None))


def extract(m, source, target, cancel, budget):
    from batch_import import checkpoint, validate_entries, MAX_FILES, MAX_BYTES

    entries = []
    size = 0
    with contextlib.closing(Archive(source, 0, cancel)) as archive:
        while (entry := archive.read()) is not None:
            entries.append(entry)
            size += entry["size"]
            if len(entries) > MAX_FILES or size > MAX_BYTES:
                raise ValueError(
                    "RAR ueberschreitet die Importgrenze (64000 Eintraege / 8 GiB)."
                )
            archive.process(0)
    validate_entries([(e["name"], e["size"], e["directory"]) for e in entries], budget)
    target.mkdir()
    with contextlib.closing(Archive(source, 1, cancel)) as archive:
        for expected in entries:
            checkpoint(cancel)
            if archive.read() != expected:
                raise ValueError("RAR-Datei hat sich waehrend des Imports geaendert.")
            destination = m.base.contained(target, target / expected["name"])
            if expected["directory"]:
                destination.mkdir(parents=True, exist_ok=True)
                archive.process(0)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as output:
                    archive.writer = output
                    archive.remaining = expected["size"]
                    archive.process(1)
                    archive.writer = None
                    if archive.remaining:
                        raise ValueError(
                            "RAR-Datei ist unvollstaendig: " + expected["name"]
                        )
        if archive.read() is not None:
            raise ValueError("RAR-Datei hat sich waehrend des Imports geaendert.")
