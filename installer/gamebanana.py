"""Read-only public GameBanana API v11 client. No HTML browser or remote code."""

import contextlib, hashlib, html, ipaddress, json, re, socket, sqlite3, threading, time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urljoin
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.error import HTTPError, URLError

API = "https://gamebanana.com/apiv11/"
GAME = 6498
SORTS = {
    "newest": "Generic_Newest",
    "updated": "Generic_LatestUpdated",
    "downloads": "Generic_MostDownloaded",
    "likes": "Generic_MostLiked",
}
MAX_DOWNLOAD = 2 * 1024**3


class ServiceError(ValueError):
    pass


class Cancelled(Exception):
    pass


def checkpoint(cancel):
    if cancel and cancel():
        raise Cancelled("Netzwerkvorgang abgebrochen.")


def pause(seconds, cancel=None):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        checkpoint(cancel)
        time.sleep(min(0.05, max(0, end - time.monotonic())))


def safe_url(url, kind="api", resolve=True):
    p = urlsplit(str(url))
    host = (p.hostname or "").lower()
    allowed = (
        host == "gamebanana.com"
        if kind == "api"
        else (
            host == "images.gamebanana.com"
            if kind == "image"
            else host in ("gamebanana.com", "files.gamebanana.com")
            or bool(re.fullmatch(r"filecache[0-9]{1,3}\.gamebanana\.com", host))
        )
    )
    if (
        p.scheme != "https"
        or not allowed
        or p.username
        or p.password
        or p.port not in (None, 443)
        or p.fragment
        or "\\" in url
        or any(ord(c) < 32 for c in url)
    ):
        raise ServiceError(
            "Unsicheres oder unbekanntes Download-/API-Ziel. Bitte die offizielle Quellseite verwenden."
        )
    if kind == "api" and not p.path.startswith("/apiv11/"):
        raise ServiceError("Unbekannter API-Pfad.")
    if resolve:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or any(
            not ipaddress.ip_address(a[4][0]).is_global for a in addresses
        ):
            raise ServiceError("Nicht oeffentliches Netzwerkziel wurde blockiert.")
    return url


class Redirects(HTTPRedirectHandler):
    def __init__(self, kind):
        self.kind = kind

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        count = getattr(req, "redirect_count", 0) + 1
        if count > 5:
            raise ServiceError("Zu viele Weiterleitungen.")
        url = safe_url(urljoin(req.full_url, newurl), self.kind)
        result = super().redirect_request(req, fp, code, msg, headers, url)
        if result:
            result.redirect_count = count
        return result


def open_url(url, kind="api", timeout=20):
    safe_url(url, kind)
    return build_opener(Redirects(kind)).open(
        Request(
            url,
            headers={
                "User-Agent": "OpenSmashModManager/3.7 (+public read-only client)",
                "Accept": "application/json" if kind == "api" else "*/*",
                "Accept-Encoding": "identity",
            },
        ),
        timeout=timeout,
    )


class Plain(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "iframe", "object"):
            self.hidden += 1
        if tag in ("p", "br", "div", "li", "h1", "h2", "h3", "tr") and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "iframe", "object") and self.hidden:
            self.hidden -= 1
        if tag in ("p", "div", "li") and not self.hidden:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain(value, limit=60000):
    parser = Plain()
    parser.feed(str(value or "")[: limit * 3])
    return re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", "".join(parser.parts)).strip()[:limit]


