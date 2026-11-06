"""Structural moveset diagnostics and explicit per-file visual overlays.

No rules depend on a mod title or a character name. Matching a marker is only
dependency evidence, never proof that an arbitrary plugin works in the game.
"""
import functools
import json
import re
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path


@functools.lru_cache(maxsize=256)
def _marker_tokens(path, modified, size):
    if size > 128 * 1024**2:
        raise ValueError('Plugin fuer Abhaengigkeitspruefung zu gross.')
    data = Path(path).read_bytes()
    return tuple(x.decode('ascii').lower() for x in
                 re.findall(rb'[A-Za-z0-9_-]+\.marker', data))


def diagnostics(repo, records):
    import catalog
    tokens, result = {}, {}
    for key, record in records.items():
        tokens[key] = set()
        for entry in record['entries']:
            if entry.get('kind') == 'plugin':
                path = catalog.location(repo, key) / 'assets' / entry['path']
                try:
                    stat = path.stat()
                    if path.is_symlink() or path.is_junction():
                        raise ValueError('Plugin ist eine Verknuepfung.')
                    tokens[key].update(_marker_tokens(str(path), stat.st_mtime_ns, stat.st_size))
                except (OSError, ValueError):
                    result[key] = 'Gameplay-Plugin fehlt oder ist nicht sicher lesbar: ' + entry['path'] + '. Originalpaket erneut pruefen.'
    all_tokens = set().union(*tokens.values())
    for key, record in records.items():
        markers = sorted({Path(e['path']).name.lower() for e in record['entries']
                          if re.fullmatch(r'fighter/[^/]+/model/body/c\d+/[^/]+\.marker', e['path'], re.I)})
        # Rust may concatenate string literals in the NRO's read-only data.
        # Accept a suffix within the same package, but require a stronger match
        # before treating an unrelated plugin as the base for an asset-only mod.
        missing = [m for m in markers if m not in all_tokens and 'c' + m not in all_tokens
                   and not any(token.endswith(m) for token in tokens[key])]
        if missing:
            result[key] = ('Moveset-Basismod fehlt oder ist nicht aktiviert: ' + ', '.join(missing)
                           + '. Dieses Paket enthaelt Zusatzmodelle fuer ein eigenes Moveset. '
                           'Die zugehoerige Basismod mit Gameplay-Plugin und ihren Abhaengigkeiten installieren.')
    return result


def preflight(repo, records):
    issues = diagnostics(repo, records)
    if issues:
        raise ValueError('\n'.join(records[k]['name'] + ': ' + message for k, message in issues.items()))


def selection_hint(record):
    import catalog
    slots = catalog.costume_slots(record)
    if not slots:
        return ''
    normal = [s for s in slots if int(s.rsplit('/c', 1)[1]) < 8]
    extended = [s for s in slots if s not in normal]
    parts = []
    if normal:
        parts.append('Kostuem waehlen: ' + ', '.join(s + ' (' + str(int(s.rsplit('/c', 1)[1]) + 1)
                                                     + '. Kostuem)' for s in normal))
    if extended:
        parts.append('Zusaetzliche Slots: ' + ', '.join(extended)
                     + '. Benoetigen Slot-/CSS-Unterstuetzung; Asset-Dateien erzeugen allein keinen neuen Charaktereintrag.')
    return ' '.join(parts)


def shared_destinations(repo, key, entry):
    """Read explicit ARC alias destinations from a selected, intact config."""
    import catalog
    import drybowser as base
    path = catalog.location(repo, key) / 'assets' / entry['path']
    if path.is_symlink() or path.is_junction() or path.stat().st_size > 16 * 1024**2 or base.digest(path) != entry['sha256']:
        raise ValueError('ARC-Konfiguration veraendert oder nicht sicher lesbar: ' + str(path))
    try:
        config = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(config, dict): raise ValueError('Objekt erwartet')
    except (ValueError, UnicodeError) as exc:
        raise ValueError('Ungueltige ARC-Konfiguration: ' + str(path)) from exc
    result = set()
    for field in ('share-to-added', 'share_to_added', 'new-shared-files', 'new_shared_files',
                  'share-to-vanilla', 'share_to_vanilla'):
        rules = config.get(field, {})
        if not isinstance(rules, dict): continue
        for destinations in rules.values():
            if not isinstance(destinations, list): continue
            for value in destinations:
                if isinstance(value, str):
                    if re.fullmatch(r'0x[0-9a-fA-F]{1,10}', value): result.add(int(value, 16))
                    elif '/' in value:
                        encoded = value.encode('utf-8')
                        result.add(len(encoded) << 32 | zlib.crc32(encoded))
                elif isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 1 << 40:
                    result.add(value)
    return result


