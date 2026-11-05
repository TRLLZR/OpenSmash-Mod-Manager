"""Build an isolated, pinned ARCropolis runtime from the user's local build.

No game bytes, generated DLLs, plugin binaries or hook site lists are distributed.
The upstream compiler settings and base-object verification remain in use.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parent))
import drybowser as base

APP='OpenSmash-ARC-runtime-v1'
VERSION='4.1.1'
URL='https://github.com/Raytwo/ARCropolis/releases/download/v4.1.1/release.zip'
SHA256='08b98371f069bc54a326660bc828288c05dd9a4ac0e3c7c00aca557796e032c6'
PLUGIN='atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libarcropolis.nro'
EXE='ssbu_modmanager.exe'
DLL='ssbu_game_modmanager.dll'
BIN='modmanager_arc/plugin_bin'


def location(repo): return repo/'opensmash_mods/arcropolis'


def file_key(repo,path):
    build=base.build_dir(repo).resolve()
    path=path.resolve()
    if path.is_relative_to(build):return '@build/'+path.relative_to(build).as_posix()
    return path.relative_to(repo.resolve()).as_posix()


def resolve_file(repo,key):
    if key.startswith('@build/'):
        build=base.build_dir(repo)
        return base.contained(build,build/key[len('@build/'):])
    return base.contained(repo,repo/key)


def signature():
    return {name:base.digest(Path(__file__).with_name(name))
            for name in ('arc_backend.py','arc_simd.py','arc_fs_support.h','legacy_addresses.py')}


def source_inputs(repo):
    """Fingerprint portable source paths, never user data or generated game C."""
    result = {}
    for directory in ('runtime', 'tools/lifter', 'tools/nro'):
        for path in sorted((repo / directory).rglob('*')):
            if path.is_file() and path.suffix in {'.py', '.c', '.cpp', '.h', '.inc', '.def'}:
                if path.is_symlink() or path.is_junction():
                    raise ValueError('Verknuepfung in den Build-Quellen: ' + str(path))
                result[path.relative_to(repo).as_posix()] = base.digest(path)
    return result


def stage_sources(repo, work):
    """Overlay current repository sources on the private staged build only."""
    for rel in source_inputs(repo):
        directory = 'runtime/' if rel.startswith('runtime/') else 'tools/lifter/' if rel.startswith('tools/lifter/') else 'tools/nro/'
        target = work / ('ro_study' if directory == 'tools/nro/' else '') / rel[len(directory):]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / rel, target)


def valid(repo, required=False):
    marker=location(repo)/'runtime.json'
    try:
        record=json.loads(marker.read_text())
        if record['app']!=APP or record['builder']!=signature(): raise ValueError('Builder-Version geaendert')
        if record.get('source_inputs') != source_inputs(repo): raise ValueError('OpenSmash-Buildquellen geaendert')
        if base.digest(base.build_dir(repo)/'work/ssbu_native.exe')!=record['native_sha256']:
            raise ValueError('OpenSmash-Version geaendert')
        for rel,sha in record['files'].items():
            if base.digest(resolve_file(repo,rel))!=sha: raise ValueError('Mod-Laufzeit geaendert: '+rel)
        return record
    except (OSError,ValueError,KeyError) as exc:
        if required: raise ValueError('ARCropolis-Laufzeit fehlt oder wurde geaendert. Eine Skin-Mod erneut installieren, um sie einzurichten. '+str(exc)) from exc
        return None


def seed_config(sd):
    # The runtime's local offline account has Uid 1/0. Flags are files: omitting
    # auto_update disables the plugin updater (it needs unsupported SSL imports).
    config=sd/'ultimate/arcropolis/config/1/0'
    config.mkdir(parents=True,exist_ok=True)
    values=dict(version=VERSION,logging_level='Info',presets='[]',workspace='Default',workspace_list='{"Default":"presets"}')
    for name,value in values.items(): (config/name).write_text(value)


def make_sd(repo, destination):
    ensure(repo)
    template=location(repo)/'template-sd'
    for name in ('atmosphere','ultimate/arcropolis/resources'):
        shutil.copytree(template/name,destination/name)
    for name in ('offsets.toml','unshare.lut','share.lut'):
        cached=template/'ultimate/arcropolis/cache/13.0.5'/name
        if cached.is_file():
            target=destination/'ultimate/arcropolis/cache/13.0.5'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(cached,target)
    seed_config(destination)


def run(args,cwd,env,log,timeout=900):
    with open(log,'ab') as stream:
        stream.write(('\nCOMMAND '+repr([str(x) for x in args])+'\n').encode());stream.flush()
        proc=subprocess.run([str(x) for x in args],cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,
                            timeout=timeout,creationflags=0x08000000 if sys.platform=='win32' else 0)
    if proc.returncode:
        raise ValueError('ARCropolis-Einrichtung fehlgeschlagen (Code %s). Details: %s'%(proc.returncode,log))


def ensure(repo):
    ready=valid(repo)
    if ready: return ready
    inputs=source_inputs(repo)
    builder_signature=signature()
    build=base.build_dir(repo)
    original=build/'work'
    state=json.loads((build/'state.json').read_text())
    if state.get('game_version')!='13.0.5':
        raise ValueError('ARCropolis %s benoetigt Spielversion 13.0.5.'%VERSION)
    clang=Path(state.get('tools',{}).get('clang',repo/'deps/llvm/bin/clang.exe'))
    if not clang.is_file(): raise ValueError('Lokaler OpenSmash-Compiler fehlt. OpenSmash-Build zuerst vervollstaendigen.')
    required=['relift_sites.py','build.py','recomp.py','ro_study/build_plugins.py','obj_eh_o1/_opt_report.txt',
              'obj_eh_o1_data/game_data.obj','obj_eh_o1_data/sdkdata.obj','obj_eh_o1_data/nro_registry.obj',
              'obj_eh_o1_data/sdklift_gen.obj','gen_eh_o2/table.c']
    if any(not (original/p).is_file() for p in required):
        raise ValueError('Der lokale OpenSmash-Build ist fuer ARCropolis unvollstaendig (Quellen/Objekte fehlen).')
    folder=location(repo)
    folder.mkdir(parents=True,exist_ok=True)
    logs=repo/'opensmash_mods/logs';logs.mkdir(exist_ok=True)
    log=logs/'arcropolis-build.log'
    work=original/'modmanager_arc'
    owner=work/'owner.json'
    if work.exists() and (not owner.is_file() or json.loads(owner.read_text()).get('app')!=APP):
        raise ValueError('Der private Build-Ordner ist bereits belegt: '+str(work))
    work.mkdir(exist_ok=True)
    base.write_json(owner,dict(app=APP))
    # Copy runtime/lifter sources only. Large generated game sources and objects
    # are read in place, never changed. Every generated artifact stays private.
    for src in original.iterdir():
        if src.is_file() and src.suffix in {'.py','.c','.cpp','.h','.inc','.txt','.json'}:
            shutil.copy2(src,work/src.name)
    for name in ('ro_study','fighter_sdk','nocrt','plat'):
        source=original/name
        if source.is_dir():
            shutil.copytree(source,work/name,dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('*.dll','*.exe','*.obj','*.pyc','__pycache__'))
    stage_sources(repo, work)
    release=folder/'release-4.1.1.zip'
    if not release.is_file() or base.digest(release)!=SHA256:
        temporary=folder/'release.download'
        urllib.request.urlretrieve(URL,temporary)
        if base.digest(temporary)!=SHA256: raise ValueError('ARCropolis-Download stimmt nicht mit SHA-256 ueberein.')
        os.replace(temporary,release)
    template=folder/'template-sd'
    if not template.exists():
        template.mkdir()
        base.unpack_zip(release,template)
    # Verify even an interrupted extraction against the pinned archive.
    import zipfile
    with zipfile.ZipFile(release) as archive:
        expected={i.filename.replace('\\','/'):hashlib.sha256(archive.read(i)).hexdigest()
                  for i in archive.infolist() if not i.is_dir()}
    for rel,sha in expected.items():
        path=base.contained(template,template/rel)
        if not path.is_file() or base.digest(path)!=sha:
            raise ValueError('ARCropolis-Ressourcen unvollstaendig: '+rel)
    seed_config(template)
    env={k:v for k,v in os.environ.items() if not k.startswith(('RECOMP_','SSBU_'))}
    env.update(RECOMP_CLANG=str(clang),RECOMP_BIN=str(build/'binaries/13.0.5'),RECOMP_TIME_LIMIT='120',
               PYTHONUNBUFFERED='1',PYTHONUTF8='1')
    python=Path(sys.executable)
    # Reuse the upstream pinned/header downloads, redirected into our folder.
    spec=importlib.util.spec_from_file_location('arc_upstream_install',repo/'scripts/install.py')
    upstream=importlib.util.module_from_spec(spec)
    sys.path.insert(0,str(repo/'scripts'))
    with open(log,'a') as stream:
        import contextlib
        with contextlib.redirect_stdout(stream):
            spec.loader.exec_module(upstream)
            upstream.DEPS=str(folder/'build-deps')
            env['SDL3_ROOT']=upstream.fetch('sdl3')
            env['VULKAN_HEADERS']=upstream.fetch('vulkan-headers')
            env['IMGUI_ROOT']=upstream.fetch('imgui')
            env['SUYU_ROOT']=upstream.fetch_suyu()
    env['FFMPEG_ROOT']=str(repo/'deps/ffmpeg')
    run([python,work/'gen_quad_tests.py'],work,env,log)
    run([python,work/'gen_sdktest.py'],work,env,log)
    builder=work/'ro_study/build_plugins.py'
    run([python,builder,'--sd',template,'--jobs','4'],builder.parent,env,log)
    import arc_simd
    arc_simd.patch_generated(work,template/PLUGIN)
    run([python,builder,'--sd',template,'--jobs','4'],builder.parent,env,log)
    # Record sites with the original EXE. Only the plugin DLL folder and SD root
    # change; original game DLL, executable and saves are not modified.
    test=folder/'probe-userdata'
    if not test.exists(): shutil.copytree(build/'saves',test)
    sites=original/'skyline_sites.log'
    saved_sites=folder/'sites-before-build.log'
    if sites.exists(): shutil.copy2(sites,saved_sites)
    probe=logs/'arcropolis-sites.log'
    args=[python,repo/'scripts/run.py','--userdata',test,'--seconds','120','--log',probe]
    envs=dict(SSBU_SD=str(template),SSBU_PLUGIN_BIN=BIN,SSBU_SKYLINE='1',SSBU_LOOSE_FILES='0',SSBU_FIGHTER_SRC='0',
              SSBU_ONLINE='0',SSBU_SHOW='0',SSBU_VOLUME='0',SSBU_ERROR_DIALOG='0',SSBU_VK_PREP='0',SSBU_SKIP_MOVIES='1')
    for key,value in envs.items(): args+=['--env',key+'='+value]
    # A trap before re-lifting is expected: the initial-loading hook is inactive.
    with open(log,'ab') as stream:
        subprocess.run([str(x) for x in args],cwd=repo,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=180,creationflags=0x08000000)
    if not sites.is_file() or 'inline ' not in sites.read_text() or 'patch ' not in sites.read_text():
        raise ValueError('ARCropolis hat keine vollstaendige Hook-Liste erzeugt. '+str(probe))
    shutil.copy2(sites,work/'skyline_sites.log')
    if saved_sites.exists(): shutil.copy2(saved_sites,sites)
    run([python,Path(__file__),'relift',work,original],work,env,log,timeout=1800)
    run([python,Path(__file__),'host',work,original],work,env,log)
    for name in (EXE,DLL):
        target=original/name
        if target.exists():
            backup=folder/(name+'.before-build')
            shutil.copy2(target,backup)
        shutil.copy2(work/name,target)
    probe=logs/'arcropolis-ready.log'
    args=[python,repo/'scripts/run.py','--exe',EXE,'--userdata',test,'--seconds','30','--log',probe]
    for key,value in envs.items():args+=['--env',key+'='+value]
    run(args,repo,env,log,timeout=90)
    text=probe.read_text(errors='replace')
    if 'Finished mounting mods:/' not in text or 'plugin sites compiled in' not in text or any(
            bad in text for bad in ('GUEST TRAP','UNTRANSLATED INSTRUCTION','NOT ACTIVE','has panicked')):
        raise ValueError('ARCropolis-Laufzeittest nicht bestanden. '+str(probe))
    outputs=[original/EXE,original/DLL,work/'plugin_bin/sky_arcropolis.dll',work/'plugin_bin/plugins.txt']
    outputs += [template/rel for rel in expected]
    if source_inputs(repo)!=inputs: raise ValueError('OpenSmash-Quellen haben sich waehrend des Builds geaendert; erneut versuchen.')
    if signature()!=builder_signature: raise ValueError('Loader-Buildwerkzeug waehrend des Builds geaendert; erneut versuchen.')
    record=dict(app=APP,version=VERSION,builder=builder_signature,source_inputs=inputs,native_sha256=base.digest(original/'ssbu_native.exe'),
                files={file_key(repo,p):base.digest(p) for p in outputs},probe=str(probe.relative_to(repo)))
    base.write_json(folder/'runtime.json',record)
    return record


def build_worker(kind,work,original):
    os.chdir(work)
    os.environ['RECOMP_GEN']=str(original/'gen_eh_o2')
    sys.path.insert(0,str(work))
    import build
    if kind=='relift':
        import relift_sites
        original_settings=relift_sites.base_settings
        def settings(*args,**kwargs):
            _,opt,extra,per_file=original_settings(*args,**kwargs)
            return os.environ['RECOMP_CLANG'],opt,extra,per_file
        relift_sites.base_settings=settings
        sys.argv=['relift_sites.py','build','skyline_sites.log','--tag=modmanager','--jobs=2',
                  '--base-gen='+str(original/'gen_eh_o2'),'--base-eh='+str(original/'gen_eh_o2'),
                  '--base-obj='+str(original/'obj_eh_o1')]
        result=relift_sites.main()
        if result:return result
        # Current upstream relift omits the separate GameData objects. Link them
        # with its verified bucket selection and updated shim, locally only.
        data=[original/'obj_eh_o1_data'/name for name in ('game_data.obj','sdkdata.obj','nro_registry.obj','sdklift_gen.obj')]
        args=[os.environ['RECOMP_CLANG'],'-shared','-O1','-w','-I',str(work),'-I',str(work/'gen_modmanager'),
              str(work/'game_shim_eh.c'),str(work/'gen_modmanager/sky_sites.c'),'@'+str(work/(DLL+'.rsp')),
              *map(str,data),'-o',str(work/DLL)]
        return subprocess.call(args)
    source=(work/'nnfs.c').read_text()
    marker='static const ImportDef fs_imports[] = {'
    if source.count(marker)!=1: raise ValueError('Unbekannte OpenSmash-Dateisystem-Version.')
    header=Path(__file__).with_name('arc_fs_support.h')
    view='static int view_path(Mount *m, const char *rel, char *out) {'
    directories='if (m->work[0]) { join(roots[n], m->work, rel); if (is_dir(roots[n])) n++; }'
    committed='if (!m->work[0] || !tomb_hides(m, rel)) { join(roots[n], m->root, rel); if (is_dir(roots[n])) n++; }'
    if source.count(view)!=1 or source.count(directories)!=1 or source.count(committed)!=1:
        raise ValueError('Unbekannte OpenSmash-RomFS-Version; Plugin-Sicht nicht eingebaut.')
    source=source.replace(view, view[:-1]+';\n#include "'+header.as_posix()+'"\n'+view+
        '\n    int overlay = arc_plugin_view(m, rel, out);\n    if (overlay >= 0) return overlay;')
    source=source.replace(directories,
        'if (arc_plugin_view(m, rel, host) >= 0) { snprintf(roots[n++], MAX_PATH, "%s", host); }\n'
        '            else '+directories)
    source=source.replace(committed,
        'if (arc_plugin_view(m, rel, host) < 0 && (!m->work[0] || !tomb_hides(m, rel))) { join(roots[n], m->root, rel); if (is_dir(roots[n])) n++; }')
    source=source.replace(marker,marker+
                          '\n {FS("24GetFileTimeStampForDebugEPNS0_13FileTimeStampEPKc"),arc_GetFileTimeStamp},')
    custom=work/'nnfs_modmanager.c'
    custom.write_text(source)
    build.HOST_SOURCES=[str(custom) if p=='nnfs.c' else p for p in build.HOST_SOURCES]
    alias_header=work/'legacy_main_aliases.h'
    if alias_header.is_file():
        rt=(work/'hostrt.c').read_text()
        call='void call_indirect(Ctx *c, uint64_t addr) {'
        failure='if (!fn) guest_trap("indirect call to an address that is not a known function", addr);'
        if rt.count(call)!=1 or rt.count(failure)!=2:
            raise ValueError('Unbekannte OpenSmash-Aufrufaufloesung; keine Kompatibilitaets-Aliase eingebaut.')
        rt=rt.replace(call,'#include "'+alias_header.as_posix()+'"\n'+call)
        rt=rt.replace(failure,'if (!fn) { uint64_t mapped=arc_legacy_target(c,addr); if(mapped!=addr) fn=lookup_guest(mapped); }\n        '+failure,1)
        patched=work/'hostrt_modmanager.c';patched.write_text(rt)
        build.HOST_SOURCES=[str(patched) if p=='hostrt.c' else p for p in build.HOST_SOURCES]
    build.GAME_DLL=DLL
    os.environ['RECOMP_EXE']=EXE
    return build.cmd_link(host_only=True)


if __name__=='__main__':
    sys.exit(build_worker(sys.argv[1],Path(sys.argv[2]),Path(sys.argv[3])))
