"""Owned, snapshot-based import queues. No untrusted code is executed."""

import contextlib, hashlib, json, os, re, shutil, stat, time, uuid, zipfile
from pathlib import Path, PurePosixPath

APP = "OpenSmash-Batch-v1"
MAX_ITEMS = 1024
MAX_FILES = 64000
MAX_BYTES = 8 * 1024**3
ARCHIVES = {".zip", ".rar", ".7z"}


class Cancelled(Exception):
    pass


def conflicting_owners(entry, owners, records, text_conflicts):
    if entry['path'].endswith('.xmsbt'):
        return [(None, records[key]['name'], key) for key in text_conflicts.get(entry['path'], [])]
    owner = owners.get(target(entry))
    return [owner] if owner and owner[0] != entry['sha256'] else []


def checkpoint(cancel):
    if cancel and cancel():
        raise Cancelled("Import abgebrochen")


def progress(callback, phase, current=0, total=0, name="", **extra):
    if callback:
        callback(
            dict(
                event="progress",
                phase=phase,
                current=current,
                total=total,
                name=name,
                **extra
            )
        )


def safe_name(name):
    name = name.replace("\\", "/")
    if not name or name.startswith("/") or ":" in name or "\x00" in name:
        raise ValueError("Unsicherer Archiv-Pfad: " + name)
    parts = name.rstrip("/").split("/")
    # Win32 also reserves the ISO-8859-1 superscript forms COM¹/LPT¹.
    # Reject them before creating files, for ZIP, RAR and nested archives alike.
    devices = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(prefix + digit for prefix in ("COM", "LPT") for digit in "123456789¹²³"),
    }
    if any(ord(c) < 32 or c in '<>"|?*' for c in name):
        raise ValueError("Ungueltiger Windows-Pfad im Archiv: " + name)
    if any(
        p in ("", ".", "..")
        or p.rstrip(" .") != p
        or p.split(".")[0].upper() in devices
        for p in parts
    ):
        raise ValueError("Ungueltiger Windows-Pfad im Archiv: " + name)
    return "/".join(parts)


def validate_entries(entries, budget=None):
    size = sum(e[1] for e in entries)
    if budget is not None:
        budget["files"] += len(entries)
        budget["bytes"] += size
        if budget["files"] > MAX_FILES or budget["bytes"] > MAX_BYTES:
            raise ValueError(
                "Der gesamte Stapel ueberschreitet die sichere Entpackgrenze."
            )
    if len(entries) > MAX_FILES or size > MAX_BYTES:
        raise ValueError(
            "Archiv ueberschreitet die Importgrenze (64000 Eintraege / 8 GiB)."
        )
    seen = {}
    for raw, size, directory in entries:
        name = safe_name(raw).casefold()
        if name in seen:
            raise ValueError("Doppelter Archiv-Pfad: " + name)
        seen[name] = directory
    for name in seen:
        if any(
            parent in seen and not seen[parent]
            for parent in (str(p) for p in PurePosixPath(name).parents)
            if parent != "."
        ):
            raise ValueError("Datei-/Ordner-Kollision im Archiv: " + name)


def extract(m, source, target, cancel, budget=None):
    if source.suffix.lower() == ".7z":
        import sevenzip_support

        return sevenzip_support.extract(m, source, target, cancel, budget)
    if source.suffix.lower() == ".rar":
        import rar_support

        return rar_support.extract(m, source, target, cancel, budget)
    with zipfile.ZipFile(source) as z:
        infos = z.infolist()
        for entry in infos:
            mode = stat.S_IFMT(entry.external_attr >> 16)
            if mode not in (0, stat.S_IFREG, stat.S_IFDIR) or entry.flag_bits & 1:
                raise ValueError(
                    "Verknuepfte oder verschluesselte ZIP-Eintraege werden nicht unterstuetzt."
                )
        validate_entries([(i.filename, i.file_size, i.is_dir()) for i in infos], budget)
        target.mkdir()
        for entry in infos:
            checkpoint(cancel)
            destination = m.base.contained(target, target / safe_name(entry.filename))
            if entry.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with z.open(entry) as source_file, destination.open("xb") as output:
                while True:
                    checkpoint(cancel)
                    block = source_file.read(1024 * 1024)
                    if not block:
                        break
                    output.write(block)


