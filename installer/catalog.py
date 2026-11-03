"""Local metadata/validation cache. JSON mod records and state remain authoritative."""

import contextlib, hashlib, json, os, re, sqlite3, stat, time
from pathlib import Path
import drybowser as base


@contextlib.contextmanager
def database(repo):
    root = repo / "opensmash_mods"
    root.mkdir(exist_ok=True)
    db = sqlite3.connect(root / "index.sqlite", timeout=10)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute(
            "CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY, location TEXT NOT NULL, stamp TEXT, body TEXT)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, stamp TEXT NOT NULL, sha TEXT NOT NULL)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS deployments(signature TEXT PRIMARY KEY, location TEXT NOT NULL)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS runtimes(signature TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS summaries(id TEXT PRIMARY KEY,body TEXT NOT NULL)"
        )
        yield db
        db.commit()
    finally:
        db.close()


def stamp(path):
    s = path.stat()
    return json.dumps(
        [s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_ino], separators=(",", ":")
    )


def relative(repo, path):
    return path.resolve().relative_to((repo / "opensmash_mods").resolve()).as_posix()


def located(repo, location):
    return base.contained(repo / "opensmash_mods", repo / "opensmash_mods" / location)


def pattern(prefix):
    return prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def location(repo, key):
    direct = repo / "opensmash_mods/library" / key
    if direct.exists():
        return direct
    with database(repo) as db:
        row = db.execute("SELECT location FROM records WHERE id=?", (key,)).fetchone()
    if row and located(repo, row[0]).is_dir():
        return located(repo, row[0])
    # Rebuildable cache: rollback records survive a lost index.
    rollback = repo / "opensmash_mods/rollback"
    if rollback.exists():
        for p in sorted(rollback.glob(key + "-*"), reverse=True):
            if (p / "mod.json").is_file():
                return p
    return direct


def record(repo, key):
    folder = location(repo, key)
    file = folder / "mod.json"
    current = stamp(file)
    rel = relative(repo, folder)
    with database(repo) as db:
        row = db.execute(
            "SELECT stamp,body,location FROM records WHERE id=?", (key,)
        ).fetchone()
        if row and row[0] == current and row[2] == rel:
            return json.loads(row[1])
        data = json.loads(file.read_text(encoding="utf-8-sig"))
        db.execute(
            "INSERT OR REPLACE INTO records VALUES(?,?,?,?)",
            (key, rel, current, json.dumps(data, ensure_ascii=False)),
        )
    return data


def costume_slots(record):
    result = set()
    for entry in record["entries"]:
        path = entry["path"].lower()
        match = re.match(r"fighter/([^/]+)/.*?/(c[0-9]{2,})(?:/|$)", path)
        if match:
            result.add(match[1] + "/" + match[2])
    return sorted(result)


def summaries(repo, rows):
    """Derived, rebuildable state/source/health/conflict metadata, no file rescans."""
    with database(repo) as db:
        for row in rows:
            body = json.dumps(row, ensure_ascii=False, sort_keys=True)
            old = db.execute(
                "SELECT body FROM summaries WHERE id=?", (row["id"],)
            ).fetchone()
            if not old or old[0] != body:
                db.execute(
                    "INSERT OR REPLACE INTO summaries VALUES(?,?)", (row["id"], body)
                )


def relocate(repo, key, path):
    with database(repo) as db:
        db.execute(
            "UPDATE records SET location=?,stamp=NULL WHERE id=?",
            (relative(repo, path), key),
        )


def walk(folder):
    if folder.is_symlink() or folder.is_junction():
        raise ValueError("Verknuepfung im verwalteten Dateibaum.")
    if not folder.exists():
        return
    queue = [folder]
    while queue:
        current = queue.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                p = Path(entry.path)
                s = entry.stat(follow_symlinks=False)
                if entry.is_symlink() or getattr(s, "st_file_attributes", 0) & 1024:
                    raise ValueError("Verknuepfung im verwalteten Dateibaum: " + str(p))
                if stat.S_ISDIR(s.st_mode):
                    queue.append(p)
                elif stat.S_ISREG(s.st_mode):
                    yield p
                else:
                    raise ValueError("Spezialdatei im verwalteten Dateibaum: " + str(p))


def validate(repo, folder, expected, force=False):
    prefix = relative(repo, folder) + "/"
    with database(repo) as db:
        cached = {
            p: (s, h)
            for p, s, h in db.execute(
                "SELECT path,stamp,sha FROM files WHERE path LIKE ? ESCAPE '\\'",
                (pattern(prefix),),
            )
        }
        found = {}
        updates = []
        for file in walk(folder):
            name = file.relative_to(folder).as_posix()
            key = prefix + name
            current = stamp(file)
            old = cached.get(key)
            sha = (
                old[1] if old and old[0] == current and not force else base.digest(file)
            )
            if current != stamp(file):
                raise ValueError("Datei aendert sich waehrend der Pruefung: " + name)
            found[name] = sha
            if not old or old != (current, sha):
                updates.append((key, current, sha))
        if found != expected:
            raise ValueError(
                "Verwaltete Dateien wurden extern veraendert: " + str(folder)
            )
        db.executemany("INSERT OR REPLACE INTO files VALUES(?,?,?)", updates)
    return found


def seed(repo, folder, expected):
    with database(repo) as db:
        db.executemany(
            "INSERT OR REPLACE INTO files VALUES(?,?,?)",
            [
                (relative(repo, folder / name), stamp(folder / name), sha)
                for name, sha in expected.items()
            ],
        )


def moved(repo, source, destination):
    old = relative(repo, source).rstrip("/") + "/"
    new = relative(repo, destination).rstrip("/") + "/"
    with database(repo) as db:
        rows = list(
            db.execute(
                "SELECT path,stamp,sha FROM files WHERE path LIKE ? ESCAPE '\\'",
                (pattern(old),),
            )
        )
        db.execute("DELETE FROM files WHERE path LIKE ? ESCAPE '\\'", (pattern(old),))
        db.executemany(
            "INSERT OR REPLACE INTO files VALUES(?,?,?)",
            [(new + p[len(old) :], s, h) for p, s, h in rows],
        )


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def digest(repo, file, force=False):
    key = "@external/" + str(file.resolve())
    current = stamp(file)
    with database(repo) as db:
        row = db.execute("SELECT stamp,sha FROM files WHERE path=?", (key,)).fetchone()
        sha = row[1] if row and row[0] == current and not force else base.digest(file)
        if stamp(file) != current:
            raise ValueError("Datei wurde waehrend der Pruefung veraendert.")
        if not row or row != (current, sha):
            db.execute(
                "INSERT OR REPLACE INTO files VALUES(?,?,?)", (key, current, sha)
            )
    return sha


def deployment(repo, key, path=None):
    with database(repo) as db:
        if path is not None:
            db.execute(
                "INSERT OR REPLACE INTO deployments VALUES(?,?)",
                (key, relative(repo, path)),
            )
            return
        row = db.execute(
            "SELECT location FROM deployments WHERE signature=?", (key,)
        ).fetchone()
    if row:
        p = located(repo, row[0])
        if p.is_dir():
            return p


def runtime(repo, key, value=None):
    with database(repo) as db:
        if value is not None:
            db.execute(
                "INSERT OR REPLACE INTO runtimes VALUES(?,?)", (key, json.dumps(value))
            )
            return value
        row = db.execute(
            "SELECT body FROM runtimes WHERE signature=?", (key,)
        ).fetchone()
    return json.loads(row[0]) if row else None
