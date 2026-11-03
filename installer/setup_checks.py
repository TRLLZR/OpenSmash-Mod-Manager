"""Read-only prerequisite checks. Never downloads or installs system components."""

import json, os, platform, subprocess, sys, tempfile
from pathlib import Path
import drybowser as base

OFFICIAL_TOOLS = "https://aka.ms/vs/17/release/vs_BuildTools.exe"


def explain_build_error(repo, error):
    message = str(error)
    if "ARCropolis-Einrichtung fehlgeschlagen" not in message:
        return message
    log = repo / "opensmash_mods/logs/arcropolis-build.log"
    try:
        with log.open("rb") as f:
            f.seek(max(0, log.stat().st_size - 32768))
            detail = f.read().decode("utf-8", errors="replace")
        if any(
            header in detail
            for header in (
                "'string.h' file not found",
                "'windows.h' file not found",
                "'stdio.h' file not found",
            )
        ):
            return (
                "C/C++-Entwicklungsheader fehlen. In den Microsoft C++ Build Tools die Desktopentwicklung mit C++ und das Windows 10/11 SDK installieren, danach erneut versuchen. "
                + message
            )
    except OSError:
        pass
    return message


def check(repo, compile_probe=True):
    result = dict(
        manager_ready=False,
        skin_ready=False,
        issues=[],
        warnings=[],
        official_build_tools=OFFICIAL_TOOLS,
        python=sys.version.split()[0],
        x64=sys.maxsize > 2**32,
    )
    if not result["x64"]:
        result["issues"].append("Windows x64 und ein 64-Bit-Python werden benoetigt.")
        return result
    try:
        build, state, arc, h40 = base.preflight(repo)
        arc.f.close()
    except Exception as exc:
        result["issues"].append(str(exc))
        return result
    result["manager_ready"] = True
    result["game_version"] = state["game_version"]
    required = [
        "relift_sites.py",
        "build.py",
        "recomp.py",
        "ro_study/build_plugins.py",
        "obj_eh_o1/_opt_report.txt",
        "obj_eh_o1_data/game_data.obj",
        "obj_eh_o1_data/sdkdata.obj",
        "obj_eh_o1_data/nro_registry.obj",
        "obj_eh_o1_data/sdklift_gen.obj",
        "gen_eh_o2/table.c",
    ]
    missing = [p for p in required if not (build / "work" / p).is_file()]
    if missing:
        result["warnings"].append(
            "Fuer neue Skins fehlen lokale OpenSmash-Builddateien: "
            + ", ".join(missing[:4])
        )
    clang = Path(state.get("tools", {}).get("clang", repo / "deps/llvm/bin/clang.exe"))
    if not clang.is_file():
        result["warnings"].append(
            "OpenSmash-Compiler fehlt. OpenSmash vollstaendig einrichten."
        )
    elif compile_probe:
        try:
            probe = subprocess.run(
                [str(clang), "-x", "c", "-fsyntax-only", "-"],
                input="#include <string.h>\n#include <windows.h>\nint main(void){return 0;}\n",
                capture_output=True,
                text=True,
                timeout=20,
                creationflags=0x08000000 if sys.platform == "win32" else 0,
            )
            if probe.returncode:
                result["warnings"].append(
                    "C/C++-Entwicklungsheader fehlen oder werden nicht erkannt. Desktopentwicklung mit C++ und Windows 10/11 SDK installieren. Bei vorhandenen Tools die x64 Native Tools Command Prompt verwenden."
                )
                result["compiler_details"] = (probe.stderr or probe.stdout)[-2500:]
        except Exception as exc:
            result["warnings"].append("Compilerpruefung nicht moeglich: " + str(exc))
    result["skin_ready"] = not result["warnings"] and state["game_version"] == "13.0.5"
    if state["game_version"] != "13.0.5":
        result["warnings"].append(
            "Der erweiterte Skin-Loader benoetigt Spielversion 13.0.5."
        )
    return result