def roots(m, source, cancel, expand=None, options=None):
    if source.name.lower() in m.ROOTS:
        raise ValueError("Bitte den Mod-Ordner ueber fighter/, ui/ usw. auswaehlen.")
    queue = [(source, 0)]
    found = []
    count = 0
    while queue:
        checkpoint(cancel)
        folder, depth = queue.pop()
        children = list(folder.iterdir())
        count += len(children)
        if options is not None:
            import library_export

            options.update(library_export.manifest(folder))
        if count > MAX_FILES:
            raise ValueError("Zu viele Dateien/Ordner in der Auswahl.")
        for p in children:
            if p.is_symlink() or p.is_junction():
                raise ValueError("Verknuepfungen werden nicht importiert: " + p.name)
        if any(
            (p.is_dir() and p.name.lower() in m.ROOTS)
            or (p.is_file() and p.suffix.lower() == ".nro")
            for p in children
        ):
            found.append(folder)
        else:
            queue.extend(
                (p, depth) for p in sorted(children, reverse=True) if p.is_dir()
            )
            if expand:
                for p in children:
                    if p.is_file() and p.suffix.lower() in ARCHIVES:
                        if depth >= 2:
                            raise ValueError(
                                "Archive sind zu tief ineinander verschachtelt (maximal 2 Ebenen)."
                            )
                        queue.append((expand(p), depth + 1))
    if not found:
        raise ValueError(
            "Keine Mod-Wurzel mit fighter/, ui/, effect/ oder sound/ gefunden."
        )
    if len(found) > MAX_ITEMS:
        raise ValueError("Maximal 1024 Mods je Stapel.")
    return sorted(found)


def path(m, repo, job_id):
    if not re.fullmatch("[0-9a-f]{32}", str(job_id)):
        raise ValueError("Ungueltige Import-ID.")
    folder = m.base.contained(
        m.root(repo) / "incoming", m.root(repo) / "incoming" / ("batch-" + job_id)
    )
    owner = json.loads((folder / "owner.json").read_text(encoding="utf-8-sig"))
    if owner.get("app") != APP:
        raise ValueError("Importauftrag gehoert nicht diesem Manager.")
    return folder


def discard(m, repo, job_id):
    folder = path(m, repo, job_id)
    if (folder / "active.lock").exists():
        raise ValueError("Importauftrag wird noch verarbeitet.")
    assert folder.resolve().parent == (m.root(repo) / "incoming").resolve()
    shutil.rmtree(folder)


def signature(record):
    # Packaging names and info.toml do not change the installed mod's behavior.
    return frozenset(
        (
            (
                ("@plugin/" + e.get("module", e["path"]))
                if e.get("kind") == "plugin"
                else e["path"]
            ),
            e["sha256"],
        )
        for e in record["entries"]
        if e["path"].lower() != "info.toml"
    )


def target(entry):
    if entry.get("kind") == "plugin":
        return "@plugin/" + entry["module"]
    return None if entry.get("metadata") else entry["path"]


def public(item):
    return {k: v for k, v in item.items() if k not in ("record", "assets_rel")}


def clear_payload(folder, keep=()):
    for child in folder.iterdir():
        if (
            child.name not in keep
            and child.name.startswith(("input-", "snapshot-"))
            and child.is_dir()
        ):
            if (
                child.is_symlink()
                or child.is_junction()
                or child.resolve().parent != folder.resolve()
            ):
                raise ValueError("Unsichere Importkopie; Bereinigung gestoppt.")
            shutil.rmtree(child)


