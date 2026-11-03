"""Strict public identifiers only. Link URLs never become arbitrary download URLs."""

import re
from urllib.parse import urlsplit

SCHEME = "opensmashmm"


def parse(value):
    if (
        not isinstance(value, str)
        or not 0 < len(value) <= 2048
        or any(ord(c) < 32 for c in value)
        or any(c in value for c in ('"', "'", "\\", "\x7f"))
    ):
        raise ValueError("Ungueltiger GameBanana-Link.")
    if value.startswith("fightplanner:"):
        value = "opensmashmm:" + value[len("fightplanner:") :]
    match = re.fullmatch(
        r"opensmashmm:https://gamebanana\.com/(?:mmdl|dl)/([1-9][0-9]{0,7}),(Mod|Sound),([1-9][0-9]{0,7}),(zip|rar|7z)",
        value,
    )
    if match:
        return dict(
            file_id=int(match[1]), model=match[2], id=int(match[3]), extension=match[4]
        )
    match = re.fullmatch(
        r"opensmashmm://gamebanana/(Mod|Sound)/([1-9][0-9]{0,7})\?file=([1-9][0-9]{0,7})",
        value,
    )
    if match:
        return dict(model=match[1], id=int(match[2]), file_id=int(match[3]))
    url = urlsplit(value)
    if (
        url.scheme == "https"
        and url.hostname == "gamebanana.com"
        and not url.username
        and not url.password
        and url.port in (None, 443)
    ):
        match = re.fullmatch(r"/(mods|sounds)/([1-9][0-9]{0,7})/?", url.path)
        if match:
            return dict(
                model="Mod" if match[1] == "mods" else "Sound", id=int(match[2])
            )
    raise ValueError(
        "Bitte eine GameBanana-Mod-/Soundseite oder einen opensmashmm-Link verwenden. Ein direkter Download-Link ohne Mod-Zuordnung reicht nicht aus."
    )


def make(model, submission, fileid, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    value = f"{SCHEME}:https://gamebanana.com/mmdl/{fileid},{model},{submission},{extension}"
    parse(value)
    return value


def accept(queue, value):
    request = parse(value)
    if "file_id" not in request:
        return dict(mode="detail", **request)
    detail = queue.client.detail(request["model"], request["id"], force=True)
    files = [f for f in detail["files"] if f["id"] == request["file_id"]]
    if not files:
        raise ValueError(
            "Die verlinkte Datei gehoert nicht zu dieser SSBU-Mod oder ist nicht mehr verfuegbar."
        )
    if request.get("extension") and not files[0]["name"].lower().endswith(
        "." + request["extension"]
    ):
        raise ValueError(
            "Verlinktes Archivformat stimmt nicht mit der Anbieterdatei ueberein."
        )
    return dict(
        mode="queued",
        job=queue.enqueue(request["model"], request["id"], request["file_id"]),
    )
