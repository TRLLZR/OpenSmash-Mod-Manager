"""Native localized layouts in an isolated synthetic library; no live downloads."""

import json
import os
import subprocess
import sys
from pathlib import Path

WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(WORK / "installer"))
import test_modmanager as fixture


def main():
    case = fixture.ManagerTests()
    case.setUp()
    output = WORK / "locale-ui-3.7"
    output.mkdir(exist_ok=True)
    try:
        from PIL import Image

        for i, title in enumerate(
            ("Own cover fixture", "A longer mod title with a neutral placeholder")
        ):
            folder = case.mod(
                title, "ui/replace/a.bntx" if i != 1 else "ui/replace/b.bntx", str(i)
            )
            if i == 0:
                Image.new("RGB", (600, 340), (35 + 50 * i, 130, 180)).save(
                    folder / "preview.png"
                )
            fixture.m.install(case.repo, folder)
        reports = []
        variants = [
            (code, "Light")
            for code in (
                "de",
                "en",
                "es",
                "fr",
                "it",
                "pt",
                "nl",
                "pl",
                "tr",
                "ru",
                "uk",
                "ja",
                "ko",
                "zh-CN",
                "zh-TW",
                "ar",
            )
        ]
        variants += [("de", "Dark"), ("ar", "Dark"), ("en", "HighContrast")]
        for language, theme in variants:
            report = output / f"{language}-{theme}.json"
            subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-STA",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(WORK / "LocaleUiTest.ps1"),
                    "-Source",
                    str(WORK / "installer"),
                    "-Repo",
                    str(case.repo),
                    "-Report",
                    str(report),
                    "-Theme",
                    theme,
                ],
                env=dict(os.environ, OPENSMASH_UI_LANGUAGE=language),
                check=True,
                timeout=25,
            )
            data = json.loads(report.read_text(encoding="utf-8-sig"))
            assert (
                data["ok"]
                and data["language"] == language
                and data["rtl"] == (language == "ar")
            )
            reports.append(data)
        result = dict(
            ok=True, variants=reports, fixture_only=True, real_library_untouched=True
        )
        (WORK / "locale-ui-result.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        print(json.dumps(dict(ok=True, native_variants=len(reports)), indent=2))
    finally:
        case.doCleanups()


if __name__ == "__main__":
    main()
