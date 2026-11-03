"""Culture routing and presentation/protocol separation through the native host."""

import json
import os
import re
import subprocess
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
CATALOG = json.loads((SOURCE / "locales.json").read_text(encoding="utf-8"))


class LocalizationTests(unittest.TestCase):
    def probe(self, language):
        script = r"""
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
[Reflection.Assembly]::LoadFrom((Join-Path $env:OPENSMASH_TEST_SOURCE 'ModManager.exe'))|Out-Null
. (Join-Path $env:OPENSMASH_TEST_SOURCE 'Localization.ps1')
$value=[pscustomobject]@{name='Bibliothek';id='Downloads';message='Bereit';warnings=@('Abgebrochen');origin=[pscustomobject]@{author='Bereit';file_name='Bibliothek.zip'}}
Localize-Result $value
@{language=[OpenSmash.Localizer]::Language;rtl=[OpenSmash.Localizer]::RightToLeft;library=(L 'Bibliothek');fallback=(L 'Profil sicher umschalten');raw=(L 'user-owned-file.zip');result=$value;traditional=[OpenSmash.Localizer]::Resolve('zh-HK');unknown=[OpenSmash.Localizer]::Resolve('xx-YY')}|ConvertTo-Json -Depth 6 -Compress
"""
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            env=dict(
                os.environ,
                OPENSMASH_UI_LANGUAGE=language,
                OPENSMASH_TEST_SOURCE=str(SOURCE),
            ),
            capture_output=True,
            encoding="utf-8",
            check=True,
            timeout=15,
        )
        return json.loads(result.stdout)

    def test_all_language_families_use_native_catalog(self):
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
        ):
            with self.subTest(language=code):
                result = self.probe(code)
                self.assertEqual(result["language"], code)
                self.assertEqual(
                    result["library"],
                    "Bibliothek" if code == "de" else CATALOG["Bibliothek"][code],
                )
                self.assertEqual(result["rtl"], code == "ar")
                self.assertEqual(result["traditional"], "zh-TW")
                self.assertEqual(result["unknown"], "en")
                self.assertEqual(result["raw"], "user-owned-file.zip")
                self.assertEqual(result["result"]["id"], "Downloads")
                self.assertEqual(result["result"]["name"], "Bibliothek")
                self.assertEqual(result["result"]["origin"]["author"], "Bereit")
                self.assertEqual(
                    result["result"]["origin"]["file_name"], "Bibliothek.zip"
                )

    def test_regional_and_unsupported_languages_fall_back(self):
        for culture, expected in (
            ("pt-BR", "pt"),
            ("de-AT", "de"),
            ("zh-Hant", "zh-TW"),
            ("en-GB", "en"),
            ("sv-SE", "en"),
        ):
            with self.subTest(culture=culture):
                self.assertEqual(self.probe(culture)["language"], expected)

    def test_format_placeholders_survive_translation(self):
        for source, translations in CATALOG.items():
            placeholders = sorted(re.findall(r"\{\d+(?::[^}]+)?\}", source))
            for language, text in translations.items():
                with self.subTest(source=source, language=language):
                    self.assertEqual(
                        sorted(re.findall(r"\{\d+(?::[^}]+)?\}", text)), placeholders
                    )


if __name__ == "__main__":
    unittest.main()
