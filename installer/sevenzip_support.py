"""Bounded 7z decoding through pinned upstream 7-Zip, without path extraction.

Only decoded bytes arrive on stdout. The manager validates every destination,
size and CRC and writes its own files. One decoder pass also handles solid
archives without repeatedly decompressing the same block for each member.
"""

import ctypes as c
import hashlib
import os
import queue
import re
import subprocess
import threading
import time
import zlib
from pathlib import Path

BINARY_SHA256 = "7ddf0a3bc451e166679296be630d6f0573eb386159c04184761c43020c484291"
MAX_METADATA = 32 * 1024**2
MEMORY_LIMIT = 768 * 1024**2


def binary():
    path = Path(__file__).with_name("7za.exe")
    if (
        path.is_symlink()
        or path.is_junction()
        or not path.is_file()
        or hashlib.sha256(path.read_bytes()).hexdigest() != BINARY_SHA256
    ):
        raise ValueError(
            "Die gepruefte portable 7z-Laufzeit fehlt oder wurde veraendert."
        )
    return path


class MemoryJob:
    """Constrain the native decoder and kill it if its parent exits."""

    def __init__(self, process):
        from ctypes import wintypes as w

        class Basic(c.Structure):
            _fields_ = [
                ("process_time", c.c_int64),
                ("job_time", c.c_int64),
                ("flags", w.DWORD),
                ("min_working", c.c_size_t),
                ("max_working", c.c_size_t),
                ("active", w.DWORD),
                ("affinity", c.c_size_t),
                ("priority", w.DWORD),
                ("scheduling", w.DWORD),
            ]

        class Io(c.Structure):
            _fields_ = [
                (name, c.c_uint64)
                for name in (
                    "read_ops",
                    "write_ops",
                    "other_ops",
                    "read_bytes",
                    "write_bytes",
                    "other_bytes",
                )
            ]

        class Limits(c.Structure):
            _fields_ = [
                ("basic", Basic),
                ("io", Io),
                ("process_memory", c.c_size_t),
                ("job_memory", c.c_size_t),
                ("peak_process", c.c_size_t),
                ("peak_job", c.c_size_t),
            ]

        self.api = c.WinDLL("kernel32", use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
        self.api.CreateJobObjectW.restype = w.HANDLE
        self.api.SetInformationJobObject.argtypes = [
            w.HANDLE,
            c.c_int,
            c.c_void_p,
            w.DWORD,
        ]
        self.api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.api.CloseHandle.argtypes = [w.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        limits = Limits()
        limits.basic.flags = 0x2000 | 0x100 | 0x200  # kill on close, process/job memory
        limits.process_memory = limits.job_memory = MEMORY_LIMIT
        if (
            not self.handle
            or not self.api.SetInformationJobObject(
                self.handle, 9, c.byref(limits), c.sizeof(limits)
            )
            or not self.api.AssignProcessToJobObject(self.handle, int(process._handle))
        ):
            self.close()
            raise ValueError("7z-Speicherbegrenzung konnte nicht eingerichtet werden.")

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def chunks(arguments, limit, cancel, timeout=900):
    from batch_import import checkpoint

    process = subprocess.Popen(
        [str(binary()), *map(str, arguments)],
        cwd=Path(__file__).parent,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=0x08000000,
    )
    job = None
    blocks = queue.Queue(maxsize=8)
    stopped = threading.Event()
    errors = bytearray()

    def stdout():
        try:
            while not stopped.is_set():
                block = process.stdout.read(256 * 1024)
                while not stopped.is_set():
                    try:
                        blocks.put(block, timeout=0.1)
                        break
                    except queue.Full:
                        pass
                if not block:
                    return
        except OSError:
            pass

    def stderr():
        try:
            while block := process.stderr.read(4096):
                if len(errors) < 8192:
                    errors.extend(block[: 8192 - len(errors)])
        except OSError:
            pass

    readers = []
    try:
        job = MemoryJob(process)
        readers = [
            threading.Thread(target=stdout, daemon=True),
            threading.Thread(target=stderr, daemon=True),
        ]
        for reader in readers:
            reader.start()
        deadline = time.monotonic() + timeout
        total = 0
        while True:
            checkpoint(cancel)
            if time.monotonic() > deadline:
                raise ValueError("7z-Pruefung dauerte zu lange; sicher abgebrochen.")
            try:
                block = blocks.get(timeout=0.1)
            except queue.Empty:
                if process.poll() is not None and not readers[0].is_alive():
                    break
                continue
            if not block:
                break
            total += len(block)
            if total > limit:
                raise ValueError("7z-Ausgabe ueberschreitet die erlaubte Groesse.")
            yield block
        code = process.wait(timeout=5)
        readers[1].join(timeout=2)
        if code:
            raise ValueError(
                "7z konnte nicht gelesen werden (beschaedigt, verschluesselt oder Speichergrenze erreicht). "
                + errors.decode("utf-8", errors="replace")[:500]
            )
    finally:
        stopped.set()
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        if job:
            job.close()
        for reader in readers:
            reader.join(timeout=2)
        process.stdout.close()
        process.stderr.close()


def entries(source, cancel):
    from batch_import import safe_name, MAX_FILES

    with source.open("rb") as stream:
        if stream.read(6) != b"7z\xbc\xaf\x27\x1c":
            raise ValueError(
                "Keine gueltige 7z-Datei; selbstentpackende Programme werden nicht importiert."
            )
    data = b"".join(
        chunks(
            ["l", "-t7z", "-slt", "-ba", "-sccUTF-8", "-p-", "--", source],
            MAX_METADATA,
            cancel,
            timeout=60,
        )
    )
    text = (
        data.decode("utf-8", errors="strict")
        .replace("\r\r\n", "\n")
        .replace("\r\n", "\n")
    )
    result = []
    for paragraph in text.strip("\n").split("\n\n"):
        if not paragraph:
            continue
        record = {}
        for line in paragraph.split("\n"):
            key, separator, value = line.partition(" = ")
            if not separator or key in record:
                raise ValueError("Mehrdeutiges 7z-Dateiverzeichnis wurde abgelehnt.")
            record[key] = value
        if (
            any(
                k in record
                for k in ("Symbolic Link", "Hard Link", "Reparse", "Alternate Stream")
            )
            or record.get("Encrypted") != "-"
            or record.get("Anti") == "+"
        ):
            raise ValueError(
                "Verknuepfte oder verschluesselte 7z-Eintraege werden nicht importiert."
            )
        attributes = record.get("Attributes", "")
        if "L" in attributes.split(" ")[0] or re.search(
            r"(?:^|\s)[lcbsp][rwxstST-]{9}(?:\s|$)", attributes
        ):
            raise ValueError(
                "7z-Verknuepfungen und Spezialdateien werden nicht importiert."
            )
        directory = attributes.startswith("D") or bool(
            re.search(r"(?:^|\s)d[rwxstST-]{9}(?:\s|$)", attributes)
        )
        size = record.get("Size", "")
        crc = record.get("CRC", "")
        if (
            (directory and size != "0")
            or not size.isascii()
            or not size.isdigit()
            or len(size) > 20
            or (
                not directory
                and not (size == "0" and not crc)
                and not re.fullmatch("[0-9A-Fa-f]{8}", crc)
            )
        ):
            raise ValueError("Ungueltige 7z-Groesse oder fehlende Dateipruefsumme.")
        result.append(
            dict(
                name=safe_name(record.get("Path", "")),
                size=int(size),
                directory=directory,
                crc=int(crc, 16) if crc else 0,
            )
        )
        if len(result) > MAX_FILES:
            raise ValueError("Zu viele 7z-Eintraege.")
    return result


def extract(m, source, target, cancel, budget=None):
    from batch_import import validate_entries, checkpoint

    records = entries(Path(source), cancel)
    validate_entries([(r["name"], r["size"], r["directory"]) for r in records], budget)
    target.mkdir()
    files = [r for r in records if not r["directory"]]
    for record in records:
        if record["directory"]:
            m.base.contained(target, target / record["name"]).mkdir(
                parents=True, exist_ok=True
            )
    decoded = chunks(
        ["x", "-t7z", "-so", "-bd", "-y", "-p-", "--", source],
        sum(r["size"] for r in files),
        cancel,
    )
    pending = memoryview(b"")
    try:
        for record in files:
            checkpoint(cancel)
            destination = m.base.contained(target, target / record["name"])
            destination.parent.mkdir(parents=True, exist_ok=True)
            remaining, crc = record["size"], 0
            with destination.open("xb") as output:
                while remaining:
                    checkpoint(cancel)
                    if not pending:
                        try:
                            pending = memoryview(next(decoded))
                        except StopIteration:
                            raise ValueError(
                                "7z-Dateidaten sind abgeschnitten."
                            ) from None
                    length = min(remaining, len(pending))
                    output.write(pending[:length])
                    crc = zlib.crc32(pending[:length], crc)
                    pending = pending[length:]
                    remaining -= length
            if crc != record["crc"]:
                raise ValueError("7z-Dateipruefsumme stimmt nicht: " + record["name"])
        if pending or any(decoded):
            raise ValueError(
                "7z-Dateigroessen stimmen nicht mit dem Verzeichnis ueberein."
            )
    finally:
        decoded.close()
