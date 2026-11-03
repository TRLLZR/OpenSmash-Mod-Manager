"""Resolve local release targets from user configuration, never developer paths."""

import json
import os
import winreg
from pathlib import Path


def installed_app():
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenSmashMods",
    ) as key:
        return Path(winreg.QueryValueEx(key, "InstallLocation")[0])


def configured_repo(explicit=None):
    value = explicit or os.environ.get("OPENSMASH_TEST_REPO")
    if not value:
        settings = Path(os.environ["LOCALAPPDATA"]) / "OpenSmashMods/settings.json"
        value = json.loads(settings.read_text(encoding="utf-8"))["repo"]
    repo = Path(value).resolve(strict=True)
    if not (repo / "scripts/run.py").is_file():
        raise ValueError("Select a configured OpenSmash game folder")
    return repo
