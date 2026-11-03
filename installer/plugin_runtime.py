"""General Skyline NRO preparation, isolated by plugin content; no game files shipped."""

import hashlib, json, os, re, shutil, struct, subprocess, sys, urllib.request
from pathlib import Path
import drybowser as base
import arc_backend
import plugin_dependencies

APP = "OpenSmash-PluginSet-v1"
BUILD_ABI = "2.3-plugins-v1"


class PluginBuildError(ValueError):
    pass


DEPENDENCIES = {
    "smashline": (
        "libsmashline_plugin.nro",
        "https://github.com/HDR-Development/smashline/releases/download/v2.0.0/libsmashline_plugin.nro",
        "d57a437000d13a85192b79941880b4e3b671d0e4a0291951d426f0f6773e6b92",
    ),
    "nro_hook": (
        "libnro_hook.nro",
        "https://github.com/ultimate-research/nro-hook-plugin/releases/download/v0.4.0/libnro_hook.nro",
        "ca7aec03aee49fea539dcb92569fea5bc5389f77377ba2a30e4d0b7ebd0255e6",
    ),
}


for _key, _record in plugin_dependencies.REGISTRY.items():
    DEPENDENCIES[_key] = (_record["filename"], _record["url"], _record["sha256"])


def inspect_nro(path):
    size = path.stat().st_size
    if not 128 <= size <= 128 * 1024**2:
        raise ValueError("Ungueltige NRO-Groesse: " + path.name)
    data = path.read_bytes()
    if data[16:20] != b"NRO0":
        raise ValueError("Kein gueltiges Skyline-NRO: " + path.name)
    file_size = struct.unpack_from("<I", data, 24)[0]
    if not 128 <= file_size <= size:
        raise ValueError("Beschaedigter NRO-Header: " + path.name)
    for off in (32, 40, 48):
        start, length = struct.unpack_from("<II", data, off)
        if start + length > file_size:
            raise ValueError("NRO-Segment liegt ausserhalb der Datei.")
    ro = struct.unpack_from("<I", data, 40)[0]
    if ro + 8 > file_size:
        raise ValueError("NRO-RODATA-Header ist abgeschnitten.")
    if file_size + struct.unpack_from("<I", data, 56)[0] > 512 * 1024**2:
        raise ValueError("NRO-Speicherabbild ist zu gross.")
    zero, n = struct.unpack_from("<Ii", data, ro)
    if zero or not 0 < n < 256 or ro + 8 + n > size:
        raise ValueError("NRO-Modulname fehlt.")
    name = data[ro + 8 : ro + 8 + n].decode("latin-1").replace("\\", "/").split("/")[-1]
    if name.lower().endswith(".nro"):
        name = name[:-4]
    name = "sky_" + "".join(c if c.isascii() and c.isalnum() else "_" for c in name)
    if len(name) > 120:
        raise ValueError("NRO-Modulname ist zu lang.")
    return dict(module=name, smashline=b"smashline_" in data)


def plugins(profile):
    return sorted(p for p in (profile / "ultimate/mods").glob("*/*.nro") if p.is_file())


def dependency(repo, name):
    if name in plugin_dependencies.REGISTRY:
        return plugin_dependencies.obtain(repo, name)
    filename, url, sha = DEPENDENCIES[name]
    cache = base.contained(repo, repo / "opensmash_mods/plugin-dependencies")
    cache.mkdir(exist_ok=True)
    target = cache / filename
    if not target.is_file() or base.digest(target) != sha:
        temporary = target.with_suffix(".download")
        urllib.request.urlretrieve(url, temporary)
        if base.digest(temporary) != sha:
            raise ValueError(
                "Plugin-Abhaengigkeit hat eine falsche Pruefsumme: " + filename
            )
        os.replace(temporary, target)
    return target


def describe(profile):
    result = []
    modules = {}
    for path in plugins(profile):
        info = inspect_nro(path)
        sha = base.digest(path)
        if info["module"] in modules and modules[info["module"]] != sha:
            raise ValueError(
                "Zwei verschiedene Versionen desselben Skyline-Plugins: "
                + info["module"]
            )
        modules[info["module"]] = sha
        result.append(
            dict(path=path.relative_to(profile).as_posix(), sha256=sha, **info)
        )
    return result


def valid(repo, record):
    if record.get("app") != APP:
        raise ValueError("Ungueltige Plugin-Laufzeit.")
    key = record.get("key", "")
    if (
        not re.fullmatch("[0-9a-f]{20}", key)
        or record.get("exe") != "modmanager_plugins/" + key + "/" + arc_backend.EXE
        or record.get("plugin_bin") != "plugin_bin"
        or record.get("nro_bin") != "../../nro_bin_eh_o2"
    ):
        raise ValueError("Ungueltige Plugin-Laufzeitpfade.")
    if not record.get("files") or "@build/work/" + record["exe"] not in record["files"]:
        raise ValueError("Plugin-Laufzeit ist unvollstaendig.")
    for rel, sha in record["files"].items():
        if base.digest(arc_backend.resolve_file(repo, rel)) != sha:
            raise ValueError("Plugin-Laufzeit wurde veraendert: " + rel)
    return record


