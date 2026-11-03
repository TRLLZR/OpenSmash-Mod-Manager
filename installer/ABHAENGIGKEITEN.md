# Abhängigkeiten und offizielle Quellen

| Komponente | Verwendung und Bezugsquelle |
|---|---|
| OpenSmash / ssbu-recomp | Bestehendes Spiel, Runtime-Quellen, ARC-Leser, Build-Werkzeuge; [Repository](https://github.com/OpenSmash-Ultimate/ssbu-recomp), [Skyline-Anleitung](https://github.com/OpenSmash-Ultimate/ssbu-recomp/blob/main/docs/SKYLINE.md); GPL-3.0. Nicht beigelegt. |
| ARCropolis 4.1.1 | Allgemeiner Asset-/Skin-Loader; [offizielles Release](https://github.com/Raytwo/ARCropolis/releases/tag/v4.1.1); GPL-3.0. Separat geladen, nicht im Paket enthalten. |
| arc-config | Referenz des Standardformats; [Quelle](https://github.com/Raytwo/arc-config/blob/master/src/lib.rs). Autor-Konfiguration bleibt unverändert. |
| Private Python-Laufzeit | CPython 3.14.10 x64, numpy 2.5.4, zstandard 0.25.0, Pillow 13.0.0 und capstone 5.0.9 sind beigelegt. Herkunft, Prüfsummen und Lizenzen: runtime/DISTRIBUTION.json und THIRD_PARTY_NOTICES.txt. |
| LLVM/Clang | Vorhandener OpenSmash-Compiler, normalerweise LLVM 9. Nicht beigelegt. |
| Microsoft C++ Build Tools / Windows SDK | Header und Windows-Linker für die separate Mod-Laufzeit; müssen vorhanden sein. Kein automatischer systemweiter Installer. |
| SDL3, Vulkan-Headers, Dear ImGui, zwei Suyu-Referenzdateien | Downloads und SHA-256-Prüfung aus vorhandenem `scripts/install.py`, umgeleitet in das private Mod-Build-Verzeichnis. Die jeweiligen Projektlizenzen gelten. |
| PowerShell 5.1 / .NET Framework 4.8 / WPF | Windows-Komponenten für die Oberfläche, auf unterstütztem Windows vorhanden. WinForms dient dem nativen Ordnerdialog und Setup. EXE-Host und XAML liegen bei; C#-Quellcode und Buildskripte bleiben im Entwicklungsprojekt. Keine WebView-/Node-Laufzeit erforderlich. |

ARCropolis-Archiv: `https://github.com/Raytwo/ARCropolis/releases/download/v4.1.1/release.zip`

SHA-256: `08b98371f069bc54a326660bc828288c05dd9a4ac0e3c7c00aca557796e032c6`

Keine Windows-Sicherheits- oder Systemeinstellungen werden verändert. Die Prozess-ExecutionPolicy gilt nur für den gestarteten Prozess. Es werden keine Nintendo-Dateien, Keys, Firmware oder Saves heruntergeladen oder weitergegeben.

Eigene Hilfsskripte, Vektor-Ergänzungen und GUI-Starter stehen unter der beiliegenden MIT-Lizenz. Lokal kopierte/übersetzte Drittprojekte behalten ihre Lizenzen. Erzeugte Runtime-/Spiel-DLLs und Plugin-Binärdateien werden nicht mit der ZIP verteilt.


## Plugin-Abhängigkeiten ab 2.3.0 (nur lokal geladen)

- Smashline 2.0.0: https://github.com/HDR-Development/smashline/releases/download/v2.0.0/libsmashline_plugin.nro — SHA-256 `d57a437000d13a85192b79941880b4e3b671d0e4a0291951d426f0f6773e6b92`.
- nro-hook 0.4.0: https://github.com/ultimate-research/nro-hook-plugin/releases/download/v0.4.0/libnro_hook.nro — SHA-256 `ca7aec03aee49fea539dcb92569fea5bc5389f77377ba2a30e4d0b7ebd0255e6`.

Diese Binärdateien und die daraus lokal erzeugten DLLs liegen nicht in der Installer-ZIP. Quellen, Lizenzen und technische Grundlagen der Projekte gelten weiterhin; OpenSmashs SKYLINE.md beschreibt die Übersetzung und den SDK-Unwind-Ersatz. Es werden keine Windows-Sicherheitsfunktionen abgeschaltet.


## RAR-Decoder ab 2.3.1 (portabel enthalten)

UnRAR64.dll 7.23.0 aus dem [offiziellen RARLAB-DLL-Paket](https://www.rarlab.com/rar_add.htm), direkte Paket-URL https://www.rarlab.com/rar/unrardll-723.exe. DLL-SHA-256 `894b7d2db8d6363eb12f30c7b89f48eab9e71963b8b438675bdd64c12dd59bcc`. Originallizenz in UNRAR_LICENSE.txt, Paket-Prüfsumme in UNRAR_DISTRIBUTION.json. Kein WinRAR-Setup und keine systemweite Installation. Unterstützung für RAR4/RAR5, auch komprimiert/Solid; geschützte oder mehrteilige RARs werden mit Hinweis abgelehnt.


## Öffentliche GameBanana-Integration 3.0

API-Dokumentation: https://api.gamebanana.com/ ; aktuelle Endpunktfamilie: https://gamebanana.com/apiv11/ ; Spiel: https://gamebanana.com/games/6498 . Öffentliche Leseanfragen ohne Login, keine Umgehung privater/gesperrter Dateien. Mod/Sound Index, ListFilterConfig, Game/6498/ProfilePage, Util/Search/Results und jeweilige ProfilePage liefern Katalog, Varianten und Prüfsummen. Der Manager enthält keine heruntergeladenen Moddateien oder Katalogbilder im Installer. Python-Standardbibliothek (HTTPS, SQLite, Threads) und vorhandenes Pillow genügen; kein Webbrowser-/WebView-Paket nötig.

## Prüfung 3.3.0

CPython 3.14.10 ersetzt 3.13.16 (offizielle TLS-Sicherheitskorrektur). Alle vier Pythonpakete entsprechen dem aktuellen stabilen PyPI-Stand, PyPI/OSV ohne bekannte Advisory für diese Versionen am 02.11.2026. Python 3.15.2 ist neuer, bietet für zstandard aber noch kein passendes Windows-Wheel. UnRAR 7.30 beta 2 wird zugunsten der stabilen DLL 7.23 nicht übernommen. .NET Framework 4.8/4.8.1 und Windows PowerShell 5.1 bleiben Windows-Komponenten, kein Wechsel der Hostingarchitektur. Details: SECURITY.md.

## Gameplay-Bibliotheken ab 3.4

Param Config 6.5: https://github.com/CSharpM7/lib_paramconfig/releases/tag/6.5 . One Slot Effects 13.0.5: https://gamebanana.com/mods/549058 . Downloads, SHA-256 und exakter NRO-Archivpfad stehen in plugin_dependencies.py. Nur diese NRO wird verwendet; optionale Flags und fremde Mods bleiben ausgeschlossen. Keine dieser Binärdateien wird im Installer oder Quellpaket weitergegeben. Die Bedingungen der jeweiligen Autoren gelten.

The CSK Collection: https://gamebanana.com/mods/499008 . Die dort angebotene 5.0.6 ist für 13.0.4 und wird für 13.0.5 blockiert. Die Autorendokumentation nennt 6.0.0 für 13.0.5, für die beim Prüfen kein offizieller Download vorlag. Keine Versionskompatibilität durch pauschales Umbenennen oder Modtitel-Sonderregeln.