@contextlib.contextmanager
def active(folder):
    lock = folder / "active.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError("Dieser Stapel wird bereits verarbeitet.") from exc
    os.close(fd)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def preview(m, repo, sources, callback=None, cancel=None, previous_job=None):
    if not sources or len(sources) > MAX_ITEMS:
        raise ValueError(
            "Bitte 1 bis 1024 ZIP-/RAR-/7z-Dateien oder Mod-Ordner auswaehlen."
        )
    m.load(repo)
    incoming = m.root(repo) / "incoming"
    # Only our inactive, expired jobs; never inspect or remove unrelated files.
    for old in incoming.glob("batch-*"):
        if (
            re.fullmatch("batch-[0-9a-f]{32}", old.name)
            and not (old / "active.lock").exists()
        ):
            try:
                owner = json.loads((old / "owner.json").read_text(encoding="utf-8-sig"))
                if (
                    owner.get("app") == APP
                    and time.time() - float(owner.get("created", time.time())) > 86400
                ):
                    discard(m, repo, old.name[6:])
            except (OSError, ValueError, KeyError):
                pass
    if previous_job:
        try:
            discard(m, repo, previous_job)
        except (FileNotFoundError, ValueError):
            pass
    job_id = uuid.uuid4().hex
    folder = m.base.contained(
        m.root(repo) / "incoming", m.root(repo) / "incoming" / ("batch-" + job_id)
    )
    folder.mkdir()
    m.base.write_json(folder / "owner.json", dict(app=APP, created=time.time()))
    is_cancel = lambda: (folder / "cancel.request").exists() or bool(
        cancel and cancel()
    )
    items = []
    seen_sources = set()
    seen_signatures = {}
    owners = {}
    text_records, text_roots = {}, {}
    names = set()
    slots = {}
    budget = dict(files=0, bytes=0)
    nested_count = 0

    def expand(archive):
        nonlocal nested_count
        nested_count += 1
        if nested_count > MAX_ITEMS:
            raise ValueError("Zu viele verschachtelte Archive.")
        destination = folder / ("input-nested-%03d" % nested_count)
        extract(m, archive, destination, is_cancel, budget)
        return destination

    state = m.load(repo)
    for key, status in state["mods"].items():
        record = m.metadata(repo, key, verify=False)
        seen_signatures[signature(record)] = ("existing", status["name"])
        names.add(status["name"].casefold())
        if status["enabled"]:
            text_records[key] = record
            text_roots[key] = m.catalog.location(repo, key) / 'assets'
            for slot in m.catalog.costume_slots(record):
                slots.setdefault(slot, set()).add(status["name"])
            for entry in record["entries"]:
                if target(entry):
                    owners.setdefault(
                        target(entry), (entry["sha256"], status["name"], key)
                    )
    progress(callback, "preview", 0, len(sources), job_id=job_id)
    try:
        with active(folder):
            for index, source_arg in enumerate(sources):
                checkpoint(is_cancel)
                source = Path(source_arg)
                label = source.name or str(source)
                progress(callback, "preview", index, len(sources), label, job_id=job_id)
                try:
                    if source.is_symlink() or source.is_junction():
                        raise ValueError(
                            "Bitte echte Dateien/Ordner verwenden, keine Verknuepfung."
                        )
                    source = source.resolve(strict=True)
                    canonical = os.path.normcase(str(source))
                    if canonical in seen_sources:
                        items.append(
                            dict(
                                name=label,
                                source=str(source),
                                status="duplicate",
                                message="Dieselbe Quelle wurde mehrfach ausgewaehlt.",
                            )
                        )
                        continue
                    seen_sources.add(canonical)
                    if source.is_file():
                        if source.suffix.lower() not in ARCHIVES:
                            raise ValueError(
                                "Nur ZIP-/RAR-/7z-Dateien und entpackte Mod-Ordner werden unterstuetzt."
                            )
                        unpacked = folder / ("input-%03d" % index)
                        extract(m, source, unpacked, is_cancel, budget)
                    elif source.is_dir():
                        unpacked = source
                    else:
                        raise ValueError("Quelle ist keine Datei oder kein Ordner.")
                    options = {}
                    candidates = roots(m, unpacked, is_cancel, expand, options)
                    import plugin_dependencies

                    plugin_dependencies.check_provided(
                        repo,
                        [
                            p
                            for candidate in candidates
                            for p in candidate.glob("*.nro")
                        ],
                    )
                    for mod_index, root in enumerate(candidates):
                        checkpoint(is_cancel)
                        if len(items) >= MAX_ITEMS:
                            raise ValueError("Maximal 1024 Mods je Stapel.")
                        try:
                            record = m.analyze(repo, root)
                            record.pop("assets_root")
                            import library_media

                            library_media.capture(repo, record["id"], root)
                            item = dict(
                                name=record["name"],
                                source=str(source),
                                status="ready",
                                message="",
                                files=record["count"],
                                bytes=record["bytes"],
                            )
                            option = options.get(root.resolve(), {})
                            if (
                                option
                                and {e["path"]: e["sha256"] for e in record["entries"]}
                                != option["files"]
                            ):
                                raise ValueError(
                                    "Modpaket-Pruefsummen stimmen nicht mit den Dateien ueberein."
                                )
                            item["enabled"] = option.get("enabled", True)
                            overlaps = sorted(
                                {
                                    slot + " (" + ", ".join(sorted(slots[slot])) + ")"
                                    for slot in m.catalog.costume_slots(record)
                                    if slot in slots
                                }
                            )
                            if overlaps:
                                item["slot_overlaps"] = overlaps
                            if any(
                                e.get("kind") == "plugin" for e in record["entries"]
                            ):
                                item["message"] = (
                                    "Skyline-Plugin mit Konfiguration: benoetigt einen lokalen Plugin-Build. Windows-Programme werden nicht geladen."
                                )
                            sig = signature(record)
                            if sig in seen_signatures:
                                kind, prior = seen_signatures[sig]
                                item.update(
                                    status=kind, message="Bereits vorhanden: " + prior
                                )
                                items.append(item)
                                continue
                            text_conflicts = m.moveset_support.text_patch_conflicts(
                                record, root, text_records, text_roots) if item['enabled'] else {}
                            conflicts = (
                                sorted(
                                    {
                                        owner[1]
                                        for e in record["entries"]
                                        for owner in conflicting_owners(e, owners, text_records, text_conflicts)
                                    }
                                )
                                if item["enabled"]
                                else []
                            )
                            if conflicts:
                                item.update(
                                    status="conflict",
                                    message="Konflikt mit: "
                                    + ", ".join(conflicts)
                                    + " — gleiche Ziele: "
                                    + ", ".join(
                                        sorted(
                                            {
                                                str(target(e))
                                                for e in record["entries"]
                                                if conflicting_owners(e, owners, text_records, text_conflicts)
                                            }
                                        )[:8]
                                    ),
                                    conflict_ids=sorted(
                                        {
                                            owner[2]
                                            for e in record["entries"]
                                            for owner in conflicting_owners(e, owners, text_records, text_conflicts)
                                        }
                                    ),
                                )
                            original_name = item["name"]
                            suffix = 2
                            while item["name"].casefold() in names:
                                item["name"] = original_name[:125] + " (%d)" % suffix
                                suffix += 1
                            if item["name"] != original_name:
                                item["message"] = (
                                    "Gleicher Name, anderer Inhalt: separater Eintrag "
                                    + item["name"]
                                )
                            names.add(item["name"].casefold())
                            record["name"] = item["name"]
                            if source.is_dir():
                                cached = folder / (
                                    "snapshot-%03d-%03d" % (index, mod_index)
                                )
                                cached.mkdir()
                                for entry in record["entries"]:
                                    checkpoint(is_cancel)
                                    dst = m.base.contained(
                                        cached, cached / entry["source_path"]
                                    )
                                    dst.parent.mkdir(parents=True, exist_ok=True)
                                    shutil.copy2(root / entry["source_path"], dst)
                                    if m.base.digest(dst) != entry["sha256"]:
                                        raise ValueError(
                                            "Quelle hat sich waehrend der Vorschau geaendert."
                                        )
                            else:
                                cached = root
                            item.update(
                                record=record,
                                assets_rel=cached.relative_to(folder).as_posix(),
                                compatibility="Experimental",
                                evidence="Struktur vom OpenSmash-Importer geprueft; Spielverhalten nicht verifiziert.",
                            )
                            items.append(item)
                            if overlaps:
                                item["message"] += (
                                    " Gleiche Kostuemslots: "
                                    + ", ".join(overlaps)
                                    + ". Unterschiedliche Dateien koennen kombinierbar sein; im Spiel pruefen."
                                )
                            seen_signatures[sig] = ("duplicate", item["name"])
                            if item["status"] == "ready" and item["enabled"]:
                                text_records[record['id']] = record
                                text_roots[record['id']] = cached
                                for slot in m.catalog.costume_slots(record):
                                    slots.setdefault(slot, set()).add(item["name"])
                            for entry in record["entries"]:
                                if (
                                    item["status"] == "ready"
                                    and item["enabled"]
                                    and target(entry)
                                ):
                                    owners.setdefault(
                                        target(entry),
                                        (entry["sha256"], item["name"], record["id"]),
                                    )
                        except Cancelled:
                            raise
                        except Exception as exc:
                            items.append(
                                dict(
                                    name=root.name,
                                    source=str(source),
                                    status="invalid",
                                    message=str(exc),
                                )
                            )
                except Cancelled:
                    raise
                except Exception as exc:
                    items.append(
                        dict(
                            name=label,
                            source=str(source_arg),
                            status="invalid",
                            message=str(exc),
                        )
                    )
            checkpoint(is_cancel)
    except Cancelled:
        for item in items:
            if item["status"] == "ready":
                item["status"] = "cancelled"
    for index, item in enumerate(items):
        item["item_id"] = index
    document = dict(
        app=APP, job_id=job_id, items=items, created=time.time(), cancelled=is_cancel()
    )
    m.base.write_json(folder / "plan.json", document)
    ready = sum(i["status"] == "ready" for i in items)
    keep = (
        {
            Path(i["assets_rel"]).parts[0]
            for i in items
            if i["status"] in ("ready", "conflict") and "assets_rel" in i
        }
        if not is_cancel()
        else set()
    )
    clear_payload(folder, keep)
    progress(callback, "preview_done", len(sources), len(sources), job_id=job_id)
    return dict(
        job_id=job_id,
        token=m.base.digest(folder / "plan.json"),
        items=[public(i) for i in items],
        ready=ready,
        cancelled=is_cancel(),
        total=len(items),
    )