def boot_name(item):
    """Preserve shared library names that plugins check on the SD card."""
    filename = Path(item["path"]).name.casefold()
    for record in plugin_dependencies.REGISTRY.values():
        if filename == record["filename"].casefold():
            return record["filename"]
    return item["module"] + ".nro"


def deploy_dependencies(repo, profile, record):
    if not record:
        return
    target = profile / "atmosphere/contents/01006A800016E000/romfs/skyline/plugins"
    target.mkdir(parents=True, exist_ok=True)
    for name in record["dependencies"]:
        src = dependency(repo, name)
        shutil.copy2(src, target / DEPENDENCIES[name][0])
    for item in describe(profile):
        if Path(item["path"]).name != "plugin.nro":
            shutil.copy2(profile / item["path"], target / boot_name(item))


def ensure(repo, profile):
    items = describe(profile)
    if not items:
        return None
    plugin_dependencies.check_provided(repo, plugins(profile))
    extra = plugin_dependencies.required(
        plugins(profile),
        [
            p.relative_to(profile).as_posix()
            for p in (profile / "ultimate/mods").rglob("*")
            if p.is_file()
        ],
    )
    plugin_dependencies.preflight(repo, extra)
    arc_backend.ensure(repo)
    build = base.build_dir(repo)
    original = build / "work"
    base_work = original / "modmanager_arc"
    configs = {
        p.relative_to(profile).as_posix(): base.digest(p)
        for p in (profile / "ultimate/mods").rglob("*")
        if p.is_file()
        and (
            (
                len(p.relative_to(profile / "ultimate/mods").parts) == 2
                and p.suffix.lower() in (".toml", ".ini", ".json")
                and p.name != "info.toml"
            )
            or p.relative_to(profile / "ultimate/mods").parts[1] == "flags"
        )
    }
    required_dependencies = (
        ["smashline", "nro_hook"] if any(i["smashline"] for i in items) or extra else []
    ) + extra
    source = dict(
        plugins=items,
        configs=configs,
        builder=BUILD_ABI,
        arc=arc_backend.signature(),
        native=base.digest(original / "ssbu_native.exe"),
        dependencies={name: DEPENDENCIES[name][2] for name in required_dependencies},
    )
    key = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()[:20]
    container = base.contained(original, original / "modmanager_plugins")
    container.mkdir(exist_ok=True)
    work = base.contained(container, container / key)
    marker = work / "ready.json"
    if marker.is_file():
        record = json.loads(marker.read_text())
        if record.get("key") != key:
            raise ValueError("Plugin-Cache passt nicht zur aktiven Auswahl.")
        return valid(repo, record)
    if work.exists() and (
        not (work / "owner.json").is_file()
        or json.loads((work / "owner.json").read_text()).get("app") != APP
    ):
        raise ValueError("Fremder Plugin-Buildordner; nichts ueberschrieben.")
    work.mkdir(exist_ok=True)
    base.write_json(work / "owner.json", dict(app=APP))
    log = repo / "opensmash_mods/logs" / ("plugin-build-" + key + ".log")
    log.parent.mkdir(exist_ok=True)
    for p in base_work.iterdir():
        if (
            p.is_file()
            and p.suffix in (".py", ".c", ".cpp", ".h", ".inc", ".txt", ".json")
            and p.name != "skyline_sites.log"
        ):
            shutil.copy2(p, work / p.name)
    for name in ("ro_study", "fighter_sdk", "nocrt", "plat", "obj_host"):
        if (base_work / name).is_dir():
            shutil.copytree(
                base_work / name,
                work / name,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
    bindir = work / "plugin_bin"
    bindir.mkdir(exist_ok=True)
    for p in (base_work / "plugin_bin").iterdir():
        if p.is_file():
            shutil.copy2(p, bindir / p.name)
    sd = work / "sd"
    if sd.exists():
        if sd.is_symlink() or sd.is_junction():
            raise ValueError("Unsichere Plugin-Testkopie.")
        shutil.rmtree(sd)
    shutil.copytree(profile, sd)
    need_smashline = "smashline" in required_dependencies
    plugin_dir = sd / "atmosphere/contents/01006A800016E000/romfs/skyline/plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    for name in required_dependencies:
        src = dependency(repo, name)
        shutil.copy2(src, plugin_dir / DEPENDENCIES[name][0])
    # Mod-local NROs are also placed in Skyline's boot folder. Content deduplication
    # and stable module names prevent two different modules from sharing a slot.
    for item in items:
        if Path(item["path"]).name != "plugin.nro":
            shutil.copy2(sd / item["path"], plugin_dir / boot_name(item))
    # The builder discovers the boot folder and mod-local NROs. Remove just its
    # duplicate discovery through an application-owned adapter, not plugin code.
    adapter = work / "build_plugin_set.py"
    adapter.write_text(
        "import sys\nsys.path.insert(0,"
        + repr(str(work / "ro_study"))
        + ")\nimport plugin_map,build_plugins\nf=plugin_map.find_plugins\ndef unique(sd):\n seen=set();out=[]\n for p in f(sd):\n  n=plugin_map.module_name(p)\n  if n not in seen:out.append(p);seen.add(n)\n return out\nplugin_map.find_plugins=unique\nraise SystemExit(build_plugins.main())\n",
        encoding="utf-8",
    )
    state = json.loads((build / "state.json").read_text())
    clang = state.get("tools", {}).get("clang", str(repo / "deps/llvm/bin/clang.exe"))
    deps = arc_backend.location(repo) / "build-deps"
    # SDL root is the directory containing lib/x64 and include.
    sdl = next(p.parent.parent for p in (deps / "SDL3").rglob("lib/x64/SDL3.lib"))
    env = {
        k: v for k, v in os.environ.items() if not k.startswith(("RECOMP_", "SSBU_"))
    }
    env.update(
        RECOMP_CLANG=str(clang),
        RECOMP_BIN=str(build / "binaries/13.0.5"),
        RECOMP_TIME_LIMIT="120",
        PYTHONUTF8="1",
        SDL3_ROOT=str(sdl.parent),
        IMGUI_ROOT=str(next((deps / "imgui").rglob("imgui.h")).parent),
        VULKAN_HEADERS=str(
            next(
                (deps / "Vulkan-Headers").rglob("include/vulkan/vulkan.h")
            ).parent.parent.parent
        ),
        SUYU_ROOT=str(deps / "suyu"),
        FFMPEG_ROOT=str(repo / "deps/ffmpeg"),
    )
    py = Path(sys.executable)
    names = {i["module"] for i in items}
    names.update(
        inspect_nro(plugin_dir / DEPENDENCIES[n][0])["module"]
        for n in required_dependencies
    )
    arc_backend.run(
        [py, adapter, "--sd", sd, "--jobs", "4", "--only", ",".join(sorted(names))],
        work,
        env,
        log,
        timeout=1800,
    )
    for name in (arc_backend.EXE, arc_backend.DLL, "SDL3.dll"):
        src = (base_work / name) if (base_work / name).is_file() else original / name
        shutil.copy2(src, work / name)
    for src in original.glob("*.dll"):
        if not src.name.startswith("ssbu_game") and not (work / src.name).exists():
            shutil.copy2(src, work / src.name)
    userdata = work / "test-userdata"
    if not userdata.exists():
        shutil.copytree(build / "saves", userdata)
    graphics = work / "test-graphics.ini"
    if (build / "config/graphics.ini").is_file():
        shutil.copy2(build / "config/graphics.ini", graphics)
    controllers = work / "test-controllers.ini"
    dlc = work / "test-dlc.txt"
    for name, target in [("controllers.ini", controllers), ("dlc.txt", dlc)]:
        if (build / "config" / name).is_file():
            shutil.copy2(build / "config" / name, target)
    seq = work / "probe-sequence.txt"
    seq.write_text("")
    envs = dict(
        SSBU_SD=str(sd),
        SSBU_PLUGIN_BIN="plugin_bin",
        SSBU_NRO_BIN="../../nro_bin_eh_o2",
        SSBU_SKYLINE="1",
        SSBU_LOOSE_FILES="0",
        SSBU_FIGHTER_SRC="0",
        SSBU_ONLINE="0",
        SSBU_SHOW="0",
        SSBU_VOLUME="0",
        SSBU_ERROR_DIALOG="0",
        SSBU_VK_PREP="0",
        SSBU_SKIP_MOVIES="1",
        SSBU_GRAPHICS_CONFIG=str(graphics),
        SSBU_CONFIG=str(controllers),
        SSBU_DLC_LIST=str(dlc),
    )

    def probe(name, seconds=40):
        path = log.parent / (name + "-" + key + ".log")
        args = [
            py,
            repo / "scripts/run.py",
            "--exe",
            str((work / arc_backend.EXE).relative_to(original)),
            "--userdata",
            userdata,
            "--seconds",
            str(seconds),
            "--log",
            path,
        ]
        for k, v in envs.items():
            args += ["--env", k + "=" + v]
        with log.open("ab") as out:
            subprocess.run(
                [str(x) for x in args],
                cwd=repo,
                env=env,
                stdout=out,
                stderr=out,
                timeout=seconds + 90,
                creationflags=0x08000000,
            )
        return path.read_text(errors="replace") if path.exists() else ""

    text = probe("plugin-sites")
    # A re-lift cannot supply a missing library. Fail before the expensive step;
    # inactive hook sites in this first probe are expected and checked later.
    if re.search(r"\b(lib[\w-]+\.nro) not found", text, re.I):
        validate_log(text, need_smashline)
    sites = work / "skyline_sites.log"
    if not sites.exists():
        raise ValueError("Keine Plugin-Hooks aufgezeichnet. Details: " + str(log))
    arc_backend.run(
        [py, Path(arc_backend.__file__), "relift", work, original],
        work,
        env,
        log,
        timeout=1800,
    )
    # Plugins may patch common when fighters load; it is rebuilt with the same
    # recorded sites, using the verified local base module objects.
    if "common " in sites.read_text(errors="replace") or need_smashline:
        arc_backend.run(
            [py, Path(__file__), "common", work, original], work, env, log, timeout=1800
        )
    arc_backend.run(
        [py, Path(arc_backend.__file__), "host", work, original],
        work,
        env,
        log,
        timeout=900,
    )
    text = probe("plugin-ready")
    warnings = validate_log(text, need_smashline)
    if "Finished mounting mods:/" not in text:
        raise ValueError(
            "Plugin-Laufzeittest nicht bestanden. Bisherige Mod-Auswahl bleibt erhalten. Details: "
            + str(log)
        )
    outputs = [
        work / arc_backend.EXE,
        *work.glob("*.dll"),
        *bindir.glob("*.dll"),
        bindir / "plugins.txt",
    ]
    outputs += list((work / "nro_bin_sky").glob("*.dll"))
    record = dict(
        app=APP,
        key=key,
        exe=(work / arc_backend.EXE).relative_to(original).as_posix(),
        plugin_bin="plugin_bin",
        nro_bin="../../nro_bin_eh_o2",
        dependencies=required_dependencies,
        warnings=warnings,
        files={arc_backend.file_key(repo, p): base.digest(p) for p in outputs},
    )
    base.write_json(marker, record)
    return record


def validate_log(text, smashline=False):
    missing = sorted(set(re.findall(r"\b(lib[\w-]+\.nro) not found", text, re.I)))
    if missing:
        raise ValueError("Fehlende Gameplay-Abhaengigkeiten: " + ", ".join(missing))
    if any(
        x in text
        for x in (
            "GUEST TRAP",
            "HOST EXCEPTION",
            "UNTRANSLATED INSTRUCTION",
            "has panicked",
            "no lifted code for this build",
        )
    ):
        detail = next(
            (
                line.strip()
                for line in text.splitlines()
                if any(
                    marker in line
                    for marker in (
                        "HOST EXCEPTION",
                        "GUEST TRAP",
                        "has panicked",
                        "UNTRANSLATED INSTRUCTION",
                    )
                )
            ),
            "",
        )
        raise ValueError("Die Plugin-Laufzeit meldet einen Fehler: " + detail[:400])
    active_module = ""
    warnings = []
    for line in text.splitlines():
        match = re.search(r"\[skyline\] (sky_\w+): main", line)
        if match:
            active_module = "" if "returned" in line else match[1]
        if "NOT ACTIVE" in line:
            # The upstream nnunwind implementation replaces Smashline's two SDK
            # unwind hooks. Only this pinned framework's initialization gets the
            # documented exemption; game/common/plugin hooks must all be active.
            if (
                smashline
                and active_module == "sky_smashline"
                and " at sdk+" in line
                and len(warnings) < 2
            ):
                warnings.append(line)
            else:
                raise ValueError(
                    "Ein Plugin-Hook ist nicht aktiv. Weitere lokale Re-Lift-Pruefung erforderlich: "
                    + line
                )
    return warnings


def build_common(work, original):
    os.chdir(work)
    sys.path.insert(0, str(work))
    import relift_sites

    original_settings = relift_sites.base_settings

    def settings(*a, **kw):
        _, opt, extra, per_file = original_settings(*a, **kw)
        return os.environ["RECOMP_CLANG"], opt, extra, per_file

    relift_sites.base_settings = settings
    sys.argv = [
        "relift_sites.py",
        "build",
        "skyline_sites.log",
        "--module=common",
        "--tag=sky",
        "--jobs=2",
        "--base-gen=" + str(original / "gen_nro_eh_o2/lua2cpp_common"),
        "--base-eh=" + str(original / "gen_nro_eh_o2/lua2cpp_common"),
        "--base-obj=" + str(original / "obj_nro_eh_o2/lua2cpp_common"),
    ]
    return relift_sites.main()


if __name__ == "__main__":
    sys.exit(build_common(Path(sys.argv[2]), Path(sys.argv[3])))
