"""Small, rebuildable cover cache outside mod/profile contents and identities."""

import io
import os
import re
import uuid
import warnings
from pathlib import Path

COVER_NAMES = (
    "preview.png",
    "thumbnail.png",
    "cover.png",
    "preview.jpg",
    "thumbnail.jpg",
    "cover.jpg",
    "preview.webp",
    "cover.webp",
)


def cover_path(repo, key):
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,79}", str(key)):
        raise ValueError("Ungueltige Mod-ID fuer Titelbild.")
    folder = Path(repo) / "opensmash_mods/previews"
    if folder.is_symlink() or folder.is_junction():
        raise ValueError("Titelbildcache darf keine Verknuepfung sein.")
    target = folder / (key + ".png")
    if target.is_symlink() or target.is_junction():
        raise ValueError("Verknuepftes Titelbild wurde blockiert.")
    return target


def cached(repo, key):
    try:
        target = cover_path(repo, key)
        return str(target) if target.is_file() and target.stat().st_size else None
    except (OSError, ValueError):
        return None


def set_cover(repo, key, source):
    from PIL import Image

    target = cover_path(repo, key)
    source = Path(source)
    if (
        source.is_symlink()
        or source.is_junction()
        or not source.is_file()
        or source.stat().st_size > 8 * 1024**2
    ):
        raise ValueError("Bitte ein echtes Bild bis 8 MiB auswaehlen.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(source.read_bytes())) as image:
            if image.width * image.height > 20_000_000:
                raise ValueError("Titelbild hat zu viele Pixel.")
            image.thumbnail((480, 270))
            converted = image.convert("RGBA")
    target.parent.mkdir(exist_ok=True)
    temporary = target.with_name(uuid.uuid4().hex + ".tmp")
    try:
        converted.save(temporary, format="PNG")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return str(target)


def capture(repo, key, source):
    """A cover is optional; a broken image must not reject a valid mod."""
    existing = cached(repo, key)
    if existing:
        return existing
    for name in COVER_NAMES:
        candidate = Path(source) / name
        if candidate.is_file():
            try:
                return set_cover(repo, key, candidate)
            except Exception:
                # Invalid optional artwork never rejects an otherwise valid mod.
                pass
    return None


def populate(repo, client, ids, callback=None):
    import modmanager as m

    state = m.load(repo)
    if not isinstance(ids, list) or len(ids) > 1024:
        raise ValueError("Ungueltige Titelbildauswahl.")
    details = {}
    result = []
    for key in dict.fromkeys(ids):
        if key not in state["mods"]:
            continue
        path = cached(repo, key)
        if not path:
            try:
                record = m.metadata(repo, key, verify=False)
                path = capture(repo, key, m.catalog.location(repo, key) / "assets")
                origin = record.get("origin") or {}
                if not path and origin.get("provider") == "GameBanana":
                    identity = (origin["model"], origin["submission_id"])
                    if origin.get("thumbnail"):
                        path = set_cover(
                            repo, key, client.thumbnail(origin["thumbnail"])
                        )
                    if path:
                        detail = {}
                    elif identity not in details:
                        details[identity] = client.detail(*identity)
                    detail = details.get(identity, {})
                    if detail.get("thumbnail"):
                        path = set_cover(
                            repo, key, client.thumbnail(detail["thumbnail"])
                        )
            except Exception:
                path = None
        row = dict(id=key, path=path)
        result.append(row)
        if callback:
            callback(dict(event="library-image", **row))
    return dict(items=result)
