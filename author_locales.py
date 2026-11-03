"""Maintain reviewed UI vocabulary; generated catalogs run entirely offline.

German source phrases are stable keys while the existing application is migrated
incrementally. Never pass file paths, mod titles or provider content to this table.
"""

import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "installer"
ENGLISH = r"""
Modliste teilen…|Share mod list…
Modliste importieren…|Import mod list…
Modliste teilen|Share mod list
Modliste importieren|Import mod list
Modliste gespeichert|Mod list saved
Modliste gespeichert.|Mod list saved.
Fehlende Mods installieren|Install missing mods
Ausgewählte Mods herunterladen…|Download selected mods…
Für jede ausgewählte Mod die gewünschte Dateivariante wählen.|Choose a file variant for each selected mod.
{0} Mods · {1} ohne Downloadquelle. Die Liste enthält keine Moddateien.|{0} mods · {1} without download sources. The list contains no mod assets.
{0} fehlen · {1} vorhanden · {2} ohne Downloadquelle|{0} missing · {1} installed · {2} without download sources
Liste prüfen. Bestätigung lädt fehlende Mods herunter und installiert sie; Konflikte bleiben pausiert.|Review the list. Confirmation downloads and installs missing mods; conflicts stay paused.
Liste|List
Kacheln|Tiles
Listenansicht|List view
Kachelansicht|Tile view
Titelbild auswählen…|Choose cover…
Titelbild auswählen|Choose cover
Mod aktivieren oder pausieren|Enable or pause mod
Ausgewählt|Selected
Download entfernen|Remove download
Entfernt Eintrag und heruntergeladenes Archiv. Installierte Mods bleiben erhalten.|Removes the entry and cached archive. Installed mods are preserved.
Download entfernt. Installierte Mods bleiben erhalten.|Download removed. Installed mods are preserved.
Details|Details
Keine passenden Mods gefunden.\nVersuche einen anderen Suchbegriff.|No matching mods.\nTry another search term.
Installiert den Manager für dein Benutzerkonto. Deine Mods und Spieldaten bleiben erhalten.|Installs the manager for your account. Your mods and game data are preserved.
Der Manager ist eingerichtet. Deine Mods und Spieldaten bleiben erhalten.|The manager is ready. Your mods and game data are preserved.
Zusätzliche Voraussetzungen werden bei Bedarf geprüft.|Additional requirements are checked when needed.
Die neue Mod wird aktiviert. Rückgängig bleibt möglich.|The new mod will be enabled. Undo remains available.
Bibliothek|Library
Entdecken|Discover
Downloads|Downloads
Design|Appearance
Mehr â‹¯|More â‹¯
Dateien…|Files…
Ordner…|Folder…
Installieren|Install
Mods hinzufügen|Add mods
ZIP/RAR/7z oder Ordner hier ablegen|Drop ZIP/RAR/7z files or folders here
Mit Mods _spielen|_Play with mods
_Vanilla spielen|Play _vanilla
Mod entfernen|Remove mod
Rückgängig|Undo
Suchen|Search
Mods durchsuchen|Search mods
Installierte Mods|Installed mods
Mod auswählen|Select a mod
Details & Import|Details
_Details|_Details
_Aktivität|_Activity
_Importliste|_Import list
Info|Info
Bereit|Ready
Bereit.|Ready.
Fehler|Error
Hinweise|Notes
Abbrechen|Cancel
Überspringen|Skip
Öffnen|Open
Erneut versuchen|Try again
Pausiert|Paused
Aktiv|Active
Ungeprüft|Unchecked
Abgeschlossen|Completed
Fehlgeschlagen|Failed
Abgebrochen|Cancelled
Unterbrochen|Interrupted
Wartet|Queued
Prüfung|Verifying
Pruefen|Checking
Pruefung abgeschlossen|Check complete
Vorbereiten|Preparing
In Arbeit|In progress
Schon vorhanden|Already installed
Doppelt|Duplicate
Konflikt|Conflict
Installiert|Installed
Ungueltig|Invalid
Ausgelassen|Skipped
Import|Import
Heller Modus|Light
Dunkler Modus|Dark
Wie Windows|Use Windows setting
Hell, Dunkel oder Windows-Einstellung|Light, dark or Windows appearance
Alle Mods als ZIP exportieren…|Export all mods as ZIP…
Sichtbare Mods umschalten|Toggle visible mods
Sichtbare Mods aktivieren|Enable visible mods
Sichtbare Mods pausieren|Pause visible mods
GameBanana-Link öffnen…|Open GameBanana link…
Manager-Link zur Datei kopieren|Copy manager link to file
GameBanana-Updates prüfen|Check GameBanana updates
Bibliothek vollständig prüfen|Verify library
Protokolle öffnen|Open logs
Weitere Funktionen|More actions
Verbundenes OpenSmash-Spiel|Connected OpenSmash game
Eine oder mehrere ZIP-/RAR-/7z-Dateien prüfen (Strg+O)|Inspect ZIP/RAR/7z files (Ctrl+O)
Entpackten Mod-Ordner prüfen (Strg+Umschalt+O)|Inspect an extracted mod folder (Ctrl+Shift+O)
Geprüfte Auswahl installieren (Strg+I)|Install inspected selection (Ctrl+I)
Nach Mod-Namen suchen (Strg+F)|Search mod names (Ctrl+F)
Ausgewählte Mod aus der Auswahl entfernen; Rückgängig bleibt möglich|Remove selected mod; undo remains available
Vorherige Mod-Auswahl wiederherstellen (Strg+Z)|Restore previous mod selection (Ctrl+Z)
Noch keine Mods|No mods yet
Deine Bibliothek ist noch leer.\nFüge oben deine erste Mod hinzu.|Your library is empty.\nAdd your first mod above.
Prüfergebnis und Hinweise|Inspection results and notes
Aktivitätsprotokoll|Activity log
Mod-Auswahl pruefen|Inspect mod selection
Stapel-Fortschritt nach Mods|Batch progress by mod
Gepruefte Mods und Importergebnisse|Inspected mods and import results
Pausiert installieren|Install paused
Konfliktpartner ersetzen|Replace conflicting mods
Konflikte werden vor der Installation geklärt.|Resolve conflicts before installing.
Modmanager wird vorbereitet…|Preparing mod manager…
Vorgang läuft|Operation in progress
Vorgang läuft…|Working…
Mit aktiven Mods starten (F5)|Start with active mods (F5)
Ohne verwaltete Mods starten (F6)|Start without managed mods (F6)
GameBanana durchsuchen|Search GameBanana
Super Smash Bros. Ultimate: Suchbegriff eingeben. Ergebnisse nach Relevanz.|Search Super Smash Bros. Ultimate. Results are ranked by relevance.
GameBanana Kategorie|GameBanana category
Charakter für Skin-Mods|Character for skins
Charakterfilter für Skins. Tippen wählt einen Namen. Für Textsuche Alle Charaktere wählen.|Filter skins by character. Type to select a name. Choose All characters for text search.
GameBanana Sortierung|GameBanana sort order
Vorherige Seite|Previous page
Naechste Seite|Next page
GameBanana wird beim Oeffnen geladen.|GameBanana loads when opened.
GameBanana Ergebnisse|GameBanana results
Vorschaubild|Preview image
Dateien für Auswahl…|Choose files…
Mehrfachauswahl mit Strg oder Umschalt. Fuer jede Mod eine Datei selbst auswaehlen.|Select multiple mods with Ctrl or Shift. Choose a file for each mod.
Vorheriges Vorschaubild|Previous image
Naechstes Vorschaubild|Next image
Bild im Vollbild öffnen|View full screen
Vorschaubild im Vollbild öffnen|View preview full screen
Kompatibilität noch ungeprüft.|Compatibility has not been checked yet.
Abhängigkeiten & Installation|Dependencies and installation
Dateivariante ausdrücklich auswählen:|Choose a file:
GameBanana Dateivariante|GameBanana file variant
Download einreihen|Download
Quellseite â†—|Source page â†—
Noch keine Downloads. Mods findest du unter Entdecken.|No downloads yet. Find mods in Discover.
Downloadwarteschlange|Download queue
Auswahl installieren…|Install selection…
Auswahl abbrechen|Cancel selection
Alle Charaktere|All characters
Zuletzt aktualisiert|Recently updated
Neueste|Newest
Meiste Downloads|Most downloaded
Meiste Likes|Most liked
Alle Mods|All mods
Skins|Skins
Sounds|Sounds
Stages|Stages
Musik|Music
Datum unbekannt|Date unknown
Noch ungeprüft|Not checked yet
Noch ungeprüft · Dateiprüfung nach dem Download.|Not checked yet. Files are inspected after downloading.
Keine Variante vorausgewählt.|No file selected.
Keine öffentlichen Dateivarianten verfügbar. Quellseite prüfen.|No public files available. Check the source page.
Dateivarianten werden geladen…|Loading files…
Auswahl fertig. Downloads vor Installation prüfen.|Selection complete. Inspect downloads before installing.
Katalog wird geladen…|Loading catalog…
Details werden geladen…|Loading details…
Keine Ergebnisse. Anderen Suchbegriff versuchen.|No results. Try another search term.
Dateien und Anbieterprüfsummen verglichen; keine automatische Installation.|Files and provider checksums verified. Installation requires confirmation.
Download eingereiht. Prüfung und Installation folgen separat.|Download queued. Inspection and installation follow separately.
Downloads werden für die Importliste geprüft…|Inspecting downloads for import…
Downloads geprüft. Importliste und Konflikte prüfen, dann Installation bestätigen.|Downloads inspected. Review the import list and conflicts, then confirm installation.
GameBanana-Link öffnen|Open GameBanana link
Modseite oder kopierten 1-Click-Link einfügen:|Paste a mod page or copied one-click link:
Manager-Link zur gewählten Datei kopiert.|Manager link copied.
GameBanana-Link wird geprüft…|Checking GameBanana link…
GameBanana-Link konnte nicht geöffnet werden.|Could not open GameBanana link.
Verlinkte Datei wird heruntergeladen. Installation anschließend prüfen.|Downloading linked file. Review it before installing.
GameBanana-Dateiversionen werden geprüft…|Checking GameBanana file versions…
GameBanana-Updateprüfung abgeschlossen.|GameBanana update check complete.
Keine Mods mit GameBanana-Herkunft installiert. Manuell importierte Mods erhalten keine erfundene Zuordnung.|No mods with GameBanana provenance installed. Manually imported mods are not assigned a guessed source.
Schließen (Esc)|Close (Esc)
‹ Zurück|‹ Previous
Weiter ›|Next ›
Originalbild wird geladen…|Loading full-size image…
OpenSmash verbinden|Connect OpenSmash
Dein OpenSmash verbinden|Connect your OpenSmash game
Waehle deinen eingerichteten OpenSmash-Ordner mit Play SSBU.bat. Spiel und eigene Spieldaten werden separat bereitgestellt.|Choose your configured OpenSmash folder containing Play SSBU.bat. The game and game data are provided separately.
OpenSmash-Projektpfad hier einfuegen|Paste your OpenSmash folder path
OpenSmash-Pfad|OpenSmash path
Ordner auswaehlen…|Choose folder…
Pfad pruefen|Check path
Verbinden und oeffnen|Connect and open
Der Manager prueft den Ordner und zeigt fehlende Voraussetzungen.|The manager checks the folder and reports missing requirements.
Bitte einen vorhandenen OpenSmash-Ordner auswaehlen.|Choose an existing OpenSmash folder.
Installation wird geprueft…|Checking installation…
OpenSmash-Projektordner mit Play SSBU.bat|OpenSmash folder containing Play SSBU.bat
OpenSmash ist bereit. Du kannst den Manager jetzt verbinden.|OpenSmash is ready. You can now connect the manager.
Bitte die kurze Pruefung abschliessen lassen.|Please wait for the check to finish.
Python-Runtime fehlt. Bitte den vollstaendigen Installer verwenden.|Python runtime is missing. Use the complete installer.
Der gewählte Ordner ist kein OpenSmash-Projekt.|The selected folder is not an OpenSmash project.
UI-Komponente fehlt: |Missing UI component: 
Spiel: |Game: 
Fehler: |Error: 
Kompatibilität: |Compatibility: 
Installationspfad: |Installed at: 
Quelle: |Source: 
Autor: |Author: 
Version: |Version: 
Geprüft: |Verified: 
Export: |Export: 
Netzwerk-Worker: |Network worker: 
Abgeschlossen: |Completed: 
Spiel gestartet. Protokoll: |Game started. Log: 
Abbruch konnte nicht angefordert werden: |Could not request cancellation: 
 · Archiviert| · Archived
 · Manuell| · Manual
 · Experimentell| · Experimental
 · Nicht unterstützt| · Unsupported
 · Datei | · File 
 · Fehler: | · Errors: 
 · Relevanz (Kategorie/Sortierung nicht angewendet)| · Relevance (category and sort do not apply)
 Dateien| files
 Dateien · | files · 
 Mods bereit| mods ready
 Mods in einer ZIP| mods in one ZIP
 Mods installieren| mods to install
 – Bilder| – Images
 beendet. | terminated. 
{0} Mods · {1} aktiv|{0} mods · {1} active
{0} Downloads · {1} in Arbeit.|{0} downloads · {1} in progress.
{0} erkannt · {1} bereit · {2} übersprungen/ungültig|{0} found · {1} ready · {2} skipped/invalid
{0} erkannt · {1} bereit · Konflikte vor Installation entscheiden|{0} found · {1} ready · Resolve conflicts before installing
{0} installiert · {1} fehlgeschlagen · {2} übersprungen|{0} installed · {1} failed · {2} skipped
Seite {0} · {1} Ergebnisse{2}|Page {0} · {1} results{2}
Stapel {0}/{1}: Datei wählen oder überspringen|Batch {0}/{1}: choose a file or skip
1 Mod installieren|Install 1 mod
Abbruch angefordert. Ein laufender Profilwechsel wird sicher beendet.|Cancellation requested. Any profile switch will finish safely.
Abbruch angefordert. Ein Profilwechsel wird sicher beendet.|Cancellation requested. Any profile switch will finish safely.
Aktivierung wird angewendet…|Applying activation…
Alle Bibliotheks- und Profildateien stimmen mit ihren Prüfsummen überein.|All library and profile files match their checksums.
Alle Dateien werden vollständig geprüft…|Verifying all files…
Alle installierten Mods exportieren|Export all installed mods
Alle Mods werden als ZIP exportiert…|Exporting all mods as ZIP…
Änderungen an der Mod-Auswahl gelten nach einem Neustart.|Changes to mod selection apply after restarting the game.
Auswahl gespeichert|Selection saved
Auswahl wird gemeinsam angewendet…|Applying selection…
Auswahl wird geprueft. Fortschritt nach Quellen/Mods.|Inspecting selection. Progress is shown by source/mod.
Begleitdateien werden ausgelassen:|Additional files will be skipped:
Bereit zur Installation|Ready to install
Betroffene Profildateien vorbereiten|Preparing affected profile files
Bitte den Hinweis prüfen und anschließend erneut versuchen.|Review the details, then try again.
Bitte den laufenden Vorgang beenden lassen, bevor du das Fenster schließt.|Wait for the current operation to finish before closing the window.
Deine Bibliothek wird geladen…|Loading your library…
Die Dateien sind für die Installation vorbereitet.|The files are ready to install.
Die Mod wird geprüft…|Inspecting mod…
Die Mod wird zunächst geprüft.|The mod will be inspected first.
Diese Konfliktpartner werden pausiert: |These conflicting mods will be paused: 
Ein Problem ist aufgetreten. Details stehen rechts.|A problem occurred. See the details on the right.
Erste Loader-Einrichtung erforderlich. Das kann mehrere Minuten dauern.|Initial loader setup is required. This can take several minutes.
Export abgeschlossen|Export complete
Haken = aktiv. Änderungen gelten beim nächsten Spielstart.|Checked means active. Changes apply next time you start the game.
Hier ablegen|Drop here
Importentscheidung wird übernommen…|Applying import choices…
Installiert · |Installed · 
Keine verwertbare Antwort vom Modmanager. |No usable response from mod manager. 
Mit „Installieren und aktivieren“ zur Bibliothek hinzufügen.|Add to your library using Install.
Mit Rückgängig kannst du die vorherige Auswahl wiederherstellen.|Use Undo to restore the previous selection.
Mod ist in deiner Bibliothek|Mod is in your library
Mod wird aus dem Profil in die Rückgängig-Ablage verschoben…|Moving mod to undo storage…
Mod wird installiert. Die erste Einrichtung kann einige Minuten dauern…|Installing mod. First-time setup can take several minutes…
Mod-Archive auswählen|Choose mod archives
Mod-Auswahl wird geprüft…|Inspecting mod selection…
Mod-Ordner mit fighter, ui, effect oder sound auswählen|Choose a mod folder containing fighter, ui, effect or sound
Mod-ZIP, RAR oder Mod-Ordner ablegen|Drop a mod ZIP, RAR or folder
Modmanager wurde mit Fehlercode |Mod manager exited with error code 
Nach dem ersten Spielstart findest du hier die Protokolle.|Logs will be available here after the first game launch.
Noch keine Spielprotokolle|No game logs yet
OpenSmash wird gestartet…|Starting OpenSmash…
OpenSmash wurde gestartet.|OpenSmash started.
Plugin-Übersetzung erforderlich. Das kann mehrere Minuten dauern.|Plugin translation is required. This can take several minutes.
Profil sicher umschalten|Switching profile safely
Prüfsummen vollständig prüfen|Verify all checksums
Prüfung abgebrochen.|Inspection cancelled.
Prüfung abgeschlossen. Du kannst die Mod jetzt installieren.|Inspection complete. You can now install the mod.
Prüfung nicht abgeschlossen|Inspection incomplete
Stapel wird vorbereitet und installiert…|Preparing and installing batch…
Suche nach Relevanz · |Search by relevance · 
Viel Spaß beim Spielen.|Enjoy the game.
Vollständige Prüfung|Full verification
Vollständige Prüfung abgeschlossen.|Full verification complete.
Vorgang nicht ausgeführt|Operation not completed
Vorherige Auswahl wird wiederhergestellt…|Restoring previous selection…
Vorschau fertig. Konflikte und vorhandene Mods werden übersprungen.|Inspection complete. Conflicting and existing mods will be skipped.
Wirksam beim nächsten Spielstart.|Applies next time you start the game.
Deine Mods. Dein Spiel.|Your mods. Your game.
OpenSmash-Ordner (optional, spaeter waehlbar)|OpenSmash folder (optional; choose later)
Auswaehlen …|Browse…
OpenSmash-Ordner mit Play SSBU.bat|OpenSmash folder containing Play SSBU.bat
Desktop-Verknuepfung mit Programmlogo erstellen|Create a desktop shortcut
Offizielle C++ Build Tools / Windows SDK|Official C++ Build Tools / Windows SDK
Schliessen|Close
Manager oeffnen|Open manager
Installation sicher abgebrochen.|Installation cancelled safely.
Abbruch wird am sicheren Punkt ausgefuehrt …|Cancelling at a safe point…
Installation abgebrochen. Vorheriger Zustand bleibt erhalten.|Installation cancelled. Previous state preserved.
Installationsdaten fehlen.|Installation payload missing.
Python und Bibliotheken werden geprueft …|Checking Python and libraries…
Pruefung fehlgeschlagen: |Check failed: 
Pruefsumme ungueltig: |Invalid checksum: 
Ziel: |Destination: 
Alle Downloads löschen…|Clear all downloads…
Alle Downloads löschen|Clear all downloads
Alle löschen|Delete all
Datei speichern…|Save file…
Datei speichern|Save file
 · Nur Download| · Download only
 · Gesperrt| · Restricted
Alle Download-Einträge und gespeicherten Archive löschen? Laufende Downloads werden abgebrochen. Installierte Mods bleiben erhalten.|Delete all download entries and cached archives? Active transfers will be cancelled. Installed mods are preserved.
Downloads werden abgebrochen und entfernt…|Cancelling and removing downloads…
Downloads entfernt.|Downloads removed.
Downloads werden abgebrochen und automatisch entfernt.|Cancelling downloads and removing them automatically.
Alle Downloads entfernt. Installierte Mods bleiben erhalten.|All downloads removed. Installed mods are preserved.
Datei gespeichert.|File saved.
Mod-ZIP, RAR, 7z oder Mod-Ordner ablegen|Drop a mod ZIP, RAR, 7z or folder
ZIP-, RAR-, 7z-Dateien oder Mod-Ordner ablegen|Drop ZIP, RAR, 7z files or mod folders
"""


def main():
    messages = {}
    for line in ENGLISH.splitlines():
        if "|" in line:
            source, english = line.split("|", 1)
            messages[source.replace(r"\n", "\n")] = {"en": english.replace(r"\n", "\n")}
    # Additional reviewed workflow translations are maintained separately from
    # technical diagnostics, whose explicit fallback is English.
    additions = SOURCE / "workflow_translations.json"
    if additions.exists():
        for key, translations in json.loads(
            additions.read_text(encoding="utf-8")
        ).items():
            messages.setdefault(key, {}).update(translations)
    (SOURCE / "locales.json").write_text(
        json.dumps(messages, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(messages)} source phrases")


if __name__ == "__main__":
    main()