@functools.lru_cache(maxsize=256)
def _text_labels(path, modified, changed, size, sha):
    import hashlib
    if size > 4 * 1024**2: raise ValueError('XMSBT-Patch zu gross.')
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != sha: raise ValueError('XMSBT-Patch wurde veraendert.')
    plain = data.replace(b'\0', b'').upper()
    if b'<!DOCTYPE' in plain or b'<!ENTITY' in plain: raise ValueError('XML-Entitaeten in XMSBT sind nicht erlaubt.')
    try:
        tree = ET.fromstring(data)
        if tree.tag != 'xmsbt': raise ValueError('XMSBT-Wurzel fehlt.')
        labels = {}
        for node in tree:
            if node.tag != 'entry' or not node.get('label') or len(node.get('label')) > 1024:
                raise ValueError('Ungueltiger XMSBT-Eintrag.')
            # Ignore formatting between entries, preserve every character of
            # the actual text and control-code markup.
            node.tail = None
            if node.text is not None and not node.text.strip(): node.text = None
            for child in node:
                if child.tail is not None and not child.tail.strip(): child.tail = None
            value = ET.tostring(node, encoding='utf-8')
            label = node.get('label')
            if label in labels and labels[label] != value: raise ValueError('Widerspruechlicher XMSBT-Eintrag: ' + label)
            labels[label] = value
        return labels
    except ET.ParseError as exc:
        raise ValueError('Ungueltiger XMSBT-Patch: ' + str(path)) from exc


def text_patch_sources(records, roots):
    import drybowser as base
    sources = {}
    for key, record in records.items():
        for entry in record['entries']:
            if entry['path'].endswith('.xmsbt'):
                sources.setdefault(entry['path'], []).append((key, entry))
    result = {}
    for name, entries in sources.items():
        if len(entries) < 2: continue
        patches = {}
        for key, entry in entries:
            path = base.contained(roots[key], roots[key] / entry.get('source_path', name))
            if path.is_symlink() or path.is_junction(): raise ValueError('XMSBT-Patch ist eine Verknuepfung.')
            stat = path.stat()
            patch = _text_labels(str(path), stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, entry['sha256'])
            patches[key] = patch
        result[name] = patches
    return result


def labels_conflict(left, right):
    return any(label in right and right[label] != value for label, value in left.items())


def text_patch_conflicts(record, root, records, roots):
    key = record['id']
    sources = text_patch_sources(dict(records, **{key: record}), dict(roots, **{key: root}))
    return {name: [other for other, labels in patches.items()
                   if other != key and key in patches and labels_conflict(patches[key], labels)]
            for name, patches in sources.items()}