def configure(m, repo, job_id, expected, choices):
    folder = path(m, repo, job_id)
    plan_file = folder / "plan.json"
    with active(folder):
        if (folder / "result.json").exists() or m.base.digest(plan_file) != expected:
            raise ValueError("Importvorschau ist nicht mehr aktuell.")
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
        state = m.load(repo)
        replacements = set()
        if not isinstance(choices, dict) or len(choices) > MAX_ITEMS:
            raise ValueError("Ungueltige Importauswahl.")
        for index, item in enumerate(plan["items"]):
            choice = choices.get(str(index))
            if choice is None:
                continue
            if "record" not in item or item["status"] not in (
                "ready",
                "conflict",
                "skipped",
            ):
                raise ValueError("Dieser Eintrag kann nicht installiert werden.")
            if choice == "skip":
                item.update(status="skipped", message="Von dir ausgelassen.")
                continue
            if choice == "disabled":
                item.pop("replacement_ids", None)
                item.pop("overlay_ids", None)
                item.pop("underlay_ids", None)
                item.update(
                    enabled=False,
                    status="ready",
                    message="Wird pausiert installiert; keine aktiven Dateien ersetzt.",
                )
            elif choice == "replace":
                item.pop("overlay_ids", None)
                item.pop("underlay_ids", None)
                ids = item.get("conflict_ids", [])
                if not ids or any(key not in state["mods"] for key in ids):
                    raise ValueError(
                        "Ersetzen ist nur fuer aktuell installierte Konfliktpartner moeglich. Sonst pausiert installieren."
                    )
                replacements.update(ids)
                item["replacement_ids"] = ids
                item.update(
                    enabled=True,
                    status="ready",
                    message="Konfliktpartner werden pausiert. Rueckgaengig bleibt moeglich.",
                )
            elif choice in ('overlay', 'underlay'):
                ids = item.get('conflict_ids', [])
                if not ids or any(key not in state['mods'] for key in ids):
                    raise ValueError('Ueberlagern erfordert installierte Konfliktpartner; Vorschau wiederholen.')
                others = {key: m.metadata(repo, key, verify=False) for key in ids}
                candidate = item['record']['id']
                others[candidate] = item['record']
                statuses = {key: state['mods'][key] for key in ids}
                statuses[candidate] = dict(overlays=ids if choice == 'overlay' else [])
                if choice == 'underlay':
                    for key in ids:
                        statuses[key] = dict(statuses[key], overlays=list(set(statuses[key].get('overlays', [])) | {candidate}))
                m.moveset_support.overlay_groups(others, statuses)
                item.pop('replacement_ids', None)
                item.pop('overlay_ids', None)
                item.pop('underlay_ids', None)
                item['overlay_ids' if choice == 'overlay' else 'underlay_ids'] = ids
                item.update(enabled=True, status='ready',
                            message='Dateiprioritaet und ARC-Dateiverknuepfungen des Patches gelten vor der Basis; Gameplay-Plugins bleiben aktiv. Rueckgaengig bleibt moeglich.')
            elif choice == "enable" and not item.get("conflict_ids"):
                item.update(enabled=True, status="ready")
            else:
                raise ValueError("Ungueltige Konfliktentscheidung.")
        plan["replace_ids"] = sorted(
            {
                key
                for item in plan["items"]
                if item["status"] == "ready"
                for key in item.get("replacement_ids", [])
            }
        )
        m.base.write_json(plan_file, plan)
    return dict(
        job_id=job_id,
        token=m.base.digest(plan_file),
        items=[public(i) for i in plan["items"]],
        ready=sum(i["status"] == "ready" for i in plan["items"]),
        total=len(plan["items"]),
        cancelled=False,
    )


