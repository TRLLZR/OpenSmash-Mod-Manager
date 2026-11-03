# OpenSmash Mod Manager 3.7.0

Native Windows-Anwendung zum Finden, Installieren und Verwalten von OpenSmash-Mods.
Das Projekt entstand mit umfangreicher Unterstützung durch ChatGPT und Codex.

## Einstieg

1. Installer-ZIP entpacken und **Setup.exe** starten.
2. Den vorhandenen OpenSmash-Ordner verbinden.
3. ZIP-/RAR-/7z-Dateien oder Mod-Ordner auf **Mods hinzufügen** ziehen oder unter
   **Entdecken** eine GameBanana-Dateivariante herunterladen.
4. Importvorschau und Konflikte prüfen und die Installation bestätigen.
5. Mods in der Bibliothek aktivieren und **Mit Mods spielen** wählen.
   **Vanilla spielen** startet ohne das aktive Modprofil.

## Bibliothek und Downloads

**Liste / Kacheln** wechselt die gespeicherte Ansicht. Titelbilder stammen aus
lokalen Vorschauen oder der gespeicherten GameBanana-Quelle; unter
**Mehr > Titelbild auswählen…** lässt sich ein eigenes Bild setzen.
**Rückgängig** stellt den vorherigen verwalteten Zustand wieder her.

**Download entfernen** löscht ausgewählte abgeschlossene Einträge und Archive.
**Alle Downloads löschen…** bricht laufende Transfers ab und räumt die
Downloadliste nach Bestätigung auf. Installierte Mods bleiben erhalten.
Öffentliche Dateiformate ohne direkten Importweg lassen sich mit
**Nur Download** laden und anschließend speichern.

**Mehr > Modliste teilen…** exportiert eine kleine `.opensmash-list.json`.
Empfänger importieren sie, prüfen die Vorschau und bestätigen
**Fehlende Mods installieren**. Bereits vorhandene Mods behalten ihre Aktivierung;
Konflikte werden pausiert installiert. Mods ohne gespeicherte Anbieterquelle und
lokale Änderungen benötigen die Originaldateien oder den vollständigen ZIP-Export.

## Sprache und Darstellung

Die Oberfläche folgt der Windows-Anzeigesprache in 16 Sprachfamilien.
Ergänzende Texte können auf Englisch und ältere technische Meldungen auf Deutsch
erscheinen. Modbeschreibungen bleiben in ihrer Originalsprache.
**Design** bietet Hell, Dunkel und **Wie Windows** sowie Windows-Kontrastfarben.

## Weitere Informationen

Modtypen werden anhand ihrer Struktur erkannt. Gameplay-Plugins benötigen
passende Bibliotheken und gegebenenfalls lokale C++-Build-Werkzeuge. Details
stehen in **BEKANNTE_EINSCHRAENKUNGEN.md** und **ABHAENGIGKEITEN.md**.
Spielstände und persönliche Spielkonfiguration bleiben beim Manager-Update erhalten.

**ANLEITUNG.txt** und **MODMANAGER_DE.md** erklären die Bedienung ausführlicher.
**README.md** dokumentiert Architektur und Entwicklung auf Englisch.
Lizenzen: **LICENSE.txt**, **THIRD_PARTY_NOTICES.txt** und **BRANDING.md**.