def integer(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def identity(model, number):
    if model not in ("Mod", "Sound") or not 0 < integer(number) < 100000000:
        raise ServiceError("Ungueltige GameBanana-ID.")
    return model, int(number)


def source_url(model, number):
    model, number = identity(model, number)
    return (
        "https://gamebanana.com/"
        + ("mods/" if model == "Mod" else "sounds/")
        + str(number)
    )


def images(data, original=False):
    result = []
    for item in (data.get("_aPreviewMedia") or {}).get("_aImages", [])[:24]:
        for key in (
            ("_sFile", "_sFile530", "_sFile220")
            if original
            else ("_sFile220", "_sFile530", "_sFile")
        ):
            if item.get(key):
                url = (
                    str(item.get("_sBaseUrl", "")).rstrip("/")
                    + "/"
                    + str(item[key]).lstrip("/")
                )
                try:
                    safe_url(url, "image", False)
                    result.append(url)
                except ValueError:
                    pass
                break
    return result


def summary(data, model, scoped=False):
    model, number = identity(data.get("_sModelName", model), data.get("_idRow"))
    game = data.get("_aGame") or {}
    if (game and integer(game.get("_idRow")) != GAME) or (not scoped and not game):
        raise ServiceError("Eintrag gehoert nicht zu Super Smash Bros. Ultimate.")
    previews = images(data)
    return dict(
        model=model,
        id=number,
        title=plain(data.get("_sName"), 500),
        author=plain((data.get("_aSubmitter") or {}).get("_sName"), 200),
        category=plain(
            (data.get("_aCategory") or data.get("_aRootCategory") or {}).get("_sName"),
            200,
        ),
        likes=data.get("_nLikeCount"),
        downloads=data.get("_nDownloadCount"),
        updated=integer(data.get("_tsDateUpdated") or data.get("_tsDateModified")),
        version=plain(data.get("_sVersion"), 200),
        source_url=source_url(model, number),
        images=images(data, True),
        thumbnail=previews[0] if previews else None,
        compatibility="Unknown",
        evidence="Katalogeintrag: Dateistruktur und Spielverhalten noch nicht geprueft.",
    )


class Client:
    def __init__(self, folder, transport=None, cancel=None, rate=1):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.transport = transport or open_url
        self.cancel = cancel
        self.rate = rate
        if self.folder.is_symlink() or self.folder.is_junction():
            raise ServiceError("Netzwerkcache darf keine Verknuepfung sein.")
        with self.db() as db:
            db.executescript(
                "CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY,created REAL,body TEXT); CREATE TABLE IF NOT EXISTS gate(id INTEGER PRIMARY KEY,next REAL); INSERT OR IGNORE INTO gate VALUES(1,0);"
            )

    @contextlib.contextmanager
    def db(self):
        db = sqlite3.connect(self.folder / "network.sqlite", timeout=20)
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def gate(self):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            now = time.time()
            at = max(now, db.execute("SELECT next FROM gate WHERE id=1").fetchone()[0])
            db.execute("UPDATE gate SET next=? WHERE id=1", (at + self.rate,))
        pause(max(0, at - time.time()), self.cancel)

    def json(self, path, params=None, ttl=300, force=False):
        url = API + path + ("?" + urlencode(params) if params else "")
        safe_url(url, resolve=False)
        key = hashlib.sha256(url.encode()).hexdigest()
        with self.db() as db:
            row = db.execute(
                "SELECT created,body FROM cache WHERE key=?", (key,)
            ).fetchone()
        if row and not force and time.time() - row[0] < ttl:
            return json.loads(row[1])
        for attempt in range(3):
            checkpoint(self.cancel)
            self.gate()
            try:
                with self.transport(url) as response:
                    raw = response.read(8 * 1024**2 + 1)
                    if len(raw) > 8 * 1024**2:
                        raise ServiceError("API-Antwort ist zu gross.")
                    data = json.loads(raw)
                if path.endswith("/SubCategories") and isinstance(data, list):
                    data = {"_aRecords": data}
                if not isinstance(data, dict) or "_aErrorCodes" in data:
                    raise ServiceError(
                        "GameBanana konnte die Anfrage nicht ausfuehren."
                    )
                with self.db() as db:
                    db.execute(
                        "INSERT OR REPLACE INTO cache VALUES(?,?,?)",
                        (key, time.time(), json.dumps(data)),
                    )
                return data
            except HTTPError as exc:
                if exc.code in (401, 403):
                    raise ServiceError(
                        "GameBanana verlangt Anmeldung oder erlaubt diesen Zugriff nicht. Bitte die Quellseite oeffnen."
                    ) from exc
                if exc.code == 429:
                    delay = retry_after(exc.headers.get("Retry-After"))
                    with self.db() as db:
                        db.execute(
                            "UPDATE gate SET next=max(next,?) WHERE id=1",
                            (time.time() + delay,),
                        )
                    if attempt < 2 and delay <= 30:
                        pause(delay, self.cancel)
                        continue
                    raise ServiceError(
                        "GameBanana-Anfragelimit erreicht. Spaeter erneut versuchen (Wartezeit: %d s)."
                        % delay
                    ) from exc
                if exc.code >= 500 and attempt < 2:
                    pause(2**attempt, self.cancel)
                    continue
                raise ServiceError(
                    "GameBanana HTTP "
                    + str(exc.code)
                    + ". Bitte spaeter erneut versuchen oder Quellseite oeffnen."
                ) from exc
            except (URLError, TimeoutError, ConnectionError, OSError) as exc:
                if attempt < 2:
                    pause(2**attempt, self.cancel)
                    continue
                raise ServiceError(
                    "Netzwerkverbindung unterbrochen oder Zeitlimit erreicht: "
                    + str(exc)
                ) from exc
            except (json.JSONDecodeError, UnicodeError) as exc:
                raise ServiceError(
                    "Unerwartete API-Antwort; keine Daten ausgefuehrt."
                ) from exc

    def config(self):
        game = self.json("Game/6498/ProfilePage", ttl=86400)
        cats = [dict(id=0, name="Alle Mods", model="Mod")]
        for row in game.get("_aModRootCategories", []):
            number = integer(row.get("_idRow"))
            if number:
                cats.append(
                    dict(id=number, name=plain(row.get("_sName"), 200), model="Mod")
                )
        cats.append(dict(id=0, name="Audio", model="Sound"))
        sort = {}
        for model in ("Mod", "Sound"):
            available = {
                s["_sAlias"]
                for s in self.json(model + "/ListFilterConfig", ttl=86400).get(
                    "_aSorts", []
                )
            }
            sort[model] = [key for key, value in SORTS.items() if value in available]
        skins = next(
            (c["id"] for c in cats if c["name"] == "Skins" and c["model"] == "Mod"), 0
        )
        characters = []
        if skins:
            children = self.json(f"ModCategory/{skins}/SubCategories", ttl=86400)
            rows = children.get("_aRecords", [children] if "_sUrl" in children else [])
            for child in rows[:512]:
                match = re.fullmatch(
                    r"https://gamebanana\.com/mods/cats/([1-9][0-9]{0,7})",
                    str(child.get("_sUrl", "")),
                )
                if match:
                    characters.append(
                        dict(
                            id=int(match[1]),
                            name=plain(child.get("_sName"), 150),
                            count=integer(child.get("_nItemCount")),
                        )
                    )
        return dict(
            categories=cats,
            sorts=sort,
            skin_category=skins,
            characters=sorted(characters, key=lambda c: c["name"].casefold()),
        )

    def browse(
        self, query="", model="Mod", category=0, sort="newest", page=1, character=0
    ):
        identity(model, 1)
        page = integer(page)
        if page < 1 or page > 10000:
            raise ServiceError("Ungueltige Ergebnisseite.")
        query = str(query).strip()[:200]
        character = integer(character)
        if character:
            config = self.config()
            if (
                model != "Mod"
                or integer(category) not in (0, config.get("skin_category"))
                or not any(c["id"] == character for c in config.get("characters", []))
            ):
                raise ServiceError(
                    "Dieser Charakterfilter ist keine verfuegbare SSBU-Skin-Kategorie."
                )
            if query:
                raise ServiceError(
                    "Textsuche und Charakterkatalog sind getrennte API-Abfragen. Suchtext zuerst leeren."
                )
        if query:
            data = self.json(
                "Util/Search/Results",
                dict(
                    _sSearchString=query,
                    _idGameRow=GAME,
                    _sModelName=model,
                    _nPage=page,
                ),
            )
            ordering = "relevance"
        else:
            if sort not in self.config()["sorts"][model]:
                raise ServiceError("Sortierung von der API nicht unterstuetzt.")
            params = {
                "_aFilters[Generic_Game]": GAME,
                "_sSort": SORTS[sort],
                "_nPage": page,
                "_nPerpage": 15,
            }
            if character:
                params["_aFilters[Generic_Category]"] = character
            elif integer(category):
                if model != "Mod" or not any(
                    c["id"] == integer(category) and c["model"] == model
                    for c in self.config()["categories"]
                ):
                    raise ServiceError("Unbekannte Kategorie.")
                params["_aFilters[Generic_Category]"] = int(category)
            data = self.json(model + "/Index", params)
            ordering = sort
        records = []
        for row in data.get("_aRecords", []):
            try:
                records.append(summary(row, model, scoped=True))
            except ServiceError:
                continue
        meta = data.get("_aMetadata") or {}
        perpage = max(1, integer(meta.get("_nPerpage"), 15))
        total = integer(meta.get("_nRecordCount"))
        return dict(
            items=records,
            page=page,
            total=total,
            perpage=perpage,
            has_next=page * perpage < total,
            ordering=ordering,
            query=query,
            character=character,
        )

    def detail(self, model, number, force=False):
        model, number = identity(model, number)
        data = self.json(f"{model}/{number}/ProfilePage", ttl=300, force=force)
        result = summary(data, model)
        blocked = any(
            data.get(k) for k in ("_bIsPrivate", "_bIsTrashed", "_bIsWithheld")
        )
        requirements = [
            dict(name=plain(row[0], 200), url=str(row[1])[:2000])
            for row in data.get("_aRequirements", [])[:64]
            if isinstance(row, list)
            and len(row) >= 2
            and isinstance(row[0], str)
            and isinstance(row[1], str)
        ]
        result.update(
            requirements=requirements,
            description=plain(data.get("_sText")),
            dependencies=plain(
                data.get("_sDependencies")
                or data.get("_aDependencies")
                or "\n".join(row["name"] + " – " + row["url"] for row in requirements)
                or "Keine strukturierten Abhaengigkeiten von der API geliefert. Beschreibung und beiliegende Anleitung pruefen."
            ),
            instructions=plain(
                data.get("_sInstallationInstructions")
                or "Archiv nach Download im Manager pruefen. Hinweise und benoetigte Plugins in der Beschreibung beachten."
            ),
            files=[],
            restricted=blocked,
        )
        for f in data.get("_aFiles", [])[:256]:
            fileid = integer(f.get("_idRow"))
            name = plain(f.get("_sFile"), 250)
            size = integer(f.get("_nFilesize"))
            checksum = str(f.get("_sMd5Checksum", "")).lower()
            reason = ""
            if blocked:
                reason = "Zugriff vom Anbieter eingeschraenkt."
            elif not 0 < size <= MAX_DOWNLOAD:
                reason = "Unbekannte oder zu grosse Datei (maximal 2 GiB)."
            elif f.get("_sAvResult") not in (None, "", "clean") or f.get(
                "_sAnalysisResult"
            ) not in (None, "", "ok"):
                reason = (
                    "Anbieterpruefung meldet ein Problem; direkter Download gesperrt."
                )
            if not fileid:
                continue
            installable = Path(name).suffix.lower() in (".zip", ".rar", ".7z")
            install_reason = (
                ""
                if installable
                else "Download im Manager moeglich. Dieses Dateiformat muss anschliessend manuell verarbeitet werden."
            )
            result["files"].append(
                dict(
                    id=fileid,
                    name=name,
                    size=size,
                    md5=checksum if re.fullmatch("[0-9a-f]{32}", checksum) else None,
                    date=integer(f.get("_tsDateAdded")),
                    version=plain(f.get("_sVersion") or result["version"], 200),
                    description=plain(f.get("_sDescription"), 3000),
                    archived=bool(f.get("_bIsArchived")),
                    download_url="https://gamebanana.com/dl/" + str(fileid),
                    supported=not reason and installable,
                    downloadable=not reason,
                    reason=reason or install_reason,
                )
            )
        return result

    def thumbnail(self, url, full=False):
        safe_url(url, "image", False)
        key = hashlib.sha256(url.encode()).hexdigest()
        folder = self.folder / ("full-images" if full else "images")
        folder.mkdir(exist_ok=True)
        path = folder / (key + ".png")
        if (
            folder.is_symlink()
            or folder.is_junction()
            or path.is_symlink()
            or path.is_junction()
        ):
            raise ServiceError("Verknuepfung im Bildcache wurde blockiert.")
        if path.exists() and path.stat().st_size:
            return str(path)
        # Fetch only on visible row requests. Never let WPF decode remote content.
        from PIL import Image
        import io, warnings

        limit = (16 if full else 8) * 1024**2
        with self.transport(url, "image") as response:
            raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ServiceError("Vorschaubild zu gross.")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.width * image.height > 20000000:
                    raise ServiceError("Vorschaubild hat zu viele Pixel.")
                import os, uuid

                image.thumbnail((4096, 4096) if full else (720, 440))
                temporary = path.with_name(key + "-" + uuid.uuid4().hex + ".tmp")
                try:
                    image.convert("RGBA").save(temporary, format="PNG")
                    os.replace(temporary, path)
                finally:
                    temporary.unlink(missing_ok=True)
        # Bounded rebuildable cache. Never enumerate/delete outside this owned folder.
        entries = sorted(
            (
                p
                for p in folder.glob("*.png")
                if re.fullmatch("[0-9a-f]{64}\\.png", p.name) and not p.is_symlink()
            ),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        used = 0
        for index, old in enumerate(entries):
            used += old.stat().st_size
            if old != path and (index >= 500 or used > 256 * 1024**2):
                old.unlink(missing_ok=True)
        return str(path)


def retry_after(value):
    if str(value or "").isdigit():
        return min(86400, max(1, int(value)))
    try:
        import email.utils, datetime

        return min(
            86400,
            max(
                1,
                int(
                    (
                        email.utils.parsedate_to_datetime(value)
                        - datetime.datetime.now(datetime.timezone.utc)
                    ).total_seconds()
                ),
            ),
        )
    except (TypeError, ValueError, OverflowError):
        return 30
