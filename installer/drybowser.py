"""Reversible native loose-file installation. No game or third-party assets bundled."""
import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

sys.dont_write_bytecode = True
if sys.version_info < (3, 12):
    raise SystemExit('Python 3.12 oder neuer erforderlich. Bitte das private OpenSmash-Python verwenden.')

APP = 'OpenSmash-DryBowser-native-v1'
LOCAL = 'drybowser_local'
LAUNCHERS = {'Play SSBU Modded.bat': 'modded', 'Play SSBU Vanilla.bat': 'vanilla'}


def digest(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def contained(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError('Unsicherer Zielpfad: ' + str(path))
    return path


def inventory(root):
    out = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink() or p.is_junction():
            raise ValueError('Verknuepfungen im verwalteten Ordner sind nicht erlaubt: ' + str(p))
        if p.is_file() and p.name != 'installation.json':
            out[p.relative_to(root).as_posix()] = digest(p)
    return out


def build_dir(repo):
    location = repo / 'build_location.txt'
    if location.exists():
        line = location.read_text(encoding='utf-8-sig').splitlines()[0].strip().strip('"')
        if line:
            return Path(os.path.abspath(os.path.expandvars(line)))
    return repo / 'build'


def alternate_launch_env(build):
    """run.py reads rollback only for the normal EXE; match it for our EXE.

    Online mode/server/code stay under OpenSmash's graphics.ini configuration.
    In particular, do not force SSBU_ONLINE to either 0 or 1.
    """
    try:
        with (build/'config/graphics.ini').open(encoding='utf-8-sig',errors='replace') as stream:
            for line in stream:
                key,sep,value=line.partition('=')
                if sep and key.strip().lower()=='rollback':
                    on=value.split('#')[0].split(';')[0].strip().lower() in ('on','1','yes','true')
                    return {'SSBU_RB_NET':'net'} if on else {}
    except OSError:
        pass
    return {}


def preflight(repo):
    repo = repo.resolve(strict=True)
    build = build_dir(repo)
    state = json.loads((build / 'state.json').read_text(encoding='utf-8-sig'))
    version = state.get('game_version')
    if version not in ('13.0.4', '13.0.5'):
        raise ValueError('Ungepruefte Spielversion: ' + str(version))
    exe = build / 'work/ssbu_native.exe'
    for p in [exe, build / 'work/ssbu_game_eh_o1.dll', build / 'work/SDL3.dll',
              build / 'work/ssbu_glslang.dll', build / ('binaries/' + version + '/main.elf'),
              repo / 'scripts/run.py', repo / 'tools/nro/arc_extract.py']:
        if not p.is_file():
            raise ValueError('Unvollstaendige OpenSmash-Installation; fehlt: ' + str(p))
    for file, tokens in {
        'runtime/loose_host.c': ['SSBU_LOOSE_FILES', 'SSBU_LOOSE_FILES=0'],
        'runtime/loose_files.c': ['SSBU_CHARACTERS', 'SSBU_LOOSE_RAW', 'lf_rawcopy'],
        'scripts/run.py': ['--env', '--log', '--userdata'],
    }.items():
        text = (repo / file).read_text(encoding='utf-8-sig')
        if not all(token in text for token in tokens):
            raise ValueError('Diese OpenSmash-Version besitzt nicht die benoetigte native Schnittstelle: ' + file)
    binary = exe.read_bytes()
    if not all(token in binary for token in (b'SSBU_LOOSE_FILES', b'SSBU_LOOSE_RAW', b'[loose] served')):
        raise ValueError('Die EXE enthaelt den nativen Asset-Loader nicht. Kein wirkungsloser Installationsversuch.')
    romfs = Path(state['dump']['romfs'])
    if not romfs.is_dir():
        romfs = build / 'dump/romfs'
    arc_path = romfs / 'data.arc'
    if not arc_path.is_file():
        raise ValueError('Eigene entpackte Spieldaten fehlen: ' + str(arc_path))
    spec = importlib.util.spec_from_file_location('drybowser_local_arc', repo / 'tools/nro/arc_extract.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        arc = module.Arc(str(arc_path))
    except ImportError as e:
        raise ValueError('Python-Paket zstandard fehlt. OpenSmash-Python bzw. vorhandene requirements.txt verwenden.') from e
    return build, state, arc, module.hash40


def find_mod(source):
    candidates = []
    for p in [source, *source.glob('*'), *source.glob('*/*')]:
        if p.is_dir() and (p / 'fighter/koopa/model/body/c00/model.numdlb').is_file():
            candidates.append(p)
    if len(candidates) != 1:
        raise ValueError('Genau einen entpackten DryBowserFullReplacement-Ordner waehlen; gefunden: ' + str(len(candidates)))
    mod = candidates[0].resolve()
    info = (mod / 'info.toml').read_text(encoding='utf-8-sig')
    if 'Dry Bowser' not in info or 'Full Replacement' not in info or 'Release 4' not in info:
        raise ValueError('Dieser Installer ist fuer Dry Bowser Full Replacement, Release 4. Andere Varianten werden nicht stillschweigend installiert.')
    for fighter in ('koopa', 'koopag'):
        for slot in range(8):
            if not (mod / f'fighter/{fighter}/model/body/c{slot:02}/model.numdlb').is_file():
                raise ValueError('Full Replacement ist unvollstaendig: ' + fighter + ', Slot ' + str(slot))
    return mod


def unpack_zip(source, target):
    with zipfile.ZipFile(source) as z:
        entries = z.infolist()
        if len(entries) > 12000 or sum(i.file_size for i in entries) > 3 * 1024**3:
            raise ValueError('Archiv ist fuer diese Mod unerwartet gross.')
        names = set()
        for entry in entries:
            name = entry.filename.replace('\\', '/')
            p = contained(target, target / name)
            if ':' in name or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unsicherer Archiveintrag: ' + name)
            if name.lower() in names:
                raise ValueError('Doppelter Archiveintrag: ' + name)
            names.add(name.lower())
            if entry.is_dir():
                p.mkdir(parents=True, exist_ok=True)
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                with z.open(entry) as src, open(p, 'wb') as dst:
                    shutil.copyfileobj(src, dst)


def analyze(mod, arc, hash40):
    selected, skipped, checksums = [], [], {}
    groups = defaultdict(list)
    raw = []
    for p in sorted(mod.rglob('*')):
        if p.is_symlink() or p.is_junction():
            raise ValueError('Mod-Ordner enthaelt Verknuepfung: ' + str(p))
        if not p.is_file():
            continue
        rel = p.relative_to(mod).as_posix()
        checksums[rel] = digest(p)
        if '/' not in rel:
            continue
        if not rel.startswith(('fighter/koopa/', 'fighter/koopag/', 'effect/fighter/koopa/', 'effect/fighter/koopag/', 'ui/replace/', 'ui/message/')):
            raise ValueError('Unerwarteter Mod-Pfad: ' + rel)
        if p.suffix.lower() in ('.nro', '.dll', '.exe', '.bat', '.ps1', '.py'):
            raise ValueError('Diese Asset-Mod darf keinen ausfuehrbaren Code enthalten: ' + rel)
        index = arc.path_index_from_hash(hash40(rel))
        if index is None:
            skipped.append({'path': rel, 'reason': 'XML-Merge nicht implementiert' if p.suffix == '.xmsbt' else 'Pfad nicht im eigenen Archiv vorhanden'})
            continue
        rec = arc.file_record(index)
        if not rec['decomp_size'] or rec['info_flags'] & 0x18000:
            raise ValueError('Regionaler/leerer Archiveintrag wird nicht direkt ersetzt: ' + rel)
        selected.append(rel)
        groups[rec['info_index']].append(rel)
        if not rec['data_flags'] & 1:
            raw.append(rel)
    if len(selected) > 4096 or len(selected) < 600:
        raise ValueError('Unplausible Dateianzahl oder Grenze des nativen Loaders: ' + str(len(selected)))
    known_hashes = {hash40(rel) for rel in selected}
    external_aliases = defaultdict(list)
    for index in range(arc.n_path):
        path_hash = arc.file_path(index)[0][0]
        if path_hash in known_hashes:
            continue
        info = arc.file_record(index)['info_index']
        if info in groups:
            external_aliases[info].append(hex(path_hash))
    # Replacing a shared empty animation also changes unrelated archive paths.
    # Never do that: preserve the game's bytes for every group with external refs.
    protected = []
    for info, references in external_aliases.items():
        paths = groups.pop(info)
        protected.append(dict(paths=paths, external_references=references))
        for rel in paths:
            selected.remove(rel)
            skipped.append(dict(path=rel, reason='Geteilter Archiveintrag mit weiteren Pfaden: Original bleibt zum Schutz anderer Assets erhalten'))
    alias_conflicts = [paths for paths in groups.values() if len({checksums[p] for p in paths}) > 1]
    # The native loader serves the first matching info_index. Make that deterministic by
    # installing just one representative; c00 is lexicographically first in this mod.
    unique = [paths[0] for paths in groups.values()]
    return dict(install_files=sorted(unique), recognized_paths=len(selected), source_files=len(checksums),
                source_sha256=checksums, skipped=skipped, uncompressed_paths=raw,
                shared_conflicts=alias_conflicts, protected_shared_entries=protected,
                limitations=['Namenspatch .xmsbt bleibt aus.',
                             'Geteilte Archiveintraege verwenden c00; einzelne Details anderer Farbslots und Giga-Formen weichen ab.',
                             'Die global geteilte model.nuanmb bleibt unveraendert; ihre zusaetzliche Modellanimation fehlt.',
                             'Nicht vorhandene zusaetzliche Giga-UI-Pfade werden ausgelassen.'])


def verify_managed(local):
    if local.is_symlink() or local.is_junction():
        raise ValueError('Verwalteter Ordner ist eine Verknuepfung.')
    state = json.loads((local / 'installation.json').read_text(encoding='utf-8'))
    if state.get('app') != APP or inventory(local) != state['owned_files']:
        raise ValueError('Verwaltete Dateien wurden geaendert. Nichts ueberschrieben/entfernt: ' + str(local))
    return state


def launcher(mode):
    return ('@echo off\r\nsetlocal DisableDelayedExpansion\r\n'
            'powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0drybowser_local\\tools\\Start.ps1" -Mode ' + mode + '\r\n'
            'if errorlevel 1 pause\r\n').encode('ascii')


def verify_launchers(repo, state):
    for name, expected in state['launchers'].items():
        path = contained(repo, repo / name)
        if not path.is_file() or digest(path) != expected:
            raise ValueError('Startdatei wurde geaendert. Rueckbau gestoppt: ' + str(path))


def update_launch_tools(repo, tool_dir=None):
    """Update owned launch helpers without requiring the original mod download."""
    local=contained(repo,repo/LOCAL)
    if not local.exists():return
    state=verify_managed(local)
    verify_launchers(repo,state)
    source=tool_dir or Path(__file__).resolve().parent
    incoming={name:digest(source/name) for name in ('drybowser.py','Start.ps1')}
    if all(digest(local/'tools'/name)==sha for name,sha in incoming.items()):return
    backup=contained(repo,repo/'drybowser_backups'/('launcher-tools-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]))
    backup.mkdir(parents=True)
    shutil.copy2(local/'installation.json',backup/'installation.json')
    for name in incoming:shutil.copy2(local/'tools'/name,backup/name)
    updated=json.loads(json.dumps(state))
    for name,sha in incoming.items():updated['owned_files']['tools/'+name]=sha
    updated['installer_sha256']=incoming['drybowser.py']
    write_json(backup/'installation.updated.json',updated)
    try:
        for name,sha in incoming.items():
            shutil.copy2(source/name,local/'tools'/name)
            if digest(local/'tools'/name)!=sha:raise ValueError('Starter-Quelle hat sich geaendert.')
        os.replace(backup/'installation.updated.json',local/'installation.json')
    except Exception:
        for name in incoming:shutil.copy2(backup/name,local/'tools'/name)
        shutil.copy2(backup/'installation.json',local/'installation.json')
        raise


def install(repo, source, check_only=False):
    build, state, arc, hash40 = preflight(repo)
    mod = find_mod(source)
    report = analyze(mod, arc, hash40)
    arc.f.close()
    print('Erkannt:', report['source_files'], 'Quelldateien;', report['recognized_paths'], 'Archivpfade;',
          len(report['install_files']), 'eindeutige Ersatzdateien;', len(report['skipped']), 'ausgelassen.')
    for warning in report['limitations']:
        print('EINSCHRAENKUNG:', warning)
    if check_only:
        return report
    local = contained(repo, repo / LOCAL)
    fingerprint = digest(build / 'work/ssbu_native.exe')
    previous = None
    if local.exists():
        previous = verify_managed(local)
        verify_launchers(repo, previous)
        if previous['source_sha256'] == report['source_sha256'] and previous['runtime_sha256'] == fingerprint and previous['installer_sha256'] == digest(Path(__file__)):
            print('Bereits identisch installiert. Keine Dateien veraendert.')
            return report
    stamp = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]
    backup = contained(repo, repo / 'drybowser_backups' / stamp)
    pending = contained(repo, repo / (LOCAL + '.pending-' + uuid.uuid4().hex))
    pending.mkdir()
    try:
        for rel in report['install_files']:
            dst = contained(pending, pending / 'assets/DryBowser' / rel)
            # The runtime uses narrow Win32 paths and fixed buffers.
            runtime_path = repo / LOCAL / dst.relative_to(pending)
            if len(str(runtime_path).encode('ascii')) >= 390:
                raise ValueError('Installationspfad ist fuer diesen nativen Loader zu lang.')
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(mod / rel, dst)
            if digest(dst) != report['source_sha256'][rel]:
                raise ValueError('Quelldatei hat sich waehrend der Installation geaendert: ' + rel)
        (pending / 'tools').mkdir()
        (pending / 'empty').mkdir()
        for name in ('drybowser.py', 'Start.ps1'):
            shutil.copy2(Path(__file__).parent / name, pending / 'tools' / name)
        write_json(pending / 'asset-report.json', report)
        originals = previous['original_launchers'] if previous else {}
        backup.mkdir(parents=True)
        if not previous:
            for name in LAUNCHERS:
                p = repo / name
                if p.exists():
                    if not p.is_file() or p.is_symlink():
                        raise ValueError('Keine regulaere Startdatei: ' + str(p))
                    shutil.copy2(p, backup / name)
                    originals[name] = dict(path=(backup / name).relative_to(repo).as_posix(), sha256=digest(p))
                else:
                    originals[name] = None
        # Back up metadata before any active installation is changed; original assets are never overwritten.
        for p, name in [(build / 'state.json', 'build-state.json'), (repo / 'Play SSBU.bat', 'original-Play-SSBU.bat')]:
            if p.exists():
                shutil.copy2(p, backup / name)
        manifest = dict(app=APP, installed=stamp, game_version=state['game_version'],
                        runtime_sha256=fingerprint, installer_sha256=digest(Path(__file__)),
                        source_sha256=report['source_sha256'], original_launchers=originals,
                        launchers={n: hashlib.sha256(launcher(m)).hexdigest() for n, m in LAUNCHERS.items()},
                        owned_files=inventory(pending))
        write_json(pending / 'installation.json', manifest)
        if previous:
            shutil.move(str(local), str(backup / 'previous-installation'))
        try:
            pending.rename(local)
            for name, mode in LAUNCHERS.items():
                (repo / name).write_bytes(launcher(mode))
        except Exception:
            if local.exists():
                local.rename(backup / 'failed-installation')
            if previous:
                (backup / 'previous-installation').rename(local)
                for name, mode in LAUNCHERS.items():
                    (repo / name).write_bytes(launcher(mode))
            else:
                for name, original in originals.items():
                    if original:
                        shutil.copy2(repo / original['path'], repo / name)
                    elif (repo / name).exists():
                        (repo / name).unlink()
            raise
        print('Installiert:', local)
        print('Sicherung:', backup)
        print('Start: Play SSBU Modded.bat (Bowser waehlen). Vanilla: Play SSBU Vanilla.bat')
        print('Laufzeit noch separat pruefen; eine erfolgreiche Dateikopie ist kein Spieltest.')
        return report
    except Exception:
        # Keep preparation for diagnosis; never recursively delete a computed user path.
        print('Vorbereitungsordner (falls vorhanden):', pending)
        raise


def uninstall(repo):
    local = contained(repo, repo / LOCAL)
    if not local.exists():
        print('Dry Bowser ist nicht installiert. Keine Aenderung.')
        return
    state = verify_managed(local)
    verify_launchers(repo, state)
    for name, original in state['original_launchers'].items():
        if original:
            path = contained(repo / 'drybowser_backups', repo / original['path'])
            if not path.is_file() or digest(path) != original['sha256']:
                raise ValueError('Originalsicherung fehlt/veraendert: ' + str(path))
    backup = contained(repo, repo / 'drybowser_backups' / ('uninstall-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]))
    backup.mkdir(parents=True)
    local.rename(backup / 'removed-installation')
    for name, original in state['original_launchers'].items():
        if original:
            shutil.copy2(repo / original['path'], repo / name)
        else:
            (repo / name).unlink()
    print('Deinstalliert. Saves, Mod-Quelle und Originalstarter unveraendert. Rueckbausicherung:', backup)


def play(repo, mode):
    manager = repo / 'opensmash_mods/tools/modmanager.py'
    if manager.is_file() and (repo / 'opensmash_mods/state.json').is_file():
        args=[sys.executable,str(manager),'--repo',str(repo),'play']
        if mode=='vanilla':args.append('--vanilla')
        return subprocess.call(args,cwd=repo)
    build = build_dir(repo)
    local = repo / LOCAL
    state = verify_managed(local)
    if digest(build / 'work/ssbu_native.exe') != state['runtime_sha256']:
        raise ValueError('OpenSmash wurde geaendert. Installer erneut ausfuehren und neu pruefen.')
    logs = build / 'logs'
    logs.mkdir(exist_ok=True)
    log = logs / ('drybowser-' + mode + '-' + time.strftime('%Y%m%d-%H%M%S') + '.log')
    args = [sys.executable, str(repo / 'scripts/run.py'), '--play', '--seconds', '0', '--log', str(log)]
    envs = dict(SSBU_LOOSE_FILES='1' if mode == 'modded' else '0', SSBU_LOOSE_RAW='1',
                SSBU_CHARACTERS=str(local / ('assets' if mode == 'modded' else 'empty')),
                SSBU_SKYLINE='0', SSBU_FIGHTER_SRC='0', SSBU_MODS=str(local / 'empty'),
                SSBU_SHOW='1')
    for k, v in envs.items():
        args.extend(['--env', k + '=' + v])
    print('Protokoll:', log, flush=True)
    return subprocess.call(args, cwd=repo)


def main():
    ap = argparse.ArgumentParser(description='Dry Bowser Full Replacement Release 4: nativer OpenSmash-Asset-Loader')
    ap.add_argument('action', choices=['install', 'check', 'uninstall', 'play'])
    ap.add_argument('--repo', required=True, type=Path)
    ap.add_argument('--mod', type=Path)
    ap.add_argument('--mode', choices=['modded', 'vanilla'], default='modded')
    a = ap.parse_args()
    repo = a.repo.resolve(strict=True)
    if not (repo / 'scripts/run.py').is_file():
        raise ValueError('Kein OpenSmash-Projektverzeichnis: ' + str(repo))
    if a.action == 'uninstall':
        uninstall(repo)
    elif a.action == 'play':
        return play(repo, a.mode)
    else:
        source = a.mod or repo / 'mods/custom'
        source = source.resolve(strict=True)
        if source.is_file():
            if source.suffix.lower() != '.zip':
                raise ValueError('Archiv bitte zuerst entpacken; direkt unterstuetzt wird ZIP.')
            with tempfile.TemporaryDirectory(prefix='drybowser-') as tmp:
                unpack_zip(source, Path(tmp))
                install(repo, Path(tmp), a.action == 'check')
        else:
            install(repo, source, a.action == 'check')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, ImportError) as exc:
        print('FEHLER:', exc, file=sys.stderr)
        sys.exit(1)
