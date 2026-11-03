"""Portable download recipes: provider identities and hashes, never mod assets.

Import is an explicit user action. Existing selections are immutable; missing
items use the normal validated download and transactional batch-import paths.
"""

import concurrent.futures
import hashlib
import json
import os
import re
import time
import uuid
from pathlib import Path

import batch_import as batch

APP = "OpenSmash-ModList-v1"
MAX_JSON = 2 * 1024**2


def identity(record):
    return hashlib.sha256(
        json.dumps(sorted(batch.signature(record)), separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def source_record(origin):
    if not isinstance(origin, dict) or origin.get("provider") != "GameBanana":
        return None
    model = origin.get("model")
    ids = [origin.get(k) for k in ("submission_id", "file_id")]
    sha = origin.get("sha256")
    if model not in ("Mod", "Sound") or any(
        type(n) is not int or not 0 < n <= 2**53 for n in ids
    ):
        raise ValueError("Ungueltige GameBanana-Dateiidentitaet in der Modliste.")
    if not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{64}", sha):
        return None
    return dict(
        provider="GameBanana",
        model=model,
        submission_id=ids[0],
        file_id=ids[1],
        sha256=sha,
    )


def export(m, repo, destination):
    destination = Path(destination).resolve()
    if destination.suffix.lower() != ".json" or not destination.parent.is_dir():
        raise ValueError("Bitte eine JSON-Datei in einem vorhandenen Ordner waehlen.")
    if destination.is_relative_to(m.root(repo)) or destination.is_relative_to(
        m.base.build_dir(repo)
    ):
        raise ValueError("Modliste ausserhalb der verwalteten Spieldateien speichern.")
    state = m.load(repo)
    if not 0 < len(state["mods"]) <= batch.MAX_ITEMS:
        raise ValueError("Eine Modliste benoetigt 1 bis 1024 installierte Mods.")
    mods = []
    for key, status in state["mods"].items():
        record = m.metadata(repo, key, verify=False)
        mods.append(
            dict(
                name=status["name"],
                signature=identity(record),
                enabled=status["enabled"],
                source=source_record(record.get("origin")),
            )
        )
    data = json.dumps(
        dict(app=APP, version=1, mods=mods), ensure_ascii=False, indent=2
    ).encode("utf-8")
    if len(data) > MAX_JSON:
        raise ValueError("Modliste ist zu gross.")
    temporary = destination.with_name(".modlist-" + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return dict(
        path=str(destination), mods=len(mods), manual=sum(not r["source"] for r in mods)
    )


def read(path, expected=None):
    path = Path(path)
    if (
        path.is_symlink()
        or path.is_junction()
        or not path.is_file()
        or path.stat().st_size > MAX_JSON
    ):
        raise ValueError("Bitte eine echte OpenSmash-Modliste bis 2 MiB waehlen.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_JSON + 1)
    if len(raw) > MAX_JSON:
        raise ValueError("Modliste ist zu gross.")
    token = hashlib.sha256(raw).hexdigest()
    if expected is not None and token != expected:
        raise ValueError(
            "Modliste wurde nach der Vorschau veraendert. Bitte erneut pruefen."
        )
    data = json.loads(raw.decode("utf-8-sig"))
    if (
        not isinstance(data, dict)
        or data.get("app") != APP
        or type(data.get("version")) is not int
        or data.get("version") != 1
    ):
        raise ValueError("Keine unterstuetzte OpenSmash-Modliste.")
    mods = data.get("mods")
    if not isinstance(mods, list) or not 0 < len(mods) <= batch.MAX_ITEMS:
        raise ValueError("Ungueltige Anzahl Mods in der Liste.")
    seen = set()
    result = []
    for row in mods:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("name"), str)
            or not 0 < len(row["name"]) <= 300
            or type(row.get("enabled")) is not bool
        ):
            raise ValueError("Ungueltiger Eintrag in der Modliste.")
        sig = row.get("signature")
        if (
            not isinstance(sig, str)
            or not re.fullmatch("[0-9a-f]{64}", sig)
            or sig in seen
        ):
            raise ValueError(
                "Ungueltige oder doppelte Inhaltsidentitaet in der Modliste."
            )
        source = row.get("source")
        if source is not None:
            normalized = source_record(source)
            if not normalized or set(source) != set(normalized):
                raise ValueError(
                    "Modlisten erlauben nur gepruefte Anbieter-IDs und SHA-256, keine Download-URLs."
                )
            source = normalized
        seen.add(sig)
        result.append(
            dict(
                name=" ".join(row["name"].split()),
                signature=sig,
                enabled=row["enabled"],
                source=source,
            )
        )
    return result, token


def preview(m, repo, path, expected=None):
    mods, token = read(path, expected)
    state = m.load(repo)
    existing = {identity(m.metadata(repo, key, verify=False)) for key in state["mods"]}
    items = []
    for index, row in enumerate(mods):
        status = (
            "existing"
            if row["signature"] in existing
            else ("ready" if row["source"] else "skipped")
        )
        message = {
            "existing": "Schon vorhanden; deine Aktivierung bleibt erhalten.",
            "ready": "Wird nach Bestaetigung heruntergeladen und installiert. Konflikte werden pausiert installiert.",
            "skipped": "Keine gespeicherte Downloadquelle. Originaldateien manuell beziehen.",
        }[status]
        items.append(dict(row, item_id=index, status=status, message=message))
    return dict(
        kind="mod-list",
        path=str(Path(path).resolve()),
        token=token,
        items=items,
        ready=sum(r["status"] == "ready" for r in items),
        existing=sum(r["status"] == "existing" for r in items),
        manual=sum(r["status"] == "skipped" for r in items),
    )


def transfer(queue, ids, callback, cancel):
    """Cooperate with the normal two-stream queue without stealing its worker."""
    while any(
        queue.get(key)["status"] in ("queued", "downloading", "verifying")
        for key in ids
    ):
        batch.checkpoint(cancel)
        with queue.worker_lock() as acquired:
            if acquired:
                pending = []
                for key in ids:
                    job = queue.get(key)
                    if job["status"] in ("downloading", "verifying"):
                        queue.update(key, status="queued")  # previous worker exited
                    if job["status"] in ("queued", "downloading", "verifying"):
                        pending.append(key)
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [
                        pool.submit(queue.transfer, key, cancel) for key in pending
                    ]
                    for future in futures:
                        future.result()
        complete = sum(
            queue.get(key)["status"] not in ("queued", "downloading", "verifying")
            for key in ids
        )
        batch.progress(callback, "list_download", complete, len(ids))
        time.sleep(0.1)


def install(m, repo, path, expected, callback=None, cancel=None, client=None):
    import downloads

    m.idle()
    plan = preview(m, repo, path, expected)
    rows = [r for r in plan["items"] if r["status"] == "ready"]
    results = [dict(r) for r in plan["items"] if r["status"] != "ready"]
    queue = downloads.Queue(repo, client)
    groups = {}
    for row in rows:
        source = row["source"]
        key = (source["model"], source["submission_id"], source["file_id"])
        group = groups.setdefault(key, dict(sha256=source["sha256"], rows=[]))
        if group["sha256"] != source["sha256"]:
            raise ValueError("Widerspruechliche Dateihashes in der Modliste.")
        group["rows"].append(row)
    jobs = {}
    completed = False
    try:
        for index, (key, group) in enumerate(groups.items()):
            batch.checkpoint(cancel)
            batch.progress(
                callback, "list_download", index, len(groups), group["rows"][0]["name"]
            )
            try:
                job = queue.enqueue(*key)
                if (
                    job["status"] == "downloaded"
                    and not queue.paths(job["id"], job["file"]["name"])[1].is_file()
                ):
                    queue.update(
                        job["id"],
                        status="queued",
                        cancel=False,
                        bytes=0,
                        message="Archivcache fehlt; wird erneut geladen.",
                    )
                jobs[job["id"]] = group
            except Exception as exc:
                results.extend(
                    dict(row, status="failed", message=str(exc))
                    for row in group["rows"]
                )
        transfer(queue, list(jobs), callback, cancel)
        batch.checkpoint(cancel)
        usable = []
        wanted = {}
        for key, group in jobs.items():
            job = queue.get(key)
            if job["status"] != "downloaded" or job.get("sha256") != group["sha256"]:
                reason = (
                    job.get("message", "Download fehlgeschlagen.")
                    if job["status"] != "downloaded"
                    else "Anbieterdatei stimmt nicht mit der geteilten Version ueberein. Keine andere Version installiert."
                )
                results.extend(
                    dict(row, status="failed", message=reason) for row in group["rows"]
                )
            else:
                usable.append(key)
                wanted.update({row["signature"]: row for row in group["rows"]})
        if usable:
            batch.checkpoint(cancel)
            imported = queue.preview(usable, callback, cancel)
            folder = batch.path(m, repo, imported["job_id"])
            document = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
            found = set()
            paused = set()
            requested_items = set()
            for item in document["items"]:
                sig = identity(item["record"]) if "record" in item else None
                row = wanted.get(sig)
                if not row:
                    if item["status"] in ("ready", "conflict"):
                        item.update(
                            status="skipped",
                            message="Nicht Bestandteil der geteilten Liste.",
                        )
                    continue
                found.add(sig)
                requested_items.add(item["item_id"])
                if item["status"] in ("ready", "conflict"):
                    enabled = row["enabled"] and not item.get("conflict_ids")
                    if row["enabled"] and not enabled:
                        paused.add(item["item_id"])
                    item.update(status="ready", enabled=bool(enabled))
            for sig in wanted.keys() - found:
                errors = "; ".join(
                    i.get("message", "")
                    for i in document["items"]
                    if i["status"] == "invalid"
                )
                now_existing = {
                    identity(m.metadata(repo, key, verify=False))
                    for key in m.load(repo)["mods"]
                }
                results.append(
                    dict(
                        wanted[sig],
                        status="existing" if sig in now_existing else "failed",
                        message=(
                            "Inzwischen vorhanden; Aktivierung bleibt erhalten."
                            if sig in now_existing
                            else (
                                errors
                                or "Gewuenschter Modinhalt ist in der angebotenen Datei nicht enthalten."
                            )
                        ),
                    )
                )
            m.base.write_json(folder / "plan.json", document)
            outcome = m.batch_install(
                repo,
                imported["job_id"],
                m.base.digest(folder / "plan.json"),
                callback,
                cancel,
            )
            for row in outcome["items"]:
                if row.get("item_id") not in requested_items:
                    continue
                if row.get("item_id") in paused and row["status"] == "installed":
                    row["message"] = (
                        "Wegen Dateikonflikt pausiert installiert. Vorhandene Mods unveraendert."
                    )
                # Extra archive members are never part of the requested recipe.
                if (
                    row["status"] != "skipped"
                    or row.get("message") != "Nicht Bestandteil der geteilten Liste."
                ):
                    results.append(row)
            if outcome.get("cancelled"):
                raise batch.Cancelled("Import abgebrochen")
        completed = True
    finally:
        if not completed:
            for key in jobs:
                if queue.get(key)["status"] in ("queued", "downloading", "verifying"):
                    queue.control(key, "cancel")
    return dict(
        installed=sum(r["status"] == "installed" for r in results),
        failed=sum(r["status"] == "failed" for r in results),
        skipped=sum(r["status"] not in ("installed", "failed") for r in results),
        items=results,
        state=m.listing(repo),
    )