def overlay_groups(records, statuses, arc=True, repo=None):
    """Resolve only explicit directed overlay permissions, never plugin conflicts."""
    parents = {}
    for key in records:
        lower = statuses[key].get('overlays', [])
        if not isinstance(lower, list) or any(not isinstance(x, str) or not re.fullmatch(r'mod-[0-9a-f]{16}', x) for x in lower):
            raise ValueError('Ungueltige Mod-Ueberlagerung.')
        parents[key] = set(lower)
    for key, lower in parents.items():
        if not isinstance(statuses[key].get('overlays', []), list) or key in lower:
            raise ValueError('Ungueltige Mod-Ueberlagerung.')
    visiting, ancestors = set(), {}
    def walk(key):
        if key in visiting:
            raise ValueError('Zyklische Mod-Ueberlagerung; Prioritaet neu festlegen.')
        if key not in ancestors:
            visiting.add(key)
            ancestors[key] = set(parents.get(key, set()))
            for lower in parents.get(key, set()):
                ancestors[key].update(walk(lower))
            visiting.remove(key)
        return ancestors[key]
    for key in records:
        walk(key)
    # A skin copied into a base folder replaces that folder's config.json too.
    # Loading both as separate ARCropolis configs can give one destination two
    # incompatible archive-sharing rules. Only explicit overlay components share
    # this identity; unrelated mods retain their independent configurations.
    components = {key: {key} for key in records}
    for key, lower in parents.items():
        for other in lower:
            if other not in records: continue
            joined = components[key] | components[other]
            for member in joined: components[member] = joined
    mergeable, hidden_text = set(), set()
    if arc and repo is not None:
        import catalog
        sources = text_patch_sources(records, {key: catalog.location(repo, key) / 'assets' for key in records})
        mergeable = set(sources)
        for name, patches in sources.items():
            keys = list(patches)
            for i, key in enumerate(keys):
                for other in keys[i+1:]:
                    if not labels_conflict(patches[key], patches[other]): continue
                    if other in ancestors[key]: hidden_text.add((other, name))
                    elif key in ancestors[other]: hidden_text.add((key, name))
                    else: raise ValueError('Widerspruechliche XMSBT-Texteintraege: ' + records[key]['name'] + ', ' + records[other]['name'] + ': ' + name)
    candidates, groups = {}, {key: {} for key in records}
    for key, record in records.items():
        for e in record['entries']:
            if (key, e['path']) in hidden_text: continue
            identity = ('arc-config', min(components[key])) if e['path']=='config.json' and len(components[key])>1 else (
                ('plugin', e['module']) if e.get('kind') == 'plugin' else (
                (key, e['path']) if e.get('metadata') or e['path'] in mergeable else ('path:' + e['path'] if arc else e['info']))
            )
            candidates.setdefault(identity, []).append((key, e))
    for identity, entries in candidates.items():
        if len({e['sha256'] for key, e in entries}) == 1:
            winner = entries[0]
        else:
            winners = [(key, e) for key, e in entries
                       if all(other == key or other in ancestors[key] for other, _ in entries)]
            if len(winners) != 1 or isinstance(identity, tuple) and identity[0] == 'plugin':
                raise ValueError('Konflikt: ' + ', '.join(records[k]['name'] for k, _ in entries)
                                 + '. Zuerst pausieren oder eine ausdrueckliche Asset-Ueberlagerung waehlen.')
            winner = winners[0]
        key, entry = winner
        groups[key][entry['path']] = entry['sha256']
    if arc and repo is not None:
        for key, record in records.items():
            if not ancestors[key] or 'config.json' not in groups[key]: continue
            entry = next(e for e in record['entries'] if e['path'] == 'config.json')
            destinations = shared_destinations(repo, key, entry)
            # A patch may replace a physical model with an ARC alias. Keeping
            # the base copy unshares that destination before ARC reshares it,
            # leaving its runtime resource unloaded. Treat the alias as this
            # patch's explicit file claim, only against its permitted bases.
            for lower in ancestors[key] & records.keys():
                for item in records[lower]['entries']:
                    name = item['path']
                    if item.get('kind') == 'plugin' or item.get('metadata'): continue
                    encoded = name.encode('utf-8')
                    if (len(encoded) << 32 | zlib.crc32(encoded)) in destinations:
                        unrelated = [other for other, record in records.items()
                                     if other != key and other not in ancestors[key] and key not in ancestors[other]
                                     and any(e['path'] == name for e in record['entries'])]
                        if unrelated:
                            raise ValueError('ARC-Dateiverknuepfung kollidiert mit ' + ', '.join(records[x]['name'] for x in unrelated)
                                             + ': ' + name + '. Ueberlagerung ausdruecklich festlegen.')
                        groups[lower].pop(name, None)
    return {key: entries for key, entries in groups.items() if entries}
