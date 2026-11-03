"""Persistent two-stream download queue; shared existing archive/import validator."""

import contextlib, concurrent.futures, hashlib, json, os, re, shutil, sqlite3, threading, time, uuid
from pathlib import Path
from types import SimpleNamespace
import gamebanana as gb

APP = "OpenSmash-Downloads-v1"
TERMINAL = {"downloaded", "failed", "cancelled", "interrupted"}


class Queue:
    def __init__(self, repo, client=None):
        self.repo = Path(repo)
        self.root = self.repo / "opensmash_mods"
        self.folder = self.root / "downloads"
        if self.root.is_symlink() or self.root.is_junction():
            raise ValueError("Manager-Ordner ist eine Verknuepfung.")
        self.folder.mkdir(exist_ok=True)
        if self.folder.is_symlink() or self.folder.is_junction():
            raise ValueError("Download-Ordner ist eine Verknuepfung.")
        self.client = client or gb.Client(self.root / "network-cache")
        with self.db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,body TEXT)")

    @contextlib.contextmanager
    def db(self):
        db = sqlite3.connect(self.folder / "queue.sqlite", timeout=20)
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def jobs(self):
        with self.db() as db:
            rows = db.execute(
                "SELECT body FROM jobs ORDER BY rowid DESC LIMIT 1024"
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def get(self, key):
        if not re.fullmatch("[0-9a-f]{32}", str(key)):
            raise ValueError("Ungueltige Download-ID.")
        with self.db() as db:
            row = db.execute("SELECT body FROM jobs WHERE id=?", (key,)).fetchone()
        if not row:
            raise ValueError("Download nicht gefunden.")
        return json.loads(row[0])

    def update(self, key, **values):
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM jobs WHERE id=?", (key,)).fetchone()
            if not row:
                raise ValueError("Download nicht gefunden.")
            job = json.loads(row[0])
            job.update(values)
            db.execute("UPDATE jobs SET body=? WHERE id=?", (json.dumps(job), key))
        return job

    def enqueue(self, model, submission, fileid):
        detail = self.client.detail(model, submission, force=True)
        match = [f for f in detail["files"] if f["id"] == gb.integer(fileid)]
        if len(match) != 1:
            raise ValueError(
                "Die ausgewaehlte Dateivariante wird nicht mehr angeboten. Bitte erneut oeffnen."
            )
        file = match[0]
        if not file.get("downloadable", file["supported"]):
            raise ValueError(file["reason"] + " " + detail["source_url"])
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT count(*) FROM jobs").fetchone()[0] >= 1024:
                raise ValueError(
                    "Downloadliste voll (1024 Eintraege). Archivierte Downloadliste vor weiteren Auftraegen sichern/leeren."
                )
            for row in db.execute("SELECT body FROM jobs"):
                job = json.loads(row[0])
                if (
                    job["model"] == model
                    and job["submission"] == int(submission)
                    and job["file"]["id"] == file["id"]
                    and job["status"] not in ("failed", "cancelled", "interrupted")
                ):
                    return job
            key = uuid.uuid4().hex
            job = dict(
                app=APP,
                id=key,
                model=model,
                submission=int(submission),
                title=detail["title"],
                author=detail["author"],
                source_url=detail["source_url"],
                file=file,
                status="queued",
                bytes=0,
                total=file["size"],
                speed=0,
                cancel=False,
                created=time.time(),
                message="Wartet auf Download",
                compatibility="Unknown",
                evidence="Archiv noch nicht untersucht.",
                thumbnail=detail.get("thumbnail"),
                requirements=detail.get("requirements", []),
            )
            db.execute("INSERT INTO jobs VALUES(?,?)", (key, json.dumps(job)))
        return job

    def control(self, key, action):
        job = self.get(key)
        if action == "cancel":
            if job["status"] == "queued":
                return self.update(
                    key, cancel=True, status="cancelled", speed=0, message="Abgebrochen"
                )
            if job["status"] in ("downloading", "verifying"):
                return self.update(key, cancel=True, message="Abbruch angefordert")
            return job
        if action == "retry" and job["status"] in (
            "failed",
            "cancelled",
            "interrupted",
        ):
            return self.update(
                key,
                cancel=False,
                status="queued",
                bytes=0,
                speed=0,
                message="Wartet auf erneuten Download",
            )
        raise ValueError("Dieser Download kann gerade nicht erneut gestartet werden.")

    def paths(self, key, filename):
        suffix = Path(filename).suffix.lower()
        if not re.fullmatch("[0-9a-f]{32}", str(key)):
            raise ValueError("Ungueltiger Download-Dateipfad.")
        if suffix not in (".zip", ".rar", ".7z"):
            suffix = ".file"  # download-only data is never given an executable suffix
        return self.folder / (key + suffix + ".part"), self.folder / (key + suffix)

    def remove(self, ids):
        """Remove terminal jobs and only their owned cached archives, never mods.

        Hold the database write lock while moving files so retry/cancel workers
        cannot race the state check. Roll back the moves if the transaction fails.
        Import previews use their own snapshots and remain valid.
        """
        if not isinstance(ids, list) or not ids or len(ids) > 1024:
            raise ValueError("Bitte fertige Downloads zum Entfernen auswaehlen.")
        ids = list(dict.fromkeys(ids))
        if any(not re.fullmatch("[0-9a-f]{32}", str(key)) for key in ids):
            raise ValueError("Ungueltige Download-ID.")
        moved = []
        try:
            with self.db() as db:
                db.execute("BEGIN IMMEDIATE")
                for key in ids:
                    row = db.execute(
                        "SELECT body FROM jobs WHERE id=?", (key,)
                    ).fetchone()
                    if not row:
                        raise ValueError("Download nicht mehr vorhanden.")
                    job = json.loads(row[0])
                    if job["status"] not in TERMINAL:
                        raise ValueError("Laufende Downloads zuerst abbrechen.")
                    for path in self.paths(key, job["file"]["name"]):
                        if (
                            path.is_symlink()
                            or path.is_junction()
                            or (path.exists() and not path.is_file())
                        ):
                            raise ValueError(
                                "Unsichere Download-Datei; nichts entfernt."
                            )
                        if path.exists():
                            trash = self.folder / ("discard-" + uuid.uuid4().hex)
                            path.rename(trash)
                            moved.append((path, trash))
                    db.execute("DELETE FROM jobs WHERE id=?", (key,))
        except BaseException:
            for original, trash in reversed(moved):
                trash.rename(original)
            raise
        for original, trash in moved:
            trash.unlink(missing_ok=True)
        return dict(items=self.jobs(), removed=len(ids))

    def cancelled(self, key):
        try:
            return bool(self.get(key).get("cancel"))
        except ValueError:
            return True

    def purge(self, key):
        """Finish a requested clear only after a transfer has closed its files."""
        try:
            job = self.get(key)
        except ValueError:
            return True
        if job.get("delete_after_cancel") and job["status"] in TERMINAL:
            try:
                self.remove([key])
            except ValueError as exc:
                try:
                    self.update(key, message=str(exc))
                except ValueError:
                    pass
                return False
            return True
        return False

    def clear(self):
        ids = [job["id"] for job in self.jobs()]
        for key in ids:
            try:
                job = self.get(key)
                values = dict(
                    cancel=True, delete_after_cancel=True, message="Wird entfernt…"
                )
                if job["status"] == "queued":
                    values["status"] = "cancelled"
                self.update(key, **values)
            except ValueError:
                pass  # another clearing worker may already have removed the row
        with self.worker_lock() as acquired:
            if acquired:
                # No transfer owns this queue. Recover abandoned active rows.
                for job in self.jobs():
                    if job["id"] in ids and job["status"] not in TERMINAL:
                        self.update(job["id"], status="cancelled", speed=0)
        for key in ids:
            self.purge(key)
        remaining = self.jobs()
        pending = sum(job["id"] in ids for job in remaining)
        return dict(items=remaining, removed=len(ids) - pending, pending=pending)

    def save(self, key, destination):
        """Explicit Save As; data is copied and verified, never opened/executed."""
        import modmanager as m

        destination = Path(destination).resolve()
        if any(
            destination.is_relative_to(folder.resolve())
            for folder in (
                self.repo,
                m.base.build_dir(self.repo),
                Path(__file__).parent,
            )
        ):
            raise ValueError(
                "Datei ausserhalb der verwalteten Spiel-/Programmdateien speichern."
            )
        job = self.get(key)
        if (
            job["status"] != "downloaded"
            or not destination.parent.is_dir()
            or destination.is_symlink()
            or destination.is_junction()
        ):
            raise ValueError(
                "Bitte einen abgeschlossenen Download und einen echten Zielordner waehlen."
            )
        _, source = self.paths(key, job["file"]["name"])
        temporary = destination.with_name(".download-" + uuid.uuid4().hex + ".tmp")
        sha = hashlib.sha256()
        try:
            with source.open("rb") as incoming, temporary.open("xb") as output:
                while block := incoming.read(1024 * 1024):
                    sha.update(block)
                    output.write(block)
            if sha.hexdigest() != job["sha256"]:
                raise ValueError(
                    "Download wurde extern veraendert; nichts gespeichert."
                )
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return dict(path=str(destination))

    def transfer(self, key, external_cancel=None):
        try:
            job = self.get(key)
        except ValueError:
            # A cancelled queued job can be removed just before the worker starts.
            return
        if job["status"] != "queued":
            return
        temporary, final = self.paths(key, job["file"]["name"])
        cancel = lambda: self.cancelled(key) or bool(
            external_cancel and external_cancel()
        )
        try:
            gb.checkpoint(cancel)
            # Revalidate current provider metadata; no saved arbitrary URL is trusted.
            current = self.client.detail(job["model"], job["submission"], force=True)
            files = [f for f in current["files"] if f["id"] == job["file"]["id"]]
            if len(files) != 1 or not files[0].get(
                "downloadable", files[0]["supported"]
            ):
                raise ValueError(
                    "Datei nicht mehr fuer direkten Download verfuegbar. Bitte Quellseite pruefen."
                )
            file = files[0]
            if file["size"] != job["file"]["size"] or file["md5"] != job["file"]["md5"]:
                raise ValueError(
                    "Anbieterdatei wurde geaendert. Variante erneut auswaehlen."
                )
            for attempt in range(3):
                gb.checkpoint(cancel)
                temporary.unlink(missing_ok=True)
                self.update(
                    key,
                    status="downloading",
                    bytes=0,
                    speed=0,
                    message="Download laeuft",
                    attempt=attempt + 1,
                )
                try:
                    with self.client.transport(
                        file["download_url"], "download"
                    ) as response, temporary.open("xb") as out:
                        length = response.headers.get("Content-Length")
                        if length and (
                            not length.isdigit() or int(length) != file["size"]
                        ):
                            raise ValueError(
                                "Downloadgroesse weicht von der API-Datei ab."
                            )
                        start = last = time.monotonic()
                        count = 0
                        md5 = hashlib.md5()
                        sha = hashlib.sha256()
                        while True:
                            gb.checkpoint(cancel)
                            block = response.read(256 * 1024)
                            if not block:
                                break
                            count += len(block)
                            if count > file["size"] or count > gb.MAX_DOWNLOAD:
                                raise ValueError(
                                    "Download ueberschreitet die erlaubte Dateigroesse."
                                )
                            out.write(block)
                            md5.update(block)
                            sha.update(block)
                            now = time.monotonic()
                            if now - last > 0.2:
                                self.update(
                                    key,
                                    bytes=count,
                                    speed=count / max(0.1, now - start),
                                )
                                last = now
                        out.flush()
                        os.fsync(out.fileno())
                    if count != file["size"]:
                        raise ConnectionError("Download wurde vorzeitig beendet.")
                    if file["md5"] and md5.hexdigest() != file["md5"]:
                        raise ValueError(
                            "Anbieter-Pruefsumme stimmt nicht. Datei verworfen."
                        )
                    break
                except gb.HTTPError as exc:
                    if exc.code == 429:
                        wait = gb.retry_after(exc.headers.get("Retry-After"))
                        if attempt < 2 and wait <= 30:
                            gb.pause(wait, cancel)
                            continue
                    if exc.code >= 500 and attempt < 2:
                        gb.pause(2**attempt, cancel)
                        continue
                    raise ValueError(
                        "Download HTTP "
                        + str(exc.code)
                        + ". Zugriff nicht umgangen; Quellseite pruefen."
                    ) from exc
                except (gb.URLError, TimeoutError, ConnectionError, OSError) as exc:
                    if attempt < 2:
                        gb.pause(2**attempt, cancel)
                        continue
                    raise ValueError(
                        "Download unterbrochen. Erneut versuchen: " + str(exc)
                    ) from exc
            self.update(
                key,
                status="verifying",
                bytes=count,
                speed=0,
                message="Archiv und OpenSmash-Struktur werden geprueft",
            )
            os.replace(temporary, final)
            if file["supported"]:
                compatibility, evidence = self.inspect(final, key, cancel)
            else:
                compatibility, evidence = (
                    "DownloadOnly",
                    "Datei heruntergeladen und auf Integritaet geprueft. Keine automatische Installation fuer dieses Format; ueber Datei speichern ablegen.",
                )
            gb.checkpoint(cancel)
            origin = dict(
                thumbnail=job.get("thumbnail"),
                requirements=job.get("requirements", []),
                provider="GameBanana",
                model=job["model"],
                submission_id=job["submission"],
                file_id=file["id"],
                file_name=file["name"],
                version=file["version"],
                file_date=file["date"],
                download_date=time.time(),
                author=job["author"],
                source_url=job["source_url"],
                md5=file["md5"],
                sha256=sha.hexdigest(),
            )
            self.update(
                key,
                status="downloaded",
                path=str(final),
                sha256=sha.hexdigest(),
                origin=origin,
                compatibility=compatibility,
                evidence=evidence,
                message=(
                    "Geprueft. Installation separat bestaetigen."
                    if file["supported"]
                    else evidence
                ),
                finished=time.time(),
            )
        except (gb.Cancelled, Exception) as exc:
            cancelled = cancel() or isinstance(exc, gb.Cancelled)
            temporary.unlink(missing_ok=True)
            final.unlink(missing_ok=True)
            try:
                self.update(
                    key,
                    status="cancelled" if cancelled else "failed",
                    speed=0,
                    message="Abgebrochen" if cancelled else str(exc),
                )
            except ValueError:
                if any(job["id"] == key for job in self.jobs()):
                    raise
        finally:
            self.purge(key)

    def inspect(self, path, key, cancel):
        import batch_import, modmanager as m

        scratch = self.folder / ("inspect-" + key)
        if scratch.exists():
            self.cleanup(scratch)
        try:
            batch_import.extract(SimpleNamespace(**vars(m)), path, scratch, cancel)
            roots = batch_import.roots(m, scratch, cancel)
            reports = []
            for root in roots:
                gb.checkpoint(cancel)
                record = m.analyze(self.repo, root)
                kinds = sorted({e.get("kind", "asset") for e in record["entries"]})
                reports.append(record["name"] + ": " + ", ".join(kinds))
            return (
                "Experimental",
                "Dateistruktur durch bestehenden OpenSmash-Importer geprueft; nicht im Spiel verifiziert. "
                + "; ".join(reports)[:2500],
            )
        except (batch_import.Cancelled, gb.Cancelled):
            raise gb.Cancelled("Abgebrochen")
        except Exception as exc:
            # Archive integrity/safety failures must never become installable files.
            self.update(
                key,
                compatibility="Unsupported",
                evidence="Konkrete Archiv-/Importer-Pruefung fehlgeschlagen: "
                + str(exc),
            )
            raise ValueError(
                "Archiv/Kompatibilitaet nicht akzeptiert: " + str(exc)
            ) from exc
        finally:
            if scratch.exists():
                self.cleanup(scratch)

    def cleanup(self, path):
        if (
            path.resolve().parent != self.folder.resolve()
            or path.is_symlink()
            or path.is_junction()
            or not re.fullmatch("inspect-[0-9a-f]{32}", path.name)
        ):
            raise ValueError("Unsicherer temporaerer Pfad.")
        shutil.rmtree(path)

    @contextlib.contextmanager
    def worker_lock(self):
        stream = (self.folder / "worker.lock").open("a+b")
        try:
            stream.seek(0)
            stream.write(b"1")
            stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                try:
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    yield False
                    return
            else:
                import fcntl

                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    yield False
                    return
            try:
                yield True
            finally:
                if os.name == "nt":
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            stream.close()

    def run(self):
        with self.worker_lock() as acquired:
            if not acquired:
                return dict(running=True)
            for job in self.jobs():
                if job["status"] in ("downloading", "verifying"):
                    part, final = self.paths(job["id"], job["file"]["name"])
                    part.unlink(missing_ok=True)
                    final.unlink(missing_ok=True)
                    self.update(
                        job["id"],
                        status="interrupted",
                        speed=0,
                        message="Vorheriger Download wurde unterbrochen. Erneut versuchen.",
                    )
                if self.purge(job["id"]):
                    continue
                scratch = self.folder / ("inspect-" + job["id"])
                if scratch.exists():
                    self.cleanup(scratch)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                pending = {}
                while True:
                    for future in list(pending):
                        if future.done():
                            future.result()
                            del pending[future]
                    ids = set(pending.values())
                    queued = [
                        j
                        for j in reversed(self.jobs())
                        if j["status"] == "queued" and j["id"] not in ids
                    ]
                    for job in queued[: max(0, 2 - len(pending))]:
                        pending[pool.submit(self.transfer, job["id"])] = job["id"]
                    if not pending:
                        return dict(running=False)
                    time.sleep(0.1)

    def preview(self, ids, callback=None, cancel=None):
        import modmanager as m, batch_import

        if not isinstance(ids, list) or not ids or len(ids) > 1024:
            raise ValueError("Bitte abgeschlossene Downloads auswaehlen.")
        jobs = [self.get(key) for key in dict.fromkeys(ids)]
        sources = []
        origins = {}
        for job in jobs:
            if job["status"] != "downloaded":
                raise ValueError("Download ist noch nicht abgeschlossen.")
            if Path(job["file"]["name"]).suffix.lower() not in (".zip", ".rar", ".7z"):
                raise ValueError(
                    "Dieses Format zuerst ueber Datei speichern ablegen und manuell verarbeiten."
                )
            _, path = self.paths(job["id"], job["file"]["name"])
            if m.base.digest(path) != job["sha256"]:
                raise ValueError(
                    "Download wurde extern geaendert. Erneut herunterladen."
                )
            sources.append(str(path))
            origins[str(path.resolve())] = job["origin"]
        result = m.batch_preview(self.repo, sources, callback, cancel)
        folder = batch_import.path(m, self.repo, result["job_id"])
        plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
        for item in plan["items"]:
            if "record" in item:
                item["origin"] = origins.get(str(Path(item["source"]).resolve()))
                item.update(
                    compatibility="Experimental",
                    evidence="Importstruktur geprueft; Spielverhalten nicht bestaetigt.",
                )
        m.base.write_json(folder / "plan.json", plan)
        result["token"] = m.base.digest(folder / "plan.json")
        result["items"] = [batch_import.public(i) for i in plan["items"]]
        return result


def updates(repo, client):
    import modmanager as m

    result = []
    for row in m.listing(repo)["mods"]:
        origin = row.get("origin") or {}
        if origin.get("provider") != "GameBanana":
            continue
        try:
            detail = client.detail(origin["model"], origin["submission_id"], force=True)
            same = next(
                (f for f in detail["files"] if f["id"] == origin.get("file_id")), None
            )
            newer = [
                f
                for f in detail["files"]
                if f["id"] != origin.get("file_id")
                and f["date"] > origin.get("file_date", 0)
            ]
            changed = bool(
                same
                and origin.get("md5")
                and same["md5"]
                and origin["md5"] != same["md5"]
            )
            result.append(
                dict(
                    id=row["id"],
                    name=row["name"],
                    model=origin["model"],
                    submission_id=origin["submission_id"],
                    source_url=detail["source_url"],
                    status=(
                        "Dateiauswahl pruefen"
                        if newer or changed
                        else (
                            "Installierte Datei nicht mehr angeboten"
                            if not same
                            else "Keine neuere Anbieterdatei"
                        )
                    ),
                    candidates=newer,
                    changed=changed,
                    message="Neue Dateivarianten sind kein Nachweis einer kompatiblen Aktualisierung. Gewuenschte Variante pruefen; Ersetzen separat bestaetigen.",
                )
            )
        except Exception as exc:
            result.append(
                dict(
                    id=row["id"],
                    name=row["name"],
                    status="Pruefung fehlgeschlagen",
                    message=str(exc),
                )
            )
    return dict(items=result)