def install(m, repo, job_id, expected=None, callback=None, cancel=None):
    folder = path(m, repo, job_id)
    plan_file = folder / "plan.json"
    if plan_file.stat().st_size > 32 * 1024**2:
        raise ValueError("Importplan ist zu gross.")
    if expected and m.base.digest(plan_file) != expected:
        raise ValueError("Importplan wurde veraendert. Bitte erneut pruefen.")
    plan = json.loads(plan_file.read_text(encoding="utf-8-sig"))
    items = plan["items"]
    if plan.get("app") != APP or plan.get("job_id") != job_id or len(items) > MAX_ITEMS:
        raise ValueError("Ungueltiger Importplan.")
    if (folder / "result.json").exists():
        raise ValueError(
            "Dieser Stapel wurde bereits abgeschlossen. Bitte neue Vorschau erstellen."
        )
    for index, item in enumerate(items):
        item["item_id"] = index
    is_cancel = lambda: (folder / "cancel.request").exists() or bool(
        cancel and cancel()
    )
    installed = 0
    cancelled = False
    prepared = []
    results = []
    created_keys = []
    ready = [i for i in items if i["status"] == "ready"]
    total = len(ready)
    m.idle()
    with active(folder), m.locked(repo):
        state = m.load(repo)
        desired = json.loads(json.dumps(state))
        for key in plan.get("replace_ids", []):
            if key not in desired["mods"]:
                raise ValueError(
                    "Zu ersetzende Mod ist nicht mehr installiert. Vorschau wiederholen."
                )
            m.metadata(repo, key)
            manifest = json.loads(
                (m.root(repo) / "profile/profile.json").read_text(encoding="utf-8")
            )
            if key in manifest.get("mods", []):
                expected_files = {
                    name[len(key) + 1 :]: sha
                    for name, sha in manifest["files"].items()
                    if name.startswith(key + "/")
                }
                m.catalog.validate(
                    repo,
                    m.root(repo)
                    / "profile"
                    / manifest.get("asset_dir", "assets")
                    / key,
                    expected_files,
                )
            desired["mods"][key]["enabled"] = False
        for item in items:
            if item["status"] != "ready":
                results.append(public(item))
        try:
            checkpoint(is_cancel)
            if ready:
                m.prepare_legacy(repo, desired)
            existing = {
                signature(m.metadata(repo, k, verify=False)) for k in desired["mods"]
            }
            owners = {}
            text_records, text_roots = {}, {}
            for key, status in desired["mods"].items():
                if status["enabled"]:
                    text_records[key] = m.metadata(repo, key, verify=False)
                    text_roots[key] = m.catalog.location(repo, key) / 'assets'
                    for entry in text_records[key]["entries"]:
                        if target(entry):
                            owners.setdefault(
                                target(entry), (entry["sha256"], status["name"], key)
                            )
            for index, item in enumerate(ready):
                checkpoint(is_cancel)
                progress(
                    callback,
                    "install",
                    index,
                    total,
                    item["name"],
                    job_id=job_id,
                    failed=sum(i["status"] == "failed" for i in results),
                )
                try:
                    record = item["record"]
                    key = record["id"]
                    if not re.fullmatch("mod-[0-9a-f]{16}", key):
                        raise ValueError("Ungueltige Mod-ID im Importplan.")
                    if key in desired["mods"] or signature(record) in existing:
                        result = public(item)
                        result.update(
                            status="existing",
                            message="Bereits installiert; Aktivierung bleibt erhalten.",
                        )
                        results.append(result)
                        continue
                    assets = m.base.contained(folder, folder / item["assets_rel"])
                    text_conflicts = m.moveset_support.text_patch_conflicts(
                        record, assets, text_records, text_roots) if item.get('enabled', True) else {}
                    conflicts = (
                        sorted(
                            {
                                owner[1]
                                for e in record["entries"]
                                for owner in conflicting_owners(e, owners, text_records, text_conflicts)
                                if owner[2] not in item.get('overlay_ids', []) + item.get('underlay_ids', [])
                            }
                        )
                        if item.get("enabled", True)
                        else []
                    )
                    if conflicts:
                        result = public(item)
                        result.update(
                            status="conflict",
                            message="Inzwischen Konflikt mit: " + ", ".join(conflicts),
                        )
                        results.append(result)
                        continue
                    for entry in record["entries"]:
                        checkpoint(is_cancel)
                        safe_name(entry["path"])
                        safe_name(entry.get("source_path", entry["path"]))
                        runtime_path = (
                            m.root(repo) / "profile/ultimate/mods" / key / entry["path"]
                        )
                        if len(str(runtime_path).encode("ascii")) >= 255:
                            raise ValueError("Zielpfad zu lang fuer den Skin-Loader.")
                        src = m.base.contained(
                            assets, assets / entry.get("source_path", entry["path"])
                        )
                        if not src.is_file():
                            raise ValueError("Datei fehlt in der geprueften Importkopie.")
                    was_present = (m.root(repo) / "library" / key).exists()
                    if item.get("origin"):
                        record["origin"] = item["origin"]
                    # save_library verifies the copied bytes before publishing
                    # the library entry. A separate hash of the snapshot here
                    # would read every asset twice without protecting the copy.
                    m.save_library(repo, record, assets)
                    if not was_present:
                        created_keys.append(key)
                    existing.add(signature(record))
                    desired["mods"][key] = dict(
                        name=item["name"], enabled=item.get("enabled", True)
                    )
                    if item.get('overlay_ids'):
                        desired['mods'][key]['overlays'] = list(item['overlay_ids'])
                    for higher in item.get('underlay_ids', []):
                        if higher not in desired['mods']:
                            raise ValueError('Ueberlagernde Mod wurde entfernt; Vorschau wiederholen.')
                        desired['mods'][higher]['overlays'] = sorted(set(desired['mods'][higher].get('overlays', [])) | {key})
                    prepared.append(item)
                    if item.get('enabled', True):
                        text_records[key] = record
                        text_roots[key] = m.catalog.location(repo, key) / 'assets'
                    for entry in record["entries"]:
                        if item.get("enabled", True) and target(entry):
                            owners.setdefault(
                                target(entry), (entry["sha256"], item["name"], key)
                            )
                except Cancelled:
                    raise
                except Exception as exc:
                    result = public(item)
                    result.update(status="failed", message=str(exc))
                    results.append(result)
            checkpoint(is_cancel)
            if prepared:
                actual_replacements = {
                    key for item in prepared for key in item.get("replacement_ids", [])
                }
                for key in plan.get("replace_ids", []):
                    if key not in actual_replacements:
                        desired["mods"][key] = state["mods"][key]
                progress(
                    callback,
                    "commit",
                    len(prepared),
                    total,
                    "Profil wird sicher umgeschaltet",
                    job_id=job_id,
                )
                import plugin_runtime

                try:
                    m.commit(repo, desired, cancel=is_cancel, callback=callback)
                except plugin_runtime.PluginBuildError as exc:
                    rejected = [
                        i
                        for i in prepared
                        if any(
                            e.get("kind") == "plugin" for e in i["record"]["entries"]
                        )
                    ]
                    remaining = [i for i in prepared if i not in rejected]
                    if not rejected or not remaining:
                        raise
                    for item in rejected:
                        desired["mods"].pop(item["record"]["id"], None)
                        row = public(item)
                        row.update(
                            status="failed",
                            message="Plugin-Gruppe konnte nicht vorbereitet werden: "
                            + str(exc),
                        )
                        results.append(row)
                    actual_replacements = {
                        key
                        for item in remaining
                        for key in item.get("replacement_ids", [])
                    }
                    for key in plan.get("replace_ids", []):
                        if key not in actual_replacements:
                            desired["mods"][key] = state["mods"][key]
                    m.commit(repo, desired, cancel=is_cancel, callback=callback)
                    prepared = remaining
                for item in prepared:
                    result = public(item)
                    result.update(
                        status="installed",
                        message=(
                            "Installiert und aktiviert."
                            if item.get("enabled", True)
                            else "Installiert und pausiert."
                        ),
                    )
                    results.append(result)
                installed = len(prepared)
        except Cancelled:
            cancelled = True
            for item in ready:
                if not any(r.get("item_id") == item["item_id"] for r in results):
                    result = public(item)
                    result.update(
                        status="cancelled", message="Vor dem Profilwechsel abgebrochen."
                    )
                    results.append(result)
        except Exception as exc:
            import setup_checks

            message = setup_checks.explain_build_error(repo, exc)
            for item in ready:
                if not any(r.get("item_id") == item["item_id"] for r in results):
                    result = public(item)
                    result.update(status="failed", message=message)
                    results.append(result)
        result = dict(
            installed=installed,
            failed=sum(i["status"] == "failed" for i in results),
            skipped=sum(i["status"] not in ("installed", "failed") for i in results),
            cancelled=cancelled,
            items=results,
            state=m.listing(repo),
            total=total,
            job_id=job_id,
        )
        m.base.write_json(folder / "result.json", result)
        committed = m.load(repo)["mods"]
        for key in created_keys:
            if key not in committed:
                try:
                    m.metadata(repo, key)
                    owned = m.base.contained(
                        m.root(repo) / "library", m.root(repo) / "library" / key
                    )
                    shutil.rmtree(owned)
                except (ValueError, OSError):
                    pass  # Preserve a concurrent manual edit rather than deleting it.
    clear_payload(folder)
    progress(
        callback,
        "done",
        total,
        total,
        job_id=job_id,
        installed=installed,
        failed=result["failed"],
        cancelled=cancelled,
    )
    return result
